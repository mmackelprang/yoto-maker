# Configuration Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a full-page Settings view built on a reusable `.setting` primitive, together with the three backend correctness fixes without which that view would lie to the user about her Yoto connection.

**Architecture:** Backend first. `yoto_maker/config.py` gains a single precedence resolver that reports both the effective Client ID *and* which tier supplied it, so the API can never disagree with `resolve_client_id()`. `yoto_maker/yoto/auth.py` gains a network-vs-rejection error distinction (today both collapse into one `AuthError`, which makes the load-bearing `unknown` state literally unimplementable) plus a non-raising `check_connection()`. Two endpoints change and two are added. Only then does the frontend land: a second `<div>` inside `<main>` that swaps with the card view on `#settings`, containing two instances of the `.setting` primitive.

**Tech Stack:** Python 3.11+, FastAPI, httpx, pytest + `fastapi.testclient`; vanilla HTML/CSS/JS (no build step, no framework, no dependencies).

**Design handoff (authoritative):** `docs/design-handoffs/configuration-surface/` — `overview.md`, `interactions.md`, `copy.md`, `tokens.md`, `mockups/settings-view.md`.

---

## Global Constraints

- **One PR.** UI and the three correctness fixes ship together. The config surface is dishonest without them. Branch `feat/configuration-surface`, merged via PR per the user's global convention. Builder owns branch + PR.
- **Copy is verbatim from `copy.md`.** Do not paraphrase, shorten, re-tone, or "improve" any user-visible string. Deviations are a Polisher finding. Two strings in `copy.md` have no reachable trigger in this PR — see "Known gaps" below; do not invent a trigger for them.
- **Typographic apostrophes (`’`, U+2019), not `'`,** in every user-visible string, matching existing markup (`app.js:408`, `index.html:51`). This applies inside JS string constants too.
- **Banned vocabulary** in user-facing copy (`docs/design-handoffs/README.md`): OAuth, token, authenticate, credentials, revoke, endpoint, API, session, cache, config, JSON, refresh token, PKCE. "Client ID" is the single permitted technical term and is always explained where it appears.
- **`--warn` must never be a text color on `--warn-soft`** (measured 3.24:1, fails AA). It appears only as the 4px left border of `.setting-confirm`. Confirmation body copy is `--ink`. Do not add a `.msg-box.warn` variant.
- **The `1 2 3 4` step flow is structurally untouched.** No fifth step, no tab strip, no renumbering. `docs/INSTALL-FOR-MOM.md` teaches "four numbered steps" verbatim and the screen must keep agreeing with it.
- **The `.setting` primitive's extensibility is the feature.** Seven slots in fixed order: `h3` title, `.setting-desc`, `.setting-status`, `.setting-body`, `.setting-actions`, `.msg-box`, `.setting-confirm`. Adding setting #3 must be "copy the section, fill slots, append" with **zero CSS changes and zero edits to the neighbouring sections**. If an implementation choice would break that, stop and say so rather than degrading it quietly.
- **Global `:focus-visible` is intentional scope.** It lands globally and changes the visual diff on steps 1–4. The user explicitly approved this. It is not scope creep and must not be reverted by a reviewer.
- **Out of scope, do not implement:** showing *which* Yoto account is connected (`YOTO_SCOPES` lacks `openid`/`profile`; adding scopes would re-prompt every existing user and break everyone who followed `docs/SETUP-YOTO-CONNECTION.md`). Also out: moving the SponsorBlock checkbox, an AI key setting, dark mode, any change to steps 1, 2, 4.
- **Tests:** `pytest -q` from the repo root. The suite is 48 tests today and must be green at every commit. `tests/conftest.py` sets `YOTO_CLIENT_ID=test_client_id` **autouse** — any test that exercises `saved` or `builtin` Client ID precedence MUST call `monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)` first or it will silently test the `env` branch.

---

## Where the design and the code still disagree

The designer caught three correctness bugs (`overview.md` §7.3, §7.4, §7.5) and one pre-existing leak (§7.6). Reading the code turned up four more. Each is resolved by a task below; they are collected here so Builder and the reviewer know they were deliberate, not drift.

1. **`AuthError` cannot distinguish "Yoto said no" from "we couldn't reach Yoto."** `auth.py:115-118` maps `httpx.HTTPStatusError` → `AuthError("Yoto rejected…")` and bare `except Exception` → `AuthError("We couldn't reach Yoto…")`. Both are the same class. `overview.md` §7.5 requires `broken` and `unknown` to be different outcomes, and the brief calls `unknown` load-bearing. **As written, the design is not implementable.** Task 3 adds `AuthNetworkError(AuthError)` — a subclass, so every existing `except AuthError` still catches it.
2. **`_token_request()` hardcodes `timeout=30`,** but `overview.md` §7.5 timeboxes the check at ~8s. A 30s HTTP timeout inside an 8s budget cannot be honoured. Task 3 makes the timeout a parameter.
3. **`AuthError` has no FastAPI exception handler and is not in `FRIENDLY_ERRORS`** (`app.py:72`), and is not exported from `yoto_maker/yoto/__init__.py`. Today an `AuthError` out of `/api/yoto/login` becomes a bare 500 and the UI shows the generic "Something went wrong. Please try again." The settings surface makes `/api/yoto/login` a prominent, repeatedly-pressed action, so Task 4 adds the handler. The handler also emits a machine-readable `reason` so the UI can render `copy.md`'s wording rather than echoing a backend message written for a different context.
4. **`Config.yoto_client_id` (`config.py:74`) is computed once when the `get_config()` singleton is built and is dead in production** — nothing outside `tests/conftest.py` reads it. It must stay dead: after a Client ID save it would be stale. All new code derives from `resolve_client_id()` / `client_id_source()`. Task 2 documents this on the field.
5. **`check_connection()` returns `connected` without a network round trip when the cached access token is still unexpired.** `get_access_token()` short-circuits at `auth.py:155`. `copy.md` says "We just checked with Yoto and everything's fine." — slightly stronger than what happened in that one case. Accepted deliberately: forcing a refresh on every settings visit burns a token rotation per visit for no benefit in the real failure modes (a dead refresh token also means a long-expired access token, so those *do* hit the network; and a Client ID change now forces `logout()`, so no token survives). Recorded here so a reviewer doesn't read it as a bug, and called out in the Test Plan so Tester knows how to force a real network check.
6. **`mockups/settings-view.md` §2 draws the back link on its own line above "Settings"; `tokens.md` §3 defines `.settings-head` as a flex row with `gap: 12px`.** The mockup's own preamble defers ("the authoritative geometry is the existing `styles.css` plus `tokens.md`"), so **follow `tokens.md`**: back link and `h2` side by side in one `.settings-head`.
7. **`copy.md` §7.2 specifies a first-4 + last-3 mask (`a8OG…oU1`) but the only copy that consumes it uses `{last3}` alone.** The API still returns the full mask as spec'd; the UI derives its last 3 characters from it (`masked.slice(-3)`). No extra field.
8. **`settings.delete()` on a key present in `_DEFAULTS` will not make the key disappear** — `_load()` re-merges defaults on every read. Harmless here (`yoto_client_id` is not in `_DEFAULTS`) but it must be documented on the method so a future caller isn't surprised.

### Known copy gaps — flagged, not invented around

Two strings in `copy.md` §3 have no trigger the frontend can observe in this PR. **Do not invent one.**

- **"Sign-in was cancelled. You can try again whenever you're ready."** — cancellation happens on Yoto's site and lands on `/yoto/callback?error=…`, which renders its own page *in the other browser tab* and tells the user there. The Settings tab never learns about it; it simply times out after 3 minutes and shows the `timed_out` message, which is written to cover exactly this case. Making this reachable would mean adding server-side callback state, which is new surface the handoff does not specify. Recommend a follow-up, not this PR.
- **"App unreachable"** — `copy.md` explicitly says to inherit the existing `api()` message from `app.js:15-17` unchanged, which the code already does. Nothing to build.

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `yoto_maker/settings.py` | Modify | Add `delete(key)`. Nothing else. |
| `yoto_maker/config.py` | Modify | One precedence chain returning `(value, source)`; `resolve_client_id()`, `client_id_source()`, `mask_client_id()` all delegate to it. |
| `yoto_maker/yoto/auth.py` | Modify | `AuthNetworkError`; timeout parameter; non-raising `check_connection()`; `connection_status()` reports source + mask. |
| `yoto_maker/yoto/__init__.py` | Modify | Export `AuthError`, `AuthNetworkError`, `check_connection`. |
| `yoto_maker/server/app.py` | Modify | `AuthError` handler; `POST /api/yoto/check`; logout-on-save; `DELETE /api/yoto/client-id`. |
| `yoto_maker/server/static/styles.css` | Modify | `--warn-soft`, global `:focus-visible`, `.settings-head` / `.back-link` / `.setting*` block. |
| `yoto_maker/server/static/index.html` | Modify | Wrap card view in `#cardView`; add `#settingsView` with two `.setting` sections; delete `#setupRow`; footer Settings link; pill `aria-label`; relabel `#advToggle`. |
| `yoto_maker/server/static/app.js` | Modify | Hash routing + view swap; account section state machine; Client ID section state machine; bounded sign-in poll; fix `connectYoto()` leak. |
| `tests/test_models_and_settings.py` | Modify | `settings.delete()`, `client_id_source()`, `mask_client_id()`. |
| `tests/test_yoto_auth.py` | Modify | `AuthNetworkError`; `check_connection()`'s four states. |
| `tests/test_api.py` | Modify | `/api/status` new fields; `/api/yoto/check`; save-logs-out; `DELETE /api/yoto/client-id`. |
| `docs/SETUP-YOTO-CONNECTION.md` | Modify | Option A points at Settings; note that saving signs you out. |
| `docs/INSTALL-FOR-MOM.md` | Modify | Step 3 note uses the new link name. |
| `docs/RELEASE_NOTES.md`, `pyproject.toml`, `yoto_maker/__init__.py` | Modify | v0.1.9 entry + version bump (matches the per-feature convention in recent commits). |

`app.js` is 596 lines and grows by roughly 300. It stays one file: the project has no build step and no module loading, `index.html` includes exactly one script, and splitting it would mean either adding `type="module"` (changes caching/CSP behaviour for zero benefit at this size) or a second `<script>` tag with implicit global ordering. New code goes in clearly-fenced sections with the same comment style as the existing file.

---

## Task 1: `settings.delete()`

**Files:**
- Modify: `yoto_maker/settings.py:33-45`
- Test: `tests/test_models_and_settings.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_Settings.delete(key: str) -> bool` — `True` when a saved key was removed, `False` when there was nothing saved under that key.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_and_settings.py`:

```python
def test_settings_delete_removes_saved_key(temp_config):
    s = get_settings()
    s.set("yoto_client_id", "mine")
    assert s.get("yoto_client_id") == "mine"

    assert s.delete("yoto_client_id") is True
    assert s.get("yoto_client_id") is None

    # Deleting again is a no-op, not an error.
    assert s.delete("yoto_client_id") is False


