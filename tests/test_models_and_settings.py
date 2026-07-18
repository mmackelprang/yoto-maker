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


def test_settings_roundtrip(temp_config):
    s = get_settings()
    assert s.get("ai_model") == "gpt-image-1"  # default
    assert s.get("missing") is None
    s.set("ai_api_key", "secret")
    assert s.get("ai_api_key") == "secret"
    # persisted to the temp data dir
    assert temp_config.settings_path.exists()
