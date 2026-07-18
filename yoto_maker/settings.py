"""Tiny JSON-backed settings store (per-user, in the app data dir).

Holds non-secret preferences and the optional AI key. Kept deliberately simple:
load-on-read, write-on-set. Never committed to git.
"""
from __future__ import annotations

import json
from typing import Any

from .config import get_config

_DEFAULTS: dict[str, Any] = {
    "ai_model": "gpt-image-1",
    # Skip advertising segments in YouTube audio (SponsorBlock). On by default.
    "remove_sponsors": True,
}


def _load() -> dict[str, Any]:
    path = get_config().settings_path
    if not path.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(_DEFAULTS)
        merged.update(data if isinstance(data, dict) else {})
        return merged
    except Exception:
        return dict(_DEFAULTS)


class _Settings:
    def get(self, key: str, default: Any = None) -> Any:
        return _load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = _load()
        data[key] = value
        path = get_config().settings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def all(self) -> dict[str, Any]:
        return _load()


_instance = _Settings()


def get_settings() -> _Settings:
    return _instance