def test_settings_delete_leaves_other_keys_alone(temp_config):
    s = get_settings()
    s.set("yoto_client_id", "mine")
    s.set("ai_api_key", "secret")
    s.delete("yoto_client_id")
    assert s.get("ai_api_key") == "secret"
    assert s.get("ai_model") == "gpt-image-1"  # default still resolves
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models_and_settings.py -q -k delete`
Expected: FAIL — `AttributeError: '_Settings' object has no attribute 'delete'`

- [ ] **Step 3: Implement `delete()`**

In `yoto_maker/settings.py`, add this method to `class _Settings` immediately after `set()`:

```python
    def delete(self, key: str) -> bool:
        """Remove a *saved* key. Returns True if something was actually removed.

        Reads the raw file rather than _load(), because _load() merges _DEFAULTS
        in — so a key that has a default would look present even when nothing was
        ever saved, and would reappear at its default value on the next read.
        Nothing in _DEFAULTS is deletable in that stronger sense; `yoto_client_id`
        is not a default, so for it this really is "forget it".
        """
        path = get_config().settings_path
        raw: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    raw = dict(loaded)
            except Exception:
                raw = {}
        if key not in raw:
            return False
        raw.pop(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_models_and_settings.py -q`
Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/settings.py tests/test_models_and_settings.py
git commit -m "feat(settings): add delete() so a saved Client ID can be cleared"
```

---

## Task 2: One precedence chain — value *and* source

**Files:**
- Modify: `yoto_maker/config.py:47-60` (replace `resolve_client_id`), `yoto_maker/config.py:70-78` (comment on the dead field)
- Modify: `yoto_maker/yoto/auth.py:175-180` (`connection_status`)
- Test: `tests/test_models_and_settings.py`

**Interfaces:**
- Consumes: `settings.get_settings().get()` (existing).
- Produces:
  - `config.resolve_client_id() -> str` (unchanged signature, unchanged behaviour)
  - `config.client_id_source() -> str` — one of `"env"`, `"saved"`, `"builtin"`
  - `config.mask_client_id(cid: str) -> str` — first 4 + `…` + last 3
  - `auth.connection_status() -> dict` — now `{"configured": bool, "connected": bool, "client_id_source": str, "client_id_masked": str}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_models_and_settings.py`:

```python
def test_client_id_source_tracks_the_same_chain(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.settings import get_settings

    # conftest sets YOTO_CLIENT_ID autouse — clear it to reach the lower tiers.
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    assert cfg.client_id_source() == "builtin"
    assert cfg.resolve_client_id() == cfg.DEFAULT_YOTO_CLIENT_ID

    get_settings().set("yoto_client_id", "from_setting")
    assert cfg.client_id_source() == "saved"
    assert cfg.resolve_client_id() == "from_setting"

    monkeypatch.setenv("YOTO_CLIENT_ID", "from_env")
    assert cfg.client_id_source() == "env"
    assert cfg.resolve_client_id() == "from_env"


def test_client_id_source_ignores_blank_values(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.settings import get_settings

    monkeypatch.setenv("YOTO_CLIENT_ID", "   ")
    get_settings().set("yoto_client_id", "from_setting")
    # A whitespace-only env var is not a Client ID; fall through to the saved one
    # rather than resolving to an empty string.
    assert cfg.client_id_source() == "saved"
    assert cfg.resolve_client_id() == "from_setting"


def test_mask_client_id(temp_config):
    from yoto_maker import config as cfg

    assert cfg.mask_client_id("a8OGO6EfbWit5tDUUrOz0g49s49NQoU1") == "a8OG…oU1"
    # Short enough that masking would reveal the whole thing anyway.
    assert cfg.mask_client_id("abc") == "abc"
    assert cfg.mask_client_id("") == ""


def test_connection_status_reports_source_and_mask(temp_config, monkeypatch):
    from yoto_maker import config as cfg
    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    st = auth.connection_status()
    assert st["connected"] is False
    assert st["client_id_source"] == "builtin"
    assert st["client_id_masked"] == cfg.mask_client_id(cfg.DEFAULT_YOTO_CLIENT_ID)
    assert st["configured"] is True  # legacy field, always True — kept for compatibility
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_models_and_settings.py -q -k "source or mask or connection_status"`
Expected: FAIL — `AttributeError: module 'yoto_maker.config' has no attribute 'client_id_source'`

- [ ] **Step 3: Replace `resolve_client_id()` with the shared chain**

In `yoto_maker/config.py`, replace the whole `resolve_client_id` function (lines 47-60) with:

```python
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
```

- [ ] **Step 4: Mark the stale `Config` field**

In `yoto_maker/config.py`, replace line 74 (`yoto_client_id: str = field(default_factory=resolve_client_id)`) with:

```python
    # Snapshot taken when the singleton is built. DO NOT read this at runtime:
    # a Client ID saved after startup would not appear here. Everything in the
    # app calls resolve_client_id() / client_id_source() live. Kept because
    # tests/conftest.py constructs Config with an explicit value.
    yoto_client_id: str = field(default_factory=resolve_client_id)
```

- [ ] **Step 5: Extend `connection_status()`**

In `yoto_maker/yoto/auth.py`, replace `connection_status` (lines 175-180) with:

```python
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
```

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: PASS — 48 existing tests plus the new ones, no failures.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/config.py yoto_maker/yoto/auth.py tests/test_models_and_settings.py
git commit -m "feat(config): report Client ID source and mask from one precedence chain"
```

---

## Task 3: Tell "Yoto said no" apart from "we're offline"

This is the task that makes the `unknown` state possible at all. Without it every failure looks like `broken`, and an offline user would be told her connection is broken and would disconnect a healthy account chasing a Wi-Fi problem.

**Files:**
- Modify: `yoto_maker/yoto/auth.py:32-38` (new exception), `:105-118` (`_token_request`), `:149-172` (`get_access_token`), append `check_connection`
- Modify: `yoto_maker/yoto/__init__.py`
- Test: `tests/test_yoto_auth.py`

**Interfaces:**
- Consumes: `config.resolve_client_id()` (Task 2).
- Produces:
  - `auth.AuthNetworkError(AuthError)` — raised when Yoto could not be reached at all
  - `auth._token_request(data: dict, timeout: float = 30) -> dict`
  - `auth.get_access_token(timeout: float = 30) -> str`
  - `auth.check_connection(timeout: float = 8.0) -> dict` — **never raises**; returns `{"state": "connected"}`, `{"state": "not_connected"}`, `{"state": "broken"}`, or `{"state": "unknown", "reason": "offline"}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_yoto_auth.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_yoto_auth.py -q`
Expected: FAIL — `AttributeError: module 'yoto_maker.yoto.auth' has no attribute 'AuthNetworkError'`

- [ ] **Step 3: Add the exception subclass**

In `yoto_maker/yoto/auth.py`, immediately after `class AuthError` (line 32-33), add:

```python
class AuthNetworkError(AuthError):
    """We couldn't reach Yoto at all — offline, DNS failure, or a timeout.

    Deliberately a *subclass* of AuthError so every existing ``except AuthError``
    still catches it and nothing downstream changes. It exists so the connection
    check can tell "your sign-in is broken" apart from "this computer isn't
    online". Reporting offline as broken would send a user to disconnect a
    perfectly healthy account while chasing a Wi-Fi problem.
    """
```

- [ ] **Step 4: Make the timeout a parameter and raise the right class**

In `yoto_maker/yoto/auth.py`, replace `_token_request` (lines 105-118) with:

```python
def _token_request(data: dict, timeout: float = 30) -> dict:
    try:
        resp = httpx.post(
            f"{config_mod.YOTO_AUTH_BASE}/oauth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise AuthError("Yoto rejected the sign-in. Please try connecting again.") from exc
    except Exception as exc:
        raise AuthNetworkError("We couldn't reach Yoto to finish signing in. Check your internet.") from exc
```

- [ ] **Step 5: Thread the timeout through `get_access_token`**

In `yoto_maker/yoto/auth.py`, change the signature and the refresh call in `get_access_token` (lines 149-172):

```python
def get_access_token(timeout: float = 30) -> str:
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
        },
        timeout=timeout,
    )
    # Auth0 may or may not rotate the refresh token; keep the old one if absent.
    new.setdefault("refresh_token", refresh)
    _save_tokens(new)
    return new["access_token"]
```

- [ ] **Step 6: Add `check_connection()`**

In `yoto_maker/yoto/auth.py`, append after `connection_status()`:

```python
def check_connection(timeout: float = 8.0) -> dict:
    """Ask Yoto whether the saved sign-in still works. Never raises.

    Four outcomes, and the difference between the last two is the entire reason
    this function exists:

      connected     — a refresh just succeeded (or an unexpired token is held)
      not_connected — nothing is saved on this computer
      broken        — something is saved, and Yoto will not accept it
      unknown       — we could not reach Yoto, so we do not know either way

    Timeboxed so an offline user is not left on a spinner. Note that when the
    cached access token has not expired yet this returns "connected" without a
    network round trip — that is intended: the failure modes this screen exists
    to catch (a dead refresh token, a Client ID change that forced a logout) all
    leave no usable cached token behind.
    """
    if _load_tokens() is None:
        return {"state": "not_connected"}
    try:
        get_access_token(timeout=timeout)
    except AuthNetworkError:
        # Must be checked before AuthError — it is a subclass.
        return {"state": "unknown", "reason": "offline"}
    except (NotConnectedError, AuthError):
        # A token file exists, so "no refresh token" is a broken sign-in rather
        # than a missing one.
        return {"state": "broken"}
    except Exception:
        return {"state": "unknown", "reason": "offline"}
    return {"state": "connected"}
```

- [ ] **Step 7: Export the new names**

Replace `yoto_maker/yoto/__init__.py` in full:

```python
"""Yoto integration: OAuth2 (PKCE) auth + MYO content upload."""
from __future__ import annotations

from .auth import (
    AuthError,
    AuthNetworkError,
    NotConnectedError,
    check_connection,
    connection_status,
    finish_login,
    logout,
    start_login,
)
from .client import YotoClient, YotoError, TrackInput

