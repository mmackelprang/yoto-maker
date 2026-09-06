# Save the files to a folder (export-only mode) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Date:** 2026-09-05
**Author:** Planner
**Queue item:** 19
**Branch:** `feat/save-to-a-folder`
**Ships as:** **v0.1.13.** This PR owns the version bump — see §Global Constraints.
**Type:** feature. New backend package + three routes + a markup block + a client
panel. The signed-in send path is not touched.

**Design basis (approved 2026-09-05):**
[`docs/superpowers/specs/2026-09-05-export-only-mode-design.md`](../specs/2026-09-05-export-only-mode-design.md)
and the handoff package
[`docs/design-handoffs/export-only-mode/`](../../design-handoffs/export-only-mode/)
— `overview.md` (the decisions), `copy.md` (**every user-visible string,
verbatim**), `interactions.md` (markup contract, state machine, focus),
`mockups/`. **`copy.md` is the authority on strings.** A string that does not
appear there is a Polisher finding.

**Goal:** a second, user-chosen way to finish one card: the app writes the
finished audio, the pictures and a self-contained instruction page into
`<Documents>\Yoto Maker\<card name>\`, and the user uploads them by hand on
`my.yotoplay.com`. **It needs no sign-in at all**, which is half the reason it
exists. The existing send path is unchanged.

**Tech stack:** Python 3.11 / dataclasses / FastAPI / the existing `jobs.py`
runner / the existing `normalize_to_mp3` ffmpeg wrapper / Pillow (already a
dependency) / vanilla JS. **No new dependencies. No new CSS. No new tokens.**

**10 tasks, one PR.** §7 of the spec argues why this does not split: the folder
without the sheet is a pile of files and a stuck user; the UI block without the
job has nothing to press; the one-string edit is a correctness fix the feature
itself causes.

---

## Global Constraints

- **Branch first.** `feat/save-to-a-folder`, PR into `main`. This changes source,
  so it never touches `main` directly (global `CLAUDE.md`).
- **This PR bumps `0.1.12` → `0.1.13`, and that is not optional.** It is almost
  entirely `app.js` and `index.html`, and the version string is the asset cache
  key (`index.html`'s `?v=__ASSET_V__`, stamped at `app.py:746`). Without the
  bump an already-running browser keeps serving the old script against the new
  markup — which is queue item 8's bug with a new payload. Bump
  `pyproject.toml:7` **and** `yoto_maker/__init__.py:3`.
- **`styles.css` is not modified. At all.** Acceptance criterion 10: *"If the PR
  touches it, something in §2 was reinterpreted and should come back to
  Designer."* Every element uses `.btn`, `.btn.primary`, `.tiny`, `.progress`,
  `.bar`, `.msg`, `.msg-box` (+ `.err`/`.ok`/`.info`), `.done-actions`,
  `.mono-value` and `.hidden` — all shipped. Task 8 adds a test that asserts this.
- **The send path is not touched.** `#sendBtn`, `#sendProgress`, `#sendError`,
  `#sendDone`, `connectYoto()`, `sendToYoto()`, `POST /api/send`, `YotoClient` —
  none of it changes behaviour. The **one** shared thing this PR extracts is the
  card-construction helper in Task 7, and `send_to_yoto()` must keep producing a
  byte-identical `TrackInput` list afterwards.
- **`POST /api/export` has NO connection check.** It takes the two guards at
  `app.py:634-638` and **not** the one at `app.py:640`. A reviewer who "fixes"
  the missing auth check has deleted the feature. Guarded by a test.
- **`_resolve_icon` is CALLED, never reimplemented.** It is lazy and has a
  filesystem side effect (`make_device_icon` writes `work/icon_<id>.png`), and it
  is the reason a card saved to a folder carries the same pictures as the same
  card sent to Yoto (acceptance criterion 8). Same for the card name and the
  track list: they come out of the shared helper.
- **Export never splits.** `split_audio` already ran at *add* time
  (`app.py:235`), and each part is already its own `Track` with a `(part N)`
  title (`app.py:243`). There is no "splitting…" progress phase. This corrects
  the original brief — spec §4.1.
- **Convert on format; advise on size. Never re-encode an MP3 to shrink it.**
  `{".mp3", ".m4a", ".aac"}` are copied byte-for-byte **even when oversized**;
  everything else becomes a **192 kbps** MP3. That asymmetry is the design
  (spec §2.4), not an oversight. Guarded by two tests.
- **192 kbps is load-bearing arithmetic.** The splitter bounds a track at 50
  minutes; 50 minutes at 192 kbps is ~72 MB, under Yoto's 100 MB per-track cap
  with margin. Anything above ~265 kbps breaks that property (acceptance
  criterion 12). Do not "improve" the bitrate.
- **No Cancel button, and no job cancellation.** `jobs.py` has none; adding it is
  Architect-scoped work (queue item 15 / ADR §3.2) and explicitly out of scope
  (spec §2.8). Do not introduce `#exportCancel`, do not add a `cancelled` state,
  do not touch `jobs.py`.
- **No user-visible string contains** `export`, `directory`, `path`,
  `file format`, `codec`, `transcode` or `metadata`. DOM ids are `#export*`;
  the copy says **save** / **files** / **a folder**. `MP3` on its own is
  permitted and used. Ban list:
  [`docs/design-handoffs/README.md`](../../design-handoffs/README.md). Guarded by
  a test that strips HTML comments first (the new comments *do* say "export").
- **Typographic apostrophes (`’`) in every user-facing string**, matching
  `index.html:264` and `app.js:408`. This includes the Python reason strings.
- **Nothing is ever overwritten, and a failed run leaves no folder behind.**
  ` (2)`, ` (3)` on collision; `shutil.rmtree` on total failure. The string
  *"Nothing was saved, and nothing on this card has changed."* is **true only
  because of that cleanup** — if the ordering ever changes, `copy.md` §5.7 must
  change with it.
- **The instruction sheet is generated from what landed on disk, never from the
  draft.** On a partial run a draft-derived sheet lists files that are not there
  and she uploads a card with a hole in it. The on-screen sentence *"The page in
  the folder lists what's actually there."* is the readable form of this
  invariant.
- **The reveal route takes no path from the browser.** The server remembers the
  last folder it wrote. Even on loopback, handing a caller-supplied string to the
  shell is a foot-gun with no upside, and the UI never needs it (spec §2.7).
- **Tests must never write to the real `Documents`.** Task 1 adds
  `Config.documents_dir`; `tests/conftest.py` **must** set it to a `tmp_path`
  subdirectory in the same edit. Skipping that step makes the suite scribble in
  the maintainer's Documents folder.

---

## Ground truth (verified in the tree — design to these)

| Fact | Where |
| --- | --- |
| `send_to_yoto()` forks above its connection check: guards at 634-638, auth at 640, card built at 643-647 | `yoto_maker/server/app.py:631-661` |
| `TrackInput` is exactly `(audio_path, title, icon_path)` | `yoto_maker/yoto/client.py:49-52` |
| `_resolve_icon(track, draft)` — library icon → card picture → suggested image → bundled `music`; middle two write `work/icon_<id>.png` | `app.py:618-628` |
| The job runner: `update(stage, percent, message)`, result on `job.result`, **exceptions become `job.error = str(exc)` and nothing else** | `yoto_maker/server/jobs.py:45-76` |
| `pollJob(jobId, onProgress)` polls `/api/jobs/{id}` at 500 ms and throws `new Error(job.error)` | `app.js:81-89` |
| The label precedent for an anchor whose `href` a result supplies, with `?t=` | `app.js:2011-2024`, `index.html:222-225` |
| `normalize_to_mp3(input, out_dir, bitrate="192k")` → `(out_dir/<stem>.mp3, AudioInfo)`; `-vn` so `.mp4` loses its video | `audio/normalize.py:155-186` |
| `SUPPORTED_EXT` = `{".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".mp4", ".opus"}` — the app does **not** transcode local files | `sources/audiofile.py:14`, `:26-61` |
| `MAX_TRACK_SECONDS = 3000` (50 min), duration-only | `audio/normalize.py:191` |
| Zero occurrences of `os.startfile` / `explorer` / `xdg-open` / `open -R` anywhere | repo-wide |
| `.msg-box p` / `.msg-box p:last-child` already carry multi-paragraph bodies | `styles.css:257-258` |
| `setMsgBoxContent(box, content)` renders an array as one `<p>` per entry, via `replaceChildren` | `app.js:71-78` |
| Sheet palette: `--bg #f6f4fb`, `--card #fff`, `--ink #241d38`, `--muted #6b6480`, `--accent-dark #5f43b0`, `--radius 16px` | `styles.css:1-23` |
| Current version in the tree | `pyproject.toml:7`, `yoto_maker/__init__.py:3` = `0.1.12` |

---

## The job result contract — pin this before writing the client

`interactions.md` §3.3 step 2: **the panel reconstructs nothing in JS.** Every
number, name, path and list it renders comes from here. Sentences are composed in
`app.js` from these fields (the same division the send path already uses).

```jsonc
{
  "ok": true,
  "folder_name": "Bedtime Stories (2)",     // named in the success sentence
  "folder_path": "C:\\Users\\mark\\OneDrive\\Documents\\Yoto Maker\\Bedtime Stories (2)",
  "saved_count": 4,
  "total_count": 5,
  "files": ["01 - Chapter One.mp3", "…"],   // as written, in order
  "failures": [{"title": "Chapter Four",
                "reason": "We couldn’t read that file — it may be open in another program."}],
  "split_groups": [{"title": "Chapter Eighteen", "parts": 2}],
  "converted": [{"label": "02 - The Sea"}, {"label": "05 - Rain"}],
  "oversize_tracks": [{"label": "09 - Chapter Nine", "title": "Chapter Nine", "size_mb": 118}],
  "card_mb": 604,
  "card_duration_words": "8 hours 40 minutes",
  "card_tracks": 62,
  "over_card_bytes": true,
  "over_card_seconds": true,
  "over_card_tracks": false,
  "sheet_url": "/api/export/sheet.html",    // added by the route, not the runner
  "can_open": true                          // added by the route, not the runner
}
```

**A total failure is not this shape.** It arrives as a job error, so the only
thing that reaches the client is `job.error` — a single string. That is why the
**cause-specific line is composed server-side** (`export/errors.py`) and the
fixed first and third paragraphs are composed client-side: `jobs.py` has no
`reason` field and this PR does not add one. `copy.md` §5.7's three paragraphs
therefore map to *(fixed head)* + `e.message` + *(fixed tail)*.

**A partial failure is NOT a job error.** It is a successful job whose result
carries `failures`. Both boxes render (`interactions.md` §3.6).

---

## File structure

| File | Responsibility | Tasks |
| --- | --- | --- |
| `yoto_maker/config.py` | `resolve_documents_dir()` through the OS + `Config.documents_dir` + `Config.saved_dir` | 1 |
| `tests/conftest.py` | Point `documents_dir` at `tmp_path` — **required, not optional** | 1 |
| `yoto_maker/export/__init__.py` | **New.** The package's public surface | 2 |
| `yoto_maker/export/errors.py` | **New.** `ExportError` + every `REASON_*` string, verbatim from `copy.md` §5.6/§5.7 | 2 |
| `yoto_maker/export/names.py` | **New.** Sanitizing, ` (2)` collisions, `NN - title.ext`, path-length truncation, MB and spoken-duration formatting. Pure | 2 |
| `yoto_maker/export/rules.py` | **New.** `COPY_AS_IS`, `EXPORT_BITRATE`, Yoto's four ceilings, `SavedFile`, `advise()`. Pure | 3 |
| `yoto_maker/export/sheet.py` | **New.** `render_sheet(SheetData) -> str`. Pure — takes bytes, returns a string | 4 |
| `yoto_maker/export/runner.py` | **New.** `export_card(...)` — the orchestration and the only filesystem writer | 5 |
| `yoto_maker/export/reveal.py` | **New.** `reveal_supported()` / `reveal_folder(path)` | 6 |
| `yoto_maker/server/app.py` | `_build_card_inputs()`, `POST /api/export`, `GET /api/export/sheet.html`, `POST /api/export/open`, `config.saved_dir` on `/api/status`, clear the remembered folder on draft reset | 7 |
| `yoto_maker/server/static/index.html` | The `#export*` block, the one edited string, the Settings help row | 8 |
| `yoto_maker/server/static/app.js` | Copy constants, `saveToFolder()`, `renderExportResult()`, wiring, `#startOver` reset, the help row | 9 |
| `tests/test_export.py` | **New.** The bulk of the coverage | 2–7 |
| `tests/test_card_view_markup.py` | Extended: placement, ban list, no-new-CSS | 8, 9 |
| `pyproject.toml`, `yoto_maker/__init__.py` | `0.1.13` | 10 |
| `docs/RELEASE_NOTES.md`, `docs/INSTALL-FOR-MOM.md`, `docs/BUILDER_QUEUE.md` | User-facing entry, the step-3 note, queue bookkeeping | 10 |

**Not modified, on purpose:** `yoto_maker/server/jobs.py` (no cancellation — spec
§2.8), `yoto_maker/audio/normalize.py` (no bitrate or split change),
`yoto_maker/yoto/**` (the send path is untouched),
`yoto_maker/server/static/styles.css` (**zero** rules added or edited).

---

# Task 1: Resolve Documents through the OS, and expose where saved files go

**Files:**
- Modify: `yoto_maker/config.py` — a new resolver above `Config`, one field and
  one property on `Config`.
- Modify: `tests/conftest.py` — point `documents_dir` at `tmp_path`.
- Add: `tests/test_export.py` — first tests.

**Interfaces produced:**
- `resolve_documents_dir() -> Path`
- `Config.documents_dir: Path` (field) and `Config.saved_dir -> Path` (property)

**Why an OS call and not a string join** (spec §2.3): OneDrive redirects
Documents and localized Windows installs rename it. The panel must display the
path actually used, never a reconstructed one — configuration-surface §13.4's
redirect-URL rule, for the same reason.

