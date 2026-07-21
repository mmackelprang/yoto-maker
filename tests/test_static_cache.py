"""The UI must never be served from a previous release's browser copy.

Regression cover for the v0.1.9 field bug: a browser holding v0.1.8's app.js
kept using it across the auto-update, so users ran new HTML against old
JavaScript and the Settings view silently never appeared.
"""
from __future__ import annotations

import inspect
import re

import pytest
from fastapi.testclient import TestClient

from yoto_maker import __version__
from yoto_maker.server import app as app_module
from yoto_maker.server.app import app


@pytest.fixture
def client(temp_config):
    return TestClient(app)


def _cp1252_safe(ch: str) -> bool:
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def test_index_stamps_asset_urls_with_the_running_version(client):
    body = client.get("/").text
    assert f"/static/app.js?v={__version__}" in body
    assert f"/static/styles.css?v={__version__}" in body


def test_index_leaves_no_unversioned_asset_url(client):
    """An unstamped URL is the bug. Catch a half-applied edit.

    Swept rather than enumerated on purpose. The plan named app.js and
    styles.css as "the complete surface" and it was wrong — logo.png was a
    third, unstamped reference. Hardcoding filenames here would have missed it
    and would miss the next asset someone adds, which is the same defect all
    over again. Assert the property instead: nothing under /static/ is served
    without a stamp.
    """
    body = client.get("/").text
    unstamped = [url for url in re.findall(r'"(/static/[^"]*)"', body) if "?v=" not in url]
    assert not unstamped, f"unversioned /static/ URLs served: {unstamped}"
    assert "__ASSET_V__" not in body


def test_asset_urls_change_when_the_version_changes(client, monkeypatch):
    """The property the fix exists for: a new release is a new cache key.

    This is the assertion that would have caught the original bug — under the
    old code the served URL was identical across every version.
    """
    monkeypatch.setattr(app_module, "__version__", "9.9.9")
    body = client.get("/").text
    assert "/static/app.js?v=9.9.9" in body
    assert "/static/styles.css?v=9.9.9" in body
    assert f"/static/app.js?v={__version__}" not in body


def test_index_document_is_never_stored(client):
    """Without this the stamps above are decorative: a cached index.html is
    never re-read, so the browser never learns the new asset URLs."""
    r = client.get("/")
    assert r.status_code == 200
    assert "no-store" in r.headers["cache-control"].lower()


@pytest.mark.parametrize("asset", ["app.js", "styles.css"])
def test_static_assets_must_revalidate(client, asset):
    r = client.get(f"/static/{asset}")
    assert r.status_code == 200
    assert "no-cache" in r.headers["cache-control"].lower()


def test_stamped_url_serves_the_asset(client):
    """The query string must not disturb StaticFiles routing."""
    r = client.get(f"/static/app.js?v={__version__}")
    assert r.status_code == 200
    assert "no-cache" in r.headers["cache-control"].lower()


def test_revalidation_stays_cheap(client):
    """no-cache means 'revalidate', not 'resend'. Proves the ETag still shortcuts."""
    first = client.get("/static/app.js")
    etag = first.headers["etag"]
    again = client.get("/static/app.js", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert not again.content


def test_index_survives_characters_the_windows_locale_cannot_decode(client):
    """Guards the explicit encoding="utf-8" in the / route.

    Without it Python reads index.html as cp1252 inside the frozen .exe and
    raises UnicodeDecodeError, 500-ing the entire UI. This passes on a UTF-8
    machine either way, so the canary assertion below keeps it honest: if
    index.html ever loses its non-cp1252 characters, this test says so rather
    than quietly stopping to test anything.
    """
    body = client.get("/").text
    canaries = [c for c in body if not _cp1252_safe(c)]
    assert canaries, "index.html no longer exercises the non-cp1252 path"
    assert "\U0001f3b5" in body  # the header logo emoji round-tripped intact


def test_index_route_pins_the_encoding_explicitly():
    """The behavioural test above cannot fail on a UTF-8-locale machine.

    It catches the regression today only because this dev box is Windows
    (cp1252). Linux CI, or Python 3.15 defaulting to UTF-8 mode (PEP 686),
    would silently disarm it while the frozen Windows .exe still 500s on every
    user's machine. Assert on the source so the guard holds everywhere.

    Match the call itself, not the bare string: the route's docstring explains
    the encoding trap and therefore contains encoding="utf-8" as prose, so a
    looser assertion passes on the documentation while the actual argument is
    gone. (It did, when this test was first written.)
    """
    assert 'read_text(encoding="utf-8")' in inspect.getsource(app_module.index)
