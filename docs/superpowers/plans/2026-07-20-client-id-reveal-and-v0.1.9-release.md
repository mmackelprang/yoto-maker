# Client ID Reveal Control + the v0.1.9 Release Cut — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal, Part A:** Show the user the Client ID that is actually in effect — the full mask by default, the whole 32-character string behind a text disclosure toggle, in monospace — for the `saved` and `env` sources only.

**Goal, Part B:** Actually cut v0.1.9. The version was bumped, release notes were written and PR #10 merged, but **no tag was pushed, no `.exe` was built, and no GitHub release exists.** `updater.py` reads GitHub releases, so every user is correctly told there is no update, because there genuinely is nothing to download. This plan ships the reveal control *inside* v0.1.9 and then cuts the release for real.

**Architecture:** Backend first, one field. `connection_status()` gains `client_id_full`, derived from a single traversal of the precedence chain so the value and its source label cannot disagree. Then CSS (one new utility), then markup (one nested block inside the existing body slot), then the render rules, then the toggle and its persistence flag. The release cut is last, after the feature merges, because the feature ships in it.

**Tech Stack:** Python 3.11+, FastAPI, pytest + `fastapi.testclient`; vanilla HTML/CSS/JS (no build step, no framework, no dependencies). PyInstaller + `gh` for the release.

**Design handoff (authoritative):** `docs/design-handoffs/configuration-surface/` **as amended in commit `884fa6a`** — `overview.md` §4.1, §4.3.3, §6.2, §7.8, §11; `interactions.md` §3.4, §3.5, §4, §4.1, §4.3, §5; `copy.md` §4 table, §4a, input label; `tokens.md` §3a, §4, §5.

**Relationship to the handoff:** **extends.** Deviates from nothing. Three points where the handoff's prose and its own markup/render-rule tables disagree are resolved below and flagged, not invented around.

**Prior plan:** `docs/superpowers/plans/2026-07-20-configuration-surface.md`. Conventions, the corrected Test Plan and the stale-cache UAT hazard all carry forward unchanged.

---

## Global Constraints

- **One PR for Part A.** Branch `feat/client-id-reveal`, merged via PR per the user's global convention. Builder owns branch + PR. Part B (Tasks 8–10) runs on `main` *after* that PR merges.
- **The `.setting` primitive is extended, never widened.** Seven slots, same order, same classes. **Zero changes to the `.setting*` block in `styles.css`.** Zero id selectors, zero positional selectors — the property that was verified adversarially at PR #10's merge gate. The only new CSS in this plan is `.mono-value`, a standalone utility that touches nothing in the `.setting*` block. **If any step here appears to require widening the primitive, stop and say so rather than degrading it quietly.**
- **Copy is verbatim from `copy.md` §4 and §4a.** Do not paraphrase, shorten, re-tone or "improve" any user-visible string.
- **Typographic apostrophes (`’`, U+2019), not `'`,** in every user-visible string, including inside JS string constants. `The one you’re using now` has one.
- **Banned vocabulary** (`docs/design-handoffs/README.md`): OAuth, token, authenticate, credentials, revoke, endpoint, API, session, cache, config, JSON, refresh token, PKCE. "Client ID" is the single permitted technical term.
- **No eye icon. No `Reveal`. No `Hide`.** `copy.md` §4a enumerates the rejected strings and why. An icon is a string; 👁 is the password-field convention and states "this value is secret", which is false for a PKCE public client ID. The chosen pair says *shortened*, not *hidden*.
- **`client_id_full` is not a secret and must not be treated as one.** `overview.md` §7.8 pre-empts the "but it rides on a 2s poll" objection explicitly: **do not add redaction, special logging handling, or a "sensitive field" wrapper.** Doing so would contradict the framing the whole amendment rests on.
- **No reveal endpoint.** The app binds `127.0.0.1` with no authentication of any kind (`config.py:111`), so a second endpoint would gate the value against nobody, and a fetch would give the toggle a failure mode it otherwise cannot have. One field on `/api/status`, one function.
- **No auto-hide, no timer.** Reset on exactly three events (Task 5). An auto-hide would flip `aria-expanded` with no user action — an unannounced state change — and would break the one task the feature exists for.
- **No live region on `#clientIdValue`.** `#clientIdStatus` in this section already carries `role="status"`, and `interactions.md` §4.3 prohibits a second one in the same section.
- **`aria-expanded`, never `aria-pressed`.** Disclosure pattern, not toggle-button.
- **No copy button, no `user-select: none`, no chunking of the value.** All three rejected in `tokens.md` §3a with reasons; a selection must yield the exact 32 characters.
- **Out of scope, do not implement:** a copy-to-clipboard control; showing the value for `builtin`; any change to `mask_client_id()`, `POST`/`DELETE /api/yoto/client-id`, or the `.setting` CSS; queue items 2–6.
- **Tests:** `pytest -q` from the repo root. `tests/conftest.py` sets `YOTO_CLIENT_ID=test_client_id` **autouse** — any test exercising `saved` or `builtin` precedence MUST call `monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)` first or it silently tests the `env` branch.
- **Known-red baseline:** `tests/test_sources.py::test_youtube_sponsorblock_best_effort_retry` fails wherever the optional `yt_dlp` dep is absent (queue item 3). Current suite: **100 passed, 1 failed**, and that one failure is environmental and pre-existing. Do not fix it here; do not let it mask a new failure.

---

## Where the design and the code still disagree

Five discrepancies between the amended handoff and the shipped code. Each is resolved by a task below; collected here so Builder and the reviewer know they were deliberate, not drift. Numbers 1 and 2 are the ones that would produce a real defect if the handoff were followed literally.

1. **`interactions.md` §3.5.4 says the reset is "tracked in a module-level `clientIdRevealed` flag that `renderClientId()` honors" — but it does not say where the flag is *set*, and the only obvious place is wrong.** `renderClientId` **is** the section's `onOpen` handler (`app.js:1066`), so reset event #1 ("entering the settings view") looks like it belongs inside `renderClientId()`. It does not: `closeClientIdConfirm()` also calls `renderClientId()` (`app.js:565`), so a reset placed inside the function would collapse the reveal on confirmation-cancel — **precisely the behavior §3.5.4 exists to prevent.** The reset must be hoisted into the `onOpen` arrow wrapper. Task 5.
2. **Reset event #2 ("a successful save or reset") has no correct hook where the handoff implies one, and the obvious hook is shared with the failure path.** `submitClientId()` calls `closeClientIdConfirm(false)` on **both** the success path (`app.js:594-596`) and the error path (`app.js:588`). Putting the reset in `closeClientIdConfirm()` would collapse the reveal after a *failed* save, which changed nothing. The reset goes in `submitClientId()` between the successful call and `refreshStatus()`. Task 5.
3. **`overview.md` §7.8 claims all three fields "come from `_resolve_client_id_with_source()` … so adding this cannot introduce drift." That guarantee is not currently structural.** `connection_status()` (`auth.py:194-195`) calls `resolve_client_id()` **and** `client_id_source()` — two independent traversals, each re-reading the env var and re-opening `settings.json`. Adding `client_id_full` as a third independent call would make it three, and two traversals straddling a settings write would report a value under the wrong source label. Task 1 collapses them to one call via a new public `resolve_client_id_with_source()`, which makes §7.8's claim true rather than incidental.
4. **`copy.md` requires a state-dependent input label; `interactions.md` §3.5.2's render-rules table — the authoritative "renderClientId() decides all of this" table — omits it entirely.** `copy.md` says the label becomes `Paste a different Client ID` for `saved` and stays `Paste a Client ID` for `builtin`/`env`. A Builder working from `interactions.md` alone ships that string never. Compounding it, `index.html:252`'s `<label>` has a `for` attribute but **no `id`**, so there is no handle to update. Task 3 adds the id; Task 4 sets the text.
5. **`interactions.md` §3.5.1's markup snippet renders the toggle unconditionally visible, but §3.5.2's render rules require it be *omitted* in two cases.** The snippet is the default-visible form. Task 3 ships the button with `hidden` in the initial markup and lets `renderClientId()` show it, which satisfies both. A deliberate, minimal deviation from the literal snippet.