- [ ] **Step 1: Add the resolver.** In `yoto_maker/config.py`, after
  `_bundle_root()` (line 36) and before `DEFAULT_YOTO_CLIENT_ID`:

```python
# --------------------------------------------------------------------------- #
# Where the user's saved card folders go.
#
# NOT %LOCALAPPDATA%, and NOT work/. "In your Documents, under Yoto Maker" is a
# sentence a person can say, and follow, about a computer that is not in front of
# them — which is the use case that decides this
# (design-handoffs/export-only-mode/overview.md §5.1).
# --------------------------------------------------------------------------- #
SAVED_FOLDER_NAME = "Yoto Maker"

# FOLDERID_Documents. Resolved through the OS, never by joining
# %USERPROFILE%\Documents: OneDrive redirects that folder and localized installs
# rename it, and the one moment this value matters is the moment a guess is wrong.
_FOLDERID_DOCUMENTS = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"


def _windows_documents_dir() -> Path | None:
    """Ask Windows where Documents actually is. None if the call fails.

    ctypes + shell32 is stdlib, so a PyInstaller-frozen build needs no hook.
    Every failure path returns None so the caller can fall back rather than 500.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        ole32 = ctypes.windll.ole32
        shell32 = ctypes.windll.shell32
        ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(_GUID)]
        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]

        guid = _GUID()
        if ole32.CLSIDFromString(_FOLDERID_DOCUMENTS, ctypes.byref(guid)) != 0:
            return None
        out = ctypes.c_wchar_p()
        # KF_FLAG_DEFAULT = 0; NULL token = the calling user.
        if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
            return None
        try:
            value = out.value
        finally:
            ole32.CoTaskMemFree(out)
        return Path(value) if value else None
    except Exception:  # noqa: BLE001 - any ctypes failure falls back below
        return None


def resolve_documents_dir() -> Path:
    """The user's Documents folder.

    ``YOTO_DOCUMENTS_DIR`` wins when set. It exists so UAT can point a run at a
    scratch folder, and so a redirected-Documents machine can be simulated
    without owning one.
    """
    env = os.environ.get("YOTO_DOCUMENTS_DIR")
    if env and env.strip():
        return Path(env.strip())
    if sys.platform.startswith("win"):
        found = _windows_documents_dir()
        if found:
            return found
    return Path.home() / "Documents"
```

- [ ] **Step 2: Add the field and the property.** In `Config`, after
  `bundle_root` (line 191):

```python
    documents_dir: Path = field(default_factory=resolve_documents_dir)
```

and, in the derived-paths block after `work_dir` (line 205):

```python
    @property
    def saved_dir(self) -> Path:
        """Where the user's saved card folders go: <Documents>\\Yoto Maker.

        Deliberately NOT created by ensure_dirs(). The app does not put a folder
        in someone's Documents until they actually ask it to save something.
        """
        return self.documents_dir / SAVED_FOLDER_NAME
```

**Do not add `saved_dir` to `ensure_dirs()`.**

- [ ] **Step 3: Keep the suite out of the real Documents.** In
  `tests/conftest.py`, inside `temp_config`, add one kwarg to the `Config(...)`
  call:

```python
    cfg = Config(
        data_dir=tmp_path / "data",
        bundle_root=REPO_ROOT,
        documents_dir=tmp_path / "Documents",   # never the real one
        yoto_client_id="test_client_id",
        host="127.0.0.1",
        port=8799,
    )
```

- [ ] **Step 4: Tests.** Create `tests/test_export.py` with:

```python
"""Save-to-a-folder mode.

Design: docs/design-handoffs/export-only-mode/. Strings: that package's copy.md.
Every test here runs against tmp_path — conftest points Config.documents_dir at
a temp directory precisely so the suite never writes to a real Documents folder.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from yoto_maker.config import get_config, resolve_documents_dir


def test_saved_dir_hangs_off_documents_and_is_not_precreated(temp_config):
    cfg = get_config()
    assert cfg.saved_dir == cfg.documents_dir / "Yoto Maker"
    assert not cfg.saved_dir.exists(), "ensure_dirs() must not create it"


def test_documents_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("YOTO_DOCUMENTS_DIR", str(tmp_path / "Docs"))
    assert resolve_documents_dir() == tmp_path / "Docs"


def test_documents_resolution_never_raises(monkeypatch):
    monkeypatch.delenv("YOTO_DOCUMENTS_DIR", raising=False)
    assert isinstance(resolve_documents_dir(), Path)
```

---

# Task 2: `export/errors.py` and `export/names.py` — the reason strings and the naming rules

**Files:**
- Add: `yoto_maker/export/__init__.py`, `yoto_maker/export/errors.py`,
  `yoto_maker/export/names.py`
- Modify: `tests/test_export.py`

**Interfaces produced:**
- `ExportError`, `NameTooLongError`, `REASON_*`
- `sanitize_component()`, `number_width()`, `track_filename()`, `unique_dir()`,
  `megabytes()`, `duration_words()`, `date_words()`

- [ ] **Step 1: `yoto_maker/export/errors.py`.** Every string is `copy.md`
  §5.6/§5.7 verbatim, with typographic apostrophes.

```python
"""Failure vocabulary for saving a card to a folder.

These live in their own module because both the runner and the reveal route
raise them, and because a total failure reaches the browser as a bare string:
jobs.py captures only ``str(exc)`` (jobs.py:70-73) and this PR deliberately does
not extend it. So the CAUSE-SPECIFIC sentence is composed here, server-side,
where the cause is known; app.js supplies the fixed first and third paragraphs of
copy.md §5.7 around it.
"""
from __future__ import annotations


class ExportError(RuntimeError):
    """A user-friendly save failure. The message is shown verbatim."""


class NameTooLongError(ValueError):
    """A file or folder name cannot be made to fit Windows' path limit."""


# --- copy.md §5.7, the {reason} table -------------------------------------- #
REASON_NO_SPACE = "This computer looks like it’s out of space."
REASON_PERMISSION = "Windows wouldn’t let Yoto Maker write to your Documents folder."
REASON_TOO_LONG = (
    "The card name is very long, and that made the file names too long for "
    "Windows. Try a shorter name in step 2."
)
REASON_GENERIC = "Something went wrong while writing the files."

# --- copy.md §5.6, the per-track {reason} ---------------------------------- #
# Both are EXISTING in-tree strings, reused rather than reinvented:
#   sources/audiofile.py:46  and  audio/normalize.py:183-185 (its first sentence
#   pair only — the "Technical detail: …" tail is a developer string and must
#   never reach this panel).
REASON_UNREADABLE = "We couldn’t read that file — it may be open in another program."
REASON_CONVERT_FAILED = "We couldn’t convert that audio. It may be an unusual or damaged file."

# --- the reveal button's own runtime failure (interactions.md §4.4) --------- #
REASON_NOTHING_SAVED = "There’s nothing saved to open yet."
REASON_CANNOT_OPEN = "Yoto Maker couldn’t open the folder."
```

- [ ] **Step 2: `yoto_maker/export/names.py`.**

```python
"""Naming rules for a saved card folder.

Pure, except for one directory probe when resolving a collision. Everything here
exists to keep two properties true:

  * **Filename sort equals play order.** That is the only ordering mechanism a
    web upload form gives us, and it survives sorting by name, by selection order
    and by dragging (overview.md §5.3a).
  * **A long name is truncated, never dropped, and the numbering is never
    disturbed** (overview.md §5.2).
"""
from __future__ import annotations

import re
from itertools import count
from pathlib import Path

from .errors import NameTooLongError

# Characters Windows forbids in a name, plus control characters.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Reserved device names. "CON.mp3" is still CON as far as Windows is concerned.
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# MAX_PATH is 260 *including* the terminating NUL. Sit under it with a margin
# rather than on it — the folder may later be copied one level deeper.
MAX_PATH_CHARS = 255

# Room a folder must leave for the longest plausible entry it will hold
# ("Track pictures\NNN - <at least one character>.png").
FOLDER_HEADROOM = 40

# Both fallbacks are strings this app already uses, so a degenerate name produces
# familiar words rather than a new invention.
FALLBACK_CARD_NAME = "My Yoto Card"    # app.py:679
FALLBACK_TRACK_TITLE = "Untitled"      # draft.py:58


def sanitize_component(name: str, *, fallback: str) -> str:
    """One path component, safe on Windows. Never empty."""
    cleaned = _ILLEGAL.sub("", name or "").strip()
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].upper() in _RESERVED:
        cleaned = f"{cleaned}_"
    return cleaned


def number_width(total: int) -> int:
    """Two digits, widening past 99 so the sort never breaks (overview.md §5.3a).

    It matches the ``key`` the API path already writes (models.py:31), so a card
    saved to a folder and the same card sent to Yoto number their tracks the same
    way.
    """
    return max(2, len(str(max(total, 1))))


def track_filename(index: int, total: int, title: str, ext: str, *, folder: Path) -> str:
    """``NN - <title><ext>``, truncated to fit under MAX_PATH_CHARS.

    The ``NN - `` prefix is what stops two titles that truncate to the same text
    from colliding — the number differs, so the names differ.
    """
    prefix = f"{index:0{number_width(total)}d} - "
    safe = sanitize_component(title, fallback=FALLBACK_TRACK_TITLE)
    room = MAX_PATH_CHARS - len(str(folder)) - 1 - len(prefix) - len(ext)
    if room < 1:
        raise NameTooLongError(str(folder))
    if len(safe) > room:
        safe = safe[:room].rstrip(". ") or FALLBACK_TRACK_TITLE[:room]
    return f"{prefix}{safe}{ext}"


def unique_dir(root: Path, name: str) -> Path:
    """``root/name``, or ``name (2)``, ``name (3)``… if that is taken.

    The convention Windows itself uses when you copy a file, so it needs no
    explanation. **Nothing is ever overwritten** — she may be halfway through
    uploading the previous copy (overview.md §5.2).
    """
    candidate = root / name
    if not candidate.exists():
        _guard_length(candidate)
        return candidate
    for n in count(2):
        candidate = root / f"{name} ({n})"
        if not candidate.exists():
            _guard_length(candidate)
            return candidate
    raise AssertionError("unreachable")  # pragma: no cover


def _guard_length(folder: Path) -> None:
    if len(str(folder)) > MAX_PATH_CHARS - FOLDER_HEADROOM:
        raise NameTooLongError(str(folder))


def megabytes(size_bytes: int) -> int:
    """Whole MB, read as 10^6 — the conservative reading (overview.md §8.3)."""
    return int(round(size_bytes / 1_000_000))


def duration_words(seconds: float) -> str:
    """``43 minutes`` / ``1 hour`` / ``8 hours 40 minutes``.

    The spoken form, for the sheet's header and the card-ceiling note. The app's
    existing _fmt_duration() (draft.py:106) gives ``8:40:00``, which is a clock
    reading rather than a sentence.
    """
    total = int(round(max(seconds, 0)))
    hours, rest = divmod(total, 3600)
    minutes = rest // 60
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour" if hours == 1 else f"{hours} hours")
    if minutes or not hours:
        parts.append(f"{minutes} minute" if minutes == 1 else f"{minutes} minutes")
    return " ".join(parts)


# Spelled out rather than strftime("%B"): %B is LOCALE-DEPENDENT and would print
# a German month on a German Windows inside an otherwise-English page.
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def date_words(d) -> str:
    """``5 September 2026`` — never a numeric format that means two things."""
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"
```

- [ ] **Step 3: `yoto_maker/export/__init__.py`.** Minimal for now — it must not
  import `.runner` or `.reveal`, which do not exist until Tasks 5 and 6, or the
  suite stops collecting between tasks. **Task 6 replaces this file with its
  final form.**

```python
"""Saving a finished card to a folder the user uploads herself.

Design: docs/design-handoffs/export-only-mode/. The package is named for the
operation; **no string it produces for a user contains the word "export"** — the
verb is *save*, the noun is *files*, the destination is *a folder*.
"""
from __future__ import annotations

from .errors import ExportError, NameTooLongError

__all__ = ["ExportError", "NameTooLongError"]
```

- [ ] **Step 4: Tests.** Append to `tests/test_export.py`:

```python
from datetime import date

from yoto_maker.export.errors import NameTooLongError
from yoto_maker.export import names


def test_sanitize_strips_windows_illegals_and_never_returns_empty():
    assert names.sanitize_component('a/b\\c:d*e?f"g<h>i|j', fallback="X") == "abcdefghij"
    assert names.sanitize_component("   ", fallback="X") == "X"
    assert names.sanitize_component("Bedtime...", fallback="X") == "Bedtime"
    assert names.sanitize_component("CON", fallback="X") == "CON_"


def test_numbering_is_two_digits_and_widens_past_99():
    assert names.number_width(5) == 2
    assert names.number_width(99) == 2
    assert names.number_width(100) == 3
    assert names.number_width(101) == 3


def test_filename_sort_equals_play_order_including_split_parts(tmp_path):
    titles = ["Chapter One", "Chapter Eighteen (part 1)", "Chapter Eighteen (part 2)", "Zebra"]
    made = [
        names.track_filename(i, len(titles), t, ".mp3", folder=tmp_path)
        for i, t in enumerate(titles, start=1)
    ]
    assert sorted(made) == made


def test_a_long_title_is_truncated_never_dropped_and_the_number_survives(tmp_path):
    name = names.track_filename(7, 20, "T" * 400, ".mp3", folder=tmp_path)
    assert name.startswith("07 - ")
    assert name.endswith(".mp3")
    assert len(str(tmp_path / name)) <= names.MAX_PATH_CHARS


def test_two_titles_that_truncate_identically_still_differ(tmp_path):
    a = names.track_filename(1, 2, "T" * 400, ".mp3", folder=tmp_path)
    b = names.track_filename(2, 2, "T" * 400, ".mp3", folder=tmp_path)
    assert a != b


def test_an_impossible_path_raises_rather_than_writing_something_wrong(tmp_path):
    deep = tmp_path / ("d" * 240)
    with pytest.raises(NameTooLongError):
        names.track_filename(1, 1, "Chapter One", ".mp3", folder=deep)


def test_collisions_get_the_windows_convention_and_never_overwrite(tmp_path):
    (tmp_path / "Bedtime Stories").mkdir()
    assert names.unique_dir(tmp_path, "Bedtime Stories").name == "Bedtime Stories (2)"
    (tmp_path / "Bedtime Stories (2)").mkdir()
    assert names.unique_dir(tmp_path, "Bedtime Stories").name == "Bedtime Stories (3)"


def test_spoken_formats():
    assert names.duration_words(43 * 60) == "43 minutes"
    assert names.duration_words(3600) == "1 hour"
    assert names.duration_words(8 * 3600 + 40 * 60) == "8 hours 40 minutes"
    assert names.duration_words(0) == "0 minutes"
    assert names.megabytes(118_000_000) == 118
    assert names.date_words(date(2026, 9, 5)) == "5 September 2026"
```

