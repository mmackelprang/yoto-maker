# Plan — Yoto's per-track size limit on the send path

**Date:** 2026-09-05
**Author:** Planner
**Queue item:** 20
**Branch:** `fix/send-path-size-limit`, branched off `main` (**not** off `feat/save-to-a-folder`)
**Ships in:** rides the next release cut — **no version bump of its own.** Backend-only;
no served static asset is touched, so the `__ASSET_V__` cache key (`server/app.py:968`
on `main`) does not need to move. Item 19 owns v0.1.13; this PR must not touch it.
**Type:** correctness fix on the **shipped authenticated send path**. No new surface,
no new markup, no CSS, no design handoff.

---

## 0. The decision this plan makes, stated first

The queue left three options open — **split on bytes**, **transcode on the send path**,
or **advise**. This plan picks **advise**, and then splits "advise" by evidence tier,
because two of the three changes worth making do not depend on the unverified number at
all.

> **Recommendation: do not act on size on the send path. Ship the two changes that are
> certain regardless of what Yoto's limits turn out to be, and hold the advisory itself
> behind a Designer ruling and a live probe.**

### 0.1 Why not split on a byte budget

Three reasons, in descending order of how much they matter.

1. **It does not fix the problem it is aimed at.** A 50-minute 16-bit/44.1 kHz stereo
   WAV is ~529 MB. Splitting it on a 100 MB budget yields six ~88 MB WAVs — six tracks,
   each under the per-track ceiling, **summing to the same 529 MB**, which is over
   Yoto's 500 MB *card* ceiling. The split converts one probable refusal into a
   different, more certain one, and adds five more uploads to get there.
2. **`split_audio` splits on time, not bytes** (`normalize.py:219-238`, the `-f segment
   -segment_time` muxer). A byte budget has to be converted into a seconds budget via an
   assumed byte-rate — which is the "at what bitrate assumption?" the queue row flags.
   For CBR the derivation is exact; for VBR it is an estimate, and every underestimate
   produces a segment over the limit anyway. The margin needed to make that safe makes
   the segments materially shorter than they need to be.
3. **It changes the shipped send path's visible behaviour for users whose cards work
   today.** One 50-minute chapter becomes `(part 1)`…`(part 6)` in the track list and on
   the card. That is a real regression in the output for anyone whose 529 MB WAV
   currently uploads fine — and nothing in the repo establishes that it does not.

### 0.2 Why not transcode on the send path

The obvious argument is "spec §2.4 / `overview.md` §8.6 said act on format, advise on
size." That argument is correct but it is not the strongest one available, and the
strongest one is specific to the send path:

**On the export path, converting costs one lossy generation. On the send path it costs
two.**

| | Export path | Send path |
| --- | --- | --- |
| What happens to a `.flac` today | Website refuses it outright | Uploaded as-is; Yoto transcodes server-side |
| Chain if we convert | FLAC → 192k MP3 → *(website)* → Opus | FLAC → 192k MP3 → *(Yoto)* → Opus |
| Chain if we don't | *(no card — she is stuck)* | FLAC → *(Yoto)* → Opus |
| Lossy generations added by converting | **0** (there is no "don't" — the alternative is failure) | **1** (a second, avoidable encode) |

On the export path conversion is *forced*: it is the only way in the door, so
`rules.py`'s `COPY_AS_IS` acts on format and the quality question never arises. On the
send path nothing forces it. Yoto's API demonstrably ingests what the website refuses —
the app has been PUTting `.wav`, `.flac`, `.ogg`, `.opus` and `.mp4` since
`AudioFileAdapter` shipped, and the repo records no refusal of any of them. So the
trigger for converting here would be **size**, using format as a proxy, and the cost of
being wrong is exactly what §8.6 named: *her audio is quietly made worse.* Only here it
is worse than on the export path, because the encode is additive rather than
substitutive.

That is the case §8.6 reserves for advice, and this is a cleaner instance of it than
the one §8.6 was written about.

### 0.3 Why "advise" still splits into two PRs

The advisory itself — a sentence on step 3 saying *"one of your tracks is over Yoto's
100 MB limit"* — depends entirely on the 100 MB figure being right. That figure is
**Yoto's published documentation, not observed behaviour** (`SESSION_STATE.md:194-200`,
`overview.md` §8.2). Two of the three changes worth making do not:

| | Depends on the 100 MB figure? | Certain today? |
| --- | --- | --- |
| The 413 names the wrong ceiling (`client.py:481-482`) | **No** — Yoto has already refused; we are only explaining a refusal that happened | ✅ Certainly wrong today |
| `_put_audio` holds the whole track in RAM (`client.py:237`) | **No** — a resource defect in our own code | ✅ Certainly true today |
| A pre-send advisory naming 100 MB | **Yes** — entirely | ❓ Unverified |