__all__ = [
    "start_login",
    "finish_login",
    "logout",
    "connection_status",
    "check_connection",
    "AuthError",
    "AuthNetworkError",
    "NotConnectedError",
    "YotoClient",
    "YotoError",
    "TrackInput",
]
```

- [ ] **Step 8: Run the full suite**

Run: `pytest -q`
Expected: PASS. In particular `test_get_access_token_refreshes_when_expired` still passes — its `fake_post` signature is `(url, data=None, **k)`, which absorbs the new `timeout` keyword.

- [ ] **Step 9: Commit**

```bash
git add yoto_maker/yoto/auth.py yoto_maker/yoto/__init__.py tests/test_yoto_auth.py
git commit -m "feat(auth): distinguish offline from rejected, add timeboxed check_connection()"
```

---

## Task 4: `POST /api/yoto/check` and a real handler for `AuthError`

**Files:**
- Modify: `yoto_maker/server/app.py:30-39` (imports), `:85-88` (handlers), `:475-478` (add the check route beside the login route)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `auth.check_connection()`, `auth.AuthError`, `auth.AuthNetworkError` (Task 3).
- Produces:
  - `POST /api/yoto/check` → `{"state": "connected"|"broken"|"not_connected"|"unknown", "reason"?: "offline"}`
  - `AuthError` → HTTP 400 `{"error": str, "reason": "offline"|"rejected"}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api.py`:

```python
def test_status_reports_client_id_source_and_mask(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "builtin"
    assert "…" in body["yoto"]["client_id_masked"]


def test_check_reports_not_connected_with_no_saved_sign_in(client):
    r = client.post("/api/yoto/check")
    assert r.status_code == 200
    assert r.json() == {"state": "not_connected"}


def test_check_reports_connected(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})
    assert client.post("/api/yoto/check").json() == {"state": "connected"}


