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

<!-- The REVEAL button's own feedback region, and it must stay below the button
     that raises it. It is NOT #exportError: that box is the SAVE button's
     region and holds a record of the run (a refusal, a partial-save notice, a
     total failure) that must survive a press of "📂 Open the folder".
     §4.4 carries the whole contract. copy.md §5.5a. -->
<div id="exportOpenError" class="msg-box err hidden" role="alert" tabindex="-1"></div>
```

Five notes, each load-bearing.

1. **`.tiny` is on the `<p>`, not on the `<button>`.** The same specificity trap
   configuration-surface §12.4 fixed on `#advToggle`: `.tiny`'s
   `color: var(--muted)` (0-1-0) would beat a `.btn`'s own colour rules and grey
   the control out. The wrapper carries the size; the button is left alone. This
   is the construction `index.html:85` already uses.

2. **`#exportRow` has no `.tiny` on the wrapper either** — unlike `#advRow`,
   which is a link. Here the wrapper holds a full-size `.btn` and a `.tiny`
   paragraph, so the size class belongs on the paragraph only.

3. **`#exportError`, `#exportDone` and `#exportOpenError` all carry
   `tabindex="-1"`.** They are programmatic focus targets (§4). This matches
   every `.msg-box` in the settings view and `#addError` (`index.html:114`).

4. **`#exportActions` is `.done-actions`, not `.setting-actions`.** It is on the
   card view, and `.done-actions` (`styles.css:260`) is the class step 4 already
   uses for exactly this — a result's follow-on controls. `.setting-actions`'
   `<420px` column rule does not apply here, deliberately (§7).

5. **`#exportOpenError` is the last `#export*` element, and `#advRow` is still
   after it.** Appending it here rather than inserting it anywhere above keeps
   every existing position fixed — `#advRow` stays the last child of step 3
   (configuration-surface `interactions.md` §1.4) and the tab order is untouched
   (§6.1), because a `tabindex="-1"` div is not a tab stop.

   **It adds no CSS and no token.** `.msg-box`, `.err` and `.hidden` are all
   shipped, so §10's ledger claim survives verbatim. On the everyday path it is
   one more `.hidden` div: a user who never presses the save button still sees
   exactly two added elements (`overview.md` §13).

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

1. Clear `#exportError`, `#exportNote` **and `#exportOpenError`**; hide
   `#exportDone` and `#exportActions`. A new run's result must never render
   beside the previous run's — and a reveal failure about the *previous* folder
   must never sit under the *new* one's buttons.
2. `#exportBtn.disabled = true`, and reveal `#exportProgress`.
3. `POST` the export request.
4. A refusal (no tracks, no card name) comes back as the existing `SourceError`
   shape and renders into `#exportError` — see §3.5. The button re-enables.
5. Otherwise, poll the returned job with the existing `pollJob()`
   (`app.js:80-89`, 500ms), feeding `job.percent` into `#exportBar` and
   `job.message` into `#exportMsg`. **This call site asks for the retry
   behaviour in §4a.**

Steps 1–3 are the shape `sendToYoto()` already uses (`app.js:1991-2006`), and
step 5 is the same helper. **No new polling mechanism** — §4a adds retrying
*inside* the existing one, requested per call site.

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
§3.6. This covers every failure of the **save** button: a refusal (§3.5), a
partial result (§3.6), a total failure, and lost contact (§4a).

**A failure of the reveal button is the one exception**, and only in *where*:
focus moves to `#exportOpenError` instead, because that is where its message
renders (§4.4). The rule — *the failure takes focus* — is unchanged.

### 4.3 `📄 What to do next` opens a new tab

An `<a target="_blank">`, exactly like `#labelOpen`. Focus follows the browser's
own behaviour; nothing is managed. If the browser blocks the popup, the anchor is
still a real link she can click again — which is why it is an anchor and not a
`window.open()` call.

### 4.4 `📂 Open the folder` — its failures get their own region

> **Ruled 2026-09-05.** A reveal failure renders into **`#exportOpenError`**, the
> region declared in §1 immediately below `#exportActions`. It **never** writes
> into `#exportError`. This subsection is the whole contract; there is nothing
> left for an implementer to choose.

**On success, focus does not move.** The window that opens is not the browser's.
Focus stays on the button, which is also the way to open it again. No focus
management, nothing to restore.

