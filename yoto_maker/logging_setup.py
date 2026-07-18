"""Quiet, file-based logging. The user never sees this; it's for debugging.

Writes to ``%LOCALAPPDATA%\\YotoMaker\\yoto-maker.log`` with rotation so it can't
grow without bound.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import get_config

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    cfg = get_config()
    cfg.ensure_dirs()
    handler = RotatingFileHandler(cfg.log_path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Keep third-party noise out of the log.
    for noisy in ("uvicorn.access", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True