### Minor, recorded but not fixed here

- **`interactions.md` §4.1's amended tab-order diagram lists `input → Save` unconditionally**, but both are `disabled` in the `env` state and therefore not focusable. The diagram annotates the toggle `(saved / env only)` and reset `(saved only)` but leaves those two unannotated. Documentation imprecision only; the code is correct. Do not "fix" the code to match the diagram.
- **`interactions.md` §3.5.2's last line — "If `client_id_masked` is also missing, hide the block entirely" — is defensive-only.** `resolve_client_id()` always falls back to a non-empty constant, so `client_id_masked` cannot be empty in practice. Implement the guard anyway (it is one `&&`), but a reviewer should not go looking for the state that triggers it.
- **`overview.md` §11's header still reads "Status: proposed, awaiting Mark's approval."** The decisions were approved. Task 7 flips it.
- **`docs/DEVELOPERS.md` says "The suite (48 tests)".** It has been 100+ since PR #10. Task 7 corrects it.

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `yoto_maker/config.py` | Modify | Add public `resolve_client_id_with_source()`. No change to the chain itself, `resolve_client_id()`, `client_id_source()` or `mask_client_id()`. |
| `yoto_maker/yoto/auth.py` | Modify | `connection_status()` → one chain traversal; add `client_id_full`, `null` for `builtin`. |
| `yoto_maker/server/static/styles.css` | Modify | Add `.mono-value`. **Nothing in the `.setting*` block.** |
| `yoto_maker/server/static/index.html` | Modify | `#clientIdCurrent` block nested inside `#clientIdBody`; `id` on the input label. Nothing outside `#clientIdBody`. |
| `yoto_maker/server/static/app.js` | Modify | `CLIENT_ID_STATUS.saved.sub`; rewrite `renderClientId()`; add `clientIdRevealed` + toggle + three resets; wire the listener. |
| `tests/test_models_and_settings.py` | Modify | `resolve_client_id_with_source()`; `connection_status()`'s new field across all three sources. |
| `tests/test_api.py` | Modify | `/api/status` `client_id_full`: `null` on `builtin`, populated on `saved` and `env`. |
| `docs/RELEASE_NOTES.md` | Modify | Add the reveal control to the existing v0.1.9 section. |
| `docs/design-handoffs/configuration-surface/overview.md` | Modify | §11 status → approved. One line. |
| `docs/DEVELOPERS.md` | Modify | Correct the test count; make the release checklist explicit (Task 10). |
| `docs/BUILDER_QUEUE.md` | Modify | Split merged from released in the status key (Task 10). |

`app.js` is 1104 lines and grows by roughly 45. It stays one file, for the reasons recorded in the prior plan.

---

# Part A — the reveal control

## Task 1: `client_id_full` on `/api/status`

**Files:**
- Modify: `yoto_maker/config.py` (after `client_id_source()`, ~line 78)
- Modify: `yoto_maker/yoto/auth.py:187-204`
- Modify: `tests/test_models_and_settings.py`
- Modify: `tests/test_api.py`

### Step 1.1 — a public form of the precedence chain

- [ ] In `yoto_maker/config.py`, immediately after `client_id_source()`, add:

```python
def resolve_client_id_with_source() -> tuple[str, str]:
    """The chain's public form: ``(client_id, source)`` from one traversal.

    Any caller that needs both MUST use this rather than calling
    resolve_client_id() and client_id_source() in sequence. Two traversals read
    the env var and settings.json independently, so a settings write landing
    between them would report a value under the wrong source label — and the
    settings screen decides what to show, and what to hide, from that label.
    """
    return _resolve_client_id_with_source()
```

Nothing else in `config.py` changes. `resolve_client_id()` and `client_id_source()` keep their signatures and their callers.

### Step 1.2 — `connection_status()` reports the full value

- [ ] In `yoto_maker/yoto/auth.py`, replace the body of `connection_status()` (currently `auth.py:194-204`) with:

```python
def connection_status() -> dict:
    """A UI-friendly summary: connected? which Client ID is in effect?

    ``connected`` here means only "a saved sign-in exists on this computer" — it
    is cheap and does not touch the network. For "does it actually still work",
    which is what the settings screen shows, use check_connection().
    """
    # One traversal, destructured: the value and the label the UI reports it
    # under are read from the same chain walk and so cannot disagree.
    cid, source = config_mod.resolve_client_id_with_source()
    return {
        # Legacy: resolve_client_id() falls back to a non-empty constant, so this
        # is permanently True and carries no information. Kept so nothing that
        # reads it breaks; no new UI may depend on it.
        "configured": bool(cid),
        "connected": _load_tokens() is not None,
        "client_id_source": source,
        "client_id_masked": config_mod.mask_client_id(cid),
        # The whole value, for the "Show the whole thing" disclosure in Settings.
        #
        # None for "builtin": the UI renders no value in that state (overview.md
        # §11.4) because there is no dashboard entry to compare it against, and
        # sending a field the UI is specified never to display would invite a
        # future contributor to display it — quietly undoing that decision. The
        # None carries the rule at the layer that owns the precedence chain.
        #
        # NOT a disclosure concern, and must not be treated as one: this is a
        # PKCE *public* client ID (see config.DEFAULT_YOTO_CLIENT_ID), sent in
        # plaintext in every sign-in URL and shipped inside the .exe, served here
        # over loopback to the same user's own browser. Do not add redaction,
        # special logging handling, or a "sensitive field" wrapper. See
        # overview.md §7.8.
        "client_id_full": None if source == "builtin" else cid,
    }
```

No new import — `config_mod` is already imported in this module.

### Step 1.3 — unit tests for the chain

- [ ] In `tests/test_models_and_settings.py`, after `test_mask_client_id`, add:

```python
def test_resolve_client_id_with_source_matches_the_two_single_getters(temp_config, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    from yoto_maker import config as cfg

    assert cfg.resolve_client_id_with_source() == (
        cfg.resolve_client_id(),
        cfg.client_id_source(),
    )

    monkeypatch.setenv("YOTO_CLIENT_ID", "fromTheEnvironment0000000000000x")
    assert cfg.resolve_client_id_with_source() == ("fromTheEnvironment0000000000000x", "env")
```

- [ ] In the same file, after `test_connection_status_reports_the_builtin_source` (the test asserting `client_id_masked` at line ~132), add:

```python
def test_connection_status_hides_the_full_client_id_for_builtin(temp_config, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    from yoto_maker.yoto import auth

    st = auth.connection_status()
    assert st["client_id_source"] == "builtin"
    # Deliberately null, not the constant: the UI renders no value in this state
    # and must not be handed one it is specified never to display.
    assert st["client_id_full"] is None


def test_connection_status_reports_the_full_client_id_for_env(temp_config, monkeypatch):
    monkeypatch.setenv("YOTO_CLIENT_ID", "envSetByS0meoneElse00000000000x1")
    from yoto_maker.yoto import auth

    st = auth.connection_status()
    assert st["client_id_source"] == "env"
    assert st["client_id_full"] == "envSetByS0meoneElse00000000000x1"
    assert st["client_id_masked"] == "envS…0x1"
```

### Step 1.4 — API tests for all three sources

- [ ] In `tests/test_api.py`, replace `test_status_reports_client_id_source_and_mask` (line 230) with it plus three siblings:

```python
def test_status_reports_client_id_source_and_mask(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "builtin"
    assert "…" in body["yoto"]["client_id_masked"]


def test_status_omits_the_full_client_id_when_builtin(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "builtin"
    assert body["yoto"]["client_id_full"] is None


def test_status_reports_the_full_client_id_when_saved(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"})
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "saved"
    assert body["yoto"]["client_id_full"] == "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"
    assert body["yoto"]["client_id_masked"] == "a8OG…oU1"


def test_status_reports_the_full_client_id_when_set_by_env(client, monkeypatch):
    monkeypatch.setenv("YOTO_CLIENT_ID", "envSetByS0meoneElse00000000000x1")
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "env"
    # env is the one state where the value is not discoverable anywhere else, so
    # it is the state the disclosure matters most in (overview.md §11.4).
    assert body["yoto"]["client_id_full"] == "envSetByS0meoneElse00000000000x1"


def test_status_full_equals_masked_for_a_short_saved_value(client, monkeypatch):
    """The frontend omits the toggle by comparing these two, never by re-implementing
    mask_client_id()'s length rule. This test pins the case that comparison exists for."""
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "mine"})
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_masked"] == body["yoto"]["client_id_full"] == "mine"
```

### Step 1.5 — verify

- [ ] `pytest -q tests/test_api.py tests/test_models_and_settings.py` — all green.
- [ ] `pytest -q` — 100 passed baseline plus the new tests; the only failure is the known `yt_dlp` one.

---

## Task 2: CSS — the `.mono-value` utility

**Files:**
- Modify: `yoto_maker/server/static/styles.css`

The highest-value line in the amendment. The built-in ID is `a8OGO6EfbWit5tDUUrOz0g49s49NQoU1` — four capital `O`, two `0`, one lowercase `o`. In `"Segoe UI"` at 14px, `O`/`0` are near-identical and `l`/`I`/`1` collapse, so the one comparison this feature exists to support fails **silently and confidently**. Do not drop this task, and do not merge it into the `.setting*` block.

### Step 2.1

- [ ] Append to `styles.css`, in the utilities region near `.tiny` (line ~240) and **outside** the `.setting*` block:

```css
/* A machine-generated value displayed for a human to compare against another
   screen, character by character. Segoe UI makes O/0 and l/I/1 ambiguous, which
   turns a failed comparison into a confident wrong answer — the worst available
   failure mode for this control. Standalone utility: it adds no rule to, and
   edits no rule in, the .setting* block. */
.mono-value {
  font-family: Consolas, "Cascadia Mono", "SF Mono", Menlo, monospace;
  font-size: 14px;
  letter-spacing: 0.02em;
  color: var(--ink);
  /* 32 characters must wrap inside the column, never push the card wide. NOT
     space-separated chunking (a8OG O6Ef …): the spaces would be copied, and
     "I copied it exactly and it didn't work" costs far more than the scanning
     help is worth. word-break inserts nothing. */
  word-break: break-all;
  /* .row is display:flex with no align-items, so this would default to stretch
     and top-align against the vertically-centred .btn.small beside it.
     Inert outside a flex row. */
  align-self: center;
}
```

- [ ] Do **not** add `user-select: none`. Do not add a copy button.
- [ ] Named `-value`, not `.mono`: a bare `.mono` reads as a pure font utility and the next person would inherit `align-self` and `break-all` by surprise.

### Step 2.2 — verify

- [ ] `git diff yoto_maker/server/static/styles.css` shows **only** the added block. No line inside `.setting`, `.setting-desc`, `.setting-status`, `.setting-body`, `.setting-actions` or `.setting-confirm` is touched.
- [ ] `grep -n '#[a-zA-Z]' yoto_maker/server/static/styles.css | grep -i setting` returns nothing — no id selector has entered the primitive.

---

## Task 3: Markup — the value block

**Files:**
- Modify: `yoto_maker/server/static/index.html:251-260`

Nested inside the existing `#clientIdBody`, above the input label. **Nothing outside `#clientIdBody` changes** — not the status paragraph, not `#clientIdActions`, not the confirmation.

### Step 3.1

- [ ] Replace `index.html:251-254`:

```html
        <div class="setting-body" id="clientIdBody">
          <label class="tiny" for="clientIdInput">Paste a Client ID</label>
          <div class="row wrap" style="margin-top:6px">
            <input id="clientIdInput" type="text" class="grow" placeholder="Paste your Yoto Client ID here" />
```

with:

```html
        <div class="setting-body" id="clientIdBody">
          <!-- The value in effect. Shown for `saved` and `env` only; `builtin`
               renders nothing here (overview.md §11.4). Two structurally
               parallel .row.wrap + .grow rows — this one and the input row
               below — which interactions.md §5 already certifies as collapsing
               correctly at narrow widths. -->
          <div id="clientIdCurrent" class="hidden" style="margin-bottom:14px">
            <p class="tiny">The one you’re using now</p>
            <div class="row wrap" style="margin-top:6px">
              <span class="mono-value grow" id="clientIdValue"></span>
              <!-- Disclosure, not a password reveal: aria-expanded + aria-controls,
                   never aria-pressed. Starts hidden because renderClientId()
                   omits it whenever it could do nothing. -->
              <button class="btn small hidden" id="clientIdReveal"
                      aria-expanded="false" aria-controls="clientIdValue">Show the whole thing</button>
            </div>
          </div>
          <label class="tiny" for="clientIdInput" id="clientIdInputLabel">Paste a Client ID</label>
          <div class="row wrap" style="margin-top:6px">
            <input id="clientIdInput" type="text" class="grow" placeholder="Paste your Yoto Client ID here" />
```

Notes for the reviewer:
- Inline `margin-bottom` / `margin-top` match the file's existing convention (`index.html:253`, `:257`) rather than introducing a class for one gap.
- `id="clientIdInputLabel"` is new and load-bearing: `copy.md` requires this label to change with state and the element had no handle. See disagreement #4.
- The button ships with `hidden`, a deliberate minimal deviation from `interactions.md` §3.5.1's snippet, which shows the default-visible form while §3.5.2 requires the toggle be omitted in two cases. See disagreement #5.
- `.btn.small` on `--card` is **row 1** of `tokens.md` §4 — ring resolves to `--accent`, 4.82:1. **No new contrast row, no `--focus-ring` override.** It never renders inside `.setting-confirm`, so it never lands on `--warn-soft`.