**This PR ships rows 1 and 2.** Row 3 becomes a new queue row (§9), blocked on a
Designer ruling and on the live probe in §8.

---

## 1. Findings that change the picture

Four things turned up that the briefing notes did not have. Two of them change what this
PR should contain.

### 1.1 `_put_audio` reads the entire track into memory — and item 14 fixes only the other half

`client.py:234-240` (on `main`):

```python
with open(audio_path, "rb") as fh:
    resp = self._client.put(
        upload_url,
        content=fh.read(),      # <-- the whole file, as one bytes object
        ...
```

For the 529 MB WAV in the queue row's own arithmetic, that is a ~529 MB resident
`bytes` object on a machine chosen for being cheap. **This is the same defect, on the
same file, that the job-system ADR §3.1 fixes on the *add* side** — *"Chunked
`copyfileobj` instead of `await file.read()` — peak RAM 260 MB → ~1 MB"*. The ADR does
not mention `_put_audio`, and neither does item 14, 15 or 16. Item 14 will halve the
problem and leave the other half in place.

It is two lines, it is verified safe (§1.2), it needs no copy, no markup and no version
bump, and it is true regardless of what Yoto's ceilings are. It belongs here.

### 1.2 Streaming the PUT is safe for a pre-signed URL — verified against the installed httpx

The obvious risk is that handing httpx a file object switches the request to
`Transfer-Encoding: chunked`, which a pre-signed storage PUT (the upload URL from
`/media/transcode/audio/uploadUrl` is a signed third-party URL, not a Yoto API route)
will usually reject. **That does not happen here**, verified in the installed
httpx 0.28.1:

- `_content.py:121-127` — for a non-`bytes` iterable, httpx calls
  `peek_filelike_length(content)`; if it returns a length it sets
  `{"Content-Length": str(length)}` and **not** `Transfer-Encoding`.
- `_utils.py:100-104` — `peek_filelike_length` on a real file object returns
  `os.fstat(fd).st_size`. An open `"rb"` file always has an `fileno()`.
- `_models.py:441-446` — the caller's own headers win via `setdefault`, so the existing
  `{"Content-Type": …}` is preserved and `Content-Length` is added beside it.
- `_models.py:422-423` — `self.read()` (the load-into-memory step) runs only for a
  `ByteStream`. A file object produces an `IteratorByteStream`, which is not read.

So the wire form is unchanged — same method, same URL, same `Content-Type`, same
`Content-Length`, same bytes — and only the memory profile moves. Task 2's tests pin all
four of those properties so a future httpx bump cannot silently turn this into a chunked
request.

**Measured, not reasoned.** Task 2a's exact `put()` call and Task 3b's exact helper were
run against the installed httpx 0.28.1 before this plan was written. A 128 000-byte file
streamed from an open handle produced:

```
method=PUT  url=http://upload.example/put
content-length=128000   transfer-encoding=None   content-type=audio/mpeg
body == the file's bytes, exactly
```

and `_track_too_big("Chapter Nine", 118_400_000)` produced `…118 MB…` with no decimal
place and no mention of 5 hours. **Builder should still expect these tests to pass on
the first run**; if any of them does not, something in the environment differs from the
one this was checked in and that difference matters more than the test.

### 1.3 A 413 is not one failure, and one string cannot be right for all of them

`_friendly_http` (`client.py:476-490`) is shared by six call sites: `_request_upload_url`,
`_put_audio`, `_poll_transcode`, `_create_content`, `list_my_cards`, `get_card`/
`update_card`. A 413 means "too large", but *which* limit depends entirely on what was
being sent:

- from `_put_audio` → one track's audio → the **per-track** ceiling
- from `_create_content` → a JSON card body → neither ceiling; a body-size limit
- from anywhere else → a small GET/POST; a 413 there is not about audio at all

Today every one of those says *"max 5 hours per card"*. Fixing the string in place would
just move the wrongness around. The fix is to let the one caller that **knows** which
limit applies say so, and make the default stop naming a ceiling it cannot vouch for.

### 1.4 `copy.md` §5.9's strings **cannot** be reused verbatim on the send path

`overview.md` §8.6 suggests they might be — *"a small argument for the send path
borrowing these strings later"*. Checked against the actual text, they cannot. Two
independent reasons:

1. **The approved sentence names the wrong actor.** §5.9: *"…Yoto's **website** may
   refuse it."* On the send path there is no website in the loop — the app is doing the
   sending. The sentence is not merely awkward there, it is false, and it points the
   user at a surface she is not using.
2. **The `{list}` format's stated justification does not carry.** §5.9 ratifies
   number-and-title (`09 - Chapter Nine (118 MB)`) explicitly because *"it is the file
   name she will have to find in a file dialog"*. On the send path there are no written
   files and no file dialog — there is a numbered track list on screen. §5.9's own
   reasoning says that the other pattern (a quoted title, as in §5.3 and §5.5a) is the
   right one when there is no list to scan in a folder. Which pattern applies here is a
   copy decision with a real argument on each side.

