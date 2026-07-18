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


# The Yoto public client ID is registered once at dashboard.yoto.dev and shipped
# with the app (PKCE = no secret needed). It can be overridden via env var so
# the developer can test with their own client without editing code.
DEFAULT_YOTO_CLIENT_ID = os.environ.get("YOTO_CLIENT_ID", "")

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
    yoto_client_id: str = DEFAULT_YOTO_CLIENT_ID
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