---

# Task 3: `export/rules.py` — what Yoto takes, and what the app does about it

**Files:**
- Add: `yoto_maker/export/rules.py`
- Modify: `tests/test_export.py`

**Interfaces produced:**
- `COPY_AS_IS`, `EXPORT_BITRATE`, `MAX_TRACK_BYTES`, `MAX_CARD_BYTES`,
  `MAX_CARD_SECONDS`, `MAX_CARD_TRACKS`
- `needs_conversion(path)`, `output_suffix(path)`
- `SavedFile`, `SplitGroup`, `Advisories`, `advise(files)`, `split_groups(files)`

`SavedFile` lives here rather than in the runner because it is the vocabulary the
rules, the sheet and the runner all speak, and putting it in the runner would
make `sheet.py` import the orchestrator.

- [ ] **Step 1: Write the module.**

```python
"""What Yoto's website will and won't take, and what the app does about it.

**The app ACTS on format and ADVISES on size** (overview.md §8.6), and that split
is a decision rather than an inconsistency. A wrong format is certainly refused
and a needless re-encode is the cheap failure; a size limit is a third party's
current policy that the app cannot verify and cannot learn has changed, and
acting wrongly on it would quietly make her audio worse.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .names import megabytes

# Yoto's product FAQ, its uploader's own error string, and a third source all
# name exactly these three.
#
# ⚠ PROVENANCE: DOCUMENTATION, NOT TESTED BEHAVIOUR (overview.md §8.2's box).
# Nothing here may be cited as a measured fact, and if a live upload ever
# disagrees, the test wins. Do NOT widen this set from Yoto's card-content schema
# `format` enum — that enum is track metadata on a card object and describes what
# a card can REFERENCE, not what the uploader will INGEST (overview.md §8.8).
COPY_AS_IS = {".mp3", ".m4a", ".aac"}

# 192 kbps is arithmetic, not taste. split_audio bounds a track at 50 minutes
# (normalize.py:191); 50 minutes at 192 kbps is ~72 MB, comfortably under the
# 100 MB per-track cap below. Anything above about 265 kbps breaks that property
# (spec acceptance criterion 12). It is also already the app's YouTube bitrate
# (sources/youtube.py:44).
EXPORT_BITRATE = "192k"

# support.yotoplay.com, published 2026-07-20. MB is read as 10^6 throughout.
MAX_TRACK_BYTES = 100_000_000
MAX_CARD_BYTES = 500_000_000
MAX_CARD_SECONDS = 5 * 60 * 60
MAX_CARD_TRACKS = 100

_PART_SUFFIX = re.compile(r"^(?P<base>.+?)\s\(part\s(?P<n>\d+)\)$")


def needs_conversion(source: Path | str) -> bool:
    """True when the website would refuse this file's type as it stands.

    Note what this does NOT do: it never returns True because a file is large.
    An oversized .mp3 is copied untouched and advised about — overview.md §8.6.
    """
    return Path(source).suffix.lower() not in COPY_AS_IS


def output_suffix(source: Path | str) -> str:
    return ".mp3" if needs_conversion(source) else Path(source).suffix.lower()


@dataclass
class SavedFile:
    """One file as it was actually written to the folder."""

    index: int
    name: str            # "01 - Chapter One.mp3"
    title: str           # the track title, unsanitized
    size_bytes: int
    duration_s: float
    converted: bool
    icon_path: Path | None = None

    @property
    def label(self) -> str:
        """``01 - Chapter One`` — the name without its extension, for a list."""
        return self.name.rsplit(".", 1)[0]


@dataclass
class SplitGroup:
    title: str           # the base title, with "(part N)" removed
    parts: int


@dataclass
class Advisories:
    """Paragraphs 3-5 of overview.md §10.3, as facts rather than sentences.

    Advisory, never blocking. The folder is complete and both buttons are live
    whatever these say.
    """

    oversize: list[SavedFile] = field(default_factory=list)
    card_bytes: int = 0
    card_seconds: float = 0.0
    card_tracks: int = 0

    @property
    def over_card_bytes(self) -> bool:
        return self.card_bytes > MAX_CARD_BYTES

    @property
    def over_card_seconds(self) -> bool:
        return self.card_seconds > MAX_CARD_SECONDS

    @property
    def over_card_tracks(self) -> bool:
        return self.card_tracks > MAX_CARD_TRACKS

    @property
    def any_ceiling(self) -> bool:
        return self.over_card_bytes or self.over_card_seconds or self.over_card_tracks

    @property
    def anything_over(self) -> bool:
        return bool(self.oversize) or self.any_ceiling


def advise(files: list[SavedFile]) -> Advisories:
    """Measure the ceilings FROM THE FILES AS WRITTEN — after any conversion.

    Testing the sources instead would report a breach the save itself had just
    fixed: a 529 MB WAV becomes a ~72 MB MP3 (spec §3.3).
    """
    return Advisories(
        oversize=[f for f in files if f.size_bytes > MAX_TRACK_BYTES],
        card_bytes=sum(f.size_bytes for f in files),
        card_seconds=sum(f.duration_s for f in files),
        card_tracks=len(files),
    )


def split_groups(files: list[SavedFile]) -> list[SplitGroup]:
    """Which tracks arrived already split into ``(part N)`` pieces.

    Export never splits anything — split_audio ran at add time (app.py:235). This
    only reports what the draft already held, so the panel and the sheet can tell
    her why she is looking at two files where she added one.
    """
    counts: dict[str, int] = {}
    order: list[str] = []
    for f in files:
        m = _PART_SUFFIX.match(f.title)
        if not m:
            continue
        base = m.group("base")
        if base not in counts:
            order.append(base)
        counts[base] = counts.get(base, 0) + 1
    return [SplitGroup(title=b, parts=counts[b]) for b in order if counts[b] > 1]


def size_mb(f: SavedFile) -> int:
    return megabytes(f.size_bytes)
```

- [ ] **Step 2: Tests.** Append to `tests/test_export.py`:

```python
from yoto_maker.export import rules


def test_the_copy_as_is_set_is_exactly_the_three_documented_types():
    assert rules.COPY_AS_IS == {".mp3", ".m4a", ".aac"}


def test_bitrate_keeps_a_50_minute_track_under_the_100_mb_cap():
    """Acceptance criterion 12. 192 kbps * 3000 s = ~72 MB; ~265 kbps breaks it."""
    kbps = int(rules.EXPORT_BITRATE.rstrip("k"))
    assert kbps * 1000 / 8 * 3000 < rules.MAX_TRACK_BYTES


@pytest.mark.parametrize("ext", [".mp3", ".m4a", ".aac", ".MP3", ".M4A"])
def test_the_copy_as_is_set_is_never_converted(ext):
    assert rules.needs_conversion(Path(f"x{ext}")) is False
    assert rules.output_suffix(Path(f"x{ext}")) == ext.lower()


@pytest.mark.parametrize("ext", [".wav", ".flac", ".ogg", ".opus", ".mp4"])
def test_everything_else_becomes_an_mp3(ext):
    assert rules.needs_conversion(Path(f"x{ext}")) is True
    assert rules.output_suffix(Path(f"x{ext}")) == ".mp3"


def test_an_oversized_mp3_is_still_never_converted():
    """overview.md §8.6's asymmetry, stated as a test so nobody 'fixes' it.

    The app acts on format and advises on size. A 320 kbps 50-minute MP3 is
    ~120 MB and is copied untouched.
    """
    assert rules.needs_conversion(Path("huge.mp3")) is False


def _f(i, name, size=1, dur=1.0, conv=False, title=None):
    return rules.SavedFile(index=i, name=name, title=title or name, size_bytes=size,
                           duration_s=dur, converted=conv)


def test_advisories_measure_the_written_files_and_never_block():
    files = [_f(1, "01 - A.mp3", size=118_000_000), _f(2, "02 - B.mp3", size=400_000_000)]
    a = rules.advise(files)
    assert [f.name for f in a.oversize] == ["01 - A.mp3"]
    assert a.over_card_bytes is True
    assert a.over_card_tracks is False


def test_split_groups_report_only_real_multi_part_tracks():
    files = [
        _f(1, "01 - Ch One.mp3", title="Ch One"),
        _f(2, "02 - Ch Two (part 1).mp3", title="Ch Two (part 1)"),
        _f(3, "03 - Ch Two (part 2).mp3", title="Ch Two (part 2)"),
    ]
    groups = rules.split_groups(files)
    assert [(g.title, g.parts) for g in groups] == [("Ch Two", 2)]
```

---

# Task 4: `export/sheet.py` — `What to do next.html`

**Files:**
- Add: `yoto_maker/export/sheet.py`
- Modify: `tests/test_export.py`

**Interfaces produced:** `SheetData`, `render_sheet(SheetData) -> str`

**This is the feature** (spec §2.6). A folder of correctly named files is not the
deliverable; a user who ends up with a working card is. Four hard requirements,
all of them tested:

1. **Generated from what landed, never from the draft.** `SheetData.files` is the
   runner's list of successes and nothing else.
2. **Self-contained.** Inline `<style>`, no web font, no script, and the card
   picture **embedded as a data URI**, not linked — a relative `<img>` works from
   the folder and breaks when the same file is served over `http://`.
3. **Her actual card name, track titles and file names, in order.**
4. **It ends at tapping the blank card in the Yoto app**, never at "press Save on
   the website". Step 6 is not conditional and must never be dropped.

Copy is `copy.md` §6, verbatim. Layout is
`mockups/instruction-sheet.md`.

- [ ] **Step 1: Write the module.**