**Consequence: the advisory surface needs a Designer pass before Builder can start it.**
That is why it is not in this PR (§0.3, §9). This plan does not invent that copy.

What this PR *does* author is two **error** strings, both replacing text that is
factually wrong today — see §7.1 for exactly what they are and why Planner authoring
them is inside the precedent item 19's plan set.

---

## 2. Global constraints

- **Branch off `main`, not off `feat/save-to-a-folder`.** This PR imports nothing from
  `yoto_maker/export/` and defines no constant that duplicates one in
  `export/rules.py`. It is independent of item 19 in both directions and must stay so —
  a merge order of 19-then-20 or 20-then-19 must both work.
- **Do not add a `MAX_TRACK_BYTES` constant to `client.py`.** The figure appears once,
  in prose, inside a sentence that runs *after Yoto has already refused*. A constant
  would imply a comparison, and there is no comparison anywhere in this PR — that
  absence is the design (§0.2). `export/rules.py:35` keeps the only machine-readable
  copy of the number, and only the path that actually acts on it.
- **`normalize.py` is not touched.** No new kwargs on `_run`, `split_audio` or
  `MAX_TRACK_SECONDS`; items 14–16's byte-identical-when-unset rule is not engaged
  because nothing in this PR goes near that module.
- **No user-visible string may name a file format, codec, path or byte count in
  developer terms** (`docs/design-handoffs/README.md`). `MB` and `MP3` are permitted —
  `MB` is the unit printed on Yoto's own support page and `copy.md` §5.9 prints it; the
  banned words are *export, directory, path, file format, codec, transcode, MP3
  encoding, metadata*.
- **New copy uses typographic apostrophes (`’`)**, per `copy.md:17`. `client.py`'s older
  strings use straight ones; Task 3 normalises the one other mom-facing string in the
  same function region and leaves the developer-facing diagnostic at line 453 alone.
- **This is a shipped path.** Task 1 lands *before* any behaviour changes and pins what
  the code does today. A test written after the change is not a regression test.

---

## 3. Task order and dependencies

```
Task 1  pin today's behaviour (tests only, all green on main)
   │
   ├── Task 2  stream the PUT                      (depends on 1)
   │      │
   │      └── Task 3  the 413 tells the truth      (depends on 1; independent of 2)
   │             │
   │             └── Task 4  wire the track title through create_card  (depends on 3)
   │                    │
   │                    └── Task 5  record the decision in the module docstring
   │
   └── Task 6  queue + plan links (docs only)
```

Tasks 2 and 3 are independently revertable. If the live probe in §8 ever contradicts the
100 MB figure, **Task 3's string is the only thing that needs rewording** and Task 2 is
unaffected.

---

## Task 1 — Pin what the send path does today

**New file `tests/test_send_size_limits.py`.** Every assertion here must pass on
unmodified `main`. Run it, see it green, commit it, *then* start Task 2.

```python
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
```

**Verify:** `pytest tests/test_send_size_limits.py -q` — 5 passed on unmodified `main`.
Then `pytest -q` — the whole suite still green.

**Commit:** `test(send): pin the audio PUT's wire form and the 413 mapper before changing them`

---

## Task 2 — Stream the audio PUT instead of holding the track in RAM

Depends on Task 1.

### 2a. The change

**`yoto_maker/yoto/client.py`** — replace the body of `_put_audio`
(`main` lines 229-244):

```python
    def _put_audio(self, upload_url: str, audio_path: Path) -> None:
        audio_path = Path(audio_path)
        content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
        size = audio_path.stat().st_size if audio_path.exists() else 0
        try:
            # Hand the client the OPEN FILE, not its bytes. `content=fh.read()`
            # held the entire track in memory — ~529 MB for a 50-minute WAV,
            # which the app copies rather than transcodes (sources/audiofile.py).
            # This is the send-side twin of the add-side fix in the job-system
            # ADR §3.1 ("chunked copyfileobj instead of await file.read()"),
            # which does not reach this function.
            #
            # The wire form is UNCHANGED and that is load-bearing: the upload URL
            # is a pre-signed third-party URL, and a pre-signed PUT rejects
            # chunked transfer-encoding. httpx peeks a real file object's length
            # (_content.py:121-127 -> _utils.py:100-104) and sets an explicit
            # Content-Length, exactly as it did for a bytes body. Pinned by
            # test_put_audio_sends_every_byte_with_an_explicit_content_length.
            with open(audio_path, "rb") as fh:
                resp = self._client.put(
                    upload_url,
                    content=fh,
                    headers={"Content-Type": content_type},
                    timeout=UPLOAD_TIMEOUT,  # don't 60s-timeout a large/slow upload
                )
            resp.raise_for_status()
        except Exception as exc:
            log.warning("Yoto audio PUT failed (%s, %d bytes): %r", audio_path.name, size, exc)
            raise YotoError(_friendly_http(exc, "uploading the audio")) from exc
```