### Step 3.2 — verify

- [ ] The new block is inside `#clientIdBody` and above the `<label>`.
- [ ] `#clientIdReveal` is a native `<button>` — no `tabindex` anywhere in the block, no `role`, no `aria-label`, no `title`.

---

## Task 4: `renderClientId()` — the render rules

**Files:**
- Modify: `yoto_maker/server/static/app.js:449-452` (`CLIENT_ID_STATUS.saved`)
- Modify: `yoto_maker/server/static/app.js:492-532` (`renderClientId`)

### Step 4.1 — the status sub-line stops carrying the value

- [ ] Replace `app.js:449-452`:

```js
  saved: {
    cls: "is-ok", head: "Using your own Client ID",
    sub: "",   // built from the masked value below
  },
```

with:

```js
  saved: {
    cls: "is-ok", head: "Using your own Client ID",
    // Was "Ends in {last3}. Saved on this computer only." The value fragment
    // moved to the body (copy.md §4a), where the whole mask is shown instead of
    // three characters — the sentence is not losing information, it is losing a
    // worse copy of it. It also retires a mild breach of the primitive's rule
    // §4.3.2 (never surface a raw stored value in the status slot).
    sub: "Saved on this computer only.",
  },
```

### Step 4.2 — rewrite `renderClientId()`

- [ ] Replace the whole of `renderClientId()` (`app.js:492-532`) with:

```js
function renderClientId() {
  const y = (STATUS && STATUS.yoto) || {};
  const source = y.client_id_source || "builtin";
  const masked = y.client_id_masked || "";
  const full = y.client_id_full || "";
  const s = CLIENT_ID_STATUS[source] || CLIENT_ID_STATUS.builtin;

  $("#clientIdStatus").className = "setting-status " + s.cls;
  $("#clientIdStatusHead").textContent = s.head;
  $("#clientIdStatusSub").textContent = s.sub;

  // ---- the value in effect (interactions.md §3.5.2) ----
  // Row order is load-bearing. `builtin` is tested FIRST because client_id_full
  // is deliberately null in exactly that state — testing for the null first
  // would misread a designed absence as version skew.
  //
  // builtin renders no value at all: the built-in ID is the app author's
  // registration, so there is no dashboard entry to compare it against and the
  // comparison task simply does not exist here. Rendering 32 characters under
  // "This is what most people use. Nothing to do here." would contradict that
  // sentence for every user who ever opens this screen, to serve no task.
  const showValue = source !== "builtin" && !!masked;
  show($("#clientIdCurrent"), showValue);
  if (showValue) {
    // The toggle is OMITTED, not disabled, whenever it could do nothing:
    //   - no client_id_full  → a frontend newer than its server. Degrade to the
    //                          mask alone rather than render a control that
    //                          cannot act.
    //   - masked === full    → mask_client_id() returns values of 8 characters
    //                          or fewer unchanged (config.py:88-89), so the
    //                          whole thing is already on screen and offering to
    //                          show it is a lie. Compare the two strings;
    //                          NEVER re-implement the server's length rule.
    const canReveal = !!full && full !== masked;
    const revealed = canReveal && clientIdRevealed;
    $("#clientIdValue").textContent = revealed ? full : masked;
    setClientIdRevealLabel(revealed);
    show($("#clientIdReveal"), canReveal);
  }

  // With the current value displayed directly above it, the `saved` state stacks
  // two Client-ID-shaped things and "Paste a Client ID" no longer distinguishes
  // the one you have from the one you would replace it with (copy.md, input
  // label). builtin and env are unchanged — in neither is there a saved value of
  // hers to differ from.
  $("#clientIdInputLabel").textContent =
    source === "saved" ? "Paste a different Client ID" : "Paste a Client ID";

  const isEnv = source === "env";
  // Disabled and explained, not hidden. Hiding the input would make the section
  // look broken to the person who came here specifically to change this.
  //
  // The value block above is deliberately EXEMPT from this disabling
  // (interactions.md §3.4 as amended). It is read-only — there is nothing to
  // disable — and env is the one state where the value is not discoverable
  // anywhere else, so it is the state the display matters most in.
  const input = $("#clientIdInput");
  input.disabled = isEnv;
  $("#clientIdSave").disabled = isEnv;
  show($("#clientIdEnvNote"), isEnv);
  // Tie the note to the field it explains, so a screen-reader user hears *why*
  // the field is disabled instead of just finding it dead. Set only while the
  // note is visible — a description pointing at a display:none element is
  // dropped from the accessibility tree anyway.
  if (isEnv) input.setAttribute("aria-describedby", "clientIdEnvNote");
  else input.removeAttribute("aria-describedby");

  const actions = $("#clientIdActions");
  if (actions) {
    // Absent, not merely hidden, when an env var is in effect: deleting the
    // saved value would fall through to the env var rather than the built-in
    // one, so "Go back to the built-in one" would be a lie.
    if (isEnv) actions.remove();
    else show(actions, source === "saved");
  }
}
```

The `last3` slicing and its empty-string fallback are deleted outright. Nothing falls back from them any more.

### Step 4.3 — verify

- [ ] `grep -n 'last3\|slice(-3)' yoto_maker/server/static/app.js` returns nothing.
- [ ] `grep -n 'Ends in' yoto_maker/server/static/app.js` returns nothing.
- [ ] The env `.tiny` note string is unchanged — *"…it won't be used while the one above is set."* With the value block inserted above the input, "the one above" now has a literal on-screen referent and reads more concretely. Still true, still verbatim.

---

## Task 5: The toggle, and the three resets

**Files:**
- Modify: `yoto_maker/server/static/app.js` — new functions before `renderClientId()`; `submitClientId()`; the `registerSetting` call at line ~1065.

### Step 5.1 — the flag and the two helpers

- [ ] Insert immediately **before** `function renderClientId()`:

```js
// Whether the full value is currently on screen. Module-level, and deliberately
// NOT reset inside renderClientId(): that function also runs from
// closeClientIdConfirm() (below), which fires when a user CANCELS a confirmation
// — an event she did not aim at this control. Without the flag, cancelling a
// confirmation would silently collapse a reveal she had opened, for no reason
// she caused. That is the single defect this flag exists to prevent.
//
// Reset on exactly three events, each set at its own site:
//   1. entering the settings view      → the onOpen wrapper in init()
//   2. a successful save or reset      → submitClientId(), success path only
//   3. source becoming "builtin"       → subsumed by 2; the block is removed
//
// There is NO timer. An auto-hide would defend against a bystander reading a
// value that is printed in the user's own sign-in URL and on a public dashboard,
// while breaking the one task the feature serves — she is mid-comparison against
// another screen, or reading it aloud over the phone. It would also flip
// aria-expanded with no user action, an unannounced state change a screen-reader
// user has no way to anticipate: a real defect traded for theatre.
let clientIdRevealed = false;

// The label names the ACTION, aria-expanded names the STATE. Together they read
// "Show the short version, button, expanded" — coherent, not contradictory. A
// constant label while the whole thing is already displayed would be plainly
// confusing to the sighted majority. aria-pressed is wrong here: it would
// announce "pressed", which describes a control switched on and says nothing
// about whether the text beside it is long or short.
function setClientIdRevealLabel(revealed) {
  const btn = $("#clientIdReveal");
  btn.textContent = revealed ? "Show the short version" : "Show the whole thing";
  btn.setAttribute("aria-expanded", revealed ? "true" : "false");
}

// Synchronous. Both strings are already in STATUS, so this makes no network
// request and has no failure mode — no spinner, no error string, no decision
// about what the toggle shows when a request times out (overview.md §7.8).
function toggleClientIdReveal() {
  clientIdRevealed = !clientIdRevealed;
  const y = (STATUS && STATUS.yoto) || {};
  $("#clientIdValue").textContent =
    clientIdRevealed ? (y.client_id_full || "") : (y.client_id_masked || "");
  setClientIdRevealLabel(clientIdRevealed);
  // Focus deliberately stays on the button: the content it controls is adjacent
  // and the button is also the way back. No focus management, nothing to get
  // wrong — a direct benefit of choosing a disclosure over a modal-ish reveal.
  //
  // And no live region on #clientIdValue: #clientIdStatus in this section
  // already carries role="status", and a second live region in one section is
  // exactly the double-announcement hazard interactions.md §4.3 prohibits. A
  // user who wants the value reads it with the virtual cursor, where she can
  // also arrow through it character by character — which is what transcription
  // needs, and what one utterance of 32 random characters would not give her.
}
```

### Step 5.2 — reset #2, in the success path only

- [ ] In `submitClientId()`, replace `app.js:592-594`:

```js
  $("#clientIdInput").value = "";
  await refreshStatus();
  closeClientIdConfirm(false);
```

with:

```js
  $("#clientIdInput").value = "";
  // Resets #2 and #3. The value just changed, so continuing to display the
  // previous revealed string would be actively wrong; and if the source became
  // "builtin" the block is removed entirely. Set BEFORE refreshStatus(), because
  // closeClientIdConfirm() below re-renders.
  //
  // Deliberately NOT inside closeClientIdConfirm(): the failure path above calls
  // it too, and a save that failed changed nothing to collapse the reveal for.
  clientIdRevealed = false;
  await refreshStatus();
  closeClientIdConfirm(false);
```

- [ ] Leave the error path (`app.js:586-590`) untouched. It calls `closeClientIdConfirm(false)` and must not reset the flag.

### Step 5.3 — reset #1 and the listener

- [ ] Replace the Client ID `registerSetting` block (`app.js:1063-1070`):

```js
  $("#clientIdReset").addEventListener("click", () => openClientIdConfirm("reset"));
  $("#clientIdConfirmNo").addEventListener("click", () => closeClientIdConfirm());
  $("#clientIdConfirmYes").addEventListener("click", () =>
    submitClientId($("#clientIdConfirm").dataset.kind));
  registerSetting({
    onOpen: renderClientId,
    onClose: () => clearError($("#clientIdMsg")),
    confirm: $("#clientIdConfirm"),
    closeConfirm: closeClientIdConfirm,
  });
```

with:

```js
  $("#clientIdReset").addEventListener("click", () => openClientIdConfirm("reset"));
  $("#clientIdReveal").addEventListener("click", toggleClientIdReveal);
  $("#clientIdConfirmNo").addEventListener("click", () => closeClientIdConfirm());
  $("#clientIdConfirmYes").addEventListener("click", () =>
    submitClientId($("#clientIdConfirm").dataset.kind));
  registerSetting({
    // Reset #1: a fresh view starts in its default state, consistent with the
    // existing scrollTo(0,0) and account re-check. It lives HERE and not inside
    // renderClientId(), which also runs on confirmation-cancel — see the comment
    // on clientIdRevealed.
    onOpen: () => { clientIdRevealed = false; renderClientId(); },
    onClose: () => clearError($("#clientIdMsg")),
    confirm: $("#clientIdConfirm"),
    closeConfirm: closeClientIdConfirm,
  });
```

### Step 5.4 — confirm nothing disables the toggle

- [ ] Read `openClientIdConfirm()` (`app.js:534-556`). It hides `#clientIdActions` and disables `#clientIdInput` and `#clientIdSave`. **It must not gain a line disabling `#clientIdReveal`.** The toggle commits nothing, so the one-live-choice-set rule does not reach it (`overview.md` §4.3.3 as amended). A user reading *"Yoto Maker will start using the Client ID you pasted"* has an obvious next question — *"what is it using now?"* — and this is the control that answers it. This is deliberate behavior, not an oversight to tidy up.
- [ ] Confirm Escape is untouched. Its one binding on this surface is dismissing a confirmation; it must not also collapse the reveal.

### Step 5.5 — verify

- [ ] `grep -n 'clientIdRevealed' yoto_maker/server/static/app.js` returns exactly four sites: the declaration, the `onOpen` wrapper, `submitClientId`'s success path, and the two reads inside `renderClientId`/`toggleClientIdReveal`.
- [ ] `grep -n 'setTimeout\|setInterval' yoto_maker/server/static/app.js` shows no new timer near the Client ID section.
- [ ] `grep -n 'aria-pressed\|aria-live' yoto_maker/server/static/app.js yoto_maker/server/static/index.html` returns nothing new.

---

## Task 6: Documentation for the feature

**Files:**
- Modify: `docs/RELEASE_NOTES.md`

### Step 6.1

- [ ] Add to the existing `### 🆕 New in v0.1.9` list in `docs/RELEASE_NOTES.md`, after the Settings-page bullet:

```markdown
- **See the Client ID you're actually using.** If you or someone else set up your
  own Client ID, Settings now shows it — the short form (`a8OG…oU1`) at a glance,
  and **Show the whole thing** when you need to read every character. It's shown
  in a typewriter font so `O` and `0` can't be confused when you're checking it
  against the Yoto website.
```

Register check: no banned vocabulary, no implication the value is secret, and it reads for someone comparing two screens. "Client ID" is the one permitted technical term.

### Step 6.2

- [ ] Do **not** bump `pyproject.toml` or `yoto_maker/__init__.py`. Both already read `0.1.9` and v0.1.9 was never released — the reveal control ships inside it. Task 8 verifies this rather than changing it.

---

## Task 7: Housekeeping in the docs that are now wrong

**Files:**
- Modify: `docs/design-handoffs/configuration-surface/overview.md` (§11 header, ~line 694)
- Modify: `docs/DEVELOPERS.md` (test count, ~line 62)

### Step 7.1

- [ ] In `overview.md` §11, replace:

```markdown
**Status:** proposed, awaiting Mark's approval. Amends §4.1, §4.3.3, §6.2, adds
```

with:

```markdown
**Status:** approved 2026-07-20; implemented in the reveal-control PR. Amends §4.1, §4.3.3, §6.2, adds
```

### Step 7.2

- [ ] In `docs/DEVELOPERS.md`, replace `The suite (48 tests) mocks all Yoto network calls` with `The suite mocks all Yoto network calls`. Dropping the number rather than updating it — it has been wrong once already and carries no information a `pytest -q` run doesn't.

---

# Part B — the v0.1.9 release cut