def test_check_reports_broken(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    class Rejecting:
        status_code = 401

        def raise_for_status(self):
            import httpx
            raise httpx.HTTPStatusError("nope", request=None, response=None)

        def json(self):
            return {}

    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post", lambda *a, **k: Rejecting())
    assert client.post("/api/yoto/check").json() == {"state": "broken"}


def test_check_reports_unknown_when_offline(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    def boom(*a, **k):
        raise OSError("no route to host")

    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post", boom)
    assert client.post("/api/yoto/check").json() == {"state": "unknown", "reason": "offline"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_api.py -q -k check`
Expected: FAIL — 405 Method Not Allowed / 404 for `/api/yoto/check`.

- [ ] **Step 3: Import the new names**

In `yoto_maker/server/app.py`, replace the `from ..yoto import (...)` block (lines 30-39) with:

```python
from ..yoto import (
    AuthError,
    AuthNetworkError,
    NotConnectedError,
    TrackInput,
    YotoClient,
    YotoError,
    check_connection,
    connection_status,
    finish_login,
    logout,
    start_login,
)
```

- [ ] **Step 4: Add the `AuthError` handler**

In `yoto_maker/server/app.py`, immediately after the `_not_connected` handler (line 88), add:

```python
@app.exception_handler(AuthError)
async def _auth_error(_request, exc):  # noqa: ANN001
    """Sign-in failures were previously unhandled and surfaced as a bare 500.

    ``reason`` lets the UI choose its own wording (see the copy handoff) instead
    of echoing a message written for a different context. AuthNetworkError is a
    subclass of AuthError, so this handler catches both.
    """
    reason = "offline" if isinstance(exc, AuthNetworkError) else "rejected"
    return JSONResponse(status_code=400, content={"error": str(exc), "reason": reason})
```

- [ ] **Step 5: Add the check route**

In `yoto_maker/server/app.py`, immediately after `yoto_login` (line 478), add:

```python
@app.post("/api/yoto/check")
async def yoto_check() -> dict:
    """Actually ask Yoto whether the saved sign-in still works.

    POST rather than GET because it performs a network round trip and may rotate
    the stored sign-in — and because the origin guard only vets non-GET requests.
    Run off the event loop: check_connection() uses blocking httpx.
    """
    return await run_in_threadpool(check_connection)
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_api.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/server/app.py tests/test_api.py
git commit -m "feat(api): add POST /api/yoto/check and a friendly AuthError handler"
```

---

## Task 5: Saving or clearing a Client ID signs the user out

**Files:**
- Modify: `yoto_maker/server/app.py:463-472`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `settings.delete()` (Task 1), `connection_status()` (Task 2), `logout()` (existing).
- Produces:
  - `POST /api/yoto/client-id` `{"client_id": str}` → `{"ok": True, "yoto": {...}}`, and the saved sign-in is gone
  - `DELETE /api/yoto/client-id` → `{"ok": True, "yoto": {...}}`, and the saved sign-in is gone

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api.py`:

```python
def test_saving_a_client_id_signs_the_user_out(client, monkeypatch, temp_config):
    import time

    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})
    assert temp_config.token_path.exists()

    r = client.post("/api/yoto/client-id", json={"client_id": "  mine  "})
    assert r.status_code == 200
    # Tokens are minted per Client ID. Keeping the old sign-in would leave the
    # app reporting "connected" while every upload failed.
    assert not temp_config.token_path.exists()
    assert r.json()["yoto"]["connected"] is False
    assert r.json()["yoto"]["client_id_source"] == "saved"

    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_masked"] == "mine"  # short: masking would reveal it anyway


def test_saving_an_empty_client_id_is_rejected(client):
    r = client.post("/api/yoto/client-id", json={"client_id": "   "})
    assert r.status_code == 400


def test_deleting_the_client_id_reverts_and_signs_out(client, monkeypatch, temp_config):
    import time

    from yoto_maker import config as cfg
    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "mine"})
    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})

    r = client.request("DELETE", "/api/yoto/client-id")
    assert r.status_code == 200
    assert not temp_config.token_path.exists()
    assert r.json()["yoto"]["client_id_source"] == "builtin"
    assert cfg.resolve_client_id() == cfg.DEFAULT_YOTO_CLIENT_ID


def test_deleting_when_nothing_is_saved_is_harmless(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    r = client.request("DELETE", "/api/yoto/client-id")
    assert r.status_code == 200
    assert r.json()["yoto"]["client_id_source"] == "builtin"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_api.py -q -k client_id`
Expected: FAIL — the token file still exists after a save; `DELETE` returns 405.

- [ ] **Step 3: Replace the Client ID routes**

In `yoto_maker/server/app.py`, replace `set_client_id` (lines 463-472) with:

```python
@app.post("/api/yoto/client-id")
async def set_client_id(body: ClientIdBody) -> dict:
    """Save a Client ID — and sign out, which is not optional.

    Tokens are minted for one specific Client ID. get_access_token() refreshes
    using the *currently resolved* ID alongside the *previously stored* refresh
    token, and once the ID changes those two no longer belong to each other, so
    Yoto rejects the refresh. Keeping the old sign-in would leave the header pill
    saying "Yoto connected" while every upload failed — which is precisely the
    broken state this settings screen exists to rescue people from.
    """
    from ..settings import get_settings

    cid = body.client_id.strip()
    if not cid:
        raise HTTPException(400, "Please paste a Client ID first.")
    get_settings().set("yoto_client_id", cid)
    logout()
    return {"ok": True, "yoto": connection_status()}


@app.delete("/api/yoto/client-id")
async def clear_client_id() -> dict:
    """Forget a saved Client ID, falling back down the resolution chain.

    Signs out for the same reason as saving one. Note the UI hides the control
    that calls this whenever YOTO_CLIENT_ID is set, because in that case the
    fallback is the env var rather than the built-in default and the button's
    label would be untrue. This endpoint stays honest either way: it removes the
    saved value and reports whatever the chain now resolves to.
    """
    from ..settings import get_settings

    get_settings().delete("yoto_client_id")
    logout()
    return {"ok": True, "yoto": connection_status()}
```

- [ ] **Step 4: Run the full suite**

Run: `pytest -q`
Expected: PASS. All backend work is now complete and the frontend can be built against real endpoints.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/server/app.py tests/test_api.py
git commit -m "fix(api): changing or clearing the Client ID now signs the user out"
```

---

## Task 6: CSS — the `.setting` primitive, `--warn-soft`, global focus ring

**Files:**
- Modify: `yoto_maker/server/static/styles.css:1-14` (token block), append the new component block

**Interfaces:**
- Consumes: existing tokens `--accent`, `--accent-dark`, `--accent-soft`, `--ink`, `--muted`, `--card`, `--ok`, `--warn`, `--err`, `--radius`, `--shadow`.
- Produces: classes `.settings-head`, `.back-link`, `.setting`, `.setting-desc`, `.setting-status` (+ `.is-ok` / `.is-warn` / `.is-err` / `.is-unknown`, `.dot`, `.sub`), `.setting-body`, `.setting-actions`, `.setting-confirm`; token `--warn-soft`.

- [ ] **Step 1: Add the `--warn-soft` token**

In `yoto_maker/server/static/styles.css`, inside `:root`, add after `--err: #c62828;`:

```css
  /* Confirmation background. --warn on this measures 3.24:1 and FAILS AA, so
     --warn is used here only as a border; confirmation text is --ink (14.43:1).
     Deliberately no .msg-box.warn variant — the obvious warn-on-warn-soft
     pairing is exactly the one that fails. */
  --warn-soft: #fdf1e3;
```

- [ ] **Step 2: Add the global focus ring**

In `yoto_maker/server/static/styles.css`, immediately after the `.hidden` rule (line 25), add:

```css
/* Visible keyboard focus. Fixes a pre-existing gap: no <button> in this app had
   any focus indicator at all, so a keyboard user could not see where they were.
   :focus-visible (not :focus) means mouse users never see the ring, so the
   everyday path is unchanged. This lands globally and improves steps 1-4 too —
   that is intended, not scope creep. */
:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}
/* Inputs already signal focus via border-color; keep the ring off them so the
   two treatments don't stack into a doubled outline. */
input:focus-visible, textarea:focus-visible { outline: none; }
```

- [ ] **Step 3: Append the settings component block**

Append to the end of `yoto_maker/server/static/styles.css`:

```css
/* --- Settings view -------------------------------------------------- */
.settings-head { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.settings-head h2 { font-size: 22px; margin: 0; }
.settings-head h2:focus { outline: none; }   /* programmatic focus target */

.back-link {
  background: none; border: none; cursor: pointer; font-family: inherit;
  font-size: 16px; font-weight: 600; color: var(--accent-dark);
  padding: 8px 12px 8px 6px; border-radius: 10px;
  display: inline-flex; align-items: center; gap: 6px;
}
.back-link:hover { background: var(--accent-soft); }

/* --- The config-section primitive -----------------------------------
   Seven slots in fixed vertical order: h3 title, .setting-desc,
   .setting-status, .setting-body, .setting-actions, .msg-box,
   .setting-confirm. Every setting is one instance of this and nothing else.
   Adding setting #3 is: copy a <section class="setting">, fill the slots you
   need, append it. No CSS below needs to change, and no neighbouring section
   needs editing — nothing here is keyed to a specific setting's id. */
.setting {
  background: var(--card);
  border-radius: var(--radius);
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.setting h3 { font-size: 18px; margin: 0 0 6px; }
.setting-desc { color: var(--muted); font-size: 15px; margin: 0 0 16px; }

.setting-status {
  display: flex; align-items: flex-start; gap: 9px;
  font-size: 15px; font-weight: 600; margin-bottom: 16px;
}
.setting-status .dot {
  width: 10px; height: 10px; border-radius: 50%; flex: none;
  margin-top: 7px; background: var(--muted);
}
.setting-status.is-ok      .dot { background: var(--ok); }
.setting-status.is-warn    .dot { background: var(--warn); }
.setting-status.is-err     .dot { background: var(--err); }
.setting-status.is-unknown .dot { background: var(--muted); }
.setting-status .sub { display: block; font-weight: 400; color: var(--muted); font-size: 14px; }

.setting-body { margin-bottom: 16px; }
.setting-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

.setting-confirm {
  background: var(--warn-soft);
  border-left: 4px solid var(--warn);   /* the only use of --warn as a color here */
  border-radius: 12px;
  padding: 16px; margin-top: 14px;
  color: var(--ink);                     /* NOT --warn — that pairing fails AA */
}
.setting-confirm p { margin: 0 0 14px; font-size: 15px; }
.setting-confirm p:first-child { font-weight: 600; }
.setting-confirm .setting-actions { justify-content: flex-end; }

@media (max-width: 420px) {
  .setting-actions { flex-direction: column; align-items: stretch; }
  .setting-actions .btn { justify-content: center; }
}
```

- [ ] **Step 4: Verify nothing regressed visually**

Run: `python -m yoto_maker --no-tray --no-browser` and open `http://127.0.0.1:8777/`.
Expected: the card view is unchanged except that pressing Tab now draws a purple ring around each button. No layout shift, no new sections yet (the markup comes in Task 7).
Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/server/static/styles.css
git commit -m "feat(ui): add the .setting primitive, --warn-soft, and a global focus ring"
```

---

## Task 7: Markup — the two views and the two settings

After this task the settings view exists in the DOM but nothing renders into it and `app.js` still references deleted elements. **The tree is briefly broken between Task 7 and Task 8**, which is why they are adjacent and why Task 8's commit is the one that must be verified in a browser. If you prefer a strictly green tree at every commit, do Tasks 7 and 8 as one commit; do not reorder them.

**Files:**
- Modify: `yoto_maker/server/static/index.html`

**Interfaces:**
- Produces the element ids `app.js` will bind in Tasks 8-10: `#cardView`, `#settingsView`, `#settingsBack`, `#settingsTitle`, `#settingsLink`; `#accountStatus`, `#accountStatusHead`, `#accountStatusSub`, `#accountActions`, `#accountPrimary`, `#accountCancel`, `#accountMsg`, `#accountConfirm`, `#accountConfirmNo`, `#accountConfirmYes`; `#clientIdStatus`, `#clientIdStatusHead`, `#clientIdStatusSub`, `#clientIdBody`, `#clientIdInput`, `#clientIdSave`, `#clientIdEnvNote`, `#clientIdActions`, `#clientIdReset`, `#clientIdMsg`, `#clientIdConfirm`, `#clientIdConfirmText`, `#clientIdConfirmBody`, `#clientIdConfirmNo`, `#clientIdConfirmYes`.
- Removes: `#setupRow`, `#setupError` (`#clientIdInput` and `#clientIdSave` keep their ids but move into the settings view).

- [ ] **Step 1: Give the header pill its accessible name**

Replace lines 16-18 of `yoto_maker/server/static/index.html`:

```html
    <button id="yotoPill" class="pill" title="Yoto connection settings" aria-label="Yoto connection settings">
      <span class="dot"></span><span id="yotoPillText">Checking…</span>
    </button>
```

- [ ] **Step 2: Open the card view wrapper**

In `yoto_maker/server/static/index.html`, immediately after `<main>` (line 21), insert:

```html
    <!-- The card wizard. Exactly one of #cardView / #settingsView is un-hidden
         at a time; the hashchange handler in app.js is the only thing that
         swaps them, so clicking a link and pressing Back cannot diverge. -->
    <div id="cardView">
```

- [ ] **Step 3: Delete `#setupRow` and relabel the advanced link**

In step 3's `<section class="step">`, delete lines 121-134 entirely — the stale comment ("shown automatically only if the app has none baked in", which was never true because `configured` is permanently `true`), the `#setupRow` div, its `.msg-box.info` explainer, the Client ID input row, and `#setupError`.

Then replace the `#advRow` block (lines 139-141) with:

```html
        <div id="advRow" style="margin-top:10px">
          <a href="#settings" id="advToggle" class="tiny">⚙️ Yoto connection settings</a>
        </div>
```

Step 3 should now read: `#connectRow` (info box + `#connectBtn` + `#advRow`), then `#sendBtn`, then progress/error/done. Nothing else in step 3 changes.

- [ ] **Step 4: Add the footer Settings link and close the card view**

Replace the footer paragraph (lines 166-170) with:

```html
      <p class="tiny" style="text-align:center">
        Made with Yoto Maker · <span id="ver"></span> ·
        <a href="#settings" id="settingsLink">Settings</a> ·
        <a href="#" id="aboutLink">About</a> ·
        <a href="#" id="startOver">Start a new card</a>
      </p>
    </div><!-- /#cardView -->
```

- [ ] **Step 5: Add the settings view**

Immediately after `</div><!-- /#cardView -->` and before `</main>`, insert:

```html
    <!-- ===================== SETTINGS VIEW =====================
         Each <section class="setting"> below is one instance of the config
         primitive. Its seven slots always appear in this order:
           1 <h3> title           (required)
           2 .setting-desc        (required)
           3 .setting-status      (optional)
           4 .setting-body        (optional — the input control, if any)
           5 .setting-actions     (optional — primary button first)
           6 .msg-box             (required in markup, hidden until needed)
           7 .setting-confirm     (optional, hidden by default)

         To add setting #3: copy one of these sections, pick a new {id}, fill the
         slots you need and delete the ones you don't, append it below, and wire
         its buttons in app.js. No CSS changes. No edits to the sections above.
         Feedback is scoped to its own section — a failure in one setting must
         never render a message inside another. -->
    <div id="settingsView" class="hidden" aria-labelledby="settingsTitle">
      <div class="settings-head">
        <button id="settingsBack" class="back-link">← Back to my card</button>
        <h2 id="settingsTitle" tabindex="-1">Settings</h2>
      </div>

      <!-- Setting 1 — Your Yoto account. No .setting-body: this setting is a
           single action, not an input. -->
      <section class="setting" id="setting-account">
        <h3>Your Yoto account</h3>
        <p class="setting-desc">
          Yoto Maker sends the cards you make to your Yoto account. You sign in once,
          on Yoto’s own website, and it remembers you on this computer.
        </p>
        <p class="setting-desc">
          Use the button below if Yoto Maker has stopped being able to send cards, or if
          you want to use a different Yoto account.
        </p>

        <p class="setting-status is-unknown" id="accountStatus" role="status">
          <span class="dot" aria-hidden="true"></span>
          <span>
            <span id="accountStatusHead">Checking your Yoto connection…</span>
            <span class="sub" id="accountStatusSub"></span>
          </span>
        </p>

        <div class="setting-actions" id="accountActions">
          <button class="btn primary" id="accountPrimary" disabled>🔗 Sign in to Yoto again</button>
          <button class="btn ghost hidden" id="accountCancel">Cancel</button>
        </div>

        <div class="msg-box err hidden" id="accountMsg" role="alert" tabindex="-1"></div>

        <div class="setting-confirm hidden" id="accountConfirm" role="group" aria-labelledby="accountConfirmText">
          <p id="accountConfirmText">Sign in to Yoto again?</p>
          <p>
            This forgets the Yoto account on this computer, then opens Yoto’s website so
            you can sign in — with the same account, or a different one.
          </p>
          <p>Nothing in your Yoto account changes. The cards you’ve already made are safe.</p>
          <div class="setting-actions">
            <button class="btn ghost" id="accountConfirmNo">Never mind</button>
            <button class="btn primary" id="accountConfirmYes">Yes, sign in again</button>
          </div>
        </div>
      </section>

      <!-- Setting 2 — Yoto Client ID. Uses every slot; its confirmation text is
           filled by app.js because the same slot serves both save and reset. -->
      <section class="setting" id="setting-client-id">
        <h3>Yoto Client ID (advanced)</h3>
        <p class="setting-desc">
          Most people never need to change this. Yoto Maker comes with everything it
          needs already built in.
        </p>
        <p class="setting-desc">
          A Client ID is a code from Yoto’s developer website that tells Yoto which app
          is asking to sign in. You’d only paste your own here if someone has asked you
          to.
          <a href="https://github.com/mmackelprang/yoto-maker/blob/main/docs/SETUP-YOTO-CONNECTION.md"
             target="_blank" rel="noopener">How to get one&nbsp;↗</a>
        </p>

        <p class="setting-status is-ok" id="clientIdStatus" role="status">
          <span class="dot" aria-hidden="true"></span>
          <span>
            <span id="clientIdStatusHead"></span>
            <span class="sub" id="clientIdStatusSub"></span>
          </span>
        </p>

        <div class="setting-body" id="clientIdBody">
          <label class="tiny" for="clientIdInput">Paste a Client ID</label>
          <div class="row wrap" style="margin-top:6px">
            <input id="clientIdInput" type="text" class="grow" placeholder="Paste your Yoto Client ID here" />
            <button class="btn" id="clientIdSave">Save</button>
          </div>
          <p class="tiny hidden" id="clientIdEnvNote" style="margin-top:8px">
            You can still type one here, but it won’t be used while the one above is set.
          </p>
        </div>

        <div class="setting-actions hidden" id="clientIdActions">
          <button class="btn" id="clientIdReset">Go back to the built-in one</button>
        </div>

        <div class="msg-box err hidden" id="clientIdMsg" role="alert" tabindex="-1"></div>

        <div class="setting-confirm hidden" id="clientIdConfirm" role="group" aria-labelledby="clientIdConfirmText">
          <p id="clientIdConfirmText"></p>
          <div id="clientIdConfirmBody"></div>
          <div class="setting-actions">
            <button class="btn ghost" id="clientIdConfirmNo">Never mind</button>
            <button class="btn primary" id="clientIdConfirmYes"></button>
          </div>
        </div>
      </section>
    </div><!-- /#settingsView -->
```

- [ ] **Step 6: Check the markup is well-formed**

Run: `python -c "import xml.dom.minidom" && python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area","base","br","col","embed","hr","img","input","link","meta","source","track","wbr"}

class Check(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.problems = []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"line {self.getpos()[0]}: </{tag}> closes {self.stack[-1:] or ['nothing']}")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()

c = Check()
c.feed(Path("yoto_maker/server/static/index.html").read_text(encoding="utf-8"))
print("UNCLOSED:", c.stack)
print("MISMATCHED:", c.problems)
PY`
Expected: `UNCLOSED: []` and `MISMATCHED: []`.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/server/static/index.html
git commit -m "feat(ui): add the settings view markup and move the Client ID out of step 3"
```

---

## Task 8: View routing

**Files:**
- Modify: `yoto_maker/server/static/app.js` — `renderStatus()` (128-139), `saveClientId()` (141-154), `init()` (51-72), `wire()` (517-593)

**Interfaces:**
- Consumes: the ids from Task 7; `/api/status` fields from Task 2.
- Produces: `inSettings()`, `applyRoute()`, `gotoSettings(opener)`, `leaveSettings()`, `openSettings()`, `closeSettings()`, module-level `returnFocusTo`.
- Note: `openSettings()` and `closeSettings()` are defined as stubs here and filled in by Tasks 9 and 10.

- [ ] **Step 1: Fix `renderStatus()` and delete the dead `saveClientId()`**

In `yoto_maker/server/static/app.js`, replace `renderStatus` and `saveClientId` (lines 128-154) with:

```js
function renderStatus() {
  const pill = $("#yotoPill");
  const text = $("#yotoPillText");
  const connected = STATUS.yoto.connected;
  pill.classList.toggle("connected", connected);
  text.textContent = connected ? "Yoto connected" : "Yoto not connected";
  // NOTE: STATUS.yoto.configured is permanently true (resolve_client_id() falls
  // back to a non-empty baked-in constant), so it drives nothing. The old
  // `show($("#setupRow"), !configured)` here meant the Client ID row could never
  // appear on its own; that row now lives in the settings view.
  show($("#connectRow"), !connected);
  $("#sendBtn").disabled = !connected;
}
```

(`saveClientId()` is deleted outright — Task 10 replaces it with the settings-view version.)

- [ ] **Step 2: Add the routing section**

In `yoto_maker/server/static/app.js`, immediately after `refreshStatus()` (line 159), insert:

```js
// ---- settings view routing ------------------------------------------------
// The hashchange handler is the single place that swaps views. Every entry point
// just sets location.hash, so a click and a browser Back press cannot diverge.
let returnFocusTo = null;

function inSettings() { return location.hash === "#settings"; }

function applyRoute() {
  if (!STATUS) return;            // init() calls applyRoute() once STATUS exists
  const on = inSettings();
  show($("#cardView"), !on);
  show($("#settingsView"), on);
  document.title = on ? "Settings · Yoto Maker" : "Yoto Maker";
  if (on) {
    // The card view may be scrolled far down a long track list; landing
    // mid-page on a fresh view is disorienting.
    window.scrollTo(0, 0);
    $("#settingsTitle").focus();
    openSettings();
  } else {
    closeSettings();
    const back = returnFocusTo && document.contains(returnFocusTo) ? returnFocusTo : null;
    returnFocusTo = null;
    if (back) back.focus();
    // The user may have just connected or disconnected; step 3 and #sendBtn
    // must reflect reality on return.
    refreshStatus().catch(() => {});
  }
}

function gotoSettings(opener) {
  returnFocusTo = opener || null;
  if (inSettings()) applyRoute();      // already there (e.g. reload) — just render
  else location.hash = "settings";     // hashchange does the swap
}

function leaveSettings() {
  // Always setting the hash costs one extra history entry but can never escape
  // the app, which history.back() could if the user arrived at #settings direct.
  if (location.hash) location.hash = "";
  else applyRoute();
}

// No focus trap and no Escape-to-exit: .hidden is `display: none !important`,
// which takes the hidden view out of the tab order, the accessibility tree and
// find-in-page for free. This is a page, not a dialog — and the user may be
// mid-way through pasting a Client ID, which a stray Escape must not discard.
```

- [ ] **Step 3: Add the open/close stubs**

Immediately after the routing section, insert:

```js
// Filled in by the two setting sections below.
function openSettings() {
  renderClientId();
  checkAccount();
}

function closeSettings() {
  stopSignInPoll();
  closeAccountConfirm();
  closeClientIdConfirm();
}
```

- [ ] **Step 4: Call `applyRoute()` from `init()`**

In `yoto_maker/server/static/app.js`, in `init()`, replace the line `checkUpdate();  // non-blocking` (line 71) with:

```js
  applyRoute();    // honour a #settings hash on load / reload
  checkUpdate();   // non-blocking
```

- [ ] **Step 5: Rewire the entry points**

In `yoto_maker/server/static/app.js`, in `wire()`, replace the `#clientIdSave` / `#advToggle` lines (564-569) with:

```js
  // Settings entry points. All three route through gotoSettings() so the
  // element to return focus to on exit is recorded in one place.
  $("#advToggle").addEventListener("click", (e) => { e.preventDefault(); gotoSettings(e.currentTarget); });
  $("#settingsLink").addEventListener("click", (e) => { e.preventDefault(); gotoSettings(e.currentTarget); });
  $("#settingsBack").addEventListener("click", leaveSettings);
  window.addEventListener("hashchange", applyRoute);
```

Then replace the `#yotoPill` handler (lines 577-579) with:

```js
  // The pill now always goes to Settings. It used to be a dead click whenever
  // the user was connected — and a user whose upload just failed looks for the
  // one thing on screen that talks about her Yoto connection, so following the
  // symptom lands her exactly where the fix is.
  $("#yotoPill").addEventListener("click", (e) => gotoSettings(e.currentTarget));
```

- [ ] **Step 6: Replace the global Escape handler**

In `yoto_maker/server/static/app.js`, in `wire()`, replace line 575
(`document.addEventListener("keydown", (e) => { if (e.key === "Escape") show(about, false); });`) with:

```js
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    show(about, false);
    if (!inSettings()) return;
    // Inside settings, Escape does exactly one thing: dismiss an open
    // confirmation. Anywhere else on this surface it does nothing.
    if (!$("#accountConfirm").classList.contains("hidden")) { closeAccountConfirm(); return; }
    if (!$("#clientIdConfirm").classList.contains("hidden")) { closeClientIdConfirm(); return; }
  });
```

- [ ] **Step 7: Verify in the browser**

Run: `python -m yoto_maker --no-tray --no-browser`, open `http://127.0.0.1:8777/`, open the browser console.
Expected: the card view renders; clicking the header pill switches to the Settings view with "Settings" focused; browser Back returns to the card; reloading on `#settings` lands on Settings. The console shows `ReferenceError: renderClientId is not defined` — expected, Tasks 9 and 10 supply it. Stop the server.

- [ ] **Step 8: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): route between the card view and the settings view via #settings"
```

---

## Task 9: The Yoto account setting

**Files:**
- Modify: `yoto_maker/server/static/app.js` — append the account section; replace `connectYoto()` (461-473); extend `wire()`

**Interfaces:**
- Consumes: `POST /api/yoto/check` (Task 4), `POST /api/yoto/logout`, `GET /api/yoto/login`, `/api/status`.
- Produces: `checkAccount()`, `setAccountState(state)`, `renderAccount()`, `openAccountConfirm()`, `closeAccountConfirm()`, `startSignIn()`, `stopSignInPoll()`, `withTimeout(promise, ms)`, `accountMsg(kind, html)`, constants `SIGNIN_POLL_MS`, `SIGNIN_MAX_MS`.

- [ ] **Step 1: Add the account section**

In `yoto_maker/server/static/app.js`, insert immediately after the `openSettings` / `closeSettings` stubs from Task 8:

```js
// ---- setting 1: your Yoto account -----------------------------------------
// Copy is verbatim from the design handoff (copy.md §3). Do not reword.
const ACCOUNT_STATUS = {
  checking: {
    cls: "is-unknown", head: "Checking your Yoto connection…", sub: "",
  },
  connected: {
    cls: "is-ok", head: "Connected and working",
    sub: "We just checked with Yoto and everything’s fine.",
  },
  not_connected: {
    cls: "is-unknown", head: "Not connected yet",
    sub: "Connect your Yoto account to send cards to it.",
  },
  broken: {
    cls: "is-err", head: "There’s a problem with this connection",
    sub: "Yoto Maker can’t send cards right now. Signing in again usually fixes it.",
  },
  unknown: {
    cls: "is-unknown", head: "We couldn’t check right now",
    sub: "This computer doesn’t seem to be online. Check your internet, then come back.",
  },
  signing_in: {
    cls: "is-warn", head: "Waiting for you to sign in…",
    sub: "We opened Yoto’s website in another tab. Sign in there, then come back here.",
  },
};

// The backend tags sign-in failures with a reason so the UI can use its own
// wording rather than echoing a message written for a different context.
const SIGNIN_ERRORS = {
  rejected: "Yoto couldn’t complete the sign-in. Please try again.",
  offline: "We couldn’t reach Yoto. Check your internet connection, then try again.",
};

const CHECK_TIMEOUT_MS = 8000;
const SIGNIN_POLL_MS = 2000;
const SIGNIN_MAX_MS = 3 * 60 * 1000;

const ACCOUNT = { state: "checking", prev: "not_connected", timer: null };

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms)),
  ]);
}