The **only** edits are `content=fh.read()` → `content=fh` and the comment. The `with`
block still encloses the `put()` call, so the file is open for the whole send and closed
immediately after — httpx has fully consumed the stream by the time `put()` returns, and
the client sets no retries and no `follow_redirects` on this call, so nothing can try to
re-read a consumed stream.

### 2b. The existing fake has to stop calling `len()` on a file

**`tests/test_yoto_client.py`** — `FakeClient.put` (`main` line 58-60) does
`len(content or b"")`, which raises `TypeError` on a file object. Replace:

```python
    def put(self, url, content=None, headers=None, **k):
        # `content` is now the open file object rather than its bytes (the send
        # path streams — client.py's _put_audio). Read it here so the recorded
        # byte count still means what it always meant.
        body = content.read() if hasattr(content, "read") else (content or b"")
        self.calls.append(("PUT", url, len(body)))
        return FakeResponse({})
```

`test_create_card_happy_path` only asserts `put_calls[0][1] == "http://upload.example/put"`
(line 101), so the third tuple element is not asserted anywhere — but keep it correct
rather than dropping it, so the next person who wants it finds a real number.

### 2c. The regression guard

Append to `tests/test_send_size_limits.py`:

```python
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
```

**Verify:** `pytest tests/test_send_size_limits.py tests/test_yoto_client.py -q` — green.
Then `pytest -q`.

**Commit:** `fix(send): stream the audio upload instead of reading the whole track into memory`

---

## Task 3 — Make a 413 name the limit that was actually hit

Depends on Task 1. Independent of Task 2 — revertable on its own.

### 3a. Red first

Add `_track_too_big` to `tests/test_send_size_limits.py`'s import line, then append:

```python
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
```

### 3b. The message helper

**`yoto_maker/yoto/client.py`** — add immediately above `_friendly_http`
(`main` line 476):

```python
def _track_too_big(title: str | None, size_bytes: int) -> str:
    """What to say when Yoto has refused ONE track's audio as too large.

    ⚠ PROVENANCE: the 100 MB figure is Yoto's published documentation
    (support.yotoplay.com, 2026-07-20), not observed behaviour — the same
    evidence tier as the accepted-format list in export/rules.py. It is used
    here ONLY to explain a refusal Yoto has already made. Nothing in this module
    compares a file against it, and nothing should: the send path advises on
    size, it does not act on it (queue item 20's plan §0.2). That is why this is
    prose and not a constant.
    """
    what = f"“{title}”" if title else "that track"
    # Whole MB, read as 10^6 — the same conservative reading copy.md §5.9 uses.
    mb = int(round(size_bytes / 1_000_000))
    how_big = f", and this one is {mb} MB" if mb > 0 else ""
    return (
        f"Yoto wouldn’t take {what} — it’s bigger than Yoto allows for one "
        f"track. Yoto’s limit is 100 MB{how_big}. If you have a shorter "
        "recording of it, try that instead — otherwise tell whoever set Yoto "
        "Maker up for you."
    )
```

### 3c. `_friendly_http` takes the caller's word for which limit applies

**`yoto_maker/yoto/client.py`** — `_friendly_http` (`main` lines 476-490):

```python
def _friendly_http(exc: Exception, doing: str, *, too_big: str | None = None) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return "Your Yoto sign-in has expired. Please connect your Yoto account again."
        if code == 413:
            # 413 is "too large" — but WHICH limit was hit depends entirely on
            # what we were sending, and this helper is shared by six call sites.
            # It used to name the card-level 5-hour ceiling for every one of
            # them, including the per-track audio PUT: the place a 413 is most
            # likely, and the place that ceiling is certainly the wrong thing to
            # say. A caller that knows which limit applies passes `too_big`;
            # everyone else gets a sentence that names no ceiling, because we
            # cannot tell which one it was.
            return too_big or "Yoto wouldn’t take that — it was too big to send."
        if 500 <= code < 600:
            return f"Yoto had a problem while {doing}. Please try again shortly."
    if isinstance(exc, httpx.TimeoutException):
        return (
            f"The connection to Yoto timed out while {doing}. This usually means a slow "
            "internet connection — please try again, ideally on a faster connection."
        )
    return f"Something went wrong while {doing}. Please check your internet and try again."
```

`too_big` is keyword-only with a `None` default, so every existing call site is
byte-identical in behaviour except for the 413 branch it was already getting wrong.

### 3d. `_put_audio` supplies it

**`yoto_maker/yoto/client.py`** — two edits to `_put_audio` as Task 2a left it: the
signature line, and the `except` clause. The `…` below is Task 2a's body **unchanged** —
the `content_type` / `size` lines, the `try:`, the `with open(...)` block and the
`raise_for_status()`. Nothing between the two edits moves.