> **Runs on `main`, after Part A's PR merges.** The reveal control ships *in* v0.1.9, so the tag must sit on a commit that contains it. Following the process v0.1.5–v0.1.8 used, verified from those tags: the tag goes on the **merge commit of the feature PR**, and the release is created with `gh release create` against `docs/RELEASE_NOTES.md`.

## Task 8: Pre-release verification

**Files:** none modified. This task is a gate.

### Step 8.1 — the version is already correct

- [ ] `grep -n '^version' pyproject.toml` → `version = "0.1.9"`
- [ ] `grep -n '__version__' yoto_maker/__init__.py` → `__version__ = "0.1.9"`
- [ ] `git tag -l 'v0.1.9'` → **empty**. If it is not empty, stop: something already tagged and this plan's premise is wrong.
- [ ] `gh release view v0.1.9` → **not found**. Same stop condition.
- [ ] `gh release list --limit 1` → `v0.1.8` is still Latest.

### Step 8.2 — the tree is releasable

- [ ] On `main`, up to date with `origin/main`, clean working tree.
- [ ] `git log --oneline -3` shows Part A's merge commit at the tip.
- [ ] `pytest -q` — green except the known environmental `yt_dlp` failure (queue item 3).
- [ ] `docs/RELEASE_NOTES.md` opens with `# Yoto Maker v0.1.9` and its v0.1.9 section covers **both** the configuration surface (already written) and the reveal control (Task 6). This whole file is the release body — it already carries the Install / What it does / Notes footer that v0.1.8's body shows, so it is passed to `gh` unedited.

### Step 8.3 — record the merge commit

- [ ] `git rev-parse HEAD` — this is the commit the tag goes on. Note it; Task 9 uses it.

---

## Task 9: Build the `.exe`

**Files:** none tracked. Build output is gitignored (`packaging/dist/`, `**/vendor/`).

### Step 9.1 — stage the bundled binaries

`packaging/vendor/` does not exist in a fresh checkout — it is gitignored because the binaries are large. Both are required: `ffprobe.exe` is what SponsorBlock needs, and shipping without it is exactly the v0.1.3 regression.

- [ ] Create `packaging/vendor/` and copy in a recent static build of **both**:
  - `packaging/vendor/ffmpeg.exe`
  - `packaging/vendor/ffprobe.exe`
- [ ] Verify both exist and are non-trivial in size before building.

### Step 9.2 — build

- [ ] `pip install pyinstaller`
- [ ] `python packaging/make_icon.py`
- [ ] `pyinstaller packaging/YotoMaker.spec --distpath packaging/dist --workpath packaging/build --noconfirm`

### Step 9.3 — verify the artifact before it is published

- [ ] `packaging/dist/YotoMaker.exe` exists. **The filename must be exactly `YotoMaker.exe`** — `docs/INSTALL-FOR-MOM.md` and the release body both name it, and `updater.py` downloads the first asset ending in `.exe`.
- [ ] Its size is in the same order as v0.1.8's published asset (109,220,666 bytes). A build an order of magnitude smaller means the vendored binaries or `yt_dlp` did not get bundled.
- [ ] Launch it once on a Windows machine. It opens the browser, the footer reads `v0.1.9`, and **Settings shows the new Client ID value block**. This is the only place the release gets checked as a real `.exe` rather than as source.

---

## Task 10: Tag, release, and verify the update path

### Step 10.1 — tag the merge commit

- [ ] `git tag v0.1.9 <merge-sha-from-step-8.3>`
- [ ] `git push origin v0.1.9`
- [ ] `git tag -l 'v0.1.9'` and `git ls-remote --tags origin v0.1.9` both return it. **The push is the step that was missed last time — confirm it landed on the remote, not just locally.**

### Step 10.2 — create the release

- [ ] ```
      gh release create v0.1.9 packaging/dist/YotoMaker.exe \
        --title "Yoto Maker v0.1.9" --notes-file docs/RELEASE_NOTES.md
      ```

### Step 10.3 — verify the release exists and is reachable

- [ ] `gh release view v0.1.9 --json tagName,name,assets` — one asset, named `YotoMaker.exe`, `"state": "uploaded"`, size matching Step 9.3.
- [ ] `gh release list --limit 1` — v0.1.9 is now `Latest`.
- [ ] `curl -sI $(gh release view v0.1.9 --json assets -q '.assets[0].url')` returns a 200/302, not a 404.

### Step 10.4 — verify the thing the user actually complained about

The complaint was "no update banner." Prove the update path is live, rather than assuming the release implies it.

- [ ] From a checkout still reporting an older version, or by pinning `__version__` locally, confirm `yoto_maker.updater.check_for_update()` returns `update_available: True` with `latest: "0.1.9"` and a `download_url` pointing at the new asset.
- [ ] Confirm a **v0.1.8 `.exe`** (the build the user is running) now shows the update banner. This is the end-to-end check; everything above is a precondition for it.

---

## Task 11: The guard against recurrence

**Files:**
- Modify: `docs/BUILDER_QUEUE.md`
- Modify: `docs/DEVELOPERS.md`

**The failure being guarded against.** The queue's Shipped row said `2026-07-20 (v0.1.9)`, which reads as *released in v0.1.9*. What had actually happened was *merged to main, version bumped*. Nothing in the queue's vocabulary could tell those two apart, so nothing flagged the gap — and the user found it by not getting an update.

Proportionate fix for a small solo project: make the queue's vocabulary able to express the difference, and give the release a checklist with a verification command whose output is the evidence. No CI, no new tooling.

**Land this in Part A's PR**, not after — the convention must exist before Builder marks the row.

### Step 11.1 — split merged from released in the queue

- [ ] In `docs/BUILDER_QUEUE.md`, replace the status key line:

```markdown
Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ shipped
```

with:

```markdown
Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ merged · 🚢 released

**`✅ merged` is not `🚢 released`.** Merged means the PR is on `main`. Released
means a tag is pushed, an `.exe` is built and a GitHub release carries it — which
is the only thing `updater.py` can see, and therefore the only thing a user can
receive. A row moves to 🚢 only when `gh release view v<version>` returns a
release with an uploaded `.exe` asset. **Paste that command's output into the
row's PR or the commit that marks it.** v0.1.9 sat merged-but-unreleased for a
day because these two states shared one word.
```

- [ ] Change the Shipped table's header from `| Shipped |` to `| Merged | Released |` and split item 1's cell:

```markdown
| # | Item | Spec | Plan | PR | Merged | Released |
|---|------|------|------|----|--------|----------|
| 1 | **Configuration surface** … | … | … | [#10](…) | 2026-07-20 | v0.1.9 |
```

Fill the Released cell for item 1 only once Task 10 has verified the release. Until then it reads `— (pending)`.

### Step 11.2 — make the release checklist explicit

- [ ] In `docs/DEVELOPERS.md`, replace the `### Publishing a release` section with:

````markdown
### Publishing a release

There is no CI. A release is these five steps in order, and **the version bump is
not one of them** — bumping `pyproject.toml` and `yoto_maker/__init__.py` happens
in the feature PR, and on its own ships nothing.

1. **Verify** — on `main`, clean, `pytest -q` green, `docs/RELEASE_NOTES.md`
   opens with the version being cut and its section covers everything in it.
2. **Tag the merge commit** and push it:
   ```bash
   git tag v0.1.9 <merge-sha> && git push origin v0.1.9
   ```
