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
    _ABSENT,
    _extract_media_id,
    CardPlan,
    CardResult,
    FieldEdit,
    apply_change_set,
    apply_format_corrections,
    build_repair_payload,
    canonical_icon,
    canonical_track_url,
    canonicalize_body_media_refs,
    format_edits,
    icon_problems,
    iter_tracks,
    overlay_label_edits,
    plan_card,
    repair_card,
    resolve_targets,
    verify_only_declared_changed,
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
def _mid(card_id, i):
    """A deterministic 43-char base64url-ish mediaId (Yoto requires exactly 43)."""
    return (f"ICONmediaId{card_id}n{i}" + "x" * 43)[:43]


def _icon_url(card_id, i, prefix="POLICY"):
    """A RESOLVED icon URL in the real shape: card-content/<policy>~/<43-char mediaId>."""
    return f"https://card-content.example/{prefix}{card_id}~/{_mid(card_id, i)}"


def _card(card_id="C1", formats=("mp3", "mp3"), with_urls=True, title="Test Card",
          overlay_labels=True):
    """A GET /card body in the UNWRAPPED (inner-card) shape — one track per
    chapter, with icons, keys, durations, sizes, channels: everything the verify
    must preserve. `trackUrl` is the RESOLVED, pre-signed https artifact URL when
    Yoto has served the card (reality), or an unresolved `yoto:#sha` ref when it
    can't be probed (with_urls=False). Icons are RESOLVED card-content URLs (the real
    shape) at BOTH chapter- and track-level, as the live GET /card returns them.

    `overlay_labels` switches the `overlayLabel` field at BOTH levels, because after
    issue #31 both states are fixtures rather than one being "the" card:

      * True  - a card that has been labelled (by this tool, or created after the
        `overlay_label` create-path fix). Its label intent is satisfied, so it is
        `already` for that intent.
      * False - a real card as this app has made them for its whole life, and as all
        ten GET bodies in %LOCALAPPDATA%\\YotoMaker\\repair-backups\\ actually are.
        Its label intent is `planned`, so an all-`opus` card in this state is `apply`,
        NOT `already` - which is blocker 1 (ADR §1.3), the silent no-op this arc fixes.

    The value is the chapter's 1-based ordinal as a STRING, unpadded, matching
    `models.overlay_label` - deliberately NOT the padded `key` beside it.
    """
    chapters = []
    for i, fmt in enumerate(formats, start=1):
        key = f"{i:02d}"
        icon = _icon_url(card_id, i)
        label = {"overlayLabel": str(i)} if overlay_labels else {}
        track = {
            "key": key, **label, "title": f"Track {i}", "type": "audio", "format": fmt,
            "duration": 100 + i, "fileSize": 1000 + i, "channels": "stereo",
            "display": {"icon16x16": icon},
            "trackUrl": (
                f"https://secure-media.example/{card_id}/{i}?Expires=1&Signature=EPHEMERAL{i}#sha256=SHA{i}"
                if with_urls else f"yoto:#SHA{i}"
            ),
        }
        chapters.append({"key": key, **label, "title": f"Track {i}", "tracks": [track],
                         "display": {"icon16x16": icon}})
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


def test_apply_change_set_creates_a_missing_leaf_and_touches_nothing_else():
    """The declared change-set's core promise: exactly the declared paths are set, a
    missing LEAF is created (which is the point - `overlayLabel` is absent on every
    card this app has made), and the input body is never mutated."""
    before = _card("C1", ("mp3", "mp3"), overlay_labels=False)
    expected = copy.deepcopy(before)
    expected["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = "1"
    edits = [FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                       _ABSENT, "1", "overlay-label", "absent -> '1'")]
    out = apply_change_set(before, edits)
    assert out == expected
    assert "overlayLabel" not in before["content"]["chapters"][0]["tracks"][0]  # input untouched


def test_apply_change_set_refuses_to_create_an_intermediate_container():
    """Guessing a container shape is how a corrector silently writes the wrong thing
    into a live card. A path whose parent is absent is a PLANNING bug and must raise.

    BOTH refusal branches of `_descend` are pinned, because they are different code
    and only one of them was in the plan. ⚠ The plan's literal test asserted
    `match="does not exist"` against an EMPTY chapter list - but index 0 of an empty
    list takes the LIST branch, whose message is "out of range", so the plan's own
    test contradicted the plan's own implementation. Pinning one message and calling
    it "refuses to create a container" would have left the other branch unasserted.
    """
    # (a) a missing LIST INDEX - chapter 0 of an empty chapter list
    with pytest.raises(ValueError, match="out of range"):
        apply_change_set({"content": {"chapters": []}},
                         [FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                                    _ABSENT, "1", "overlay-label", "x")])
    # (b) a missing DICT KEY - a chapter that exists but carries no `tracks` container
    with pytest.raises(ValueError, match="does not exist"):
        apply_change_set({"content": {"chapters": [{"key": "01"}]}},
                         [FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                                    _ABSENT, "1", "overlay-label", "x")])


def test_apply_change_set_refuses_two_edits_for_one_path():
    """Two edits for one path would make the POST body depend on list order while the
    verify's expectation depended on it identically - so it would PASS while writing
    something nobody declared twice over."""
    path = ("content", "chapters", 0, "tracks", 0, "format")
    with pytest.raises(ValueError, match="two edits"):
        apply_change_set(_card("C1", ("mp3",)), [
            FieldEdit(path, "mp3", "opus", "format", "a"),
            FieldEdit(path, "mp3", "aac", "format", "b"),
        ])


