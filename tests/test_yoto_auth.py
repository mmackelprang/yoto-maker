"""Yoto OAuth (PKCE) tests — URL building, token save/load, refresh. No network."""
from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

import pytest

from yoto_maker.yoto import auth


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


def test_start_login_url_has_pkce(temp_config):
    url = auth.start_login()
    q = parse_qs(urlparse(url).query)
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["test_client_id"]
    assert q["code_challenge_method"] == ["S256"]
    assert "code_challenge" in q and len(q["code_challenge"][0]) > 20
    assert q["redirect_uri"][0].endswith("/yoto/callback")
    assert "state" in q


def test_finish_login_saves_tokens(temp_config, monkeypatch):
    url = auth.start_login()
    state = parse_qs(urlparse(url).query)["state"][0]

    monkeypatch.setattr(auth.httpx, "post",
                        lambda *a, **k: FakeResponse({"access_token": "AT", "refresh_token": "RT", "expires_in": 3600}))
    auth.finish_login("thecode", state)
    assert temp_config.token_path.exists()
    assert auth.get_access_token() == "AT"
    assert auth.connection_status()["connected"] is True


def test_finish_login_rejects_bad_state(temp_config):
    auth.start_login()
    with pytest.raises(auth.AuthError):
        auth.finish_login("code", "wrong-state")


def test_get_access_token_refreshes_when_expired(temp_config, monkeypatch):
    # seed an expired token with a refresh token
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    calls = {}

    def fake_post(url, data=None, **k):
        calls["data"] = data
        return FakeResponse({"access_token": "NEW", "expires_in": 3600})

    monkeypatch.setattr(auth.httpx, "post", fake_post)
    assert auth.get_access_token() == "NEW"
    assert calls["data"]["grant_type"] == "refresh_token"
    # refresh token preserved when the response omits a new one
    import json
    saved = json.loads(temp_config.token_path.read_text())
    assert saved["refresh_token"] == "RT"


def test_not_connected_raises(temp_config):
    with pytest.raises(auth.NotConnectedError):
        auth.get_access_token()


def test_logout_removes_token(temp_config, monkeypatch):
    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})
    assert temp_config.token_path.exists()
    auth.logout()
    assert not temp_config.token_path.exists()


def test_network_failure_raises_auth_network_error(temp_config, monkeypatch):
    def boom(*a, **k):
        raise OSError("no route to host")

    monkeypatch.setattr(auth.httpx, "post", boom)
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    with pytest.raises(auth.AuthNetworkError):
        auth.get_access_token()


def test_rejection_raises_plain_auth_error(temp_config, monkeypatch):
    monkeypatch.setattr(auth.httpx, "post", lambda *a, **k: FakeResponse({}, status=401))
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    with pytest.raises(auth.AuthError) as exc:
        auth.get_access_token()
    # A rejection must NOT be reported as a network problem, or the settings
    # screen would tell an offline-looking story about a genuinely dead sign-in.
    assert not isinstance(exc.value, auth.AuthNetworkError)


def test_check_connection_not_connected_when_nothing_saved(temp_config):
    assert auth.check_connection() == {"state": "not_connected"}


def test_check_connection_connected_after_successful_refresh(temp_config, monkeypatch):
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post",
                        lambda *a, **k: FakeResponse({"access_token": "NEW", "expires_in": 3600}))
    assert auth.check_connection() == {"state": "connected"}


def test_check_connection_broken_when_yoto_rejects(temp_config, monkeypatch):
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post", lambda *a, **k: FakeResponse({}, status=401))
    assert auth.check_connection() == {"state": "broken"}


def test_check_connection_broken_when_saved_sign_in_has_no_refresh_token(temp_config):
    # A token file exists but is unusable. That is broken, not not_connected —
    # the distinction matters because the two states show different copy.
    auth._save_tokens({"access_token": "old", "expires_at": time.time() - 10})
    assert auth.check_connection() == {"state": "broken"}


def test_check_connection_unknown_when_offline(temp_config, monkeypatch):
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})

    def boom(*a, **k):
        raise OSError("no route to host")

    monkeypatch.setattr(auth.httpx, "post", boom)
    assert auth.check_connection() == {"state": "unknown", "reason": "offline"}


def test_check_connection_unknown_on_timeout(temp_config, monkeypatch):
    import httpx as _httpx

    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})

    def slow(*a, **k):
        raise _httpx.ReadTimeout("took too long")

    monkeypatch.setattr(auth.httpx, "post", slow)
    assert auth.check_connection(timeout=0.01) == {"state": "unknown", "reason": "offline"}


def test_check_connection_passes_its_timeout_through(temp_config, monkeypatch):
    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    seen = {}

    def fake_post(url, data=None, timeout=None, **k):
        seen["timeout"] = timeout
        return FakeResponse({"access_token": "NEW", "expires_in": 3600})

    monkeypatch.setattr(auth.httpx, "post", fake_post)
    auth.check_connection(timeout=8.0)
    assert seen["timeout"] == 8.0
