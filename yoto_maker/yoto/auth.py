"""Yoto OAuth2 Authorization-Code flow with PKCE.

Why PKCE + a public client: the app ships a public Client ID (registered once at
dashboard.yoto.dev) and needs **no secret**. The user clicks "Connect", signs in
on Yoto's own website, and we exchange the returned code for tokens. The refresh
token is cached so future runs are silent.

The redirect lands back on *this app's own local server* at
``http://127.0.0.1:<port>/yoto/callback`` — so no second server is needed. That
exact URL must be registered as an allowed redirect for the client.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from ..config import get_config
from .. import config as config_mod


class NotConnectedError(RuntimeError):
    """Raised when an API call needs auth but the user hasn't connected Yoto."""


class AuthError(RuntimeError):
    """User-friendly authentication failure."""


# In-memory store for the pending login (verifier + state) between redirect and
# callback. Fine because the whole flow happens in one short-lived browser trip.
_pending: dict[str, str] = {}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _redirect_uri() -> str:
    cfg = get_config()
    return f"http://{cfg.host}:{cfg.port}{config_mod.YOTO_REDIRECT_PATH}"


def _client_id() -> str:
    cid = config_mod.resolve_client_id()
    if not cid:
        raise AuthError(
            "This copy of the app hasn't been set up with a Yoto Client ID yet. "
            "(One-time setup step — see docs/SETUP-YOTO-CONNECTION.md.)"
        )
    return cid


# --------------------------------------------------------------------------- #
# Login flow
# --------------------------------------------------------------------------- #
def start_login() -> str:
    """Begin login: return the Yoto authorize URL to send the user's browser to."""
    verifier = _b64url(os.urandom(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = _b64url(os.urandom(16))
    _pending.clear()
    _pending.update(verifier=verifier, state=state)

    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "scope": config_mod.YOTO_SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        # Yoto uses Auth0; audience selects the API.
        "audience": config_mod.YOTO_API_BASE,
    }
    return f"{config_mod.YOTO_AUTH_BASE}/authorize?{urlencode(params)}"


def finish_login(code: str, state: str) -> None:
    """Handle the redirect callback: validate state, exchange code for tokens."""
    if not _pending or state != _pending.get("state"):
        raise AuthError("The sign-in didn't match what we expected. Please try connecting again.")
    verifier = _pending.get("verifier", "")
    data = {
        "grant_type": "authorization_code",
        "client_id": _client_id(),
        "code": code,
        "redirect_uri": _redirect_uri(),
        "code_verifier": verifier,
    }
    tokens = _token_request(data)
    _save_tokens(tokens)
    _pending.clear()


# --------------------------------------------------------------------------- #
# Token storage + refresh
# --------------------------------------------------------------------------- #
def _token_request(data: dict) -> dict:
    try:
        resp = httpx.post(
            f"{config_mod.YOTO_AUTH_BASE}/oauth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise AuthError("Yoto rejected the sign-in. Please try connecting again.") from exc
    except Exception as exc:
        raise AuthError("We couldn't reach Yoto to finish signing in. Check your internet.") from exc


def _save_tokens(tokens: dict) -> None:
    tokens = dict(tokens)
    if "expires_in" in tokens:
        tokens["expires_at"] = time.time() + float(tokens["expires_in"]) - 60
    path = get_config().token_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load_tokens() -> dict | None:
    path = get_config().token_path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def logout() -> None:
    path = get_config().token_path
    path.unlink(missing_ok=True)


def get_access_token() -> str:
    """Return a valid access token, refreshing if needed. Raises NotConnectedError."""
    tokens = _load_tokens()
    if not tokens:
        raise NotConnectedError("Yoto isn't connected yet.")

    if tokens.get("expires_at", 0) > time.time() and tokens.get("access_token"):
        return tokens["access_token"]

    refresh = tokens.get("refresh_token")
    if not refresh:
        raise NotConnectedError("Your Yoto sign-in has expired. Please connect again.")

    new = _token_request(
        {
            "grant_type": "refresh_token",
            "client_id": _client_id(),
            "refresh_token": refresh,
        }
    )
    # Auth0 may or may not rotate the refresh token; keep the old one if absent.
    new.setdefault("refresh_token", refresh)
    _save_tokens(new)
    return new["access_token"]


def connection_status() -> dict:
    """A UI-friendly summary: connected? which Client ID is in effect?

    ``connected`` here means only "a saved sign-in exists on this computer" — it
    is cheap and does not touch the network. For "does it actually still work",
    which is what the settings screen shows, use check_connection().
    """
    cid = config_mod.resolve_client_id()
    return {
        # Legacy: resolve_client_id() falls back to a non-empty constant, so this
        # is permanently True and carries no information. Kept so nothing that
        # reads it breaks; no new UI may depend on it.
        "configured": bool(cid),
        "connected": _load_tokens() is not None,
        "client_id_source": config_mod.client_id_source(),
        "client_id_masked": config_mod.mask_client_id(cid),
    }