def test_change_set_addresses_a_still_wrapped_body_at_its_real_path():
    """`_find_chapters` tolerates three shapes; an edit must address the one THIS body
    actually uses, or apply_change_set raises on a body the walker handles fine. This
    is why `_chapters_path` exists rather than a hard-coded ("content","chapters")."""
    wrapped = {"card": {"content": {"chapters": [{"tracks": [{"format": "mp3"}]}]}}}
    out = apply_change_set(wrapped, format_edits(wrapped, {"0.0"}))
    assert out["card"]["content"]["chapters"][0]["tracks"][0]["format"] == "opus"


def test_verify_catches_a_declared_write_the_server_silently_dropped():
    """⚠ THE branch this whole refactor exists for, and the one ADR §1.4 says is most
    likely in the field. Under format-only this case reported `applied` while the fix
    had NOT landed - the silent half of blocker 2. It must now be LOUD."""
    before = _card("C1", ("mp3", "mp3"), overlay_labels=False)
    after = _card("C1", ("opus", "opus"), overlay_labels=False)   # server dropped the label
    edits = format_edits(before, {"0.0", "1.0"}) + [
        FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                  _ABSENT, "1", "overlay-label", "absent -> '1'")]
    problems = verify_only_declared_changed(before, after, edits)
    assert any("overlayLabel" in p and "REMOVED" in p for p in problems)


def test_verify_still_catches_an_undeclared_addition():
    """The `k not in a` branch must stay armed for fields we did NOT declare -
    otherwise the change-set would have bought narrowness by giving up coverage."""
    before = _card("C1", ("mp3",))
    after = copy.deepcopy(before)
    after["content"]["chapters"][0]["tracks"][0]["format"] = "opus"
    after["content"]["chapters"][0]["tracks"][0]["somethingYotoInvented"] = "x"
    problems = verify_only_declared_changed(before, after, format_edits(before, {"0.0"}))
    assert any("somethingYotoInvented" in p and "ADDED" in p for p in problems)


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
    assert all("no resolvable artifact URL" in d.blocked_reason for d in res.plan.blocked)


def test_dry_run_issues_no_post(tmp_path):
    """T3.

    `CardPlan.correct_keys` is RETIRED (ADR §3.2), so this asserts on the declared
    change-set instead. Re-expressed, NOT weakened: it still pins that both tracks
    are to be corrected and that the intent is `format`, which `correct_keys` could
    say only by implication.
    """
    fake = FakeClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=False, backup_dir=tmp_path / "b")
    assert res.outcome == "dry-run"
    fmt = [e for e in res.plan.change_set if e.intent == "format"]
    # path is (..., "chapters", ci, "tracks", ti, "format"), so ci is path[-4].
    assert {e.path[-4] for e in fmt} == {0, 1}            # both chapters' tracks
    assert all(e.path[-1] == "format" and e.new == "opus" for e in fmt)
    assert res.plan.tracks_changed == 2
    assert fake.posts == []


def test_idempotent_already_opus_and_already_labelled_no_post(tmp_path):
    """T4, first half. EVERY declared intent satisfied -> `already`, no POST.

    Split from the original `test_idempotent_already_opus_no_post`, whose premise
    INVERTED: being `opus` is no longer sufficient for `already`. The labelled
    fixture is what makes this half still true.
    """
    fake = FakeClient(_card("C1", ("opus", "opus"), overlay_labels=True))
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "already"
    assert fake.posts == []


def test_already_opus_but_unlabelled_does_apply_and_posts_exactly_once(tmp_path):
    """T4, second half - and this is BLOCKER 1'S REGRESSION GUARD.

    ⚠ This is the test that proves the silent no-op is gone, and it is the single
    most important test in this commit. Before the second decision axis existed,
    `CardPlan.outcome` returned `already` whenever no track needed a FORMAT fix, and
    `repair_card` then returned before the backup and before the POST. So a card
    needing only a label WROTE NOTHING and cheerfully reported
    "already correct - nothing to do".

    That is not hypothetical: on 2026-09-10 all three of the maintainer's live cards
    were already `opus` and all three were unlabelled, so the widened repair would
    have been a silent no-op on exactly the three cards that can test the hypothesis.
    """
    fake = FakeClient(_card("C1", ("opus", "opus"), overlay_labels=False))
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert len(fake.posts) == 1                   # it really wrote, exactly once
    # Zero format edits - the whole change-set is the label intent.
    assert [e.intent for e in res.plan.change_set] == ["overlay-label"] * 4
    posted = fake.posts[0]
    for i, ch in enumerate(posted["content"]["chapters"], start=1):
        assert ch["overlayLabel"] == str(i)
        assert ch["tracks"][0]["overlayLabel"] == str(i)
        assert ch["tracks"][0]["format"] == "opus"          # untouched, already right


def test_no_overlay_labels_flag_turns_the_unproven_half_off(tmp_path):
    """ADR §8 lever 1 - the IN-CODE backout, which is why it ships WITH the intent
    rather than being added later if needed.

    Same unlabelled all-`opus` card as the test above: with the flag it is `already`
    and writes NOTHING; without it, it writes. That pair is the whole lever.
    """
    body = _card("C1", ("opus", "opus"), overlay_labels=False)

    off = FakeClient(body)
    res_off = repair_card(off, "C1", apply=True, backup_dir=tmp_path / "b",
                          overlay_labels=False)
    assert res_off.outcome == "already"
    assert off.posts == []

    on = FakeClient(body)
    res_on = repair_card(on, "C1", apply=True, backup_dir=tmp_path / "b2")
    assert res_on.outcome == "applied"            # default is labels ON
    assert len(on.posts) == 1


