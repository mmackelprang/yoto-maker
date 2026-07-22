# Client ID validation + multi-file audio upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [`docs/superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](../specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md)
— the authoritative document for both items.

**Handoff:** [`docs/design-handoffs/configuration-surface/`](../../design-handoffs/configuration-surface/)
— `overview.md` §13, `copy.md` §4b/§4c/§4d/§7, `interactions.md` §3.6.

**Relationship to the handoff:** **extends** for Item A; Item B has no handoff
package by decision (spec §B.0). Six `PLANNER RESOLUTION` notes are marked inline
and tabulated in §Deviations. **Two of them correct statements in the handoff that
are stale residue from a reversed draft** — read §Deviations before starting.

**Goal:** Stop a malformed Yoto Client ID from destroying a working sign-in or
producing an uninterpretable Auth0 error page, and let a user add many audio files
in one pick with honest partial-failure reporting, retry and cancel.

**Architecture:** One validation function in `config.py` is the single source of
the verdict; it is surfaced on `/api/status` and read by the frontend and both
server call sites, so the save gate and the sign-in gate cannot disagree. Item B
adds a sequential batch runner around the existing single-file `POST
/api/tracks/file` endpoint — no endpoint contract changes — with an
`AbortController` for cancel and a two-class failure taxonomy that decides whether
a retry control is honest.

**Tech Stack:** Python 3 / FastAPI / Pydantic on the server; vanilla ES2019+ (no
build step, no framework) in `yoto_maker/server/static/`; pytest for tests.

**20 tasks in four stacks.** See §Commit stacks — the stack boundaries are a
shipping constraint, not a suggestion.

---

## Global Constraints

- **Branch first.** `feat/client-id-validation-and-multi-upload`, PR into `main`.
  Never commit implementation to `main` (global `CLAUDE.md`).
- **One PR, three commit stacks, in order: Stack 0 → Stack A → Stack B.** See
  §Commit stacks.
- **The hard gate is a DENY-LIST, never the 32-character allow-list.** The 32-char
  rule is advice shown to the user and the source of the `unusual` verdict. It
  never hard-blocks. Task 2 is where this is decided and Task 2's tests are what
  guard it.
- **`DEFAULT_YOTO_CLIENT_ID` must score `ok`** and `"test_client_id"` (from
  `tests/conftest.py:26`) must **not** score `invalid`. Both are asserted tests,
  not conventions.
- **The verdict check runs before `get_settings().set(...)` and before
  `logout()`.** The refusal copy's last line — *"Nothing was changed, and you're
  still signed in to Yoto."* — is only true because of that ordering. **If the
  reassurance line is true, the ordering is correct; if the ordering changes, the
  line must change with it.**
- **Blocking is uniform across all three tiers** (`env` / `saved` / `builtin`).
  There is **no tier condition in the blocking decision**. Only the recovery copy
  varies by tier.
- **Counts shown to the user are FILES, not tracks.** One file can become several
  tracks (`split_audio` at 50 minutes, `normalize.py:191`). `11 of your 12 files`
  stays correct when the track list gained seventeen rows.
- **A cancelled batch never issues `/api/tracks/reorder`.**
- **`#picUploadInput` (`index.html:108`) stays single-select.** Do not "finish the
  job".
- **No per-file retry buttons** — one button per group, by design.
- **No per-file timeouts** — explicitly withdrawn; cancel replaces them.
- **Copy is verbatim from the handoff.** Apostrophes follow this file's existing
  typographic convention (`’`, as in `Yoto’s`, `you’ll`, `We couldn’t`); double
  quotes stay straight. Do not reword anything else.
- **The version bump is not optional** — see §Why this PR must bump the version.

---

## Commit stacks

The maintainer's constraint: **both items in one PR, as two separable commit
stacks, Item A first, and Item A revertable independently.**

A literal reading collides with spec §A.6 decision 1 and §B.8 decision 2, which
say the `.msg-box` multi-paragraph extension is **one small extension serving both
items**, sequenced in Item A so Item B builds on it. If that extension lives in
Item A's stack, reverting Item A breaks Item B.

> **PLANNER RESOLUTION 1 — a third stack, at the bottom.** The shared groundwork
> becomes **Stack 0**, landed before either item: the `.msg-box` paragraph
> extension (Task 1, purely additive, no behavior change) and the `api()`
> HTTPException `detail` fallback (Task 1b, a small additive fix both items'
> error paths benefit from). Then:
>
> | Stack | Tasks | Contents |
> | --- | --- | --- |
> | **0** | 1, 1b | `.msg-box` renders paragraphs (1); `api()` surfaces HTTPException `detail` (1b). Shared groundwork. |
> | **A** | 2–10 | Item A. `git revert` these and Stack 0 survives, so **Item B still works**. |
> | **B** | 11–18 | Item B. Depends on Stack 0, not on Stack A. |
> | **C** | 19 | Version bump + release notes. Touches neither item's logic. |
>
> This satisfies the constraint as stated (Item A's commits are contiguous, come
> first, and revert cleanly) and satisfies the spec's "do not build it twice".
> Stack 0 is two small additive commits and reverting it alone is never something anyone wants.

**Do not interleave.** Finish and commit every task in a stack before starting the
next stack. Each task is its own commit.

---

## Why this PR must bump the version

`index.html:7` loads `/static/styles.css?v=__ASSET_V__`, and `app.py:704` replaces
`__ASSET_V__` with `__version__` at serve time. **The asset cache key is the
version string.** Item A is almost entirely `app.js`, and Item B is entirely
`app.js` + `index.html`.

Shipping this without a bump means every existing user's browser keeps serving
v0.1.10's `app.js` against v0.1.11's markup — which is queue item 8's bug
reproduced with a new payload, and it is exactly how v0.1.9 shipped a fix nobody
received. **Task 19 bumps `pyproject.toml:7` and `yoto_maker/__init__.py:3` to
`0.1.11`.** No other row in the queue is competing for that bump.

---

## Verified during planning — read this, it changes one assumption

Spec §B.3.4.6 flagged its own analysis as read-from-code and asked Planner to
verify by observation. **Done, and it holds — with one refinement that matters.**

A structural repro of `add_file` (`async def`, one `UploadFile`, one
`await file.read()`, then synchronous work, then the mutation as the last
statement) was run against uvicorn with a 40 MB body and a client abort three
seconds in:

```
[t+  3.19s] ENDPOINT ENTERED
[t+  3.20s] READ COMPLETE (41,943,040 bytes)     ← 10 ms after entering
[t+  3.33s] CLIENT ABORTED — connection dropped
[t+ 11.20s] TRACK ADDED -> ['lullaby-03.mp3']    ← 8 s AFTER the abort
             server says: {'landed': ['lullaby-03.mp3']}
```

**Three conclusions:**

1. **The in-flight file does land.** Confirmed by observation, not inference. The
   copy's hedge — *"The one that was still going may still finish — it'll turn up
   in your list if it does."* — is correct and must ship.
2. **Spec §B.3.4.6's escape hatch is effectively unreachable, and this refines the
   spec.** It says *"aborting during `await file.read()` does prevent it"*. That
   read took **10 ms for 40 MB**, because FastAPI resolves the `UploadFile`
   parameter by consuming the entire request body *before* the endpoint body runs.
   So the window in which a cancel prevents a landing is not "during the read" —
   it is "during the body transfer, before the endpoint is entered", measured here
   at ~190 ms for 40 MB over loopback. **In practice the in-flight file almost
   always lands.** No copy change is needed (*"may still finish"* remains true and
   does not overclaim), but do not let anyone "tighten" that sentence into a
   promise that it won't.
3. **A finding the spec did not have, and it supports the cancel design.**
   `adapter.fetch()` and `split_audio()` are synchronous inside an `async def`, so
   **they block uvicorn's event loop for the whole transcode** — the repro's
   `time.sleep(8)` did exactly this. Consequence for Item B: the server can
   acknowledge nothing during a transcode, so **cancel must be purely client-side**
   (`AbortController` rejects the `fetch()` promise locally, no round trip). That
   is what makes success criterion 14 — *"Cancel stops a multi-minute file in
   seconds"* — achievable at all. **Do not add a server-side cancel endpoint or
   wait for any server acknowledgement.** There is nothing to wait for and the
   server is blocked anyway.

Repro scripts are not committed; they were scratch. Test Plan §J.3 re-checks
conclusion 1 against the real app.

---

## File structure

| File | Responsibility | Tasks |
| --- | --- | --- |
| `yoto_maker/config.py` | `validate_client_id()` — the single source of the verdict, beside `_resolve_client_id_with_source()`. | 2 |
| `yoto_maker/yoto/auth.py` | Verdict on `connection_status()`; public `redirect_uri()`; the sign-in gate in `start_login()`; `AuthError.reason`. | 3, 5 |
| `yoto_maker/server/app.py` | `config` object on `/api/status`; the save gate in `set_client_id()`; the `AuthError` handler honoring `exc.reason`; the two softened `Unknown icon` messages (1b). | 1b, 3, 4, 5 |
| `yoto_maker/server/static/index.html` | `#connectWarn`; setting 3; `multiple`; `#addCancel`; step-1 copy. | 8, 9, 12 |
| `yoto_maker/server/static/app.js` | `setMsgBoxContent()`; the `api()` `detail` fallback (1b); refusal + status + mask suppression; `#connectWarn` + deep link; setting 3 render; `api()` abort branch; the whole batch runner. | 1, 1b, 6, 7, 8, 9, 11, 13–17 |
| `yoto_maker/server/static/styles.css` | Two rules for `.msg-box p`. Nothing else. | 1 |
| `tests/test_httpexception_reaches_user.py` | **New.** The `{detail}` → `api()` → user path, as a server-shape half and a client-contract half. | 1b |
| `tests/test_client_id_validation.py` | **New.** The deny-list, the two protected values, and the ordering invariant. | 2, 4, 5 |
| `tests/test_client_id_ui_markup.py` | **New.** Item A's frontend contract, as static assertions. | 10 |
| `tests/test_multi_upload_markup.py` | **New.** Item B's frontend contract, as static assertions. | 18 |
| `docs/RELEASE_NOTES.md` | v0.1.11 section. | 19 |

---

# STACK 0 — shared groundwork

### Task 1: `.msg-box` renders paragraphs

**Files:**
- Modify: `yoto_maker/server/static/app.js` (add helper beside `showError`, ~line 32)
- Modify: `yoto_maker/server/static/styles.css` (after the `.msg-box` block, line 242)

**Interfaces:**
- Produces: `setMsgBoxContent(box: HTMLElement, content: string | string[]): void`.
  A string sets one text node — today's behavior, byte for byte. An array
  replaces the box's children with one `<p>` per entry. Used by Tasks 6, 8 and 14.

**Why this is its own commit:** spec §A.6 decision 1 and §B.8 decision 2 both
name it as the one extension serving both items. See §Commit stacks.

- [ ] **Step 1: Add the helper**

In `yoto_maker/server/static/app.js`, immediately after `clearError` (line 33),
insert:

```javascript
// Render a .msg-box's contents. A string sets one text node — byte for byte
// what showError() has always done. An array becomes one <p> per entry.
//
// The array shape is not new: CLIENT_ID_CONFIRM.body is already an array and
// openClientIdConfirm() already renders it exactly this way into
// #clientIdConfirmBody. This lifts that loop out of one call site so the two
// places that now need it — the Client ID refusal messages (copy.md §4c) and
// the grouped upload summary (spec §B.3.3) — share one implementation instead
// of growing two. Landed as its own commit ahead of both items for that reason.
//
// replaceChildren() and not innerHTML: every string here is user-facing copy or
// a filename the user chose, and a filename is attacker-controllable in the
// only sense that matters locally — it is not ours to trust into markup.
function setMsgBoxContent(box, content) {
  if (!Array.isArray(content)) { box.textContent = content; return; }
  box.replaceChildren(...content.map((text) => {
    const p = document.createElement("p");
    p.textContent = text;
    return p;
  }));
}
```

- [ ] **Step 2: Add the two CSS rules**

In `yoto_maker/server/static/styles.css`, immediately after line 242
(`.msg-box.info { … }`), insert:

```css
/* Multi-paragraph .msg-box bodies (setMsgBoxContent()). Two rules, and they are
   the ONLY CSS this change needs.
   Required, not cosmetic: .setting-confirm p's margin reset (line 345) is
   scoped to .setting-confirm and does not reach here, so without these a <p>
   inside a .msg-box takes the UA default `margin: 1em 0` — ~15px of dead space
   above the first line and below the last, inside a box whose own vertical
   padding is 12px.
   10px and not .setting-confirm's 14px: .msg-box has padding 12px 16px against
   .setting-confirm's 16px, so a 14px inter-paragraph gap would be larger than
   the box's own inset and the paragraphs would read as separate boxes.
   No :first-child weight rule. .setting-confirm's bolding of the opening
   question (line 351) is deliberate there and wrong here — a refusal's first
   line is a statement, not a heading. */
.msg-box p { margin: 0 0 10px; }
.msg-box p:last-child { margin-bottom: 0; }
```

- [ ] **Step 3: Verify no behavior changed**

Run: `python -m pytest tests/ -q`
Expected: the suite's existing count, all passing. This commit is additive —
nothing calls `setMsgBoxContent` yet and no existing selector changed.

- [ ] **Step 4: Commit**

```bash
git add yoto_maker/server/static/app.js yoto_maker/server/static/styles.css
git commit -m "feat(ui): let .msg-box render an array of paragraphs

Shared groundwork for the Client ID refusal messages and the grouped
multi-file upload summary. Lifts the loop openClientIdConfirm() already
runs for CLIENT_ID_CONFIRM.body into a helper both can use.

Landed ahead of both items so reverting either leaves the other working."
```

---

### Task 1b: `api()` surfaces an HTTPException message instead of swallowing it

**Files:**
- Modify: `yoto_maker/server/static/app.js:22` (`api`)
- Modify: `yoto_maker/server/app.py:322` (`set_track_icon`) and `:395`
  (`picture_library`) — copy softening only
- Test: `tests/test_httpexception_reaches_user.py` (**new**)

**Interfaces:**
- Produces: `api()` sets the thrown `Error`'s message from `data.detail` — the
  body a bare `HTTPException` serialises to — when our own `data.error` envelope
  is absent. No signature change; `err.data` and `err.status` are untouched.
  Consumed by every existing `api()` caller: the change is that `HTTPException`
  messages stop being swallowed.

**Why this is Stack 0, and why the client-side fix is the whole fix.**

`api()` (`app.js:22`) reads only `data.error`, our own envelope — every
`FRIENDLY_ERRORS` handler and the `AuthError` handler emit `{error}`. But a bare
`raise HTTPException(status, "message")` serialises to `{"detail": "message"}`,
FastAPI's shape and not ours, so **every** `HTTPException` message in `app.py`
currently reaches the user as the generic *"Something went wrong. Please try
again."* This is the latent class PLANNER RESOLUTION 2 and §For the queue flagged;
the maintainer folded the fix in here rather than deferring it.

**One fallback in `api()` fixes the whole class at once** — both items' error
paths benefit, and it reverts cleanly with the rest of Stack 0. It was checked
against `api()` for soundness and it holds:

- Nothing depends on the current silent-swallow. `err.data` still carries the
  full parsed body, `err.status` is unchanged, and no caller branches on the
  literal generic string (`grep -n 'Something went wrong' app.js` finds only the
  two fallback definitions, never a comparison).
- **The one non-obvious hazard is 422.** FastAPI *also* uses `detail` for
  request-validation errors, where it is a **list of error objects, not a
  sentence**. `new Error([{…}])` renders `"[object Object]"`, which is worse than
  the generic line — so the fallback is **string-guarded** and a non-string
  `detail` is ignored. That guard is asserted by a test so a later
  "simplification" to a bare `|| data.detail` trips a named failure.

**No server-side envelope normalisation is needed.** The alternative — an
`HTTPException` handler, or rewriting eleven call sites to raise a
`FRIENDLY_ERRORS` type — has a larger blast radius, touches routes neither item
goes near, and buys no additional user benefit over the one-line client fallback.
The client fix is preferred precisely because it is minimal and reverts with the
stack.

> **Copy audit — every `raise HTTPException` in `app.py`, and what the fix makes
> visible.** Only endpoints called through `api()` (the JSON fetch helper)
> surface their message. The image/PDF GETs are loaded as `<img src>` or
> downloads, so their 404 body is never read by `api()` and nothing about them
> changes.
>
> | app.py | Endpoint | Message | Through `api()`? | Verdict |
> | --- | --- | --- | --- | --- |
> | 307 | `PATCH /api/tracks/{id}` (rename) | `Track not found` | yes (app.js:849) | Terse but user-parseable; only reachable via a delete/act race. **Left as-is.** |
> | 320 | `POST /api/tracks/{id}/icon` | `Track not found` | yes (app.js:999) | Same. **Left as-is.** |
> | 322 | `POST /api/tracks/{id}/icon` | `Unknown icon` | yes (app.js:999) | **Developer register — softened (Step 4).** The reachable one. |
> | 330 | `DELETE /api/tracks/{id}` | `Track not found` | yes (app.js:861) | Same as 307. **Left as-is.** |
> | 395 | `POST /api/picture/library` | `Unknown icon` | **no current caller** | Endpoint has no client call site today; **softened anyway (Step 4)** so its identical twin does not become a landmine if a caller is added. |
> | 467 | `GET /api/picture.png` | `No picture yet` | no (`<img src>`) | Not surfaced. Left. |
> | 475 | `GET /api/picture/source.png` | `No source picture` | no (`<img src>`) | Not surfaced. Left. |
> | 491 | `GET /api/icons/{id}.png` | `Unknown icon` | no (`<img src>`, app.js:827) | Not surfaced — a broken image, never text. Left as-is even though its POST siblings are softened. |
> | 517 | `POST /api/yoto/client-id` | `Please paste a Client ID first.` | yes | Already user copy, and unreachable — the frontend guards empty first (Tasks 4, 6). Left. |
> | 648 | `GET /api/label.pdf` | `No label yet` | no (download nav) | Not surfaced. Left. |
> | 659 | `GET /api/jobs/{id}` | `Job not found` | yes (pollJob → app.js:38) | **Developer register, and now reachable** after an app restart / tab reload mid-poll. **Flagged, deliberately not touched:** the job-system ADR (`docs/architecture/decisions/2026-07-21-file-upload-on-job-system.md` §5.2.3) owns the proper copy — its PR A maps this 404 to a *"Yoto Maker restarted"* message. Softening it here would pre-empt that scope, and it is no worse than today's generic line meanwhile. See Test Plan §L.2. |

- [ ] **Step 1: Write the failing test**

Create `tests/test_httpexception_reaches_user.py`:

```python
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
```

Use the same `client` fixture the other API tests use (Task 3's tests already
rely on it; if `tests/conftest.py` names it differently, match that name).

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_httpexception_reaches_user.py -q`
Expected: FAIL on `test_api_surfaces_detail_and_string_guards_it` —
`api()` has no `data.detail` fallback yet. The server-half assertion already
passes (the server has always emitted `{detail}`); it is the anchor, not the
driver.

- [ ] **Step 3: Add the fallback in `api()`**

In `yoto_maker/server/static/app.js`, replace line 22:

```javascript
    const msg = (data && data.error) || "Something went wrong. Please try again.";
```

with:

```javascript
    // Prefer our own {error} envelope. Fall back to FastAPI's {detail} — the shape
    // a bare HTTPException(status, "message") serialises to — so those messages
    // reach the user instead of being swallowed to the generic line below.
    //
    // typeof === "string" is load-bearing: FastAPI ALSO uses `detail` for 422
    // request-validation errors, where it is a LIST of error objects, not a
    // sentence. new Error([{…}]) renders "[object Object]", which is worse than the
    // generic fallback — so a non-string detail is ignored and the generic line
    // stands. Guarded by tests/test_httpexception_reaches_user.py.
    const msg =
      (data && data.error) ||
      (data && typeof data.detail === "string" && data.detail) ||
      "Something went wrong. Please try again.";
```

`err.data = data` (line 24) and `err.status = res.status` (line 25) are
**unchanged** — every consumer that reads `err.data.reason`, `err.data.retryable`
or `err.status` (the batch classifier, `SIGNIN_ERRORS`) is unaffected. Only the
human-readable message changes, and only for responses that had no `data.error`.

- [ ] **Step 4: Soften the one developer-register string the fix surfaces**

In `yoto_maker/server/app.py`, in `set_track_icon` (line 322), replace:

```python
        raise HTTPException(400, "Unknown icon")