```python
    def _put_audio(self, upload_url: str, audio_path: Path, *, title: str | None = None) -> None:
        audio_path = Path(audio_path)
        …                                    # Task 2a's body, unchanged
        except Exception as exc:
            log.warning("Yoto audio PUT failed (%s, %d bytes): %r", audio_path.name, size, exc)
            raise YotoError(
                _friendly_http(
                    exc, "uploading the audio", too_big=_track_too_big(title, size)
                )
            ) from exc
```

`size` is already computed on the line above the `try` (`main` line 232) for the log —
no new `stat()` call. `title` is keyword-only with a `None` default, so
`_put_audio(url, path)` keeps working unchanged and `_track_too_big(None, size)` falls
back to *"that track"*.

### 3e. The one other mom-facing straight apostrophe in the same region

**`yoto_maker/yoto/client.py:226`** — `copy.md:17` mandates `’` for user-visible copy,
and this string sits four lines above the code Task 2 and Task 3 rewrite:

```python
            raise YotoError("Yoto didn’t give us a place to upload to. Please try again.")
```

Leave `client.py:453`'s `couldn't read the artifact` alone — that is an `ArtifactProbe`
reason surfaced only by the `repair` CLI, which is a maintainer tool, not mom-facing.

**Verify:** `pytest tests/test_send_size_limits.py -q` — all green (was red before 3b–3d).
Then `pytest -q`.

**Commit:** `fix(send): a 413 now names the per-track limit and the track, not the card ceiling`

---

## Task 4 — Pass the track title through so the message can name it

Depends on Task 3.

**`yoto_maker/yoto/client.py`** — in `create_card`, the upload line
(`main` line 159):

```python
            self._put_audio(upload_url, tr.audio_path, title=tr.title)
```

That is the whole change. `TrackInput.title` is already in scope on that line — the same
`tr` is read as `tr.title` in the `log.warning` block at `main` lines 182-187.

Append to `tests/test_send_size_limits.py`. This test drives `create_card`, which reaches
`_poll_transcode` → `_headers()` → `auth.get_access_token()`, so it needs the same
auth/sleep stubbing `test_yoto_client.py:79-82` uses. That fixture is `autouse` but
module-scoped, so this file needs its own copy — put it near the top of the file:

```python
from yoto_maker.yoto import client as client_mod
from yoto_maker.yoto.client import TrackInput


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
```

```python
def test_create_card_names_the_refused_track(sample_mp3, temp_config, _authed):
    """End-to-end: a 413 on the second track's PUT must name the second track.

    `TrackInput` is (audio_path, title, icon_path) — client.py's dataclass.
    """

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
                TrackInput(audio_path=sample_mp3, title="Chapter One"),
                TrackInput(audio_path=sample_mp3, title="Chapter Two"),
            ],
        )

    assert "Chapter Two" in str(exc.value)
    assert "Chapter One" not in str(exc.value)
