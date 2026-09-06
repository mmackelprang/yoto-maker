# Interactions — Save-to-a-folder mode

State machine, focus management, keyboard behavior, announcements and responsive
rules. Copy for every state is in [`copy.md`](copy.md); the reasoning behind each
decision is in [`overview.md`](overview.md).

---

## 1. Markup contract

Appended inside step 3's `<section class="step">`, **after `#connectWarn` and
before `#advRow`**. Nothing above it moves; `#advRow` stays last
(configuration-surface `interactions.md` §1.4).

```html
<!-- The alternative delivery path. ALWAYS RENDERED, in both connection
     states — hiding it in either one would be arbitrary, since saving needs
     no sign-in at all, and configuration-surface §12.4's lesson is that a
     control which vanishes in the state where you want it IS the bug.
     Never disabled by STATUS.yoto.connected. overview.md §4.3, §10.1. -->
<div id="exportRow" style="margin-top:14px">
  <button id="exportBtn" class="btn">📁 Save the files to a folder</button>
  <p class="tiny" style="margin-top:8px">
    You’ll put them on Yoto’s website yourself. You don’t need to be signed in for this.
  </p>
</div>

<div id="exportProgress" class="progress hidden">
  <div class="bar"><div id="exportBar"></div></div>
  <div class="msg" id="exportMsg" role="status"></div>
</div>

<div id="exportError" class="msg-box err hidden" role="alert" tabindex="-1"></div>
<div id="exportDone" class="msg-box ok hidden" tabindex="-1"></div>
<div id="exportNote" class="msg-box info hidden"></div>

<div id="exportActions" class="done-actions hidden">
  <a id="exportReadme" class="btn primary" target="_blank" rel="noopener">📄 What to do next</a>
  <button id="exportOpen" class="btn">📂 Open the folder</button>
</div>
```

Four notes, each load-bearing.

1. **`.tiny` is on the `<p>`, not on the `<button>`.** The same specificity trap
   configuration-surface §12.4 fixed on `#advToggle`: `.tiny`'s
   `color: var(--muted)` (0-1-0) would beat a `.btn`'s own colour rules and grey
   the control out. The wrapper carries the size; the button is left alone. This
   is the construction `index.html:85` already uses.

2. **`#exportRow` has no `.tiny` on the wrapper either** — unlike `#advRow`,
   which is a link. Here the wrapper holds a full-size `.btn` and a `.tiny`
   paragraph, so the size class belongs on the paragraph only.

3. **`#exportError` and `#exportDone` both carry `tabindex="-1"`.** They are
   programmatic focus targets (§4). This matches every `.msg-box` in the settings
   view and `#addError` (`index.html:114`).

4. **`#exportActions` is `.done-actions`, not `.setting-actions`.** It is on the
   card view, and `.done-actions` (`styles.css:260`) is the class step 4 already
   uses for exactly this — a result's follow-on controls. `.setting-actions`'
   `<420px` column rule does not apply here, deliberately (§7).

### 1.1 Render rules

`#exportRow` is **never** touched by `renderStatus()`. No `show()` call, no
`.hidden`, no `disabled`. It is the only control in step 3 with no connection
dependency, and that is the feature.

`app.js:288`'s `$("#sendBtn").disabled = !connected;` is unchanged and gains no
sibling.

---

## 2. State machine

```
                    ┌──────────┐
   page load  ─────▶│   idle   │◀────────────────────────────┐
                    └────┬─────┘                             │
                         │ press 📁 Save the files            │
                         ▼                                    │
                  ┌─────────────┐   refused (no tracks /      │
                  │  checking   │───  no card name)  ─────────┤
                  └──────┬──────┘                             │
                         │ accepted → job started             │
                         ▼                                    │
                  ┌─────────────┐                             │
                  │   working   │  poll /api/jobs/{id} @500ms  │
                  └──┬────┬───┬─┘                             │
             all ok  │    │   │  job error                    │
                     │    │   └──────────▶ ┌────────────┐     │
                     │    │                │   failed   │─────┤
                     │    │ some tracks    └────────────┘     │
                     │    │ failed                            │
                     ▼    ▼                                   │
              ┌────────────────┐                              │
              │  saved         │  (full or partial)           │
              │  + actions     │──── press 📁 again ──────────┘
              └────────────────┘      (new folder, "(2)")

   No cancel transition — see §3.4.
   No terminal state: the button is live in every state.
```

