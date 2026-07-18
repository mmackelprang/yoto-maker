"""Central configuration: where things live on disk, and app-wide settings.

Everything that touches the filesystem goes through here so the rest of the app
never hard-codes a path. On Windows the per-user data dir is
``%LOCALAPPDATA%\\YotoMaker``.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _local_appdata() -> Path:
    """Return the per-user writable data directory for this app."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "YotoMaker"
    # macOS / Linux fallbacks (dev only; v1 target is Windows)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "YotoMaker"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "YotoMaker"


def _bundle_root() -> Path:
    """Directory containing bundled resources.

    When frozen by PyInstaller, resources live under ``sys._MEIPASS``. In dev we
    use the package's parent (repo root).
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


# The Yoto public client ID, registered at dashboard.yoto.dev. This is a PKCE
# *public* client id — it is NOT a secret (it's sent in the browser sign-in URL
# by design), so shipping it in the app and committing it is safe and standard.
# It's resolved at runtime in order: YOTO_CLIENT_ID env var → saved setting →
# this baked-in default, so a user can still point the app at their own Yoto app
# without a rebuild.
DEFAULT_YOTO_CLIENT_ID = "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"


def resolve_client_id() -> str:
    """Client ID from env var, then saved setting, then the baked-in default."""
    env = os.environ.get("YOTO_CLIENT_ID")
    if env:
        return env.strip()
    try:
        from .settings import get_settings  # lazy import to avoid a cycle

        saved = get_settings().get("yoto_client_id")
        if saved:
            return str(saved).strip()
    except Exception:
        pass
    return DEFAULT_YOTO_CLIENT_ID

YOTO_AUTH_BASE = "https://login.yotoplay.com"
YOTO_API_BASE = "https://api.yotoplay.com"
YOTO_SCOPES = "user:content:manage offline_access"
# Loopback redirect for the PKCE flow (port chosen at runtime if busy).
YOTO_REDIRECT_HOST = "127.0.0.1"
YOTO_REDIRECT_PATH = "/yoto/callback"


@dataclass(frozen=True)
class Config:
    data_dir: Path = field(default_factory=_local_appdata)
    bundle_root: Path = field(default_factory=_bundle_root)
    yoto_client_id: str = field(default_factory=resolve_client_id)
    # Bind the local UI server to loopback only — never exposed to the network.
    host: str = "127.0.0.1"
    port: int = 8777

    # ---- derived paths -------------------------------------------------
    @property
    def work_dir(self) -> Path:
        """Scratch space for downloaded/transcoded audio and images."""
        return self.data_dir / "work"

    @property
    def token_path(self) -> Path:
        """Cached Yoto OAuth tokens (refresh token). Never committed."""
        return self.data_dir / "yoto_token.json"

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "yoto-maker.log"

    @property
    def vendor_dir(self) -> Path:
        """Where bundled/downloaded ffmpeg + yt-dlp live."""
        # Prefer bundled binaries; fall back to a writable per-user copy.
        bundled = self.bundle_root / "vendor"
        return bundled if bundled.exists() else (self.data_dir / "vendor")

    @property
    def icons_dir(self) -> Path:
        """Bundled kid-friendly pixel-icon library."""
        return self.bundle_root / "yoto_maker" / "server" / "static" / "icons"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.work_dir, self.data_dir / "vendor"):
            p.mkdir(parents=True, exist_ok=True)


# Singleton-style accessor; tests can build their own Config.
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_dirs()
    return _config


def set_config(cfg: Config) -> None:
    """Override the active config (used by tests)."""
    global _config
    _config = cfg
