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
    # aggregate metadata sums durations/sizes
    assert p["metadata"]["media"]["duration"] == 631
    assert p["metadata"]["media"]["fileSize"] == 3000


def test_build_content_payload_empty():
    p = build_content_payload("Empty", [])
    assert p["content"]["chapters"] == []
    assert p["metadata"]["media"]["duration"] == 0


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
