"""Pins on the send path's upload leg — its bytes, its headers, its 413.

Written BEFORE the fix (queue item 20). Everything in this file that is not
marked as new behaviour passes on unmodified `main`; that is the point. The send
path is shipped and a real user depends on it, so the wire form is pinned first
and only then changed.
"""
from __future__ import annotations

import inspect
import re

import httpx
import pytest

from yoto_maker.server.app import STATIC_DIR
from yoto_maker.yoto import client as client_mod
from yoto_maker.yoto.client import (
    TrackInput,
    YotoClient,
    YotoError,
    _friendly_http,
    _track_too_big,
)

# The cross-path pointer copy.md §10.3 ruled in. Held as one constant because
# three different assertions need it and a typo in any of them would silently
# stop guarding anything.
_POINTER = "press “📁 Save the files to a folder” below"


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


@pytest.fixture
def _authed(monkeypatch):
    """Mirrors test_yoto_client.py:79-82. NOT autouse here — most tests in this
    file call _put_audio directly, which touches neither auth nor sleep."""
    monkeypatch.setattr(client_mod.time, "sleep", lambda *_: None)
    monkeypatch.setattr(client_mod.auth, "get_access_token", lambda: "TOKEN")


class _Resp:
    """Minimal stand-in for httpx.Response, matching test_yoto_client.py's
    FakeResponse. Defined locally rather than imported so the two test modules
    stay independently readable — the repo's existing per-file-fake habit."""

    def __init__(self, payload=None, status=200):
        self._payload = payload or {}
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err",
                request=httpx.Request("PUT", "http://upload.example/put"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


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
    assert seen["content_type"].startswith("audio/")     # pinned, not just truthy


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
            # `is_readable` alone passes against io.BytesIO(fh.read()) — fully
            # materialised, then streamed. fileno() is the discriminator, and it
            # is httpx's own: peek_filelike_length (_utils.py, httpx 0.28) opens
            # with `fd = stream.fileno()` under the comment "Is it an actual
            # file?". Note it must be CALLED, not hasattr'd — BytesIO inherits a
            # fileno() from io.IOBase that raises UnsupportedOperation, so the
            # attribute is present on both and hasattr cannot tell them apart.
            try:
                content.fileno()
                captured["is_real_file"] = True
            except Exception:
                captured["is_real_file"] = False
            captured["bytes_available"] = len(content.read()) if hasattr(content, "read") else 0

            class _Resp:
                status_code = 200

                def raise_for_status(self):
                    return None

            return _Resp()

    YotoClient(client=_CaptureClient())._put_audio("http://upload.example/put", audio)

    assert captured["is_bytes"] is False
    assert captured["is_readable"] is True
    assert captured["is_real_file"] is True
    assert captured["bytes_available"] == 4096


# --- 413: which ceiling? ---------------------------------------------------- #
#
# ⚠ These assertions were INVERTED on 2026-09-06 by copy.md §10.2's ruling, and
# the inversion is the point. The first test used to assert the message named
# Yoto's 100 MB ceiling and the file's size; it now asserts that NEITHER appears.
# Deleting it instead would have left the absence unguarded, and the absence is
# the ruling: the refusal is observed, the 100 MB figure is documentation, and
# plan §8's live probe has not run. This test is what stops the number coming
# back as an improvement.

def test_track_too_big_names_the_track_and_prints_no_number_at_all():
    """copy.md §10.2 — the inverse of the assertion this test used to make."""
    msg = _track_too_big("Chapter Nine")

    assert "Chapter Nine" in msg          # which track — unchanged
    assert "100" not in msg               # not Yoto's ceiling, in any wording
    assert "MB" not in msg                # not the file's size either
    assert "5 hours" not in msg           # and still not the card-level ceiling
    # Nothing is rounded, so no rounding has to be right. The title carries no
    # digits, so any digit in the message came from the app.
    assert not any(ch.isdigit() for ch in msg), msg


def test_track_too_big_is_not_even_given_a_size():
    """The structural half of §10.2, and the reason the test above cannot rot.

    Replaces test_track_too_big_omits_the_size_when_it_is_unknown, whose premise
    (a missing file probes as 0 bytes, and "this one is 0 MB" is nonsense) is now
    unreachable by construction. A function that never receives a size cannot
    print one, and a byte comparison cannot creep into client.py behind it —
    which is plan §2's design, restated as a signature.
    """
    assert list(inspect.signature(_track_too_big).parameters) == ["title"]


def test_track_too_big_falls_back_when_no_title_is_known():
    msg = _track_too_big(None)
    assert "one of your tracks" in msg    # copy.md §10.1's no-title arm, verbatim
    assert "100" not in msg
    assert _POINTER in msg                # the recovery survives the title fallback


def test_track_too_big_is_copy_md_10_1_verbatim():
    """Both arms, character for character, curly quotes and all.

    The strings are the deliverable of a Designer ruling, not prose this module
    owns. A paraphrase that reads identically is still a different string, and
    §10.1's three sentences were ordered deliberately: which track, what it cost
    her, what to do.
    """
    assert _track_too_big("Chapter Nine") == (
        "Yoto wouldn’t take “Chapter Nine” — it’s bigger than Yoto allows for a "
        "single track. No card was made in your Yoto account. There’s another "
        "way to finish this card: press “📁 Save the files to a folder” below."
    )
    assert _track_too_big(None) == (
        "Yoto wouldn’t take one of your tracks — it’s bigger than Yoto allows "
        "for a single track. No card was made in your Yoto account. There’s "
        "another way to finish this card: press “📁 Save the files to a folder” "
        "below."
    )


def test_the_pointer_promises_nothing_about_size():
    """copy.md §10.3. An oversized file already in the copy-as-is set is copied
    untouched (export/rules.py:46-47), so saving would not shrink it. The string
    offers another way to FINISH THE CARD and never claims smaller files."""
    msg = _track_too_big("Chapter Nine")
    assert "There’s another way to finish this card" in msg
    for promise in ("smaller", "shrink", "reduce", "compress"):
        assert promise not in msg.lower()


def test_the_pointer_is_not_conditioned_on_file_type():
    """§10.3's box: conditioning on an extension would put a rule in client.py
    that export/rules.py already owns. The save path's §5.9 advisory fires on
    the other side for the minority this cannot help.

    Both scopes are checked, because the natural place to write the forbidden
    condition is NOT inside the helper — it is the call site, which is where
    `audio_path` is actually in scope:
        too_big=_track_too_big(title) if audio_path.suffix in ... else None
    """
    def body_of(fn) -> str:
        """Source with any docstring removed. `_put_audio` has none, so a bare
        two-index slice raises rather than checking nothing."""
        src = inspect.getsource(fn)
        first = src.find('"""')
        if first == -1:
            return src
        close = src.index('"""', first + 3)
        return src[:first] + src[close + 3:]

    for scope in (client_mod._track_too_big, client_mod.YotoClient._put_audio):
        text = body_of(scope)
        for ext in (".wav", ".flac", ".mp3", ".ogg", ".opus", ".mp4"):
            assert ext not in text, f"{ext} conditions the pointer in {scope.__name__}"
        # The call site must hand over the title unconditionally.
        assert "_track_too_big(title) if" not in text


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
    assert _POINTER in str(exc.value)   # §4b.1 row 1 — the only row that points


def test_413_elsewhere_no_longer_claims_a_ceiling_it_cannot_vouch_for():
    """_friendly_http is shared by six call sites. A 413 from the card-creation
    POST is a body-size limit, not an audio one; it must not name either ceiling.
    """
    msg = _friendly_http(_http_error(413), "building your card")
    assert "5 hours" not in msg
    assert "100 MB" not in msg
    assert "too big" in msg.lower()


def test_the_generic_413_is_no_longer_a_dead_end():
    """copy.md §10.4 — the app's only error sentence that offered nothing now
    ends in configuration-surface §4d's ratified recovery, the phrasing already
    shipped at app.js:2267."""
    msg = _friendly_http(_http_error(413), "building your card")
    assert msg == (
        "Yoto wouldn’t take that — it was too big to send. "
        "Tell whoever set Yoto Maker up for you."
    )
    # No retry hedge: the realistic generic 413 is the same size next time.
    assert "keeps happening" not in msg
    assert "try again" not in msg.lower()
    # `doing` is deliberately not interpolated — two of the six call sites are
    # reads, and "wouldn't take that while listing your cards" says nothing.
    assert "building your card" not in msg
    # §4b.1 row 2: this arm does NOT point at the save button.
    assert "Save the files to a folder" not in msg


# ⚠ interactions.md §4b.1's table, implemented as a test rather than trusted.
#
# The pointer belongs ONLY to failures a retry cannot fix. A size refusal is
# deterministic — the file is the same size next time — which is what makes
# "there's another way" honest there and wrong everywhere else. Sending a user
# with an expired sign-in, or a transient 5xx, to the save button is wrong
# advice, and it is exactly the leak a string change can reintroduce: the old
# guard asserted on "100 MB", which this ruling deleted, so it would have gone
# vacuous and still passed.

_NOT_POINTED_AT = [
    pytest.param(_http_error(401), id="401-sign-in-expired"),
    pytest.param(_http_error(403), id="403-sign-in-expired"),
    pytest.param(_http_error(500), id="500-retry-is-the-recovery"),
    pytest.param(_http_error(503), id="503-retry-is-the-recovery"),
    pytest.param(httpx.ConnectTimeout("slow"), id="timeout-retry"),
    pytest.param(httpx.ConnectError("x"), id="transport-retry"),
]


@pytest.mark.parametrize("exc", _NOT_POINTED_AT)
def test_too_big_never_leaks_out_of_the_413_branch(exc):
    """_put_audio passes too_big on EVERY failure, not just 413 (client.py:267).
    Only the 413 branch may use it."""
    msg = _friendly_http(exc, "uploading the audio",
                         too_big=_track_too_big("Chapter Nine"))
    assert "Chapter Nine" not in msg
    assert _POINTER not in msg
    assert "Save the files to a folder" not in msg
    assert "bigger than Yoto allows" not in msg


def test_an_expired_sign_in_during_a_track_upload_still_says_reconnect(tmp_path):
    """§4b.1 row 3, end to end through the call site that supplies `too_big`.

    The MEDIUM this closes: `too_big` is built on every _put_audio failure, so
    the only thing keeping a 401 from claiming the track was too large is the
    413 branch's exclusive use of it.
    """
    audio = tmp_path / "chapter nine.wav"
    audio.write_bytes(b"z" * 1024)

    with pytest.raises(YotoError) as exc:
        YotoClient(client=_mock_client(lambda r: httpx.Response(401)))._put_audio(
            "http://upload.example/put", audio, title="Chapter Nine"
        )

    assert str(exc.value) == (
        "Your Yoto sign-in has expired. Please connect your Yoto account again."
    )


# --- §4b.4: "below" is a positional claim, so it is checked ------------------ #

@pytest.fixture(scope="module")
def index_html() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATIC_DIR / "app.js").read_text(encoding="utf-8")


