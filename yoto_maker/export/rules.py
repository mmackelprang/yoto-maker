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