**There is no state in which `#exportBtn` is unavailable**, except the ~seconds
it is disabled while its own job runs (§3.2). Nothing about the connection,
the draft, the Client ID verdict or a previous failure ever removes it.

---

## 3. Pressing the button

### 3.1 On press

1. Clear `#exportError`, `#exportNote`; hide `#exportDone` and
   `#exportActions`. A new run's result must never render beside the previous
   run's.
2. `#exportBtn.disabled = true`, and reveal `#exportProgress`.
3. `POST` the export request.
4. A refusal (no tracks, no card name) comes back as the existing `SourceError`
   shape and renders into `#exportError` — see §3.5. The button re-enables.
5. Otherwise, poll the returned job with the existing `pollJob()`
   (`app.js:80-89`, 500ms), feeding `job.percent` into `#exportBar` and
   `job.message` into `#exportMsg`.

Steps 1–3 are the shape `sendToYoto()` already uses (`app.js:1991-2006`), and
step 5 is the same helper with the same three existing call sites. **No new
polling mechanism.**

### 3.2 While working

- `#exportBtn` is `disabled`. `#sendBtn` is **not** — the two paths are
  independent and there is no reason to block one on the other. (Whether pressing
  both at once is sensible is her business; neither writes to the other's
  output.)
- `#exportMsg` carries `role="status"` and updates per track (`copy.md` §4).
- `#exportProgress` follows the existing `.progress` markup exactly, so the bar's
  `transition: width .3s ease` (`styles.css:235`) is inherited with no new CSS.

### 3.3 On completion

1. Hide `#exportProgress`.
2. Render `#exportDone` from the job result — **only** from the job result.
   Nothing about the folder, its name or its path may be reconstructed in JS
   (`overview.md` §11.3). This is configuration-surface §13.4's rule for the
   redirect URL applied to a second server-owned value, for the same reason.
3. Render `#exportNote` from the result, one paragraph per condition that fired,
   in the fixed order `overview.md` §10.3's table gives: split → converted →
   track over 100 MB → card over 500 MB / 5 hours → card over 100 tracks, then
   the single shared recovery sentence if any card-level ceiling fired
   (`copy.md` §5.9). `.msg-box p` / `.msg-box p:last-child`
   (`styles.css:257-258`) already carry multi-paragraph bodies — no new CSS, and
   the order is fixed in the renderer so two cards with the same conditions never
   read differently.

   **The whole box is omitted when no condition fired.** An empty `.msg-box` has
   12px of padding and a background; on the everyday path it would render as a
   stray grey bar between the result and the buttons.
4. Render `#exportError` **in addition** if the result reports failed tracks
   (§3.6).
5. Set `#exportReadme.href` from the result's URL, with a cache-busting query
   string — the same `+ "?t=" + Date.now()` the label flow uses
   (`app.js:2015`), and required for the same reason: the served path is stable
   across runs.
6. Show `#exportOpen` **only** if the server reported that it can open a folder;
   otherwise omit it from the DOM and append the path line to `#exportDone`
   (`copy.md` §5.5). **Omitted, never disabled** — configuration-surface §3.5.2
   and §13.5.
7. Show `#exportActions`.
8. Move focus to `#exportDone` (§4.1).
9. `#exportBtn.disabled = false`.

### 3.4 There is no Cancel

`yoto_maker/server/jobs.py` has no cancellation of any kind. The `#addCancel`
precedent (`index.html:108`) aborts a frontend `fetch` on the **synchronous**
file-upload path and has no equivalent for a job.

Specifying a Cancel here would require new job-runner capability — an Architect
decision — for a job that is mostly local file copying. `overview.md` §10.2
records the trade and the condition under which it should be revisited.

**Consequence to design around:** a very large audiobook will hold the button
disabled for some seconds with no way out. The per-track progress message (§3.2)
is what makes that tolerable, which is why it is not optional.

### 3.5 Refusals

Rendered in `#exportError` (`role="alert"`), focus moved to it, and the button
left enabled. The two strings are in `copy.md` §3.

**No confirmation is ever shown for this action.** It creates a new folder,
overwrites nothing, and signs nobody out — there is no consequence to accept.
configuration-surface `interactions.md` §3.2's *"never confirm a no-op"* rule
generalises: never confirm something with no cost.

### 3.6 Partial results render two boxes

`#exportDone` (with its count already reduced, `copy.md` §5.1) **and**
`#exportError` (naming the failed tracks, `copy.md` §5.6). Both visible at once.

Focus goes to `#exportError`, not `#exportDone` — the failure is the part she has
to read, and `role="alert"` will interrupt for it anyway (§5).

