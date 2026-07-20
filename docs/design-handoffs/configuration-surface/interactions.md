# Interactions — Configuration surface

State machines, focus management, keyboard behavior, and responsive rules.
Copy for every state is in [`copy.md`](copy.md).

---

## 1. View switching

### 1.1 Enter

Triggered by: header pill click, footer `Settings` link, step 3's
`⚙️ Yoto connection settings` link, or a `#settings` hash on load / `hashchange`.

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

---

## 4. Keyboard

| Key | Context | Behavior |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | Settings view | Natural DOM order. Card view is `display:none`, so it's out of the tab order entirely. |
| `Enter` / `Space` | Any `.btn` | Activate. Native `<button>` behavior — no custom handlers. |
| `Enter` | Client ID input | Same as clicking `Save`. Matches `#ytUrl` at `app.js:519`. |
| `Escape` | Confirmation open | Dismiss it, return focus to the button that opened it. |
| `Escape` | Anywhere else in settings | **Nothing.** See `overview.md` §5.3 — a page, not a dialog, and the user may be mid-paste. |
| `Alt+←` / browser Back | Settings view | Returns to the card view via `hashchange`. |

### 4.1 Tab order in the settings view

```
← Back to my card
  → [account] primary button  → [account] Cancel (signing_in only)
  → [client-id] input → Save  → [client-id] Go back to the built-in one
```

When a confirmation is open, that section's own actions are `.hidden` and
therefore skipped; the confirmation's two buttons take their place in sequence.

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

---

## 5. Responsive

Runs in a desktop browser; must not break narrow. `<main>`'s existing
`max-width: 720px; padding: 24px 18px 80px` carries the settings view unchanged.

| Width | Behavior |
| --- | --- |
| ≥ 720px | Settings view sits at 720px, centered. Identical rhythm to the step cards. |
| 480–720px | Fluid. `.setting-actions` wraps via `flex-wrap`. The Client ID input + Save row uses the existing `.row.wrap` + `.grow`, which already collapses correctly. |
| < 420px | `.setting-actions` switches to `flex-direction: column; align-items: stretch` and buttons go full-width and centered (`tokens.md` §3). Prevents a wrapped two-button row from producing a stranded half-width button. |

### 5.1 Header at narrow widths

The header is `display: flex; justify-content: space-between`, holding the brand
and the pill. **This spec adds no new header controls** — the pill is repurposed,
not supplemented — so header crowding is unchanged from today. This was a factor
in choosing the pill over a separate gear button.

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
