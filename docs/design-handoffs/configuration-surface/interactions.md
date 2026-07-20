# Interactions — Configuration surface

State machines, focus management, keyboard behavior, and responsive rules.
Copy for every state is in [`copy.md`](copy.md).

---

## 1. View switching

### 1.1 Enter

Triggered by: header pill click, footer `Settings` link, step 3's `⚙️` link
(§1.4 — its text is state-dependent as of 2026-07-20), or a `#settings` hash on
load / `hashchange`.

1. Record the element that triggered it in a module-level `returnFocusTo`.
   (For a hash-driven entry with no opener, leave it `null`.)
2. Set `location.hash = "settings"` if it isn't already. The `hashchange`
   handler is the single place that performs the swap — every entry point just
   sets the hash. One code path, so Back/Forward and clicks cannot diverge.
3. `#cardView` → `.hidden`; `#settingsView` → visible.
4. `window.scrollTo(0, 0)`. The card view may be scrolled far down (a long track
   list); landing mid-page on a fresh view is disorienting.
5. `document.title = "Settings · Yoto Maker"`.
6. Move focus to `#settingsTitle` (`<h2 tabindex="-1">`). Screen readers
   announce "Settings, heading level 2", which is the correct orientation
   message. Sighted keyboard users land at the top of the new view.
7. Kick off the account check (§2.1).

### 1.2 Exit

Triggered by: `← Back to my card`, browser Back, or any hash change away from
`#settings`.

1. `history.back()` if the hash was pushed by us and Back would land on the card
   view; otherwise `location.hash = ""`. Simplest correct implementation:
   `← Back to my card` calls `history.back()` when
   `history.state?.fromCard === true`, else sets the hash. Planner may simplify
   to always setting the hash — an extra history entry is acceptable; a Back
   button that escapes the app is not.
2. `#settingsView` → `.hidden`; `#cardView` → visible.
3. `document.title = "Yoto Maker"`.
4. Focus `returnFocusTo` if it's still in the document, else `document.body`.
5. Refresh the card view's status (`refreshStatus()`), since the user may have
   just connected or disconnected. Step 3's `#connectRow` and `#sendBtn`
   disabled state must reflect reality on return.

### 1.3 No focus trap

`.hidden` is `display: none !important`, which removes the hidden view from the
tab order, the accessibility tree, and browser find-in-page. No `inert`, no trap,
no scrim. This is the main accessibility argument for the view swap over a
modal — see `overview.md` §3.1.

---

### 1.4 The step-3 entry point — always rendered (amendment, 2026-07-20)

Required by [`overview.md` §12.4](overview.md). This is the only behavioral
change in that amendment; everything else is CSS, copy and one attribute.

#### Markup

`#advRow` moves **out of `#connectRow`** and becomes the **last child** of step
3's `<section class="step">`, after `#sendDone`.

```html
<!-- ...#sendProgress, #sendError, #sendDone... -->
<div id="advRow" class="tiny">
  <a href="#settings" id="advToggle">⚙️ Connect a different Yoto account</a>
</div>
```

Three structural notes, each load-bearing:

1. **Last child, not before `#sendBtn`.** Ahead of the primary button it would
   push `🚀 Send to Yoto` down and take a tab stop before it — a cost paid on
   every card-making visit for a control used twice ever. Last child also means
   its position never shifts as `#sendProgress` / `#sendError` / `#sendDone`
   appear and disappear, so the user learns one location.
2. **It lands directly beneath `#sendError` on a failed send.** That adjacency
   is the follow-the-symptom path `overview.md` §5.1 claimed for the pill and
   never had — the pill is at the top of the page, the error is at the bottom of
   step 3, and the user's eyes are on the error.
3. **`.tiny` moves to the wrapper; the anchor is left bare.** On the anchor,
   `.tiny`'s `color: var(--muted)` (0-1-0) beat `a { color: var(--accent-dark) }`
   (0-0-1), so the link rendered grey and read as a caption. On the wrapper it
   sets only the 13px size, and the anchor takes accent purple by inheritance-free
   direct rule — 7.20:1 on `--card`, underlined, obviously a link. **This is the
   exact construction the footer's `#settingsLink` already uses**, and it adds no
   CSS.

#### Render rule

