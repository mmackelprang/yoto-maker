"""Locate the external tools we depend on: ffmpeg / ffprobe.

Resolution order:
1. A binary bundled next to the app (``vendor/``) — the normal case for an
   installed build.
2. A binary on the system ``PATH`` — the normal case in development.

yt-dlp is used as a *Python library* (it's a pip dependency), so it needs no
separate binary. We still expose a check so the UI can report a clear status.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import get_config


class ToolsMissingError(RuntimeError):
    """Raised when a required tool can't be found. Message is user-friendly."""


def _exe(name: str) -> str:
    return f"{name}.exe" if sys.platform.startswith("win") else name


def _find(name: str) -> str | None:
    """Find a tool binary in vendor/ then on PATH. Returns absolute path or None."""
    cfg = get_config()
    candidate = cfg.vendor_dir / _exe(name)
    if candidate.exists():
        return str(candidate)
    found = shutil.which(name)
    return found


def find_ffmpeg() -> str | None:
    return _find("ffmpeg")


def find_ffprobe() -> str | None:
    return _find("ffprobe")


def yt_dlp_available() -> bool:
    try:
        import yt_dlp  # noqa: F401

        return True
    except Exception:  # pragma: no cover - environment specific
        return False


@dataclass
class ToolStatus:
    ffmpeg: str | None
    ffprobe: str | None
    yt_dlp: bool

    @property
    def ok(self) -> bool:
        # ffprobe ships with ffmpeg; if ffmpeg is present we can still work
        # without a separate ffprobe (we fall back to ffmpeg for probing).
        return bool(self.ffmpeg) and self.yt_dlp


def check_tools() -> ToolStatus:
    return ToolStatus(
        ffmpeg=find_ffmpeg(),
        ffprobe=find_ffprobe(),
        yt_dlp=yt_dlp_available(),
    )


def require_ffmpeg() -> str:
    path = find_ffmpeg()
    if not path:
        raise ToolsMissingError(
            "We couldn't find the audio converter (ffmpeg) that this app needs. "
            "If you installed Yoto Maker with the installer this shouldn't happen "
            "— please reinstall, or ask for help."
        )
    return path


def require_ffprobe() -> str:
    """Return ffprobe, falling back to ffmpeg's built-in probing if absent."""
    return find_ffprobe() or require_ffmpeg()