3. **Build** (see above). Stage `packaging/vendor/ffmpeg.exe` **and**
   `ffprobe.exe` first — they are gitignored and absent in a fresh checkout.
4. **Publish:**
   ```bash
   gh release create v0.1.9 packaging/dist/YotoMaker.exe \
     --title "Yoto Maker v0.1.9" --notes-file docs/RELEASE_NOTES.md
   ```
5. **Verify the release exists**, because steps 2–4 can each half-succeed:
   ```bash
   gh release view v0.1.9 --json tagName,assets \
     -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
   ```
   Expected: `v0.1.9 -> YotoMaker.exe`. Anything else — including a release with
   no asset — means users get no update.

**`updater.py` reads GitHub releases, not tags and not `pyproject.toml`.** A
bumped version with no release is invisible to every installed copy: the app
correctly reports "no update available" because there is nothing to download.
This is what happened to v0.1.9, and the symptom is indistinguishable from the
app being up to date. If a user says "I'm not getting the update", run step 5
first.

The end-user install guide ([INSTALL-FOR-MOM.md](INSTALL-FOR-MOM.md)) points at
`releases/latest`, so an un-created release also leaves that link on the previous
version.
````

---

## Test Plan

Required and will be executed: a **Tester** agent drives a live browser, a **Polisher** agent audits the diff against the amended handoff.

Run from a clean checkout of the branch. Start with `python -m yoto_maker --no-tray --no-browser` and open `http://127.0.0.1:8777/#settings`.

**Where state lives** (needed to set up the three sources):
- Saved sign-in: `%LOCALAPPDATA%\YotoMaker\yoto_token.json`
- Saved settings: `%LOCALAPPDATA%\YotoMaker\settings.json`

Back both up before you start, and restore them at the end.

> **Clear the browser cache before any UAT on this repo — or you will measure a build that isn't there.**
> The static assets are served without cache-busting, so a browser will happily reuse a stale `app.js`/`styles.css`
> across a rebuild. During PR #10's UAT this produced **three false failures** in a row — `--focus-ring` reading
> empty, the header pill showing a UA-default dark outline, and the pill triggering sign-in instead of routing to
> Settings — all three artifacts of a cached bundle, not real defects.
>
> - **Before you measure anything:** issue `Network.clearBrowserCache` and `Network.setCacheDisabled {cacheDisabled: true}`
>   over CDP (or hard-reload with DevTools open and "Disable cache" ticked).
> - **The tell is a size mismatch.** Compare the served asset's byte count against the file on disk — the stale run
>   served `app.js` at 22706 bytes while disk had 43353. If those two disagree, every measurement you just took is
>   suspect; clear the cache and start the section over.
> - Treat a surprising CSS/JS failure as a cache miss until proven otherwise, *especially* a custom property that
>   reads empty or a control that behaves like its previous version. **This section is unusually exposed to it:**
>   a stale `app.js` has no `#clientIdReveal` listener and a stale `styles.css` has no `.mono-value`, which together
>   look exactly like "the feature doesn't work."

### A. `builtin` — the block must not appear

1. Ensure no `YOTO_CLIENT_ID` env var and no saved value. Open Settings.
2. **Expect:** status reads `Using the built-in Client ID` / `This is what most people use. Nothing to do here.`
3. **Expect:** **no value, no label, no toggle.** `#clientIdCurrent` is `hidden`.
4. **Expect:** the input label reads `Paste a Client ID`.
5. In DevTools, confirm `/api/status` → `yoto.client_id_full` is `null`.
6. **Expect:** this state is visually identical to v0.1.9-pre-reveal. This is the state ~every user is in; it must not get heavier.

### B. `saved` — the core case

1. Paste `a8OGO6EfbWit5tDUUrOz0g49s49NQoU1` and save; confirm.
2. **Expect:** status reads `Using your own Client ID` / `Saved on this computer only.` — **no `Ends in …` fragment.**
3. **Expect:** above the input, `The one you’re using now`, then `a8OG…oU1` and a `Show the whole thing` button.
4. **Expect:** the value renders in a **monospace** face. Confirm via computed style, not by eye — `font-family` must resolve to Consolas / Cascadia Mono, not Segoe UI. **This is the check most likely to be lost to a stale `styles.css`.**
5. **Expect:** the input label now reads `Paste a different Client ID`.
6. Click the toggle. **Expect:** the full 32-character string; label becomes `Show the short version`; focus stays on the button; **no network request fires** (check the Network panel).
7. Click again. **Expect:** back to `a8OG…oU1`, label back to `Show the whole thing`.
8. Select the revealed value with the mouse and copy it. **Expect:** exactly 32 characters, no spaces, no ellipsis.

### C. `env` — shown, and exempt from the disabling

1. Restart with `YOTO_CLIENT_ID` set to a distinct 32-character value.
2. **Expect:** status reads `Set outside the app` with the amber dot.
3. **Expect:** the input and `Save` are **disabled** — and the value block and its toggle are **shown and fully enabled**. This is the exemption; a disabled toggle here is a bug.
4. Toggle it. **Expect:** it works exactly as in section B.
5. **Expect:** the input label reads `Paste a Client ID` (not `a different`).
6. **Expect:** `Go back to the built-in one` is absent from the DOM.
7. **Expect:** the env note still reads *"You can still type one here, but it won't be used while the one above is set."* — unchanged, and now with a literal on-screen referent above it.

### D. Reveal persistence across a cancelled confirmation — the regression this feature is most likely to ship

1. In the `saved` state, click `Show the whole thing`. Full value on screen.
2. Type a new Client ID into the input and click `Save`. The confirmation opens.
3. **Expect:** the value is **still revealed**, and the toggle is **still enabled** while the confirmation is open. The input, `Save` and `Go back to the built-in one` are all disabled or hidden.
4. Toggle it twice while the confirmation is open. **Expect:** it works; the confirmation is unaffected.
5. Leave it revealed. Click `Never mind`.
6. **Expect:** the value is **still revealed.** A collapse here is the exact defect `clientIdRevealed` exists to prevent — `closeClientIdConfirm()` calls `renderClientId()`, and without the flag that call would collapse it for no reason the user caused.
7. **Expect:** focus returns to `Save`, and the input and actions are restored.

### E. The three resets

1. **View entry.** Reveal the value, leave Settings via `← Back to my card`, return. **Expect:** collapsed.
2. **Successful save.** Reveal, then save a different Client ID and confirm. **Expect:** collapsed, and showing the mask of the **new** value.
3. **Successful reset.** With a saved value, reveal, then `Go back to the built-in one` and confirm. **Expect:** the block disappears entirely (source is now `builtin`).
4. **Failed save.** Reveal, then force a save failure (stop the server mid-confirm, or block `POST /api/yoto/client-id` in DevTools). **Expect:** the error message appears and the value is **still revealed** — a failed save changed nothing.
5. **No timer.** Reveal the value and leave the tab untouched for **three minutes**. **Expect:** still revealed. Any auto-collapse is a bug.

### F. Accessibility, both states