One line in `renderStatus()`, beside the two `show()` calls already there:

```
#advToggle text  ←  connected ? "⚙️ Connect a different Yoto account"
                              : "⚙️ Yoto connection settings"
```

Verbatim strings and their rationale in [`copy.md` §1a](copy.md). `#advRow`
itself is **never** hidden — no `show()` call, no `.hidden`. The whole point of
the amendment is that this control does not disappear.

Note that `renderStatus()` currently also does `show($("#connectRow"), !connected)`.
After the move, that call no longer reaches `#advRow`, which is the fix.

#### Behavior

Unchanged from today: it is an `<a href="#settings">` whose click handler calls
`gotoSettings(e.currentTarget)` (§1.1). It is therefore already an entry point in
the sense §1.1 defines — including recording itself as `returnFocusTo`, so
`← Back to my card` returns the user to the link she came from, at the bottom of
step 3, exactly where she left. That return behavior is worth stating because it
is now reachable in the connected state for the first time.

#### Tab order (card view)

Step 3's order becomes, by state:

```
connected      →  #sendBtn  →  #advToggle
not connected  →  #connectBtn  →  #sendBtn (disabled, skipped)  →  #advToggle
```

In both states the primary action comes first and the link is the last stop in
step 3. No `tabindex` anywhere; plain document order.

`#advToggle` is an `<a>` on `--card` (inside `.step`), which is **row 1** of
`tokens.md` §4's focus-ring table — `--accent` at 4.82:1, already certified. No
new row and no `--focus-ring` override.

---

## 2. Setting 1 — Your Yoto account

### 2.1 State machine

```
                      ┌──────────────────────────────────────┐
     enter view  ───▶ │            checking                  │
                      └──────────────────────────────────────┘
                          │         │          │         │
              connected ◀─┘         │          │         └─▶ unknown
                                    ▼          ▼            (offline)
                             not_connected   broken
                                    │          │
        ┌───────────────────────────┴──────────┴───────────────┐
        │                                                      │
   (not_connected:                                    (connected/broken/
    straight to Yoto)                                  unknown: confirm first)
        │                                                      │
        │                                              ┌───────▼────────┐
        │                                              │  confirming    │
        │                                              └───────┬────────┘
        │                                        "Yes, sign in again"
        │                                                      │
        └──────────────────────┬───────────────────────────────┘
                               ▼
                     ┌───────────────────┐
                     │    signing_in     │◀── polling /api/status every 2s
                     └───────────────────┘
                        │     │      │
              success ──┘     │      └── 3 min elapsed ─▶ timed_out
                              │
                         Cancel pressed ─▶ back to prior state
                              │
                        ▼ (success)
                       connected
```

### 2.2 On entering the view

`POST /api/yoto/check` (`overview.md` §7.5) fires immediately. Until it
resolves, the section shows `checking` with the button **disabled**.

- The check is timeboxed at **8 seconds** client-side. Exceeding it → `unknown`.
- On `unknown` the button is **re-enabled**, not disabled. An offline user may
  still legitimately want to start a sign-in (she might be about to fix her
  Wi-Fi). Never dead-end her because we couldn't reach a server.
- The check is **not** re-run on every render — only on view entry and after a
  sign-in completes. It's a network round trip; polling it would be rude.

### 2.3 Confirmation flow

For states `connected`, `broken`, `unknown`:

1. Click the primary button → `#accountActions` gets `.hidden`,
   `#accountConfirm` loses it. (Primitive rule §4.3.3 — never two live choice
   sets at once.)
2. Focus moves to `#accountConfirmNo` (**"Never mind"**, the safe option).
   Deliberate: focus starts on the way out, not the way through. A user who
   presses Space or Enter reflexively must not disconnect her account.
3. **Escape** dismisses the confirmation and returns focus to the primary
   button. This is the only Escape binding on the surface (`overview.md` §5.3).
4. "Never mind" → same as Escape.
5. "Yes, sign in again" → §2.4.

Tab order within the confirmation is `Never mind` → `Yes, sign in again`, i.e.
cancel is both focused first and reachable first.

For state `not_connected`, the confirmation is skipped entirely — the button
goes straight to §2.4.

### 2.4 Signing in

1. `POST /api/yoto/logout` — only if currently connected. This is what makes one
   button serve both intents: the sign-out is folded into the sign-in, so the
   user never has to know they're two operations.