```python
"""``What to do next.html`` — the page that goes in the folder.

One file, one rendering, both routes: the same bytes are written into the folder
and served by GET /api/export/sheet.html, so the two can never drift
(overview.md §6.3).

Pure. It takes already-read bytes and returns a string; the runner does the I/O.
"""
from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field

from .names import duration_words
from .rules import Advisories, SavedFile, SplitGroup

_STYLE = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#f6f4fb;color:#241d38;
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;
  font-size:17px;line-height:1.5}
.wrap{max-width:720px;margin:0 auto;padding:28px 18px 64px}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:22px;margin:0 0 4px}
h3{font-size:18px;margin:0 0 10px}
.rule{height:1px;background:#e3ddf3;margin:14px 0 22px}
.muted{color:#6b6480}
.meta{color:#6b6480;font-size:15px;margin:0}
.lede{margin:0 0 22px}
.head{display:flex;gap:16px;align-items:center}
.cover{width:180px;height:180px;object-fit:cover;border-radius:16px;flex:0 0 auto}
.card{background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(90,60,160,.10);
  padding:20px 22px;margin:0 0 18px}
.card p:last-child{margin-bottom:0}
a{color:#5f43b0}
.files{font-family:Consolas,"Cascadia Mono","Courier New",monospace;font-size:14px;
  background:#f6f4fb;border-radius:12px;padding:14px 16px;margin:14px 0;
  white-space:pre-wrap;word-break:break-all}
.name{font-size:22px;font-weight:600;margin:6px 0 12px}
.notice{background:#fdeaea;color:#c62828;border-radius:12px;padding:14px 16px;margin:0 0 18px}
ul{margin:0;padding-left:20px}
li{margin-bottom:10px}
li:last-child{margin-bottom:0}
.foot{color:#6b6480;font-size:14px;margin-top:22px}
@media print{
  body{background:#fff}
  .wrap{padding:0}
  .card{box-shadow:none;border:1px solid #e3ddf3;break-inside:avoid}
  .notice{border:1px solid #c62828}
}
"""


@dataclass
class SheetData:
    card_name: str
    files: list[SavedFile]
    failures: list[str]                      # titles that did not make it
    advisories: Advisories
    split: list[SplitGroup] = field(default_factory=list)
    picture_png: bytes | None = None
    has_card_picture_file: bool = False
    version: str = ""
    date_label: str = ""

    @property
    def converted(self) -> list[SavedFile]:
        return [f for f in self.files if f.converted]


def render_sheet(d: SheetData) -> str:
    e = html.escape
    out: list[str] = []
    out.append("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    out.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    out.append(f"<title>What to do next — {e(d.card_name)}</title>")
    out.append(f"<style>{_STYLE}</style></head><body><div class=\"wrap\">")

    out.append("<h1>What to do next</h1><div class=\"rule\"></div>")

    # --- the missing-track notice, above everything (copy.md §6.8) ---------- #
    if d.failures:
        out.append(_missing_notice(d.failures))

    # --- head: picture, card name, the REAL counts (copy.md §6.1) ---------- #
    out.append('<div class="head">')
    if d.picture_png:
        uri = base64.b64encode(d.picture_png).decode("ascii")
        out.append(f'<img class="cover" alt="" src="data:image/png;base64,{uri}">')
    total_s = sum(f.duration_s for f in d.files)
    noun = "track" if len(d.files) == 1 else "tracks"
    out.append("<div>")
    out.append(f"<h2>{e(d.card_name)}</h2>")
    out.append(f'<p class="meta">{len(d.files)} {noun} · {e(duration_words(total_s))}</p>')
    out.append("</div></div>")

    out.append(
        '<p class="lede">Everything for your card is in this folder. Here’s how to '
        "put it on your Yoto — it takes about five minutes, and there’s nothing "
        "here you can break.</p>"
    )

    # --- 1 ------------------------------------------------------------------ #
    out.append(
        '<div class="card"><h3>1. Open Yoto’s website</h3>'
        '<p>Go to <a href="https://my.yotoplay.com">my.yotoplay.com</a> and sign in '
        "with your normal Yoto email and password — the same one you use in the "
        "Yoto app on your phone.</p>"
        "<p>Click <strong>Make Your Own</strong>, then start a new card.</p></div>"
    )

    # --- 2 ------------------------------------------------------------------ #
    out.append(
        '<div class="card"><h3>2. Give it this name</h3>'
        f'<p class="name">{e(d.card_name)}</p>'
        "<p>It doesn’t have to match — but it’s easier if your card, your label "
        "and this folder all say the same thing.</p></div>"
    )

    # --- 3 ------------------------------------------------------------------ #
    out.append('<div class="card"><h3>3. Add the audio files</h3>')
    out.append(
        "<p>Add these files from this folder. <strong>Pick them all at once</strong> "
        "— they’re numbered so they stay in the right order.</p>"
    )
    if d.split:
        out.append(
            "<p>One of your tracks was too long for a Yoto card, so it’s in more "
            "than one piece. That’s normal — add all the pieces and they’ll play "
            "one after the other.</p>"
        )
    if d.converted:
        out.append(
            "<p>Some of these are MP3 copies that Yoto Maker made, because Yoto’s "
            "website is fussier about this than the app is. They’re the same "
            "audio.</p>"
        )
    if d.advisories.anything_over:
        out.append(
            "<p>One of these is bigger than Yoto usually allows on a card. If the "
            "website refuses it, that’s why — the numbers are at the bottom of "
            "this page.</p>"
        )
    listing = "\n".join(e(f.name) for f in d.files)
    out.append(f'<div class="files">{listing}</div>')
    out.append(
        "<p>If you add them one at a time, add them in number order — 01 first, "
        "then 02, and so on.</p></div>"
    )

    # --- 4: omitted entirely when there is no picture (mockup §5) ----------- #
    if d.has_card_picture_file:
        out.append(
            '<div class="card"><h3>4. Add the picture <span class="muted">(if you '
            'want one)</span></h3>'
            "<p><strong>Card picture.png</strong>, in this folder, is the picture "
            "from your card. Add it wherever the website asks for a picture.</p>"
            "</div>"
        )

    # --- the little pictures: ALWAYS, and true under both answers to the ---- #
    # --- open question about per-track pictures (overview.md §9.2) ---------- #
    out.append(
        '<div class="card"><h3>The little pictures on the Yoto screen</h3>'
        "<p>There’s a folder here called <strong>Track pictures</strong>, with a "
        "small picture for each track — the ones that show on the Yoto player’s "
        "screen. They’re named to match the audio files.</p>"
        "<p>If Yoto’s website asks you for a picture for each track, they’re in "
        "there. If it doesn’t ask, you don’t need them.</p></div>"
    )

    # --- 5 and 6. STEP 6 IS NEVER CONDITIONAL AND MUST NEVER BE DROPPED. ---- #
    out.append('<div class="card"><h3>5. Save it on the website</h3></div>')
    out.append(
        '<div class="card"><h3>6. Put it on a card</h3>'
        "<p>Open the Yoto app on your phone, tap a blank <strong>Make Your Own</strong> "
        "card to link it, and press play. 🎶</p>"
        "<p>This last bit is a Yoto step — no app can do it for you, and it’s the "
        "same whether you upload by hand or send straight from Yoto Maker.</p>"
        "</div>"
    )

    # --- footer: the ONE place Yoto's limits are written down --------------- #
    out.append('<div class="rule"></div><h3>If something doesn’t work</h3><ul>')
    out.append(
        "<li><strong>The website won’t take one of the files.</strong> Tell whoever "
        "set Yoto Maker up for you which file it was — that’s the useful thing to "
        "say.</li>"
    )
    out.append(
        "<li><strong>The website says something is too big, or won’t take them "
        "all.</strong> Yoto allows <strong>100 MB and an hour</strong> for any one "
        "track, and <strong>500 MB, five hours and 100 tracks</strong> for a whole "
        "card. If you’ve gone over, make two shorter cards instead of one.</li>"
    )
    out.append(
        "<li><strong>The tracks came out in the wrong order.</strong> Remove them "
        "and add them again, picking them all at once, or drag them into number "
        "order on the website.</li>"
    )
    out.append(
        "<li><strong>You can’t find the folder.</strong> It’s in your "
        "<strong>Documents</strong>, in a folder called <strong>Yoto Maker</strong>.</li>"
    )
    out.append("</ul>")
    out.append(
        f'<p class="foot">Made by Yoto Maker {e(d.version)} on {e(d.date_label)}. '
        "Not affiliated with Yoto.</p>"
    )

    out.append("</div></body></html>")
    return "".join(out)


def _missing_notice(titles: list[str]) -> str:
    e = html.escape
    if len(titles) == 1:
        head = "One of your tracks isn’t here."
        body = (
            f"Yoto Maker couldn’t save <strong>“{e(titles[0])}”</strong>, so it isn’t "
            "in this folder and isn’t in the list below."
        )
    else:
        head = f"{len(titles)} of your tracks aren’t here."
        listed = ", ".join(f"“{e(t)}”" for t in titles)
        body = (
            f"Yoto Maker couldn’t save <strong>{listed}</strong>, so they aren’t in "
            "this folder and aren’t in the list below."
        )
    return (
        f'<div class="notice"><p><strong>⚠️ {head}</strong></p><p>{body} If you want '
        "it on the card, go back to Yoto Maker and try again.</p></div>"
    )
```

- [ ] **Step 2: Tests.** Append to `tests/test_export.py`:

```python
from yoto_maker.export import sheet as sheet_mod


def _sheet(files, failures=(), picture=None, split=(), version="0.1.13"):
    return sheet_mod.SheetData(
        card_name="Bedtime Stories",
        files=list(files),
        failures=list(failures),
        advisories=rules.advise(list(files)),
        split=list(split),
        picture_png=picture,
        has_card_picture_file=picture is not None,
        version=version,
        date_label="5 September 2026",
    )


def test_the_sheet_lists_her_actual_files_in_order():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3"), _f(2, "02 - B.mp3")]))
    assert html_out.index("01 - A.mp3") < html_out.index("02 - B.mp3")
    assert "Bedtime Stories" in html_out


def test_the_sheet_is_self_contained():
    """No external request, ever. DESIGN.md §8 — the app makes none anywhere."""
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")], picture=b"\x89PNG-fake"))
    assert "<script" not in html_out.lower()
    assert "<link" not in html_out.lower()
    assert "data:image/png;base64," in html_out
    # The ONLY absolute URL on the page is the one she is meant to click.
    for token in ("http://", "https://"):
        assert html_out.count(token) == html_out.count("https://my.yotoplay.com")


def test_step_6_is_always_present():
    """Omitting it leaves a correct upload and a card that does nothing."""
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "6. Put it on a card" in html_out
    assert "tap a blank" in html_out


def test_the_picture_step_is_omitted_entirely_when_there_is_no_picture():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "Card picture.png" not in html_out
    assert "4. Add the picture" not in html_out


def test_a_partial_run_names_the_missing_track_and_counts_only_what_landed():
    files = [_f(1, "01 - A.mp3"), _f(2, "02 - B.mp3")]
    html_out = sheet_mod.render_sheet(_sheet(files, failures=["Chapter Four"]))
    assert "isn’t here" in html_out
    assert "Chapter Four" in html_out
    assert "2 tracks" in html_out
    assert html_out.index("isn’t here") < html_out.index("Bedtime Stories")


def test_titles_are_escaped():
    files = [rules.SavedFile(index=1, name="01 - x.mp3", title="<b>x</b>",
                             size_bytes=1, duration_s=1, converted=False)]
    data = _sheet(files)
    data.card_name = "<script>alert(1)</script>"
    html_out = sheet_mod.render_sheet(data)
    assert "<script>alert(1)" not in html_out
    assert "&lt;script&gt;" in html_out


def test_the_size_bullet_is_always_shown_even_for_a_small_card():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "100 MB and an hour" in html_out
    assert "500 MB, five hours and 100 tracks" in html_out
```

---

# Task 5: `export/runner.py` — the orchestration

**Files:**
- Add: `yoto_maker/export/runner.py`
- Modify: `tests/test_export.py`

**Interfaces produced:** `ExportTrack`, `Failure`, `ExportResult`,
`export_card(...)`, and the three name constants.

- [ ] **Step 1: Write the module.**

```python
"""Write a finished card into a folder the user can upload herself.

The only module in this package that touches the filesystem. It is deliberately
the *whole* transaction: it creates the folder, writes every file, and — on a
total failure — **removes the folder it created**. That last part is not
housekeeping. copy.md §5.7 tells the user *"Nothing was saved, and nothing on
this card has changed."*, and that sentence is true only because of it.
"""
from __future__ import annotations

import errno
import io
import logging
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Sequence

from ..audio.normalize import AudioError, normalize_to_mp3
from .errors import (
    REASON_CONVERT_FAILED,
    REASON_GENERIC,
    REASON_NO_SPACE,
    REASON_PERMISSION,
    REASON_TOO_LONG,
    REASON_UNREADABLE,
    ExportError,
    NameTooLongError,
)
from .names import (
    FALLBACK_CARD_NAME,
    date_words,
    duration_words,
    megabytes,
    sanitize_component,
    track_filename,
    unique_dir,
)
from .rules import EXPORT_BITRATE, Advisories, SavedFile, advise, needs_conversion, output_suffix, split_groups
from .sheet import SheetData, render_sheet

log = logging.getLogger("yoto_maker.export")

SHEET_NAME = "What to do next.html"
CARD_PICTURE_NAME = "Card picture.png"
TRACK_PICTURES_DIR = "Track pictures"

# The card picture is embedded in the sheet as a data URI, so it is downscaled
# first: the file on disk can be 1024px (picture.py:14), and a page that carries
# a megabyte of base64 for a 180px thumbnail is a page nobody wants to open.
_SHEET_PICTURE_PX = 360


@dataclass
class ExportTrack:
    """One track to write. Built from the SAME TrackInput list the send path uses."""

    title: str
    audio_path: Path
    icon_path: Path | None = None
    duration_s: float = 0.0


@dataclass
class Failure:
    title: str
    reason: str


@dataclass
class ExportResult:
    folder: Path
    files: list[SavedFile] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    total_count: int = 0

    def view(self) -> dict:
        """Everything the panel renders. It reconstructs nothing in JS."""
        adv: Advisories = advise(self.files)
        return {
            "ok": True,
            "folder_name": self.folder.name,
            "folder_path": str(self.folder),
            "saved_count": len(self.files),
            "total_count": self.total_count,
            "files": [f.name for f in self.files],
            "failures": [{"title": f.title, "reason": f.reason} for f in self.failures],
            "split_groups": [{"title": g.title, "parts": g.parts} for g in split_groups(self.files)],
            "converted": [{"label": f.label} for f in self.files if f.converted],
            "oversize_tracks": [
                {"label": f.label, "title": f.title, "size_mb": megabytes(f.size_bytes)}
                for f in adv.oversize
            ],
            "card_mb": megabytes(adv.card_bytes),
            "card_duration_words": duration_words(adv.card_seconds),
            "card_tracks": adv.card_tracks,
            "over_card_bytes": adv.over_card_bytes,
            "over_card_seconds": adv.over_card_seconds,
            "over_card_tracks": adv.over_card_tracks,
        }


def export_card(
    *,
    tracks: Sequence[ExportTrack],
    card_name: str,
    picture_path: Path | None,
    root: Path,
    scratch_dir: Path,
    version: str,
    update: Callable[..., None] | None = None,
    today: date | None = None,
) -> ExportResult:
    """Write the card into ``root/<card name>/`` and return what landed.

    ``update(stage, percent, message)`` is jobs.py's callback, verbatim.
    """
    say = update or (lambda *a, **k: None)
    say("start", 2, "Making the folder…")

    folder_name = sanitize_component(card_name, fallback=FALLBACK_CARD_NAME)
    try:
        root.mkdir(parents=True, exist_ok=True)
        folder = unique_dir(root, folder_name)
        folder.mkdir()
    except NameTooLongError as exc:
        raise ExportError(REASON_TOO_LONG) from exc
    except OSError as exc:
        raise ExportError(_os_reason(exc)) from exc

    try:
        return _write_all(
            tracks=tracks, folder=folder, picture_path=picture_path,
            scratch_dir=scratch_dir, version=version, say=say,
            today=today or date.today(),
        )
    except BaseException:
        # A folder that exists but is wrong is worse than no folder — she will
        # find it and use it (overview.md §10.5).
        shutil.rmtree(folder, ignore_errors=True)
        raise


def _write_all(*, tracks, folder: Path, picture_path, scratch_dir: Path,
               version: str, say, today: date) -> ExportResult:
    total = len(tracks)
    saved: list[SavedFile] = []
    failures: list[Failure] = []

    for i, track in enumerate(tracks, start=1):
        src = Path(track.audio_path)
        convert = needs_conversion(src)
        say(
            "save",
            5 + int(i / max(total, 1) * 70),
            (f"Turning “{track.title}” into an MP3 ({i} of {total})…" if convert
             else f"Saving “{track.title}” ({i} of {total})…"),
        )
        try:
            name = track_filename(i, total, track.title, output_suffix(src), folder=folder)
        except NameTooLongError as exc:
            raise ExportError(REASON_TOO_LONG) from exc

        dest = folder / name
        try:
            if convert:
                # A per-track scratch directory: normalize_to_mp3 names its
                # output after the INPUT's stem, so two same-named sources would
                # otherwise share one path.
                stage = scratch_dir / f"{i:04d}"
                if stage.exists():
                    shutil.rmtree(stage, ignore_errors=True)
                produced, _info = normalize_to_mp3(src, stage, bitrate=EXPORT_BITRATE)
                shutil.move(str(produced), str(dest))
                shutil.rmtree(stage, ignore_errors=True)
            else:
                shutil.copy2(src, dest)
        except AudioError as exc:
            log.warning("save: could not convert %s: %s", src.name, exc)
            dest.unlink(missing_ok=True)
            failures.append(Failure(track.title, REASON_CONVERT_FAILED))
            continue
        except OSError as exc:
            # Out of space is not one track's problem — continuing would fill the
            # folder with truncated files. Everything else is.
            if getattr(exc, "errno", None) == errno.ENOSPC:
                raise ExportError(REASON_NO_SPACE) from exc
            log.warning("save: could not write %s: %s", name, exc)
            dest.unlink(missing_ok=True)
            failures.append(Failure(track.title, REASON_UNREADABLE))
            continue

        saved.append(
            SavedFile(
                index=i, name=name, title=track.title,
                size_bytes=dest.stat().st_size,
                duration_s=track.duration_s,
                converted=convert,
                icon_path=track.icon_path,
            )
        )

    if not saved:
        # There is no "0 of your 5" message in copy.md §5.1, deliberately: a
        # folder with no audio in it is the total-failure case (§5.7), so it
        # unwinds and the folder is removed.
        raise ExportError(failures[0].reason if failures else REASON_GENERIC)

    say("pictures", 82, "Saving the pictures…")
    has_picture = _write_pictures(folder, picture_path, saved)

    say("sheet", 92, "Writing the instructions…")
    data = SheetData(
        card_name=folder.name,
        files=saved,
        failures=[f.title for f in failures],
        advisories=advise(saved),
        split=split_groups(saved),
        picture_png=_sheet_picture(folder / CARD_PICTURE_NAME) if has_picture else None,
        has_card_picture_file=has_picture,
        version=version,
        date_label=date_words(today),
    )
    try:
        (folder / SHEET_NAME).write_text(render_sheet(data), encoding="utf-8")
    except OSError as exc:
        raise ExportError(_os_reason(exc)) from exc

    say("done", 100, "Saved.")
    return ExportResult(folder=folder, files=saved, failures=failures, total_count=len(tracks))


def _write_pictures(folder: Path, picture_path, saved: list[SavedFile]) -> bool:
    """Best-effort. A picture must never fail a save that has the audio in it."""
    has_picture = False
    if picture_path and Path(picture_path).exists():
        try:
            shutil.copy2(picture_path, folder / CARD_PICTURE_NAME)
            has_picture = True
        except OSError as exc:
            log.warning("save: could not write the card picture: %s", exc)

    # One picture per track even when they are byte-identical: _resolve_icon
    # derives most cards' icons from the card picture, and de-duplicating would
    # break the 1:1 name match that makes the subfolder usable (overview.md §9.3).
    # Only for tracks that LANDED — a picture with no matching audio is a decoy.
    wanted = [f for f in saved if f.icon_path and Path(f.icon_path).exists()]
    if not wanted:
        return has_picture
    pics = folder / TRACK_PICTURES_DIR
    try:
        pics.mkdir(exist_ok=True)
    except OSError as exc:
        log.warning("save: could not make the pictures folder: %s", exc)
        return has_picture
    for f in wanted:
        try:
            shutil.copy2(f.icon_path, pics / (Path(f.name).stem + ".png"))
        except OSError as exc:
            log.warning("save: could not write a track picture: %s", exc)
    return has_picture


def _sheet_picture(path: Path) -> bytes | None:
    try:
        from PIL import Image

        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((_SHEET_PICTURE_PX, _SHEET_PICTURE_PX))
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:  # noqa: BLE001 - the sheet is fine without a picture
        log.warning("save: could not embed the card picture: %s", exc)
        return None


def _os_reason(exc: OSError) -> str:
    code = getattr(exc, "errno", None)
    if code == errno.ENOSPC:
        return REASON_NO_SPACE
    if code in (errno.EACCES, errno.EPERM):
        return REASON_PERMISSION
    # WinError 206 is ERROR_FILENAME_EXCED_RANGE; 3 is ERROR_PATH_NOT_FOUND,
    # which is what an over-length path usually surfaces as.
    if code == errno.ENAMETOOLONG or getattr(exc, "winerror", None) in (3, 206):
        return REASON_TOO_LONG
    return REASON_GENERIC
```

