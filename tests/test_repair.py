"""Tests for the card-format repair CLI (yoto_maker/yoto/repair.py + client additions).

Everything runs against a MOCKED client — no network, no ffmpeg, no live calls.
The six safety guarantees the plan requires are T1..T6 below; the probe classifier
and the pinned real-body shape are covered directly against a tiny httpx fake.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from yoto_maker.yoto import auth
from yoto_maker.yoto.client import ArtifactProbe, CardSummary, YotoClient, YotoError
from yoto_maker.yoto.repair import (
    apply_format_corrections,
    build_repair_payload,
    canonical_track_url,
    canonicalize_body_track_urls,
    iter_tracks,
    plan_card,
    repair_card,
    resolve_targets,
    verify_only_format_changed,
)

FIXTURE = Path(__file__).parent / "fixtures" / "card_sample.json"


# --------------------------------------------------------------------------- #
# Task 1: the probe classifier + update_card, against a tiny local httpx fake
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, headers=None, content=b""):
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        pass


def test_probe_reads_opus_content_type():
    class HttpFake:
        def head(self, url, **k):
            return _Resp({"Content-Type": "audio/ogg; codecs=opus"})

        def get(self, url, **k):
            return _Resp(content=b"OggS...OpusHead...")

    yc = YotoClient(client=HttpFake())
    assert yc.probe_artifact("https://x/a").is_opus


def test_probe_sniffs_ogg_opus_magic_when_content_type_is_generic():
    """The REAL field case: Content-Type is a bare 'audio/ogg' (no codecs param),
    so the magic-byte sniff is what actually confirms Opus."""
    class HttpFake:
        def head(self, url, **k):
            return _Resp({"Content-Type": "audio/ogg"})

        def get(self, url, **k):
            return _Resp({"Content-Type": "audio/ogg"},
                         b"OggS\x00\x02" + b"\x00" * 20 + b"OpusHead" + b"\x00" * 20)

    assert YotoClient(client=HttpFake()).probe_artifact("https://x/a").is_opus


def test_probe_rejects_non_opus():
    class HttpFake:
        def head(self, url, **k):
            return _Resp({"Content-Type": "audio/mpeg"})

        def get(self, url, **k):
            return _Resp({"Content-Type": "audio/mpeg"}, b"ID3\x03mp3data")

    p = YotoClient(client=HttpFake()).probe_artifact("https://x/a")
    assert p.is_opus is False and "not Opus" in p.detail


def test_probe_soft_fails_when_artifact_unreadable():
    """probe never raises: a HEAD-rejecting, GET-erroring URL is a soft non-Opus."""
    class HttpFake:
        def head(self, url, **k):
            raise RuntimeError("no HEAD")

        def get(self, url, **k):
            raise RuntimeError("boom")

    p = YotoClient(client=HttpFake()).probe_artifact("https://x/a")
    assert p.is_opus is False and "couldn't read" in p.detail


def test_update_card_injects_cardid_and_posts_content(monkeypatch):
    monkeypatch.setattr(auth, "get_access_token", lambda *a, **k: "T")
    posts = []

    class HttpFake:
        def post(self, url, json=None, headers=None, **k):
            posts.append((url, json))

            class R:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"cardId": "C1"}

            return R()

    YotoClient(client=HttpFake()).update_card("C1", {"title": "T", "content": {}})
    assert posts[0][0].endswith("/content")
    assert posts[0][1]["cardId"] == "C1"


# --------------------------------------------------------------------------- #
# Pinned real shape (plan Task 1/Step 0): GET /card returns {"card":..., "ownership":...}
# and each track's pre-signed artifact URL lives on `trackUrl`.
# --------------------------------------------------------------------------- #
def test_get_card_unwraps_card_envelope(monkeypatch):
    monkeypatch.setattr(auth, "get_access_token", lambda *a, **k: "T")
    envelope = {"card": {"cardId": "C1", "title": "T", "content": {"chapters": []}},
                "ownership": {"canAccess": True}}

    class HttpFake:
        def get(self, url, **k):
            class R:
                def raise_for_status(self):
                    pass

                def json(self):
                    return envelope

            return R()

    inner = YotoClient(client=HttpFake()).get_card("C1")
    assert inner == {"cardId": "C1", "title": "T", "content": {"chapters": []}}
    assert "ownership" not in inner


def test_real_fixture_pins_shape_trackurl_and_format(monkeypatch):
    """Against the sanitized REAL GET /card/gzP2B body: get_card unwraps the
    envelope, chapters resolve at content.chapters, and the pre-signed artifact
    URL is picked up from `trackUrl` (an https URL, not a yoto:#sha ref)."""
    monkeypatch.setattr(auth, "get_access_token", lambda *a, **k: "T")
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    class HttpFake:
        def get(self, url, **k):
            class R:
                def raise_for_status(self):
                    pass

                def json(self):
                    return raw

            return R()

    inner = YotoClient(client=HttpFake()).get_card("gzP2B")
    assert "ownership" not in inner and inner["cardId"] == "gzP2B"
    tracks = iter_tracks(inner)
    assert len(tracks) == 1
    assert tracks[0].declared_format == "mp3"
    assert tracks[0].artifact_url and tracks[0].artifact_url.startswith("http")


# --------------------------------------------------------------------------- #
# Orchestration fixtures + fake client (pure Python — no network)
# --------------------------------------------------------------------------- #
def _card(card_id="C1", formats=("mp3", "mp3"), with_urls=True, title="Test Card"):
    """A GET /card body in the UNWRAPPED (inner-card) shape — one track per
    chapter, with icons, keys, durations, sizes, channels: everything the verify
    must preserve. `trackUrl` is the RESOLVED, pre-signed https artifact URL when
    Yoto has served the card (reality), or an unresolved `yoto:#sha` ref when it
    can't be probed (with_urls=False)."""
    chapters = []
    for i, fmt in enumerate(formats, start=1):
        key = f"{i:02d}"
        track = {
            "key": key, "title": f"Track {i}", "type": "audio", "format": fmt,
            "duration": 100 + i, "fileSize": 1000 + i, "channels": "stereo",
            "display": {"icon16x16": f"https://card-content.example/{card_id}/{i}?sig=ICON{i}"},
            "trackUrl": (
                f"https://secure-media.example/{card_id}/{i}?Expires=1&Signature=EPHEMERAL{i}#sha256=SHA{i}"
                if with_urls else f"yoto:#SHA{i}"
            ),
        }
        chapters.append({"key": key, "title": f"Track {i}", "tracks": [track]})
    return {"cardId": card_id, "title": title,
            "content": {"chapters": chapters},
            "updatedAt": "2026-07-21T00:00:00Z"}


class FakeClient:
    """Scripts get_card/list_my_cards/update_card/probe_artifact. get_card returns
    the original until a POST happens, then the posted body (or an `after`
    override, to simulate the server changing something unexpectedly)."""

    def __init__(self, body, *, probe=None, after=None, summaries=None):
        self._body = copy.deepcopy(body)
        self._after = after
        self._probe = probe or (lambda url: ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
        self._summaries = summaries
        self.posts = []

    def is_connected(self):
        return True

    def list_my_cards(self):
        if self._summaries is not None:
            return self._summaries
        return [CardSummary(self._body.get("cardId", "C1"), self._body.get("title", "Test Card"), "2026-07-21", 2)]

    def probe_artifact(self, url):
        return self._probe(url)

    def get_card(self, card_id):
        if self.posts:
            return copy.deepcopy(self._after if self._after is not None else self.posts[-1])
        return copy.deepcopy(self._body)

    def update_card(self, card_id, body):
        self.posts.append(copy.deepcopy(body))
        return {"cardId": card_id}


# --------------------------------------------------------------------------- #
# The six required safety guarantees
# --------------------------------------------------------------------------- #
def test_corrector_sets_only_format_everything_else_byte_identical():
    """T1: apply_format_corrections sets format='opus' and leaves every other field
    byte-identical (deep structural equality), and does not mutate its input."""
    before = _card("C1", ("mp3", "mp3"))
    expected = copy.deepcopy(before)
    for ch in expected["content"]["chapters"]:
        ch["tracks"][0]["format"] = "opus"

    out = apply_format_corrections(before, {"0.0", "1.0"})

    assert out == expected                                   # ONLY format changed, everywhere
    assert before["content"]["chapters"][0]["tracks"][0]["format"] == "mp3"  # input untouched


def test_unprobeable_or_non_opus_track_skips_whole_card_no_post(tmp_path):
    """T2: a single non-Opus/unprobeable track blocks the ENTIRE card (all-or-nothing):
    no POST is issued and the card is reported skipped."""
    def probe(url):
        # track 2's artifact is (say) still MP3 / unreadable
        return (ArtifactProbe(False, "Content-Type audio/mpeg — not Opus", "audio/mpeg")
                if "EPHEMERAL2" in url else ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
    fake = FakeClient(_card("C1", ("mp3", "mp3")), probe=probe)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []                                  # NEVER wrote a partial card
    assert len(res.plan.blocked) == 1


def test_unresolvable_artifact_url_blocks_card(tmp_path):
    """A track whose trackUrl never resolved to an https URL (still yoto:#sha) is
    unprobeable -> blocks the whole card, no POST."""
    fake = FakeClient(_card("C1", ("mp3", "mp3"), with_urls=False))
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "blocked"
    assert fake.posts == []
    assert all("no resolvable artifact URL" in d.reason for d in res.plan.blocked)


def test_dry_run_issues_no_post(tmp_path):
    """T3."""
    fake = FakeClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=False, backup_dir=tmp_path / "b")
    assert res.outcome == "dry-run"
    assert res.plan.correct_keys == {"0.0", "1.0"}
    assert fake.posts == []


def test_idempotent_already_opus_no_post(tmp_path):
    """T4."""
    fake = FakeClient(_card("C1", ("opus", "opus")))
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "already"
    assert fake.posts == []


def test_backup_written_before_any_post(tmp_path):
    """T5: the backup file must be durably on disk BEFORE the POST fires, and hold
    the verbatim ORIGINAL (still-mp3) body."""
    backup_dir = tmp_path / "b"
    existed_at_post = {"value": None}

    class OrderingClient(FakeClient):
        def update_card(self, card_id, body):
            existed_at_post["value"] = any(backup_dir.glob(f"{card_id}-*.json"))
            return super().update_card(card_id, body)

    fake = OrderingClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=True, backup_dir=backup_dir)

    assert existed_at_post["value"] is True                 # backup existed when POST ran
    assert res.backup_path and res.backup_path.exists()
    saved = json.loads(res.backup_path.read_text(encoding="utf-8"))
    assert saved["content"]["chapters"][0]["tracks"][0]["format"] == "mp3"


def test_verify_catches_an_unexpected_extra_field_change(tmp_path):
    """T6a: if the re-GET shows a change beyond the intended format flip, verify fails."""
    after = _card("C1", ("opus", "opus"))
    after["title"] = "Changed By Server"                    # an unsanctioned change
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "verify-failed"
    assert any("title" in p.lower() for p in res.problems)


def test_verify_passes_when_only_format_changed(tmp_path):
    """T6b: the happy path — re-GET differs only in format (+ rotated pre-signed
    URL signatures and updatedAt, which must be ignored)."""
    after = _card("C1", ("opus", "opus"))
    after["updatedAt"] = "2026-07-21T23:59:59Z"             # volatile, must be ignored
    # Rotate the pre-signed signatures (query only) — the sha-bearing path is stable,
    # exactly as the real CDN URLs behave across the ~60-min signing window.
    for i, ch in enumerate(after["content"]["chapters"], start=1):
        tr = ch["tracks"][0]
        tr["trackUrl"] = f"https://secure-media.example/C1/{i}?Expires=999&Signature=ROTATED{i}#sha256=SHA{i}"
        tr["display"]["icon16x16"] = f"https://card-content.example/C1/{i}?sig=ROTATEDICON{i}"
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert res.problems == []
    assert len(fake.posts) == 1


def test_verify_catches_a_changed_artifact_resource(tmp_path):
    """Safety beyond the plan's original strip: if the POST changed the artifact
    the track points at (a different sha-bearing PATH, not just a rotated
    signature), verify catches it. URL normalization keeps the path, so a real
    remap is NOT masked."""
    after = _card("C1", ("opus", "opus"))
    after["content"]["chapters"][0]["tracks"][0]["trackUrl"] = (
        "https://secure-media.example/C1/DIFFERENT?Signature=x#sha256=OTHER")
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "verify-failed"
    assert any("trackurl" in p.lower() or "different" in p.lower() for p in res.problems)


def test_verify_ignores_a_bumped_content_version(tmp_path):
    """Pre-merge review MEDIUM #3: Yoto may bump the nested `content.version`
    counter on any write; that must not read as a verify failure."""
    before = _card("C1", ("mp3", "mp3"))
    before["content"]["version"] = "1"
    after = _card("C1", ("opus", "opus"))
    after["content"]["version"] = "2"                       # server bumped it on write
    fake = FakeClient(before, after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert res.problems == []


def test_write_uncertain_when_post_errors_after_backup(tmp_path):
    """Pre-merge review HIGH #2: if the POST raises AFTER the backup is durable,
    the result is 'write-uncertain' (never a bare escape) and carries the backup."""
    class RaisingClient(FakeClient):
        def update_card(self, card_id, body):
            raise YotoError("connection reset by peer")

    backup_dir = tmp_path / "b"
    fake = RaisingClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=True, backup_dir=backup_dir)

    assert res.outcome == "write-uncertain"
    assert res.backup_path and res.backup_path.exists()     # backup stayed durable
    assert any("may already have landed" in p.lower() for p in res.problems)


def test_empty_card_reports_empty_not_already(tmp_path):
    """Pre-merge review MEDIUM #4: a card the walker finds no tracks on reports
    'empty' (a possible parse miss), distinct from a genuinely already-correct card."""
    fake = FakeClient({"cardId": "C1", "title": "Empty", "content": {"chapters": []}})
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "empty"
    assert fake.posts == []


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def test_resolve_targets_passes_card_ids_through():
    fake = FakeClient(_card())
    assert resolve_targets(fake, card_ids=["1WCvI", "gzP2B", "7FcVe"], titles=[]) == [
        ("1WCvI", "1WCvI"), ("gzP2B", "gzP2B"), ("7FcVe", "7FcVe")]


def test_resolve_targets_refuses_ambiguous_title():
    summaries = [CardSummary("A", "The Wild Robot", "d1", 5),
                 CardSummary("B", "The Wild Robot 2", "d2", 3)]
    fake = FakeClient(_card(), summaries=summaries)
    with pytest.raises(YotoError) as exc:
        resolve_targets(fake, card_ids=[], titles=["wild"])   # substring-matches both
    assert "disambiguate" in str(exc.value).lower()


def test_resolve_targets_matches_exact_title():
    summaries = [CardSummary("A", "The BFG", "d1", 18),
                 CardSummary("B", "The BFG Read-Along", "d2", 18)]
    fake = FakeClient(_card(), summaries=summaries)
    assert resolve_targets(fake, card_ids=[], titles=["The BFG"]) == [("A", "The BFG")]


# --------------------------------------------------------------------------- #
# Rollback
# --------------------------------------------------------------------------- #
def test_rollback_reposts_backup_in_place(tmp_path):
    """--rollback re-POSTs a backup body with its cardId and verifies the re-GET."""
    original = _card("C1", ("mp3", "mp3"))
    backup = tmp_path / "C1-backup.json"
    backup.write_text(json.dumps(original), encoding="utf-8")
    fake = FakeClient(_card("C1", ("mp3", "mp3")))
    from yoto_maker.yoto.repair import rollback_from_backup

    res = rollback_from_backup(fake, backup)

    assert res.outcome == "restored"
    assert len(fake.posts) == 1
    assert fake.posts[0]["cardId"] == "C1"


def test_rollback_posts_canonical_refs_not_expiring_urls(tmp_path):
    """The rollback POST must ALSO canonicalize trackUrls (the backup holds resolved,
    now-expired signed URLs) so a restore never re-introduces HIGH #1."""
    original = _card("C1", ("mp3", "mp3"))
    backup = tmp_path / "C1-backup.json"
    backup.write_text(json.dumps(original), encoding="utf-8")
    fake = FakeClient(_card("C1", ("mp3", "mp3")))
    from yoto_maker.yoto.repair import rollback_from_backup

    res = rollback_from_backup(fake, backup)

    assert res.outcome == "restored"
    posted = fake.posts[0]
    urls = [ch["tracks"][0]["trackUrl"] for ch in posted["content"]["chapters"]]
    assert urls == ["yoto:#SHA1", "yoto:#SHA2"]
    assert "secure-media" not in json.dumps(posted)     # no resolved/expiring URL restored


# --------------------------------------------------------------------------- #
# HIGH #1 hardening: canonicalize resolved trackUrls to yoto:#<sha> before POST
# --------------------------------------------------------------------------- #
def test_canonicalize_extracts_sha_from_fragment():
    """The #sha256=<sha> fragment is the preferred (most reliable) source."""
    raw = ("https://secure-media.yotoplay.com/POLICYtoken~/44aJsha?"
           "Expires=1&Signature=S&Key-Pair-Id=K#sha256=44aJsha")
    canon, err = canonical_track_url(raw)
    assert err is None
    assert canon == "yoto:#44aJsha"


def test_canonicalize_enforces_fragment_path_agreement():
    """If the #sha256 fragment and the ~/<sha> path segment DISAGREE, refuse (block) —
    never guess which is the real sha."""
    raw = "https://secure-media.yotoplay.com/POLICYtoken~/PATHsha?Signature=S#sha256=FRAGsha"
    canon, err = canonical_track_url(raw)
    assert canon is None
    assert err and "sha" in err.lower()


def test_canonicalize_from_path_when_no_fragment():
    """No fragment -> fall back to the ~/<sha> path segment."""
    raw = "https://secure-media.yotoplay.com/POLICYtoken~/onlyPathSha?Expires=1&Signature=S"
    canon, err = canonical_track_url(raw)
    assert err is None
    assert canon == "yoto:#onlyPathSha"


def test_canonicalize_leaves_already_canonical_ref_untouched():
    """An already-canonical yoto:#<sha> ref is returned verbatim (never rewritten)."""
    canon, err = canonical_track_url("yoto:#alreadyCanonicalSha")
    assert err is None
    assert canon == "yoto:#alreadyCanonicalSha"


def test_canonicalize_unrecognized_form_is_an_error():
    canon, err = canonical_track_url("ftp://weird/thing")
    assert canon is None
    assert err


def test_unextractable_sha_blocks_whole_card_no_post(tmp_path):
    """A resolved trackUrl whose sha can't be extracted/validated (fragment/path
    disagree) blocks the ENTIRE card (all-or-nothing) — no POST."""
    body = _card("C1", ("mp3", "mp3"))
    # tamper track 1: fragment and path disagree -> unvalidatable sha
    body["content"]["chapters"][0]["tracks"][0]["trackUrl"] = (
        "https://secure-media.example/POLICY~/PATHsha?Signature=S#sha256=FRAGsha")
    fake = FakeClient(body)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []
    assert any("sha" in d.reason.lower() for d in res.plan.blocked)


def test_post_body_uses_canonical_refs_not_resolved_urls(tmp_path):
    """THE core assertion: the body handed to update_card contains yoto:#<sha> for
    every track and NOT the resolved secure-media signed URL."""
    fake = FakeClient(_card("C1", ("mp3", "mp3")))

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert len(fake.posts) == 1
    posted = fake.posts[0]
    urls = [ch["tracks"][0]["trackUrl"] for ch in posted["content"]["chapters"]]
    assert urls == ["yoto:#SHA1", "yoto:#SHA2"]
    dumped = json.dumps(posted)
    assert "secure-media" not in dumped                 # the audio host is gone
    assert "EPHEMERAL" not in dumped                    # so is the ephemeral signature
    assert "Expires=" not in dumped


def test_mixed_card_canonicalizes_all_tracks_including_already_opus(tmp_path):
    """Every track in the POST body is canonicalized — even a track that was already
    'opus' and not format-corrected — because the whole card is re-POSTed."""
    fake = FakeClient(_card("C1", ("opus", "mp3")))     # track 1 already opus, track 2 mp3

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    posted = fake.posts[0]
    urls = [ch["tracks"][0]["trackUrl"] for ch in posted["content"]["chapters"]]
    formats = [ch["tracks"][0]["format"] for ch in posted["content"]["chapters"]]
    assert urls == ["yoto:#SHA1", "yoto:#SHA2"]         # BOTH canonicalized
    assert formats == ["opus", "opus"]                  # track 1 stays opus, track 2 corrected


def test_icons_left_verbatim_stable_case(tmp_path):
    """The real card serves icons from STABLE card-content URLs (no Expires/Signature),
    so they are re-POSTed byte-for-byte — canonicalization touches trackUrl only."""
    before = _card("C1", ("mp3", "mp3"))
    fake = FakeClient(copy.deepcopy(before))

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    posted = fake.posts[0]
    for ch_post, ch_before in zip(posted["content"]["chapters"], before["content"]["chapters"]):
        assert (ch_post["tracks"][0]["display"]["icon16x16"]
                == ch_before["tracks"][0]["display"]["icon16x16"])


def test_signed_icon_blocks_whole_card_no_post(tmp_path):
    """A SIGNED/expiring icon URL (Expires/Signature) would break if re-POSTed
    verbatim, and this tool does not canonicalize icons -> block the whole card."""
    body = _card("C1", ("mp3", "mp3"))
    body["content"]["chapters"][0]["tracks"][0]["display"]["icon16x16"] = (
        "https://card-content.example/POLICY~/mediaid?Expires=1&Signature=SIG&Key-Pair-Id=K")
    fake = FakeClient(body)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []
    assert any("signed" in p.lower() and "icon" in p.lower() for p in res.problems)


def test_signed_chapter_level_icon_also_blocks(tmp_path):
    """The chapter-level display.icon16x16 is checked too, not just the track-level."""
    body = _card("C1", ("mp3", "mp3"))
    body["content"]["chapters"][0]["display"] = {
        "icon16x16": "https://card-content.example/POLICY~/mediaid?Expires=1&Signature=SIG"}
    fake = FakeClient(body)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []


def test_stable_icon_does_not_block(tmp_path):
    """The stable case (the real card): an unsigned card-content icon URL is fine and
    the card is corrected normally."""
    fake = FakeClient(_card("C1", ("mp3", "mp3")))     # _card icons are `?sig=ICONi` (no Expires/Signature)
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "applied"


def _real_shaped_card(formats, *, prefix, sig):
    """A card whose URLs use the REAL '<policy>~/<key>...#sha256=<key>' shape, so a
    test can rotate the policy prefix AND the signature (as a real re-GET does)."""
    chapters = []
    for i, fmt in enumerate(formats, start=1):
        sha = f"AUDIOsha{i}base64token"
        icon = f"ICONmedia{i}base64token"
        track = {
            "key": f"{i:02d}", "title": f"Track {i}", "type": "audio", "format": fmt,
            "duration": 100 + i, "fileSize": 1000 + i, "channels": "stereo",
            "display": {"icon16x16": f"https://card-content.example/{prefix}~/{icon}"},
            "trackUrl": (f"https://secure-media.example/{prefix}~/{sha}?"
                         f"Expires=9&Signature={sig}&Key-Pair-Id=K#sha256={sha}"),
        }
        chapters.append({"key": f"{i:02d}", "title": f"Track {i}", "tracks": [track]})
    return {"cardId": "C1", "title": "Real Shaped", "content": {"chapters": chapters},
            "updatedAt": "2026-07-22T00:00:00Z"}


def test_verify_passes_across_rotated_prefix_and_signature_same_sha(tmp_path):
    """Real-shaped round-trip: the re-GET rotates BOTH the <policy>~ path prefix and
    the query signature but keeps the same sha -> verify passes (sha-based, not naive)."""
    before = _real_shaped_card(("mp3", "mp3"), prefix="POLICYA", sig="SIGA")
    after = _real_shaped_card(("opus", "opus"), prefix="POLICYB", sig="SIGB")
    fake = FakeClient(before, after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied", res.problems
    assert res.problems == []


def test_verify_fails_when_the_sha_actually_changes(tmp_path):
    """If the re-GET's trackUrl carries a DIFFERENT sha, the verify catches it even
    though the prefix/signature also rotated."""
    before = _real_shaped_card(("mp3", "mp3"), prefix="POLICYA", sig="SIGA")
    after = _real_shaped_card(("opus", "opus"), prefix="POLICYB", sig="SIGB")
    after["content"]["chapters"][0]["tracks"][0]["trackUrl"] = (
        "https://secure-media.example/POLICYB~/COMPLETELYdifferentsha?"
        "Expires=9&Signature=SIGB#sha256=COMPLETELYdifferentsha")
    fake = FakeClient(before, after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "verify-failed"
    assert any("trackurl" in p.lower() for p in res.problems)


def test_real_fixture_trackurl_canonicalizes_to_yoto_sha():
    """Against the sanitized REAL GET /card/gzP2B body: the resolved trackUrl
    canonicalizes to yoto:#<sha>, and the icon is the STABLE case (no expiry/signature),
    so it is left as-is."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    inner = raw["card"]
    refs = iter_tracks(inner)
    assert len(refs) == 1
    canon, err = canonical_track_url(refs[0].track_url_raw)
    assert err is None
    assert canon == "yoto:#44aJeE5Xj4OTnmK3VpoYNATWziizU3w4HLucKHqjmec"

    icon = inner["content"]["chapters"][0]["tracks"][0]["display"]["icon16x16"]
    assert icon.startswith("https://card-content.yotoplay.com/")
    assert "Expires" not in icon and "Signature" not in icon   # STABLE -> re-POST verbatim
