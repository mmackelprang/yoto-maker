"""Yoto upload client tests with a fake HTTP client (no real network)."""
from __future__ import annotations

import httpx
import pytest

from yoto_maker.yoto import client as client_mod
from yoto_maker.yoto.client import (
    TrackInput,
    YotoClient,
    YotoError,
    _transcoded_format,
)


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
            # first poll: not ready; second: ready. The ready shape is the
            # live-captured one: transcodedInfo is a child of `transcode`, and
            # Yoto reports format "opus" (it serves Ogg Opus), channels "stereo".
            if self._transcode_polls < 2:
                return FakeResponse({})
            return FakeResponse({"transcode": {
                "transcodedSha256": "SHA123",
                "transcodedInfo": {
                    "duration": 123, "codec": "opus", "format": "opus",
                    "sampleRate": 48000, "channels": "stereo",
                    "bitrate": 92000, "inputFormat": "mp3", "fileSize": 456789,
                },
            }})
        return FakeResponse({})

    def put(self, url, content=None, headers=None, **k):
        self.calls.append(("PUT", url, len(content or b"")))
        return FakeResponse({})

    def post(self, url, json=None, files=None, headers=None, content=None, **k):
        self.calls.append(("POST", url, json))
        if url.endswith("/displayIcons/user/me/upload"):
            # Yoto requires raw bytes, not multipart — record how we sent it.
            self.icon_sent_content = content
            self.icon_sent_files = files
            self.icon_content_type = (headers or {}).get("Content-Type")
            return FakeResponse({"displayIcon": {"mediaId": "ICON1"}})
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
    track = chapters[0]["tracks"][0]
    assert track["trackUrl"] == "yoto:#SHA123"
    # The card advertises Yoto's TRUE transcoded format ("opus"), not the local
    # MP3 — this is the entire behavioural delta of this change.
    assert track["format"] == "opus"
    # channels stays the app's existing "stereo"/"mono" STRING (this change must
    # not turn it into an int); the sample is mono, so it's "mono" here.
    assert track["channels"] in ("stereo", "mono")
    assert isinstance(track["channels"], str)
    assert chapters[0]["display"]["icon16x16"] == "yoto:#ICON1"
    # icon must be sent as RAW BYTES (image/png), never multipart — Yoto rejects
    # multipart with 400 "A binary image file is required".
    assert fake.icon_sent_content is not None
    assert fake.icon_sent_files is None
    assert fake.icon_content_type == "image/png"
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


# -- transcoded format propagation (the format-only fix) ---------------------

_LIVE_INFO = {
    "duration": 123, "codec": "opus", "format": "opus", "sampleRate": 48000,
    "channels": "stereo", "bitrate": 92000, "inputFormat": "mp3", "fileSize": 456789,
}


def test_transcoded_format_returns_opus_for_live_shape():
    assert _transcoded_format(_LIVE_INFO) == "opus"


def test_transcoded_format_degrades_to_none():
    # Missing / empty / wrong-type / None must return None so create_card falls
    # back to the local probe — never an exception, never a wrong value.
    assert _transcoded_format(None) is None
    assert _transcoded_format({}) is None
    assert _transcoded_format({"format": ""}) is None
    assert _transcoded_format({"format": 123}) is None
    assert _transcoded_format("not-a-dict") is None
    assert _transcoded_format({"codec": "opus"}) is None  # no "format" key


def test_poll_transcode_returns_sha_and_info():
    """_poll_transcode returns (sha, transcodedInfo dict) once ready."""

    class PollClient:
        def __init__(self):
            self.n = 0

        def get(self, url, **k):
            self.n += 1
            if self.n < 2:
                return FakeResponse({})  # still transcoding, no sha yet
            return FakeResponse({"transcode": {
                "transcodedSha256": "SHAxyz", "transcodedInfo": dict(_LIVE_INFO)}})

        def close(self):
            pass

    yc = YotoClient(client=PollClient())
    sha, info = yc._poll_transcode("uid1")
    assert sha == "SHAxyz"
    assert isinstance(info, dict) and info["format"] == "opus"


def test_poll_transcode_returns_none_info_when_absent():
    """A ready transcode with no transcodedInfo yields (sha, None)."""

    class PollClient:
        def get(self, url, **k):
            return FakeResponse({"transcode": {"transcodedSha256": "SHAonly"}})

        def close(self):
            pass

    sha, info = YotoClient(client=PollClient())._poll_transcode("uid1")
    assert sha == "SHAonly"
    assert info is None


def test_create_card_degrades_when_transcoded_info_missing(sample_mp3, temp_config):
    """A ready transcode missing transcodedInfo must still build the card
    (degrade to the local probe's format), never raise."""

    class NoInfoClient(FakeClient):
        def get(self, url, **k):
            if "/transcoded" in url:
                self._transcode_polls += 1
                if self._transcode_polls < 2:
                    return FakeResponse({})
                # sha present but NO transcodedInfo — the degrade path.
                return FakeResponse({"transcode": {"transcodedSha256": "SHA123"}})
            return super().get(url, **k)

    yc = YotoClient(client=NoInfoClient())
    result = yc.create_card("X", [TrackInput(audio_path=sample_mp3, title="t")])
    assert result.content_id == "CARD123"  # built, no exception
    track = yc._client.last_content["content"]["chapters"][0]["tracks"][0]
    # Falls back to the local probe's format (a real MP3), not "opus".
    assert track["format"] != "opus"
    assert isinstance(track["format"], str) and track["format"]