```

with:

```python
        raise HTTPException(400, "That icon isn't available. Please pick another.")
```

Make the **identical** change to `picture_library` (line 395) — same string.
Note the apostrophe is **straight** (`isn't`), matching `app.py`'s existing copy
convention (e.g. line 292 *"That file type isn't supported…"*), not the curly
apostrophe Item A's `app.js` copy uses.

Leave the third `"Unknown icon"` at `get_icon` (line 491) untouched: it is a `GET`
image endpoint, never surfaced through `api()` (see the Copy audit). Leave every
`Track not found` and `Please paste a Client ID first.` as they are — the audit
records why.

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_httpexception_reaches_user.py -q`
Expected: all PASS.
Then the whole suite: `python -m pytest tests/ -q` — the existing count plus the
new file, all green.

- [ ] **Step 6: Commit**

```bash
git add yoto_maker/server/static/app.js yoto_maker/server/app.py tests/test_httpexception_reaches_user.py
git commit -m "fix(ui): surface HTTPException messages through api()

api() read only our own {error} envelope, so every raise HTTPException(...)
— which FastAPI serialises to {detail} — reached the user as the generic
'Something went wrong. Please try again.' One string-guarded fallback to
data.detail makes them all visible; the guard ignores 422 validation
lists so a detail array never renders as '[object Object]'.

Softens the one developer-register string this newly surfaces
('Unknown icon'). Shared Stack 0 groundwork: both items' error paths
benefit and it reverts cleanly with the stack."
```

---

# STACK A — Item A: malformed Client ID detection, blocking, and config visibility

### Task 2: `validate_client_id()` — the single source of the verdict

**Files:**
- Modify: `yoto_maker/config.py` (after `mask_client_id`, line 103)
- Test: `tests/test_client_id_validation.py` (**new**)

**Interfaces:**
- Produces: `validate_client_id(cid: str | None) -> tuple[str, str | None]`
  returning `(verdict, reason)` where
  `verdict ∈ {"ok", "unusual", "invalid"}` and
  `reason ∈ {None, "email", "url", "spaces", "length", "charset", "too_long"}`.
  Consumed by Tasks 3, 4 and 5.

**This is the most important task in Stack A. Read the whole task before editing.**

- [ ] **Step 1: Write the failing tests**

Create `tests/test_client_id_validation.py`:

```python
"""The Client ID verdict: a deny-list hard gate and a 32-character advisory.

The two rules are DELIBERATELY NOT THE SAME RULE, and that is the single most
important fact in this module. The gate that hard-blocks fires only on shapes
that are wrong regardless of format. The 32-character alphanumeric rule is
knowledge about a third party's current format, the app has no way to learn
that it has changed, and its failure mode as a hard gate is a total lockout
with no override — so it only ever advises.

Do not "simplify" the gate into the 32-character check. See
docs/design-handoffs/configuration-surface/overview.md §13.2.
"""
from __future__ import annotations

import pytest

from yoto_maker.config import DEFAULT_YOTO_CLIENT_ID, validate_client_id


# --- the two values that must never be hard-blocked ---------------------------

def test_the_shipped_default_scores_ok():
    """The one failure this whole design cannot recover from.

    A validator that rejects the shipped default bricks the app on first run for
    every user, and "Go back to the built-in one" would go back to a value the
    app refuses. overview.md §13.2 marks this test required, not optional.
    """
    assert validate_client_id(DEFAULT_YOTO_CLIENT_ID) == ("ok", None)


def test_the_test_suites_own_client_id_is_not_blocked():
    """tests/conftest.py:26 injects YOTO_CLIENT_ID="test_client_id".

    14 characters with an underscore. It contains no @, no whitespace, no / and
    no :, so it passes the gate — which is why uniform blocking across all three
    tiers (overview.md §13.5) does not block every test run in this repo.

    Had the gate been the strict 32-char allow-list, this assertion would fail
    and so would the entire suite. That is the point of the assertion.
    """
    verdict, _ = validate_client_id("test_client_id")
    assert verdict != "invalid"
    assert verdict == "unusual"


# --- the deny-list: invalid regardless of what format Yoto adopts -------------

@pytest.mark.parametrize(
    "value,reason",
    [
        ("mandydeogie@gmail.com", "email"),          # the observed real failure
        ("someone@example.co.uk", "email"),
        ("http://127.0.0.1:8777/yoto/callback", "email" if False else "url"),
        ("127.0.0.1:8777", "url"),
        ("some/path", "url"),
        ("a8OGO6EfbWit5tDU UrOz0g49s49NQoU1", "spaces"),
        ("a8OGO6EfbWit\n5tDUUrOz0g49s49", "spaces"),
        ("<script>alert(1)</script>", "charset"),
        ("a" * 129, "too_long"),
        ("", "length"),
        ("   ", "length"),
        (None, "length"),
    ],
)
def test_deny_list_values_are_invalid(value, reason):
    assert validate_client_id(value) == ("invalid", reason)


def test_an_email_inside_a_url_reports_email():
    """@ is checked before / and :.

    An email address is the more actionable diagnosis and it is the incident's
    actual case; a value with both gets the message that names the mistake she
    made.
    """
    assert validate_client_id("http://x/mandy@gmail.com") == ("invalid", "email")


# --- the exclusions: these demonstrate the principle, not merely apply it ------

@pytest.mark.parametrize(
    "value",
    [
        "yotoplay.com",                               # a dot is NOT denied
        "123-abc.apps.googleusercontent.com",         # dotted identifiers exist
        "a8OGO6Ef-bWit-5tDU-UrOz-0g49s49NQoU1",       # hyphens are NOT denied
        "a8OGO6Ef_bWit_5tDUUrOz0g49s49NQoU",          # underscores are NOT denied
        "a8OGO6EfbWit5tDUU",                          # a truncated paste
        "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1EXTRA40CHAR",  # a 40-char future format
    ],
)
def test_narrow_deny_list_leaves_these_usable(value):
    """Each of these is warned about and MUST remain usable.

    - and _ are the two commonest characters in machine identifiers; denying
    them would be the fastest possible way to build the lockout this rule exists
    to prevent. A 40-character ID is what happens if Yoto changes its format
    tomorrow — under a strict allow-list every legitimate new ID would be
    hard-blocked and the app would tell the user, confidently and in red, that
    her correct value is wrong. Recovery would need a code change and a release.
    """
    verdict, _ = validate_client_id(value)
    assert verdict == "unusual"


def test_the_32_char_rule_is_advice_and_never_hard_blocks():
    """Stated as its own assertion so a future 'simplification' trips a test
    whose name says what it broke."""
    for value in ("short", "a" * 31, "a" * 33, "MiXeD1234567890abcdefGHIJKLMNOP"):
        verdict, _ = validate_client_id(value)
        assert verdict != "invalid", value


def test_surrounding_whitespace_is_trimmed_not_rejected():
    """A paste that grabbed a trailing newline is the normal case, not an error.
    Interior whitespace is what means 'a phrase'; the trim is what makes that
    distinction possible."""
    assert validate_client_id(f"  {DEFAULT_YOTO_CLIENT_ID}\n") == ("ok", None)


def test_verdict_and_reason_are_only_meaningful_as_a_pair():
    """'charset' appears under BOTH verdicts and means different things.

    invalid+charset = contains < or >. unusual+charset = passes the deny-list
    but is not 32 alphanumerics. The verdict disambiguates; nothing may branch
    on the reason alone.
    """
    assert validate_client_id("<b>") == ("invalid", "charset")
    assert validate_client_id("not-32-chars") == ("unusual", "charset")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: FAIL — `ImportError: cannot import name 'validate_client_id'`

- [ ] **Step 3: Implement**

In `yoto_maker/config.py`, add `import re` to the imports (after `import os`),
then insert this immediately after `mask_client_id` (line 103):

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: all PASS.

Then the whole suite: `python -m pytest tests/ -q` — the existing count plus the
new file, all green. **If anything else went red, `test_client_id` is being
hard-blocked and the deny-list was implemented as an allow-list.**

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/config.py tests/test_client_id_validation.py
git commit -m "feat(config): classify a Client ID as ok / unusual / invalid

The hard gate is a deny-list of shapes that are wrong regardless of
format (@, whitespace, / : < >, empty, over 128 chars). The
32-character alphanumeric rule is advisory only and produces 'unusual'
— as a hard gate it would lock every user out the day Yoto changes its
ID format, with recovery requiring a code change and a release.

Guarded: the shipped default scores ok, and conftest's test_client_id
is not blocked."
```

---

### Task 3: Surface the verdict and the config summary on `/api/status`

**Files:**
- Modify: `yoto_maker/yoto/auth.py:187-220` (`connection_status`) and after
  `_redirect_uri` (line 58)
- Modify: `yoto_maker/server/app.py:132-144` (`status`)
- Test: `tests/test_client_id_validation.py` (append)

**Interfaces:**
- Consumes: `validate_client_id()` from Task 2.
- Produces: `/api/status` gains `yoto.client_id_verdict`, `yoto.client_id_reason`,
  and a top-level `config` object `{version, redirect_uri, data_dir}`. Consumed by
  Tasks 6–9.
- Produces: `yoto_maker.yoto.auth.redirect_uri() -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_client_id_validation.py`:

```python
# --- what the frontend actually reads -----------------------------------------

def test_status_carries_the_verdict_and_the_config_summary(client):
    """Both fields are derived from the ONE function in config.py.

    A second implementation is how the save gate and the sign-in gate come to
    disagree, and a user allowed to save a value she is then not allowed to use
    is in a worse state than the one this change is fixing.
    """
    body = client.get("/api/status").json()

    assert body["yoto"]["client_id_verdict"] in ("ok", "unusual", "invalid")
    assert "client_id_reason" in body["yoto"]

    cfg = body["config"]
    assert cfg["version"]
    # Rendered from auth._redirect_uri(), the same function start_login() uses,
    # so the string the user reads out to a helper and the string sent to Yoto
    # cannot disagree. That is the entire reason the row exists.
    assert cfg["redirect_uri"].startswith("http://127.0.0.1:")
    assert cfg["redirect_uri"].endswith("/yoto/callback")
    assert cfg["data_dir"]


def test_redirect_uri_is_not_a_frontend_constant(client):
    """config.py:108 notes the port is chosen at runtime if 8777 is busy, so a
    hardcoded frontend string would be wrong exactly when it matters most."""
    from yoto_maker.yoto import auth

    assert client.get("/api/status").json()["config"]["redirect_uri"] == auth.redirect_uri()
```

If `tests/conftest.py` does not already expose a `client` fixture, check how the
existing API tests obtain a `TestClient` and use the same fixture name.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: FAIL — `KeyError: 'client_id_verdict'`

- [ ] **Step 3: Add the public `redirect_uri()`**

In `yoto_maker/yoto/auth.py`, immediately after `_redirect_uri()` (line 58):

```python
def redirect_uri() -> str:
    """The loopback callback URL, for the settings summary (copy.md §7 row 4).

    A delegation and deliberately not a second construction: the string the user
    reads out to whoever is helping her and the string start_login() actually
    sends to Yoto must be the same string, or the row is worse than useless —
    it would confirm a match that does not exist. SETUP-YOTO-CONNECTION.md:30
    warns "This must match exactly", and a mismatch produces an Auth0 error page
    — the same failure mode as the incident this change answers, from a
    different cause.
    """
    return _redirect_uri()
```

- [ ] **Step 4a: Export `redirect_uri` from the `..yoto` package**

`app.py` imports auth symbols through `yoto_maker/yoto/__init__.py`, not from
`auth.py` directly — the established pattern for every function it uses
(`start_login`, `connection_status`, …). Follow it. In
`yoto_maker/yoto/__init__.py`, add `redirect_uri` to the `from .auth import (…)`
list (keep it alphabetical: after `logout`, before `start_login`) **and** to
`__all__`.

- [ ] **Step 4: Add the verdict to `connection_status()`**

In `yoto_maker/yoto/auth.py`, inside `connection_status()`, after the
`cid, source = ...` line (196), add:

```python
    # One traversal, one classification. The frontend and both server gates read
    # this same verdict, so they cannot drift. config.py owns the rule.
    verdict, reason = config_mod.validate_client_id(cid)
```

and add these two entries to the returned dict, after `"client_id_full"`:

```python
        "client_id_verdict": verdict,
        "client_id_reason": reason,
```

- [ ] **Step 5: Add the `config` object to `/api/status`**

In `yoto_maker/server/app.py`, in `status()` (line 137-144), add a `config` key
after `"yoto"`:

```python
        "yoto": connection_status(),
        # The config summary (copy.md §7). Every value comes from the server —
        # none may be constructed in JS. The port is not a constant
        # (config.py:108: "chosen at runtime if busy"), so a hardcoded frontend
        # redirect URL would be wrong in exactly the case where the row matters.
        "config": {
            "version": __version__,
            "redirect_uri": redirect_uri(),
            "data_dir": str(get_config().data_dir),
        },
```

Add `redirect_uri` to the existing `from ..yoto import (…)` block at the top of
the file (the same block that already imports `connection_status`, `start_login`,
etc.). Keep it alphabetical. `__version__` and `get_config` are already imported.

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: all PASS.
Then: `python -m pytest tests/ -q` — all green.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/yoto/auth.py yoto_maker/server/app.py tests/test_client_id_validation.py
git commit -m "feat(api): surface the Client ID verdict and a config summary

/api/status gains yoto.client_id_verdict, yoto.client_id_reason and a
config object carrying version, redirect_uri and data_dir. redirect_uri
delegates to auth._redirect_uri() — the same function start_login()
uses — so the string shown and the string sent cannot disagree."
```

---

### Task 4: The server refuses the save — above the write, above `logout()`

**Files:**
- Modify: `yoto_maker/server/app.py:502-520` (`set_client_id`) and `:117-126`
  (the `AuthError` handler)
- Modify: `yoto_maker/yoto/auth.py:32-34` (`AuthError`)
- Test: `tests/test_client_id_validation.py` (append)

**Interfaces:**
- Consumes: `validate_client_id()` (Task 2).
- Produces: `AuthError(message, reason=None)` with a `.reason` attribute; the
  handler at `app.py:117` emits `{"error": …, "reason": …}` at 400. Consumed by
  Task 5 and by the frontend in Task 6.

**The ordering in this task IS the feature.** A test asserts it, not just the
refusal.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_client_id_validation.py`:

```python
# --- the save gate ------------------------------------------------------------

def test_saving_an_email_is_refused(client):
    r = client.post("/api/yoto/client-id", json={"client_id": "mandydeogie@gmail.com"})
    assert r.status_code == 400
    assert r.json()["reason"] == "email"


def test_the_refusal_runs_BEFORE_the_write_and_BEFORE_logout(client, monkeypatch):
    """The invariant the whole of Item A rests on, asserted as ordering.

    The refusal copy ends with "Nothing was changed, and you're still signed in
    to Yoto." That sentence is TRUE ONLY BECAUSE OF THIS ORDERING. If a refactor
    moves the verdict check below get_settings().set(...) or below logout(), the
    copy silently becomes a lie about the one thing this change exists to
    guarantee — a user with a working sign-in must never lose it to a typo.

    Asserting "the value wasn't saved" alone would not catch a check placed
    between the write and logout(). This asserts NEITHER side effect fired.

    IF THIS TEST FAILS, DO NOT RELAX IT. Either the ordering regressed, or the
    ordering changed on purpose and copy.md §4c's reassurance line must change
    with it.
    """
    from yoto_maker.server import app as app_mod

    calls = []
    monkeypatch.setattr(app_mod, "logout", lambda: calls.append("logout"))

    from yoto_maker.settings import get_settings
    before = get_settings().get("yoto_client_id")

    r = client.post("/api/yoto/client-id", json={"client_id": "mandydeogie@gmail.com"})

    assert r.status_code == 400
    assert calls == [], "logout() ran on a refused save — a working sign-in was destroyed"
    assert get_settings().get("yoto_client_id") == before, "the refused value was written"


@pytest.mark.parametrize(
    "value,reason",
    [("someone@example.com", "email"),
     ("http://127.0.0.1:8777/yoto/callback", "url"),
     ("two words here", "spaces"),
     ("a" * 200, "too_long")],
)
def test_every_invalid_reason_reaches_the_client(client, value, reason):
    r = client.post("/api/yoto/client-id", json={"client_id": value})
    assert r.status_code == 400
    assert r.json()["reason"] == reason
    assert r.json()["error"]