function accountMsg(kind, html) {
  const box = $("#accountMsg");
  box.className = "msg-box " + kind;
  box.innerHTML = html;
  show(box, true);
}

function setAccountState(state) {
  // Remember the last settled state so Cancel and a 3-minute timeout can put
  // the section back where it was rather than guessing.
  if (state !== "signing_in" && state !== "checking") ACCOUNT.prev = state;
  ACCOUNT.state = state;
  renderAccount();
}

function renderAccount() {
  const s = ACCOUNT_STATUS[ACCOUNT.state] || ACCOUNT_STATUS.unknown;
  $("#accountStatus").className = "setting-status " + s.cls;
  $("#accountStatusHead").textContent = s.head;
  $("#accountStatusSub").textContent = s.sub;

  const btn = $("#accountPrimary");
  if (ACCOUNT.state === "signing_in") {
    btn.textContent = "Waiting for Yoto…";
    btn.disabled = true;
  } else if (ACCOUNT.state === "not_connected") {
    // Word-for-word identical to step 3's #connectBtn, deliberately: the two
    // places that do this must never look like different features.
    btn.textContent = "🔗 Connect my Yoto account";
    btn.disabled = false;
  } else {
    btn.textContent = "🔗 Sign in to Yoto again";
    // Only "checking" disables it. An offline user may still legitimately want
    // to start a sign-in — she might be about to fix her Wi-Fi — so `unknown`
    // must never dead-end her.
    btn.disabled = ACCOUNT.state === "checking";
  }
  show($("#accountCancel"), ACCOUNT.state === "signing_in");
}

async function checkAccount() {
  setAccountState("checking");
  let res;
  try {
    res = await withTimeout(api("/api/yoto/check", { method: "POST" }), CHECK_TIMEOUT_MS);
  } catch (_) {
    // Never render a network problem as "your connection is broken", or she
    // will disconnect a healthy account chasing a Wi-Fi fault.
    setAccountState("unknown");
    return;
  }
  setAccountState(res && res.state ? res.state : "unknown");
}