```

**Verify:** `pytest -q`.

**Commit:** `fix(send): name the refused track in the too-big message`

---

## Task 5 — Record the decision where the next reader will hit it

Depends on Task 3.

**`yoto_maker/yoto/client.py`** — append to the module docstring, after the existing
`NOTE:` paragraph (`main` lines 14-16):

```
SIZE LIMITS: this module does NOT check a track against Yoto's published ceilings
(100 MB / 60 min per track; 500 MB / 5 h / 100 tracks per card) before uploading,
and that is deliberate rather than an oversight. Those figures are Yoto's
documentation, not observed behaviour, and the send path — unlike the save-to-a-
folder path — has no format reason to re-encode, so acting on them would mean a
second lossy generation on top of Yoto's own server-side transcode, triggered by
a number the app cannot verify. The app therefore only EXPLAINS a refusal Yoto
has already made (see _track_too_big). Reasoning in full:
docs/superpowers/plans/2026-09-05-per-track-size-limit.md §0.
```

No test. This is the guard-rail against a future pass "fixing" the absent check.

**Commit:** `docs(send): record why the send path does not check size before uploading`

---

## Task 6 — Close the row out

Docs only, no code.

**Already landed by the planning PR — do not redo:** row 20 rewritten and linked to this
plan, row 21 filed, the banner moved, and the "Item 20 — briefing notes" section updated
to record that the act-vs-advise question is answered and that `copy.md` §5.9 was checked
and found not verbatim-reusable.

**What Builder does:**

1. **`docs/BUILDER_QUEUE.md`** — flip row 20's status 📋 → 🚧 on claim, → ✅ on merge,
   and add the PR number and merge commit to the row the way rows 13, 18 and 19 carry
   theirs.
2. **`docs/BUILDER_QUEUE.md`** — add the Shipped-table entry, matching the existing rows.
3. **`docs/BUILDER_QUEUE.md`** — move the last-updated banner.
4. **Do not touch row 21.** It is Designer's next, and its dependency on this row is
   satisfied by the merge, not by an edit.

**Commit:** `docs(queue): mark item 20 shipped`

---

## 7. Copy authored by this plan

> ⛔ **SUPERSEDED 2026-09-06 — §7 is history, not instructions.** The copy gate
> refused both strings below and the escalation was ruled by Designer. The
> authority is now
> [`design-handoffs/export-only-mode/copy.md`](../../design-handoffs/export-only-mode/copy.md)
> **§10** (rendering: [`interactions.md`](../../design-handoffs/export-only-mode/interactions.md)
> **§4b**), and what shipped is §10's text, not §7.1's. Two things changed:
> **no number is printed at all** — the whole-MB rounding made the sentence
> refute itself for the modal near-miss size, and the 100 MB figure is
> documentation §8's probe has not tested — and the recovery **points at
> `📁 Save the files to a folder`** instead of at a shorter recording, which
> `server/app.py:263` had already made unreachable advice. §7.2's first two
> questions are answered by that ruling. Kept unedited because §10.1 and §10.2
> are written against it and are only legible next to what they rejected.

### 7.1 Two strings, both replacing text that is wrong today

| Where | Today | New |
| --- | --- | --- |
| 413 from the track PUT | `That audio file is too big for Yoto (max 5 hours per card).` | `Yoto wouldn’t take “{title}” — it’s bigger than Yoto allows for one track. Yoto’s limit is 100 MB, and this one is {n} MB. If you have a shorter recording of it, try that instead — otherwise tell whoever set Yoto Maker up for you.` |
| 413 from anywhere else | *(same string)* | `Yoto wouldn’t take that — it was too big to send.` |

**Why Planner authors these rather than blocking on Designer.** Item 19's plan set the
precedent — it authored three one-sentence strings *"because nothing in `copy.md` covers
them"* and flagged them for Designer confirmation. These two are a weaker case than
those: they are error strings on a path the user reaches only after a failure, they
replace text that is **factually wrong**, and they change no layout, no element and no
state machine. Leaving *"max 5 hours per card"* in place while waiting for a ruling is
worse than shipping a true sentence that a Designer may later reword.

**Where they borrow from approved copy.** Deliberately, so a Designer pass is a
rubber stamp rather than a rewrite:

- *"bigger than Yoto allows for one track. Yoto's limit is 100 MB"* — §5.9's construction,
  with *"a single track"* shortened to *"one track"* to fit a sentence that already names
  the track.
- *"tell whoever set Yoto Maker up for you"* — `copy.md` §4d's established pattern for
  states the app cannot fix, used verbatim by §5.9 for this exact ceiling.
- **Whole MB, 10⁶** — §5.9's ratified rule, and `overview.md` §8.3's reading of Yoto's
  own figure. `118 MB`, never `118.4 MB`, never MiB.
- **A quoted title, not a numbered file name** — §5.9's `{list}` form is justified by a
  file dialog that does not exist here; §5.3 and §5.5a's quoted-title form is the one
  §5.9 itself points at for naming a single thing in prose.
- **`wouldn’t` / `refused`, not `may refuse`.** §5.9 hedges because it is *predicting*.
  This string runs after Yoto has already said no, so hedging there would be false in
  the other direction.

**What is deliberately absent:** no byte count in developer terms, no format name, no
path, no *"413"*, no *"upload"* as a noun. `MB` and the track title are the only figures.

### 7.2 What a Designer should be asked to confirm (non-blocking)

- The two strings above.
- Whether *"If you have a shorter recording of it, try that instead"* is a recovery she
  can actually perform, or whether it should drop and leave only the
  tell-whoever-set-this-up half.

Neither answer changes any code outside two string literals.

---

## 8. The live probe that settles the number (maintainer, not Builder)

This does not gate this PR. It gates item 21.

**Why it is cheap and safe.** The upload leg and the card-creation leg are separate calls.
`_request_upload_url()` + `_put_audio()` can be run without ever calling
`_create_content()` — the result is an orphaned upload in Yoto's transcode staging and
**no card, no change to any existing card, nothing in the user's library.** That is a
strictly smaller footprint than item 18's live `--apply` run, which was approved.

**The probe:**

1. Make a ~120 MB MP3 locally (`ffmpeg -f lavfi -i sine=frequency=440:duration=5000
   -b:a 192k probe.mp3` is ~120 MB).
2. With a connected account, from a Python REPL: `c = YotoClient(); url, uid =
   c._request_upload_url(); c._put_audio(url, Path("probe.mp3"), title="probe")`.
3. Record: the HTTP status, the response body, and whether `_poll_transcode(uid)` ever
   returns a sha.

**What each outcome means:**

| Outcome | What it settles |
| --- | --- |
| PUT returns 413 (or any 4xx) | The ceiling is real on the API path. Item 21 ships the advisory as specced. Task 3's string is confirmed correct. |
| PUT returns 200 and the transcode poll returns a sha | **The 100 MB figure does not bind the API path.** Item 21 should be **closed unshipped** — an advisory naming a limit that does not apply to the path she is on is a false alarm on the shipped path. ~~Task 3's string … should be reworded to stop naming 100 MB.~~ **Already done, before the probe ran** — `copy.md` §10.2 removed the figure from the shipped string, so **no outcome of this probe requires a copy change on the send path.** Every clause that shipped is entailed by the observed refusal alone; only the number could have been falsified, and it is not printed. |
| PUT 200, transcode never completes | The ceiling binds later and differently. Item 21 needs re-scoping around the transcode timeout message (`client.py:295-299`), not a pre-send advisory. |

**Record the result in `docs/BUILDER_QUEUE.md` item 21's row either way.** This is the
"if a live test disagrees, the test wins" rule with a concrete test attached.

---

## 9. The follow-on row — item 21, filed by the planning PR

Appended, not inserted — the maintainer sets priority. Reproduced here so the plan is
readable on its own; `docs/BUILDER_QUEUE.md` is the live copy.

> **21 · 📋 · The send path never tells her a track is over Yoto's limits before she
> presses Send** — the app knows every track's size the moment it is added, and says
> nothing until a 20-minute upload fails. A `.msg-box info` on step 3, above
> `🚀 Send to Yoto`, naming the per-track and card-level ceilings.
> **Spec:** _needs Designer pass_ · **Plan:** _needs Designer pass, then Planner_ ·
> **Depends on:** 20 (this PR) + a Designer ruling on copy + the live probe in
> [item 20's plan §8](superpowers/plans/2026-09-05-per-track-size-limit.md)
> **Notes:** LOW-MEDIUM, and **may turn out not to ship at all** — §8's probe can
> conclude the ceiling does not bind the API path, in which case an advisory is a false
> alarm on a shipped path and the row closes unshipped. `copy.md` §5.9's approved
> strings **cannot** be reused verbatim: they name *"Yoto's website"*, which is false
> here, and their `{list}` format is justified by a file dialog that does not exist on
> this path (item 20's plan §1.4). Touches `index.html` → **needs a version bump.**

---

## Test Plan

### A. Unit and integration — the suite

| # | Check | Where |
| --- | --- | --- |
| A1 | The audio PUT sends **every byte**, unaltered | `test_put_audio_sends_every_byte_with_an_explicit_content_length` |
| A2 | The PUT sets an explicit `Content-Length` and **never** `Transfer-Encoding: chunked` — the property a pre-signed URL depends on | same |
| A3 | The PUT's method, URL and `Content-Type` are unchanged from `main` | same |
| A4 | The client is handed a **file object, not bytes** — the regression guard against reintroducing `fh.read()` | `test_put_audio_streams_the_file_and_never_materialises_it` |
| A5 | ~~names **100 MB**~~ → **INVERTED by the §10 ruling.** A per-track 413 names the track, prints **no number at all** (no ceiling, no size, no digit), does **not** say *"5 hours"*, and **points at `📁 Save the files to a folder`** | `test_413_on_a_track_upload_uses_the_per_track_message` + `test_track_too_big_names_the_track_and_prints_no_number_at_all` + `test_track_too_big_is_copy_md_10_1_verbatim` |
| A6 | ~~whole MB read as 10⁶~~ → **retired with the number.** Nothing is rounded, so no rounding has to be right | — (subsumed by A5's no-digit assertion) |
| A7 | ~~an unknown size (0) omits the size clause~~ → **unreachable by construction.** `_track_too_big` is no longer given a size, so it cannot print one | `test_track_too_big_is_not_even_given_a_size` |
| A7b | The pointer appears on the track-PUT 413 and on **nothing else** — not 401/403, not 5xx, not a timeout, not the generic 413 (`interactions.md` §4b.1's table) | `test_too_big_never_leaks_out_of_the_413_branch` + `test_an_expired_sign_in_during_a_track_upload_still_says_reconnect` + `test_the_generic_413_is_no_longer_a_dead_end` |
| A7c | *"below"* is true: `#exportRow` is the next **visible** element after `#sendError`, with nothing new between them (`interactions.md` §4b.4's standing condition) | `test_the_save_button_really_is_below_the_send_error` + `test_connect_warn_cannot_be_visible_during_a_send_that_reaches_a_413` + `test_the_pointer_quotes_the_button_label_that_ships` |
| A8 | A 413 from any **other** call site names neither ceiling | `test_413_elsewhere_no_longer_claims_a_ceiling_it_cannot_vouch_for` |
| A9 | 401/403, 5xx and timeout messages are **byte-identical** to `main` | the three pinning tests in Task 1 |
| A10 | `create_card` names the **right** track when the second of two is refused | `test_create_card_names_the_refused_track` |
| A11 | The existing send-path suite is untouched and green | `pytest tests/test_yoto_client.py -q` |
| A12 | Whole suite green | `pytest -q` |

