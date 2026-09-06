"""Saving a finished card to a folder the user uploads herself.

Design: docs/design-handoffs/export-only-mode/. The package is named for the
operation; **no string it produces for a user contains the word "export"** — the
verb is *save*, the noun is *files*, the destination is *a folder*.
"""
from __future__ import annotations

from .errors import ExportError, NameTooLongError

__all__ = ["ExportError", "NameTooLongError"]