def test_the_save_button_really_is_below_the_send_error(index_html):
    """interactions.md §4b.4's standing condition, as an invariant.

    The string says "below". That is true only while #exportRow is the next
    VISIBLE element after #sendError in step 3 — and the two elements that sit
    between them in the DOM are both hidden when this message renders.
    """
    order = [index_html.index(f'id="{el}"')
             for el in ("sendError", "sendDone", "connectWarn", "exportRow")]
    assert order == sorted(order)

    # Strictly between the two: from the end of #sendError's opening tag to the
    # start of #exportRow's. Slicing on the id= positions instead would swallow
    # #exportRow's own "<div " and count it as something sitting in between.
    start = index_html.index(">", index_html.index('id="sendError"')) + 1
    end = index_html.rindex("<", 0, index_html.index('id="exportRow"'))
    between = index_html[start:end]
    ids = set(re.findall(r'id="([^"]+)"', between))
    # A new box inserted here is precisely what §4b.4 says must change the string.
    assert ids == {"sendDone", "connectWarn"}, (
        f"{ids} now sits between #sendError and #exportRow — copy.md §10.1's "
        "'below' is no longer true and the string must change with it"
    )

    # ...and an element with no id at all must not slip through the check above.
    # A bare <p class="tiny"> hint or an <hr> dropped in here would leave the id
    # set unchanged while "below" quietly stopped meaning "directly below".
    elements = re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)\b",
                          re.sub(r"<!--.*?-->", " ", between, flags=re.S))
    assert elements == ["div", "div"], (
        f"expected exactly #sendDone and #connectWarn between them, got {elements}"
    )

    for el in ("sendDone", "connectWarn"):
        tag = index_html[index_html.index(f'id="{el}"'):]
        assert "hidden" in tag[:tag.index(">") + 1]

    row = index_html[index_html.index('id="exportRow"'):]
    assert "hidden" not in row[:row.index(">") + 1]