def test_an_unusual_value_still_saves(client):
    """Soft, not hard. A truncated paste is warned about and then allowed —
    the false-positive cost of hard-blocking it is a total lockout."""
    r = client.post("/api/yoto/client-id", json={"client_id": "a8OGO6EfbWit5tDUU"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_client_id_validation.py -q -k "refus or reason or unusual_value"`
Expected: FAIL — the email currently saves and returns 200.

- [ ] **Step 3: Give `AuthError` an optional reason**

In `yoto_maker/yoto/auth.py`, replace:

```python
class AuthError(RuntimeError):
    """User-friendly authentication failure."""
```

with:

```python
class AuthError(RuntimeError):
    """User-friendly authentication failure.

    ``reason`` is an optional machine tag the frontend maps to its own wording
    through SIGNIN_ERRORS (app.js:1033). When absent the handler in
    server/app.py falls back to the offline/rejected split it has always
    computed, so every existing raise site is unaffected.
    """

    def __init__(self, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason
```

- [ ] **Step 4: Let the handler honor it**

In `yoto_maker/server/app.py`, in the `AuthError` handler (line 125), replace:

```python
    reason = "offline" if isinstance(exc, AuthNetworkError) else "rejected"
```

with:

```python
    # An explicit reason on the exception wins. Nothing raised one before this
    # change, so the fallback below is byte-for-byte the previous behavior.
    reason = getattr(exc, "reason", None)
    if reason is None:
        reason = "offline" if isinstance(exc, AuthNetworkError) else "rejected"
```

- [ ] **Step 5: Add the gate to `set_client_id`**

In `yoto_maker/server/app.py`, in `set_client_id()`, replace lines 515-519:

```python
    cid = body.client_id.strip()
    if not cid:
        raise HTTPException(400, "Please paste a Client ID first.")
    get_settings().set("yoto_client_id", cid)
    logout()
```

with:

```python
    cid = body.client_id.strip()
    if not cid:
        raise HTTPException(400, "Please paste a Client ID first.")

    # ------------------------------------------------------------------ #
    # THE ORDERING BELOW IS THE FEATURE. DO NOT MOVE THIS CHECK.
    #
    # It sits above the set() and above the logout() so a user with a working
    # sign-in can never lose it to a typo. The refusal message the frontend
    # renders ends with "Nothing was changed, and you're still signed in to
    # Yoto." — that sentence is true ONLY because of this ordering, so the copy
    # is the readable statement of the invariant. If this check ever moves below
    # either line, copy.md §4c's reassurance line must change with it, because
    # the app would otherwise be lying about the one thing this exists to
    # guarantee.
    #
    # Guarded by test_the_refusal_runs_BEFORE_the_write_and_BEFORE_logout.
    # overview.md §13.3.
    #
    # This is the SAFETY property. The frontend runs the same check before
    # opening its confirmation, but that check is only for the honesty of the
    # confirmation flow — this one is what protects a user running a stale
    # app.js, which this project has shipped before (overview.md §12.1).
    # ------------------------------------------------------------------ #
    verdict, reason = validate_client_id(cid)
    if verdict == "invalid":
        raise AuthError(
            "That isn't a Client ID, so Yoto Maker didn't save it. Nothing was changed.",
            reason=reason,
        )

    get_settings().set("yoto_client_id", cid)
    logout()
```

Change the config import at the top of the file from
`from ..config import get_config` to
`from ..config import get_config, validate_client_id`.

> **PLANNER RESOLUTION 2 — the refusal is an `AuthError`, not an `HTTPException`.**
> `interactions.md` §3.6.5 says *"do not invent a second error-mapping
> mechanism"*, and `HTTPException` **still** cannot satisfy the refusal's needs
> even after Task 1b makes its `detail` visible: the refusal must carry a machine
> `reason` tag that `SIGNIN_ERRORS` reads, and an `HTTPException` body has no room
> for one — it is `{"detail": …}` and nothing else. The `AuthError` handler at
> `app.py:117` already emits exactly `{"error", "reason"}` at 400 — the shape both
> gates need and the shape `api()` and `SIGNIN_ERRORS` already consume. Reusing it
> is what "do not invent a second mechanism" asks for.
>
> (**This resolution originally flagged a pre-existing latent bug — an
> `HTTPException` message never reaching the user at all, because `api()` read
> only `data.error`. Task 1b now fixes that class app-wide, so
> `"Please paste a Client ID first."` on line 517 would become visible; it stays
> unreachable only because the frontend guards the empty case first. No longer
> "noted for the queue" — folded into Stack 0.**)

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: all PASS.
Then: `python -m pytest tests/ -q` — all green.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/yoto/auth.py yoto_maker/server/app.py tests/test_client_id_validation.py
git commit -m "feat(api): refuse an invalid Client ID before the write and logout

The verdict check goes above get_settings().set() and above logout(),
so a user with a working sign-in never loses it to a typo. That
ordering is what makes the refusal message's 'nothing was changed, and
you're still signed in' line true, and a test asserts neither side
effect fires.

AuthError gains an optional reason so the refusal reaches the frontend
through the {error, reason} shape api() and SIGNIN_ERRORS already read."
```

---

### Task 5: The server refuses the sign-in

**Files:**
- Modify: `yoto_maker/yoto/auth.py:74-91` (`start_login`)
- Test: `tests/test_client_id_validation.py` (append)

**Interfaces:**
- Consumes: `validate_client_id()` (Task 2), `AuthError(…, reason=…)` (Task 4).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_client_id_validation.py`:

```python
# --- the sign-in gate ---------------------------------------------------------

def test_start_login_refuses_an_invalid_client_id(monkeypatch):
    """No doomed authorize request is ever CONSTRUCTED.

    The alternative is the worst outcome available and it is the one that
    actually happened: an Auth0 error page on a foreign domain, with copy Yoto
    Maker cannot control and the user cannot interpret.
    """
    from yoto_maker import config as config_mod
    from yoto_maker.yoto import auth

    monkeypatch.setattr(config_mod, "resolve_client_id", lambda: "mandy@gmail.com")

    with pytest.raises(auth.AuthError) as exc:
        auth.start_login()
    assert exc.value.reason == "email"


@pytest.mark.parametrize("source_value", ["mandy@gmail.com", "http://x/y", "a b c"])
def test_the_gate_has_no_tier_condition(monkeypatch, source_value):
    """Uniform across env / saved / builtin (overview.md §13.5).

    start_login() needs the VERDICT only, never the source — which is where the
    'keep it simple' instruction actually banks its simplicity. This test would
    fail the moment someone added a resolve_client_id_with_source() call and a
    tier branch.
    """
    from yoto_maker import config as config_mod
    from yoto_maker.yoto import auth

    monkeypatch.setattr(config_mod, "resolve_client_id", lambda: source_value)
    with pytest.raises(auth.AuthError):
        auth.start_login()


def test_start_login_proceeds_on_unusual(monkeypatch):
    """Soft verdicts sign in normally. This is the assertion that keeps the
    whole test suite runnable — conftest injects test_client_id, which is
    'unusual'."""
    from yoto_maker import config as config_mod
    from yoto_maker.yoto import auth

    monkeypatch.setattr(config_mod, "resolve_client_id", lambda: "test_client_id")
    url = auth.start_login()
    assert url.startswith("https://login.yotoplay.com/authorize?")
    assert "client_id=test_client_id" in url
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_client_id_validation.py -q -k "start_login or tier_condition"`
Expected: FAIL — `start_login()` builds the URL without complaint.

- [ ] **Step 3: Implement**

In `yoto_maker/yoto/auth.py`, in `start_login()`, insert as the **first statement**
of the function body, above `verifier = _b64url(...)`:

```python
    # Defense in depth against a stale app.js, which this project has shipped
    # before (overview.md §12.1). The frontend gate in connectYoto() and this
    # one test the SAME condition — "verdict is invalid" — so they agree
    # trivially. A server that refused what the frontend permitted would produce
    # a button that fails with no explanation, which is worse than either
    # behavior alone.
    #
    # NO TIER CONDITION, matching overview.md §13.5. This function needs the
    # verdict only and never the source, which is exactly where "block all tiers
    # uniformly, keep it simple" banks its simplicity. Do not add a
    # resolve_client_id_with_source() call here.
    verdict, reason = config_mod.validate_client_id(_client_id())
    if verdict == "invalid":
        raise AuthError(
            "Yoto Maker can't sign in to Yoto, because the Client ID it's using isn't one.",
            reason=reason,
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_client_id_validation.py -q`
Expected: all PASS.
Then: `python -m pytest tests/ -q` — all green. **A red suite here means the gate
is blocking `test_client_id`; re-read Task 2.**

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/yoto/auth.py tests/test_client_id_validation.py
git commit -m "feat(auth): block sign-in when the resolved Client ID is invalid

The authorize URL is never constructed. Uniform across all three tiers
— start_login() reads the verdict and never the source, which is where
the 'keep it simple' instruction banks its simplicity."
```

---

### Task 6: The client refuses the save, and names the concern on `unusual`

**Files:**
- Modify: `yoto_maker/server/static/app.js` — `clientIdMsg` (499-504),
  `openClientIdConfirm` (636-…), `trySave` (1158-1167)

**Interfaces:**
- Consumes: `setMsgBoxContent` (Task 1), `STATUS.yoto.client_id_verdict` (Task 3).
- Produces: `clientIdVerdict(value) -> {verdict, reason}`, `CLIENT_ID_REFUSAL`.

- [ ] **Step 1: Let `clientIdMsg` take an array**

Replace `clientIdMsg` (lines 499-504):

```javascript
function clientIdMsg(kind, content) {
  const box = $("#clientIdMsg");
  box.className = "msg-box " + kind;
  // A string is one text node, exactly as before; an array is one <p> each.
  // The refusal messages (copy.md §4c) are three paragraphs — what you entered
  // / what it should be / reassurance — and the reassurance line keeps its own
  // visual separation because it is the sentence doing the most work.
  setMsgBoxContent(box, content);
  show(box, true);
}
```

- [ ] **Step 2: Add the client-side verdict and the refusal copy**

Insert immediately above `clientIdMsg`:

```javascript
// The client-side mirror of config.py's validate_client_id(). It exists ONLY
// for the honesty of the confirmation flow — never confirm an action that will
// be refused (interactions.md §3.6.3, extending §3.2's "never confirm a no-op"
// from no-op to no-op or refusal). Showing the save confirmation for a value
// that will be refused would ask the user to accept a frightening consequence
// ("you'll need to sign in to Yoto again") that is never going to happen, and
// then error at her.
//
// THE SERVER CHECK IS THE SAFETY PROPERTY (app.py set_client_id). This one is
// allowed to be a second implementation for that reason and for no other; it
// must stay in lockstep with config.py. Same deny-list, same order, same
// reasons. It is NOT the 32-character rule — see config.validate_client_id.
function clientIdVerdict(value) {
  const t = (value || "").trim();
  if (!t) return { verdict: "invalid", reason: "length" };
  if (t.includes("@")) return { verdict: "invalid", reason: "email" };
  if (t.includes("/") || t.includes(":")) return { verdict: "invalid", reason: "url" };
  if (t.includes("<") || t.includes(">")) return { verdict: "invalid", reason: "charset" };
  if (/\s/.test(t)) return { verdict: "invalid", reason: "spaces" };
  if (t.length > 128) return { verdict: "invalid", reason: "too_long" };
  if (!/^[A-Za-z0-9]{32}$/.test(t)) return { verdict: "unusual", reason: "charset" };
  return { verdict: "ok", reason: null };
}

// copy.md §4c, verbatim. Three paragraphs each: what you entered / what it
// should be / reassurance. The reassurance line is appended at render time
// because it is state-dependent.
const CLIENT_ID_REFUSAL = {
  email: [
    "That looks like an email address, not a Client ID.",
    "A Client ID is a code from Yoto’s developer website — letters and numbers, with " +
    "no @ sign. It isn’t the email address you sign in to Yoto with.",
  ],
  url: [
    "That looks like a web address, not a Client ID.",
    "The setup page shows a web address and a Client ID next to each other, and it’s " +
    "easy to copy the wrong one. The Client ID is the shorter one — just letters and " +
    "numbers.",
  ],
  _default: [
    "That doesn’t look like a Client ID.",
    "A Client ID is one unbroken run of letters and numbers, with no spaces. It may " +
    "help to copy it again from Yoto’s developer website.",
  ],
};

// The reassurance line is TRUE ONLY BECAUSE the server's verdict check runs
// above get_settings().set(...) and above logout() (app.py set_client_id). It is
// the readable form of that invariant. If the ordering ever changes, this string
// must change with it.
//
// And it is state-dependent because "you're still signed in" is false when she
// isn't, and a reassurance that is audibly wrong about her situation costs more
// trust than it buys. copy.md §4c; same rule §1a and §4 already apply twice.
function clientIdReassurance() {
  const connected = !!(STATUS && STATUS.yoto && STATUS.yoto.connected);
  return connected
    ? "Nothing was changed, and you’re still signed in to Yoto."
    : "Nothing was changed.";
}
```

- [ ] **Step 3: Gate `trySave`**

Replace `trySave` (lines 1158-1167) with:

```javascript
  const trySave = () => {
    const cid = $("#clientIdInput").value.trim();
    if (!cid) {
      // Never confirm a no-op.
      clientIdMsg("err", "Please paste a Client ID first.");
      $("#clientIdInput").focus();
      return;
    }
    const { verdict, reason } = clientIdVerdict(cid);
    if (verdict === "invalid") {
      // Never confirm a refusal, either — the same rule, extended.
      // Focus and input handling mirror interactions.md §3.2 exactly: show the
      // message, focus the input, LEAVE THE VALUE INTACT so nothing she pasted
      // is lost, open no confirmation, touch neither the value display nor the
      // actions. Select-all on focus was considered and rejected — her first
      // job here is to READ what she typed and recognise it.
      const body = CLIENT_ID_REFUSAL[reason] || CLIENT_ID_REFUSAL._default;
      clientIdMsg("err", body.concat(clientIdReassurance()));
      $("#clientIdInput").focus();
      return;
    }
    openClientIdConfirm("save", verdict === "unusual");
  };
```

- [ ] **Step 4: Add the `unusual` paragraph to the confirmation**

Change `openClientIdConfirm`'s signature and body construction:

```javascript
function openClientIdConfirm(kind, unusual = false) {
  const c = CLIENT_ID_CONFIRM[kind];
  $("#clientIdConfirm").dataset.kind = kind;
  $("#clientIdConfirmText").textContent = c.title;
  const body = $("#clientIdConfirmBody");
  body.innerHTML = "";
  // An `unusual` value IS saved — the concern is named, not enforced. One extra
  // paragraph, inserted FIRST, above "Yoto Maker will start using the Client ID
  // you pasted." No new UI: the slot already carries multi-paragraph bodies.
  // copy.md §4c. Buttons unchanged: Never mind / Yes, use it.
  const paras = unusual
    ? ["Just so you know: a Client ID is usually 32 letters and numbers, and this one " +
       "isn’t. If you’re sure it’s right, go ahead."].concat(c.body)
    : c.body;
  paras.forEach((para) => {
    const p = document.createElement("p");
    p.textContent = para;
    body.appendChild(p);
  });
```

(the rest of the function is unchanged)

The `reset` call site at line 1170 passes no second argument and therefore gets
`unusual = false` — correct, a reset has no pasted value to be unusual.

- [ ] **Step 5: Verify by hand**

Start the app (`python -m yoto_maker`). **Read the launch log** — if it says
*"Yoto Maker is already running"* you are testing an old build (see Test Plan
§Standing hazards). Open Settings, paste `mandydeogie@gmail.com`, press Save.
Expect: three paragraphs in `#clientIdMsg`, **no confirmation**, the value still
in the input, focus on the input. Then paste `a8OGO6EfbWit5tDUU` — expect the
confirmation with the extra first paragraph.

- [ ] **Step 6: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): refuse a malformed Client ID before the confirmation

Never confirm an action that will be refused. Three-paragraph refusal
in the existing #clientIdMsg — what you entered / what it should be /
reassurance — with the reassurance line conditional on whether she is
actually still signed in. An unusual value still saves, with the
concern named in an extra first paragraph on the existing confirmation."
```

---

### Task 7: The status line, the mask suppression, and the promoted reset

**Files:**
- Modify: `yoto_maker/server/static/app.js` — `CLIENT_ID_STATUS` (~465-476),
  `renderClientId` (559-…)

**Interfaces:**
- Consumes: `STATUS.yoto.client_id_verdict` / `client_id_reason` (Task 3).
- Produces: `clientIdStatusRow(source, verdict, reason)`.

- [ ] **Step 1: Replace `CLIENT_ID_STATUS` with the total table**

Replace the whole `CLIENT_ID_STATUS` object with:

```javascript
// copy.md §4b. Replaces the three-row table this object used to hold.
//
// Keyed source-then-verdict, and the table is TOTAL: every combination of
// source and verdict has a row, including builtin+invalid, which is unreachable
// in a correct build and guarded by test_the_shipped_default_scores_ok. It
// exists so nobody has to reason about whether a gap is a decision. Same
// completeness discipline tokens.md §4 adopted after an unmeasured pair shipped
// a 2.56:1 label.
const ENV_SUB =
  "Someone set this up on this computer using YOTO_CLIENT_ID, and that takes " +
  "priority. To change it, they’ll need to change it there.";

const CANT_SIGN_IN_FIX_BELOW =
  "Yoto Maker can’t sign in to Yoto until this is fixed. " +
  "Press \"Go back to the built-in one\" below.";

const CLIENT_ID_STATUS = {
  builtin: {
    ok: {
      cls: "is-ok", head: "Using the built-in Client ID",
      sub: "This is what most people use. Nothing to do here.",
    },
    invalid: {
      cls: "is-err", head: "Something’s wrong with the built-in Client ID",
      sub: "Yoto Maker can’t sign in to Yoto. This shouldn’t be possible — the " +
           "details at the bottom of this page are what someone will need to help you.",
    },
  },
  saved: {
    ok: {
      cls: "is-ok", head: "Using your own Client ID",
      sub: "Saved on this computer only.",
    },
    unusual: {
      cls: "is-warn", head: "Using your own Client ID",
      sub: "Saved on this computer only. It isn’t the usual 32 letters and numbers, " +
           "so signing in to Yoto may not work.",
    },
    invalid: { cls: "is-err", head: "This isn’t a Client ID", sub: CANT_SIGN_IN_FIX_BELOW },
    // The email case gets its OWN headline. The thesis of this whole change is
    // that NAMING the mistake is what visibility failed to do — the mask
    // rendered mandydeogie@gmail.com as "mand…com", deleting the one substring
    // that would have made it self-evident. Being explicit in the save refusal
    // while being coy here would be inconsistent, and this is the exact user in
    // the incident.
    invalid_email: {
      cls: "is-err", head: "That’s an email address, not a Client ID",
      sub: CANT_SIGN_IN_FIX_BELOW,
    },
  },
  env: {
    // env + unusual DELIBERATELY has no row of its own. On a value a developer
    // set on purpose, "that isn't the usual shape" is precisely the
    // false-positive noise the deny-list's conservatism exists to suppress. On
    // env we speak up only when the value is definitely wrong.
    ok: { cls: "is-warn", head: "Set outside the app", sub: ENV_SUB },
    unusual: { cls: "is-warn", head: "Set outside the app", sub: ENV_SUB },
    invalid: {
      cls: "is-err", head: "Set outside the app, and it isn’t a Client ID",
      sub: "Yoto Maker can’t sign in to Yoto until this is fixed. YOTO_CLIENT_ID on " +
           "this computer holds something that isn’t a Client ID, and only whoever " +
           "set it can change it.",
    },
  },
};

function clientIdStatusRow(source, verdict, reason) {
  const tier = CLIENT_ID_STATUS[source] || CLIENT_ID_STATUS.builtin;
  if (verdict === "invalid" && reason === "email" && tier.invalid_email) {
    return tier.invalid_email;
  }
  // Falls back to the tier's `ok` row for any combination the table does not
  // enumerate (builtin+unusual, which the shipped default makes unreachable).
  return tier[verdict] || tier.ok;
}
```

- [ ] **Step 2: Rewrite the top of `renderClientId`**

Replace the first block of `renderClientId` (from `const y = …` through the
`$("#clientIdStatusSub").textContent = s.sub;` line) with:

```javascript
function renderClientId() {
  const y = (STATUS && STATUS.yoto) || {};
  const source = y.client_id_source || "builtin";
  const masked = y.client_id_masked || "";
  const full = y.client_id_full || "";
  const verdict = y.client_id_verdict || "ok";
  const reason = y.client_id_reason || null;
  const s = clientIdStatusRow(source, verdict, reason);

  $("#clientIdStatus").className = "setting-status " + s.cls;
  $("#clientIdStatusHead").textContent = s.head;
  $("#clientIdStatusSub").textContent = s.sub;
```

**The `The one you’re using now` label above the value stays constant across all
verdicts** — a second problem-naming string 20px below the headline is the
duplication `overview.md` §11.6 was pleased to remove. Do not make it
conditional.

- [ ] **Step 3: Suppress the mask on a bad value**

Replace the `if (showValue) { … }` block with:

```javascript
  const showValue = source !== "builtin" && !!masked;
  show($("#clientIdCurrent"), showValue);
  if (showValue) {
    // interactions.md §3.6.4 adds two rows ABOVE the existing ones, reached by
    // the same principle the table already establishes: the toggle is OMITTED,
    // never disabled, whenever it could do nothing. Here it could do nothing
    // because the whole value is already displayed.
    //
    // THE RULE: the mask is the summary form of a value that has the expected
    // SHAPE. Applied to a value that does not, it is not a summary — it is
    // camouflage. mask_client_id("mandydeogie@gmail.com") is "mand…com", which
    // deleted @gmail.com — the exact substring that would have made the mistake
    // self-evident — and what survived reads MORE code-like than the original.
    //
    // `unusual` matters here as much as `invalid`: a truncated 17-character
    // paste masks to "a8OG…tDU", hiding the truncation completely and looking
    // entirely plausible.
    const shapeFailed = verdict === "invalid" || verdict === "unusual";
    const canReveal = !shapeFailed && !!full && full !== masked;
    // clientIdRevealed is irrelevant when there is no toggle and must not be
    // consulted (§3.6.4). Its three reset events are unchanged.
    const revealed = canReveal && clientIdRevealed;
    $("#clientIdValue").textContent =
      shapeFailed ? (full || masked) : (revealed ? full : masked);
    setClientIdRevealLabel(revealed);
    show($("#clientIdReveal"), canReveal);
  }
```

`.mono-value` does the rest and is unchanged: monospace makes `@` and `.`
unmistakable, and `word-break: break-all` wraps a long value inside the column.
**Do not colour the value red** — this package reserves status colours for dots
and borders, never body text, and a 32-character monospace string set in red is
simply harder to read at the exact moment reading it is the task.

- [ ] **Step 4: Promote the reset in the `invalid` state**

At the end of `renderClientId`, after the `if (actions) { … }` block, append:

```javascript
  // Promoted to .btn primary in the invalid state ONLY, and this does not
  // breach overview.md §4.3.4's one-primary-per-setting rule: the Client ID
  // section has NO primary today — Save and the reset are both plain .btn — so
  // promoting one is within budget. It is the only state in which this section
  // has a primary action.
  //
  // Null when source is "env": the actions block is removed entirely there,
  // because deleting the saved value would fall through to the env var and
  // "Go back to the built-in one" would be a lie (overview.md §7.4).
  const reset = $("#clientIdReset");
  if (reset) reset.classList.toggle("primary", verdict === "invalid");
```

**The input and Save stay fully enabled in every non-`env` state.** The block is
on *signing in*, never on *fixing it*. Do not add a disable here.

- [ ] **Step 5: Verify by hand**

With `settings.json` holding `"yoto_client_id": "mandydeogie@gmail.com"`, open
Settings. Expect: red dot, headline *"That’s an email address, not a Client ID"*,
the value rendered **in full and unmasked** with **no** `Show the whole thing`
button, and `Go back to the built-in one` rendered as a purple primary button.

- [ ] **Step 6: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): flag a bad saved Client ID, and stop masking it

The status table becomes total across source x verdict, the email case
gets its own headline, and a value that fails the shape check renders
in full with the reveal toggle omitted — the mask turned
mandydeogie@gmail.com into 'mand…com', deleting the one substring that
made the mistake visible. The reset is promoted to primary while
invalid; the section has no other primary, so this is within budget."
```

---

### Task 8: `#connectWarn` — the card-view block and its deep link

**Files:**
- Modify: `yoto_maker/server/static/index.html` (between `#sendDone` line 144
  and the `#advRow` comment at 146)
- Modify: `yoto_maker/server/static/app.js` — `renderStatus` (129-148),
  `applyRoute` (~163), `connectYoto` (1016)

**Interfaces:**
- Consumes: `setMsgBoxContent` (Task 1), `STATUS.yoto.client_id_verdict` (Task 3).
- Produces: module-level `pendingIntent`; `renderConnectWarn()`.

- [ ] **Step 1: Add the markup**

In `yoto_maker/server/static/index.html`, insert between line 144 (`#sendDone`)
and the blank line before the `#advRow` comment:

```html
      <!-- The sign-in block (copy.md §4d). Second-to-last child, deliberately:
           it sits directly above the ⚙️ link it refers to, and #advRow stays
           last per interactions.md §1.4.

           It must NOT be #sendError. Both connectYoto() and sendToYoto() call
           clearError($("#sendError")) on entry, so a config warning parked
           there would be wiped by an unrelated action.

           Rendered proactively by renderStatus(): this state is never the
           everyday path, so overview.md §2's weight constraint is not engaged.
           In the "ok" state it renders nothing at all and step 3 is
           byte-for-byte what it was. -->
      <div id="connectWarn" class="msg-box err hidden" role="alert"></div>
```

> **PLANNER RESOLUTION 3 — `role="alert"` unconditionally.** `interactions.md`
> §3.6.7 says `#connectWarn` *"takes `role="alert"` when blocking (`saved`) and
> no role when advisory (`env`)"*. **That sentence is stale residue from the
> draft that exempted `env` from the block**, which §13.5 and §3.6.5 reversed on
> 2026-07-21. Under uniform blocking there is no advisory state — every rendered
> `#connectWarn` is a block — so the role is unconditional and lives in the
> static markup. The same residue survives in §3.6.2's state-machine diagram,
> which still reads *"invalid → RED status, sign-in still proceeds"* for `env`.
> **Both are superseded. `env` blocks.**

- [ ] **Step 2: Add the copy and the renderer**

In `app.js`, insert immediately above `renderStatus` (line 129):

```javascript
// copy.md §4d. ONE GATE, NO TIER CONDITION — if the verdict is invalid the
// sign-in is blocked whichever tier supplied the value. Only the RECOVERY
// varies, and it varies in copy rather than in control flow. That is what
// satisfies both "block all tiers uniformly" and the guard rail that every
// blocked state must be honest about its own way out.
const CONNECT_WARN = {
  saved: {
    body: ["Yoto Maker can’t sign in to Yoto, because the Client ID saved on this " +
           "computer isn’t one."],
    button: "Put back the built-in Client ID",
  },
  env: {
    // No button, and the recovery carried in words instead. Yoto Maker didn't
    // set this value and cannot unset it, and offering a control that cannot
    // act is the failure overview.md §7.4 already ruled against.
    //
    // The env var's real name appears verbatim, TWICE, deliberately: copy.md §4
    // already licenses this one narrow exception for this one tier, and it
    // applies with more force here because THE NAME IS THE RECOVERY
    // INSTRUCTION. A user who cannot act on it will read it out to someone who
    // can — the same phone call setting 3 exists to serve.
    //
    // The second paragraph exists to stop her hunting. Every other blocked
    // state in this app has a button; without a sentence saying why there
    // isn't one here, she will scroll looking for it and conclude the screen is
    // broken.
    body: ["Yoto Maker can’t sign in to Yoto. The Client ID it’s using comes from " +
           "outside the app — the YOTO_CLIENT_ID environment variable on this " +
           "computer — and what’s in there isn’t a Client ID.",
           "There’s no button here that can fix it, because Yoto Maker didn’t set it. " +
           "Whoever did will need to clear or correct YOTO_CLIENT_ID and then start " +
           "Yoto Maker again."],
    button: null,
  },
  builtin: {
    // Unreachable in a correct build; guarded by
    // test_the_shipped_default_scores_ok. The row exists so the table is total.
    //
    // "Put back the built-in Client ID" would be WRONG here: the built-in one
    // IS the broken one, so the button would promise to restore the thing that
    // is already failing. Points at setting 3 instead.
    body: ["Yoto Maker can’t sign in to Yoto, and the Client ID it came with is the " +
           "problem — which shouldn’t be possible. The details at the bottom of this " +
           "page are what someone will need to help you."],
    button: null,
  },
};

// renderStatus() runs on every refreshStatus(), including the 2-second poll
// connectYoto() starts. #connectWarn carries role="alert", so re-rendering
// identical content would re-announce the block to a screen-reader user every
// two seconds for up to three minutes. Re-render only when the state it depends
// on actually changed.
let connectWarnKey = null;

function renderConnectWarn() {
  const y = (STATUS && STATUS.yoto) || {};
  const blocked = y.client_id_verdict === "invalid";
  const key = blocked ? "invalid|" + (y.client_id_source || "builtin") : "ok";
  if (key === connectWarnKey) return;
  connectWarnKey = key;

  const box = $("#connectWarn");
  if (!blocked) {
    box.replaceChildren();
    show(box, false);
    return;
  }
  const c = CONNECT_WARN[y.client_id_source] || CONNECT_WARN.builtin;
  setMsgBoxContent(box, c.body);
  if (c.button) {
    // Omitted, never disabled, on the two tiers with no reset — the same
    // discipline interactions.md §3.5.2 applies to the reveal toggle. A
    // disabled button would invite her to keep pressing it.
    const btn = document.createElement("button");
    btn.className = "btn primary";
    btn.id = "connectWarnReset";
    btn.style.marginTop = "10px";
    btn.textContent = c.button;
    // It does NOT perform the reset. The reset signs her out and forgets her
    // value, and copy.md §4's confirmation carries the sentence answering the
    // fear she actually has ("Nothing in your Yoto account changes."). A
    // one-press control here would skip it. Routing to the ARMED confirmation
    // is one press from symptom to consequences, and it composes with the
    // existing flow rather than bypassing it.
    btn.addEventListener("click", () => {
      pendingIntent = "reset-client-id";
      gotoSettings(btn);
    });
    box.appendChild(btn);
  }
  show(box, true);
}
```

- [ ] **Step 3: Call it from `renderStatus`**

In `renderStatus`, immediately before the closing `}` (after the `#sendBtn` line):

```javascript
  $("#sendBtn").disabled = !connected;
  renderConnectWarn();
}
```

**`#connectBtn` stays enabled.** Disabling it with no visible reason is the
dead-end antipattern `interactions.md` §2.2 forbids — pressing it is the *fastest
path to the explanation*.

- [ ] **Step 4: Gate `connectYoto`**

Replace the opening of `connectYoto` (lines 1016-1018):

```javascript
async function connectYoto() {
  clearError($("#sendError"));
  // The press does not send a request — it renders the block. Follow the
  // symptom: her symptom is "connecting doesn't work", and the recovery has to
  // be adjacent to the button she pressed, not two navigations away
  // (overview.md §5.1, §12.4). renderConnectWarn() has already drawn it from
  // the last renderStatus(); this call re-asserts it in case STATUS changed.
  if (STATUS && STATUS.yoto && STATUS.yoto.client_id_verdict === "invalid") {
    renderConnectWarn();
    $("#connectWarn").scrollIntoView({ block: "nearest" });
    return;
  }
  try {
```

- [ ] **Step 5: Add `pendingIntent` and consume it**

Beside `let returnFocusTo = null;` (line ~160), add:

```javascript
// A one-shot instruction carried across the view swap, consumed by applyRoute().
// interactions.md §3.6.6: a module-level flag, NOT a second hash route — §1.1
// step 2 makes hashchange the single place the swap happens, and a second route
// would give Back and Forward two code paths to diverge across.
let pendingIntent = null;
```

In `applyRoute()`, in the `if (on)` branch, replace `openSettings();` with:

```javascript
    openSettings();
    // Consumed AFTER focus moved to #settingsTitle and AFTER openSettings()
    // kicked off the account check, so the confirmation opens into a settled
    // view (interactions.md §3.6.6). openClientIdConfirm() then moves focus to
    // #clientIdConfirmNo per §2.3 — the safe option, focused first.
    if (pendingIntent === "reset-client-id") {
      pendingIntent = null;
      $("#setting-client-id").scrollIntoView({ block: "start" });
      openClientIdConfirm("reset");
    }
```

- [ ] **Step 6: Verify by hand**

With `settings.json` holding an email address, load `/`. Expect the red box above
the ⚙️ link in step 3, with a purple `Put back the built-in Client ID` button.
Press `🔗 Connect my Yoto account` — **no new browser tab opens**, and the block
is still there. Press the recovery button — Settings opens scrolled to the Client
ID section with the reset confirmation already showing and `Never mind` focused.

Then set `YOTO_CLIENT_ID=not a client id` in the shell, restart, and confirm the
**two-paragraph** env copy with **no button**.

- [ ] **Step 7: Commit**

```bash
git add yoto_maker/server/static/index.html yoto_maker/server/static/app.js
git commit -m "feat(ui): block sign-in on the card view, with recovery inline

#connectWarn renders above the settings link in step 3 whenever the
resolved Client ID is invalid. The connect button stays enabled —
pressing it renders the explanation instead of firing a doomed
authorize request. One gate, no tier condition; only the recovery
varies: a deep link to the armed reset confirmation on 'saved', and the
YOTO_CLIENT_ID fix named in words on 'env'."
```

---

### Task 9: Setting 3 — "If you need to ask for help"

**Files:**
- Modify: `yoto_maker/server/static/index.html` (after `</section>` at line 311,
  before `</div><!-- /#settingsView -->`)
- Modify: `yoto_maker/server/static/app.js` — a new render function and a
  `registerSetting` call in `wire()`

**Interfaces:**
- Consumes: `STATUS.config` and `STATUS.yoto` (Task 3), the mask-suppression rule
  (Task 7).

- [ ] **Step 1: Add the markup**

In `index.html`, immediately after line 311's `</section>`:

```html
      <!-- Setting 3 — the config summary. overview.md §13.4, copy.md §7.
           §4.4's "copy the template, fill the slots, append" run once: slots 1
           (title), 2 (description), 4 (body) and 6 (feedback). No Status, no
           Actions, no Confirmation.

           PLACED LAST, ALWAYS VISIBLE, NO DISCLOSURE. §2's "must not get one
           pixel heavier" governs the card view, which this does not touch.
           Within the settings view, BEING LAST does the job a disclosure would
           have done — the frustrated user repairing her connection never
           scrolls here — and it does it without a control. A disclosure would
           actively hurt the one use case this section exists for: on the phone
           it turns "read me what it says at the bottom" into "no, first press
           the grey button that says…".

           SLOT 6 IS PRESENT THOUGH EMPTY AND PERMANENTLY HIDDEN. This is the
           first read-only section and it has no action that could produce
           feedback, but §4.2 says "treat this as the literal template", and
           amending the primitive to carve out an exception for one section
           would be exactly the widening §11.5 worked to avoid. One empty div is
           cheaper than a clarification to a rule that has now held three times.

           No copy button: the stated use case is READING ALOUD, which a copy
           button does not serve at all, and it would need its own transient
           "Copied!" state and clipboard-failure path (tokens.md §3a).

           Zero new CSS. Labels are .tiny above the value, stacked — the exact
           "The one you're using now" construction from §4a. NOT a two-column
           table: values wrap under .mono-value's word-break: break-all, and a
           two-column layout at 720px with wrapping values produces ragged
           rows. -->
      <section class="setting" id="setting-help">
        <h3>If you need to ask for help</h3>
        <p class="setting-desc">
          If something isn’t working and you’re asking someone for help, these are the
          details they’ll ask for. Nothing here can be changed — it’s just what Yoto
          Maker is using right now.
        </p>

        <div class="setting-body">
          <p class="tiny">Version</p>
          <div class="mono-value" id="helpVersion" style="margin-top:6px"></div>

          <!-- Obeys the mask-suppression rule: full when the verdict is
               unusual or invalid, exactly as setting 2 does. A summary that
               re-masked a bad value would undo, 200px lower, the fix directly
               above it. There is exactly ONE reveal toggle on this surface and
               it stays in setting 2, where the value's controls live. -->
          <p class="tiny" style="margin-top:14px">Client ID in use</p>
          <div class="mono-value" id="helpClientId" style="margin-top:6px"></div>

          <!-- Prose, not .mono-value: this is a sentence fragment, not a
               machine value to compare character by character. -->
          <p class="tiny" style="margin-top:14px">Where that came from</p>
          <div id="helpClientIdSource" style="margin-top:6px"></div>

          <!-- "Redirect URL" is the SETUP GUIDE's words, deliberately, and the
               one label in this section that is not plain English.
               "Sign-in address" was drafted first, reads better for the primary
               user, and was rejected. This row exists for ONE moment: she is on
               the phone and the helper is looking at dashboard.yoto.dev and at
               SETUP-YOTO-CONNECTION.md, which calls it "the redirect URL" and
               warns "This must match exactly". A string is only findable if it
               contains the word the person is holding, and the person holding a
               word here is the helper. The section title is what licenses the
               exception — a parent not in that occasion never needs to parse
               it. Carrying both names was rejected as a hedge. copy.md §7. -->
          <p class="tiny" style="margin-top:14px">Redirect URL</p>
          <div class="mono-value" id="helpRedirect" style="margin-top:6px"></div>

          <p class="tiny" style="margin-top:14px">Where Yoto Maker keeps its files</p>
          <div class="mono-value" id="helpDataDir" style="margin-top:6px"></div>
        </div>

        <div class="msg-box err hidden" id="helpMsg" role="alert" tabindex="-1"></div>
      </section>
```

- [ ] **Step 2: Add the renderer**

In `app.js`, immediately after `renderClientId`, add:

```javascript
// copy.md §7 row 3. Bare facts answering "where did it come from?", NOT the §4b
// status headlines, which answer "what state am I in?" as a sentence. Reusing
// "Using the built-in Client ID" as a value under the label "Where that came
// from" would read as a fragment.
const CLIENT_ID_ORIGIN = {
  builtin: "Built in",
  saved: "Saved on this computer",
  env: "Set outside the app",
};

function renderHelpSection() {
  const cfg = (STATUS && STATUS.config) || {};
  const y = (STATUS && STATUS.yoto) || {};
  const verdict = y.client_id_verdict || "ok";

  $("#helpVersion").textContent = cfg.version || "";
  // Same mask-suppression rule as setting 2, and no drift risk: both render
  // from the same STATUS.yoto object in the same pass (overview.md §7.2).
  const shapeFailed = verdict === "invalid" || verdict === "unusual";
  $("#helpClientId").textContent =
    shapeFailed ? (y.client_id_full || y.client_id_masked || "")
                : (y.client_id_masked || "");
  $("#helpClientIdSource").textContent =
    CLIENT_ID_ORIGIN[y.client_id_source] || CLIENT_ID_ORIGIN.builtin;
  $("#helpRedirect").textContent = cfg.redirect_uri || "";
  $("#helpDataDir").textContent = cfg.data_dir || "";
}
```

- [ ] **Step 3: Register the section**

In `wire()`, immediately after the Client ID `registerSetting({…})` block and
**before** `auditSettingConfirms()`:

```javascript
  // Setting 3 — read-only. No confirm, no closeConfirm, nothing to clear on
  // close. It re-renders on entry so a value that changed while she was on the
  // card view (a saved Client ID, a restart onto a different port) is current.
  registerSetting({ onOpen: renderHelpSection });
```

`auditSettingConfirms()` only inspects `.setting-confirm` elements, and this
section has none, so it stays silent.

- [ ] **Step 4: Keep setting 3 in the same render pass as setting 2**

Setting 3's `Client ID in use` row shares `STATUS.yoto` with setting 2. The spec
(§A.3.3) requires them to render *"in the same pass"* so they cannot drift — but
`onOpen` alone leaves setting 3 stale after an **in-settings** save (which
re-renders setting 2 through `renderClientId()` but never re-enters the view).
Wire the one coupling here, now that `renderHelpSection` exists — deliberately
**not** in Task 7, so `renderClientId()` stayed runnable on its own.

At the very end of `renderClientId()` (after the reset-promotion block added in
Task 7), append:

```javascript
  // Setting 3 reads the same STATUS.yoto (its "Client ID in use" row obeys the
  // same mask-suppression rule). Render it in the SAME PASS so a save that
  // changes the value cannot leave the two sections disagreeing (§A.3.3).
  // Guarded so renderClientId() is still safe to call before setting 3 exists.
  if (typeof renderHelpSection === "function") renderHelpSection();
```

The `typeof` guard costs nothing and documents that setting 2 does not hard-depend
on setting 3 — it updates it when present.

- [ ] **Step 5: Verify by hand**

Open Settings and scroll to the bottom. Expect five stacked label/value rows, the
version matching the footer, and the redirect URL matching the port the app is
actually serving on. Save a new Client ID **without leaving Settings** and confirm
`Client ID in use` updates in the same action. **Start the app with `--port 9000`
and confirm the redirect URL follows** — that row is the one that must never be a frontend constant.
(Note: queue item 2 is a known `--port` defect in `cfg.port`; if the row shows
8777 under `--port 9000`, that is item 2 and **not** this task. Record it, do not
fix it here.)

- [ ] **Step 6: Commit**

```bash
git add yoto_maker/server/static/index.html yoto_maker/server/static/app.js
git commit -m "feat(ui): add the 'If you need to ask for help' config summary

A read-only third .setting, last and always visible: version, the
Client ID in use, which tier supplied it, the redirect URL and the data
folder. The redirect URL is the highest-value row and was not visible
anywhere in the app — a mismatch against the Yoto dashboard produces
the same Auth0 error page as the incident, from a different cause. It
comes from the server because the port is chosen at runtime."
```

---

### Task 10: Item A regression tests

**Files:**
- Test: `tests/test_client_id_ui_markup.py` (**new**)

- [ ] **Step 1: Write the tests**

```python
"""Item A's frontend contract, as static assertions.

Markup and script assertions deliberately. The defects here are structural — a
gate on the wrong side of a write, a mask applied to a value it was never meant
to summarise, a control offered in a state where it cannot act — and that is the
class a cheap static assertion catches reliably. The live-behaviour half is in
the plan's Test Plan §A–§E.
"""
from __future__ import annotations

import pytest

from yoto_maker.server.app import STATIC_DIR


@pytest.fixture(scope="module")
def index_html() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATIC_DIR / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def styles_css() -> str:
    return (STATIC_DIR / "styles.css").read_text(encoding="utf-8")


def test_connect_warn_is_not_send_error(index_html):
    """Both connectYoto() and sendToYoto() call clearError($("#sendError")) on
    entry, so a config warning parked there would be wiped by an unrelated
    action."""
    assert 'id="connectWarn"' in index_html
    assert 'id="connectWarn" class="msg-box err hidden" role="alert"' in index_html


def test_connect_warn_sits_between_send_done_and_adv_row(index_html):
    """Second-to-last child: directly above the link it refers to, with #advRow
    still last (interactions.md §1.4)."""
    order = [index_html.index(f'id="{el}"')
             for el in ("sendDone", "connectWarn", "advRow")]
    assert order == sorted(order)


def test_the_connect_button_is_never_disabled_by_the_block(app_js):
    """Disabling it with no visible reason is the dead-end antipattern §2.2
    forbids. Pressing it is the fastest path to the explanation."""
    assert '$("#connectBtn").disabled' not in app_js


def test_the_reset_button_is_omitted_not_disabled_on_env_and_builtin(app_js):
    """A disabled button would invite her to keep pressing it. env and builtin
    get a recovery SENTENCE instead; only `saved` gets a button."""
    assert 'button: "Put back the built-in Client ID"' in app_js
    assert app_js.count("button: null") == 2


def test_the_env_variable_name_is_spoken_twice(app_js):
    """copy.md §4d: deliberate, and the name IS the recovery instruction. A user
    who cannot act on it will read it out to someone who can."""
    start = app_js.index("const CONNECT_WARN")
    end = app_js.index("let connectWarnKey")
    assert app_js[start:end].count("YOTO_CLIENT_ID") == 2


def test_there_is_no_tier_condition_in_the_blocking_decision(app_js):
    """One gate. The source decides the RECOVERY and nothing else."""
    assert 'y.client_id_verdict === "invalid"' in app_js
    # The blocked test must never be conjoined with a source test.
    assert 'client_id_verdict === "invalid" && ' not in app_js
    assert 'client_id_source === "saved" && ' not in app_js


def test_the_email_case_has_its_own_headline(app_js):
    """Naming the mistake is what visibility failed to do. Being explicit in the
    refusal while being coy in the status line would be inconsistent."""
    assert "That’s an email address, not a Client ID" in app_js
    assert "invalid_email" in app_js


def test_all_three_refusal_bodies_are_present(app_js):
    assert "That looks like an email address, not a Client ID." in app_js
    assert "That looks like a web address, not a Client ID." in app_js
    assert "That doesn’t look like a Client ID." in app_js


def test_the_reassurance_line_is_state_dependent(app_js):
    """"You're still signed in" is false when she isn't, and a reassurance that
    is audibly wrong about her situation costs more trust than it buys.

    The longer line is also the readable form of the server-side ordering
    invariant (app.py set_client_id). If it ever disappears, check that the
    ordering did not change with it.
    """
    assert "Nothing was changed, and you’re still signed in to Yoto." in app_js
    assert '"Nothing was changed."' in app_js


def test_the_client_gate_is_the_deny_list_not_the_32_char_rule(app_js):
    """The client mirror must stay in lockstep with config.validate_client_id.
    A "simplification" to the 32-char test here would refuse legitimate values
    at the confirmation while the server accepted them — the exact
    save-gate/sign-in-gate disagreement one shared rule exists to prevent."""
    fn = app_js[app_js.index("function clientIdVerdict") : app_js.index("const CLIENT_ID_REFUSAL")]
    assert 'reason: "email"' in fn
    assert 'reason: "url"' in fn
    assert 'reason: "spaces"' in fn
    # The 32-char rule appears, and it produces "unusual" — never "invalid".
    assert '{32}$/.test(t)' in fn
    assert fn.index("{32}$/.test(t)") > fn.index('verdict: "invalid", reason: "too_long"')
    assert 'verdict: "unusual"' in fn


def test_the_mask_is_suppressed_when_the_shape_check_fails(app_js):
    """The mask is the summary form of a value that has the expected SHAPE.
    Applied to one that does not it is camouflage — mand…com reads MORE
    code-like than mandydeogie@gmail.com. `unusual` matters as much as
    `invalid`: a 17-character truncation masks to a8OG…tDU, which hides the
    truncation entirely."""
    assert 'const shapeFailed = verdict === "invalid" || verdict === "unusual";' in app_js
    assert "const canReveal = !shapeFailed" in app_js


def test_setting_three_uses_the_literal_template(index_html):
    """Slot 6 is present though empty and permanently hidden. §4.2 says treat
    this as the literal template; carving an exception for one section would be
    the widening §11.5 worked to avoid."""
    start = index_html.index('id="setting-help"')
    end = index_html.index("</section>", start)
    section = index_html[start:end]
    assert "<h3>If you need to ask for help</h3>" in section
    assert 'class="setting-desc"' in section
    assert 'id="helpMsg"' in section
    assert 'class="setting-confirm' not in section
    assert 'class="setting-actions' not in section
    assert 'class="setting-status' not in section


def test_setting_three_has_all_five_rows_and_the_guides_label(index_html):
    for label in ("Version", "Client ID in use", "Where that came from",
                  "Redirect URL", "Where Yoto Maker keeps its files"):
        assert f">{label}</p>" in index_html
    # "Sign-in address" was drafted first and deliberately rejected: the person
    # holding a word at that moment is the helper, reading SETUP-YOTO-CONNECTION.md.
    assert "Sign-in address" not in index_html


def test_setting_three_is_last(index_html):
    order = [index_html.index(f'id="{el}"')
             for el in ("setting-account", "setting-client-id", "setting-help")]
    assert order == sorted(order)


def test_no_config_value_is_constructed_in_js(app_js):
    """config.py:108 — the port is chosen at runtime if 8777 is busy, so a
    hardcoded frontend redirect URL would be wrong exactly when the row matters
    most."""
    assert "127.0.0.1:8777" not in app_js
    assert "/yoto/callback" not in app_js


def test_the_msg_box_paragraph_rules_exist(styles_css):
    """.setting-confirm p's margin reset is scoped and does not reach .msg-box,
    so without these a <p> takes the UA default 1em margin inside a box with
    12px of padding."""
    assert ".msg-box p { margin: 0 0 10px; }" in styles_css
    assert ".msg-box p:last-child { margin-bottom: 0; }" in styles_css
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_client_id_ui_markup.py -q`
Expected: all PASS. If `test_no_config_value_is_constructed_in_js` fails, a
literal URL was hardcoded somewhere in Task 8 or 9 — fix the source, not the test.

- [ ] **Step 3: Full suite**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_client_id_ui_markup.py
git commit -m "test: guard Item A's frontend contract

Structural assertions for the things that regress silently: the block
is not #sendError, the connect button is never disabled, the reset is
omitted rather than disabled on env and builtin, the client gate is the
deny-list and not the 32-char rule, and the mask is suppressed on both
failing verdicts."
```

**Stack A is complete. Everything above reverts as a unit without touching Stack 0.**

---

# STACK B — Item B: multi-file audio upload

### Task 11: `api()` re-throws `AbortError` distinctly

**Files:**
- Modify: `yoto_maker/server/static/app.js:7-28` (`api`)

**Interfaces:**
- Produces: `api()` now rejects with the original `DOMException` (`.name ===
  "AbortError"`) when the caller's signal fired, instead of converting it into
  the "Couldn't reach the Yoto Maker app" `Error`. Consumed by Tasks 14 and 17.

**This is a correctness bug, not polish. Without it, cancel actively misinforms.**

- [ ] **Step 1: Implement**

Replace the `catch` block in `api()` (lines 11-18):

```javascript
  } catch (e) {
    // A deliberate cancel is a fetch rejection too, and it MUST NOT be dressed
    // up as a network failure. Without this branch, pressing Cancel reports
    // "Couldn't reach the Yoto Maker app. Make sure it's still running" —
    // alarming, and false. Worse: the upload classifier treats a rejection with
    // no .status as TRANSIENT, so the user's own cancel would come back with a
    // "Try again" button offering to retry the thing she just stopped.
    //
    // Re-thrown unchanged so callers can test e.name === "AbortError". No
    // caller passed a signal before this change, so nothing else can reach this
    // branch and no existing behaviour moves.
    if (e && e.name === "AbortError") throw e;
    // fetch() throws "Failed to fetch" when the local app server can't be
    // reached — turn that into something a non-technical user can act on.
    throw new Error(
      "Couldn't reach the Yoto Maker app. Make sure it's still running " +
      "(look for the 🎵 icon near the clock), then try again."
    );
  }
```

- [ ] **Step 2: Confirm no other caller regresses**

Run: `grep -n "signal" yoto_maker/server/static/app.js`
Expected: **no matches** before Task 17 adds one. That is the proof that the new
branch is unreachable by every existing caller.

- [ ] **Step 3: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "fix(ui): let api() re-throw AbortError instead of masking it

Every fetch rejection became 'Couldn't reach the Yoto Maker app' — an
AbortError included. That is false for a deliberate cancel, and because
the upload classifier reads a missing .status as transient, the user's
own cancel would be offered a 'Try again' button for the thing she just
stopped. No existing caller passes a signal, so nothing else changes."
```

---

### Task 12: Markup and copy for the batch

**Files:**
- Modify: `yoto_maker/server/static/index.html:65-77` (step 1)

- [ ] **Step 1: Replace the step-1 block**

Replace lines 65-74:

```html
      <div class="row">
        <button id="filePick" class="btn">📁 Choose an audio file</button>
        <input id="fileInput" type="file" accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg" class="hidden" />
      </div>

      <div id="addProgress" class="progress hidden">
        <div class="bar"><div id="addBar"></div></div>
        <div class="msg" id="addMsg"></div>
      </div>
      <div id="addError" class="msg-box err hidden"></div>
```

with:

```html
      <div class="row">
        <!-- The plural is what ADVERTISES the feature. overview.md §12.2's
             lesson: a user who wants to add twelve files needs a string on
             screen containing the words she is holding, and "Choose an audio
             file" states the opposite of the new capability. -->
        <button id="filePick" class="btn">📁 Choose audio files</button>
        <!-- `multiple` here ONLY. #picUploadInput (line 108) stays
             single-select, deliberately — do not "finish the job". -->
        <input id="fileInput" type="file" multiple accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg" class="hidden" />
      </div>
      <!-- Earns its 13px on the everyday path. It states the ordering rule in
           plain words, so the order is a PROMISE rather than a surprise; and it
           pre-answers the panic, because natural sort is only SAFE on the
           strength of reordering existing, and that safety is only real if she
           knows it. The failure case is concrete: an audiobook named
           "Chapter One / Chapter Three / Chapter Two" sorts wrong under any
           filename rule, and she needs to know both that it happened and that
           it is fixable. Rejected: a title attribute (invisible to scanning and
           to touch) and showing it only after a batch (a promise has to precede
           the action it governs). -->
      <p class="tiny" style="margin-top:8px">You can pick more than one. They go in order by file name, and you can move them around afterwards.</p>

      <div id="addProgress" class="progress hidden">
        <div class="bar"><div id="addBar"></div></div>
        <!-- Cancel is a plain .btn beside the bar — the exact string and shape
             copy.md §3 already uses for the signing_in state, where
             interactions.md §2.4 puts Cancel next to a disabled primary during
             a long wait. Same problem, same answer, no new vocabulary.
             It appears whenever #addProgress does, INCLUDING for a single file:
             that is where the multi-minute waits actually live today, so
             excluding n=1 would withhold the button from the case that
             motivated it.
             align-items and the inline margin-top mirror .progress .msg's own
             8px so the two tops align. Zero new CSS. -->
        <div class="row wrap" style="align-items:flex-start">
          <!-- role="status", polite. During a batch this announces once per
               file — twelve announcements, which is a lot, and it is correct:
               the progress text is the ONLY signal of liveness a non-sighted
               user has, and hearing nothing for forty seconds is
               indistinguishable from a hung app. -->
          <div class="msg grow" id="addMsg" role="status"></div>
          <button id="addCancel" class="btn small" style="margin-top:8px">Cancel</button>
        </div>
      </div>
      <!-- role="alert" and tabindex="-1": neither existed, a pre-existing gap
           against the pattern every .msg-box in the settings view follows.
           tabindex is what lets a retry or a cancel move focus here. -->
      <div id="addError" class="msg-box err hidden" role="alert" tabindex="-1"></div>
```

- [ ] **Step 2: Verify the page still loads**

Start the app, load `/`. The button reads `📁 Choose audio files`, the `.tiny`
line sits beneath it, and nothing else in step 1 moved. Picking a file still
works (the batch runner arrives in Task 13; `addFile` is still wired and takes
`files[0]`).

- [ ] **Step 3: Commit**

```bash
git add yoto_maker/server/static/index.html
git commit -m "feat(ui): multi-select the audio picker, and say so

#fileInput gains `multiple`; #picUploadInput deliberately does not. The
button's plural is what advertises the feature, and one 13px line makes
the filename ordering a promise rather than a surprise. #addProgress
gains a Cancel button and #addMsg/#addError gain the live-region roles
they never had."
```

---

### Task 13: Natural sort, the pre-check, and the sequential batch runner

**Files:**
- Modify: `yoto_maker/server/static/app.js` — `refreshDraft` (715), `addFile`
  (908-923), the `#fileInput` change handler (1083)

**Interfaces:**
- Produces: module-level `BATCH`; `addFiles(fileList)`; `runBatch(files)`;
  `uploadOneFile(file, {signal, onProgress})` (**seam S1**);
  `setAddProgress(pct, msg)` (**seam S3**); `refreshDraft()` now **returns** the
  draft object.
- Consumed by Tasks 14–17.

**Three structural seams from the job-system ADR
([`docs/architecture/decisions/2026-07-21-file-upload-on-job-system.md`](../../architecture/decisions/2026-07-21-file-upload-on-job-system.md)
§3.0) land in this stack.** They change nothing a user sees and are good
factoring on their own terms; they also keep a later endpoint swap to one
function body. **That arc is out of scope for this PR — do not plan it.** The
seams: **S1** one upload call site (`uploadOneFile`, this task); **S2** the
classifier reads the server's tag before any status code (Task 14); **S3** one
progress setter (`setAddProgress`, this task). Each is guarded by a test in
Task 18.

- [ ] **Step 1: Make `refreshDraft` return the draft**

In `refreshDraft` (line 715), add a return at the end of the function:

```javascript
  // Returned so the batch runner can learn which track ids each file produced.
  // POST /api/tracks/file reports `count` but only the FIRST track's view, and
  // one file can become several tracks (split_audio at 50 minutes,
  // normalize.py:191). Diffing the draft is how one file maps to one OR MORE
  // ids without changing the endpoint's contract, which is out of scope.
  // Every existing caller ignores this and is unaffected.
  return draft;
```

- [ ] **Step 2: Replace `addFile` with the batch runner**

Replace the whole `addFile` function (lines 908-923) with:

```javascript
// ---- add audio: the batch -------------------------------------------------
// Upload order is natural sort by filename, applied BEFORE any upload begins.
// Use the platform. Do NOT hand-roll digit-run splitting — it is the obvious
// implementation, it is what gets written, and it gets 07-vs-7, unicode digits
// and case wrong in ways that only show up on a user's machine.
//   numeric: true        digit runs compare as numbers, so track9 < track10
//   sensitivity: "base"  case-insensitive, so Track2 and track2 don't straddle
//                        a case boundary — the behaviour a file manager gives
//   ties                 keep the browser's FileList order: Array.sort has been
//                        stable by specification since ES2019, so no tiebreak
//                        rule is needed
const FILENAME_COLLATOR = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function sortByFilename(files) {
  return files.slice().sort((a, b) => FILENAME_COLLATOR.compare(a.name, b.name));
}

// The likely real scenario is not one corrupt MP3 — it is that she selected
// everything in a folder, which included cover.jpg, AlbumArt.ini and notes.txt.
// Each of those costs a round-trip and returns a server error, turning one
// mistake into several confusing lines.
//
// The extension list is READ FROM #fileInput's own `accept` attribute rather
// than restated here, so there is literally one list and it cannot drift.
function isProbablyAudio(file) {
  if (file.type && file.type.startsWith("audio/")) return true;
  const exts = ($("#fileInput").getAttribute("accept") || "")
    .split(",").map((s) => s.trim().toLowerCase()).filter((s) => s.startsWith("."));
  const name = (file.name || "").toLowerCase();
  return exts.some((ext) => name.endsWith(ext));
}

// The batch in flight, or the one that just finished. Null when idle.
//   total      — files.length at the ORIGINAL pick. Summary counts are always
//                against this, so "11 of your 12" is stable across retries.
//   ok         — Files that landed.
//   failed     — [{file, cls: "transient"|"deterministic", text}]
//   notStarted — Files never attempted, because she cancelled.
//   inflight   — the File that was going when she cancelled, or null.
//   groups     — Map<File, string[]>. ONE FILE -> ONE OR MORE TRACK IDS.
//   cancelled  — set on cancel; the reorder is skipped unconditionally when set.
//   repaired   — a retry actually recovered something, so a reorder is owed.
let BATCH = null;
let addAbort = null;

function newBatch(files) {
  return {
    total: files.length, ok: [], failed: [], notStarted: [], inflight: null,
    groups: new Map(), cancelled: false, repaired: false,
  };
}

// Entry point from the file picker. Sorts, pre-checks, then runs.
async function addFiles(fileList) {
  const picked = sortByFilename(Array.from(fileList));
  if (!picked.length) return;

  BATCH = newBatch(picked);
  const toUpload = [];
  for (const f of picked) {
    if (isProbablyAudio(f)) toUpload.push(f);
    // Pre-check skips are ALWAYS deterministic and never enter the retry set:
    // they never reached the network, so there is nothing about them a retry
    // could change. They land straight in the "can't be added" group with no
    // control beside them.
    else BATCH.failed.push({ file: f, cls: "deterministic", text: "That isn’t an audio file." });
  }
  await runBatch(toUpload);
}

// Seam S3 — the ONE place #addBar and #addMsg are written. No inlined "40%" or
// width strings scattered at call sites. PR A and PR C of the job-system arc both
// change what feeds the bar, and neither should have to touch the batch loop to
// do it. pct is a number 0–100, or null to LEAVE THE BAR WHERE IT IS (the cancel
// case freezes the bar and changes only the message — §B.5). msg is the status
// line.
function setAddProgress(pct, msg) {
  if (pct !== null) $("#addBar").style.width = pct + "%";
  $("#addMsg").textContent = msg;
}

// Seam S1 — the ONE upload call site. The batch loop, the retry round and the
// n=1 path all send a file through here, so the eventual move of
// POST /api/tracks/file onto the job system (ADR 2026-07-21, out of scope here)
// rewrites THIS FUNCTION BODY and nothing around it — no call-site hunt.
//
// Returns the endpoint's {count, track} payload. Throws on failure exactly as
// api() does, including re-throwing AbortError (Task 11) so the caller can tell
// a cancel from a network drop.
//
// `onProgress` is accepted and, today, unused: fetch() has no upload-progress
// event, so there is no intra-file percentage to report — the file-count bar the
// loop drives is the honest signal available now. The parameter exists because
// PR C of that arc swaps fetch() here for XMLHttpRequest + upload.onprogress, and
// this is the seam it plugs into. Do not delete it for being unused; that is the
// point of a seam.
async function uploadOneFile(file, { signal, onProgress } = {}) {
  void onProgress;
  const fd = new FormData();
  fd.append("file", file);
  return api("/api/tracks/file", { method: "POST", body: fd, signal });
}

// The sequential loop. Retry re-enters this same function with the failed
// subset as its file list (spec §B.3.1.3) — same progress bar, same #addMsg
// format, same disabling, same summary rendering. There is no second batch flow.
async function runBatch(files) {
  clearError($("#addError"));
  addAbort = new AbortController();
  $("#addCancel").disabled = false;
  show($("#addProgress"), true);
  // Sequential, and that is a CORRECTNESS decision, not a performance one.
  // _add_result_as_tracks (app.py:295) appends, so parallel uploads would land
  // in the draft in nondeterministic order — destroying the sort order this
  // feature just promised. Sequential upload is what makes the natural-sort
  // rule true rather than approximately true.
  //
  // Both pickers are disabled for the same reason: a YouTube add or a second
  // file batch landing mid-sequence would interleave and break the order.
  // (#filePick was NOT disabled during a YouTube add before this change — a
  // pre-existing interleave that multi-select makes far easier to hit. The fix
  // is symmetric and lands in the same place.)
  $("#filePick").disabled = true;
  $("#ytAdd").disabled = true;

  const n = files.length;
  const single = BATCH.total === 1;
  try {
    for (let i = 0; i < n; i++) {
      const file = files[i];
      if (BATCH.cancelled) { BATCH.notStarted.push(file); continue; }

      BATCH.inflight = file;
      // n=1 keeps today's behaviour EXACTLY: bar at 40%, "Adding your file…".
      // It is the overwhelmingly common case, it works, and changing it is a
      // regression risk for no gain. The batch treatment appears only when
      // there is a batch.
      //
      // In a retry round, n is the RETRY count and not the original batch size:
      // she is watching two files go by, and "Adding 1 of 12" would be a lie.
      // The summary count stays against the original — different numbers,
      // different questions.
      setAddProgress(
        single ? 40 : Math.round((i / n) * 100),
        single ? "Adding your file…" : `Adding ${i + 1} of ${n} — ${file.name}`,
      );

      try {
        await uploadOneFile(file, { signal: addAbort.signal });
        // refreshDraft() runs after EACH success, so rows appear one by one as
        // she watches. The track list is the per-file progress display — it
        // already exists, it is the app's own model of truth, and on a partial
        // failure it does the hardest job for free: the successes are already
        // on screen and obviously safe. Cost is n round-trips over loopback.
        const draft = await refreshDraft();
        BATCH.ok.push(file);
        BATCH.groups.set(file, newTrackIds(draft));
        BATCH.inflight = null;
      } catch (e) {
        BATCH.inflight = null;
        if (e && e.name === "AbortError") {
          // Cancellation is NOT a failure and goes in neither group. She
          // stopped on purpose; classifying her decision as a failure and
          // offering to retry it would be presumptuous, and it would blur
          // "Try again" into meaning two different things.
          BATCH.cancelled = true;
          BATCH.inflight = file;
          continue;
        }
        // Continue, never stop. Stopping strands the files she already chose,
        // for a reason she did not cause, and forces her to re-pick a subset
        // she now has to compute by hand. The failures here are properties of
        // individual files — one bad file says nothing about the next.
        const cls = classifyUploadError(e);
        BATCH.failed.push({ file, cls, text: uploadReasonText(e, cls, BATCH.total) });
      }
    }
  } finally {
    addAbort = null;
    show($("#addProgress"), false);
    $("#filePick").disabled = false;
    $("#ytAdd").disabled = false;
  }

  await repairOrderIfNeeded();
  renderAddError();
}

// Track ids present in `draft` that this batch has not already claimed.
// A set difference and not a tail slice: the per-row delete buttons are
// deliberately NOT disabled during a batch, so the list can shrink under us and
// a slice would mis-attribute. Uploads are sequential and both pickers are
// disabled, so nothing else appends.
function newTrackIds(draft) {
  const claimed = new Set();
  for (const ids of BATCH.groups.values()) for (const id of ids) claimed.add(id);
  const priorOk = new Set(BATCH.__seen || []);
  const all = draft.tracks.map((t) => t.id);
  const fresh = all.filter((id) => !claimed.has(id) && !priorOk.has(id));
  BATCH.__seen = all.filter((id) => !fresh.includes(id));
  return fresh;
}
```

> **PLANNER RESOLUTION 4 — `newTrackIds` seeds `BATCH.__seen` on first call.**
> On the first file `BATCH.__seen` is undefined, so every id in the draft looks
> fresh. Seed it in `addFiles` before the loop.

Add to `addFiles`, immediately after `BATCH = newBatch(picked);`:

```javascript
  // Seed the "already there before this batch" set. Without it the first file
  // would claim every pre-existing track as its own, and the reorder would then
  // permute tracks she ordered by hand.
  try { BATCH.__seen = (await api("/api/draft")).tracks.map((t) => t.id); }
  catch (_) { BATCH.__seen = []; }
```

- [ ] **Step 3: Rewire the picker**

Replace the `#fileInput` change handler (line 1083):

```javascript
  $("#fileInput").addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length) addFiles(e.target.files);
    // The File objects are held in BATCH from here on, so nothing is re-read
    // from disk on a retry and she is never re-prompted. Clearing the input is
    // what lets her pick the same files again.
    e.target.value = "";
  });
```

- [ ] **Step 4: Add the stubs this task calls forward to**

Tasks 14–16 fill these in. Add them now so the file parses:

```javascript
function classifyUploadError(e) { return "transient"; }   // Task 14
function uploadReasonText(e, cls, total) { return e.message; }   // Task 14
async function repairOrderIfNeeded() {}                    // Task 16
function renderAddError() {}                               // Task 14
```

- [ ] **Step 5: Verify**

Pick three audio files named `track1`, `track2`, `track10`. Expect three rows in
that order (not `1, 10, 2`), the bar advancing in thirds, and `Adding 2 of 3 —
track2.mp3` in the message line. `📁 Choose audio files` and the YouTube button
are both disabled while it runs and re-enabled after.

- [ ] **Step 6: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): upload picked audio files sequentially in filename order

Intl.Collator with numeric: true and sensitivity: base, applied before
any upload begins — never a hand-rolled digit-run split. Sequential is
a correctness decision, not a performance one: the server appends, so
parallel uploads would land in nondeterministic order and destroy the
ordering this feature just promised. Both pickers are disabled during a
batch, which also closes a pre-existing interleave with YouTube adds.

A non-audio pre-check reads its extension list from #fileInput's own
accept attribute, so there is one list and it cannot drift.

Structural seams (job-system ADR, that arc out of scope here): S1 one
upload call site (uploadOneFile), S3 one progress setter
(setAddProgress). No behavior change."
```

---

### Task 14: Classification and the grouped error box

**Files:**
- Modify: `yoto_maker/server/static/app.js` — replace the Task 13 stubs

**Interfaces:**
- Consumes: `BATCH` (Task 13), `setMsgBoxContent` (Task 1), `api()`'s AbortError
  branch (Task 11).
- Produces: `classifyUploadError(e)`, `uploadReasonText(e, cls, total)`,
  `renderAddError()`.

- [ ] **Step 1: Replace the classification stubs**

```javascript
// Seam S2 — the server's own tag wins when present, checked BEFORE any status
// code. An optional reason→class override map; empty on day one. A specific
// server reason can force a class through it. Same e.data channel SIGNIN_ERRORS
// already consumes (app.js:1033); do not invent a second one.
const UPLOAD_ERROR_CLASS = {};   // e.g. { unsupported_format: "deterministic" }

// THE PRINCIPLE: never show a control that RELIABLY fails.
// A retry on a transient failure has a real chance of succeeding, which is what
// makes offering it honest. A retry on a deterministic failure has none, which
// is what makes offering it a lie.
//
// SEAM S2, and it is load-bearing beyond forward-compat: a job-based endpoint
// (job-system ADR 2026-07-21, out of scope here) reports failure as a bare error
// with NO .status. A classifier that keyed off status alone would then
// misclassify EVERY future job failure as transient and offer a "Try again" that
// reliably fails — breaking success criterion 12 from the server side. So the
// server's tag is consulted FIRST and the status table is only the fallback.
//
// The ADR's Job grows `reason` (a string) and `retryable` (bool | None, where
// None = unknown). pollJob() attaches both to the thrown Error. This branch
// honors them:
//   * a reason in UPLOAD_ERROR_CLASS   → that class (an explicit override)
//   * retryable === true               → transient
//   * retryable === false              → deterministic
//   * a reason with neither            → transient, the same default as unknown
//     (§B.3.1.2): the server flagged the failure but couldn't say whether it is
//     worth retrying, and guessing deterministic would tell her to change a file
//     that may be fine.
//
// NOTHING EMITS `reason` ON THIS ENDPOINT TODAY — add_file raises SourceError →
// 400 with {error} and no reason — so on day one this whole block is skipped and
// the status table is the authority, exactly as the spec's day-one behavior
// requires. The block and its test (test_the_server_tag_beats_the_status_code)
// exist so PR A of that arc is one function-body rewrite.
function classifyUploadError(e) {
  const d = (e && e.data) || {};
  if (d.reason) {
    if (UPLOAD_ERROR_CLASS[d.reason]) return UPLOAD_ERROR_CLASS[d.reason];
    if (d.retryable === true) return "transient";
    if (d.retryable === false) return "deterministic";
    return "transient";
  }

  const s = e && e.status;
  // fetch() rejected — connection refused, dropped, DNS. api() throws a plain
  // Error with no .status in exactly this case.
  if (s === undefined || s === null) return "transient";
  if (s >= 500) return "transient";
  if (s === 408 || s === 429) return "transient";
  // Any other 4xx. Reliably deterministic HERE specifically: app.py:99-109 maps
  // SourceError / AudioError / ImageError to 400 with a plain-language `error`
  // string, and app.py:5-6 states those messages are written to be shown
  // verbatim. So a 400 from this endpoint means "the server looked at this file
  // and rejected it", and it arrives with the sentence explaining why already
  // written. That is exactly the branch that must not offer a retry, and
  // exactly the branch that can explain itself instead.
  if (s >= 400 && s < 500) return "deterministic";

  // UNKNOWN DEFAULTS TO TRANSIENT, and this is a decision, not a fallthrough.
  // The principle forbids offering a control we KNOW will fail; an unknown
  // failure is by definition not reliably anything. And the two wrong guesses
  // cost wildly different amounts. Guessing transient when it was
  // deterministic costs one press and two seconds. Guessing deterministic when
  // it was transient TELLS HER TO CHANGE THE FILE — she opens a file that is
  // fine, finds nothing wrong, and concludes the app is broken, or re-encodes
  // or deletes a perfectly good file on the app's bad advice. That is not a
  // slower path to the same place; it is wrong advice, and wrong advice from a
  // tool aimed at a non-technical user is the most expensive failure here.
  //
  // The default is also self-correcting: a retry that returns a 400 lands the
  // file in the deterministic group, replaces "Something went wrong." with the
  // server's specific sentence, and REMOVES the control. The app corrects
  // itself in front of her.
  return "transient";
}

function uploadReasonText(e, cls, total) {
  // n = 1 is deliberately untouched: it shows exactly what it shows today, the
  // server's message alone. The short strings below exist for the GROUPED list,
  // where "Couldn't reach the Yoto Maker app. Make sure it's still running
  // (look for the 🎵 icon near the clock), then try again." repeated on four
  // lines would be unreadable. See §Deviations, resolution 5.
  if (total === 1) return e.message;
  if (cls === "deterministic") return e.message;   // the server's sentence, verbatim
  const s = e && e.status;
  if (s === undefined || s === null) return "Yoto Maker stopped responding.";
  if (s >= 500 || s === 408 || s === 429) return "Yoto Maker had a problem with this one.";
  // Claims nothing. It does not assert the connection dropped and does not
  // assert the file is bad — the default went to transient precisely BECAUSE we
  // do not know, and a reason string that guessed would undo that honesty.
  return "Something went wrong.";
  // (No timeout branch. Per-file timeouts were withdrawn — any threshold
  // generous enough to survive a real three-hour audiobook is far too long to
  // rescue a hang, and any threshold short enough to rescue a hang would kill
  // audiobooks. Cancel replaces them and needs no number. If a future PR adds
  // one, its string is "This one took too long." and its class is transient.)
}
```

- [ ] **Step 2: Replace `renderAddError`**

```javascript
// #addError renders STRUCTURED CHILDREN — a summary paragraph, group headings,
// per-file lines and a button — not one text node. .msg-box has no rule
// forbidding child elements and .setting-confirm already sets the precedent for
// a box with a heading, body lines and actions.
//
// COUNTS ARE FILES, NOT TRACKS, throughout. One file can become several tracks
// (split_audio at 50 minutes), so "11 of your 12 files were added" stays correct
// even when the track list gained seventeen rows. She picked files, and the
// part-splitting is pre-existing behaviour she has already met on the
// single-file path.
//
// Class is .msg-box err even for a mostly-successful batch. Eleven of twelve is
// mostly a success, but a silently missing track is a real problem she must
// notice, and tokens.md §1 already argued .info is "too quiet to slow anyone
// down". The copy carries the proportionality by LEADING WITH WHAT WORKED.
function renderAddError() {
  const box = $("#addError");
  const b = BATCH;
  if (!b) { clearError(box); return; }

  const transient = b.failed.filter((f) => f.cls === "transient");
  const deterministic = b.failed.filter((f) => f.cls === "deterministic");

  // When everything succeeded, NOTHING appears. The tracks in the list are the
  // success message; a "12 files added!" box would linger or need dismissing,
  // carrying information already on screen in a more useful form. This is the
  // current single-file behaviour, preserved. It also covers a retry that
  // recovered everything: the end state is indistinguishable from a batch that
  // never failed, so nothing lingers to explain a problem that no longer exists.
  if (!b.failed.length && !b.cancelled) { clearError(box); return; }

  const kids = [];
  const p = (text, cls) => {
    const el = document.createElement("p");
    el.textContent = text;
    if (cls) el.className = cls;
    kids.push(el);
  };
  const lines = (items, render) => {
    const ul = document.createElement("ul");
    ul.style.margin = "0 0 10px";
    ul.style.paddingLeft = "18px";
    items.forEach((it) => {
      const li = document.createElement("li");
      li.textContent = render(it);
      ul.appendChild(li);
    });
    kids.push(ul);
  };

  const k = b.ok.length;
  const n = b.total;

  // --- summary line ---
  if (b.cancelled) {
    // A cancelled batch is the one end state where she cannot infer what the
    // draft now contains — she stopped partway and does not know where. The
    // summary must state it exactly.
    p(n === 1 && k === 0 ? "Stopped. Nothing was added."
                         : `Stopped. ${k} of your ${n} files were added.`);
    if (b.inflight) {
      // The honest sentence. Verified by observation during planning: after
      // the request body is received there are no await points left in
      // add_file, so the transcode and the split run to completion and the
      // track lands seconds or minutes after she pressed Cancel. Without this
      // line, a track appearing thirty seconds later looks like the button
      // failed. It says "may", and it must keep saying "may".
      p("The one that was still going may still finish — it’ll turn up in your list if it does.");
    }
  } else if (n === 1) {
    // Unchanged from today: the server's message alone, no summary, no groups,
    // no heading. "1 of your 1 files were added." is what a naive template
    // produces and it is the failure mode this branch exists to prevent.
    p(b.failed[0].text);
  } else if (k === 0) {
    p(`None of your ${n} files could be added.`);
  } else {
    // Counts are always against the ORIGINAL batch size, so the number is
    // stable across retries: after one file recovers, "10 of your 12" simply
    // becomes "11 of your 12".
    p(`${k} of your ${n} files were added.`);
  }

  // --- groups, rendered only when they have members ---
  // The common cases (all transient, all deterministic) show one group and read
  // as simply as before.
  if (transient.length && n > 1) {
    // "might" is deliberate: it sets the expectation honestly — a retry is a
    // real chance, not a promise — and it is what keeps the control truthful
    // even when the retry fails.
    p(transient.length === 1
      ? "This one didn’t work, but trying again might fix it:"
      : `These ${transient.length} didn’t work, but trying again might fix them:`);
    lines(transient, (f) => `${f.file.name} — ${f.text}`);
  }
  if (deterministic.length && n > 1) {
    // "can't be added" is deliberately final: it tells her not to wait, and not
    // to press anything.
    p(deterministic.length === 1
      ? "This one can’t be added:"
      : `These ${deterministic.length} can’t be added:`);
    lines(deterministic, (f) => `${f.file.name} — ${f.text}`);
  }
  if (b.notStarted.length) {
    // "You stopped before…" and not "These didn't work". These files did not
    // fail; she chose. Factual, carries no fault, and deliberately does not
    // offer to resume — a control that restarts what she just stopped is a
    // confusing thing to put in front of someone who has just pressed Cancel.
    p(b.notStarted.length === 1
      ? "You stopped before this one:"
      : `You stopped before these ${b.notStarted.length}:`);
    // Filenames alone — NO reason string, because there is no reason beyond her
    // own decision, and inventing one would read as blame.
    lines(b.notStarted, (f) => f.name);
  }

  box.className = "msg-box err";
  box.replaceChildren(...kids);

  // ONE button per group, never one per file (spec §B.3.1.4). A network blip
  // takes out a CONTIGUOUS RUN of files, not one, so per-file buttons would
  // mean three presses for one cause — and twelve buttons on twelve rows is
  // twelve tab stops in a visually heavy box. The button lives INSIDE the group
  // it acts on, which is why the groups exist: "I pressed Try again, why is
  // cover.jpg still failing?" cannot arise. The deterministic group sits there
  // with no control beside it — "explain, don't offer" made visible.
  //
  // Genuine failures from before a cancel keep their groups and their button:
  // that failure is real and unrelated to her decision.
  if (transient.length) {
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.id = "addRetry";
    btn.textContent = "Try again";
    btn.addEventListener("click", retryTransient);
    box.appendChild(btn);
  }
  show(box, true);

  // Focus: after the INITIAL batch, focus does NOT move here. That is a
  // deliberate divergence from interactions.md §3.2 step 4, which does move
  // focus after a save — the difference is that a save is a synchronous
  // response to a press she just made, and this lands up to a minute after her
  // click, by which time she may have moved on. role="alert" announces it
  // without stealing focus, which is exactly what the role is for. Retry and
  // cancel DO manage focus, and they do it at their own call sites (Tasks 15
  // and 17), because those results ARE synchronous responses to a press.
}
```

- [ ] **Step 3: Add the retry stub**

Task 15 fills it in:

```javascript
async function retryTransient() {}   // Task 15
```

- [ ] **Step 4: Verify**

Pick two audio files and one `.txt` renamed to look like a pick-everything
mistake — actually pick a real `cover.jpg`. Expect: two tracks added, a red box
reading `2 of your 3 files were added.`, then `This one can’t be added:` and
`cover.jpg — That isn’t an audio file.`, and **no `Try again` button**.

- [ ] **Step 5: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): classify upload failures and group them in #addError

Transient failures get a retry control; deterministic ones get the
server's own sentence and no control, because a retry on a
deterministic failure reliably fails and offering it is a lie. Unknown
defaults to transient: guessing deterministic when it was transient
tells the user to change a file that is fine, which is wrong advice
rather than a slower path to the same place.

Counts are files and never tracks — one file can become several."
```

---

### Task 15: Retry

**Files:**
- Modify: `yoto_maker/server/static/app.js` — replace the `retryTransient` stub

**Interfaces:**
- Consumes: `BATCH`, `runBatch` (Task 13), `renderAddError` (Task 14).

- [ ] **Step 1: Implement**

```javascript
// Try again re-enters the batch flow of Task 13 with the failed subset as its
// file list. Same sequential loop, same progress bar, same #addMsg format, same
// disabling, same summary rendering. THERE IS NO SECOND BATCH FLOW and no
// second partial-failure state — a retry that half-fails simply produces the
// batch summary again over a smaller n.
//
// The File objects are held from the original FileList, so nothing is re-read
// from disk and she is never re-prompted.
async function retryTransient() {
  if (!BATCH) return;
  const retry = BATCH.failed.filter((f) => f.cls === "transient").map((f) => f.file);
  if (!retry.length) return;

  // DISABLE, do not remove. Removing the button destroys it while it is
  // focused and focus falls to <body> — the single most common way a keyboard
  // user gets lost in a flow like this. Disabling also keeps #addError's
  // layout still rather than collapsing it under her cursor.
  const btn = $("#addRetry");
  if (btn) btn.disabled = true;

  // Drop the transient entries; whatever fails again is re-added by runBatch()
  // with a FRESH classification. That is what makes the unknown default
  // self-correcting: a retry that returns a 400 moves the file into the
  // deterministic group and the control disappears for it.
  BATCH.failed = BATCH.failed.filter((f) => f.cls !== "transient");
  const before = BATCH.ok.length;
  await runBatch(retry);
  if (BATCH.ok.length > before) BATCH.repaired = true;

  // After a retry, focus IS managed, and the distinction is principled rather
  // than inconsistent: a retry result IS a synchronous response to a press she
  // just made, which is exactly interactions.md §3.2 step 4's condition.
  const again = $("#addRetry");
  if (again) again.focus();                       // she may want to press again
  else if (!$("#addError").classList.contains("hidden")) $("#addError").focus();
  // If #addError is hidden, everything recovered and there is nothing to
  // announce — leaving focus where it fell is correct, because the box that
  // held it no longer exists and the track list is the outcome.
}
```

> **Note for the implementer:** `runBatch()` calls `renderAddError()` at its end,
> which rebuilds `#addError` and therefore creates a *new* `#addRetry` element.
> That is why the focus lookup above re-queries `$("#addRetry")` rather than
> reusing `btn`.

- [ ] **Step 2: Verify**

Start a batch of four files. Kill the server after the first lands (`Ctrl+C` in
the launch terminal). Expect three in the transient group with
`Yoto Maker stopped responding.` and one `Try again`. Restart the server, press
`Try again` — expect all three to land and the red box to disappear entirely.

- [ ] **Step 3: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): retry the transient group as a re-entered batch

One button for the whole group, not one per file: a network blip takes
out a contiguous run, so per-file buttons would mean three presses for
one cause. The button is disabled rather than removed while the retry
runs, so focus is not dropped to <body>, and the retry re-classifies —
a file that comes back 400 moves to the deterministic group and loses
its control."
```

---

### Task 16: The reorder repair

**Files:**
- Modify: `yoto_maker/server/static/app.js` — replace the
  `repairOrderIfNeeded` stub

**Interfaces:**
- Consumes: `BATCH.groups`, `BATCH.repaired`, `BATCH.cancelled` (Tasks 13, 15).

- [ ] **Step 1: Implement**

```javascript
// The server appends, so a file retried after files 4-12 lands LAST — she
// picked twelve, one failed, and the fix drops it at position 12 instead of 3.
// She would then press ▲ nine times, which is the friction this feature exists
// to remove. One /api/tracks/reorder at the end puts it back.
async function repairOrderIfNeeded() {
  const b = BATCH;
  if (!b) return;

  // A CANCELLED BATCH NEVER ISSUES THE REORDER. The call sends a FULL order
  // array, and after a cancel the files that never arrived have no ids — the
  // array would be built against an incomplete set, permuting real tracks
  // against positions that do not exist. Nothing is lost by skipping it: the
  // files that DID land arrived sequentially in sorted order, so they are
  // already correct. The reorder exists only to repair a retry, and a cancelled
  // batch has no repair to make.
  if (b.cancelled) return;
  // FIRE IT ONLY IF A RETRY ACTUALLY SUCCEEDED. On the happy path the
  // sequential upload already produced the right order, so the call is skipped
  // entirely. The reorder is a REPAIR, not a step.
  if (!b.repaired) return;

  const draft = await api("/api/draft");
  const present = new Set(draft.tracks.map((t) => t.id));

  // ONE FILE -> ONE OR MORE TRACK IDS. _add_result_as_tracks (app.py:213-240)
  // splits anything over MAX_TRACK_SECONDS (50 minutes) into "Title (part 1)",
  // "(part 2)"… each its own track. So sorting the batch by filename SORTS
  // GROUPS, NOT INDIVIDUAL TRACKS, and within a file the parts must stay in
  // their part order — which they do, because groups.get(file) preserves the
  // order the draft reported them in.
  const ordered = sortByFilename(b.ok);
  const batchIds = [];
  for (const file of ordered) {
    for (const id of (b.groups.get(file) || [])) if (present.has(id)) batchIds.push(id);
  }
  if (!batchIds.length) return;

  // NEVER RE-SORT THE WHOLE DRAFT. Tracks she added earlier — YouTube tracks,
  // an earlier batch — may have been ordered BY HAND. Re-sorting them would
  // destroy deliberate work to fix an incidental problem. Only indices
  // belonging to this batch are permuted, and everything else keeps its
  // current relative order, ahead of them.
  //
  // The "before" set is rebuilt from the draft AS IT IS NOW rather than from a
  // start-of-batch snapshot: the per-row delete controls are deliberately not
  // disabled during a batch, and a snapshot could send a dead id.
  const batchSet = new Set(batchIds);
  const order = draft.tracks.map((t) => t.id).filter((id) => !batchSet.has(id)).concat(batchIds);

  // Once, at the end — not after each retried file. One write, one re-render.
  await api("/api/tracks/reorder", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order }),
  });
  await refreshDraft();
}
```

- [ ] **Step 2: Verify — including the split case**

1. Add one YouTube track and move it with `▼` so its position is deliberate.
2. Pick `a.mp3`, `b.mp3`, `c.mp3`. Kill the server so `b` fails; restart; press
   `Try again`.
3. Expect the final order: **the YouTube track wherever she put it**, then
   `a`, `b`, `c` — not `a`, `c`, `b`.
4. **Repeat with an audio file longer than 50 minutes as `b`.** It becomes
   `b (part 1)`, `b (part 2)`… and those parts must land **together, in part
   order, between `a` and `c`** — not scattered.
5. Run a batch with no failures and confirm in DevTools' Network tab that
   **`/api/tracks/reorder` is never called**.

- [ ] **Step 3: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): put a retried file back in its natural-sort position

The server appends, so a retried file would land last. One reorder at
the end of a retry repairs it. It sorts GROUPS and not tracks — one
file becomes several when split_audio cuts at 50 minutes — never
re-sorts tracks that existed before the batch, fires only when a retry
actually recovered something, and never fires after a cancel, where the
missing ids would permute against positions that do not exist."
```