### B. Locally verifiable by Builder

| # | Check | How |
| --- | --- | --- |
| B1 | **A normal card still sends.** The one thing that must not regress | Run the app, add a short MP3, name it, `🚀 Send to Yoto`, confirm the card appears in the Yoto app. This exercises the streamed PUT against the **real** pre-signed URL — the only thing `MockTransport` cannot prove |
| B2 | **A large file still sends, and memory stays flat** | Add a ~200 MB WAV; watch the process's peak RSS during send in Task Manager. Before: a spike of roughly the file size. After: flat |
| B3 | **No served static asset changed** | `git diff --stat main` names no file under `yoto_maker/server/static/` |
| B4 | **The version did not move** | `git diff main -- yoto_maker/__init__.py pyproject.toml` is empty |
| B5 | **Nothing under `yoto_maker/export/` is imported or duplicated** | `grep -rn "export" yoto_maker/yoto/client.py` returns nothing; `grep -n "100_000_000" yoto_maker/yoto/client.py` returns nothing |
| B6 | **`normalize.py` is untouched** | `git diff --stat main` names no `normalize.py` |
| B7 | **No banned word reached user-visible copy** | Read the two new strings against `docs/design-handoffs/README.md`'s list; check both use `’` and not `'` |
| B8 | **The branch really is off `main`** | `git merge-base --is-ancestor main HEAD` succeeds and `git log --oneline main..HEAD` shows only this PR's commits — no item 19 commits |

### C. Not verifiable without a live account — deferred to §8

| # | Check | Owner |
| --- | --- | --- |
| C1 | Whether a >100 MB track is actually refused by the API | Maintainer, §8's probe |
| C2 | Whether the refusal is a 413 or some other status | Maintainer, §8's probe |

**C2 matters and is worth stating plainly:** if the pre-signed storage endpoint refuses
an oversized PUT with a `400` rather than a `413`, Task 3's improved message never fires
and the user gets the generic *"Something went wrong while uploading the audio"*. Task 3
is still strictly better than `main` in that world — it stops naming a wrong ceiling —
but the per-track sentence would be dead code until the real status is known. **Do not
widen the branch to catch 400 on speculation**; a 400 has many other causes and
mapping them all to *"too big"* would be a worse lie than the one being fixed. §8's
probe answers it.

### D. What this PR does not test, and why

- **No test asserts a file is refused before upload**, because nothing in this PR checks
  a file before upload. A test that appeared to do so would be evidence of the §0.2
  decision having been reverted.
- **No UAT of an advisory surface**, because there is no advisory surface (§9).

---

## 10. Deviations, judgement calls and open questions

| # | Call | Why |
| --- | --- | --- |
| 1 | **Scope grew by one item** — `_put_audio`'s memory profile was not in the queue row | It is the same defect on the same file that item 14's ADR fixes on the add side, it is unclaimed by any queue row, and it is the only thing here that is certainly broken independent of Yoto's ceilings (§1.1) |
| 2 | **Scope shrank by one item** — no advisory surface | `copy.md` §5.9 is not verbatim-reusable (§1.4), so it needs Designer; and §8's probe may conclude it should not ship at all |
| 3 | **Two strings authored, not blocked on Designer** | Both replace factually-wrong text on an error path; item 19's plan set the precedent for authoring-and-flagging (§7.1) |
| 4 | **No `MAX_TRACK_BYTES` constant in `client.py`** | A constant implies a comparison. There is no comparison, and its absence is the design (§2) |
| 5 | **No ADR** | The act-vs-advise reasoning is cross-cutting enough to justify one, but ADRs are Architect's artifact. It lives in §0 of this plan, which the queue row links, plus a pointer in the module docstring (Task 5). If a future Architect pass wants it promoted, §0.1–0.2 is the content |
| 6 | **`_track_too_big` is module-private but imported by tests** | Matches `test_yoto_client.py`'s existing use of `_transcoded_format` |

**Nothing here is blocking.** The one thing Builder must not do on its own judgement is
add a size check before upload — see §2 and Task 5.

---

## 11. Success criteria

1. A card that sends today still sends, byte-identically on the wire (A1–A3, B1).
2. Sending a large track no longer holds it in memory (A4, B2).
3. A per-track refusal names the track, names the per-track limit, and never names the
   card-level one (A5, A10).
4. A 413 from any other call site names no ceiling at all (A8).
5. Every non-413 message is unchanged (A9).
6. No static asset, no version bump, no `normalize.py` change, no `export/` coupling
   (B3–B6).
7. Both new strings pass the ban list and use `’` (B7).
8. The reason the send path does not check size is written down where the next reader
   will find it (Task 5).
