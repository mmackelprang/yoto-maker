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

# The subfolder the runner puts per-track pictures in. It lives HERE rather than
# in runner.py because it is part of the path budget below — a track's picture is
# written one level deeper than its audio, and the length of this name is exactly
# how much deeper. runner.py imports it from here so there is still one constant.
TRACK_PICTURES_DIR = "Track pictures"

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

    The budget is measured against the DEEPEST path this name produces, which is
    the track picture — ``<folder>\\Track pictures\\<name>.png``, one segment and
    one separator further down than the audio file itself. Budgeting for the audio
    alone put the picture 15 characters over: with long paths disabled (the
    Windows default) that write fails, the runner swallows it as a log warning,
    and the pictures vanish while the sheet says they are there.

    ``len(ext)`` stands in for the picture's ``.png`` as well: every suffix this
    is given comes from output_suffix(), i.e. ``.mp3`` or a member of COPY_AS_IS,
    and all of them are four characters — the same as ``.png``.
    """
    prefix = f"{index:0{number_width(total)}d} - "
    safe = sanitize_component(title, fallback=FALLBACK_TRACK_TITLE)
    deeper = len(TRACK_PICTURES_DIR) + 1
    room = MAX_PATH_CHARS - len(str(folder)) - 1 - deeper - len(prefix) - len(ext)
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