---

### Task 17: Cancel

**Files:**
- Modify: `yoto_maker/server/static/app.js` — `wire()`, and the tail of
  `runBatch`

**Interfaces:**
- Consumes: `addAbort`, `BATCH` (Task 13), `api()`'s AbortError branch (Task 11).

- [ ] **Step 1: Wire the button**

In `wire()`, immediately after the `#fileInput` handler:

```javascript
  // Cancel ABORTS THE REQUEST IN FLIGHT. It does not merely decline to start
  // the next file — large split audio files already run for MULTIPLE MINUTES on
  // the existing single-file path (add_file is fully synchronous: it reads the
  // upload, transcodes via ffmpeg, then splits at 50 minutes, all inside one
  // held-open request). Stop-after-current would leave her waiting minutes
  // after pressing it, which is WORSE than having no button, because a control
  // that appears to do nothing reads as broken.
  //
  // Purely client-side, and it has to be: the transcode runs synchronously
  // inside an async def, so it blocks uvicorn's event loop and the server can
  // acknowledge nothing until it finishes. AbortController rejects the fetch
  // promise locally with no round trip, which is the only reason this returns
  // in seconds. Do NOT add a server-side cancel endpoint or wait for an ack.
  $("#addCancel").addEventListener("click", () => {
    if (!addAbort || !BATCH) return;
    BATCH.cancelled = true;
    // Disabled rather than removed, for the same focus reason as Try again.
    $("#addCancel").disabled = true;
    // A real state, not a flourish. The abort is not instantaneous — the
    // request has to unwind — and the multi-minute file that provoked the
    // cancel is exactly the case where a frozen bar with no acknowledgement
    // reads as a second failure. Bar frozen (pct null), message only.
    setAddProgress(null, "Stopping…");
    addAbort.abort();
  });
```

