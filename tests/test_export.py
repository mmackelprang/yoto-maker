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