Between the press and the folder appearing there is a real gap. The button shows
no spinner and gets no transient "Opened!" state — configuration-surface
`tokens.md` §3a rejected exactly that shape for a copy button (*"its own
transient state and failure path"*).

#### 4.4.1 Why a region and not a composition rule

The two candidate shapes were a second region, or a rule for composing two
messages inside the shared one. The second region wins on four counts, and the
first is the one that decides it.

1. **The shared region held the sentence that must survive.** After a partial
   save, `#exportError` carries `copy.md` §5.6 — the failed track, and
   *"Everything else is in the folder. The page in the folder lists what's
   actually there."* That second sentence is the **only pointer she has to the
   instruction sheet**, which `overview.md` §10.4 point 3 makes the authority on
   what actually landed and which `copy.md` §6.8 fills with the missing-track
   notice. A reveal failure overwriting it deletes the pointer at the exact
   moment she is trying to reach the folder it points into.
2. **Feedback belongs beneath the control that raised it.** `overview.md` §4.3
   point 1 refused a placement because it would *"make feedback appear below a
   different button"*. A reveal message in `#exportError` makes feedback appear
   **above** a different button. Same defect, other direction.
3. **The two messages have different lifetimes.** `#exportError` holds a record
   of the run and must live until the next run. A reveal message is transient and
   must clear the moment the folder does open. One region cannot express both
   without a flag, and a flag protecting one message from another is a thing that
   gets forgotten in the next edit. **The region deletes that state rather than
   maintaining it.**
4. **It costs nothing.** No CSS, no token, no tab stop, no change to `#advRow`'s
   position, and nothing on the everyday path (§1 note 5).

**Rejected: a composition rule.** Every version of it needs answers this design
does not want to have to give — does the reveal message go above or below the
partial list, does a successful open remove only its own paragraph, does a new
save clear both. That is more contract surface, not less, and each answer is a
place to get it wrong.

**Rejected: a combined string.** That is the composition rule arriving as copy.
`copy.md` §5.5a records the check that neither reveal string needs one.

#### 4.4.2 The rules

| | Rule |
| --- | --- |
| **Region** | `#exportOpenError`, `.msg-box err`, `role="alert"`, `tabindex="-1"`, immediately after `#exportActions` (§1). |
| **Focus on failure** | Moves to `#exportOpenError`. |
| **Focus on success** | Does not move (above). |
| **Cleared by** | (i) a successful open — **unconditionally**, since the region holds nothing else; (ii) the start of a new save run (§3.1 step 1); (iii) `#startOver` (§9.3). Nothing else clears it, ever. |
| **`#exportError` on a reveal press** | **Untouched, in both directions.** Not written, not cleared, not re-focused. |

**The flag is deleted.** `exportErrorIsRevealFailure` (`app.js:2053`) exists only
to keep two messages out of each other's way inside one region. With two regions
there is nothing for it to guard, and it must go rather than be left as dead
state that implies a rule that no longer holds.

**Focus still moves, but it is no longer compensating for a bad position.** §4.2's
rule applied here because `#exportError` sits *above* `#exportDone` and
`#exportActions`, so a reveal message rendered behind the user's scroll position
and could be off screen entirely; the focus move was the thing that took her to
it. `#exportOpenError` is directly beneath the button she just pressed, so it is
already where she is looking. **The focus move stays** — it is what announces the
message to a screen reader, and one focus rule for every failure on this surface
is worth more than a special case — but it is now doing one job instead of two.

#### 4.4.3 The two failures

Both strings are `copy.md` §5.5a and neither changes.

| Case | What the server found | Message |
| --- | --- | --- |
| (a) | No folder recorded, or the recorded folder is gone | `copy.md` §5.5a(a) — one string for both, because the recovery is identical: press save again. |
| (b) | The folder is there; the OS refused to open it | `copy.md` §5.5a(b) — the failure **plus the full path** in `.mono-value`, so the message is not a dead end. |

**The button stays on screen after (b)** — removing a control the user just
pressed is disorienting, and with the path now rendered a second press costs her
nothing. After (a) the panel is stale anyway and her next action is the save
button above it. **Neither case removes or alters `#exportActions`** — see §10's
list of what this feature does not add, and the note there on why (a) does not
tear the panel down.

**§5.5 is a different case and keeps its own treatment**: there, the app knows
*before rendering* that it cannot reveal a folder, so the button is never drawn
and the path ships inside `#exportDone`. Known-in-advance omits the control;
failed-at-the-press explains itself, below itself.

---

## 4a. A poll that fails while a job is running — retry, then say so honestly

*(Inserted rather than numbered §4.5: this is not a focus rule. The letter-suffix
convention is the package's own — `copy.md` §5.5a, `mockups/step-3.md` §7a.)*

> **Ruled 2026-09-05.** The defect: a dropped status poll rendered `copy.md`
> §5.7, which opens *"Yoto Maker couldn't save the files"* and closes *"Nothing
> was saved"*. **Neither is knowable in that state**, and both are false in the
> direction that makes her act — told nothing happened, she presses save again
> while a folder is being written.

**Three rules, in order.**

**(1) Retry first, and retry silently.** A failed poll is retried before anything
user-visible changes. During the retry window the progress bar and the last
`#exportMsg` line stay **exactly as they were** — no "reconnecting…", no new
string, no visual change of any kind. A blip that resolves must leave no trace to
read; and the progress line's job is liveness (§3.2), which the last real message
serves better than a technical one.

The window has two bounds and Builder tunes between them against a real card:

- **Long enough** to ride out a stall on a machine that is busy writing hundreds
  of megabytes. A couple of seconds is not enough.
- **Short enough** that a frozen bar does not read as a hung app — which is the
  exact failure `index.html:102-106` and §3.4 built the per-track message to
  prevent. **Past ~30 seconds the cure is the disease.**

No number is specified here on purpose; see the closing note of this file.

**(2) When the retries are spent, render `copy.md` §5.10** into `#exportError`,
`.msg-box err`, `role="alert"`, focus moved there per §4.2. Then:

- **Hide `#exportProgress`.** A bar left on screen says the app is still
  watching. It is not.
- **Re-enable `#exportBtn`.** §5.10's third paragraph tells her to press it.
- **Render no success box and no actions.** No result arrived, so there is
  nothing to render them from — and §5.10 is written for a user who has no
  buttons, naming *"a page called 'What to do next'"* in words because that is
  her only route to the sheet.

**(3) The boundary is whether a job id exists.** `copy.md` §5.10's table is
normative:

| Failure | Renders |
| --- | --- |
| `POST /api/export` never returned a job id | §5.7, unchanged — *"Nothing was saved"* is true, no job started |
| A refusal (no tracks / no card name) | §3, unchanged |
| The job itself reported an error | §5.7, unchanged — the app was told the outcome |
| **A poll failed after a job id existed** | **§5.10** |

Blurring that line re-introduces the defect from the other side: §5.7 stops being
true, or §5.10 starts hedging about a failure the app actually observed.

### 4a.1 The retry is opt-in per call site, and this is a design rule

`pollJob()` has four call sites. **Retrying must be requested by the caller, not
imposed by the helper**, because the same transport event does not mean the same
thing at all four:

| Call site | What a failed poll means | Opts in? |
| --- | --- | --- |
| `saveToFolder()` `app.js:2231` | *I don't know the outcome* | **Yes** — §5.10 |
| `sendToYoto()` `app.js:1995` | *I don't know the outcome* | **Designed yes, NOT SHIPPED** — `copy.md` §9's banner. The maintainer took §9.1's fallback on 2026-09-05: verifying a send-path retry needs a live authenticated send against a real Yoto account. It keeps today's generic transport line. |
| `doUpdate()` `app.js:160` | *The app is restarting — this is the expected end* | **No.** It already catches every poll failure and reports success (`app.js:167-171`). Retrying would freeze a bar for the whole window before showing a message that was already right. |
| `addYouTube()` `app.js:1251` | *I don't know the outcome* | **No, deliberately.** Its message asserts nothing false, and the thing left uncertain is the track list on the same screen. `copy.md` §9.3 records why this is a later job. |

**The send path's string is `copy.md` §9**, and §9.1 carries why it is in this
package and what declining it would give up. **It was declined — see §9's
banner and item 5 of §11; the rules below are what the follow-up implements, not
what shipped.** Its rendering rules are the save
path's — hide `#sendProgress`, re-enable `#sendBtn`, render no success box —
with one difference, and it follows from the shipped markup rather than from a
choice made here: `#sendError` carries neither `role` nor `tabindex`
(`index.html:195`), so **nothing is announced and focus does not move.**
Recorded in `copy.md` §9.3 as a pre-existing gap this package stands next to
rather than closes.

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
- `#exportOpenError` — `role="alert"` (assertive). It is the answer to a button
  she just pressed, exactly as `#exportError` is.

**One live region per outcome.** In a partial result the assertive `#exportError`
must land after the focus move, not before, so the alert is not queued behind it
— the ordering rule configuration-surface §4.3 already states for the
`signing_in → connected` transition.

**Two `role="alert"` regions in one block is not a violation of that rule, and
the reason is the word *outcome*.** `#exportError` announces the save's outcome,
at the moment the save ends. `#exportOpenError` announces a button press's
outcome, at a later moment the user chose. They can never fire together: the only
way to reach the reveal button is from a rendered result, which happened first.
The hazard §4.3 prohibits is **two regions announcing one event** — which is why
`#exportDone` and `#exportNote` still get no role, and why nothing here changes
that.

---

## 6. Keyboard

| Key | Context | Behavior |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | Card view | Natural DOM order. No `tabindex` anywhere except the three `-1` focus targets. |
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

**`#exportOpenError` adds no tab stop** and does not appear in the sequence
above. It is a `tabindex="-1"` div: reachable by the focus move in §4.4.2 and by
the virtual cursor, never by `Tab`. That is what lets §1 append it after
`#exportActions` without touching the order this table fixes.

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
`#exportProgress`, `#exportError`, `#exportDone`, `#exportNote`,
`#exportActions` **and `#exportOpenError`**, and drop `#exportReadme.href`.

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
- **No two live regions for one outcome.** §5 — which is the rule
  `#exportOpenError` satisfies rather than the one it breaks.
- **No `tabindex` for ordering.** §6.1.
- **No new CSS class, no new token, no edit to an existing rule.** Every element
  above uses `.btn`, `.btn.primary`, `.tiny`, `.progress`, `.bar`, `.msg`,
  `.msg-box` (+`.err`/`.ok`/`.info`), `.done-actions`, `.mono-value` and
  `.hidden`, all shipped. **`#exportOpenError` and every string added on
  2026-09-05 hold this unchanged.**
- **No teardown of the panel after a reveal failure of type (a).** The success
  box and both buttons stay. The panel describes a **completed past action** and
  is still true about it — the files were saved; the folder was moved, deleted or
  forgotten afterwards — and §9.2's rule is that the panel is left alone while
  its sentence remains true. Removing controls the user just pressed is the
  disorientation §4.4.3 already rejects for (b), and doing it for (a) only would
  need a rule for a state nobody has yet observed. Deliberately left as it is;
  revisit if UAT produces a real (a).

---

## 11. Deliberately unspecified *(added 2026-09-05)*

Four things a reader might expect to find above and will not. Each is left open
on purpose, and each says who owns it.

1. **The retry count and the retry window** (§4a rule 1). The design fixes the
   two bounds — long enough to ride out a busy machine, under ~30 seconds — and
   the shape (silent, no visual change). The number between them is a
   **measurement against a real card on a real machine**, which is Builder's to
   take in UAT and not a thing a spec can assert from a desk.

2. **What `📄 What to do next` does after a reveal failure of type (a).** The
   folder is gone, so the sheet route has nothing to serve and the new tab shows
   the browser's own error page — outside every region this document governs. It
   is a real gap and it is **not** closed here: closing it means a server-side
   response in the app's voice, which is a route-shape decision (Architect) and a
   new page's worth of copy. Recorded so it is found deliberately rather than
   discovered by a user. Low frequency: it needs a folder deleted or a server
   restarted between a save and a press.

3. **Whether `#sendError` should become a live region.** `copy.md` §9.3 declines
   it and says why — it changes announcement behaviour for every shipped send
   failure and deserves its own pass. This package adds a message to a silent
   region knowingly, and no worse announced than the messages already there.

4. **Whether the YouTube add path should carry §5.10's shape.** §4a.1 declines
   it for this PR; `copy.md` §9.3 carries the reasoning. It is a follow-up with a
   real user benefit and no urgency.

5. **When the send path gets §9's message.** *(Moved here 2026-09-05, out of the
   "now settled" line below.)* Designer ruled it into this package and the
   maintainer took `copy.md` §9.1's stated fallback instead: verifying a
   send-path retry needs a live authenticated send against a real Yoto account,
   which is exactly what this feature exists to avoid needing. So §9 is
   **written and unshipped**, `#sendError` keeps today's generic transport line,
   and the duplicate-card protection is knowingly given up until a follow-up
   ships it. The string, the argument and the rendering rules are all already
   written — §9, §9.1, §9.2 and §4a.1 — so the follow-up is implementation, not
   design.

**What is *not* on this list, because it is now settled:** which region a reveal
failure renders into (§4.4), and what the app may claim when it loses contact
with a running job (§4a, `copy.md` §5.10). **Whether the send path is *in* was
on this line until 2026-09-05 and is now item 5 above** — it was named settled
in the section whose whole job is to list what is still open, which is the drift
this file's own §1 note about stale claims exists to catch.
