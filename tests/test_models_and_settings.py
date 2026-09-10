"""Pure-logic tests: content payload builder + settings store."""
from __future__ import annotations

from yoto_maker.settings import get_settings
from yoto_maker.yoto.models import TrackMeta, build_content_payload


def test_build_content_payload_basic():
    metas = [
        TrackMeta("Intro", "sha1", 30.4, 1000, icon_ref="yoto:#i1"),
        TrackMeta("Story", "sha2", 600.6, 2000),
    ]
    p = build_content_payload("My Card", metas)
    assert p["title"] == "My Card"
    chapters = p["content"]["chapters"]
    assert len(chapters) == 2
    # keys are zero-padded and sequential
    assert [c["key"] for c in chapters] == ["01", "02"]
    # track url references the transcoded sha
    assert chapters[0]["tracks"][0]["trackUrl"] == "yoto:#sha1"
    # duration is rounded
    assert chapters[0]["tracks"][0]["duration"] == 30
    # icon only where provided
    assert chapters[0]["display"]["icon16x16"] == "yoto:#i1"
    assert "display" not in chapters[1]
    # `overlayLabel` is present at both levels regardless of whether an icon is
    # (issue #31) - the two are independent, which is why the line above still holds.
    assert chapters[1]["overlayLabel"] == "2"
    assert chapters[1]["tracks"][0]["overlayLabel"] == "2"
    assert [c["key"] for c in chapters] == ["01", "02"]      # padded, unchanged
    # aggregate metadata sums durations/sizes
    assert p["metadata"]["media"]["duration"] == 631
    assert p["metadata"]["media"]["fileSize"] == 3000


def test_build_content_payload_empty():
    p = build_content_payload("Empty", [])
    assert p["content"]["chapters"] == []
    assert p["metadata"]["media"]["duration"] == 0


def test_build_content_payload_pins_one_full_chapter_and_track_exactly():
    """EXACT equality on a whole chapter and its whole track. Every key spelled out.

    WHY THIS TEST EXISTS, and why it must stay an `==` and never soften into `in`
    checks: `overlayLabel` is REQUIRED by Yoto's published track schema, and this
    app never sent it for the entire life of the project - the player's knob brought
    up no chapter list on any card it ever made (issue #31). Nothing caught it,
    because every other assertion in the suite indexes into keys it already expects
    to be there, and a missing key is invisible to that.

    The two near-misses, so nobody thinks this duplicates them. `test_repair.py`'s
    `test_corrector_sets_only_format_everything_else_byte_identical` does compare a
    whole card body, but against a deepcopy of its OWN INPUT plus one known delta -
    it pins the corrector's narrowness and is structurally blind to a field its
    fixture never had. `test_get_card_unwraps_card_envelope` is an absolute equality,
    but against an EMPTY chapter list. This is the suite's only absolute equality
    against a POPULATED chapter and track.

    Consequence, deliberately: any future field added to or removed from the
    create-path payload must be STATED here. A payload change that cannot be stated
    here is a payload change nobody reviewed.
    """
    p = build_content_payload("My Card", [
        TrackMeta("Intro", "sha1", 30.4, 1000, icon_ref="yoto:#i1"),
    ])
    assert p["content"]["chapters"][0] == {
        "key": "01",
        "overlayLabel": "1",
        "title": "Intro",
        "display": {"icon16x16": "yoto:#i1"},
        "tracks": [
            {
                "key": "01",
                "overlayLabel": "1",
                "title": "Intro",
                "trackUrl": "yoto:#sha1",
                "type": "audio",
                "format": "mp3",
                "duration": 30,
                "fileSize": 1000,
                "channels": "stereo",
                "display": {"icon16x16": "yoto:#i1"},
            }
        ],
    }


def test_build_content_payload_pins_the_top_level_shape():
    """No test pinned the POST body's TOP-LEVEL keys either - `test_yoto_client.py`
    and the test above both index into `["content"]["chapters"]` - so a create-path
    change could add or drop a top-level key and ship green.

    `content` carries `chapters` and nothing else. Yoto ADDS `playbackType`,
    `version`, `activity`, `availability`, `cover` and `config` server-side (ADR
    2026-09-10 §1.4, measured against the real gzP2B body); we must not start
    sending them.
    """
    p = build_content_payload("My Card", [TrackMeta("Intro", "sha1", 30.4, 1000)])
    assert set(p) == {"title", "content", "metadata"}
    assert set(p["content"]) == {"chapters"}
    assert set(p["metadata"]) == {"media"}
    assert set(p["metadata"]["media"]) == {"duration", "fileSize"}


def test_overlay_label_is_one_based_and_unpadded():
    """Pin the VALUE as well as the plumbing. A shared helper stops the create and
    repair paths disagreeing; it does not stop both being wrong. N > 9 is the case
    that distinguishes unpadded from padded."""
    from yoto_maker.yoto.models import overlay_label
    assert overlay_label(1) == "1"
    assert overlay_label(9) == "9"
    assert overlay_label(10) == "10"
    assert overlay_label(18) == "18"


