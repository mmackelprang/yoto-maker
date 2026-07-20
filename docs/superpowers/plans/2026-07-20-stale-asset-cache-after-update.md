# Plan — Stale browser assets after auto-update

**Date:** 2026-07-20
**Author:** Planner
**Ships in:** v0.1.10 (alongside Designer's Settings-discoverability fix — separate PR, see §Cross-PR)
**Queue item:** 8
**Branch:** `fix/asset-cache-busting`
**Type:** shipping bug. No new user-facing surface, no new copy, no design handoff required.

---

## The defect

After the auto-updater installs a new release, the browser keeps serving `app.js`
and `styles.css` from its own store. The user gets **new HTML against old
JavaScript**. Reported against v0.1.9: `#settings` appeared to bounce back to the
main page and the header pill did nothing, because v0.1.8's `app.js` has no hash
routing and never un-hides `#settingsView`.

Measured on the running v0.1.9 instance:

| Response | ETag | Last-Modified | Cache-Control |
|---|---|---|---|
| `/` (index.html) | yes | yes | **absent** |
| `/static/app.js` | yes | yes | **absent** |
| `/static/styles.css` | yes | yes | **absent** |

Both asset URLs in `index.html` are unversioned (`index.html:7`, `index.html:309`).
The server is not at fault — it serves the correct bytes. With **no
`Cache-Control` and no version in the URL**, browsers fall back to *heuristic
caching* (RFC 9111 §4.2.2): freshness is invented as a fraction of
`Date − Last-Modified`. A copy of `app.js` that had been sitting in a
long-running v0.1.8 install therefore carries a multi-hour invented freshness
lifetime and is reused **without any request to the server at all**.

### Why it is worse than a cosmetic bug

- **It has plausibly degraded every release since v0.1.5**, when the auto-updater
  shipped. Silently, and invisibly to us.
- **It fails silently and partially.** Markup and script from different versions:
  features look present and are dead. No error, no console message worth
  searching for, nothing for the user to report beyond "it's being weird."
- **It targets the least-equipped user.** This app is built for someone who reads
  `docs/INSTALL-FOR-MOM.md`. She will never press Ctrl+Shift+R. She experiences
  an app that updated itself and then started misbehaving.

---

## Approach

**Do both: version-stamped asset URLs *and* `Cache-Control`.** They fix
different halves of the problem and each covers the other's blind spot. The
document itself gets `no-store`, which is the linchpin.

### 1. `no-store` on `index.html` — resolve this first or nothing else matters

`index.html` is currently served by a route handler
(`app.py:656-659`, `FileResponse`) and Starlette's `FileResponse` sets ETag and
Last-Modified but **no `Cache-Control`** — so the document is heuristically
cacheable on exactly the same terms as the assets.

**This is the failure mode that would make a version-stamp fix silently
useless.** If the browser reuses a cached `index.html`, it never reads the new
`?v=` stamps, and stamping accomplishes nothing. Version-stamping without fixing
the document is a fix that appears correct in every test that fetches `/` fresh
and does nothing whatsoever in the field.

**Decision: `Cache-Control: no-store` on `/`.** Not `no-cache`.

- The document is ~15 KB over loopback. Revalidation savings are not measurable
  here, so there is nothing to trade away.
- `no-store` forbids writing the response to any store at all, so the document
  cannot be served stale under any condition, including conditions we have not
  thought of. `no-cache` still permits storage and depends on the browser
  choosing to revalidate.
- The document is the one response whose staleness invalidates the entire
  remedy. It is the correct place to spend the strongest available directive.

Known cost: Chrome historically declines to bfcache a `no-store` page, so Back
re-fetches. Irrelevant here — in-page navigation is `hashchange` (which is not a
bfcache event), and a re-fetch of `/` re-reads live draft state from the server
rather than restoring a stale snapshot. That is the behavior we want.

### 2. Version-stamped asset URLs — the only mechanism that repairs users who are *already* poisoned

`/static/app.js?v=0.1.10`, stamped at serve time from `yoto_maker.__version__`.

This is the load-bearing argument for stamping, and it is worth being precise
about: **shipping `Cache-Control` alone cannot rescue anyone who is already
broken today.** A browser holding a heuristically-fresh v0.1.9 `app.js` does not
issue a request, so it never sees the new header. The header only takes effect
once the invented freshness lifetime lapses. It is purely prophylactic, and it
protects v0.1.11 onward — not the users broken right now.

A changed URL is a **cache miss by construction**. `/static/app.js?v=0.1.10` is
a key the browser has never seen, so the poisoned entry for `/static/app.js` is
simply not consulted. Every user on v0.1.5–v0.1.9 is repaired on their first
load of v0.1.10, with no action from them and no dependence on browser
revalidation policy.

### 3. `Cache-Control: no-cache` on `/static/*` — **not** `immutable`

`no-cache` does **not** mean "do not cache". It means: you may store this, but
you must revalidate with the origin before every reuse. Combined with the ETag
that `StaticFiles` already emits, the steady-state cost is a conditional request
answered `304 Not Modified` over loopback — a fraction of a millisecond, no body
transferred.

The alternative spelling `max-age=0, must-revalidate` is near-equivalent in
effect (`max-age=0` makes the response instantly stale; `must-revalidate` then
forbids serving it stale). `no-cache` is the clearer and more uniformly
implemented expression of the same intent. Use `no-cache`.

**Rejected: `max-age=31536000, immutable`,** the usual partner to version
stamping. It would be actively harmful in this codebase:

- `__version__` does not change between dev rebuilds. Under `immutable`, editing
  `app.js` without bumping the version produces a URL the browser already holds
  and will never revalidate — converting today's documented UAT hazard into a
  permanent one, and re-creating the exact bug at development time.
- The performance it buys is nil. Every request is loopback to a process on the
  same machine.

`no-cache` covers within-version changes; version stamps cover across-version
changes and repair existing damage. Together they leave no gap.

---

## PyInstaller

Static files in the frozen build come from the bundled `_MEIPASS` tree, not the
source tree. Verified as safe:

- `STATIC_DIR = Path(__file__).resolve().parent / "static"` (`app.py:46`) already
  resolves under `_MEIPASS`, because `YotoMaker.spec:16` bundles the static
  directory to `yoto_maker/server/static` inside the archive. `index.html` is
  served today from the shipped `.exe`, so **reading it as text needs no new path
  logic.**
- **Serve-time substitution, never build-time.** A build step that stamped the
  file (a spec hook, a pre-build script) would produce a fix that behaves
  differently from source than from the `.exe` — the exact class of fix the brief
  warns about. Reading and substituting inside the request handler is byte-identical
  in both, and has no build-order dependency to get wrong.

### The one thing that will break the frozen build if missed

**`read_text()` must be given `encoding="utf-8"` explicitly.**

`Path.read_text()` with no encoding uses `locale.getpreferredencoding()`. On a
stock Windows box — and therefore inside the frozen `.exe`, which inherits the
user's locale — that is **cp1252**. Verified on this machine:

```
locale.getpreferredencoding(): cp1252
index.html: 14956 bytes, 54 non-ASCII characters
distinct: U+00A7 U+00B7 U+2014 U+2019 U+2026 U+2190 U+2197 U+2699 U+2702
          U+270F U+2728 U+2795 U+2B07 U+FE0F U+1F3B5 U+1F49C U+1F4C1 U+1F4C4
          U+1F4E4 U+1F517 U+1F5A8 U+1F60A U+1F680 U+1F916
cp1252 decode: UnicodeDecodeError -> character maps to <undefined> at byte 1201
```

A bare `read_text()` raises `UnicodeDecodeError` at byte 1201 and **the `/` route
returns 500 — the app cannot serve its own UI at all.** It would pass on any
UTF-8-locale machine and die on the users'. Task 3 pins the encoding; Task 4
holds a regression test on it.

---

## Cross-PR coordination

**This PR owns the version bump to `0.1.10`** (`pyproject.toml:7`,
`yoto_maker/__init__.py:3`). Designer's Settings-discoverability PR must **not**
also bump, or the two conflict. Whichever lands second rebases onto the bumped
version. Flagged on both queue rows.

Rationale for owning it here: the stamp is only *useful* when the version string
changes, so this fix and the bump are one unit of user-visible value.

Adjacent, deliberately **out of scope**: queue item 2 (`--port` does not update
`cfg.port`) lives in `main.py:59`, one file over. Do not fold it in — it changes
OAuth redirect behavior and has its own queue row.

---

## Constraints

- **No user-visible strings change in the app.** No copy review needed.
- **`docs/RELEASE_NOTES.md` is user-visible**, and `docs/design-handoffs/README.md`
  **bans the word "cache"** from user-facing copy (along with OAuth, token,
  endpoint, API, session, config, JSON). Task 6's release note is written in plain
  language and must stay that way — no "browser cache", no "cache-busting".
- Every task leaves the app working. Task 2 stamps the HTML with a literal
  placeholder, which `StaticFiles` serves fine (query strings are ignored in
  routing), so even the intermediate commit boots.

---

## Tasks

### Task 1 — Bump to v0.1.10

`yoto_maker/__init__.py`:

```python
__version__ = "0.1.10"
```

`pyproject.toml` line 7:

```toml
version = "0.1.10"
```

### Task 2 — Stamp the asset URLs in `index.html`

Two lines. The placeholder `__ASSET_V__` is distinctive and greppable; confirm
with `grep -rn __ASSET_V__` that these are the only two occurrences after the edit.

`yoto_maker/server/static/index.html` line 7:

```html
  <link rel="stylesheet" href="/static/styles.css?v=__ASSET_V__" />
```

line 309:

```html
  <script src="/static/app.js?v=__ASSET_V__"></script>
```

There are no other references to `/static/` anywhere in the UI — `app.js`
contains none (verified by grep), so these two tags are the complete surface.

### Task 3 — Substitute at serve time and set the cache headers

`yoto_maker/server/app.py`. Replace the `/` route (currently lines 656-659):

```python
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the UI with its asset URLs stamped with the running version.

    Two independent guards against a browser reusing a previous release's
    ``app.js``/``styles.css`` (which shipped new markup against old script and
    made the Settings view unreachable in v0.1.9):

    * ``no-store`` on this document, so the stamps below are always re-read. A
      cached index.html would make the stamping useless — the browser would
      never see the new URLs.
    * the ``?v=`` stamp itself, which changes the cache key every release and so
      repairs browsers that are *already* holding a stale copy. A Cache-Control
      header cannot do that: a browser serving from its own store issues no
      request and never sees the header.

    ``encoding="utf-8"`` is not optional. Without it Python uses
    ``locale.getpreferredencoding()`` — cp1252 on a stock Windows box, and so
    inside the frozen .exe — and this file's emoji and arrows raise
    UnicodeDecodeError, turning the whole UI into a 500.
    """
    ensure_library()  # make sure icons exist before the UI asks for them
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        html.replace("__ASSET_V__", __version__),
        headers={"Cache-Control": "no-store"},
    )
```

Then replace the static mount (currently line 663) with the mount plus a cache
policy middleware. Place the middleware **above** the mount, with the other
middleware near the top of the file for readability — Starlette applies
middleware independently of route order, so location is a style choice only:

```python
@app.middleware("http")
async def _static_cache_policy(request, call_next):
    """Make the browser revalidate static assets instead of guessing.

    Served without Cache-Control, ``app.js`` and ``styles.css`` fall under
    *heuristic* caching: the browser invents a freshness lifetime from
    Date - Last-Modified and reuses the file with no request at all. That is how
    a v0.1.8 app.js survived the update to v0.1.9.

    ``no-cache`` does not mean "don't cache" — it means "revalidate before every
    reuse". StaticFiles already emits an ETag, so the steady state is a
    conditional request answered 304 with no body, over loopback.

    Deliberately not ``immutable``: __version__ does not change between dev
    rebuilds, so immutable would make an edited app.js permanently invisible
    without a version bump — the same bug, moved to development time. There is
    no performance to win on loopback anyway.
    """
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
```

The mount itself is unchanged:

```python
# Static assets (app.js/styles.css). Mounted last so API routes take precedence.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

**Do not add an in-process cache of the substituted HTML.** It is a 15 KB read
once per page load on loopback, and a module-level cache would introduce a third
staleness vector into the fix for a staleness bug — plus it would stop `index.html`
edits from appearing without a server restart.

`FileResponse` stays imported; it is still used by `/api/picture.png`,
`/api/label.pdf` and the icon routes.

### Task 4 — Regression tests

New file `tests/test_static_cache.py`. The `temp_config` fixture is autouse from
`conftest.py` and points `bundle_root` at the repo root, so `STATIC_DIR` resolves
normally.

```python
"""The UI must never be served from a previous release's browser copy.

Regression cover for the v0.1.9 field bug: a browser holding v0.1.8's app.js
kept using it across the auto-update, so users ran new HTML against old
JavaScript and the Settings view silently never appeared.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from yoto_maker import __version__
from yoto_maker.server import app as app_module
from yoto_maker.server.app import STATIC_DIR, app


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
    """An unstamped URL is the bug. Catch a half-applied edit."""
    body = client.get("/").text
    assert '"/static/app.js"' not in body
    assert '"/static/styles.css"' not in body
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
```

Expected: 9 tests (the parametrize yields 2). Run `pytest -q tests/test_static_cache.py`
and then the full suite; with `yt-dlp` installed the baseline is **110 passed**,
so expect **119 passed**. Without `yt-dlp` expect **118 passed, 1 failed** — that
one failure is queue item 3 and is environmental, not this PR.

### Task 5 — Correct the misfiling in `docs/DEVELOPERS.md`

This symptom was hit twice during UAT (PR #10 and PR #11) and written up both
times as a *testing hazard* rather than the user-facing defect it is. Replace the
opening of the "Testing UI changes in a browser" section — currently lines 46-61,
from the heading through "...clear the cache and re-run the check." — with:

```markdown
### Testing UI changes in a browser — you may be measuring a build that isn't there

Two independent causes. The first was a real shipping bug and is now fixed; the second is still live. Rule out both
before you believe a UI failure.

**1. A stale browser copy of `app.js` / `styles.css` — fixed in v0.1.10, and it was never just a testing problem.**

Until v0.1.10 the static assets were served with no `Cache-Control` and unversioned URLs, so browsers applied
*heuristic* caching and reused them across a rebuild — or across an **auto-update**, which is where it mattered.
We met this three times during PR #10's UAT (`--focus-ring` reading empty, the header pill drawing a UA-default
outline, the pill triggering sign-in instead of routing to Settings) and filed it as a UAT hygiene note. It was in
fact the v0.1.9 field bug — a user on a self-updated install running new HTML against old JavaScript — wearing a
costume. The third of those three false failures *is* the exact symptom the user later reported.

**The fix (v0.1.10):** `/` is served `Cache-Control: no-store` with its asset URLs stamped `?v={__version__}`, and
`/static/*` is served `no-cache` so the existing ETag forces a revalidation. Dev rebuilds within a single version
are covered by the `no-cache` half, so **you no longer need to disable the cache to test UI changes.**

If you suspect this anyway, the tell is unchanged: compare the byte count of the served asset against the file on
disk. A mismatch means you are testing a build that no longer exists.

**Never disable the cache when testing the update path itself.** Doing so hides the entire class of bug above —
it puts you in a configuration no real user is ever in, which is precisely how this survived five releases.
```

Leave cause 2 (the stale-server / single-instance trap, lines 62-83) exactly as
it stands. It is accurate and unaffected.

### Task 6 — Release note

Prepend to `docs/RELEASE_NOTES.md`, replacing the `# Yoto Maker v0.1.9` heading
with a v0.1.10 heading and a new section above the existing v0.1.9 content. Keep
the two-line intro paragraph as it is.

**No banned vocabulary** (`docs/design-handoffs/README.md`) — this note does not
say cache, browser cache, asset, or header:

```markdown
# Yoto Maker v0.1.10

### Fixed in v0.1.10
- **The app now finishes updating itself properly.** After an update, some parts
  of the app could still be the old version — so new buttons were there but did
  nothing, and the Settings page wouldn't open. Everything now arrives together.
  If the app has been behaving strangely since it last updated, this release
  fixes it on its own; you don't need to do anything.
```

### Task 7 — Note the correction on the historical plan files

`docs/superpowers/plans/2026-07-20-client-id-reveal-and-v0.1.9-release.md` carries
the hazard block at lines 851-885 and
`docs/superpowers/plans/2026-07-20-configuration-surface.md` carries its ancestor.
These are the durable record of shipped work — **do not rewrite the narrative.**
Insert one blockquote line directly above the "Cause 1 — a stale browser cache"
paragraph in each:

```markdown
> **[Corrected 2026-07-20]** Cause 1 below was misfiled as a testing hazard. It was the
> user-facing v0.1.9 bug (new HTML, old `app.js` after auto-update), fixed in v0.1.10 —
> see `docs/superpowers/plans/2026-07-20-stale-asset-cache-after-update.md`. The three
> "false failures" recorded below were real, they just were not reproducible only in dev.
```

---

## Test plan

### A. Automated

```bash
pytest -q tests/test_static_cache.py     # expect 9 passed
pytest -q                                # expect 119 passed (110 baseline + 9)
```

### B. The repair, from source — **do not clear the cache**

This is the section that actually proves the fix, and the instinct to clear the
cache first would destroy it. The whole claim is that an already-poisoned browser
is repaired **with no user action**.

1. `git stash` the branch, or check out `v0.1.9`. Start `python -m yoto_maker --no-tray --no-browser`.
2. Open `http://127.0.0.1:8777/` in a normal browser window with caching **on**
   and DevTools **closed** (DevTools defaults can disable the cache — that would
   invalidate the whole test).
3. In DevTools Network, reload once and confirm `app.js` shows **`(disk cache)`**
   or **`(memory cache)`** with no network round trip. That is the poisoned state
   reproduced. Record the request URL: it must be bare `/static/app.js`.
4. Stop the server. Check out the fix branch. Start it again on the same port.
5. Reload the page **normally — F5, not Ctrl+Shift+R, cache still enabled.**
6. **Expect:** the document request for `/` shows `Cache-Control: no-store` and a
   `200` (not `304`, not `(disk cache)`).
7. **Expect:** the script request is now `/static/app.js?v=0.1.10` — a different
   URL from step 3 — fetched over the network with status `200`, **not** served
   from cache.
8. **Expect:** `Cache-Control: no-cache` on that response.
9. **Expect:** the Settings view works — click the header pill, and navigate
   directly to `http://127.0.0.1:8777/#settings`. Both must land on Settings.
   This is the user's original symptom; it must be gone without a hard reload.
10. Reload again. **Expect:** `app.js` is now a `304`, proving revalidation is
    working and cheap rather than re-downloading the body each time.

### C. The frozen build — the only test that speaks for real users

A fix that works from source and not from the shipped `.exe` fixes nothing.
Steps 3-5 specifically cover the cp1252 decode failure, which **cannot reproduce
from source on a UTF-8 machine.**

1. Build per `docs/DEVELOPERS.md`: stage `packaging/vendor/ffmpeg.exe` and
   `ffprobe.exe`, then
   `pyinstaller packaging/YotoMaker.spec --distpath packaging/dist --workpath packaging/build --noconfirm`.
2. Run `packaging/dist/YotoMaker.exe`.
3. **Expect the UI to load at all.** A blank page or a 500 on `/` is the encoding
   bug — check that `read_text` in the `/` route has `encoding="utf-8"`.
4. Confirm the stamp survives bundling:
   ```bash
   curl -s http://127.0.0.1:8777/ | grep -o '/static/app.js?v=[0-9.]*'
   ```
   **Expect:** `/static/app.js?v=0.1.10`. An unsubstituted `__ASSET_V__` means the
   route is not doing the replacement; a bare `/static/app.js` means `index.html`
   was not rebundled.
5. Confirm the non-ASCII content decoded rather than mangled — the header shows
   🎵 and the step headings show their emoji, not `Ã¯Â¿Â½` or similar.
6. ```bash
   curl -sI http://127.0.0.1:8777/ | grep -i cache-control              # no-store
   curl -sI "http://127.0.0.1:8777/static/app.js?v=0.1.10" | grep -i cache-control   # no-cache
   ```

### D. End-to-end update path (optional but this is the bug's native habitat)

Only meaningful once v0.1.10 is released. With a v0.1.9 `.exe` installed and its
UI already loaded in a browser (so the poisoned entry exists), accept the update
banner, let the app restart, and confirm the reopened tab picks up
`?v=0.1.10` — **without clearing anything.** If this passes, the bug is closed
for real users rather than for us.

---

## Self-review

- **Spec coverage.** Version stamping ✅ (§2, Tasks 2-3). Cache-Control with the
  `no-cache` semantics stated precisely ✅ (§3). `index.html` caching resolved
  explicitly rather than assumed ✅ (§1). PyInstaller verified, with the encoding
  trap found ✅. Regression test asserting URLs change across versions ✅ (Task 4,
  `test_asset_urls_change_when_the_version_changes`). Real stale-cache repair
  simulated ✅ (Test plan §B). Misfiling corrected ✅ (Tasks 5, 7).
- **Placeholders.** None. No `TBD`, no "similar to Task N". Every task carries
  literal code or literal prose.
- **Scope.** No new endpoints, no user-facing copy in the app, no design decisions.
  Queue item 2 (`--port`) is adjacent in `main.py` and explicitly excluded.
- **Type consistency.** `__version__` is `str`; `.replace()` takes and returns
  `str`; `HTMLResponse` takes `str`. The middleware returns the response object it
  was handed. No signature changes anywhere.