- [ ] **Step 2: Move focus to `#addError` after a cancel**

At the end of `runBatch`, replace:

```javascript
  await repairOrderIfNeeded();
  renderAddError();
}
```

with:

```javascript
  await repairOrderIfNeeded();
  renderAddError();

  // A cancel IS a synchronous response to a press she just made, so
  // interactions.md §3.2 step 4's condition is met exactly as it is for retry —
  // unlike the initial batch, which lands up to a minute after her click.
  // Announcing the cancelled state matters more than most: it is the one end
  // state where she cannot infer what the draft now contains.
  if (BATCH && BATCH.cancelled && !$("#addError").classList.contains("hidden")) {
    $("#addError").focus();
  }
}
```

- [ ] **Step 3: Verify — this is success criterion 14**

1. Pick one genuinely long audio file (an audiobook chapter, or anything that
   takes ffmpeg more than 30 seconds). Press `Cancel` during the transcode.
2. **The UI must return within a couple of seconds** — `#addProgress` hides,
   `#addError` shows `Stopped. Nothing was added.` followed by
   *"The one that was still going may still finish…"*, and focus lands on the
   box. A cancel that leaves her waiting has failed even if it eventually works.
3. Wait. **The track probably appears anyway** — that is expected and verified
   (see §Verified during planning), and it is why the sentence is there.