def test_the_cli_flag_actually_reaches_repair_card(monkeypatch):
    """⚠ FOUND BY MUTATION, and it is the gap that mattered most in this commit.

    The test above calls `repair_card(..., overlay_labels=False)` DIRECTLY, so it
    proves the parameter works and proves NOTHING about the CLI. Deleting the
    `overlay_labels=not args.no_overlay_labels` threading in `main` left the entire
    suite green: the flag would have parsed, printed in `--help`, and silently done
    nothing.

    That is unacceptable for this flag specifically. `--no-overlay-labels` is ADR §8
    LEVER 1 - the in-code backout for the unproven half of this arc, the thing an
    operator reaches for when a live card has regressed. A backout lever that is
    wired to nothing is worse than no lever, because it reports success.
    """
    from yoto_maker.yoto import repair as repair_mod

    seen: list[bool] = []

    def _record(client, card_id, *, apply, backup_dir, overlay_labels=True, **k):
        seen.append(overlay_labels)
        return CardResult(card_id, card_id, "already", CardPlan(card_id, card_id, []))

    monkeypatch.setattr(repair_mod, "setup_logging", lambda *a, **k: None)
    monkeypatch.setattr(repair_mod, "YotoClient", lambda *a, **k: FakeClient(_card()))
    monkeypatch.setattr(repair_mod, "repair_card", _record)

    repair_mod.main(["--card-id", "C1"])
    assert seen == [True]                       # default: labels ON

    repair_mod.main(["--card-id", "C1", "--no-overlay-labels"])
    assert seen == [True, False]                # the flag is threaded through


