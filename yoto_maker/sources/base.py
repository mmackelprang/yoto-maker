"""Common contract every audio source must satisfy.

A source turns *something the user provided* (a URL, a file path) into a
normalized :class:`SourceResult` that the rest of the app understands, without
downstream code caring whether it came from YouTube or a file.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SourceError(RuntimeError):
    """User-friendly failure while fetching a source (bad link, missing file...)."""


@dataclass
class SourceResult:
    """Everything downstream needs from one imported item."""

    audio_path: Path
    suggested_title: str
    source_kind: str  # "youtube" | "file"
    duration_s: float = 0.0
    suggested_image_path: Path | None = None  # thumbnail / embedded art, if any
    source_ref: str = ""  # original URL or filename, for logs/labels

    def __post_init__(self) -> None:
        self.audio_path = Path(self.audio_path)
        if self.suggested_image_path is not None:
            self.suggested_image_path = Path(self.suggested_image_path)


class SourceAdapter(Protocol):
    """Implemented by YouTubeAdapter, AudioFileAdapter, and future adapters."""

    kind: str

    def can_handle(self, user_input: str) -> bool:
        """True if this adapter recognizes the given input (URL or path)."""
        ...

    def fetch(self, user_input: str, work_dir: Path) -> SourceResult:
        """Produce audio + metadata into ``work_dir``. Raises SourceError."""
        ...