def test_send_done_is_hidden_at_runtime_before_the_error_can_render(app_js):
    """The other half of §4b.4 row 1, which the static `hidden` attribute does
    not cover. #sendDone's default is only its FIRST state; what keeps it out of
    the way on a failed send is sendToYoto() hiding it on entry. Without that
    line, a success followed by a 413 leaves the green "🎉 Your card is ready"
    box sitting between the red pointer and the button it names.

    Scoped to sendToYoto's own body, not the whole file: the same call also
    appears in the "Start a new card" handler, so a file-wide `in app_js` check
    stays green when the one that matters here is deleted (proven by mutation).
    """
    body = app_js[app_js.index("async function sendToYoto()"):]
    body = body[:body.index("\n}")]
    assert 'show($("#sendDone"), false);' in body


# ⚠ §4b.4 row 2 is NOT asserted here, because it is not true — see queue item 27.
#
# The table says a send that can reach a 413 "cannot coexist with a visible
# #connectWarn", via: invalid Client ID → sign-in hard-blocked → #sendBtn
# disabled. The middle link does not hold. `connected` is token-presence only
# (auth.py:246, `_load_tokens() is not None`) and is computed independently of
# `client_id_verdict` (auth.py:264), while renderConnectWarn() triggers on the
# verdict alone (app.js:325). Sign in, then have YOTO_CLIENT_ID become invalid
# with the token still live, and both are true at once — confirmed by driving
# the state in the browser, not by reading.
#
# The shipped string is unaffected and must not be changed for this: #exportRow
# stays visible and still below, so "below" remains true. Only §4b.4's REASONING
# is falsified, and narrowing it is Designer's call (item 27) — every code fix
# touches the send path's state machine, which §4b.3 forbids.
#
# So this test asserts the two links that DO hold, and nothing more. A test
# named for a claim that is false is worse than no test at all.