function openAccountConfirm() {
  // Primitive rule: the confirmation replaces the actions slot, so there is
  // never more than one live set of choices in a section.
  show($("#accountActions"), false);
  show($("#accountConfirm"), true);
  // Focus starts on the way out, not the way through: a reflexive Space or
  // Enter must not disconnect her account.
  $("#accountConfirmNo").focus();
}

// restoreFocus defaults to true: Escape and "Never mind" both return focus to
// the button that opened the confirmation. The "Yes" path passes false, because
// startSignIn() is about to take over.
function closeAccountConfirm(restoreFocus = true) {
  const box = $("#accountConfirm");
  if (box.classList.contains("hidden")) return;
  show(box, false);
  show($("#accountActions"), true);
  if (restoreFocus) $("#accountPrimary").focus();
}

function stopSignInPoll() {
  if (ACCOUNT.timer) { clearInterval(ACCOUNT.timer); ACCOUNT.timer = null; }
}

async function startSignIn() {
  const wasConnected = !!(STATUS && STATUS.yoto && STATUS.yoto.connected);
  clearError($("#accountMsg"));
  let url;
  try {
    // Folding the sign-out into the sign-in is what lets one button serve both
    // "fix this" and "switch accounts" — the user never has to know they are
    // two operations.
    if (wasConnected) await api("/api/yoto/logout", { method: "POST" });
    ({ url } = await api("/api/yoto/login"));
  } catch (e) {
    await refreshStatus().catch(() => {});
    setAccountState(wasConnected ? "broken" : "not_connected");
    accountMsg("err", SIGNIN_ERRORS[e.data && e.data.reason] || e.message);
    return;
  }

  const win = window.open(url, "_blank");
  if (!win) {
    // Popup blocked. A real link is the only reliable recovery — "allow popups"
    // is not an actionable instruction for this audience.
    accountMsg("info",
      "Your browser stopped the Yoto window from opening.<br>" +
      '<a id="accountOpenLink" target="_blank" rel="noopener">Open Yoto’s sign-in page&nbsp;↗</a>');
    $("#accountOpenLink").href = url;   // set as a property, never interpolated
    await refreshStatus().catch(() => {});
    await checkAccount();
    return;
  }

  setAccountState("signing_in");
  const deadline = Date.now() + SIGNIN_MAX_MS;
  stopSignInPoll();
  ACCOUNT.timer = setInterval(async () => {
    if (Date.now() > deadline) {
      stopSignInPoll();
      setAccountState(ACCOUNT.prev);
      accountMsg("info",
        "We stopped waiting for the sign-in. If you finished signing in on Yoto’s website, " +
        "press “Sign in to Yoto again” — otherwise you can try again now.");
      return;
    }
    try { await refreshStatus(); } catch (_) { return; }
    if (STATUS.yoto.connected) {
      stopSignInPoll();
      // A token file appearing is not proof it works; confirm with a real check
      // before claiming success. The status line updates first so the polite
      // role="status" announcement isn't queued behind the assertive alert.
      await checkAccount();
      accountMsg("ok", "🎉 You’re signed in. Yoto Maker can send cards again.");
    }
  }, SIGNIN_POLL_MS);
}

function cancelSignIn() {
  stopSignInPoll();
  setAccountState(ACCOUNT.prev);
  accountMsg("info", "Stopped waiting. You can close the Yoto tab if it’s still open.");
}
```

- [ ] **Step 2: Fix the pre-existing poller leak in `connectYoto()`**

In `yoto_maker/server/static/app.js`, replace `connectYoto` (lines 461-473) with:

```js
// ---- connect + send -------------------------------------------------------
let connectTimer = null;

async function connectYoto() {
  clearError($("#sendError"));
  try {
    const { url } = await api("/api/yoto/login");
    window.open(url, "_blank");
    // Bounded poll. The previous version cleared the interval only on success,
    // so a sign-in the user closed or cancelled polled /api/status forever until
    // the page was reloaded.
    if (connectTimer) { clearInterval(connectTimer); connectTimer = null; }
    const deadline = Date.now() + SIGNIN_MAX_MS;
    connectTimer = setInterval(async () => {
      if (Date.now() > deadline) { clearInterval(connectTimer); connectTimer = null; return; }
      try { await refreshStatus(); } catch (_) { return; }
      if (STATUS.yoto.connected) { clearInterval(connectTimer); connectTimer = null; }
    }, SIGNIN_POLL_MS);
  } catch (e) {
    if (connectTimer) { clearInterval(connectTimer); connectTimer = null; }
    showError($("#sendError"), SIGNIN_ERRORS[e.data && e.data.reason] || e.message);
  }
}
```

- [ ] **Step 3: Wire the account buttons**

In `yoto_maker/server/static/app.js`, in `wire()`, immediately after the settings entry-point lines added in Task 8, add:

```js
  // Account setting. not_connected skips the confirmation entirely — there is
  // nothing to forget, so the button goes straight to Yoto.
  $("#accountPrimary").addEventListener("click", () => {
    if (ACCOUNT.state === "not_connected") startSignIn();
    else openAccountConfirm();
  });
  $("#accountConfirmNo").addEventListener("click", () => closeAccountConfirm());
  $("#accountConfirmYes").addEventListener("click", () => {
    closeAccountConfirm(false);
    startSignIn();
  });
  $("#accountCancel").addEventListener("click", cancelSignIn);
```

- [ ] **Step 4: Verify in the browser**

Run: `python -m yoto_maker --no-tray --no-browser` and open `http://127.0.0.1:8777/#settings`.
Expected: the account section shows "Checking your Yoto connection…" with the button disabled, then settles on `not_connected` (or `connected` if you have a real sign-in). The console still shows `ReferenceError: renderClientId is not defined` — Task 10 supplies it. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): Yoto account setting with a live check and a bounded sign-in poll"
```

---

## Task 10: The Client ID setting

**Files:**
- Modify: `yoto_maker/server/static/app.js` — append the Client ID section; extend `wire()`

**Interfaces:**
- Consumes: `STATUS.yoto.client_id_source` / `client_id_masked` (Task 2), `POST` and `DELETE /api/yoto/client-id` (Task 5), `checkAccount()` (Task 9).
- Produces: `renderClientId()`, `openClientIdConfirm(kind)`, `closeClientIdConfirm()`, `submitClientId(kind)`, `clientIdMsg(kind, text)`.

- [ ] **Step 1: Add the Client ID section**

Append to `yoto_maker/server/static/app.js`, immediately after the account section from Task 9:

```js
// ---- setting 2: Yoto Client ID --------------------------------------------
// Copy is verbatim from the design handoff (copy.md §4). Do not reword.
const CLIENT_ID_STATUS = {
  builtin: {
    cls: "is-ok", head: "Using the built-in Client ID",
    sub: "This is what most people use. Nothing to do here.",
  },
  saved: {
    cls: "is-ok", head: "Using your own Client ID",
    sub: "",   // built from the masked value below
  },
  env: {
    cls: "is-warn", head: "Set outside the app",
    sub: "Someone set this up on this computer using YOTO_CLIENT_ID, and that takes " +
         "priority. To change it, they’ll need to change it there.",
  },
};

const CLIENT_ID_CONFIRM = {
  save: {
    title: "Use this Client ID?",
    body: [
      "Yoto Maker will start using the Client ID you pasted. Because this changes how " +
      "the app signs in, you’ll need to sign in to Yoto again afterwards.",
      "Nothing in your Yoto account changes.",
    ],
    yes: "Yes, use it",
  },
  reset: {
    title: "Go back to the built-in Client ID?",
    body: [
      "Yoto Maker will forget the Client ID you pasted and use the one it came with. " +
      "You’ll need to sign in to Yoto again afterwards.",
      "Nothing in your Yoto account changes.",
    ],
    yes: "Yes, use the built-in one",
  },
};

function clientIdMsg(kind, text) {
  const box = $("#clientIdMsg");
  box.className = "msg-box " + kind;
  box.textContent = text;
  show(box, true);
}

function renderClientId() {
  const source = (STATUS && STATUS.yoto && STATUS.yoto.client_id_source) || "builtin";
  const masked = (STATUS && STATUS.yoto && STATUS.yoto.client_id_masked) || "";
  const s = CLIENT_ID_STATUS[source] || CLIENT_ID_STATUS.builtin;

  $("#clientIdStatus").className = "setting-status " + s.cls;
  $("#clientIdStatusHead").textContent = s.head;
  $("#clientIdStatusSub").textContent =
    source === "saved" ? `Ends in ${masked.slice(-3)}. Saved on this computer only.` : s.sub;

  const isEnv = source === "env";
  // Disabled and explained, not hidden. Hiding the input would make the section
  // look broken to the person who came here specifically to change this.
  $("#clientIdInput").disabled = isEnv;
  $("#clientIdSave").disabled = isEnv;
  show($("#clientIdEnvNote"), isEnv);

  const actions = $("#clientIdActions");
  if (actions) {
    // Absent, not merely hidden, when an env var is in effect: deleting the
    // saved value would fall through to the env var rather than the built-in
    // one, so "Go back to the built-in one" would be a lie.
    if (isEnv) actions.remove();
    else show(actions, source === "saved");
  }
}

function openClientIdConfirm(kind) {
  const c = CLIENT_ID_CONFIRM[kind];
  $("#clientIdConfirm").dataset.kind = kind;
  $("#clientIdConfirmText").textContent = c.title;
  const body = $("#clientIdConfirmBody");
  body.innerHTML = "";
  c.body.forEach((para) => {
    const p = document.createElement("p");
    p.textContent = para;
    body.appendChild(p);
  });
  $("#clientIdConfirmYes").textContent = c.yes;

  const actions = $("#clientIdActions");
  if (actions) show(actions, false);
  // The Save button lives in the body slot rather than the actions slot, so
  // disable it too — one live set of choices per section, always.
  $("#clientIdInput").disabled = true;
  $("#clientIdSave").disabled = true;
  show($("#clientIdConfirm"), true);
  $("#clientIdConfirmNo").focus();
}

function closeClientIdConfirm(restoreFocus = true) {
  const box = $("#clientIdConfirm");
  if (box.classList.contains("hidden")) return;
  const kind = box.dataset.kind;
  show(box, false);
  $("#clientIdConfirmNo").disabled = false;
  $("#clientIdConfirmYes").disabled = false;
  renderClientId();                       // restores the input, Save and the reset action
  if (restoreFocus) {
    const opener = kind === "reset" ? $("#clientIdReset") : $("#clientIdSave");
    if (opener) opener.focus();
  }
}

