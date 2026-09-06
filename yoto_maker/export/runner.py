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
    TRACK_PICTURES_DIR,
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
# Re-exported, not redefined: names.py owns it because it is part of the path
# budget there (a track's picture sits one segment deeper than its audio).

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
        folder = _claim_folder(root, folder_name)
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


# How many times to re-resolve a taken name before giving up. A few dozen covers
# any plausible number of saves racing for one card name; past that something
# other than a race is wrong and the generic failure is the honest answer.
_FOLDER_ATTEMPTS = 40


def _claim_folder(root: Path, name: str) -> Path:
    """Resolve the next free name and create it, re-resolving if we lose a race.

    unique_dir() is a probe followed by a create, so two saves of the same card
    resolve to the SAME candidate and the loser's mkdir() raises FileExistsError
    — which _os_reason maps to the generic failure, reporting a fault for what is
    only a collision. Re-resolving is the whole fix.

    mkdir() without ``exist_ok`` is what keeps this safe: the winner's folder is
    never opened, never written into and never overwritten (overview.md §5.2), so
    the " (2)" behaviour is exactly what it was. The last attempt is deliberately
    unguarded — it falls through to export_card's existing OSError handling.
    """
    for _ in range(_FOLDER_ATTEMPTS - 1):
        folder = unique_dir(root, name)
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        return folder
    folder = unique_dir(root, name)
    folder.mkdir()
    return folder


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
        # copy.md §5.1's zero case is a TOTAL failure, not a partial one: the
        # folder unwinds below and copy.md §5.7's "Nothing was saved" stays
        # literally true. When every track failed individually a single cause
        # line would be a guess, so §5.7's fourth row reuses §5.6's numbered
        # list rather than inventing a format.
        raise ExportError(_all_failed_message(failures, len(tracks)))

    say("pictures", 82, "Saving the pictures…")
    has_picture, has_track_pictures = _write_pictures(folder, picture_path, saved)

    say("sheet", 92, "Writing the instructions…")
    data = SheetData(
        card_name=folder.name,
        files=saved,
        failures=[f.title for f in failures],
        advisories=advise(saved),
        split=split_groups(saved),
        picture_png=_sheet_picture(folder / CARD_PICTURE_NAME) if has_picture else None,
        has_card_picture_file=has_picture,
        has_track_pictures=has_track_pictures,
        version=version,
        date_label=date_words(today),
    )
    try:
        # write_bytes, not write_text: text mode translates "\n" to "\r\n" on
        # Windows, so the file on disk would no longer be byte-identical to what
        # GET /api/export/sheet.html serves. overview.md §6.3's "one file, one
        # rendering, both routes" is a byte-identity claim, and this is what
        # keeps it literally true.
        (folder / SHEET_NAME).write_bytes(render_sheet(data).encode("utf-8"))
    except OSError as exc:
        raise ExportError(_os_reason(exc)) from exc

    say("done", 100, "Saved.")
    return ExportResult(folder=folder, files=saved, failures=failures, total_count=len(tracks))


def _all_failed_message(failures: list[Failure], total: int) -> str:
    """copy.md §5.7's every-track-failed row. Newline-separated paragraphs.

    jobs.py carries only str(exc) (jobs.py:70-73) and this PR does not extend
    it, so the paragraph break travels as a newline and app.js splits on it.
    """
    if not failures:
        return REASON_GENERIC
    lines = [f"None of your {total} tracks could be saved:"]
    lines += [f"{i}. “{f.title}” — {f.reason}" for i, f in enumerate(failures, start=1)]
    return "\n".join(lines)


def _write_pictures(folder: Path, picture_path, saved: list[SavedFile]) -> tuple[bool, bool]:
    """Best-effort. A picture must never fail a save that has the audio in it.

    Returns ``(card picture written, track-pictures subfolder written with at
    least one picture in it)``. The second value exists because the sheet's
    paragraph about that subfolder is CONDITIONAL (overview.md §9.2, spec §2.6
    requirement 1: the sheet is generated from what actually landed on disk) and
    every branch below can silently decline to create it.
    """
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
        return has_picture, False
    pics = folder / TRACK_PICTURES_DIR
    try:
        pics.mkdir(exist_ok=True)
    except OSError as exc:
        log.warning("save: could not make the pictures folder: %s", exc)
        return has_picture, False
    written = 0
    for f in wanted:
        try:
            shutil.copy2(f.icon_path, pics / (Path(f.name).stem + ".png"))
            written += 1
        except OSError as exc:
            log.warning("save: could not write a track picture: %s", exc)
    return has_picture, written > 0


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
