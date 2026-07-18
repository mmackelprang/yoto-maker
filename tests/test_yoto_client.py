"""Yoto upload client tests with a fake HTTP client (no real network)."""
from __future__ import annotations

import httpx
import pytest

from yoto_maker.yoto import client as client_mod
from yoto_maker.yoto.client import TrackInput, YotoClient, YotoError


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self._payload = payload or {}
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=httpx.Request("GET", "http://x"),
                                        response=httpx.Response(self.status_code))

    def json(self):
        return self._payload


class FakeClient:
    """Scripts the documented upload sequence and records calls."""

    def __init__(self):
        self.calls = []
        self._transcode_polls = 0

    def get(self, url, **k):
        self.calls.append(("GET", url))
        if url.endswith("/uploadUrl"):
            return FakeResponse({"uploadUrl": "http://upload.example/put", "uploadId": "uid1"})
        if "/transcoded" in url:
            self._transcode_polls += 1
            # first poll: not ready; second: ready
            if self._transcode_polls < 2:
                return FakeResponse({})
            return FakeResponse({"transcodedSha256": "SHA123"})
        return FakeResponse({})

    def put(self, url, content=None, headers=None, **k):
        self.calls.append(("PUT", url, len(content or b"")))
        return FakeResponse({})

    def post(self, url, json=None, files=None, headers=None, **k):
        self.calls.append(("POST", url, json))
        if url.endswith("/displayIcons/user/me/upload"):
            return FakeResponse({"mediaId": "ICON1"})
        if url.endswith("/content"):
            self.last_content = json
            return FakeResponse({"cardId": "CARD123"})
        return FakeResponse({})

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _fast_and_authed(monkeypatch):
    monkeypatch.setattr(client_mod.time, "sleep", lambda *_: None)
    monkeypatch.setattr(client_mod.auth, "get_access_token", lambda: "TOKEN")


def test_create_card_happy_path(sample_mp3, temp_config):
    from yoto_maker.images.library import icon_path

    fake = FakeClient()
    yc = YotoClient(client=fake)
    events = []
    tracks = [TrackInput(audio_path=sample_mp3, title="Song One", icon_path=icon_path("star"))]

    result = yc.create_card("Bedtime", tracks, progress=lambda *a: events.append(a))

    assert result.content_id == "CARD123"
    # sequence: uploadUrl, put, transcoded x2, icon upload, content
    kinds = [c[0] for c in fake.calls]
    assert kinds.count("GET") >= 3  # uploadUrl + 2 transcode polls
    # the audio was PUT to the signed upload URL
    put_calls = [c for c in fake.calls if c[0] == "PUT"]
    assert put_calls and put_calls[0][1] == "http://upload.example/put"
    # content payload references the transcoded sha + icon
    chapters = fake.last_content["content"]["chapters"]
    assert chapters[0]["tracks"][0]["trackUrl"] == "yoto:#SHA123"
    assert chapters[0]["display"]["icon16x16"] == "yoto:#ICON1"
    # progress was reported and ended at 'done'
    assert events and events[-1][0] == "done"


def test_create_card_requires_tracks(temp_config):
    with pytest.raises(YotoError):
        YotoClient(client=FakeClient()).create_card("Empty", [])


def test_upload_url_failure_is_friendly(sample_mp3, temp_config, monkeypatch):
    class BadClient(FakeClient):
        def get(self, url, **k):
            if url.endswith("/uploadUrl"):
                return FakeResponse({}, status=401)
            return super().get(url, **k)

    yc = YotoClient(client=BadClient())
    with pytest.raises(YotoError) as exc:
        yc.create_card("X", [TrackInput(audio_path=sample_mp3, title="t")])
    assert "sign-in" in str(exc.value).lower() or "expired" in str(exc.value).lower()


def test_icon_upload_best_effort(sample_mp3, temp_config):
    from yoto_maker.images.library import icon_path

    class NoIconClient(FakeClient):
        def post(self, url, **k):
            if url.endswith("/displayIcons/user/me/upload"):
                return FakeResponse({}, status=500)  # icon fails
            return super().post(url, **k)

    yc = YotoClient(client=NoIconClient())
    result = yc.create_card("X", [TrackInput(audio_path=sample_mp3, title="t", icon_path=icon_path("star"))])
    # card still succeeds; the track just has no icon
    assert result.content_id == "CARD123"
    chapters = yc._client.last_content["content"]["chapters"]
    assert "display" not in chapters[0]