def test_the_two_links_of_4b4_row_2_that_do_hold(app_js):
    """Sign-in state gates the send button, and the warning is verdict-driven.
    What is NOT asserted — that those two facts imply each other — is item 27."""
    assert '$("#sendBtn").disabled = !connected;' in app_js      # link 3
    assert 'y.client_id_verdict === "invalid"' in app_js         # what renders it


def test_the_pointer_quotes_the_button_label_that_ships(index_html):
    """copy.md §10.3: the string is ratified in export-only-mode because it
    quotes that package's button label — so a future relabel finds it here."""
    label = "📁 Save the files to a folder"
    assert f">{label}</button>" in index_html
    assert label in _track_too_big("Chapter Nine")


# --- end to end: the right track gets named --------------------------------- #

def test_create_card_names_the_refused_track(tmp_path, temp_config, _authed):
    """End-to-end: a 413 on the second track's PUT must name the second track.

    `TrackInput` is (audio_path, title, icon_path) — client.py's dataclass.

    Deliberately NOT the `sample_mp3` fixture. This is the only test that fails
    if `title=tr.title` is dropped from create_card's _put_audio call, and
    sample_mp3 skips when ffmpeg is missing — there is no CI here, so on a
    machine without ffmpeg the sole guard for that call site would silently
    vanish. `_safe_probe` swallows probe failures, so bytes are enough.
    """
    audio = tmp_path / "chapter.mp3"
    audio.write_bytes(b"x" * 256)

    class _RefuseSecondPut:
        def __init__(self):
            self.puts = 0

        def get(self, url, **k):
            if url.endswith("/uploadUrl"):
                return _Resp({"uploadUrl": "http://upload.example/put", "uploadId": "u1"})
            return _Resp({"transcode": {"transcodedSha256": "SHA", "transcodedInfo": {}}})

        def put(self, url, content=None, headers=None, **k):
            if hasattr(content, "read"):
                content.read()
            self.puts += 1
            return _Resp({}, status=200 if self.puts == 1 else 413)

        def post(self, url, **k):
            return _Resp({"cardId": "C1"})

    with pytest.raises(YotoError) as exc:
        YotoClient(client=_RefuseSecondPut()).create_card(
            "My Card",
            [
                TrackInput(audio_path=audio, title="Chapter One"),
                TrackInput(audio_path=audio, title="Chapter Two"),
            ],
        )

    assert "Chapter Two" in str(exc.value)
    assert "Chapter One" not in str(exc.value)