This is the same shape the multi-file add already produces
(`RELEASE_NOTES.md:39-46`).

---

## 4. Focus

### 4.1 On success

Focus moves to `#exportDone` (`tabindex="-1"`). A screen reader announces the
result sentence, and the next `Tab` lands on `📄 What to do next` — the action
the design wants pressed first (`overview.md` §7.1).

This is configuration-surface `interactions.md` §3.2 step 4's rule (*"move focus
to the `.msg-box` so the outcome is announced"*) applied unchanged.

### 4.2 On failure or refusal

Focus moves to `#exportError`. On a **partial** result this overrides §4.1 — see
§3.6.

### 4.3 `📄 What to do next` opens a new tab

An `<a target="_blank">`, exactly like `#labelOpen`. Focus follows the browser's
own behaviour; nothing is managed. If the browser blocks the popup, the anchor is
still a real link she can click again — which is why it is an anchor and not a
`window.open()` call.

### 4.4 `📂 Open the folder` — no focus move on success, §4.2's rule on failure

**On success, focus does not move.** The window that opens is not the browser's.
Focus stays on the button, which is also the way to open it again. No focus
management, nothing to restore.

Between the press and the folder appearing there is a real gap. The button shows
no spinner and gets no transient "Opened!" state — configuration-surface
`tokens.md` §3a rejected exactly that shape for a copy button (*"its own
transient state and failure path"*).

**On failure it renders into `#exportError` and focus moves there, per §4.2** —
one rule for every failure on this surface, not a second one for this button.
That is load-bearing here rather than merely tidy: `#exportError` sits **above**
`#exportDone` and `#exportActions` in the DOM (§1), so a message triggered from
the reveal button appears *behind* the user's current position and can be off
screen entirely. Moving focus is what takes her to it.

**Two failures, two strings, both specified in `copy.md` §5.5a**
*(added 2026-09-05 — this subsection previously said only that a failure
"renders into `#exportError`", which left Builder to invent the message):*

| Case | What the server found | Message |
| --- | --- | --- |
| (a) | No folder recorded, or the recorded folder is gone | `copy.md` §5.5a(a) — one string for both, because the recovery is identical: press save again. |
| (b) | The folder is there; the OS refused to open it | `copy.md` §5.5a(b) — the failure **plus the full path** in `.mono-value`, so the message is not a dead end. |

**The button stays on screen after (b)** — removing a control the user just
pressed is disorienting, and with the path now rendered a second press costs her
nothing. After (a) the panel is stale anyway and her next action is the save
button above it.

**§5.5 is a different case and keeps its own treatment**: there, the app knows
*before rendering* that it cannot reveal a folder, so the button is never drawn
and the path ships inside `#exportDone`. Known-in-advance omits the control;
failed-at-the-press explains itself.

---

## 5. Announcements

- `#exportMsg` — `role="status"` (polite). Per-track updates during the run.
  Announced without stealing focus, which is correct for a progress line.
- `#exportError` — `role="alert"` (assertive). It is the answer to something she
  just did.
- `#exportDone` — **no role.** Focus is moved to it (§4.1), which is what
  announces it. Giving it `role="status"` as well would announce the same
  sentence twice, which is the double-announcement hazard
  configuration-surface `interactions.md` §4.3 prohibits.
- `#exportNote` — **no role.** It is adjacent to `#exportDone`, which the user
  has just been placed on, and it is reached by the next virtual-cursor movement.
  A second live region in the same block is the same hazard.

**One live region per outcome.** In a partial result the assertive `#exportError`
must land after the focus move, not before, so the alert is not queued behind it
— the ordering rule configuration-surface §4.3 already states for the
`signing_in → connected` transition.

---

## 6. Keyboard

| Key | Context | Behavior |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | Card view | Natural DOM order. No `tabindex` anywhere except the two `-1` focus targets. |
| `Enter` / `Space` | `#exportBtn`, `#exportOpen` | Activate. Native `<button>`; no custom handlers. |
| `Enter` | `#exportReadme` | Follow the link. Native `<a>`. |
| `Escape` | Anywhere in step 3 | **Nothing.** The card view binds no Escape and this feature adds none. There is no dialog and no confirmation to dismiss. |

### 6.1 Tab order in step 3

```
connected      →  #sendBtn  →  #exportBtn  →  [#exportReadme → #exportOpen]  →  #advToggle
not connected  →  #connectBtn  →  #sendBtn (disabled, skipped)
                             →  #exportBtn  →  [#exportReadme → #exportOpen]  →  #advToggle
```

The bracketed pair exists only after a successful run. `#advToggle` remains the
last stop in step 3 in every state — configuration-surface §1.4's rule, unchanged
and still satisfied.

**No `tabindex` is used to reorder anything.** Plain document order produces the
right sequence because the DOM order is the reading order.

### 6.2 Focus ring

Every control added here is a `.btn` or an `<a class="btn">` sitting on
`.step`'s `var(--card)` background. That is **row 1** of configuration-surface
`tokens.md` §4's certified focus-ring table — ring resolves to `--accent`,
4.82:1, and `.btn` is already enumerated there.

**No new row, no `--focus-ring` override, no new measurement.** Verified that
none of these controls can land anywhere else: they are inside `.step`, never
inside `header`, never inside `.setting-confirm`, and never on the update
banner's gradient.

---

## 7. Responsive

`<main>`'s existing `max-width: 720px; padding: 24px 18px 80px` carries all of
this unchanged.

| Width | Behavior |
| --- | --- |
| ≥ 720px | `#exportActions`' two buttons sit on one row with the existing 10px gap. |
| 480–720px | Fluid. `.done-actions` is `flex-wrap: wrap`, so the second button drops beneath the first at its natural width. |
| < 420px | **The `.setting-actions` column rule does not apply here** — it targets `.setting-actions` only, and this is `.done-actions`. The buttons wrap and stay at their natural width, exactly as step 4's label row does today. That parallel is deliberate: the two result rows in this app must behave the same way. |

**Two things to confirm in UAT.**

- **A long folder name in `#exportDone`.** The sentence carries a user-supplied
  card name inside typographic quotes. It is prose, not `.mono-value`, so it
  wraps on word boundaries — confirm it does not push the card wide at 320px.
- **The full path line, when the reveal button is omitted** (`copy.md` §5.5). It
  is `.mono-value`, whose `word-break: break-all` is what guarantees a long
  redirected OneDrive path wraps inside the column instead of overflowing. This
  is the specific regression to look for, because it appears only in a degraded
  state and only when narrow — the same shape of trap configuration-surface
  `interactions.md` §5 flagged for the revealed Client ID.

---

## 8. Motion

None beyond what exists. The panel appears instantly; `#exportBar` inherits
`.bar > div`'s `transition: width .3s ease` (`styles.css:235`) and nothing else
animates.

Consistent with configuration-surface `interactions.md` §6: this app animates
only direct feedback on a user action, and adds nothing for appearance or
navigation.

---

## 9. Lifecycle

### 9.1 Leaving and returning to Settings

Nothing is cleared. The panel describes a **completed past action**, not the
current draft, so it stays true across a view swap. `gotoSettings()` /
`← Back to my card` need no changes.

### 9.2 The draft changes after a successful save

**The panel is left alone**, and this is deliberate rather than unhandled.

`#sendDone` already behaves this way — a green "sent" box survives adding a
track. The panel's sentence and its two buttons all remain literally true: that
folder exists, it holds what the box says it holds, and the instruction sheet
inside it describes its own contents (`overview.md` §6.2). Pressing save again
produces a new folder and a fresh panel (`copy.md` §5.8).

Clearing it on every draft edit would mean wiring the panel to six unrelated
handlers to remove a message that has not become false.

### 9.3 "Start a new card"

`#startOver` **must clear the whole `#export*` block** — hide
`#exportProgress`, `#exportError`, `#exportDone`, `#exportNote` and
`#exportActions`, and drop `#exportReadme.href`.

This is the one case where the panel *does* become misleading: the card it
described is gone, and a stale `📄 What to do next` on a blank draft points at
instructions for a card the user has just discarded. It goes with the same reset
that clears the tracks and the picture.

---

## 10. What this feature deliberately does not add

- **No focus trap, no `inert`, no scrim.** There is no dialog anywhere in it.
- **No confirmation step.** §3.5 — nothing is overwritten and nothing is
  destroyed, so there is no consequence to accept.
- **No `Escape` binding.** §6.
- **No second live region per block.** §5.
- **No `tabindex` for ordering.** §6.1.
- **No new CSS class, no new token, no edit to an existing rule.** Every element
  above uses `.btn`, `.btn.primary`, `.tiny`, `.progress`, `.bar`, `.msg`,
  `.msg-box` (+`.err`/`.ok`/`.info`), `.done-actions`, `.mono-value` and
  `.hidden`, all shipped.