4. Confirm the error box does **not** say *"Couldn't reach the Yoto Maker app"*
   and does **not** offer `Try again` for the cancelled file. If either appears,
   Task 11 did not land.
5. Cancel mid-batch (files 1–2 landed, cancel during 3, files 4–5 never start).
   Expect `Stopped. 2 of your 5 files were added.`, the "may still finish"
   sentence, and `You stopped before these 2:` listing 4 and 5 by name with **no
   reason strings and no button**.
6. Confirm in the Network tab that **`/api/tracks/reorder` was not called**.

- [ ] **Step 4: Commit**

```bash
git add yoto_maker/server/static/app.js
git commit -m "feat(ui): cancel aborts the upload in flight

Multi-minute transcodes are today's reality on the single-file path, so
stop-after-current would be indistinguishable from no cancel at all.
AbortController rejects the fetch locally — the only mechanism that can
return in seconds, since the synchronous transcode blocks the server's
event loop and it can acknowledge nothing.

Cancellation is not a failure: it gets its own group, no reason string,
and no retry control. The summary states exactly what landed, and says
honestly that the in-flight file may still turn up."
```

---

### Task 18: Item B regression tests

**Files:**
- Test: `tests/test_multi_upload_markup.py` (**new**)

- [ ] **Step 1: Write the tests**