async function submitClientId(kind) {
  $("#clientIdConfirmNo").disabled = true;
  $("#clientIdConfirmYes").disabled = true;
  clearError($("#clientIdMsg"));
  try {
    if (kind === "reset") {
      await api("/api/yoto/client-id", { method: "DELETE" });
    } else {
      await api("/api/yoto/client-id", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: $("#clientIdInput").value.trim() }),
      });
    }
  } catch (e) {
    // Leave the value intact so nothing the user pasted is lost.
    closeClientIdConfirm(false);
    clientIdMsg("err", "We couldn’t save that. Please try again.");
    $("#clientIdInput").focus();
    return;
  }

  $("#clientIdInput").value = "";
  await refreshStatus();
  closeClientIdConfirm(false);
  // Both actions signed the user out on the server, so re-render the account
  // section above — it has already flipped to "Not connected yet".
  await checkAccount();
  clientIdMsg("ok", kind === "reset"
    ? "Done — back to the built-in Client ID. Now sign in to Yoto again using the button above."
    : "Saved. Now sign in to Yoto again using the button above.");
  $("#clientIdMsg").focus();
}
```

- [ ] **Step 2: Wire the Client ID controls**

In `yoto_maker/server/static/app.js`, in `wire()`, immediately after the account button wiring from Task 9, add:

```js
  // Client ID setting.
  const trySave = () => {
    const cid = $("#clientIdInput").value.trim();
    if (!cid) {
      // Never confirm a no-op.
      clientIdMsg("err", "Please paste a Client ID first.");
      $("#clientIdInput").focus();
      return;
    }
    openClientIdConfirm("save");
  };
  $("#clientIdSave").addEventListener("click", trySave);
  $("#clientIdInput").addEventListener("keydown", (e) => { if (e.key === "Enter") trySave(); });
  $("#clientIdReset").addEventListener("click", () => openClientIdConfirm("reset"));
  $("#clientIdConfirmNo").addEventListener("click", () => closeClientIdConfirm());
  $("#clientIdConfirmYes").addEventListener("click", () =>
    submitClientId($("#clientIdConfirm").dataset.kind));
```

- [ ] **Step 3: Verify in the browser**

Run: `python -m yoto_maker --no-tray --no-browser` and open `http://127.0.0.1:8777/#settings`.
Expected: no console errors. The Client ID section shows "Using the built-in Client ID" (assuming `YOTO_CLIENT_ID` is unset) with no reset button. Typing a value and pressing Save opens the confirmation with "Never mind" focused; Escape dismisses it. Stop the server.

- [ ] **Step 4: Run the full suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): Client ID setting with source-aware states and inline confirmations"
```

---

## Task 11: Documentation

Both user-facing guides go stale the moment `#setupRow` moves, and both are read by the least technical users in the audience.

**Files:**
- Modify: `docs/SETUP-YOTO-CONNECTION.md` (Option A, around lines 51-54)
- Modify: `docs/INSTALL-FOR-MOM.md` (step 3 note, around lines 81-83)
- Modify: `docs/RELEASE_NOTES.md`, `pyproject.toml:7`, `yoto_maker/__init__.py:3`
- Modify: `docs/design-handoffs/README.md` (mark the package Shipped)

- [ ] **Step 1: Rewrite Option A**

In `docs/SETUP-YOTO-CONNECTION.md`, replace the "Option A" paragraph with:

```markdown
**Option A — paste it into the app (no rebuild).**
Open Yoto Maker and click the **Yoto** button in the top-right corner (or
**Settings** at the bottom of the page). Under **Yoto Client ID (advanced)**,
paste your Client ID and click **Save**. It's stored on that computer only and
overrides the bundled one.

Saving a Client ID **signs you out of Yoto**, because a sign-in belongs to one
specific Client ID. The Settings page says so before you confirm, and afterwards
the **Your Yoto account** section right above tells you to sign in again. If you
change your mind, **Go back to the built-in one** appears once you've saved your
own — it signs you out too, for the same reason.

> If `YOTO_CLIENT_ID` is set on that computer (Option B), it wins over anything
> saved in the app. Settings shows **Set outside the app** in that case and
> disables the box, rather than accepting a value it would then ignore.
```

- [ ] **Step 2: Update the install guide's step 3 note**

In `docs/INSTALL-FOR-MOM.md`, replace the step 3️⃣ note block with:

```markdown
> ℹ️ Connecting your Yoto is already set up for you — you just sign in. (If you
> ever need to use a *different* Yoto account, or if sending stops working,
> click the **Yoto** button in the top-right corner — that opens a **Settings**
> page with one button to fix it. Most people never need it.) And even without
> connecting, adding audio, pictures, and printing labels all work.
```

Leave the "four numbered steps" sentence earlier in the file exactly as it is — the screen still has four steps and must keep agreeing with the printed guide.

- [ ] **Step 3: Bump the version**

`pyproject.toml` line 7: `version = "0.1.9"`
`yoto_maker/__init__.py` line 3: `__version__ = "0.1.9"`

- [ ] **Step 4: Add the release note**

In `docs/RELEASE_NOTES.md`, change the title line to `# Yoto Maker v0.1.9` and insert above the `### 🆕 New in v0.1.8` section:

```markdown
### 🆕 New in v0.1.9
- **A Settings page.** Click the **Yoto** button in the top-right corner (or
  **Settings** at the bottom) to see whether your Yoto connection is actually
  working, and fix it with one button if it isn't. The four numbered steps are
  unchanged — step 3 is now a little shorter.
- **"Yoto connected" now means it.** The app used to say you were connected
  whenever a saved sign-in existed on the computer, even if Yoto had stopped
  accepting it — so the one time you needed the truth, it told you everything
  was fine. Settings now checks with Yoto for real, and says **We couldn't check
  right now** if the computer is offline, rather than blaming your account.
- **Keyboard users can see where they are.** Every button now shows a purple
  outline when you move to it with the Tab key.

### Fixed in v0.1.9
- **Changing the Client ID no longer breaks sending, silently.** A sign-in
  belongs to one Client ID, so changing it now signs you out and tells you to
  sign in again — instead of leaving the app claiming to be connected while
  every upload failed.
- **You can go back to the built-in Client ID** after pasting your own. There was
  previously no way to undo it.
- **An abandoned sign-in stops waiting.** Closing the Yoto tab without signing in
  used to leave the app checking every two seconds forever. It now stops after
  three minutes, and you can press **Cancel**.
```

- [ ] **Step 5: Mark the handoff shipped**

In `docs/design-handoffs/README.md`, change the `configuration-surface` row's Status from `Proposed` to `Shipped`.

- [ ] **Step 6: Commit**

```bash
git add docs/SETUP-YOTO-CONNECTION.md docs/INSTALL-FOR-MOM.md docs/RELEASE_NOTES.md \
        docs/design-handoffs/README.md pyproject.toml yoto_maker/__init__.py
git commit -m "docs: point the setup guides at Settings; release notes for v0.1.9"
```

---

## Task 12: Final verification

**Files:** none modified unless a defect is found.

- [ ] **Step 1: Run the full suite**

Run: `pytest -q`
Expected: PASS, no failures, no errors. Expect roughly 48 + 22 tests.

- [ ] **Step 2: Confirm no dead references remain**

Run: `grep -n "setupRow\|setupError\|saveClientId\|yoto.configured" yoto_maker/server/static/*.js yoto_maker/server/static/*.html`
Expected: no output. Every one of these was removed.

- [ ] **Step 3: Confirm the primitive is not keyed to a specific setting**

Run: `grep -n "setting-account\|setting-client-id" yoto_maker/server/static/styles.css`
Expected: no output. If a per-setting id appears in the stylesheet, the extensibility property is broken — fix it before opening the PR.

- [ ] **Step 4: Confirm no straight apostrophes reached user-visible copy**

Run: `grep -n "won't\|can't\|you'll\|doesn't\|Yoto's\|you've\|everything's\|couldn't\|there's\|you'd\|they'll\|it's" yoto_maker/server/static/index.html yoto_maker/server/static/app.js`
Expected: no output in any user-visible string. (Comments may use straight apostrophes; only rendered copy must use `’`.)

- [ ] **Step 5: Run the Test Plan below in a real browser**

Every scenario in the Test Plan must be exercised. `broken` and `unknown` are the entire reason fix #2 exists and must be *reproduced*, not assumed.

- [ ] **Step 6: Push and open the PR**

```bash
git push -u origin feat/configuration-surface
```

PR body must include a Docs Impact section listing `docs/SETUP-YOTO-CONNECTION.md`, `docs/INSTALL-FOR-MOM.md`, `docs/RELEASE_NOTES.md`, and `docs/design-handoffs/README.md`, and must note that the global `:focus-visible` rule intentionally changes the appearance of steps 1–4.

---

## Test Plan

Run from a clean checkout of the branch. Start the app with
`python -m yoto_maker --no-tray --no-browser` and open `http://127.0.0.1:8777/`.

**Where state lives** (needed to set up several scenarios):
- Saved sign-in: `%LOCALAPPDATA%\YotoMaker\yoto_token.json`
- Saved settings: `%LOCALAPPDATA%\YotoMaker\settings.json`

Back both up before you start, and restore them at the end.

### A. The everyday path is not heavier

1. Load `/` with no hash. **Expect:** four numbered steps, exactly as before. No tab strip, no fifth step, no new banner.
2. Scroll to step 3. **Expect:** the Client ID input, its blue explainer box, and the old "⚙️ Use a different Yoto account (advanced)" link are gone. Step 3 is visibly shorter.
3. **Expect** the footer reads `Made with Yoto Maker · v0.1.9 · Settings · About · Start a new card`.

### B. Entry and exit

4. Click the header pill while **connected**. **Expect:** the Settings view replaces the card view. (This click did nothing before.)
5. Click the pill while **not connected**. **Expect:** Settings, not a jump to Yoto's sign-in.
6. Press the browser's Back button. **Expect:** the card view returns, scrolled to the top, and focus is back on the header pill.
7. Click the footer **Settings** link, then `← Back to my card`. **Expect:** the card view, with focus back on the footer link.
8. In Settings, check the browser tab title. **Expect:** `Settings · Yoto Maker`. On the card view: `Yoto Maker`.
9. Load `http://127.0.0.1:8777/#settings` directly and reload the page. **Expect:** Settings both times.
10. Scroll the card view far down (add several tracks first), then open Settings. **Expect:** Settings is scrolled to the top, not mid-page.
11. While not connected, expand step 3 and click `⚙️ Yoto connection settings`. **Expect:** the Settings view.

### C. Keyboard and focus

12. From the card view, press Tab repeatedly. **Expect:** a 3px purple ring on every button, including in steps 1, 2 and 4. This is intended — it is a fix, not a regression.
13. Click a button with the mouse. **Expect:** no ring (`:focus-visible`, not `:focus`).
14. Enter Settings. **Expect:** focus lands on the "Settings" heading; a screen reader announces "Settings, heading level 2".
15. Tab through Settings. **Expect:** `← Back to my card` → account button → Client ID input → Save → (reset button, if present). Nothing in the hidden card view is reachable — Shift+Tab from the back link should leave the page, not enter step 4.
16. Press Ctrl+F and search for text that exists only in step 1. **Expect:** no match while Settings is open.