- [ ] **Step 2: Tests.** Append to `tests/test_export.py`. These need real audio,
  so they use the existing `sample_mp3` fixture (which skips without ffmpeg).

```python
from yoto_maker.export import runner as runner_mod
from yoto_maker.export.errors import ExportError


def _track(path, title, dur=2.0, icon=None):
    return runner_mod.ExportTrack(title=title, audio_path=Path(path),
                                  icon_path=icon, duration_s=dur)


def test_a_saved_folder_holds_exactly_the_deliverables(tmp_path, sample_mp3):
    root = tmp_path / "saved"
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One"), _track(sample_mp3, "Chapter Two")],
        card_name="Bedtime Stories", picture_path=None, root=root,
        scratch_dir=tmp_path / "scratch", version="0.1.13",
    )
    names_on_disk = sorted(p.name for p in res.folder.iterdir())
    assert names_on_disk == ["01 - Chapter One.mp3", "02 - Chapter Two.mp3",
                            "What to do next.html"]
    assert res.folder == root / "Bedtime Stories"


def test_pressing_save_twice_never_overwrites(tmp_path, sample_mp3):
    root = tmp_path / "saved"
    kwargs = dict(tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
                  picture_path=None, root=root, scratch_dir=tmp_path / "s",
                  version="0.1.13")
    first = runner_mod.export_card(**kwargs)
    second = runner_mod.export_card(**kwargs)
    assert first.folder.name == "Bedtime Stories"
    assert second.folder.name == "Bedtime Stories (2)"
    assert first.folder.exists()


def test_a_mixed_card_copies_mp3_and_m4a_and_converts_flac(tmp_path, sample_mp3):
    """Acceptance criterion 11. The .m4a staying put is the specific thing to check."""
    from yoto_maker.tools import find_ffmpeg
    import subprocess

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("ffmpeg not available")
    incoming = tmp_path / "in"
    incoming.mkdir()
    m4a = incoming / "sea.m4a"
    flac = incoming / "rain.flac"
    for out in (m4a, flac):
        subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=1", str(out)],
                       capture_output=True, check=True)

    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Song"), _track(m4a, "The Sea"), _track(flac, "Rain")],
        card_name="Mixed", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    written = [f.name for f in res.files]
    assert written == ["01 - Song.mp3", "02 - The Sea.m4a", "03 - Rain.mp3"]
    assert [f.converted for f in res.files] == [False, False, True]


def test_conversion_uses_192k(tmp_path, sample_mp3, monkeypatch):
    seen = {}
    real = runner_mod.normalize_to_mp3

    def spy(src, out_dir, *, bitrate="192k", **kw):
        seen["bitrate"] = bitrate
        return real(src, out_dir, bitrate=bitrate, **kw)

    monkeypatch.setattr(runner_mod, "normalize_to_mp3", spy)
    wav = tmp_path / "in.wav"
    wav.write_bytes(sample_mp3.read_bytes())      # extension drives the decision
    try:
        runner_mod.export_card(
            tracks=[_track(wav, "A")], card_name="C", picture_path=None,
            root=tmp_path / "saved", scratch_dir=tmp_path / "s", version="0.1.13",
        )
    except ExportError:
        pass                                       # ffmpeg may reject the fake wav
    assert seen["bitrate"] == "192k"


def test_a_partial_run_keeps_the_rest_and_the_sheet_tells_the_truth(tmp_path, sample_mp3):
    """Acceptance criterion 5."""
    missing = tmp_path / "in" / "gone.mp3"
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One"), _track(missing, "Chapter Four")],
        card_name="Bedtime Stories", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    assert [f.name for f in res.files] == ["01 - Chapter One.mp3"]
    assert [f.title for f in res.failures] == ["Chapter Four"]
    page = (res.folder / "What to do next.html").read_text(encoding="utf-8")
    assert "Chapter Four" in page              # named in the notice
    assert "02 - Chapter Four" not in page     # NOT in the file list
    assert "1 track" in page


def test_a_total_failure_leaves_no_folder_behind(tmp_path):
    """Acceptance criterion 9, and the reason copy.md §5.7's last line is true."""
    root = tmp_path / "saved"
    with pytest.raises(ExportError):
        runner_mod.export_card(
            tracks=[_track(tmp_path / "nope.mp3", "A")], card_name="Bedtime Stories",
            picture_path=None, root=root, scratch_dir=tmp_path / "s", version="0.1.13",
        )
    assert not (root / "Bedtime Stories").exists()


def test_track_pictures_go_in_a_subfolder_named_to_match(tmp_path, sample_mp3):
    icon = tmp_path / "icon.png"
    from PIL import Image
    Image.new("RGB", (16, 16), "purple").save(icon)
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One", icon=icon)],
        card_name="Bedtime Stories", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    assert (res.folder / "Track pictures" / "01 - Chapter One.png").exists()
    # The subfolder is the whole point: no loose 16x16 PNG beside the audio.
    assert not list(res.folder.glob("*.png"))


def test_the_result_view_carries_everything_the_panel_needs(tmp_path, sample_mp3):
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
        picture_path=None, root=tmp_path / "saved", scratch_dir=tmp_path / "s",
        version="0.1.13",
    )
    v = res.view()
    for key in ("folder_name", "folder_path", "saved_count", "total_count", "files",
                "failures", "split_groups", "converted", "oversize_tracks", "card_mb",
                "card_duration_words", "card_tracks", "over_card_bytes",
                "over_card_seconds", "over_card_tracks"):
        assert key in v
```

---

# Task 6: `export/reveal.py` — opening the folder

**Files:**
- Add: `yoto_maker/export/reveal.py`
- Modify: `tests/test_export.py`

- [ ] **Step 1: Write the module.**

```python
"""Show the user the folder, in her own file manager.

The browser cannot do this. A ``file:///`` link from an ``http://`` page is
refused **silently** — it must not be shipped and must not be "tried first" — and
a ZIP download lands in Downloads and asks her to unzip it, which is precisely
the file management DESIGN.md §2 promises she never faces.

So the server does it, and that is sound here for configuration-surface §7.8's
reason, unchanged: the app binds to 127.0.0.1 (config.py:198) with no
authentication, so *the browser, the server, the OS account and the person are
all the same.* There is nothing for a gate to gate.

**The caller never supplies a path.** app.py remembers the folder it last wrote
and passes that. Handing an arbitrary caller-supplied string to the shell is a
foot-gun with no upside, and the UI never needs it — there is exactly one folder
this button can mean (overview.md §7.3).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .errors import REASON_CANNOT_OPEN, ExportError

log = logging.getLogger("yoto_maker.export")


def reveal_supported() -> bool:
    """Whether this machine can be asked to show a folder.

    ``os.startfile`` is stdlib and Windows-only, so a PyInstaller-frozen build
    needs no hook — but confirm it in the .exe rather than take that on trust
    (overview.md §16.2 item 5).

    When this is False the UI **omits** the button rather than disabling it, and
    shows the full path instead (copy.md §5.5). Omitted, never disabled —
    configuration-surface §3.5.2 and §13.5.
    """
    return hasattr(os, "startfile")


def reveal_folder(folder: Path) -> None:
    if not reveal_supported():
        raise ExportError(REASON_CANNOT_OPEN)
    try:
        os.startfile(str(folder))  # noqa: S606 - a path this process itself wrote
    except OSError as exc:
        log.warning("save: could not open %s: %s", folder, exc)
        raise ExportError(REASON_CANNOT_OPEN) from exc
```

- [ ] **Step 2: Finish `yoto_maker/export/__init__.py`.** Now that every module
  exists, replace Task 2's minimal version with the package's real public
  surface:

```python
"""Saving a finished card to a folder the user uploads herself.

Design: docs/design-handoffs/export-only-mode/. The package is named for the
operation; **no string it produces for a user contains the word "export"** — the
verb is *save*, the noun is *files*, the destination is *a folder*.
"""
from __future__ import annotations

from .errors import (
    REASON_CANNOT_OPEN,
    REASON_NOTHING_SAVED,
    ExportError,
    NameTooLongError,
)
from .reveal import reveal_folder, reveal_supported
from .runner import CARD_PICTURE_NAME, SHEET_NAME, TRACK_PICTURES_DIR, ExportTrack, export_card

__all__ = [
    "ExportError",
    "NameTooLongError",
    "ExportTrack",
    "export_card",
    "reveal_folder",
    "reveal_supported",
    "REASON_CANNOT_OPEN",
    "REASON_NOTHING_SAVED",
    "SHEET_NAME",
    "CARD_PICTURE_NAME",
    "TRACK_PICTURES_DIR",
]
```

- [ ] **Step 3: Tests.**

```python
import sys

from yoto_maker.export import reveal as reveal_mod


def test_reveal_support_matches_the_platform():
    assert reveal_mod.reveal_supported() is hasattr(os, "startfile")
    if not sys.platform.startswith("win"):
        assert reveal_mod.reveal_supported() is False


def test_reveal_refuses_rather_than_raising_something_technical(tmp_path, monkeypatch):
    monkeypatch.setattr(reveal_mod, "reveal_supported", lambda: False)
    with pytest.raises(ExportError):
        reveal_mod.reveal_folder(tmp_path)
```

---

# Task 7: the three routes, and the shared card construction

**Files:**
- Modify: `yoto_maker/server/app.py`
- Modify: `tests/test_export.py`

**Interfaces produced:**
- `_build_card_inputs(draft) -> tuple[list[TrackInput], str]`
- `POST /api/export` → `{job_id}`
- `GET /api/export/sheet.html`
- `POST /api/export/open` → `{ok: true}`
- `/api/status` → `config.saved_dir`