2. `GET /api/yoto/login` → `window.open(url, "_blank")`.
3. Enter `signing_in`: status line updates, primary button disabled and
   relabelled `Waiting for Yoto…`, `Cancel` appears beside it.
4. Poll `/api/status` every 2s.
   - `yoto.connected === true` → clear the interval, run a fresh
     `POST /api/yoto/check` to confirm it actually works, then → `connected`
     and show the success message.
   - **3 minutes elapsed → clear the interval** and enter `timed_out`.
   - `Cancel` pressed → clear the interval, return to the previous state, show
     the cancel message.

**Every exit from this state must clear the interval.** This is the fix for the
pre-existing leak at `app.js:466-469` (`overview.md` §7.6); apply it to
`connectYoto()` too so step 3 benefits.

5. If `window.open` returns `null` (popup blocked), do **not** enter
   `signing_in`. Instead show, in the section's `.msg-box info`, a real link the
   user can click:
   > Your browser stopped the Yoto window from opening.
   > [Open Yoto's sign-in page ↗](#)

   Rendering the URL as an anchor is the only reliable recovery; a message that
   just says "allow popups" is not actionable for this audience.

### 2.5 `timed_out`

Status line returns to whatever it was before, and the `timed_out` message
(`copy.md` §3) appears. It deliberately covers both possibilities — she may have
completed the sign-in successfully and just taken longer than three minutes —
by telling her to press the button again, which will re-check.

---

## 3. Setting 2 — Yoto Client ID

### 3.1 State machine

```
   ┌─────────┐   ┌────────┐   ┌──────┐
   │ builtin │   │ saved  │   │ env  │  ← from status.yoto.client_id_source
   └────┬────┘   └───┬────┘   └──┬───┘
        │            │           └── input + Save disabled;
        │            │               reset action hidden;
        │            │               explanation shown. Terminal.
        │            │
        │  "Go back to the built-in one" ──▶ confirm_reset ──▶ saving ──▶ builtin
        │            │
        └──── Save (non-empty) ─────────────▶ confirm_save ──▶ saving ──▶ saved
```

### 3.2 Save

1. Trim the input. Empty → show `Please paste a Client ID first.`, focus the
   input, stop. **No confirmation for an empty save** — never confirm a no-op.
2. Non-empty → show `#clientIdConfirm` with the save copy; hide the section's
   actions. Focus `Never mind`. Escape / `Never mind` dismisses and returns
   focus to `Save`.
3. `Yes, use it` → `POST /api/yoto/client-id`. Disable the input and both
   confirm buttons while in flight.
4. On success: clear the input, re-read `/api/status`, re-render **both**
   sections (the account section is now `not_connected`, per `overview.md` §7.3),
   show the success message, and move focus to the Client ID section's
   `.msg-box` (`tabindex="-1"`) so the outcome is announced.
5. On failure: show the error, leave the input's value intact so nothing the
   user pasted is lost, re-enable everything, focus the input.

### 3.3 Reset

Same shape as §3.2 with the reset copy, calling `DELETE /api/yoto/client-id`.
Only reachable when `client_id_source === "saved"`.

### 3.4 The `env` state

Input and Save are `disabled`; the reset action is absent from the DOM (not
merely hidden — there is nothing for it to do). The explanatory `.tiny` line
sits below the disabled controls.

This is the one state where the surface tells the user she cannot do the thing
she came to do. It does so plainly, explains why, and says who can fix it —
rather than silently accepting a value that `resolve_client_id()` would ignore.

**Amendment 2026-07-20 — the value block is exempt from this state's
disabling.** `#clientIdCurrent` and its toggle are **shown and fully enabled**
when `client_id_source == "env"`. They are read-only; there is nothing to
disable. See [`overview.md` §11.4](overview.md) for why this is the state where
the value matters most — it is the only one where the user cannot discover it
anywhere else.

Note the existing env `.tiny` note reads *"…it won't be used while the one above
is set."* With the value block inserted above the input, **"the one above" gains
a literal on-screen referent** and becomes more concrete. The string is unchanged
and still true.

---

### 3.5 The value in effect, and its disclosure — NEW (amendment, 2026-07-20)

Specified by [`overview.md` §11](overview.md). Copy in
[`copy.md` §4](copy.md); CSS in [`tokens.md` §3a](tokens.md).

#### 3.5.1 Markup

Nested inside the existing `#clientIdBody`, **above** the `Paste a…` label.
Nothing outside `#clientIdBody` changes.

```html
<div id="clientIdCurrent" class="hidden" style="margin-bottom:14px">
  <p class="tiny">The one you’re using now</p>
  <div class="row wrap" style="margin-top:6px">
    <span class="mono-value grow" id="clientIdValue"></span>
    <button class="btn small" id="clientIdReveal"
            aria-expanded="false" aria-controls="clientIdValue">Show the whole thing</button>
  </div>
</div>
```

Inline margins match the file's existing convention at `index.html:253` rather
than introducing a class for one gap.

#### 3.5.2 Render rules

`renderClientId()` decides all of this from `STATUS.yoto`:

| Condition | Block | Toggle |
| --- | --- | --- |
| `client_id_source === "builtin"` | hidden | — |
| `client_id_full` is null / absent | shown, mask only | **omitted** |
| `client_id_masked === client_id_full` | shown, value only | **omitted** |
| otherwise (`saved` / `env`) | shown | shown |

Row 2 is the version-skew case (a frontend newer than its server). Degrade to
the mask alone rather than rendering a toggle that cannot do anything — the same
graceful-drop discipline already applied at `app.js:499-508`.

Row 3 is the short-value case: `mask_client_id()` returns the input unchanged at
≤8 characters (`config.py:88-89`), so a user who pasted something short or wrong
sees the whole value already. Offering to "show the whole thing" when the whole
thing is on screen is a lie the frontend can detect without duplicating the
server's length rule — **compare the two strings, never re-implement the
threshold.**

If `client_id_masked` is also missing, hide the block entirely. The status line
still carries the state, so nothing is lost.

#### 3.5.3 Toggle behavior

Synchronous. Both strings are already in `STATUS`; **the toggle makes no network
request and has no failure mode** (`overview.md` §7.8).

| From | Click | To |
| --- | --- | --- |
| collapsed | → | `#clientIdValue` ← `client_id_full`; label ← `Show the short version`; `aria-expanded="true"` |
| expanded | → | `#clientIdValue` ← `client_id_masked`; label ← `Show the whole thing`; `aria-expanded="false"` |

**Focus never moves.** The button stays focused across the toggle; the content
it controls is adjacent, and the button is also the way back. No focus
management, no restoration, nothing to get wrong — a direct benefit of choosing
a disclosure over a modal-ish reveal.

#### 3.5.4 Persistence — no auto-hide

**The revealed state persists until the user collapses it or one of the three
resets below fires. It does not time out.**

An auto-hide timer is the password-field reflex, and it is wrong twice over
here. It defends against a bystander reading the screen — a threat that does not
exist for a value printed in the user's own sign-in URL and on a public
dashboard. And it would **break the one task the feature exists for**: the user
is mid-comparison against another screen, or reading the string aloud over the
phone, and the value would vanish under her. It would also flip `aria-expanded`
with no user action, which is an unannounced state change a screen reader user
has no way to anticipate — a real defect traded for theatre.

Reset to collapsed on exactly three events, tracked in a module-level
`clientIdRevealed` flag that `renderClientId()` honors:

1. **Entering the settings view** (§1.1) — a fresh view starts in its default
   state, consistent with the existing `scrollTo(0,0)` and account re-check.
2. **A successful save or reset** — the value has changed; continuing to display
   the previous revealed string would be actively wrong.
3. **Source becoming `builtin`** — the block is removed. (Subsumed by 2 in
   practice; listed so the rule is complete.)

**Explicitly not a reset:** cancelling a confirmation, or any `refreshStatus()`
that did not change the value. `closeClientIdConfirm()` calls `renderClientId()`
to restore the input and actions (`app.js:565`); without the flag that call
would silently collapse a reveal the user had opened, for no reason she caused.
The flag exists to prevent precisely that.

#### 3.5.5 While a confirmation is open

**The toggle stays enabled** — unlike the input, Save, and the reset action,
which are all disabled per the one-live-choice-set rule. The toggle commits
nothing, so that rule does not reach it; see the scope clarification at
[`overview.md` §4.3.3](overview.md).

This is a deliberate behavior, not an oversight to be tidied up: a user reading
*"Yoto Maker will start using the Client ID you pasted"* has an obvious next
question — *"what is it using now?"* — and this is the control that answers it.

#### 3.5.6 Accessibility contract

**Pattern: disclosure.** `aria-expanded` on the button, `aria-controls` naming
the region whose content changes.

`aria-pressed` is **rejected.** A toggle-button role would announce "pressed" /
"not pressed", which describes a control that is switched on — it says nothing
about whether the text beside it is long or short. `aria-expanded` describes
exactly what changed.

**Accessible name in both states** — the visible label, no `aria-label`, no
`title`. The name is the *action*; `aria-expanded` is the *state*:

| State | Announced |
| --- | --- |
| collapsed | `Show the whole thing, button, collapsed` |
| expanded | `Show the short version, button, expanded` |

The label changes with the state, which is the deliberate choice over the
constant-label variant of this pattern. A constant `Show the whole thing` while
the whole thing is already displayed is straightforwardly confusing to a sighted
user, and the sighted user is the majority case here. The pairing reads
correctly because a button label names an action and a state names a state:
"show the short version" (what pressing does) + "expanded" (where we are) is
coherent, not contradictory.

**On toggle, a screen reader announces the `aria-expanded` change and nothing
else.** No live region on `#clientIdValue`. Deliberate, and required by §4.3 of
this file: `.setting-status` in this section already carries `role="status"`,
and a second live region in the same section is exactly the double-announcement
hazard that rule prohibits. A user who wants the value reads it with the virtual
cursor — where she can also arrow through it character by character, which is
what transcription needs and what a single live-region utterance of 32 random
characters would not give her.

`aria-controls` has patchy screen-reader support. It is included because it is
the correct markup and costs nothing; **no behavior may depend on it.**

**The value is selectable.** Plain text, no `user-select: none`, and
`word-break` inserts no characters — a selection yields the exact string
(`tokens.md` §3a).

---

## 4. Keyboard

| Key | Context | Behavior |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | Settings view | Natural DOM order. Card view is `display:none`, so it's out of the tab order entirely. |
| `Enter` / `Space` | Any `.btn` | Activate. Native `<button>` behavior — no custom handlers. |
| `Enter` | Client ID input | Same as clicking `Save`. Matches `#ytUrl` at `app.js:519`. |
| `Enter` / `Space` | `Show the whole thing` | Toggle the value between short and full. Native `<button>`; focus does not move. *(amendment, 2026-07-20)* |
| `Escape` | Value revealed, no confirmation open | **Nothing.** Escape does not collapse the reveal — see below. *(amendment, 2026-07-20)* |
| `Escape` | Confirmation open | Dismiss it, return focus to the button that opened it. |
| `Escape` | Anywhere else in settings | **Nothing.** See `overview.md` §5.3 — a page, not a dialog, and the user may be mid-paste. |
| `Alt+←` / browser Back | Settings view | Returns to the card view via `hashchange`. |

### 4.1 Tab order in the settings view

```
← Back to my card
  → [account] primary button  → [account] Cancel (signing_in only)
  → [client-id] Show the whole thing          (saved / env only)
  → [client-id] input → Save                  (skipped when env — both disabled)
  → [client-id] Go back to the built-in one   (saved only)
```

When a confirmation is open, that section's own actions are `.hidden` and
therefore skipped; the confirmation's two buttons take their place in sequence.

**Amendment 2026-07-20.** The reveal toggle takes its position from natural DOM
order — it precedes the input because it sits above it (§3.5.1). **No `tabindex`
anywhere**; the block is plain document order.

It is also the one control in this section that remains focusable while a
confirmation is open (§3.5.5), so with the save confirmation showing, the order
through the Client ID section is:

```
Show the whole thing → Never mind → Yes, use it
```

Cancel is still the first control inside the confirmation and still focused on
open, so §2.3's safety property — *reflexive Enter or Space must not commit* —
is unaffected. The toggle sits ahead of the confirmation rather than inside it,
and pressing it commits nothing.

**Escape does not collapse the reveal.** Escape's one binding on this surface is
dismissing a confirmation (`overview.md` §5.3), and overloading it would mean a
user with both a confirmation open and a value revealed cannot predict which one
a keypress hits. The toggle is its own way back.

### 4.2 Focus visibility

Global `:focus-visible` ring — see [`tokens.md`](tokens.md) §2. This fixes a
pre-existing gap: **no button anywhere in Yoto Maker has a visible focus
indicator today.** Non-negotiable for this surface, since it is the screen a
user reaches when something is already wrong.

### 4.3 Announcements

- `.setting-status` carries `role="status"` (polite). State changes are
  announced without stealing focus — correct for a status line that updates
  during a 2-second poll.
- `.msg-box` carries `role="alert"` (assertive). Action results interrupt,
  because they're the answer to something the user just did.
- Never both for the same event. The `signing_in` → `connected` transition
  updates the status line *and* shows a success message; the status line update
  must land first so the assertive alert isn't queued behind it.
- **Amendment 2026-07-20:** the Client ID value (`#clientIdValue`) is **not** a
  live region. Its section already has one (`#clientIdStatus`, `role="status"`),
  and the toggle's `aria-expanded` change is the announcement the disclosure
  pattern specifies. See §3.5.6.

---

## 5. Responsive

Runs in a desktop browser; must not break narrow. `<main>`'s existing
`max-width: 720px; padding: 24px 18px 80px` carries the settings view unchanged.

| Width | Behavior |
| --- | --- |
| ≥ 720px | Settings view sits at 720px, centered. Identical rhythm to the step cards. |
| 480–720px | Fluid. `.setting-actions` wraps via `flex-wrap`. The Client ID input + Save row uses the existing `.row.wrap` + `.grow`, which already collapses correctly. |
| < 420px | `.setting-actions` switches to `flex-direction: column; align-items: stretch` and buttons go full-width and centered (`tokens.md` §3). Prevents a wrapped two-button row from producing a stranded half-width button. |

**Amendment 2026-07-20 — the value row.** `#clientIdCurrent`'s row is the same
`.row.wrap` + `.grow` as the input row directly below it, so it inherits the
behavior in the table above with no new rule. Two things to confirm in UAT:

- **Revealed, at the narrowest width.** 32 monospace characters plus a
  `Show the short version` button must wrap, not overflow. `.mono-value`'s
  `word-break: break-all` (`tokens.md` §3a) is what guarantees the value wraps
  inside its column instead of pushing the card wide — this is the specific
  regression to look for, because it only appears in the expanded state and only
  when narrow.
- **The `< 420px` rule does not apply here.** It targets `.setting-actions`, and
  this row is `.row.wrap` inside `.setting-body`, so the toggle wraps beneath the
  value at its natural width rather than going full-width. That is correct and
  matches the Save button's behavior in the row below — the two rows must stay
  visually parallel at every width, which is the whole reason they share a
  structure.

### 5.1 Header at narrow widths

The header is `display: flex; justify-content: space-between`, holding the brand
and the pill. **This spec adds no new header controls** — the pill is repurposed,
not supplemented — so header crowding is unchanged from today. This was a factor
in choosing the pill over a separate gear button.

**Amendment 2026-07-20.** Still no new header *control*, but the pill gains a
trailing `›` (`tokens.md` §2b) — roughly 16px including the pill's existing gap,
added inside the control rather than beside it. The claim above is therefore
weakened, not void: **confirm at 320px** that `🎵 Yoto Maker` and
`● Yoto not connected ›` (the longest combination) neither wrap nor overflow. If
they do, the escalation is dropping the chevron's leading gap — never a second
header row, and never moving the brand.

### 5.2 Confirmation at narrow widths

`.setting-confirm` inherits the section's width and its buttons follow the
< 420px column rule. In column layout the order is unchanged — `Never mind`
above `Yes, …` — keeping the safe option first both visually and in tab order.

---

## 6. Motion

None beyond what exists. The view swap is instantaneous — no transition.

Deliberate: a cross-fade or slide on a full-view swap costs perceived
responsiveness and adds a window where both views are partly visible, which
reads as a glitch to a low-confidence user. The existing app animates only two
things (`.btn` hover `filter`/`transform` at `styles.css:94`, and the progress
bar width at `:162`), both of which are direct feedback on a user action. A view
swap is navigation, and navigation in this app is instant.
