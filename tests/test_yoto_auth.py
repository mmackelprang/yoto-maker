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
