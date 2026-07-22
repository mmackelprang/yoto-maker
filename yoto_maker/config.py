"""Central configuration: where things live on disk, and app-wide settings.

Everything that touches the filesystem goes through here so the rest of the app
never hard-codes a path. On Windows the per-user data dir is
``%LOCALAPPDATA%\\YotoMaker``.
"""
from __future__ import annotations

import os
import re
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


def _resolve_client_id_with_source() -> tuple[str, str]:
    """The single precedence chain: env var → saved setting → baked-in default.

    Returns ``(client_id, source)`` where source is "env" | "saved" | "builtin".
    Both resolve_client_id() and client_id_source() delegate here, so the value in
    effect and the label the UI reports it under cannot drift apart — the settings
    screen hides its reset action based on that label, and a label that disagreed
    with the value would make the screen lie.
    """
    env = os.environ.get("YOTO_CLIENT_ID")
    if env and env.strip():
        return env.strip(), "env"
    try:
        from .settings import get_settings  # lazy import to avoid a cycle

        saved = get_settings().get("yoto_client_id")
        if saved and str(saved).strip():
            return str(saved).strip(), "saved"
    except Exception:
        pass
    return DEFAULT_YOTO_CLIENT_ID, "builtin"


def resolve_client_id() -> str:
    """Client ID from env var, then saved setting, then the baked-in default."""
    return _resolve_client_id_with_source()[0]


def client_id_source() -> str:
    """Which tier of the chain supplied the effective Client ID."""
    return _resolve_client_id_with_source()[1]


def resolve_client_id_with_source() -> tuple[str, str]:
    """The chain's public form: ``(client_id, source)`` from one traversal.

    Any caller that needs both MUST use this rather than calling
    resolve_client_id() and client_id_source() in sequence. Two traversals read
    the env var and settings.json independently, so a settings write landing
    between them would report a value under the wrong source label — and the
    settings screen decides what to show, and what to hide, from that label.
    """
    return _resolve_client_id_with_source()


def mask_client_id(cid: str) -> str:
    """First 4 + last 3 of the Client ID, for recognition on a phone call.

    Not a security measure — a PKCE public client ID is not a secret (see the
    note on DEFAULT_YOTO_CLIENT_ID). This exists so a user can confirm *which*
    ID is in effect without a 32-character string on screen.
    """
    cid = (cid or "").strip()
    if len(cid) <= 8:
        return cid
    return f"{cid[:4]}…{cid[-3:]}"


# The shape Yoto issues today, confirmed against DEFAULT_YOTO_CLIENT_ID above.
# ADVISORY ONLY — see validate_client_id().
_CLIENT_ID_SHAPE = re.compile(r"^[A-Za-z0-9]{32}$")

# A sanity limit, not a format rule: it exists so settings.json cannot be filled
# with prose. Any real paste this long almost certainly contains whitespace and
# will have been caught already.
CLIENT_ID_MAX_LEN = 128


def validate_client_id(cid: str | None) -> tuple[str, str | None]:
    """Classify a Client ID. Returns ``(verdict, reason)``.

    verdict: "ok" | "unusual" | "invalid"
    reason:  None | "email" | "url" | "spaces" | "length" | "charset" | "too_long"

    THE HARD GATE IS THE DENY-LIST BELOW, NOT _CLIENT_ID_SHAPE. That distinction
    is load-bearing and it is not a style preference:

      * A hard gate's failure mode is a lockout with no override. It may
        therefore only fire on shapes that are wrong REGARDLESS of format. "@"
        is not a character in an opaque identifier — it is the character that
        means *address*. "/" and ":" mean *URL*, and that is a live designed-in
        risk, not a hypothetical: SETUP-YOTO-CONNECTION.md:30 prints
        http://127.0.0.1:8777/yoto/callback directly beside the Client ID the
        user is told to copy. Interior whitespace means a phrase, or a paste
        that grabbed a line break. None of these can become valid if Auth0
        changes its format.
      * _CLIENT_ID_SHAPE is knowledge about a third party's CURRENT format and
        this app has no way to learn that it has changed. As a hard gate it
        would block every legitimate ID the day Yoto issues 40-character or
        UUID-shaped ones, and tell the user in red that her correct value is
        wrong. So it only ever produces "unusual", which warns and proceeds.

    Deliberately NOT denied, and each exclusion demonstrates the principle:
      "." — a domain has one, but so do real identifiers
            (…apps.googleusercontent.com), and the cost of being wrong is a
            lockout.
      "-" and "_" — the two commonest characters in machine identifiers.
            Denying them would be the fastest possible way to build the lockout
            this function exists to prevent. "test_client_id" in
            tests/conftest.py:26 is a live in-tree example.

    There is no lower length bound. A 3-character value is obviously wrong, but
    "obviously" there is format knowledge, and format knowledge does not get to
    hard-block.

    See docs/design-handoffs/configuration-surface/overview.md §13.2.
    """
    trimmed = (cid or "").strip()

    # Order matters. Character checks precede the length bound so a pasted
    # document reports what it actually is rather than "too long"; "@" precedes
    # "/" and ":" so a value that is both reports the email case, which is the
    # incident's case and the more actionable diagnosis.
    if not trimmed:
        return "invalid", "length"
    if "@" in trimmed:
        return "invalid", "email"
    if "/" in trimmed or ":" in trimmed:
        return "invalid", "url"
    if "<" in trimmed or ">" in trimmed:
        return "invalid", "charset"
    if any(ch.isspace() for ch in trimmed):
        # The strip() above means anything left is INTERIOR whitespace.
        return "invalid", "spaces"
    if len(trimmed) > CLIENT_ID_MAX_LEN:
        return "invalid", "too_long"

    if not _CLIENT_ID_SHAPE.match(trimmed):
        return "unusual", "charset"
    return "ok", None


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
    # Snapshot taken when the singleton is built. DO NOT read this at runtime:
    # a Client ID saved after startup would not appear here. Everything in the
    # app calls resolve_client_id() / client_id_source() live. Kept because
    # tests/conftest.py constructs Config with an explicit value.
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