def test_a_blocked_tracks_label_edit_is_dropped_not_smuggled(tmp_path):
    """⚠ ALSO FOUND BY MUTATION. The `not by_key[key].blocked_reason` guard in
    `plan_card` was asserted by nothing: removing it left the suite green.

    A blocked card is never written (all-or-nothing), so the consequence is a
    MISREPORTED plan rather than a bad write - the CLI would print `[x]` for a track
    while its decision carried a pending edit, and `change_set` would count a write
    that can never happen. On the one channel that tells an operator what a live
    write did, that is not cosmetic.
    """
    def probe(url):
        return (ArtifactProbe(False, "not Opus", "audio/mpeg") if "EPHEMERAL2" in url
                else ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
    body = _card("C1", ("mp3", "mp3"), overlay_labels=False)
    res = repair_card(FakeClient(body, probe=probe), "C1", apply=True,
                      backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    blocked = [d for d in res.plan.decisions if d.blocked_reason]
    assert len(blocked) == 1
    assert blocked[0].edits == []               # no label edit rode along on it
    assert blocked[0].ref.key == "1.0"


def test_a_second_run_writes_nothing_and_never_overwrites_an_existing_label(tmp_path):
    """Idempotency on live-shaped data, both halves (plan A6).

    Half 1: run `repair_card` twice against a client whose `get_card` returns the
    POSTED body after a write. The second run declares zero edits, reports `already`,
    and `len(posts)` stays at 1.

    Half 2: a pre-existing NON-EMPTY label is never overwritten. This is not only
    idempotency - it stops the tool flip-flopping against ANOTHER editor. A user who
    types "Chapter 1" in the Yoto app would otherwise have it reset to "1" on every
    run, forever.
    """
    fake = FakeClient(_card("C1", ("mp3", "mp3"), overlay_labels=False))
    first = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert first.outcome == "applied"
    assert len(fake.posts) == 1

    second = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert second.outcome == "already"
    assert second.plan.change_set == []
    assert len(fake.posts) == 1                   # the second run wrote NOTHING

    # Half 2: a human-authored label survives untouched.
    hand = _card("C1", ("opus", "opus"), overlay_labels=False)
    hand["content"]["chapters"][0]["overlayLabel"] = "Chapter 1"
    hand["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = "Chapter 1"
    keeper = FakeClient(hand)
    res = repair_card(keeper, "C1", apply=True, backup_dir=tmp_path / "b3")
    # Chapter 2 is still unlabelled, so the card DOES write - which is what makes
    # this a real test that chapter 1 is left alone rather than a no-op.
    assert res.outcome == "applied"
    posted = keeper.posts[0]
    assert posted["content"]["chapters"][0]["overlayLabel"] == "Chapter 1"
    assert posted["content"]["chapters"][0]["tracks"][0]["overlayLabel"] == "Chapter 1"
    assert posted["content"]["chapters"][1]["overlayLabel"] == "2"
    assert any("left alone" in n for d in res.plan.decisions for n in d.notes)


def test_an_empty_or_whitespace_label_is_treated_as_absent(tmp_path):
    """`_is_set`: absent, None, "" and "   " all mean the field needs writing. Only a
    non-empty string is a label a human could have meant."""
    for placeholder in ("", "   ", None):
        body = _card("C1", ("opus",), overlay_labels=False)
        body["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = placeholder
        fake = FakeClient(body)
        res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / f"b{placeholder!r}")
        assert res.outcome == "applied", placeholder
        assert fake.posts[0]["content"]["chapters"][0]["tracks"][0]["overlayLabel"] == "1"


def test_a_multi_track_chapter_declines_both_levels_and_keeps_the_format_fix(tmp_path):
    """⚠ `declined` must NEVER cost a card the PROVEN fix (plan A8, ADR §3.2).

    An unprobeable artifact is a correctness hazard and blocks the card; a label we
    cannot confidently number is not, and must not. Without `declined`, an
    unusually-shaped card would lose access to the proven format fix because of the
    unproven label one - the exact inversion this row exists to prevent.

    BOTH levels are declined, not just the tracks: writing the chapter label alone
    would leave the schema-REQUIRED track field missing while making a later run's
    idempotency check see a labelled chapter and skip it - a partial job that
    permanently hides itself.
    """
    body = _card("C1", ("mp3",), overlay_labels=False)
    chapter = body["content"]["chapters"][0]
    second = copy.deepcopy(chapter["tracks"][0])
    second["trackUrl"] = (
        "https://secure-media.example/C1/2?Expires=1&Signature=EPHEMERAL2#sha256=SHA2")
    chapter["tracks"].append(second)               # now a 2-track chapter

    fake = FakeClient(body)
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"                 # NOT blocked
    assert len(fake.posts) == 1
    # The format fix landed on both tracks...
    posted = fake.posts[0]
    assert [t["format"] for t in posted["content"]["chapters"][0]["tracks"]] == ["opus", "opus"]
    # ...and NOT ONE overlayLabel was written, at either level.
    assert "overlayLabel" not in posted["content"]["chapters"][0]
    assert all("overlayLabel" not in t for t in posted["content"]["chapters"][0]["tracks"])
    assert [e.intent for e in res.plan.change_set] == ["format", "format"]
    assert any("numbering convention unknown" in n for d in res.plan.decisions for n in d.notes)


def test_label_edits_use_the_same_raw_track_indices_as_iter_tracks():
    """⚠ PRE-MERGE REVIEW MEDIUM #1. `iter_tracks` and `format_edits` walk the
    UNFILTERED `tracks` list and skip non-dict entries while KEEPING their raw index,
    so a raw index is what every positional "ci.ti" key in this module means.

    `overlay_label_edits` originally filtered the list and re-enumerated the
    survivors, which RENUMBERS them. On `tracks=[None, {...}]` it addressed
    `tracks[0]` - the `None` - for what is really `tracks[1]`; `plan_card` decoded
    that as key "0.0", failed to find it in `by_key` (which holds "0.1"), and
    SILENTLY DROPPED the edit. The schema-required label went unwritten with nothing
    in the report to say why.
    """
    body = {"cardId": "C1", "title": "T", "content": {"chapters": [
        {"key": "01", "tracks": [None, {"key": "01", "title": "Real", "format": "opus",
                                        "trackUrl": "yoto:#SHA1"}]}]}}
    from yoto_maker.yoto.repair import _key_of_track_path

    assert [r.key for r in iter_tracks(body)] == ["0.1"]     # the walker says index 1
    edits, _notes = overlay_label_edits(body)
    track_edits = [e for e in edits if _key_of_track_path(e.path) is not None]
    assert len(track_edits) == 1
    assert _key_of_track_path(track_edits[0].path) == "0.1"  # and so must the edit
    assert track_edits[0].path == ("content", "chapters", 0, "tracks", 1, "overlayLabel")

    # End to end: the edit must SURVIVE plan_card rather than be dropped as unmatched.
    plan = plan_card(FakeClient(body), body, "C1")
    assert plan.blocked == []
    assert [e.path for e in plan.change_set if _key_of_track_path(e.path)] == [
        ("content", "chapters", 0, "tracks", 1, "overlayLabel")]


def test_a_track_less_chapter_is_declined_so_outcome_empty_loses_nothing(tmp_path):
    """⚠ PRE-MERGE REVIEW MEDIUM #2, and it is blocker 1's shape a second time.

    `CardPlan.outcome` checks `empty` (no decisions) BEFORE `change_set`. A card whose
    every chapter is track-less produces no decisions, so if the label intent still
    declared chapter-level edits for those chapters, the plan would carry pending
    writes and `outcome` would report `empty` - "no tracks found, nothing to do" -
    throwing them away silently. Exactly the silent no-op the second decision axis
    exists to abolish.

    Fixed at the source rather than by reordering `outcome`: a chapter with no tracks
    has nothing that can carry the schema-REQUIRED track-level label, so labelling the
    chapter alone is the same partial-job-that-hides-itself the multi-track case is
    declined for. Reordering `outcome` instead would have made the tool WRITE to a body
    it had just reported it could not parse.
    """
    body = {"cardId": "C1", "title": "T", "content": {"chapters": [
        {"key": "01", "title": "Ch1", "tracks": []},
        {"key": "02", "title": "Ch2", "tracks": []}]}}
    edits, notes = overlay_label_edits(body)
    assert edits == []                                   # nothing declared...
    assert all("declined" in n for ns in notes.values() for n in ns)   # ...and it SAYS so

    fake = FakeClient(body)
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "empty"
    assert res.plan.change_set == []                     # nothing pending to lose
    assert fake.posts == []

    # A track-less chapter ALONGSIDE a real one: the real one is still labelled.
    mixed = _card("C1", ("opus",), overlay_labels=False)
    mixed["content"]["chapters"].append({"key": "02", "title": "Empty", "tracks": [],
                                         "display": mixed["content"]["chapters"][0]["display"]})
    fake2 = FakeClient(mixed)
    res2 = repair_card(fake2, "C1", apply=True, backup_dir=tmp_path / "b2")
    assert res2.outcome == "applied"
    posted = fake2.posts[0]
    assert posted["content"]["chapters"][0]["overlayLabel"] == "1"
    assert posted["content"]["chapters"][0]["tracks"][0]["overlayLabel"] == "1"
    assert "overlayLabel" not in posted["content"]["chapters"][1]      # declined


def test_the_create_path_and_the_repair_path_agree_by_round_trip(tmp_path):
    """⚠ THE agreement test (plan A5, ADR §4.1 REQUIRED) — and it has TWO halves,
    because the obvious one-half version CANNOT FAIL.

    ⚠ THE TRAP, recorded because the first draft of this test fell into it and a
    review caught it. Feeding a create-path body straight to `overlay_label_edits`
    and asserting `== []` proves NOTHING about agreement: the create path always
    writes a non-empty label, so `_is_set` is true at every position and the helper
    returns via its "already - left alone" branch WITHOUT EVER COMPUTING `expected`.
    Verified by mutation: making the repair side zero-pad (`f"{ci+1:02d}"`, the exact
    padding disagreement this test names in its own docstring) left that assertion
    GREEN. An off-by-one and a chapter/track nesting swap were equally invisible,
    for the same reason.

    So:

      * HALF 1 (idempotency at N = 12) - a create-path body satisfies the label
        intent, so zero edits and `already`. Worth keeping; just not "agreement".
      * HALF 2 (the real agreement) - STRIP every label, forcing the repair path to
        COMPUTE each one, then require the recomputed value at every position to
        equal what the create path actually wrote there. Compared as whole dicts
        keyed by FieldEdit path, so it catches an off-by-one in EITHER direction, a
        padding disagreement, and a chapter/track nesting swap - none of which two
        literal value assertions would catch.

    N = 12 is the point: N > 9 is where padded and unpadded diverge, and half 2 is
    the only place in the suite that drives the repair side's own computation past 9.
    """
    from yoto_maker.yoto.models import TrackMeta, build_content_payload

    # fmt="opus" deliberately. ⚠ With the default "mp3" these tracks would each BLOCK
    # (a `yoto:#sha` trackUrl is not probeable), and `plan_card` DROPS a label edit
    # belonging to a blocked track - so the change-set assertion below would have
    # passed for the wrong reason and could never have failed. Making every track
    # already-`opus` keeps the format intent quiet and leaves the label intent as the
    # only thing under test.
    payload = build_content_payload("Twelve", [
        TrackMeta(f"Track {i}", f"sha{i}", 10.0, 100, fmt="opus") for i in range(1, 13)])
    # Shape it as a GET /card body: the create path's chapters, with a cardId.
    body = {"cardId": "C1", "title": "Twelve", "content": payload["content"]}
    assert len(body["content"]["chapters"]) == 12

    # ---- HALF 1: the create path already satisfies the intent (idempotency, N=12).
    label_edits, _notes = overlay_label_edits(body)
    assert label_edits == [], f"create and repair disagree: {[e.path for e in label_edits]}"

    plan = plan_card(FakeClient(body), body, "C1")
    assert plan.blocked == [], [d.blocked_reason for d in plan.blocked]   # not vacuous
    assert plan.outcome == "already"
    assert plan.change_set == []

    # ---- HALF 2: what the CREATE path wrote, keyed by the path a FieldEdit would use.
    created: dict[tuple, str] = {}
    for ci, ch in enumerate(body["content"]["chapters"]):
        created[("content", "chapters", ci, "overlayLabel")] = ch["overlayLabel"]
        for ti, tr in enumerate(ch["tracks"]):
            created[("content", "chapters", ci, "tracks", ti, "overlayLabel")] = tr["overlayLabel"]
    assert len(created) == 24                      # 12 chapters + 12 tracks

    # Strip them, so the REPAIR path must compute every value itself.
    stripped = copy.deepcopy(body)
    for ch in stripped["content"]["chapters"]:
        del ch["overlayLabel"]
        for tr in ch["tracks"]:
            del tr["overlayLabel"]

    recomputed_edits, _ = overlay_label_edits(stripped)
    recomputed = {e.path: e.new for e in recomputed_edits}
    assert recomputed == created, (
        "the create path and the repair path compute different labels: "
        f"{ {k: (created[k], recomputed.get(k)) for k in created if created.get(k) != recomputed.get(k)} }")

    # And the double-digit end specifically, spelled out so a failure reads clearly.
    assert created[("content", "chapters", 11, "overlayLabel")] == "12"
    assert body["content"]["chapters"][11]["key"] == "12"     # padded key, unpadded label


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
    # Rotate the pre-signed trackUrl signature AND the icon <policy>~ prefix — the
    # sha / mediaId are stable, exactly as the real CDN URLs behave across a re-GET.
    for i, ch in enumerate(after["content"]["chapters"], start=1):
        tr = ch["tracks"][0]
        tr["trackUrl"] = f"https://secure-media.example/C1/{i}?Expires=999&Signature=ROTATED{i}#sha256=SHA{i}"
        rotated_icon = _icon_url("C1", i, prefix="ROTATEDPOLICY")     # same mediaId, new prefix
        ch["display"]["icon16x16"] = rotated_icon
        tr["display"]["icon16x16"] = rotated_icon
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
def test_report_strings_describe_changes_not_formats(tmp_path, capsys):
    """⚠ Assert on what the new strings CONTAIN, never on what they lack. A negative
    guard goes vacuous the moment the thing it negates is deleted, and still passes -
    item 20's `"100 MB" not in msg` did exactly that, in this same repo.

    `already` here means EVERY DECLARED INTENT is satisfied, not "every track is
    opus". A card that is already opus but unlabelled must NOT print `already`: the
    old string would have said "already correct (all 2 track(s) 'opus')" AND THEN
    WRITTEN, a report that contradicts itself.
    """
    from yoto_maker.yoto.repair import _print_card_result

    labelled = _card("C1", ("opus", "opus"), overlay_labels=True)
    res = repair_card(FakeClient(labelled), "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "already"
    _print_card_result(res)
    out = capsys.readouterr().out
    assert "already correct (2 track(s), nothing to change)" in out

    unlabelled = _card("C1", ("opus", "opus"), overlay_labels=False)
    res = repair_card(FakeClient(unlabelled), "C1", apply=False, backup_dir=tmp_path / "b")
    assert res.outcome == "dry-run"
    _print_card_result(res)
    out = capsys.readouterr().out
    # 2 chapter labels + 2 track labels = 4 changes across 2 tracks.
    assert "WOULD make 4 change(s) across 2 track(s)" in out

    mp3 = _card("C1", ("mp3", "mp3"), overlay_labels=False)
    res = repair_card(FakeClient(mp3), "C1", apply=True, backup_dir=tmp_path / "b4")
    assert res.outcome == "applied"
    _print_card_result(res)
    out = capsys.readouterr().out
    # 2 format + 2 chapter labels + 2 track labels = 6.
    assert "made 6 change(s); POST ok; verify ok" in out


def test_a_blocked_track_prints_its_reason_and_a_changed_one_prints_its_notes(tmp_path, capsys):
    """The per-track mark and detail now come from the decision's own state
    (`blocked_reason` / `edits` / `notes`) rather than a `status` string. Pin all
    three marks, because this is the operator's only window into a tool that mutates
    live cards."""
    from yoto_maker.yoto.repair import _print_card_result

    def probe(url):
        return (ArtifactProbe(False, "Content-Type audio/mpeg - not Opus", "audio/mpeg")
                if "EPHEMERAL2" in url else ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
    res = repair_card(FakeClient(_card("C1", ("mp3", "mp3")), probe=probe), "C1",
                      apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "blocked"
    _print_card_result(res)
    out = capsys.readouterr().out
    assert '[>] track 0.0' in out                       # an edit is planned
    assert '[x] track 1.0' in out                       # blocked
    assert "not confirmed Opus" in out                  # the blocked_reason is printed

    res = repair_card(FakeClient(_card("C1", ("opus",), overlay_labels=True)), "C1",
                      apply=False, backup_dir=tmp_path / "b2")
    _print_card_result(res)
    out = capsys.readouterr().out
    assert "[=] track 0.0" in out                       # nothing to change
    assert "already: 'opus'" in out


def test_a_declined_chapter_note_is_printed(tmp_path, capsys):
    """A `declined` label on a multi-track chapter must be VISIBLE. It is the one
    note an operator could otherwise mistake for 'the label was written'."""
    from yoto_maker.yoto.repair import _print_card_result

    body = _card("C1", ("mp3",), overlay_labels=False)
    chapter = body["content"]["chapters"][0]
    second = copy.deepcopy(chapter["tracks"][0])
    second["trackUrl"] = (
        "https://secure-media.example/C1/2?Expires=1&Signature=EPHEMERAL2#sha256=SHA2")
    chapter["tracks"].append(second)

    res = repair_card(FakeClient(body), "C1", apply=False, backup_dir=tmp_path / "b")
    _print_card_result(res)
    out = capsys.readouterr().out
    assert "declined" in out and "numbering convention unknown" in out


def test_the_real_fixture_is_unlabelled_and_the_repair_path_declares_both_levels():
    """The real GET /card/gzP2B body has NO `overlayLabel` anywhere - which is the
    bug, observed on real data rather than asserted from a fixture we invented.

    The labelled SIBLING is built here by deep-copying the real body and adding the
    labels, rather than committing a second large JSON file: a duplicated real body
    is a drift hazard, and the point is that the two states differ by exactly this
    field. The original stays untouched, so the fixture-pinning test above keeps
    pointing at a genuinely unlabelled card.
    """
    inner = json.loads(FIXTURE.read_text(encoding="utf-8"))["card"]
    assert "overlayLabel" not in json.dumps(inner)        # the bug, on real data

    edits, notes = overlay_label_edits(inner)
    assert [e.path[-1] for e in edits] == ["overlayLabel", "overlayLabel"]
    assert [e.new for e in edits] == ["1", "1"]           # chapter and its one track
    assert [e.old for e in edits] == [_ABSENT, _ABSENT]
    assert all(e.intent == "overlay-label" for e in edits)
    # chapter-level first, then the track - and both at the body's REAL path
    assert edits[0].path == ("content", "chapters", 0, "overlayLabel")
    assert edits[1].path == ("content", "chapters", 0, "tracks", 0, "overlayLabel")
    assert any("planned" in n for ns in notes.values() for n in ns)

    # The labelled sibling: the same real body after this tool has run on it.
    labelled = apply_change_set(inner, edits)
    assert overlay_label_edits(labelled) == ([], {
        "c0": ["already: chapter overlayLabel '1' - left alone"],
        "0.0": ["already: overlayLabel '1' - left alone"],
    })


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


def test_rollback_posts_canonical_refs_not_resolved_urls(tmp_path):
    """The rollback POST must canonicalize BOTH trackUrls and icons (the backup holds
    resolved URLs POST /content rejects) so a restore never re-POSTs a resolved ref."""
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
    dumped = json.dumps(posted)
    assert "secure-media" not in dumped                 # no resolved audio URL restored
    assert "card-content" not in dumped                 # no resolved icon URL restored
    for ch in posted["content"]["chapters"]:
        assert ch["display"]["icon16x16"].startswith("yoto:#")
        assert ch["tracks"][0]["display"]["icon16x16"].startswith("yoto:#")


def test_rollback_tolerates_a_residual_overlay_label_as_explanation_not_failure(tmp_path):
    """ADR §3.5. A backup PREDATES `overlayLabel`, so restoring one POSTs a body
    without the field - correct and deliberate: a rollback that preserved an unproven
    field we had just added would not be a rollback.

    But if `POST /content` MERGES rather than REPLACES, `after` still carries the
    label the backup lacks, `_diff_paths` emits `unexpectedly ADDED`, and the restore
    would report `verify-failed` ON A CARD THAT IS IN FACT FINE - turning a recovery
    action into a false alarm at the worst possible moment.
    """
    original = _card("C1", ("mp3", "mp3"), overlay_labels=False)   # a real pre-label backup
    backup = tmp_path / "C1-backup.json"
    backup.write_text(json.dumps(original), encoding="utf-8")
    # The server MERGED: it kept the label we had written, which the backup lacks.
    merged = _card("C1", ("mp3", "mp3"), overlay_labels=True)
    fake = FakeClient(original, after=merged)
    from yoto_maker.yoto.repair import rollback_from_backup

    res = rollback_from_backup(fake, backup)

    assert res.outcome == "restored"                  # NOT verify-failed
    assert any("still carries overlayLabel" in p for p in res.problems)   # explained
    assert any("Everything else is restored" in p for p in res.problems)


def test_rollback_still_fails_on_a_changed_overlay_label_value(tmp_path):
    """The tolerance is PRESENCE-only and one-directional. A label whose VALUE the
    server changed is a real difference and must still fail - otherwise the tolerance
    would be the `_VOLATILE_TOP_KEYS` blind spot by another name."""
    original = _card("C1", ("mp3", "mp3"), overlay_labels=True)
    backup = tmp_path / "C1-backup.json"
    backup.write_text(json.dumps(original), encoding="utf-8")
    changed = _card("C1", ("mp3", "mp3"), overlay_labels=True)
    changed["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = "99"
    fake = FakeClient(original, after=changed)
    from yoto_maker.yoto.repair import rollback_from_backup

    res = rollback_from_backup(fake, backup)

    assert res.outcome == "verify-failed"
    assert any("overlayLabel" in p and "99" in p for p in res.problems)


def test_rollback_tolerance_does_not_leak_into_the_repair_verify():
    """⚠ The structural difference from the `_VOLATILE_TOP_KEYS` trap: the tolerance
    lives ONLY in the rollback path. The repair path's verify must still fail loudly
    on an UNDECLARED `overlayLabel` the server invented, because that is a field
    appearing on a live card that nobody asked for."""
    before = _card("C1", ("mp3",), overlay_labels=False)
    after = _card("C1", ("opus",), overlay_labels=False)
    after["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = "7"   # undeclared
    problems = verify_only_declared_changed(before, after, format_edits(before, {"0.0"}))
    assert any("overlayLabel" in p and "ADDED" in p for p in problems)


def test_canonicalize_body_media_refs_rewrites_tracks_and_icons():
    """The rollback helper canonicalizes BOTH trackUrls and icons, best-effort."""
    out = canonicalize_body_media_refs(_card("C1", ("mp3", "mp3")))
    dumped = json.dumps(out)
    assert "secure-media" not in dumped and "card-content" not in dumped
    for i, ch in enumerate(out["content"]["chapters"], start=1):
        assert ch["tracks"][0]["trackUrl"] == f"yoto:#SHA{i}"
        assert ch["display"]["icon16x16"] == f"yoto:#{_mid('C1', i)}"
        assert ch["tracks"][0]["display"]["icon16x16"] == f"yoto:#{_mid('C1', i)}"


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
    assert any("sha" in d.blocked_reason.lower() for d in res.plan.blocked)


def test_post_body_uses_canonical_refs_not_resolved_urls(tmp_path):
    """THE core assertion: the body handed to update_card contains yoto:#<...> for
    every trackUrl AND every icon16x16, and NO resolved host of either kind."""
    fake = FakeClient(_card("C1", ("mp3", "mp3")))

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert len(fake.posts) == 1
    posted = fake.posts[0]
    urls = [ch["tracks"][0]["trackUrl"] for ch in posted["content"]["chapters"]]
    assert urls == ["yoto:#SHA1", "yoto:#SHA2"]
    dumped = json.dumps(posted)
    assert "secure-media" not in dumped                 # the audio host is gone
    assert "card-content" not in dumped                 # the icon host is gone too
    assert "EPHEMERAL" not in dumped                    # so is the ephemeral signature
    assert "Expires=" not in dumped
    # every icon (chapter- AND track-level) is now a canonical yoto:# ref
    for ch in posted["content"]["chapters"]:
        assert ch["display"]["icon16x16"].startswith("yoto:#")
        assert ch["tracks"][0]["display"]["icon16x16"].startswith("yoto:#")


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


# --------------------------------------------------------------------------- #
# Icon canonicalization (live-run finding): POST /content REQUIRES every
# display.icon16x16 to be canonical yoto:#<mediaId> (43 chars) - signed OR not.
# --------------------------------------------------------------------------- #
def test_extract_media_id_from_resolved_icon_url():
    mid = "xV2a9v63mNcsYy5QYsBhlmK5MXgoM5Fuk8ed4nQqcUg"     # 43 chars, base64url-ish
    assert len(mid) == 43
    assert _extract_media_id(f"https://card-content.yotoplay.com/POLICYtoken~/{mid}") == mid


def test_extract_media_id_rejects_wrong_length():
    """Yoto requires EXACTLY 43 chars; a non-43-char segment isn't a mediaId."""
    assert _extract_media_id("https://card-content.example/P~/tooShort") is None
    assert _extract_media_id("https://card-content.example/no-tilde-segment") is None


def test_canonical_icon_canonicalizes_resolved_and_leaves_canonical():
    mid = "xV2a9v63mNcsYy5QYsBhlmK5MXgoM5Fuk8ed4nQqcUg"
    canon, err = canonical_icon(f"https://card-content.example/P~/{mid}")
    assert err is None and canon == f"yoto:#{mid}"
    # already-canonical yoto:#<mediaId> is left untouched
    assert canonical_icon(f"yoto:#{mid}") == (f"yoto:#{mid}", None)
    # no icon to rewrite -> (None, None); unextractable -> error
    assert canonical_icon(None) == (None, None)
    assert canonical_icon("https://card-content.example/P~/short")[1]


def test_icons_canonicalized_in_post_body(tmp_path):
    """Icons are canonicalized to yoto:#<mediaId>, at BOTH chapter- and track-level
    (not left verbatim) — the live 400 was on both display paths."""
    fake = FakeClient(_card("C1", ("mp3", "mp3")))

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    posted = fake.posts[0]
    for i, ch in enumerate(posted["content"]["chapters"], start=1):
        expected = f"yoto:#{_mid('C1', i)}"
        assert ch["display"]["icon16x16"] == expected
        assert ch["tracks"][0]["display"]["icon16x16"] == expected


def test_unextractable_icon_blocks_whole_card_no_post(tmp_path):
    """An icon URL with no extractable 43-char mediaId blocks the ENTIRE card
    (all-or-nothing) — never POST an icon Yoto will 400 on."""
    body = _card("C1", ("mp3", "mp3"))
    body["content"]["chapters"][0]["tracks"][0]["display"]["icon16x16"] = (
        "https://card-content.example/POLICY~/notA43CharMediaId")     # wrong length
    fake = FakeClient(body)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []
    assert any("mediaid" in p.lower() or "icon" in p.lower() for p in res.problems)


def test_icon_problems_flags_only_unextractable():
    """icon_problems() is empty for a fully-resolvable card and flags an unextractable
    icon (both chapter- and track-level are inspected)."""
    assert icon_problems(_card("C1", ("mp3", "mp3"))) == []
    bad = _card("C1", ("mp3", "mp3"))
    bad["content"]["chapters"][0]["display"]["icon16x16"] = "https://card-content.example/P~/short"
    problems = icon_problems(bad)
    assert len(problems) == 1 and "chapter 0" in problems[0]


def _real_shaped_card(formats, *, prefix, sig, overlay_labels=True):
    """A card whose URLs use the REAL '<policy>~/<key>' shape (trackUrl also carries a
    '#sha256=<key>' fragment), so a test can rotate the policy prefix AND the signature
    (as a real re-GET does). mediaId is a real 43-char token.

    ⚠ `overlay_labels` defaults True and that is LOAD-BEARING, though neither the plan
    nor the ADR's breaks-by-design table mentions this helper at all. Leaving it
    unlabelled would make `intended` (= before + the declared label edits) differ from
    an unlabelled `after` on EVERY round trip, so the two
    `test_verify_fails_when_*_changes` tests below would have gone on passing because
    of a MISSING LABEL rather than because of the sha / mediaId change they claim to
    test - green, and no longer testing their own subject.
    """
    chapters = []
    for i, fmt in enumerate(formats, start=1):
        sha = f"AUDIOsha{i}base64token"
        mid = _mid("RS", i)                                # 43-char mediaId
        icon = f"https://card-content.example/{prefix}~/{mid}"
        label = {"overlayLabel": str(i)} if overlay_labels else {}
        track = {
            "key": f"{i:02d}", **label, "title": f"Track {i}", "type": "audio", "format": fmt,
            "duration": 100 + i, "fileSize": 1000 + i, "channels": "stereo",
            "display": {"icon16x16": icon},
            "trackUrl": (f"https://secure-media.example/{prefix}~/{sha}?"
                         f"Expires=9&Signature={sig}&Key-Pair-Id=K#sha256={sha}"),
        }
        chapters.append({"key": f"{i:02d}", **label, "title": f"Track {i}", "tracks": [track],
                         "display": {"icon16x16": icon}})
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


def test_verify_fails_when_an_icon_mediaid_changes(tmp_path):
    """Parity with the trackUrl case: a re-GET whose icon points at a DIFFERENT
    mediaId is caught even though the <policy>~ prefix also rotated."""
    before = _real_shaped_card(("mp3", "mp3"), prefix="POLICYA", sig="SIGA")
    after = _real_shaped_card(("opus", "opus"), prefix="POLICYB", sig="SIGB")
    other_mid = ("COMPLETELYdifferentMediaId" + "z" * 43)[:43]
    after["content"]["chapters"][0]["tracks"][0]["display"]["icon16x16"] = (
        f"https://card-content.example/POLICYB~/{other_mid}")
    fake = FakeClient(before, after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "verify-failed"
    assert any("icon16x16" in p.lower() for p in res.problems)


def test_card_level_icon_problem_reports_blocked_not_empty(tmp_path):
    """A card the walker finds no tracks on but with an un-canonicalizable chapter
    icon reports 'blocked' (with the reason), never a silent 'empty'."""
    body = {"cardId": "C1", "title": "Weird",
            "content": {"chapters": [
                {"key": "01", "display": {"icon16x16": "https://card-content.example/P~/short"},
                 "tracks": []}]}}
    fake = FakeClient(body)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []
    assert any("icon" in p.lower() for p in res.problems)


def test_real_fixture_canonicalizes_track_and_icon():
    """Against the sanitized REAL GET /card/gzP2B body: the resolved trackUrl
    canonicalizes to yoto:#<sha>, and the resolved icon (chapter- AND track-level)
    canonicalizes to yoto:#<43-char mediaId> — the form POST /content requires."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    inner = raw["card"]
    refs = iter_tracks(inner)
    assert len(refs) == 1
    canon, err = canonical_track_url(refs[0].track_url_raw)
    assert err is None
    assert canon == "yoto:#44aJeE5Xj4OTnmK3VpoYNATWziizU3w4HLucKHqjmec"

    expected_icon = "yoto:#xV2a9v63mNcsYy5QYsBhlmK5MXgoM5Fuk8ed4nQqcUg"
    chapter = inner["content"]["chapters"][0]
    mid = _extract_media_id(chapter["tracks"][0]["display"]["icon16x16"])
    assert mid == "xV2a9v63mNcsYy5QYsBhlmK5MXgoM5Fuk8ed4nQqcUg" and len(mid) == 43
    assert canonical_icon(chapter["tracks"][0]["display"]["icon16x16"]) == (expected_icon, None)
    assert canonical_icon(chapter["display"]["icon16x16"]) == (expected_icon, None)
    assert icon_problems(inner) == []      # the real card is fully resolvable

    # end-to-end: the POST body built from the real fixture carries ONLY yoto:# refs
    posted = build_repair_payload(inner, format_edits(inner, {"0.0"}), {"0.0": canon})
    dumped = json.dumps(posted)
    assert "card-content.yotoplay.com" not in dumped
    assert "secure-media.yotoplay.com" not in dumped
    assert posted["content"]["chapters"][0]["display"]["icon16x16"] == expected_icon
    assert posted["content"]["chapters"][0]["tracks"][0]["display"]["icon16x16"] == expected_icon