### D. The account setting — `connected`

Requires a real Yoto sign-in.

17. Open Settings. **Expect:** briefly "Checking your Yoto connection…" with a grey dot and the button disabled, then "Connected and working" / "We just checked with Yoto and everything's fine." with a **green** dot and the button enabled reading `🔗 Sign in to Yoto again`.
18. Click it. **Expect:** the button row is replaced by the warm-beige confirmation. Its body text is dark ink, not brown. Focus is on **Never mind**, and Tab reaches **Yes, sign in again** second.
19. Press Escape. **Expect:** the confirmation closes, the button row returns, focus is back on the primary button.
20. Reopen it and click **Never mind**. **Expect:** identical result.

### E. The account setting — `broken` (must be reproduced, not assumed)

21. Stop the app. Open `yoto_token.json` and set `"refresh_token"` to `"definitely-not-valid"` **and** `"expires_at"` to `1`. Save. Restart the app.
    - Both edits matter: with a live `expires_at`, `check_connection()` returns the cached token without contacting Yoto and you will see `connected`.
22. Open Settings. **Expect:** a **red** dot, "There's a problem with this connection", and "Yoto Maker can't send cards right now. Signing in again usually fixes it." The button reads `🔗 Sign in to Yoto again` and is enabled.
23. **Expect** the header pill still reads "Yoto connected" (it reflects only that a file exists). That is the discrepancy this feature exists to expose, and the Settings page is the one telling the truth.
24. Go back to the card view and press **Send to Yoto** with a track added. **Expect:** it fails — confirming the `broken` reading was correct.

### F. The account setting — `unknown` (must be reproduced, not assumed)

25. With a valid-looking but expired token in place (`expires_at: 1`, a plausible refresh token), disconnect the computer from the internet — turn off Wi-Fi, or block `login.yotoplay.com` in your hosts file with `127.0.0.2 login.yotoplay.com`.
26. Reload and open Settings. **Expect:** a **grey** dot, "We couldn't check right now", and "This computer doesn't seem to be online. Check your internet, then come back."
27. **Expect the button is ENABLED**, not disabled. An offline user may be about to fix her Wi-Fi and must never be dead-ended.
28. **Expect the wording never says the connection is broken.** If it does, `AuthNetworkError` is not being raised or not being caught first — this is the single most important assertion in the test plan.
29. **Expect** the check settles within about 8 seconds, not 30. Time it.
30. Restore the network and reload. **Expect:** the state changes accordingly.

### G. The account setting — `not_connected` and signing in

31. Stop the app, delete `yoto_token.json`, restart, open Settings. **Expect:** a grey dot, "Not connected yet", "Connect your Yoto account to send cards to it.", and the button reads `🔗 Connect my Yoto account` — word-for-word identical to step 3's button.
32. Click it. **Expect: no confirmation** — there is nothing to forget, so it goes straight to Yoto's sign-in in a new tab.
33. **Expect** the Settings tab shows an **amber** dot, "Waiting for you to sign in…", a disabled `Waiting for Yoto…` button, and a `Cancel` button beside it.
34. Complete the sign-in on Yoto. Return to the Settings tab. **Expect** within ~2 seconds: green dot, "Connected and working", and a green message "🎉 You're signed in. Yoto Maker can send cards again."
35. Repeat step 32, then press **Cancel** instead. **Expect:** the section returns to "Not connected yet" and shows "Stopped waiting. You can close the Yoto tab if it's still open."
36. Open DevTools → Network. Repeat step 32, press Cancel, and watch for 30 seconds. **Expect: no further `/api/status` requests.** This is the poller-leak fix.
37. Repeat step 32 from a `connected` state (confirming through the dialog). **Expect:** a `POST /api/yoto/logout` fires before `GET /api/yoto/login` — one button doing both jobs.
38. Block popups for `127.0.0.1` in the browser, then click the button. **Expect:** the section does **not** enter the waiting state; instead a blue message appears with a clickable "Open Yoto's sign-in page ↗" link that actually opens Yoto.
39. Start a sign-in, leave it, and wait three minutes without completing it. **Expect:** the section returns to its previous state and shows the timeout message. Confirm in DevTools that polling has stopped.
40. On the **card view** (step 3, not connected), press `🔗 Connect my Yoto account`, then close the Yoto tab without signing in. Watch Network for 30 seconds. **Expect: polling stops within three minutes and never runs forever** — the same leak, fixed in `connectYoto()` too.

### H. The Client ID setting — `builtin`

41. Ensure `YOTO_CLIENT_ID` is unset and `settings.json` has no `yoto_client_id`. Open Settings. **Expect:** green dot, "Using the built-in Client ID", "This is what most people use. Nothing to do here."
42. **Expect no "Go back to the built-in one" button** — there is nothing to go back from.
43. Click **Save** with the box empty. **Expect:** a red "Please paste a Client ID first.", focus in the input, and **no confirmation dialog** — never confirm a no-op.

### I. The Client ID setting — saving

44. Paste any non-empty string and click **Save**. **Expect:** the confirmation reads "Use this Client ID?" with the two specified paragraphs, buttons **Never mind** / **Yes, use it**, focus on **Never mind**. The input and Save are disabled while it is open.
45. Press Escape. **Expect:** the confirmation closes, input and Save re-enable, the pasted value is still there, focus returns to **Save**.
46. Click **Save** → **Yes, use it**. **Expect:**
    - the input clears;
    - the status becomes "Using your own Client ID" / "Ends in {last 3 characters}. Saved on this computer only.";
    - a **Go back to the built-in one** button appears;
    - a green message "Saved. Now sign in to Yoto again using the button above.";
    - **the account section above has flipped to "Not connected yet"**; and
    - the header pill now reads "Yoto not connected".
47. Confirm `yoto_token.json` is gone from disk. This is fix #1 — without it the pill would still claim "Yoto connected" and every upload would fail.
48. Go back to the card view. **Expect:** step 3 shows the connect row and **Send to Yoto** is disabled.

### J. The Client ID setting — resetting

49. From the saved state, click **Go back to the built-in one**. **Expect:** the confirmation reads "Go back to the built-in Client ID?" with buttons **Never mind** / **Yes, use the built-in one**, focus on **Never mind**.
50. Confirm it. **Expect:** the status returns to "Using the built-in Client ID", the reset button disappears, and a green "Done — back to the built-in Client ID. Now sign in to Yoto again using the button above."
51. Confirm `yoto_client_id` is gone from `settings.json` and `yoto_token.json` is gone from disk.

### K. The Client ID setting — `env` (the honest dead end)

52. Stop the app. Set `$env:YOTO_CLIENT_ID = "some-value"` and restart. Open Settings.
53. **Expect:** an **amber** dot, "Set outside the app", and the sub-line naming `YOTO_CLIENT_ID` and saying "they'll need to change it there."
54. **Expect** the input and **Save** are visibly **disabled** but still present, with "You can still type one here, but it won't be used while the one above is set." below them.
55. **Expect "Go back to the built-in one" is completely absent** — inspect the DOM and confirm `#clientIdActions` is not merely hidden but removed. Deleting the saved value here would fall through to the env var, so the label would be untrue.
56. Set a saved value too (via `settings.json` directly), restart, and reopen Settings. **Expect:** still "Set outside the app" — the env var wins and the screen says so, rather than showing a saved value that is being ignored.

### L. Layout and responsive

57. Resize the window to 400px wide with Settings open. **Expect:** the confirmation's two buttons stack full-width, with **Never mind** above **Yes, …** — the safe option stays first both visually and in tab order. Nothing overflows horizontally.
58. At 600px, **expect** the Client ID input and Save wrap sensibly.
59. Compare the two `.setting` cards against the four `.step` cards. **Expect** the same card background, radius, shadow and padding rhythm — but **no numbered badge** on the settings cards.

### M. The extensibility property (the point of the feature)

60. In DevTools, copy one `<section class="setting">`, change its `id` and its `<h3>`, and paste it after the Client ID section. **Expect** it renders correctly with no CSS edits and no visual change to either existing section. If it does not, the primitive has been compromised and the PR should not merge.

### N. Regression sweep

61. Complete a full card end to end: add a YouTube track, name it, pick an emoticon, adjust the picture, send to Yoto, print a label. **Expect** no regressions.
62. Open the About modal and press Escape. **Expect** it still closes (the Escape handler was rewritten).
63. Click **Start a new card**. **Expect** the confirm dialog and reset still work.
64. Check the browser console across all of the above. **Expect** no errors and no warnings.

---

## Self-Review

**Spec coverage.** `overview.md` §3.3 view structure → Task 7; §4 primitive → Tasks 6-7; §5.1 pill → Task 8; §5.2 footer → Task 7; §5.3 exit → Task 8; §5.4 routing → Task 8; §6.1-6.2 both settings → Tasks 9-10; §6.3 what leaves step 3 → Task 7; §7.1 dead `configured` → Tasks 2 and 8; §7.2 source + mask → Task 2; §7.3 logout on save → Task 5; §7.4 delete + `DELETE` route + hide-on-env → Tasks 1, 5, 10; §7.5 check endpoint → Tasks 3-4; §7.6 poller leak → Task 9; §7.7 account identity → deliberately not planned; §8 docs → Task 11. `interactions.md` §1 view switching → Task 8; §2 account state machine → Task 9; §3 Client ID state machine → Task 10; §4 keyboard → Tasks 6, 8, 9, 10; §5 responsive → Task 6; §6 no motion → nothing added. `tokens.md` §1-3 → Task 6. `copy.md` — every string appears verbatim in Tasks 7, 9, 10, 11, except the two documented as unreachable in "Known copy gaps".

**Placeholder scan.** No `TBD`, no "implement later", no "similar to Task N", no "add error handling" without the handling. Every code step carries literal code.

**Type consistency.** `check_connection(timeout: float = 8.0) -> dict` is defined in Task 3 and consumed unchanged in Task 4. `client_id_source()` / `mask_client_id()` are defined in Task 2 and consumed in Tasks 2 (`connection_status`), 5 (tests) and 10 (frontend, via the `/api/status` payload). `stopSignInPoll()` is called by `closeSettings()` in Task 8 and defined in Task 9 — a forward reference inside function bodies, which is fine for hoisted function declarations and never evaluated before Task 9 lands. `renderClientId()` is called by `openSettings()` (Task 8) and defined in Task 10; Tasks 8 and 9 each note the expected console error in the interim. `closeAccountConfirm(restoreFocus)` and `closeClientIdConfirm(restoreFocus)` share a signature shape and are called consistently.