1. With a screen reader (NVDA or Narrator), Tab to the toggle in the collapsed state. **Expect:** `Show the whole thing, button, collapsed`.
2. Activate with `Enter`. **Expect:** the expanded-state announcement; the accessible name is now `Show the short version`; state is `expanded`.
3. Activate with `Space`. **Expect:** same behavior — native `<button>`, no custom key handling.
4. **Expect:** the value itself is **not** announced as a live region on toggle. One announcement, from `aria-expanded`. Two announcements is the `interactions.md` §4.3 violation.
5. Arrow through `#clientIdValue` with the virtual cursor. **Expect:** the characters are readable one at a time.
6. Confirm `aria-expanded` and `aria-controls` are present and `aria-pressed` is absent.
7. Tab to the toggle and confirm the focus ring is the global `--accent` ring — not a UA default. (`.btn.small` on `--card` is row 1 of `tokens.md` §4; no override expected.)
8. **Escape does nothing** while the value is revealed and no confirmation is open.

### G. Keyboard order

1. In `saved`, Tab from `← Back to my card`. **Expect:** `… → Show the whole thing → input → Save → Go back to the built-in one`. No `tabindex` anywhere in the block.
2. With the save confirmation open, **expect:** `Show the whole thing → Never mind → Yes, use it`. `Never mind` is still first inside the confirmation and still focused on open — reflexive `Enter`/`Space` must not commit.
3. In `env`, **expect:** the toggle is focusable and the disabled input and `Save` are skipped.

### H. Layout — the narrow-width regression

1. At 720px, **expect:** the value row and the input row below it are visually parallel — same structure, same wrap behavior.
2. **Revealed, at 400px.** 32 monospace characters plus `Show the short version` must **wrap, not overflow**. The page body must not scroll horizontally and the card must not widen. This regression appears **only in the expanded state and only when narrow**, which is why it needs its own step.
3. **Expect:** the toggle wraps beneath the value at its natural width — it does **not** go full-width. The `< 420px` rule targets `.setting-actions`, and this row is `.row.wrap` inside `.setting-body`.

### I. Version skew and short values

1. Simulate an older server: in DevTools, override `/api/status` to drop `client_id_full` from the `yoto` object. **Expect:** the block still renders with the mask, and the toggle is **absent** — not present-and-broken.
2. Save a 4-character Client ID (`mine`). **Expect:** the block shows `mine` with **no toggle**, because `masked === full`. Offering to show the whole thing when it is already on screen is the lie this comparison prevents.

### J. The primitive is not widened

1. `git diff yoto_maker/server/static/styles.css` — the only change is the added `.mono-value` block. **Zero lines inside the `.setting*` block.**
2. Zero id selectors and zero positional selectors (`:nth-child`, `+`, `~`) anywhere in `.setting*`.
3. Sanity-check extensibility: copy the Client ID `<section>` in the markup, rename its ids, and confirm it renders as a third setting with **no CSS change**. Revert.

### K. Regression sweep

1. The four numbered steps on the card view are unchanged.
2. The account setting is unchanged in all its states.
3. Save, reset, and the env dead end all behave as they did in PR #10.
4. `pytest -q` — green except the known `yt_dlp` failure.
5. No new console errors or warnings; `auditSettingConfirms()` logs nothing.

### L. Release verification (Part B, after merge)

1. `gh release view v0.1.9 --json tagName,assets -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'` → `v0.1.9 -> YotoMaker.exe`.
2. `gh release list --limit 1` → v0.1.9 is Latest.
3. Launch the published `.exe` on Windows. Footer reads `v0.1.9`; Settings shows the value block.
4. **Run a v0.1.8 `.exe` and confirm the update banner appears.** This is the check that closes the user's original complaint; the three above are preconditions for it.

---

## Self-Review

**Spec coverage.** `overview.md` §4.1 slot-4 wording → Task 3 (value lives in Body); §4.3.3 scope clarification → Task 5.4 (toggle stays enabled during a confirmation); §6.2 body row → Tasks 3–4; §7.8 `client_id_full` on `/api/status`, `null` for builtin, no reveal endpoint, no redaction → Task 1; §11.1(a) full mask not last-3 → Task 4.2; §11.1(b) monospace → Task 2; §11.2 text toggle not an eye icon → Tasks 3, 5.1; §11.3 mask survives as the summary form → Task 4.2; §11.4 three sources decided separately → Task 4.2 (`builtin` hidden, `env` exempt); §11.5 primitive untouched → Tasks 2.2, 3, Test Plan §J; §11.6 status sub-line drops the value → Task 4.1. `interactions.md` §3.4 env exemption → Task 4.2; §3.5.1 markup → Task 3; §3.5.2 render rules incl. both toggle-omission rows → Task 4.2; §3.5.3 synchronous toggle, focus never moves → Task 5.1; §3.5.4 no auto-hide, three resets, the flag → Task 5.1–5.3; §3.5.5 enabled during a confirmation → Task 5.4; §3.5.6 `aria-expanded`/`aria-controls`, no live region, selectable → Tasks 3, 5.1; §4/§4.1 keyboard and tab order → Task 3 (no tabindex), Test Plan §G; §4.3 no second live region → Task 5.1; §5 narrow widths → Task 2, Test Plan §H. `copy.md` §4 table (`saved` sub-line) → Task 4.1; §4a all five strings → Tasks 3, 5.1; state-dependent input label → Tasks 3, 4.2. `tokens.md` §3a `.mono-value` verbatim → Task 2; §4 no new contrast row → Task 3.1 note; §5 `.btn.small` first use → Task 3.

**Placeholder scan.** No `TBD`, no "implement later", no "similar to Task N", no "add error handling" without the handling. Every code step carries literal code. Every `gh`/`git`/`pyinstaller` invocation is complete and runnable.

**Type consistency.** `resolve_client_id_with_source() -> tuple[str, str]` is defined in Step 1.1 and destructured in Step 1.2; it returns the same tuple as the existing private `_resolve_client_id_with_source()`, so `resolve_client_id()` and `client_id_source()` keep working unchanged. `client_id_full` is `str | None` in Python and `string | null` in the payload; the frontend coerces once at `const full = y.client_id_full || ""` and every downstream use is a string — `!!full` distinguishes absent from present, and `full !== masked` is a string comparison on both sides. `setClientIdRevealLabel(revealed: boolean)` is defined in Step 5.1 and called from both `renderClientId()` (Task 4.2) and `toggleClientIdReveal()` (Task 5.1) with a boolean in each. `clientIdRevealed` is declared with `let` at module scope in Task 5.1 and read in `renderClientId()` (Task 4.2) — a forward reference in source order, which is why it is a module-level `let` initialized before any handler can run, and `renderClientId()` is only ever called from `onOpen`/`closeClientIdConfirm`, both of which execute after parse.

**Scope check.** Nothing here implements queue items 2–6. No copy button, no clipboard, no `builtin` value, no reveal endpoint, no change to `mask_client_id()` or the two client-id routes. The `.setting*` CSS block is untouched. Part B modifies no source at all.

**Ambiguity check.** The five handoff/code disagreements are resolved above with the resolution stated, not left to Builder's judgement. The two that would produce real defects — where the reveal-reset is *set* (#1) and which of `submitClientId()`'s two `closeClientIdConfirm()` call sites owns reset #2 (#2) — each have an explicit code site and a Test Plan step (§E.1, §E.4) that fails if they are placed wrong.
</content>
</invoke>
