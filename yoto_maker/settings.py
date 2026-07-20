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

    def delete(self, key: str) -> bool:
        """Remove a *saved* key. Returns True if something was actually removed.

        Reads the raw file rather than _load(), because _load() merges _DEFAULTS
        in — so a key that has a default would look present even when nothing was
        ever saved, and would reappear at its default value on the next read.
        Nothing in _DEFAULTS is deletable in that stronger sense; `yoto_client_id`
        is not a default, so for it this really is "forget it".
        """
        path = get_config().settings_path
        raw: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    raw = dict(loaded)
            except Exception:
                raw = {}
        if key not in raw:
            return False
        raw.pop(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return True

    def all(self) -> dict[str, Any]:
        return _load()


_instance = _Settings()


def get_settings() -> _Settings:
    return _instance
