"""Saving a finished card to a folder the user uploads herself.

Design: docs/design-handoffs/export-only-mode/. The package is named for the
operation; **no string it produces for a user contains the word "export"** — the
verb is *save*, the noun is *files*, the destination is *a folder*.
"""
from __future__ import annotations

from .errors import (
    REASON_CANNOT_OPEN,
    REASON_FOLDER_GONE,
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
    "REASON_FOLDER_GONE",
    "SHEET_NAME",
    "CARD_PICTURE_NAME",
    "TRACK_PICTURES_DIR",
]