```python
"""Item B's frontend contract, as static assertions.

The live-behaviour half — a real batch, a real network kill, a real cancel
during a real transcode — is in the plan's Test Plan §F-§J and cannot be
asserted here. What can be asserted here is the set of decisions that regress
silently under a well-meaning refactor.
"""
from __future__ import annotations

import pytest

from yoto_maker.server.app import STATIC_DIR


@pytest.fixture(scope="module")
def index_html() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATIC_DIR / "app.js").read_text(encoding="utf-8")


def test_only_the_audio_input_is_multiple(index_html):
    """#picUploadInput stays single-select. Named in the brief and restated in
    the spec so nobody 'finishes the job'."""
    audio = index_html[index_html.index('id="fileInput"'):]
    audio = audio[:audio.index(">") + 1]
    assert " multiple" in audio

    pic = index_html[index_html.index('id="picUploadInput"'):]
    pic = pic[:pic.index(">") + 1]
    assert "multiple" not in pic


def test_the_button_says_files_plural(index_html):
    """The plural is what ADVERTISES the feature — overview.md §12.2's lesson.
    'Choose an audio file' states the opposite of the new capability."""
    assert "📁 Choose audio files" in index_html
    assert "📁 Choose an audio file" not in index_html


def test_the_ordering_promise_is_on_screen_before_she_picks(index_html):
    """Natural sort is only SAFE because tracks can be reordered afterwards, and
    that safety is only real if she knows it. Rejected: a title attribute
    (invisible to scanning and touch) and showing it after the batch (a promise
    has to precede the action it governs)."""
    assert "You can pick more than one. They go in order by file name, and you can move them around afterwards." in index_html


def test_api_rethrows_abort_error_before_the_network_message(app_js):
    """Without this, the user's own cancel is reported as a network failure AND
    offered a Try again button, because the classifier reads a missing .status
    as transient. spec §B.3.4.2 — the one change without which cancel actively
    misinforms."""
    fn = app_js[app_js.index("async function api(") : app_js.index("function show(")]
    assert 'if (e && e.name === "AbortError") throw e;' in fn
    assert fn.index('e.name === "AbortError"') < fn.index("Couldn't reach the Yoto Maker app")


def test_the_sort_uses_the_platform_collator(app_js):
    """Do NOT hand-roll digit-run splitting. It is the obvious implementation,
    it is what gets written, and it gets 07-vs-7, unicode digits and case wrong
    in ways that only show up on a user's machine."""
    assert 'new Intl.Collator(undefined, { numeric: true, sensitivity: "base" })' in app_js


def test_the_precheck_reads_the_accept_attribute(app_js):
    """One list, and it cannot drift."""
    fn = app_js[app_js.index("function isProbablyAudio") : app_js.index("let BATCH")]
    assert 'getAttribute("accept")' in fn
    assert ".mp3" not in fn, "the extension list was restated in JS"


def test_uploads_are_sequential_and_lock_both_pickers(app_js):
    """A correctness decision, not a performance one: the server appends, so
    parallel uploads would land in nondeterministic order and destroy the
    ordering this feature promised."""
    fn = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    assert "Promise.all" not in fn
    assert '$("#filePick").disabled = true;' in fn
    assert '$("#ytAdd").disabled = true;' in fn


def test_a_cancelled_batch_never_reorders(app_js):
    """The reorder sends a FULL order array. After a cancel, files that never
    arrived have no ids, so it would permute real tracks against positions that
    do not exist."""
    fn = app_js[app_js.index("async function repairOrderIfNeeded") : app_js.index("$(\"#addCancel\").addEventListener")]
    assert "if (b.cancelled) return;" in fn
    assert "if (!b.repaired) return;" in fn


def test_the_reorder_sorts_groups_not_tracks(app_js):
    """One file becomes one OR MORE tracks — split_audio cuts at 50 minutes. The
    parts must stay together and in part order."""
    fn = app_js[app_js.index("async function repairOrderIfNeeded") : app_js.index("$(\"#addCancel\").addEventListener")]
    assert "b.groups.get(file)" in fn
    assert "sortByFilename(b.ok)" in fn


def test_counts_are_files_never_tracks(app_js):
    """She picked FILES, and the part-splitting is pre-existing behaviour she has
    already met on the single-file path."""
    assert "files were added." in app_js
    assert "tracks were added" not in app_js
    assert "of your ${n} files" in app_js


def test_the_single_file_summary_is_untouched(app_js):
    """'1 of your 1 files were added.' is what a naive template produces and it
    is the failure mode this branch exists to prevent."""
    fn = app_js[app_js.index("function renderAddError") : app_js.index("async function retryTransient")]
    assert "} else if (n === 1) {" in fn


def test_unknown_failures_default_to_transient(app_js):
    """Guessing deterministic when it was transient TELLS HER TO CHANGE A FILE
    THAT IS FINE. That is wrong advice, not a slower path to the same place."""
    fn = app_js[app_js.index("function classifyUploadError") : app_js.index("function uploadReasonText")]
    assert fn.rstrip().rstrip("}").rstrip().endswith('return "transient";')


def test_a_cancelled_file_is_in_neither_failure_group(app_js):
    """She stopped on purpose. Classifying her decision as a failure and
    offering to retry it would blur Try again into meaning two things."""
    fn = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    abort = fn[fn.index('e.name === "AbortError"'):]
    abort = abort[:abort.index("BATCH.failed.push")]
    assert "BATCH.cancelled = true;" in abort
    assert "continue;" in abort


def test_the_not_started_group_has_no_reason_and_no_button(app_js):
    """There is no reason beyond her own decision, and inventing one would read
    as blame."""
    assert "You stopped before this one:" in app_js
    assert "You stopped before these ${b.notStarted.length}:" in app_js
    assert "lines(b.notStarted, (f) => f.name);" in app_js


def test_the_in_flight_hedge_says_may(app_js):
    """Verified by observation: the transcode runs to completion after the
    abort, so the track lands. The sentence must keep saying 'may' — do not
    tighten it into a promise that it won't."""
    assert "The one that was still going may still finish — it’ll turn up in your list if it does." in app_js


def test_there_is_one_retry_button_and_it_is_disabled_not_removed(app_js):
    """Removing it destroys it while focused and focus falls to <body> — the
    single most common way a keyboard user gets lost in a flow like this."""
    assert 'btn.id = "addRetry"' in app_js
    assert "if (btn) btn.disabled = true;" in app_js
    assert app_js.count('btn.textContent = "Try again"') == 1


def test_the_add_regions_have_their_roles(index_html):
    assert 'id="addMsg" role="status"' in index_html
    assert 'id="addError" class="msg-box err hidden" role="alert" tabindex="-1"' in index_html


# --- the three job-system ADR seams (that arc is out of scope; these are not) ---

def test_seam_s1_there_is_one_upload_call_site(app_js):
    """uploadOneFile is the ONLY place POST /api/tracks/file is sent. The batch
    loop, the retry round and the n=1 path all route through it, so the eventual
    endpoint swap rewrites one function body and hunts no call sites."""
    assert "async function uploadOneFile(file, { signal, onProgress } = {})" in app_js
    # Exactly one POST to the file endpoint in the whole script, and it is inside
    # uploadOneFile. (The GET at /api/draft and the reorder POST are different
    # paths.)
    assert app_js.count('"/api/tracks/file"') == 1
    fn = app_js[app_js.index("async function uploadOneFile") : app_js.index("async function runBatch")]
    assert '"/api/tracks/file"' in fn
    # onProgress is the seam for PR C's XHR swap; it must survive being unused.
    assert "onProgress" in fn


def test_seam_s2_the_server_tag_beats_the_status_code(app_js):
    """The classifier consults e.data.reason / e.data.retryable BEFORE any status
    code. Without this, a future job-based failure — a bare error with no
    .status — misclassifies as transient and offers a retry that reliably fails,
    breaking success criterion 12 from the server side.

    Asserted structurally AND executably: the reason branch must appear before
    the first status read, and the precedence must actually hold.
    """
    fn = app_js[app_js.index("function classifyUploadError") : app_js.index("function uploadReasonText")]
    assert "if (d.reason)" in fn
    assert "if (d.retryable === true) return \"transient\";" in fn
    assert "if (d.retryable === false) return \"deterministic\";" in fn
    # The reason branch precedes the first status-code read.
    assert fn.index("if (d.reason)") < fn.index("const s = e && e.status;")


def test_seam_s2_precedence_holds_when_evaluated(tmp_path):
    """Extract classifyUploadError and run it under Node if available; otherwise
    assert the source guarantees the precedence. The behavior under test:
    {data:{reason:'x', retryable:false}, status:500} must be 'deterministic'
    (reason wins over a 5xx that status alone would call transient), and
    {data:{reason:'x', retryable:true}, status:400} must be 'transient'
    (reason wins over a 4xx that status alone would call deterministic).
    """
    import shutil
    import subprocess

    from yoto_maker.server.app import STATIC_DIR

    node = shutil.which("node")
    src = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    start = src.index("const UPLOAD_ERROR_CLASS")
    end = src.index("function uploadReasonText")
    snippet = src[start:end]

    if not node:
        # No Node in this environment — the structural test above is the guard,
        # and we still assert the two decisive lines exist in the right order.
        assert snippet.index("if (d.retryable === false)") < snippet.index("const s = e && e.status;")
        pytest.skip("node not available; precedence checked structurally")

    harness = tmp_path / "check.js"
    harness.write_text(
        snippet
        + """
const a = classifyUploadError({ data: { reason: "x", retryable: false }, status: 500 });
const b = classifyUploadError({ data: { reason: "x", retryable: true }, status: 400 });
const c = classifyUploadError({ status: 400 });          // no tag -> status wins
const d = classifyUploadError({});                        // unknown -> transient
if (a !== "deterministic") throw new Error("reason:false did not beat 500: " + a);
if (b !== "transient") throw new Error("reason:true did not beat 400: " + b);
if (c !== "deterministic") throw new Error("day-one 400 regressed: " + c);
if (d !== "transient") throw new Error("unknown default regressed: " + d);
console.log("ok");
""",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(harness)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout


def test_seam_s3_one_progress_setter(app_js):
    """Every #addBar / #addMsg write goes through setAddProgress. No inlined
    width strings at call sites in the batch code."""
    assert "function setAddProgress(pct, msg)" in app_js
    # The loop and the cancel handler call the setter, never write the bar
    # directly. (renderStatus/send flows have their own #sendBar and are
    # unrelated.) No literal "40%" survives as an inlined batch width.
    batch = app_js[app_js.index("async function runBatch") : app_js.index("async function retryTransient")]
    assert '$("#addBar").style.width' not in batch
    assert 'setAddProgress(' in batch
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_multi_upload_markup.py -q`
Expected: all PASS.

- [ ] **Step 3: Full suite**

Run: `python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_multi_upload_markup.py
git commit -m "test: guard Item B's frontend contract

Covers the decisions that regress silently: only the audio input is
multiple, api() re-throws AbortError ahead of the network message, the
sort uses Intl.Collator, uploads stay sequential, a cancelled batch
never reorders, the reorder sorts groups and not tracks, counts are
files, and unknown failures default to transient.

Also guards the three job-system-ADR seams: one upload call site, the
classifier reading the server tag before the status code, and one
progress setter."
```

**Stack B is complete.**

---

# STACK C — release

### Task 19: Version bump and release notes

**Files:**
- Modify: `pyproject.toml:7`, `yoto_maker/__init__.py:3`
- Modify: `docs/RELEASE_NOTES.md`

**This task is not optional. See §Why this PR must bump the version.**

- [ ] **Step 1: Bump**

`pyproject.toml` line 7: `version = "0.1.10"` → `version = "0.1.11"`
`yoto_maker/__init__.py` line 3: `__version__ = "0.1.10"` → `__version__ = "0.1.11"`

- [ ] **Step 2: Release notes**

In `docs/RELEASE_NOTES.md`, change line 1 to `# Yoto Maker v0.1.11`, keep the
three-line description, and insert a new section above the existing
`### Fixed in v0.1.10`. Demote nothing else — the v0.1.10 sections keep their
headings, as the v0.1.9 ones did before them.

