"""Audio source adapters. v1: YouTube + local audio file."""
from __future__ import annotations

from .base import SourceError, SourceResult
from .audiofile import AudioFileAdapter
from .youtube import YouTubeAdapter

__all__ = ["SourceResult", "SourceError", "YouTubeAdapter", "AudioFileAdapter"]
