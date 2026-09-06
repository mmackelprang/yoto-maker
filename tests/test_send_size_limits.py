"""Pins on the send path's upload leg — its bytes, its headers, its 413.

Written BEFORE the fix (queue item 20). Everything in this file that is not
marked as new behaviour passes on unmodified `main`; that is the point. The send
path is shipped and a real user depends on it, so the wire form is pinned first
and only then changed.
"""
from __future__ import annotations

import httpx
import pytest

from yoto_maker.yoto.client import YotoClient, YotoError, _friendly_http


def _mock_client(handler) -> httpx.Client:
    """A real httpx.Client whose transport is scripted, so httpx's own header
    and body encoding is exercised rather than stubbed out."""
    return httpx.Client(transport=httpx.MockTransport(handler))


def _http_error(status: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        f"HTTP {status}",
        request=httpx.Request("PUT", "http://upload.example/put"),
        response=httpx.Response(status),
    )


# --- the wire form of the audio PUT ---------------------------------------- #

def test_put_audio_sends_every_byte_with_an_explicit_content_length(tmp_path):
    """The four properties a pre-signed storage PUT depends on.

    Chunked transfer-encoding is the failure mode to guard against: a pre-signed
    PUT rejects it, and it is what httpx falls back to for a body whose length it
    cannot peek. Pinned here so a future httpx bump cannot break the upload
    silently.
    """
    payload = bytes(range(256)) * 500          # 128 000 bytes, non-repeating head
    audio = tmp_path / "track.mp3"
    audio.write_bytes(payload)

    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["content_length"] = request.headers.get("content-length")
        seen["transfer_encoding"] = request.headers.get("transfer-encoding")
        seen["content_type"] = request.headers.get("content-type")
        seen["body"] = request.read()
        return httpx.Response(200)

    YotoClient(client=_mock_client(handler))._put_audio(
        "http://upload.example/put", audio
    )

    assert seen["method"] == "PUT"
    assert seen["url"] == "http://upload.example/put"
    assert seen["body"] == payload                       # every byte, unaltered
    assert seen["content_length"] == str(len(payload))   # explicit, not chunked
    assert seen["transfer_encoding"] is None
    assert seen["content_type"]                          # some audio type is set


def test_put_audio_turns_a_failed_upload_into_a_yoto_error(tmp_path):
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"x" * 64)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(YotoError):
        YotoClient(client=_mock_client(handler))._put_audio(
            "http://upload.example/put", audio
        )


# --- the shared HTTP-error mapper ------------------------------------------ #

@pytest.mark.parametrize("status", [401, 403])
def test_auth_failures_still_say_the_sign_in_expired(status):
    msg = _friendly_http(_http_error(status), "uploading the audio")
    assert "sign-in has expired" in msg


def test_server_errors_still_name_what_we_were_doing():
    msg = _friendly_http(_http_error(503), "uploading the audio")
    assert "uploading the audio" in msg


def test_timeouts_are_unchanged():
    msg = _friendly_http(httpx.ConnectTimeout("slow"), "uploading the audio")
    assert "timed out" in msg
