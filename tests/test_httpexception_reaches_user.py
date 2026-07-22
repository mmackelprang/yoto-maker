"""An HTTPException message must reach the user — not be swallowed to the generic line.

FastAPI serialises `raise HTTPException(status, "message")` to
`{"detail": "message"}`, but api() (app.js) historically read only `data.error`
— our own envelope — so every HTTPException fell through to
"Something went wrong. Please try again." (queue item 13, §For the queue).

This asserts the {detail} -> api() -> user path in two halves, because the suite
runs no JavaScript:

  * the SERVER half — a real HTTPException endpoint emits {"detail": <string>};
  * the CLIENT half — api() surfaces `data.detail`, and only when it is a string.

The client half is the differentiator the scope asked for: proof the message
reaches the USER, not merely that the endpoint raised.
"""
from __future__ import annotations

from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "yoto_maker" / "server" / "static" / "app.js"


def test_httpexception_serialises_as_a_detail_string(client):
    """The server half: a bare HTTPException is {"detail": <str>} and nothing else.

    rename_track (app.py:307) on a missing id is the cheapest reachable
    HTTPException. Pinning the shape here means that if a FastAPI upgrade or a new
    custom handler ever changes it, the client fallback below would read the wrong
    key and this test says so instead of the bug shipping silently.
    """
    r = client.patch("/api/tracks/does-not-exist", json={"title": "x"})
    assert r.status_code == 404
    body = r.json()
    assert isinstance(body.get("detail"), str) and body["detail"], body
    assert "error" not in body  # it is NOT our envelope — that is the whole problem


def test_api_surfaces_detail_and_string_guards_it():
    """The client half: api() falls back to data.detail, guarded to strings.

    A static assertion because the suite has no JS runtime — the same house
    pattern as the *_markup.py contract tests. The string guard is asserted on its
    own so a future 'simplification' to a bare `|| data.detail` (which would render
    a 422 validation list as "[object Object]") trips a test whose name says what
    it broke.
    """
    src = APP_JS.read_text(encoding="utf-8")
    assert "data.detail" in src, "api() no longer falls back to FastAPI's detail shape"
    assert 'typeof data.detail === "string"' in src, (
        "the detail fallback is not string-guarded; a 422 validation list would "
        'render to the user as "[object Object]"'
    )
