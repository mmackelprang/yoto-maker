"""The step-3 Settings link must survive a live connect/disconnect, both ways.

tests/test_card_view_markup.py already asserts the *shipped markup* is right:
#advRow sits outside #connectRow, carries no .hidden, is the last child of step
3, and app.js contains both copy strings. Those are static assertions against
files on disk. They pin the page as authored — they cannot observe what
renderStatus() does to it at runtime, because nothing in them ever runs
renderStatus().

That gap matters here specifically. The v0.1.9 defect was not a typo in the
markup; it was a *runtime* consequence of structure — #advRow was a child of
#connectRow, and renderStatus() calls `show($("#connectRow"), !connected)`, so
the only contextual route into Settings disappeared the moment the user
connected. Static assertions catch that shape of bug only by proxy, and only for
as long as someone remembers which container is the dangerous one.

PR #16 then made the link's copy state-dependent inside the same function:

    $("#advToggle").textContent = connected
      ? "⚙️ Connect a different Yoto account"
      : "⚙️ Yoto connection settings";

A grep for both string literals proves they exist in the file. It does not prove
either one is ever assigned, nor that the assignment is reversible — a one-way
flip (set on connect, never restored on disconnect) satisfies every existing
assertion in the suite while leaving a user who signs out looking at "Connect a
different Yoto account".

So this test drives the real page, in a real browser, against the real FastAPI
app, and flips /api/status through renderStatus() the way the app itself does —
disconnected → connected → disconnected, with no page reload. The transition is
triggered by calling the app's own refreshStatus(); the test never writes to
textContent or to any class itself, because a test that sets the value it is
about to assert proves nothing about the code under test.

Playwright is an optional dev dependency (declared in pyproject.toml's
[project.optional-dependencies] dev). It is not installed by the default `pip
install -e .`, and its browser binaries are a separate download on top of the
Python package. Both are therefore skipped rather than failed: the module-level
importorskip covers a missing package, and the guarded launch in the `page`
fixture covers a package present with no chromium behind it.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright not installed (optional dev dependency: pip install -e .[dev])",
)

from yoto_maker.server.app import app  # noqa: E402  (after the skip guard)

# Verbatim from copy.md §1a, and duplicated in test_card_view_markup.py on
# purpose: that test asserts the strings are in the source, this one asserts
# they reach the screen in the right state. Keep both in step with app.js.
CONNECTED_COPY = "⚙️ Connect a different Yoto account"
DISCONNECTED_COPY = "⚙️ Yoto connection settings"

# The sync Playwright API refuses to run inside a live asyncio event loop, and
# this suite sets asyncio_mode = "auto". That is not a conflict: "auto" only
# wraps *async* test functions in a loop, so a plain `def` test — like the one
# below — runs with no loop running and the sync API is safe. Making these
# functions async would break them.


def _free_port() -> int:
    """Bind :0 and hand back what the OS picked.

    A hard-coded port collides with a Yoto Maker the developer left running
    (conftest's temp_config uses 8799) and with a parallel test run.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def live_server(temp_config):
    """The real app on a real port.

    Depends on temp_config (autouse anyway, named here to fix ordering) so the
    server thread reads the temp data dir and can never see a real token.
    """
    import uvicorn

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 30
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            server.should_exit = True
            pytest.fail(f"uvicorn failed to come up on 127.0.0.1:{port}")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=15)


@pytest.fixture
def page(live_server):
    """A chromium page, or a skip if the browser binary was never downloaded.

    `pip install playwright` does not install browsers; `playwright install
    chromium` does. Failing here would make a green suite depend on a step that
    isn't in any install instruction, which is the trap docs/BUILDER_QUEUE.md
    item 3 is open about.
    """
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # noqa: BLE001 - any launch failure is a skip
            pytest.skip(f"chromium not available to playwright: {exc}")
        try:
            yield browser.new_page()
        finally:
            browser.close()


# The one thing this test controls. Everything else about /api/status is served
# by the real app, so a change to that payload's shape breaks this test loudly
# instead of being papered over by a hand-written fixture that drifts.
def _install_status_route(page, state: dict) -> None:
    def handler(route):
        upstream = route.fetch()
        payload = upstream.json()
        payload["yoto"] = {**payload["yoto"], "connected": state["connected"]}
        route.fulfill(json=payload)

    page.route("**/api/status", handler)
    # checkUpdate() reaches GitHub. Nothing here depends on it and a test should
    # not need the network.
    page.route("**/api/update", lambda route: route.abort())