- [ ] **Step 1: Imports.** Add to the import block near line 28:

```python
from ..export import (
    REASON_NOTHING_SAVED,
    SHEET_NAME,
    ExportError,
    ExportTrack,
    export_card,
    reveal_folder,
    reveal_supported,
)
```

- [ ] **Step 2: Register `ExportError` as a friendly error.** At line 100, extend
  the tuple and add a decorator to `_friendly_handler`:

```python
FRIENDLY_ERRORS = (SourceError, YotoError, AudioError, ImageError, AIUnavailableError, ExportError)
```

Then add one decorator to the existing stack at line 103, on top:

```python
@app.exception_handler(ExportError)
@app.exception_handler(SourceError)
@app.exception_handler(YotoError)
@app.exception_handler(AudioError)
@app.exception_handler(ImageError)
@app.exception_handler(AIUnavailableError)
@app.exception_handler(updater.UpdateError)
async def _friendly_handler(_request, exc):  # noqa: ANN001
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

The other six lines and the body are unchanged — only `ExportError` is new.

- [ ] **Step 3: `/api/status` gains one field.** In `status()`'s `"config"` dict
  (line 151-155), after `data_dir`:

```python
            # Where HER files go, as distinct from where the app keeps ITS files
            # on the line above. Resolved on the server and never constructed in
            # JS — configuration-surface §13.4's rule for the redirect URL, for
            # the same reason: OneDrive redirects Documents and a guess would be
            # wrong in exactly the case where the value matters (copy.md §7).
            "saved_dir": str(get_config().saved_dir),
```

- [ ] **Step 4: Extract the shared card construction.** Replace the body of
  `send_to_yoto()`'s list comprehension (lines 643-647) with a call, and add the
  helper immediately after `_resolve_icon` (line 628):

```python
def _build_card_inputs(draft) -> tuple[list[TrackInput], str]:
    """The complete, network-free description of the card: tracks and name.

    SHARED by POST /api/send and POST /api/export, and that sharing is a design
    requirement rather than a tidiness one (spec §3.1, acceptance criterion 8):
    a card saved to a folder and the same card sent to Yoto must be the same
    card. In particular _resolve_icon is CALLED here, not reimplemented — it is
    lazy and has a filesystem side effect (make_device_icon writes
    work/icon_<id>.png), and it is the reason both paths carry identical
    pictures.
    """
    inputs = [
        TrackInput(audio_path=t.audio_path, title=t.title, icon_path=_resolve_icon(t, draft))
        for t in draft.tracks
    ]
    return inputs, draft.card_name.strip()
```

and inside `send_to_yoto()`:

```python
    inputs, card_name = _build_card_inputs(draft)
```

**`send_to_yoto()` must produce a byte-identical list afterwards.** Nothing else
in it changes.

- [ ] **Step 5: The export routes.** Add a new section immediately after
  `send_to_yoto()` (line 661), before the Label PDF section:

```python
# --------------------------------------------------------------------------- #
# Save the files to a folder (background job with progress)
#
# The alternative delivery path. See docs/design-handoffs/export-only-mode/.
# --------------------------------------------------------------------------- #

# The folder the server last wrote. The reveal route reads THIS and never a path
# from the browser (overview.md §7.3) — even on loopback, handing a
# caller-supplied string to the shell is a foot-gun with no upside, and the UI
# never needs it: there is exactly one folder the button can mean.
_last_saved_folder: Path | None = None


@app.post("/api/export")
async def export_to_folder() -> dict:
    draft = get_draft()
    # The same two guards as the send path, worded in parallel (copy.md §3).
    # Two sentences that differ by two words is how the user learns the buttons
    # are peers — do NOT refactor them into one string.
    if not draft.tracks:
        raise SourceError("Add some audio before saving it.")
    if not draft.card_name.strip():
        raise SourceError("Give your card a name before saving it.")
    # ------------------------------------------------------------------ #
    # THERE IS NO CONNECTION CHECK HERE, AND THAT IS THE FEATURE.
    #
    # send_to_yoto() checks connection_status() at app.py:640. This path takes
    # the two guards above it and not that one: saving needs no sign-in at all,
    # which is the headline property (spec §1.2) and the reason a user whose
    # Client ID has hard-blocked sign-in still has a way to finish a card.
    # Guarded by test_saving_needs_no_sign_in.
    # ------------------------------------------------------------------ #

    inputs, card_name = _build_card_inputs(draft)
    tracks = [
        ExportTrack(
            title=ti.title,
            audio_path=Path(ti.audio_path),
            icon_path=ti.icon_path,
            duration_s=t.duration_s,
        )
        for ti, t in zip(inputs, draft.tracks)
    ]
    picture = Path(draft.picture_path) if draft.picture_path else None
    cfg = get_config()
    root = cfg.saved_dir
    scratch = cfg.work_dir / "export"

    def work(update):
        global _last_saved_folder
        result = export_card(
            tracks=tracks,
            card_name=card_name,
            picture_path=picture,
            root=root,
            scratch_dir=scratch,
            version=__version__,
            update=update,
        )
        _last_saved_folder = result.folder
        return {
            **result.view(),
            "sheet_url": "/api/export/sheet.html",
            "can_open": reveal_supported(),
        }

    job_id = get_jobs().start(work)
    return {"job_id": job_id}


@app.get("/api/export/sheet.html")
async def get_export_sheet():
    """Serve the page that is already in the folder. Same shape as /api/label.pdf.

    One file, one rendering, both routes: this returns the exact bytes written
    into the folder, so the two can never drift (overview.md §6.3).
    """
    if _last_saved_folder is None:
        raise HTTPException(404, "Nothing has been saved yet")
    page = _last_saved_folder / SHEET_NAME
    if not page.exists():
        raise HTTPException(404, "Nothing has been saved yet")
    return FileResponse(page, media_type="text/html")


@app.post("/api/export/open")
async def open_saved_folder() -> dict:
    """Show the folder the server last wrote. TAKES NO PATH FROM THE BROWSER.

    POST rather than GET: it has an effect, and the origin guard only vets
    non-GET requests (app.py:66).
    """
    if _last_saved_folder is None or not _last_saved_folder.exists():
        raise ExportError(REASON_NOTHING_SAVED)
    await run_in_threadpool(reveal_folder, _last_saved_folder)
    return {"ok": True}
```

`REASON_NOTHING_SAVED` is already in Step 1's import list.

- [ ] **Step 6: Forget the folder on "Start a new card".** In `reset_draft()`
  (line 202):

```python
@app.post("/api/draft/reset")
async def reset_draft() -> dict:
    global _last_saved_folder
    get_draft().reset()
    # The card that folder described is gone. Serving its instruction page from
    # a blank draft would point at a card the user has just discarded
    # (interactions.md §9.3). The folder itself is hers and stays on disk.
    _last_saved_folder = None
    return {"ok": True}
```

- [ ] **Step 7: Tests.** Append to `tests/test_export.py`:

```python
from fastapi.testclient import TestClient

from yoto_maker.server.app import app as fastapi_app


@pytest.fixture
def client(temp_config):
    with TestClient(fastapi_app) as c:
        yield c


def _drain(client, job_id):
    for _ in range(400):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            return job
    raise AssertionError("job never finished")


def test_refusals_are_the_parallel_wording_and_come_before_anything_is_written(client):
    client.post("/api/draft/reset")
    r = client.post("/api/export")
    assert r.status_code == 400
    assert r.json()["error"] == "Add some audio before saving it."


def test_saving_needs_no_sign_in(client, sample_mp3, monkeypatch):
    """The headline property. If this test ever needs a connection, the feature
    has been deleted."""
    import yoto_maker.server.app as app_mod

    monkeypatch.setattr(app_mod, "connection_status",
                        lambda: {"connected": False, "client_id_verdict": "ok"})
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    assert job["status"] == "done", job
    assert job["result"]["saved_count"] == 1


def test_the_status_route_reports_where_saved_files_go(client):
    cfg = client.get("/api/status").json()["config"]
    assert cfg["saved_dir"].endswith("Yoto Maker")
    assert cfg["saved_dir"] != cfg["data_dir"]


def test_the_sheet_route_serves_what_is_in_the_folder(client, sample_mp3):
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    folder = Path(job["result"]["folder_path"])
    served = client.get(job["result"]["sheet_url"])
    assert served.status_code == 200
    assert served.text == (folder / "What to do next.html").read_text(encoding="utf-8")


def test_the_open_route_accepts_no_path(client):
    """The safety property. The route's signature takes nothing at all."""
    import inspect
    from yoto_maker.server.app import open_saved_folder

    assert list(inspect.signature(open_saved_folder).parameters) == []
    assert client.post("/api/export/open").status_code == 400   # nothing saved yet


def test_starting_a_new_card_forgets_the_folder(client, sample_mp3):
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    _drain(client, client.post("/api/export").json()["job_id"])
    assert client.get("/api/export/sheet.html").status_code == 200
    client.post("/api/draft/reset")
    assert client.get("/api/export/sheet.html").status_code == 404


def test_both_paths_build_the_same_card(client, sample_mp3):
    """Acceptance criterion 8, at the seam where the two could drift."""
    import yoto_maker.server.app as app_mod

    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    draft = app_mod.get_draft()
    a, name_a = app_mod._build_card_inputs(draft)
    b, name_b = app_mod._build_card_inputs(draft)
    assert name_a == name_b == "Bedtime Stories"
    assert [(x.title, x.audio_path, x.icon_path) for x in a] == \
           [(x.title, x.audio_path, x.icon_path) for x in b]
    assert all(x.icon_path is not None for x in a), "_resolve_icon must have run"
```

---

# Task 8: `index.html` — the markup block, the one edited string, the Settings row

**Files:**
- Modify: `yoto_maker/server/static/index.html`
- Modify: `tests/test_card_view_markup.py`

- [ ] **Step 1: Edit the one shipped string that becomes false.** Line 173:

```html
        <div class="msg-box info">To send cards straight to your Yoto, connect your account first.</div>
```

It does **not** mention saving. Advertising the alternative inside the connect
box would bury the connect intent, which is still the right first answer for most
people; the save button's own caption twelve pixels below already says
*"You don't need to be signed in for this."* (`copy.md` §1).

- [ ] **Step 2: Insert the block.** Between `#connectWarn` (line 198) and the
  `#advRow` comment (line 200). Verbatim from `interactions.md` §1, with the
  rationale comment the file's house style expects:

```html
      <!-- The alternative delivery path. ALWAYS RENDERED, in both connection
           states — saving needs no sign-in at all, and configuration-surface
           §12.4's lesson is that a control which vanishes in the state where you
           want it IS the bug. Never disabled by STATUS.yoto.connected.

           Appended after #connectWarn and before #advRow, never inserted next to
           #sendBtn: inserting there would make the SEND button's own feedback
           appear below a different button. Appending also lands it directly
           beneath #sendError on a failed send, and directly beneath #connectWarn
           when a bad Client ID has hard-blocked sign-in — which is the first
           time that state has had a live way forward.

           .tiny is on the <p>, NOT on the <button>: .tiny's color: var(--muted)
           (0-1-0) would beat .btn's own colour rules and grey the control out.
           Same specificity trap configuration-surface §12.4 fixed on #advToggle.

           Zero new CSS. overview.md §4.3, interactions.md §1. -->
      <div id="exportRow" style="margin-top:14px">
        <button id="exportBtn" class="btn">📁 Save the files to a folder</button>
        <p class="tiny" style="margin-top:8px">
          You’ll put them on Yoto’s website yourself. You don’t need to be signed in for this.
        </p>
      </div>

      <div id="exportProgress" class="progress hidden">
        <div class="bar"><div id="exportBar"></div></div>
        <div class="msg" id="exportMsg" role="status"></div>
      </div>

      <!-- #exportError and #exportDone are programmatic focus targets, hence
           tabindex="-1" — the same construction #addError uses. #exportDone gets
           NO role: focus is moved to it, and adding role="status" as well would
           announce the same sentence twice. #exportNote likewise. -->
      <div id="exportError" class="msg-box err hidden" role="alert" tabindex="-1"></div>
      <div id="exportDone" class="msg-box ok hidden" tabindex="-1"></div>
      <div id="exportNote" class="msg-box info hidden"></div>

      <!-- .done-actions, not .setting-actions: this is the card view, and
           .done-actions (styles.css:260) is what step 4 already uses for a
           result's follow-on controls. The instructions are the PRIMARY action
           and the folder is secondary — deliberately inverted (overview.md §7.1). -->
      <div id="exportActions" class="done-actions hidden">
        <a id="exportReadme" class="btn primary" target="_blank" rel="noopener">📄 What to do next</a>
        <button id="exportOpen" class="btn">📂 Open the folder</button>
      </div>
```

- [ ] **Step 3: The Settings help row** (`copy.md` §7, spec §6.2). After the
  `helpDataDir` div (line 437), inside `.setting-body`:

```html
          <!-- Two rows that both look like folders, and they ARE different
               folders: the row above is where the app keeps ITS files, this one
               is where it puts HERS. The labels already say which is which, and
               lengthening either to disambiguate would make both worse to read
               aloud on the phone — which is the only thing this section is for.
               Rendered from the server, never constructed in JS. copy.md §7. -->
          <p class="tiny" style="margin-top:14px">Where saved files go</p>
          <div class="mono-value" id="helpSavedDir" style="margin-top:6px"></div>
```

- [ ] **Step 4: Markup tests.** Append to `tests/test_card_view_markup.py`:

```python
# --------------------------------------------------------------------------- #
# Save-to-a-folder mode. docs/design-handoffs/export-only-mode/.
# --------------------------------------------------------------------------- #
import re

_BANNED_IN_COPY = ("export", "directory", "file format", "codec", "transcode", "metadata")


def _visible_text(index_html: str) -> str:
    """Text nodes only. Comments are stripped FIRST — the new markup's own
    comments say "export" repeatedly, and they are not user-visible."""
    without_comments = re.sub(r"<!--.*?-->", " ", index_html, flags=re.S)
    return " ".join(re.findall(r">([^<>]+)<", without_comments))


def test_the_export_block_sits_after_connect_warn_and_before_adv_row(index_html):
    order = [
        index_html.index(f'id="{el}"')
        for el in ("connectWarn", "exportRow", "exportProgress", "exportError",
                   "exportDone", "exportNote", "exportActions", "advRow")
    ]
    assert order == sorted(order)


def test_adv_row_is_still_the_last_child_of_step_3(index_html):
    """configuration-surface interactions.md §1.4, unchanged by this feature."""
    assert index_html.index('id="advRow"') > index_html.index('id="exportActions"')


def test_the_export_row_is_never_hidden(index_html):
    row = index_html[index_html.index('id="exportRow"'):]
    row = row[:row.index(">") + 1]
    assert "hidden" not in row


def test_the_export_button_is_never_disabled_by_connection_state(app_js):
    """overview.md §10.1. Disabling it would delete the feature's reason to exist."""
    assert "#exportBtn\").disabled = !STATUS" not in app_js
    assert "#exportBtn\").disabled = !connected" not in app_js
    assert 'show($("#exportRow")' not in app_js


def test_the_word_export_never_reaches_the_user(index_html):
    """Acceptance criterion 6."""
    text = _visible_text(index_html).lower()
    for word in _BANNED_IN_COPY:
        assert word not in text, f"{word!r} is visible in index.html"


def test_the_connect_box_no_longer_claims_connecting_is_required(index_html):
    assert "To send cards straight to your Yoto, connect your account first." in index_html
    assert "You'll need to connect your Yoto account first." not in index_html


def test_the_feature_adds_no_css(styles_css, index_html):
    """Acceptance criterion 10. If this fails, something in the spec §2 was
    reinterpreted and it goes back to Designer — do not add a rule to make it
    pass."""
    for token in ("export", "#exportRow", "#exportBtn", "msg-box.warn", ".warn "):
        assert token not in styles_css
    block = index_html[index_html.index('id="exportRow"'):index_html.index('id="advRow"')]
    used = set(re.findall(r'class="([^"]+)"', block))
    allowed = {"btn", "btn primary", "tiny", "progress", "bar", "msg",
               "msg-box err hidden", "msg-box ok hidden", "msg-box info hidden",
               "done-actions hidden"}
    assert used <= allowed, used - allowed
```

---

# Task 9: `app.js` — the panel

**Files:**
- Modify: `yoto_maker/server/static/app.js`
- Modify: `tests/test_card_view_markup.py`

- [ ] **Step 1: The strings and the two handlers.** Insert after `makeLabel()`
  (line 2024), before `// ---- wire up`:

```js
// ---- save the files to a folder -------------------------------------------
// Every string below is docs/design-handoffs/export-only-mode/copy.md, verbatim,
// with typographic apostrophes. The word "export" appears only in identifiers.
//
// THE PANEL RECONSTRUCTS NOTHING. Every name, number, path and list comes from
// the job result (interactions.md §3.3 step 2) — the same rule
// configuration-surface §13.4 set for the redirect URL, for the same reason.

const EXPORT_FAIL_HEAD = "Yoto Maker couldn’t save the files.";
const EXPORT_FAIL_TAIL =
  "Nothing was saved, and nothing on this card has changed. You can try again, " +
  "or send it to your Yoto instead.";
const EXPORT_PARTIAL_TAIL =
  "Everything else is in the folder. The page in the folder lists what’s actually there.";
const EXPORT_CEILING_FIX =
  "Yoto’s website may refuse some of it. If it does, make two shorter cards instead of one.";

function exportWhere(r) {
  return `in a folder called “${r.folder_name}” — in your Documents, under Yoto Maker.`;
}

function exportSuccessLine(r) {
  // The 🎉 is dropped from the partial message, deliberately: celebrating an
  // incomplete result is the kind of small dishonesty that costs trust, and the
  // missing track is named directly below (copy.md §5.1).
  if (r.failures.length) return `${r.saved_count} of your ${r.total_count} tracks are saved, ${exportWhere(r)}`;
  if (r.saved_count === 1) return `🎉 Your track is saved, ${exportWhere(r)}`;
  return `🎉 All ${r.saved_count} tracks are saved, ${exportWhere(r)}`;
}

// The fixed order of overview.md §10.3's table: split → converted → track over
// 100 MB → card over 500 MB / 5 hours → card over 100 tracks, then ONE shared
// recovery sentence if any card ceiling fired. Fixed here so two cards with the
// same conditions never read differently.
function exportNotes(r) {
  const out = [];

  for (const g of r.split_groups) {
    out.push(
      "One of your tracks was too long for a Yoto card, so it’s saved as more " +
      `than one file — “${g.title}” is in ${g.parts} parts. Add them all, in ` +
      "number order, and they’ll play one after the other."
    );
  }

  if (r.converted.length) {
    const list = r.converted.map((c) => c.label).join(", ");
    out.push(
      r.converted.length === 1
        ? "Yoto Maker saved an MP3 copy of one of your files, because Yoto’s " +
          "website is fussier about this than the app is. It’s the same audio, " +
          `and nothing else changed: ${list}.`
        : `Yoto Maker saved MP3 copies of ${r.converted.length} of your files, ` +
          "because Yoto’s website is fussier about this than the app is. They’re " +
          `the same audio, and nothing else changed: ${list}.`
    );
  }

  if (r.oversize_tracks.length === 1) {
    const t = r.oversize_tracks[0];
    out.push(
      `One of your tracks is bigger than Yoto allows — “${t.title}” is ${t.size_mb} MB, ` +
      "and Yoto’s limit for one track is 100 MB. Yoto’s website may refuse it. If it " +
      "does, tell whoever set Yoto Maker up for you — that track needs making smaller."
    );
  } else if (r.oversize_tracks.length > 1) {
    const list = r.oversize_tracks.map((t) => `${t.label} (${t.size_mb} MB)`).join(", ");
    out.push(
      `${r.oversize_tracks.length} of your tracks are bigger than Yoto allows for a ` +
      `single track — Yoto’s limit is 100 MB each: ${list}. Yoto’s website may refuse ` +
      "them. If it does, tell whoever set Yoto Maker up for you — those tracks need " +
      "making smaller."
    );
  }

  if (r.over_card_bytes) {
    out.push(`This card is ${r.card_mb} MB altogether, and Yoto allows 500 MB on one card.`);
  }
  if (r.over_card_seconds) {
    out.push(`This card is ${r.card_duration_words} altogether, and Yoto allows 5 hours on one card.`);
  }
  if (r.over_card_tracks) {
    out.push(`This card has ${r.card_tracks} tracks, and Yoto allows 100 on one card.`);
  }
  // ONE closing sentence, however many of the three fired. At ~192 kbps the
  // 500 MB and 5-hour ceilings are the same card, and repeating the fix under
  // each would read as two problems with two fixes (copy.md §5.9).
  if (r.over_card_bytes || r.over_card_seconds || r.over_card_tracks) {
    out.push(EXPORT_CEILING_FIX);
  }

  return out;
}

function exportFailureParagraphs(r) {
  if (r.failures.length === 1) {
    const f = r.failures[0];
    return [`One track couldn’t be saved: “${f.title}”. ${f.reason}`, EXPORT_PARTIAL_TAIL];
  }
  return [
    `${r.failures.length} tracks couldn’t be saved:`,
    ...r.failures.map((f, i) => `${i + 1}. “${f.title}” — ${f.reason}`),
    EXPORT_PARTIAL_TAIL,
  ];
}

function renderExportResult(r) {
  const done = $("#exportDone");
  const lines = [exportSuccessLine(r)];
  // The full path appears ONLY when the folder cannot be opened for her, where
  // it stops being clutter and becomes the answer (copy.md §5.5).
  if (!r.can_open) lines.push("The folder is here:");
  setMsgBoxContent(done, lines);
  if (!r.can_open) {
    const p = document.createElement("div");
    p.className = "mono-value";
    p.textContent = r.folder_path;
    done.appendChild(p);
  }
  show(done, true);

  const notes = exportNotes(r);
  const noteBox = $("#exportNote");
  // Omitted entirely when nothing fired: an empty .msg-box has 12px of padding
  // and a background, and would render as a stray grey bar.
  if (notes.length) { setMsgBoxContent(noteBox, notes); show(noteBox, true); }
  else { noteBox.textContent = ""; show(noteBox, false); }

  $("#exportReadme").href = r.sheet_url + "?t=" + Date.now();
  // Omitted, never disabled — a disabled button invites her to keep pressing it
  // (configuration-surface §3.5.2, §13.5).
  show($("#exportOpen"), !!r.can_open);
  show($("#exportActions"), true);

  if (r.failures.length) {
    setMsgBoxContent($("#exportError"), exportFailureParagraphs(r));
    show($("#exportError"), true);
    // The failure is the part she has to read, and it overrides the success
    // focus (interactions.md §3.6). The assertive alert lands AFTER the focus
    // move so it is not queued behind it.
    $("#exportError").focus();
  } else {
    done.focus();
  }
}

async function saveToFolder() {
  clearError($("#exportError"));
  $("#exportNote").textContent = "";
  show($("#exportNote"), false);
  show($("#exportDone"), false);
  show($("#exportActions"), false);
  show($("#exportProgress"), true);
  $("#exportBar").style.width = "2%";
  $("#exportMsg").textContent = "Making the folder…";
  $("#exportBtn").disabled = true;
  try {
    const { job_id } = await api("/api/export", { method: "POST" });
    const result = await pollJob(job_id, (p, m) => {
      $("#exportBar").style.width = Math.max(2, p) + "%";
      $("#exportMsg").textContent = m;
    });
    renderExportResult(result);
  } catch (e) {
    // A refusal (no tracks / no card name) is one sentence on its own. A job
    // failure is copy.md §5.7's three paragraphs, and only the middle one is
    // cause-specific — jobs.py carries no reason code, so the server composes
    // that line and these two frame it.
    const paragraphs = e.status === 400 && !e.jobFailure
      ? [e.message]
      : [EXPORT_FAIL_HEAD, e.message, EXPORT_FAIL_TAIL];
    setMsgBoxContent($("#exportError"), paragraphs);
    show($("#exportError"), true);
    $("#exportError").focus();
  } finally {
    show($("#exportProgress"), false);
    // Never gated on the connection. overview.md §10.1.
    $("#exportBtn").disabled = false;
  }
}

async function openSavedFolder() {
  // No spinner, no transient "Opened!" state — configuration-surface tokens.md
  // §3a rejected exactly that shape. If it fails, it fails server-side and the
  // message renders below (interactions.md §4.4).
  try {
    await api("/api/export/open", { method: "POST" });
  } catch (e) {
    showError($("#exportError"), e.message);
  }
}
```

**One thing to pin while implementing:** the `catch` above distinguishes a
*refusal* (a 400 from `POST /api/export`) from a *job failure* (thrown by
`pollJob`, which builds a bare `Error` with no `.status`). `pollJob`'s error has
no `status` property, so `e.status === 400` is false for it and the three-
paragraph shape is used. **Drop the `!e.jobFailure` clause** — it is a
belt-and-braces guard for a property nothing sets. Written here so the
implementer removes it deliberately rather than shipping dead code.

- [ ] **Step 2: Wire it.** In `wire()`, after line 2208:

```js
  $("#exportBtn").addEventListener("click", saveToFolder);
  $("#exportOpen").addEventListener("click", openSavedFolder);
```

- [ ] **Step 3: `#startOver` must clear the block.** This is the one case where
  the panel becomes misleading — the card it described is gone. Extend the
  handler at line 2210:

```js
      show($("#sendDone"), false);
      show($("#labelDone"), false);
      // The card this described has been discarded, and a stale
      // "📄 What to do next" points at instructions for it (interactions.md §9.3).
      show($("#exportProgress"), false);
      show($("#exportError"), false);
      show($("#exportDone"), false);
      show($("#exportNote"), false);
      show($("#exportActions"), false);
      $("#exportReadme").removeAttribute("href");
```

- [ ] **Step 4: The Settings help row.** In `renderHelpSection()` (line 965):

```js
  $("#helpDataDir").textContent = cfg.data_dir || "";
  $("#helpSavedDir").textContent = cfg.saved_dir || "";
```

- [ ] **Step 5: Static assertions.** Append to `tests/test_card_view_markup.py`:

```python
def test_the_export_panel_renders_only_from_the_job_result(app_js):
    """It must never rebuild the folder name or path from anything local."""
    block = app_js[app_js.index("function renderExportResult"):app_js.index("async function saveToFolder")]
    assert "Documents" not in block.replace("in your Documents, under Yoto Maker", "")
    assert "r.folder_path" in block and "r.folder_name" in block


def test_the_open_button_is_omitted_not_disabled(app_js):
    assert 'show($("#exportOpen"), !!r.can_open)' in app_js
    assert '#exportOpen").disabled' not in app_js


def test_there_is_no_cancel(app_js, index_html):
    """jobs.py has no cancellation and this PR does not add one (spec §2.8)."""
    assert "exportCancel" not in app_js
    assert "exportCancel" not in index_html


def test_start_over_clears_the_saved_panel(app_js):
    handler = app_js[app_js.index('$("#startOver")'):]
    assert 'show($("#exportActions"), false)' in handler
    assert '$("#exportReadme").removeAttribute("href")' in handler


def test_the_recovery_sentence_appears_once_however_many_ceilings_fired(app_js):
    assert app_js.count("make two shorter cards instead of one") == 1
```

---

# Task 10: version bump, docs, queue bookkeeping

**Files:**
- Modify: `pyproject.toml`, `yoto_maker/__init__.py`
- Modify: `docs/RELEASE_NOTES.md`, `docs/INSTALL-FOR-MOM.md`,
  `docs/BUILDER_QUEUE.md`
- Verify (no change expected): `docs/SETUP-YOTO-CONNECTION.md`

