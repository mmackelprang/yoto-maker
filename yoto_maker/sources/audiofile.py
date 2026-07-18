"""Local audio-file source adapter (mp3 / m4a / wav / flac / ogg).

Copies the file into the work dir, reads a suggested title from tags (falling
back to the filename), and extracts embedded cover art if present.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ..audio.normalize import probe_audio
from .base import SourceError, SourceResult

SUPPORTED_EXT = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".mp4", ".opus"}


class AudioFileAdapter:
    kind = "file"

    def can_handle(self, user_input: str) -> bool:
        try:
            return Path(user_input).suffix.lower() in SUPPORTED_EXT
        except Exception:
            return False

    def fetch(self, user_input: str, work_dir: Path) -> SourceResult:
        src = Path(user_input)
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        if not src.exists():
            raise SourceError(f"That file could not be found: {src.name}")
        if src.suffix.lower() not in SUPPORTED_EXT:
            raise SourceError(
                f"'{src.suffix}' files aren't supported yet. Try an MP3, M4A or WAV file."
            )

        dest = work_dir / src.name
        try:
            # If the file is already where we'd copy it, just use it in place.
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
        except shutil.SameFileError:
            dest = src
        except OSError as exc:
            raise SourceError("We couldn't read that file — it may be open in another program.") from exc

        title, image_path = self._read_metadata(dest, work_dir)
        try:
            duration = probe_audio(dest).duration_s
        except Exception:
            duration = 0.0

        return SourceResult(
            audio_path=dest,
            suggested_title=title,
            source_kind=self.kind,
            duration_s=duration,
            suggested_image_path=image_path,
            source_ref=src.name,
        )

    @staticmethod
    def _read_metadata(path: Path, work_dir: Path) -> tuple[str, Path | None]:
        """Return (title, cover_image_path_or_None) using mutagen best-effort."""
        title = path.stem.replace("_", " ").strip()
        image_path: Path | None = None
        try:
            from mutagen import File as MutagenFile

            mf = MutagenFile(str(path))
            if mf is not None:
                title = _tag_title(mf) or title
                image_path = _extract_cover(mf, work_dir / f"{path.stem}_cover")
        except Exception:
            pass  # tags are a nice-to-have; never fail the import over them
        return title, image_path


def _tag_title(mf) -> str | None:
    tags = getattr(mf, "tags", None)
    if not tags:
        return None
    for key in ("TIT2", "title", "\xa9nam", "Title"):
        try:
            value = tags.get(key)
        except Exception:
            value = None
        if value:
            text = value.text[0] if hasattr(value, "text") else value
            text = str(text[0] if isinstance(text, list) else text).strip()
            if text:
                return text
    return None


def _extract_cover(mf, out_stem: Path) -> Path | None:
    """Pull embedded APIC/cover art to a file; return its path or None."""
    data: bytes | None = None
    ext = ".jpg"
    try:
        # ID3 (mp3)
        if getattr(mf, "tags", None):
            for key in mf.tags.keys():
                if key.startswith("APIC"):
                    apic = mf.tags[key]
                    data = apic.data
                    ext = ".png" if "png" in (apic.mime or "").lower() else ".jpg"
                    break
        # MP4 / M4A cover
        if data is None and hasattr(mf, "tags") and mf.tags and "covr" in mf.tags:
            covr = mf.tags["covr"][0]
            data = bytes(covr)
        # FLAC / OGG pictures
        if data is None and getattr(mf, "pictures", None):
            data = mf.pictures[0].data
    except Exception:
        return None

    if not data:
        return None
    out = out_stem.with_suffix(ext)
    try:
        out.write_bytes(data)
        return out
    except OSError:
        return None
