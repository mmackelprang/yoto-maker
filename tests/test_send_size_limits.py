"""Pins on the send path's upload leg — its bytes, its headers, its 413.

Written BEFORE the fix (queue item 20). Everything in this file that is not
marked as new behaviour passes on unmodified `main`; that is the point. The send
path is shipped and a real user depends on it, so the wire form is pinned first
and only then changed.
"""
from __future__ import annotations

import httpx
import pytest

from yoto_maker.yoto.client import (
    YotoClient,
    YotoError,
    _friendly_http,
    _track_too_big,
)


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


# --- the memory profile ----------------------------------------------------- #

def test_put_audio_streams_the_file_and_never_materialises_it(tmp_path):
    """Fails the moment someone reintroduces `content=fh.read()`.

    The wire-form test above cannot catch that regression — a bytes body and a
    streamed file produce an identical request. This one looks at what is handed
    to the client instead.
    """
    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"y" * 4096)
    captured: dict = {}

    class _CaptureClient:
        def put(self, url, content=None, headers=None, **k):
            captured["is_bytes"] = isinstance(content, (bytes, bytearray))
            captured["is_readable"] = hasattr(content, "read")
            captured["bytes_available"] = len(content.read()) if hasattr(content, "read") else 0

            class _Resp:
                status_code = 200

                def raise_for_status(self):
                    return None

            return _Resp()

    YotoClient(client=_CaptureClient())._put_audio("http://upload.example/put", audio)

    assert captured["is_bytes"] is False
    assert captured["is_readable"] is True
    assert captured["bytes_available"] == 4096


# --- 413: which ceiling? ---------------------------------------------------- #
#
# Three tests rather than one, because the size assertion and the routing
# assertion want different fixtures: asserting "118 MB" needs a 118 MB number,
# and writing a 118 MB file into tmp_path on every suite run to get one would be
# absurd. So the message is tested directly with a number, and _put_audio is
# tested only for whether it reaches that message at all.

def test_track_too_big_message_names_the_track_the_limit_and_the_size():
    msg = _track_too_big("Chapter Nine", 118_400_000)
    assert "Chapter Nine" in msg     # which track
    assert "100 MB" in msg           # which ceiling
    assert "118 MB" in msg           # whole MB, 10^6 — copy.md §5.9's ratified rule
    assert "118.4" not in msg        # never a decimal place
    assert "5 hours" not in msg      # NOT the card-level ceiling


def test_track_too_big_omits_the_size_when_it_is_unknown():
    """A missing file probes as 0 bytes; "this one is 0 MB" is nonsense.

    Note the assertion is on the CLAUSE, not on the string "0 MB" — "100 MB"
    contains "0 MB" as a substring, so that check would pass vacuously.
    """
    msg = _track_too_big("Chapter Nine", 0)
    assert "Chapter Nine" in msg
    assert "100 MB" in msg
    assert "this one is" not in msg


def test_track_too_big_falls_back_when_no_title_is_known():
    msg = _track_too_big(None, 118_400_000)
    assert "that track" in msg
    assert "100 MB" in msg


def test_413_on_a_track_upload_uses_the_per_track_message(tmp_path):
    """The defect in queue item 20's second half.

    A 413 while PUTting one track's audio is a per-track refusal. Naming the
    card-level 5-hour ceiling there sends the user to a fix that cannot work.
    """
    audio = tmp_path / "chapter nine.wav"
    audio.write_bytes(b"z" * 1024)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(413)

    with pytest.raises(YotoError) as exc:
        YotoClient(client=_mock_client(handler))._put_audio(
            "http://upload.example/put", audio, title="Chapter Nine"
        )

    assert "Chapter Nine" in str(exc.value)
    assert "5 hours" not in str(exc.value)


def test_413_elsewhere_no_longer_claims_a_ceiling_it_cannot_vouch_for():
    """_friendly_http is shared by six call sites. A 413 from the card-creation
    POST is a body-size limit, not an audio one; it must not name either ceiling.
    """
    msg = _friendly_http(_http_error(413), "building your card")
    assert "5 hours" not in msg
    assert "100 MB" not in msg
    assert "too big" in msg.lower()