_PROBE = """() => {
  const adv = document.querySelector("#advRow");
  const toggle = document.querySelector("#advToggle");
  const connectRow = document.querySelector("#connectRow");
  const step = adv && adv.closest("section.step");
  if (!adv || !toggle || !connectRow || !step) return null;
  return {
    copy: toggle.textContent.trim(),
    // getClientRects() is empty for display:none, which is what .hidden is.
    advVisible: adv.getClientRects().length > 0,
    advInsideConnectRow: connectRow.contains(adv),
    advIsLastChild: step.lastElementChild === adv,
    // Proves `step` really is step 3 and not some other section.step.
    stepOwnsSendBtn: !!step.querySelector("#sendBtn"),
    // Proves renderStatus() actually ran, rather than the copy having been
    // right by luck: these two are set in the same function body.
    connectRowVisible: connectRow.getClientRects().length > 0,
    sendBtnDisabled: document.querySelector("#sendBtn").disabled,
  };
}"""


def _assert_settings_link_intact(probe: dict, *, connected: bool) -> None:
    where = "connected" if connected else "disconnected"
    assert probe is not None, f"[{where}] #advRow / #advToggle / #connectRow not all present"
    assert probe["stepOwnsSendBtn"], f"[{where}] #advRow is no longer inside step 3"
    assert not probe["advInsideConnectRow"], (
        f"[{where}] #advRow is inside #connectRow again — renderStatus() hides that "
        "container, so this is the v0.1.9 defect"
    )
    assert probe["advVisible"], f"[{where}] #advRow is not rendered"
    assert probe["advIsLastChild"], f"[{where}] #advRow is not the last child of step 3"
    expected = CONNECTED_COPY if connected else DISCONNECTED_COPY
    assert probe["copy"] == expected, f"[{where}] #advToggle reads {probe['copy']!r}"
    # renderStatus() sets these alongside the copy; if they didn't move, the
    # copy we just checked wasn't produced by the transition we think we drove.
    assert probe["connectRowVisible"] is (not connected), f"[{where}] #connectRow visibility wrong"
    assert probe["sendBtnDisabled"] is (not connected), f"[{where}] #sendBtn disabled state wrong"


def test_settings_link_survives_a_live_connect_and_disconnect(page, live_server):
    """Drives disconnected → connected → disconnected with no reload.

    Breaks if someone:
      * puts #advRow back inside #connectRow — it stops rendering when connected,
        and stops being step 3's last child in both states;
      * hides #advRow in either state, by markup or by a show() call;
      * makes the copy static in either direction — including the subtle
        one-way version, where connecting swaps the text and disconnecting
        never swaps it back, which every static assertion in the suite passes;
      * moves #advRow off the end of step 3.

    The flips go through the app's own refreshStatus(), which re-fetches
    /api/status and calls renderStatus(). The test changes only the JSON.
    """
    state = {"connected": False}
    _install_status_route(page, state)

    page.goto(live_server, wait_until="domcontentloaded")
    # init() is async, and #advToggle already carries the disconnected copy in
    # the shipped markup — so waiting for that text to be non-empty would pass
    # before renderStatus() had ever run, and the "disconnected" leg of this
    # test would assert against static HTML instead of against the code.
    # STATUS is the app's own guard (`let STATUS = null`, assigned only from a
    # resolved /api/status). init() assigns it and calls renderStatus() in one
    # synchronous run of the post-await continuation, so a poll that observes a
    # non-null STATUS is necessarily observing a page renderStatus() has
    # already touched. It is a bare `let`, not a window property, hence the
    # typeof guard.
    page.wait_for_function("() => typeof STATUS !== 'undefined' && STATUS !== null")

    _assert_settings_link_intact(page.evaluate(_PROBE), connected=False)

    # → connected. This is the state the v0.1.9 defect made unreachable.
    state["connected"] = True
    page.evaluate("() => refreshStatus()")
    _assert_settings_link_intact(page.evaluate(_PROBE), connected=True)

    # → back to disconnected. The direction a one-way copy flip fails on.
    state["connected"] = False
    page.evaluate("() => refreshStatus()")
    _assert_settings_link_intact(page.evaluate(_PROBE), connected=False)