```markdown
### 🆕 New in v0.1.11
- **You can add several audio files at once.** Press **📁 Choose audio files**
  and pick as many as you like. They're added one after another, in order by
  file name, and you can move them around afterwards. If one of them doesn't
  work, the rest still get added and Yoto Maker tells you which one it was and
  why.
- **You can stop a long add.** A **Cancel** button now sits beside the progress
  bar. Anything already added stays in your list, and Yoto Maker tells you
  exactly what got in and what didn't.
- **A new "If you need to ask for help" section at the bottom of Settings.**
  It shows the handful of details anyone helping you will ask for. Nothing
  there can be changed by looking at it.

### Fixed in v0.1.11
- **Typing the wrong thing in the Client ID box can't sign you out any more.**
  If you paste something that isn't a Client ID — an email address, say, or a
  web address — Yoto Maker now says so and changes nothing. Before, it would
  save it and sign you out, and the only thing you'd see was an error page on
  Yoto's website.
- **If a bad Client ID is already saved, Yoto Maker now says so plainly** — on
  the Settings screen and next to the Connect button — shows you the whole
  value rather than a shortened version, and gives you a one-press way back to
  the built-in one.
```

Written for the `INSTALL-FOR-MOM.md` reader: no element ids, no "verdict", no
"deny-list", no "AbortController".

- [ ] **Step 3: Full suite and a served-build check**

Run: `python -m pytest tests/ -q` — all green.

Then start the app and confirm the served document carries `?v=0.1.11` on both
`/static/styles.css` and `/static/app.js`. **This is the check that decides
whether any of the above reaches a user.**

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml yoto_maker/__init__.py docs/RELEASE_NOTES.md
git commit -m "chore: bump to 0.1.11 and write the release notes

The version string is the asset cache key (index.html's ?v=__ASSET_V__,
replaced at app.py:704), and this PR is almost entirely app.js. Without
the bump every existing browser keeps serving v0.1.10's script against
v0.1.11's markup — queue item 8's bug with a new payload."
```

---

## Deviations and resolutions

| # | Source says | Plan does | Why |
| --- | --- | --- | --- |
| 1 | Maintainer: two commit stacks, Item A first, Item A revertable independently. Spec §A.6/§B.8: the `.msg-box` extension is shared groundwork sequenced in Item A. | A third **Stack 0** below both, holding the shared extension alone. | The two constraints collide as literally stated: shared groundwork *inside* Item A means reverting Item A breaks Item B. One additive commit at the base satisfies both. Item A's commits are still contiguous and still first. |
| 2 | `interactions.md` §3.6.5: *"do not invent a second error-mapping mechanism"*. | The save refusal raises `AuthError(msg, reason=…)` rather than `HTTPException`. | `HTTPException` serialises to `{"detail": …}` but `api()` (`app.js:22`) reads `data.error` — so before Task 1b an `HTTPException` message **never reached the user** at all. Even now that Task 1b surfaces `detail`, only `AuthError` carries the machine `reason` tag `SIGNIN_ERRORS` reads. The `AuthError` handler (`app.py:117`) already emits `{"error", "reason"}` at 400, the exact shape both gates need and `SIGNIN_ERRORS` already consumes. **The latent bug this once flagged** — `"Please paste a Client ID first."` at `app.py:517` never being visible — **is now fixed by Task 1b** (Stack 0); that line stays unreachable only because the frontend catches empty first. |
| 3 | `interactions.md` §3.6.7: `#connectWarn` *"takes `role="alert"` when blocking (`saved`) and no role when advisory (`env`)"*. §3.6.2's diagram: `env` + invalid *"sign-in still proceeds"*. | `role="alert"` unconditionally in static markup; `env` blocks. | **Both are stale residue from the draft that exempted `env`**, reversed by Mark on 2026-07-21 and re-specced in `overview.md` §13.5 and `interactions.md` §3.6.5. Under uniform blocking there is no advisory state. The reversal is the later and explicit decision; these two sentences were not updated with it. **Flagged rather than silently applied.** |
| 4 | Spec is silent on how the frontend learns which track ids a file produced. | `refreshDraft()` returns the draft; the runner takes a set difference per file. | `POST /api/tracks/file` returns `count` but only the *first* track's view, and moving the endpoint onto the job system is explicitly out of scope. A set difference (not a tail slice) is used because the per-row delete controls are not disabled during a batch. |
| 5 | Spec §B.3.3: `n = 1` failed shows *"the server's message alone, unchanged from today"*; the per-file table gives short reason strings for transient classes. | `n = 1` shows `e.message`; `n ≥ 2` shows the short strings. | For a deterministic 400 these agree — `e.message` *is* the server's sentence. They diverge only for transient failures, where `e.message` is `api()`'s 30-word *"Couldn't reach the Yoto Maker app…"*. Keeping it at `n = 1` is what makes success criterion 10 (*"the single-file path is byte-for-byte what it is today, except that a transient failure now offers Try again"*) literally true. The short strings exist because that sentence repeated on four list lines is unreadable. |
| 6 | Spec §A.2.5: *"Item A introduces no new token, no new utility, and no new rule"* / *"zero new CSS"*. | Two rules: `.msg-box p { margin: 0 0 10px }` and `.msg-box p:last-child { margin-bottom: 0 }`, in Stack 0. | **The zero-CSS claim is true of everything else in Item A** — the status line, the value display, the promoted reset and setting 3 all use only shipped classes, exactly as specced. It is false only for the `.msg-box` paragraph capability, which the spec itself introduces as a change to `.msg-box`: `.setting-confirm p`'s margin reset (`styles.css:345`) is scoped to `.setting-confirm` and does not reach `.msg-box`, so a `<p>` there takes the UA default `1em` inside a 12px-padded box. Two rules is the minimum; they are in Stack 0 because both items need them. |

Two spec statements are **refined rather than deviated from**, in §Verified during
planning: the `await file.read()` cancellation window is effectively unreachable
(the body is buffered before the endpoint runs), and the synchronous transcode
blocks the server's event loop. Neither changes any shipped copy or decision.

---

## Test Plan

**Standing UAT hazards — both have produced false readings on this project:**

1. **Browser cache.** `docs/DEVELOPERS.md` §Hazards. Every observation below is
   worthless against a stale `app.js`. **This PR bumps the version specifically
   so a real user's browser gets the new script** — but during development, a dev
   server serving the same version string across rebuilds will not. Hard-reload
   between builds; verify with `?v=0.1.11` in the served HTML.
2. **A stale server.** The app is single-instance. If an installed `YotoMaker.exe`
   or an earlier `python -m yoto_maker` already owns port 8777, a new dev server
   **prints one line and exits 0** — and UAT then silently measures the old build.
   The tell is `Yoto Maker is already running at http://127.0.0.1:8777`. **Read
   the launch log before testing anything.**

**Fixtures to prepare before starting:**

| Name | What | Used by |
| --- | --- | --- |
| `track1.mp3`, `track2.mp3`, `track9.mp3`, `track10.mp3` | short, valid | §F |
| `Track2.mp3` | same stem, different case | §F.3 |
| `long.mp3` | **over 50 minutes** — forces `split_audio` | §H.4, §I.5 |
| `slow.mp3` | anything ffmpeg takes ≥ 30 s on | §I |
| `cover.jpg` | not audio | §G |
| `broken.mp3` | a text file renamed — server rejects with 400 | §G.2 |

---

### A. Item A — the save gate, on a live session

1. Sign in to Yoto so the header pill reads **Yoto connected**.
2. Settings → Client ID → paste `mandydeogie@gmail.com` → **Save**.
3. Expect: **no confirmation dialog**, three paragraphs in the red box —
   *"That looks like an email address, not a Client ID."* / *"A Client ID is a
   code from Yoto's developer website…"* / **"Nothing was changed, and you're
   still signed in to Yoto."**
4. **The value is still in the input**, and the input is focused.
5. **The pill still reads Yoto connected.** This is the criterion. If it flipped,
   `logout()` ran and the ordering regressed.
6. Sign out. Repeat step 2. The third paragraph must now read **"Nothing was
   changed."** with no *"and you're still signed in"*.
7. Paste `http://127.0.0.1:8777/yoto/callback` → the *web address* message.
8. Paste `some client id` → the *doesn't look like a Client ID* message.
9. Paste `a8OGO6EfbWit5tDUU` (17 chars) → **the confirmation opens**, with
   *"Just so you know: a Client ID is usually 32 letters and numbers…"* as its
   **first** paragraph. Press `Yes, use it` — it saves.

### B. Item A — the already-broken state, per tier

Run all three. **This is the "blocked Client ID on each of the three tiers"
scenario, and it is where the uniform-gate decision is actually exercised.**

**B.1 `saved`.** Put `"yoto_client_id": "mandydeogie@gmail.com"` in
`%LOCALAPPDATA%\YotoMaker\settings.json` and restart.
- Card view: a red box above the ⚙️ link reading *"…because the Client ID saved
  on this computer isn't one."* with a **purple** `Put back the built-in Client ID`.
- `🔗 Connect my Yoto account` is **enabled**. Press it: **no new browser tab
  opens** and no `/api/yoto/login` request is made (check the Network tab). The
  block is still on screen.
- Settings: red dot, headline **"That's an email address, not a Client ID"**, the
  value **in full and unmasked**, **no** `Show the whole thing` button, and
  `Go back to the built-in one` rendered as a primary.
- The input and `Save` are **enabled** — the block is on signing in, never on
  fixing it. Paste the real default and save; everything returns to green.

**B.2 `env`.** `set YOTO_CLIENT_ID=not a client id` and restart.
- Card view: the **two-paragraph** env message, `YOTO_CLIENT_ID` named **twice**,
  and **no button at all** (not a disabled one).
- Settings: red dot, *"Set outside the app, and it isn't a Client ID"*, value in
  full. The `Go back to the built-in one` action is **absent** (it is removed on
  `env`, which is pre-existing and correct).
- Press connect: blocked, no request.

**B.3 `builtin`.** Unreachable in a correct build. Verify the guard instead:
`python -m pytest tests/test_client_id_validation.py::test_the_shipped_default_scores_ok -v`.
To see the copy, temporarily edit `DEFAULT_YOTO_CLIENT_ID` to `"bad@value"`,
restart, confirm the *"the Client ID it came with is the problem"* message with
**no reset button**, then **revert the edit**.

### C. Item A — the deep link

1. From B.1's card view, press `Put back the built-in Client ID`.
2. Settings opens, **scrolled to the Client ID section**, with the reset
   confirmation **already showing** and `Never mind` focused.
3. Press `Never mind` — the confirmation closes and focus returns to
   `Go back to the built-in one`.
4. Press the card-view button again, then `Yes, use the built-in one`. Expect the
   green *"Done — back to the built-in Client ID…"* message and the block gone
   from the card view on return.
5. Press browser **Back** twice. Nothing should double-open a confirmation — the
   intent is one-shot.

### D. Item A — setting 3

1. Settings, scroll to the bottom. Five stacked rows.
2. `Version` matches the footer. `Redirect URL` matches what the app is actually
   serving. `Where Yoto Maker keeps its files` is a real path.
3. With a bad Client ID saved, `Client ID in use` shows the **full** value, not
   `mand…com`. With a good one, it shows the mask and **has no reveal toggle of
   its own**.
4. Nothing in the section is focusable except by the virtual cursor.

### E. Item A — no regression

1. A user with the built-in Client ID sees **no** `#connectWarn`, and step 3 is
   pixel-identical to v0.1.10.
2. Sign in end to end. The 2-second poll runs; confirm with a screen reader (or
   by watching the DOM) that `#connectWarn` is **not re-rendered** on every poll.
3. The reveal toggle still works on a valid `saved` value, still resets on
   entering Settings, and still survives cancelling a confirmation.

### F. Item B — ordering

1. Pick `track1, track2, track9, track10` (select them in a scrambled order in
   the dialog). Expect list order **1, 2, 9, 10** — not 1, 10, 2, 9.
2. The `.tiny` promise line is visible **before** picking.
3. Pick `Track2.mp3` and `track2.mp3` together. They must not straddle a case
   boundary; both land adjacent, in `FileList` order.
4. During the batch, `📁 Choose audio files` and the YouTube `Add` are both
   **disabled**, and re-enabled after. Confirm the YouTube button is also
   disabled during a *YouTube* add and that `📁` is too — the pre-existing
   interleave this closes.
5. `Adding 3 of 4 — track9.mp3` appears in the message line, and the bar
   advances in quarters. **Rows appear one by one** as each file lands.

### G. Item B — a deterministic failure mixed with a transient one

**This is the named scenario, and it is success criterion 12.**

1. Pick five files: `track1.mp3`, `track2.mp3`, `cover.jpg`, `broken.mp3`,
   `track9.mp3`.
2. `cover.jpg` never reaches the network — the pre-check skips it.
3. **While `track9` is uploading, kill the server** (`Ctrl+C`).
4. Expect one `.msg-box err` containing:
   - `2 of your 5 files were added.` (or 3, depending on timing — the count is
     whatever actually landed)
   - `This one didn’t work, but trying again might fix it:` →
     `track9.mp3 — Yoto Maker stopped responding.`
   - **one** `Try again` button, **inside** the transient group
   - `These 2 can’t be added:` → `cover.jpg — That isn’t an audio file.` and
     `broken.mp3 — That file type isn’t supported. Try an MP3, M4A or WAV file.`
   - **no control beside the deterministic group**
5. **The two classes must be in different groups with exactly one button between
   them.** One button total on the whole box.
6. Restart the server. Press `Try again`. `track9` lands; the transient group
   disappears; the summary becomes `3 of your 5 files were added.`; the
   deterministic group and its two files **stay**, still with no button.
7. Focus after the retry: on `#addError` (the `Try again` button is gone).

### H. Item B — a network kill mid-batch, and the ordering repair

**This is the named scenario, and it is success criteria 11 and 13.**

1. Add one YouTube track first. Move it with `▼` so its position is deliberate.
2. Pick `track1, track2, track9, track10`. Kill the server while `track2`
   uploads. Restart it.
3. Expect `track1` in the list, and `track2, track9, track10` in the transient
   group with one `Try again`.
4. Press `Try again`. **All three land.** Expect the final order:
   **the YouTube track wherever she put it**, then `track1, track2, track9,
   track10` — the retried files back in natural position, not appended.
5. **Repeat with `long.mp3` (over 50 minutes) as the retried file.** It becomes
   `long (part 1)`, `(part 2)`… Those parts must land **contiguously and in part
   order** in `long.mp3`'s natural-sort position. If they scatter, the reorder is
   sorting tracks instead of groups.
6. Run a batch with **no failures** and confirm in the Network tab that
   `/api/tracks/reorder` is **never called**.
7. Confirm the pre-existing YouTube track's position **did not move** in any run.

### I. Item B — cancel during a genuinely long transcode

**This is the named scenario, and it is success criteria 14, 15 and 16.**

1. Pick `slow.mp3` alone. Press `Cancel` **during the transcode** (after the
   upload bar has moved, while the message still reads `Adding your file…`).
2. `Cancel` goes **disabled**, the message becomes `Stopping…`, and the bar
   freezes.
3. **The UI must return within a couple of seconds.** `#addProgress` hides,
   `#addError` shows `Stopped. Nothing was added.` and *"The one that was still
   going may still finish — it'll turn up in your list if it does."*, and focus
   lands on the box. **A cancel that leaves her waiting has failed even if it
   eventually works.**
4. **The box must NOT say "Couldn't reach the Yoto Maker app" and must NOT offer
   `Try again`.** Either means Task 11 did not land.
5. **Wait.** The track probably appears anyway. **That is expected** (see
   §Verified during planning) and it is what the sentence exists for.
6. Cancel mid-*batch*: pick five, let two land, cancel during three.
   Expect `Stopped. 2 of your 5 files were added.`, the may-still-finish
   sentence, then `You stopped before these 2:` listing files 4 and 5 **by name,
   with no reason strings and no button**.
7. **Confirm `/api/tracks/reorder` was not called.**
8. Cancel **during a retry round** — the button is there, and it behaves
   identically.
9. If a file genuinely failed *before* the cancel, its transient group and its
   `Try again` are **still there**, alongside the not-started group.

### J. Item B — accessibility and edge cases

1. **Screen reader.** With NVDA or Narrator, run a 4-file batch. Expect four
   polite `Adding n of 4 — …` announcements, then the assertive summary. The
   assertive one jumps the queue, which is correct — it is the outcome.
2. **Keyboard.** Tab to `Try again` and press Enter. Focus must **never** land on
   `<body>`. Same for `Cancel`.
3. **The in-flight landing, on the real app.** §I.5 already covers it. Record what
   you observed — the planning repro says it lands; if it does **not** on the real
   endpoint, the *"may still finish"* sentence is still correct (it says "may"),
   but say so in the PR body.
4. **`#picUploadInput` is still single-select.** Open step 2 → Upload → confirm
   the dialog allows exactly one picture.
5. A single valid file still shows the 40% bar and `Adding your file…`, exactly
   as before — with a `Cancel` button beside it, which is the one addition.

### K. Unit suite

`python -m pytest tests/ -q` — everything green, including the four new files.
Note the running total in the PR body.

### L. Stack 0 — an HTTPException message reaches the user (Task 1b)

1. **Unit.** `python -m pytest tests/test_httpexception_reaches_user.py -q` — both
   halves green: the server emits `{"detail": <str>}` and `api()` surfaces it,
   string-guarded.
2. **In the browser (optional, faithful).** With the app running (mind the two
   standing hazards above — a stale `app.js` will read only `data.error`), open
   the DevTools console and run
   `await api("/api/jobs/definitely-not-a-job").catch(e => e.message)`. Expect
   **`"Job not found"`** — the real `HTTPException` message — not *"Something went
   wrong. Please try again."* This is the one place a developer-register string is
   surfaced by design; Task 1b's copy audit records why (the job-system ADR owns
   its replacement copy).
3. **No regression on the softened path.** Pick an icon for a track normally and
   confirm nothing changed — the softened `"That icon isn't available…"` copy is
   only reachable on a client/library desync, never on the happy path.

---

## For the queue — found during planning (one now folded in)

1. ~~**`HTTPException` messages never reach the user.**~~ **Folded into this PR —
   no longer deferred.** `api()` (`app.js:22`) read only `data.error`; FastAPI's
   `HTTPException` serialises to `{"detail": …}`, so every
   `raise HTTPException(400|404, "…")` in `app.py` (lines 307, 320, 322, 330,
   395, 467, 475, 491, 517, 648, 659) showed the user *"Something went wrong.
   Please try again."* instead of its written message. **Fixed in Stack 0,
   Task 1b** — a single string-guarded `data.detail` fallback in `api()`, chosen
   over a server-side `HTTPException` handler for minimal blast radius. Task 1b's
   copy audit lists all eleven raises and softens the one developer-register
   string the fix newly surfaces (`"Unknown icon"`); `"Job not found"` is flagged
   and left to the job-system ADR's PR A, which owns the *"Yoto Maker restarted"*
   replacement.
2. **`--port` still does not move the OAuth redirect URI** (queue item 2,
   `main.py:59`). Task 9's setting-3 row now **displays** that wrong value, which
   makes item 2 visible for the first time. Not a new defect and not this PR's to
   fix — but the row is a good argument for raising item 2's priority.
3. **`POST /api/tracks/file` blocks uvicorn's event loop for the whole
   transcode** (verified — see §Verified during planning). Nothing else is served
   for minutes at a time. This is the same defect Architect is already holding
   for the job-system migration; it is now measured rather than suspected, which
   strengthens that case.

---

## Docs Impact

- `docs/RELEASE_NOTES.md` — Task 19.
- `docs/BUILDER_QUEUE.md` — mark this row `✅ merged`, then `🚢 released` with
  `gh release view v0.1.11` output pasted per the queue's own rule.
- `docs/design-handoffs/configuration-surface/` — **needs one amendment after
  merge, not before:** `interactions.md` §3.6.2's state-machine diagram and
  §3.6.7's role sentence both still describe the reversed `env`-exemption draft
  (§Deviations, resolution 3). Amend in place with a supersession note, the way
  `tokens.md` §2a was.
- `docs/design-handoffs/audio-add-surface/` — **still does not exist**, by
  decision (spec §B.0), and this PR **grows the surface it would have covered**.
  Spec §B.0 says to mint it *"when the upload surface next grows"*. It just did.
  Recommend filing a Designer row rather than doing it here.
- No change to `docs/DESIGN.md`, `docs/DEVELOPERS.md`, `docs/INSTALL-FOR-MOM.md`
  or `docs/SETUP-YOTO-CONNECTION.md`. `SETUP-YOTO-CONNECTION.md:30`'s redirect URL
  is now echoed in-app, which makes that page more useful, not less accurate.