- [ ] **Step 1: Bump to `0.1.13`.** `pyproject.toml:7` and
  `yoto_maker/__init__.py:3`. **Not optional** — see §Global Constraints.

- [ ] **Step 2: `docs/RELEASE_NOTES.md`.** New section at the top, in the
  register the file establishes:

```markdown
# Yoto Maker v0.1.13

### 🆕 New in v0.1.13

- **There’s a second way to finish a card, and it doesn’t need you to be signed
  in.** Under **🚀 Send to Yoto** in step 3 there is now
  **📁 Save the files to a folder**. Press it and Yoto Maker puts everything for
  your card — the audio, the pictures, and a page of instructions — into a folder
  in your **Documents**, under **Yoto Maker**. You then put them on Yoto’s
  website yourself. Nothing about sending straight to your Yoto has changed.
- **The folder comes with instructions written for your card.** A page called
  **What to do next** opens in your browser and names your card, lists your
  actual files in order, links to Yoto’s website, and ends where it should — at
  tapping a blank card in the Yoto app. It stays in the folder, so you can open
  it a week later, or on a different computer.
- **Files Yoto’s website is fussy about are saved as MP3 copies.** They’re the
  same audio, and Yoto Maker tells you which ones it did that to. Your original
  files are untouched.
- **Nothing is ever overwritten.** Save the same card twice and you get a second
  folder ending in **(2)**, exactly like copying a file in Windows.
```

- [ ] **Step 3: `docs/INSTALL-FOR-MOM.md`.** The last sentence of the step-3
  callout (line 83) is now incomplete. Replace *"And even without connecting,
  adding audio, pictures, and printing labels all work."* with:

```markdown
> ℹ️ Connecting your Yoto is already set up for you — you just sign in. (If you
> ever need to use a *different* Yoto account, or if sending stops working,
> click the **Yoto** button in the top-right corner — that opens a **Settings**
> page with one button to fix it. Most people never need it.)
>
> 📁 **You don’t have to connect at all if you’d rather not.** Under the big
> **Send to Yoto** button there’s **Save the files to a folder**. Press it and
> Yoto Maker puts everything for your card in your **Documents**, under **Yoto
> Maker**, along with a page telling you how to put it on Yoto’s website
> yourself. Adding audio, pictures and printing labels all work without
> connecting too.
```

- [ ] **Step 4: Verify `docs/SETUP-YOTO-CONNECTION.md` needs no change.** It
  describes connecting, which is unchanged. Confirm and say so in the PR body
  rather than editing it.

- [ ] **Step 5: Queue bookkeeping.** Move item 19 to `✅` in
  `docs/BUILDER_QUEUE.md`, add a Shipped row, and update the last-updated banner
  with the suite count and the review outcome.

- [ ] **Step 6: PR body — Docs Impact section.** List the three doc files above,
  say `SETUP-YOTO-CONNECTION.md` was checked and needs nothing, and record which
  Test Plan items were **not** verifiable (see §Test Plan §Z — this matters more
  than usual here).

---

## Test Plan

**Read §Z first. The normal UAT story does not apply to this feature.**

### A. Unit and integration (the suite, `pytest`)

Everything in Tasks 1–9's test steps. Every test runs offline, needs no Yoto
account, and needs no device. `sample_mp3`-based tests skip cleanly without
ffmpeg, matching the existing convention.

### B. Locally verifiable by Builder, in the app

| # | Check | How |
| --- | --- | --- |
| B1 | **A never-signed-in user can finish a card.** Acceptance criterion 1 | Delete `%LOCALAPPDATA%\YotoMaker\yoto_token.json`, reload, add audio, name it, press `📁 Save the files to a folder`. The button must be live with `🚀 Send to Yoto` greyed above it |
| B2 | **Filename sort equals play order**, in Explorer *and* in a browser's file-open dialog | Save a card with a split track; sort by name in both views |
| B3 | **Conversion fires on the right inputs at the right bitrate** | One card holding `.mp3` + `.m4a` + `.flac`. The first two are byte-identical to their sources; the third is an MP3. `ffprobe` the output: **192 kbps**. The panel names only the `.flac` |
| B4 | **An oversized MP3 is NOT re-encoded** | A >100 MB `.mp3`. It is copied untouched and the panel *advises* — spec §2.4's asymmetry |
| B5 | **The instruction page renders and is self-contained** | Open `What to do next.html` from the folder with the app **stopped**. Picture shows, link works, step 6 present. Then Ctrl+P |
| B6 | **`📂 Open the folder` works in the frozen `.exe`** | Build the `.exe`, run it, save a card, press the button. This is the one genuinely new mechanism and the one thing the source-run cannot prove (spec §2.7) |
| B7 | **The job does not block the event loop** | While a large save runs, `GET /api/status` must answer promptly in a second tab |
| B8 | **A partial run never produces a sheet describing files that are not there.** Acceptance criterion 5 | Lock one source file (open it in another program) mid-run; read the generated sheet |
| B9 | **A failed run leaves no folder behind.** Acceptance criterion 9 | Make `Documents` read-only; press save; confirm nothing is created |
| B10 | **Saved twice gives ` (2)`, and the panel names it.** Acceptance criterion 7 | Press save twice |
| B11 | **The real path is never guessed.** Acceptance criterion 7 | Run once with `YOTO_DOCUMENTS_DIR` pointed at a redirected-looking path, and once on a OneDrive-redirected Documents if one is reachable. The panel's path and Settings' *Where saved files go* must both show the real one |
| B12 | **The degraded path.** `copy.md` §5.5 | Monkeypatch `reveal_supported()` to `False` (or run from source on macOS/Linux): the button must be **absent**, and the `.mono-value` path must wrap inside the column at 320px — `interactions.md` §7's named regression |
| B13 | **The everyday-path ledger.** Acceptance criterion 4 | With nothing pressed, step 3 gains exactly one `.btn` and two lines of 13px text, both below `🚀 Send to Yoto` and below every existing feedback box |
| B14 | **`styles.css` is unmodified.** Acceptance criterion 10 | `git diff --stat` names no `styles.css` |
| B15 | **Focus and announcements** | On success focus lands on `#exportDone` and the next Tab is `📄 What to do next`; on a partial result focus lands on `#exportError` instead |

### C. The first real-world test, and what it does and does not exercise

The planned first end-to-end run is a YouTube audiobook — *The Wild Robot*,
~3h50m.

**At 192 kbps that is ~5 parts of ~72 MB each, ~330 MB total.** Against Yoto's
published ceilings: comfortably inside 100 MB per track, 500 MB per card, 5 hours
per card and 100 tracks per card.

So it **does** exercise: multi-part splitting, zero-padded filename ordering
across a five-file web upload, the split note in both the panel and the sheet,
and the whole upload procedure end to end.

It **does not** exercise: the 100 MB per-track advisory, or any card-level
ceiling. Nothing in this card comes near them. Reaching the per-track cap needs a
**local WAV or FLAC** — and note the asymmetry that makes it hard to hit on this
path: the YouTube source arrives as `.mp3` and is therefore *copied*, never
converted, so it is exactly the case the app advises about rather than acts on.
If B4 above is skipped, the oversize advisory ships **unverified against a real
file** and must be recorded as such in the PR body.

### Z. What nobody can verify, and why that must be said out loud

**The maintainer has no Yoto player.** His daughter owns it and lives in another
state. That inverts the usual UAT story and this PR must not pretend otherwise.

| Verifiable by | What |
| --- | --- |
| **Builder, locally** | The folder is written correctly; filenames are zero-padded and ordered; conversion fires on the right inputs at 192 kbps; the sheet renders and is self-contained; the reveal button works in the frozen `.exe`; the job does not block the event loop. All of §A and §B |
| **The maintainer, by hand** | That `my.yotoplay.com` accepts the files, that the tracks land in the right order, and that the card assembles on the website. §C |
| **Nobody, in this PR** | **The motivating defect itself** |

**The defect this feature exists to route around is a physical player's offline
download never completing.** No part of it can be observed without the player.

> ⚠ **Streaming in the phone app will very likely work fine even on a malformed
> card — that is why this bug survived three releases. A card that plays in the
> app is NOT evidence of a fix.** Anyone reporting "it works" from the phone app
> has confirmed nothing about this defect.

**What to ask the daughter.** Keep it to three questions she can answer without
debugging anything, after she has linked the card:

1. **Does the card show up on the player at all** when you tap it — does the
   player's screen show the card's name?
2. **Does it finish downloading for offline?** In the Yoto app, turn the download
   on for that card and tell me whether it reaches 100% and stops, or sits there.
3. **Does it play with the wi-fi turned off?** Turn wi-fi off on the player and
   press play — does it play the whole way through, or stop?

Question 2 is the one that matters. Question 3 is the confirmation. Question 1
rules out a mis-linked card, so a "no" on 1 means the other two answers say
nothing. **The feedback loop is remote and slow — ask all three at once, and ask
for the card's name so the answer can be tied to a specific upload.**

---

## Deviations, judgement calls, and gaps the handoff does not close

Surfaced rather than buried. Four are Planner decisions the spec did not make;
three are places where `copy.md` is silent and the implementer would otherwise
invent something.

1. **Total-failure reasons are composed server-side; the frame is composed in
   JS.** `jobs.py` captures only `str(exc)` and has no `reason` field, and adding
   one is job-runner work this PR is forbidden from doing (spec §2.8, ADR arc).
   So `copy.md` §5.7's middle paragraph comes from `export/errors.py` and the
   first and third from `app.js`. **Not a design change** — the rendered
   paragraphs are exactly what `copy.md` specifies.

2. **Zero tracks saved is a TOTAL failure, not a partial one.** `copy.md` §5.1
   has no *"0 of your 5"* variant, and §5.7's *"Nothing was saved"* is precisely
   that case. The folder is removed. **Planner inference** — flag it to Designer
   if it reads wrongly.

3. **Card duration is summed from the draft's probed track durations, not
   re-probed from the written files.** Spec §3.3 says the three card totals must
   be measured *"from the files as written"*, and the reason it gives is that
   conversion changes **size**. Conversion does not change duration, so the two
   numbers are identical and re-probing would cost one `ffprobe` subprocess per
   track. **Size is measured from disk**, as specified. Called out because a
   reviewer reading §3.3 literally will look for a second probe loop.

4. **`normalize_to_mp3` failing is reported as a per-track failure using the
   existing `AudioError` string's first two sentences**, with the
   `"Technical detail: …"` tail dropped — that tail is a developer string and
   `copy.md`'s register bans it from this panel. `copy.md` §5.6 says `{reason}`
   uses the app's existing plain-language file errors *"where they apply"*, which
   anticipates this but does not name it.

5. **`copy.md` gives no plural for the split note.** §5.3 is written for one
   split track (*"One of your tracks was too long… “{title}” is in {n} parts"*),
   and `overview.md` §10.3's table calls it one paragraph. A card with **two**
   split tracks has no specified wording. **Implemented as one paragraph per
   split group**, each naming its own title, which keeps every sentence true and
   preserves the fixed ordering. **Designer should confirm or supply a plural.**

6. **`copy.md` §5.9's plural per-track list says `{list, with each size}` without
   giving a format.** Implemented as `01 - Title (118 MB)`, matching the
   `NN - Title` shape §5.4's list already uses. **Minor; confirm.**

7. **Two new strings this plan authors, because nothing in `copy.md` covers
   them.** Both are one sentence and both are flagged for Designer:
   `"There’s nothing saved to open yet."` and
   `"Yoto Maker couldn’t open the folder."` — the *runtime* failure of
   `📂 Open the folder`. `copy.md` §5.5 covers only the pre-emptive omission
   case; `interactions.md` §4.4 says a runtime failure "renders into
   `#exportError`" without saying what it renders.

8. **The card picture is downscaled to 360px before being embedded in the
   sheet.** The written `Card picture.png` is untouched and is what she uploads;
   only the sheet's `<img>` is smaller. Without this the page carries ~1.4 MB of
   base64 for a 180px thumbnail. `mockups/instruction-sheet.md` §1 shows the
   sheet at 18 KB, which is only achievable this way.

9. **A stale mockup, which the implementer will hit.**
   `mockups/step-3.md` §7 still shows `copy.md` §5.4's **pre-amendment** wording
   (*"2 of your files weren't MP3s, so Yoto Maker saved MP3 copies…"*).
   `copy.md` §5.4 was amended on 2026-09-05 precisely because that phrasing is
   quietly misleading once `.m4a` and `.aac` are copied as-is. **`copy.md` wins —
   it is the declared authority on strings.** Worth a one-line correction to the
   mockup in a later pass; not this PR's job.

10. **Two harmless cross-reference drifts in the handoff**, noted so nobody
    chases them: `overview.md` §6.2 and §10.4 cite `copy.md` §6.7 for the
    missing-track notice, which is actually `copy.md` §6.8; and `overview.md`
    §15's criterion 4 says *"one line of 13px text"* where the spec's §8 and the
    mockups say *"two lines"* (the caption is one sentence pair that wraps to
    two lines at 720px). Neither changes anything to build.

---

## For the queue

**One item surfaced during planning and is now filed as queue item 20** — a
pre-existing defect on the **shipped authenticated send path**, independent of
this feature:

> The app splits on **duration only** (`MAX_TRACK_SECONDS = 3000`,
> `normalize.py:191`, applied at `app.py:235`) and never checks bytes, while Yoto
> caps a single track at **100 MB**. Because the app does not transcode local
> files, a local WAV at that 50-minute bound is ~529 MB. Compounding it,
> `client.py:481-482` maps a 413 to *"That audio file is too big for Yoto (max 5
> hours per card)"* — the **card-level** limit, when the user has almost
> certainly hit the **per-track** one.

**Export-only mode is immune and does not fix it.** This path converts anything
outside `{.mp3,.m4a,.aac}` to 192 kbps MP3, which is ~72 MB at the same 50-minute
bound. The two items do not overlap and neither blocks the other. See item 20's
briefing notes.