def test_client_id_resolution_order(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.settings import get_settings

    # 1. With no env and no saved setting, the baked-in default is used.
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    assert cfg.resolve_client_id() == "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"

    # 2. A saved setting overrides the baked-in default.
    get_settings().set("yoto_client_id", "from_setting")
    assert cfg.resolve_client_id() == "from_setting"

    # 3. The env var overrides everything.
    monkeypatch.setenv("YOTO_CLIENT_ID", "from_env")
    assert cfg.resolve_client_id() == "from_env"


def test_settings_roundtrip(temp_config):
    s = get_settings()
    assert s.get("ai_model") == "gpt-image-1"  # default
    assert s.get("missing") is None
    s.set("ai_api_key", "secret")
    assert s.get("ai_api_key") == "secret"
    # persisted to the temp data dir
    assert temp_config.settings_path.exists()


def test_settings_delete_removes_saved_key(temp_config):
    s = get_settings()
    s.set("yoto_client_id", "mine")
    assert s.get("yoto_client_id") == "mine"

    assert s.delete("yoto_client_id") is True
    assert s.get("yoto_client_id") is None

    # Deleting again is a no-op, not an error.
    assert s.delete("yoto_client_id") is False


def test_settings_delete_leaves_other_keys_alone(temp_config):
    s = get_settings()
    s.set("yoto_client_id", "mine")
    s.set("ai_api_key", "secret")
    s.delete("yoto_client_id")
    assert s.get("ai_api_key") == "secret"
    assert s.get("ai_model") == "gpt-image-1"  # default still resolves


def test_client_id_source_tracks_the_same_chain(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.settings import get_settings

    # conftest sets YOTO_CLIENT_ID autouse — clear it to reach the lower tiers.
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    assert cfg.client_id_source() == "builtin"
    assert cfg.resolve_client_id() == cfg.DEFAULT_YOTO_CLIENT_ID

    get_settings().set("yoto_client_id", "from_setting")
    assert cfg.client_id_source() == "saved"
    assert cfg.resolve_client_id() == "from_setting"

    monkeypatch.setenv("YOTO_CLIENT_ID", "from_env")
    assert cfg.client_id_source() == "env"
    assert cfg.resolve_client_id() == "from_env"


def test_client_id_source_ignores_blank_values(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.settings import get_settings

    monkeypatch.setenv("YOTO_CLIENT_ID", "   ")
    get_settings().set("yoto_client_id", "from_setting")
    # A whitespace-only env var is not a Client ID; fall through to the saved one
    # rather than resolving to an empty string.
    assert cfg.client_id_source() == "saved"
    assert cfg.resolve_client_id() == "from_setting"


def test_mask_client_id(temp_config):
    from yoto_maker import config as cfg

    assert cfg.mask_client_id("a8OGO6EfbWit5tDUUrOz0g49s49NQoU1") == "a8OG…oU1"
    # Short enough that masking would reveal the whole thing anyway.
    assert cfg.mask_client_id("abc") == "abc"
    assert cfg.mask_client_id("") == ""


def test_resolve_client_id_with_source_matches_the_two_single_getters(temp_config, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    from yoto_maker import config as cfg

    assert cfg.resolve_client_id_with_source() == (
        cfg.resolve_client_id(),
        cfg.client_id_source(),
    )

    monkeypatch.setenv("YOTO_CLIENT_ID", "fromTheEnvironment0000000000000x")
    assert cfg.resolve_client_id_with_source() == ("fromTheEnvironment0000000000000x", "env")


def test_connection_status_reports_source_and_mask(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    st = auth.connection_status()
    assert st["connected"] is False
    assert st["client_id_source"] == "builtin"
    assert st["client_id_masked"] == cfg.mask_client_id(cfg.DEFAULT_YOTO_CLIENT_ID)
    assert st["configured"] is True  # legacy field, always True — kept for compatibility


def test_connection_status_hides_the_full_client_id_for_builtin(temp_config, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    from yoto_maker.yoto import auth

    st = auth.connection_status()
    assert st["client_id_source"] == "builtin"
    # Deliberately null, not the constant: the UI renders no value in this state
    # and must not be handed one it is specified never to display.
    assert st["client_id_full"] is None


def test_connection_status_reports_the_full_client_id_for_env(temp_config, monkeypatch):
    monkeypatch.setenv("YOTO_CLIENT_ID", "envSetByS0meoneElse00000000000x1")
    from yoto_maker.yoto import auth

    st = auth.connection_status()
    assert st["client_id_source"] == "env"
    assert st["client_id_full"] == "envSetByS0meoneElse00000000000x1"
    assert st["client_id_masked"] == "envS…0x1"
