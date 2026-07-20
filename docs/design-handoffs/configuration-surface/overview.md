# Configuration surface — design spec

**Status:** Proposed — awaiting Mark's approval before Planner picks it up
**Date:** 2026-07-20
**Relationship to prior handoffs:** N/A — this is the **first** package in
`docs/design-handoffs/`. It establishes the convention. It **follows** the
existing implemented visual language in `yoto_maker/server/static/styles.css`
and the copy register of `docs/INSTALL-FOR-MOM.md`, deviating from neither.

---

## 1. What this is

One place where the user can change how Yoto Maker talks to Yoto. Two settings
ship in this PR:

1. **Your Yoto account** — one action that both *reconnects a broken connection*
   and *switches to a different Yoto account*.
2. **Yoto Client ID** — advanced; currently buried inline in step 3.

The **overriding requirement** is that setting #3, #4, and #12 are "add one more
`<section class="setting">`", never "redesign the page". Section 4 defines the
primitive that guarantees that.

## 2. Who uses it, and how often

The primary user is a non-technical grandparent. She will open this surface
**rarely** — realistically twice ever:

- once if she ever gets a new Yoto account, and
- once when something breaks and the app stops uploading.

The second visit is the one that matters. She arrives **already frustrated**,
having just watched "Send to Yoto" fail. Every decision below optimizes for that
visit: she must be able to find this screen without being told where it is,
understand what she's looking at, and fix it with one button.

**Corollary, and the hardest constraint in this spec:** the ~200 visits where
she is just making a card must not get one pixel heavier. She should be able to
use Yoto Maker for a year without ever noticing this surface exists.

---

## 3. Placement decision

> **Decision: a full-page view swap, reached from the header status pill and a
> footer link, with a `#settings` URL hash. Not a tab strip, not a modal, not a
> fifth step.**

### 3.1 What was rejected, and why

**A top-level tab strip (`Make a card` | `⚙️ Settings`) — rejected.**

Two independent reasons.

First, it taxes the everyday path. A tab strip is persistent chrome sitting
above step 1. It forces a first-time user to resolve a navigation choice
*before* she reaches "1. Add your audio" — and this app's whole teaching
strategy is that the first thing you see is a big friendly `1`. Making her
parse a nav bar first to conclude "I want the left one" is a real cost paid on
every visit, to serve a screen visited twice.

Second — and this is the specific question the brief asked me to make a
deliberate call on — it **overloads `.tab` at two scopes**. Today `.tab` means
"pick which kind of picture you want", a within-step, low-stakes, instantly
reversible choice among peers. Reusing that same pill visual for "swap the
entire application view" teaches the user that pills are sometimes trivial and
sometimes navigational, and the only way to tell is to click. That is a worse
outcome than either consistent option. If a top-level tab strip were the right
structure, it should get its **own** visual treatment — at which point the
"consistency win" that motivated reusing `.tab` has evaporated, and all that's
left is reason one. So: no tab strip, and `.tab` stays meaning exactly one
thing.

**A modal or drawer over the four-step flow — rejected.**

Three reasons, in ascending order of severity.

1. `.modal` is capped at `max-width: 400px` and the surface must grow
   indefinitely. Setting #8 turns this into a scroll-within-a-scroll — the
   single most confusing layout for a low-confidence user.
2. A modal needs a focus trap, an Escape handler, a scrim click handler, and
   inert-background management to be accessible. A view swap needs none of
   these, because `display: none` on the step flow removes it from the tab
   order for free. Less code, fewer bugs, better default behavior.
3. **Decisive:** the primary action on this surface *opens a second browser tab*
   (Yoto's sign-in page), and then this surface must sit in a waiting state for
   up to a minute polling for the result. A modal is a "you are briefly blocked
   on one small thing" container. Sitting inside one while you go do a
   multi-minute task in another tab, come back, and read a result is a misuse of
   the pattern. The user will lose the modal behind the sign-in tab and have no
   idea whether the app is still waiting.

**A fifth step section — rejected, and Mark's skepticism is correct.**

Concurring with the brief and adding the sharper version of the argument: the
damage isn't that config "isn't a step". It's that **the numbered sequence is a
promise about completion.** `1 2 3 4` tells the user "there are four things and
then you're done" — that's the entire reason the wizard feels approachable, and
it's the structure `docs/INSTALL-FOR-MOM.md` teaches verbatim ("You'll see
**four numbered steps** on the screen. Just go top to bottom.").

A `5` breaks that promise for every user on every visit. Either she does step 5
(wrong — she should never touch it) or she learns that the numbers don't
actually mean "do these in order" (which devalues 1–4). And the printed guide
for the least confident user in the audience now says "four" while the screen
says five. There is no version of this that isn't a net loss.

The only argument for it — discoverability, everything on one page — is served
better by the header pill (§5), which is *more* discoverable because it's
attached to the thing that's broken.

### 3.2 Why a view swap wins

- **Zero cost to the everyday path.** No new persistent chrome. The entry point
  is the header pill, which already exists and already occupies that space.
  Nothing about steps 1–4 changes visually, and step 3 actually gets *lighter*
  (§6.3).
- **Unlimited room to grow.** It's a page. Setting #12 just goes at the bottom.
  This is the requirement the brief called overriding, and it's the structure
  that satisfies it most cheaply.
- **Accessible by default.** Hiding `<main>`'s step flow with the existing
  `.hidden` (`display: none !important`) takes it out of the tab order, the
  accessibility tree, and Ctrl+F — no trap, no `inert`, no scrim.
- **Browser Back works.** With a `#settings` hash, the browser's own Back button
  returns to the card. Low-confidence users reach for Back constantly; getting
  that right for free is worth more here than in most apps.
- **It matches the app's own mental model.** Yoto Maker is a page you scroll top
  to bottom. Settings is a different page you scroll top to bottom. Nothing new
  to learn.

### 3.3 Where the two views live

```html
<main>
  <div id="cardView">        <!-- update banner, tools warning, steps 1-4, footer -->
  <div id="settingsView" class="hidden" aria-labelledby="settingsTitle">
</main>
```

Exactly one is un-`hidden` at a time. `#settingsView` is inside `<main>`, so it
inherits the existing `max-width: 720px` centering with no new layout code.

---

## 4. The `.setting` primitive

The reusable config-section pattern. **Every setting on this surface, now and
forever, is one instance of this and nothing else.** If a future setting can't
be expressed as an instance, that's a signal to revise the primitive here — not
to hand-roll a one-off section.

### 4.1 Anatomy

Seven slots, in fixed vertical order. Slots 1, 2 and 6 are required; the rest
are omitted when the setting doesn't need them.

| # | Slot         | Class              | Required | Purpose |
|---|--------------|--------------------|----------|---------|
| 1 | Title        | `h3`               | **yes**  | Names the setting in the user's words. Never a jargon term alone. |
| 2 | Description  | `.setting-desc`    | **yes**  | 1–2 sentences: what this is, and why you'd ever touch it. Written for someone who does not know what the setting is. |
| 3 | Status       | `.setting-status`  | no       | Colored dot + current state, in plain language. Present when the setting *has* an observable state; omitted for pure preferences (a checkbox is its own status). |
| 4 | Body         | `.setting-body`    | no       | The setting's own value area — the control that reads or writes it. Usually an input; may also include a read-only display of the value currently in effect. Omitted for action-only settings. |
| 5 | Actions      | `.setting-actions` | no       | Buttons. Primary first (leftmost), then secondary. |
| 6 | Feedback     | `.msg-box`         | **yes**\* | Result of the last action. `.err` / `.ok` / `.info`. \*Required to *exist* in markup (hidden); shown on demand. |
| 7 | Confirmation | `.setting-confirm` | no       | Inline confirm step for anything destructive-ish. Hidden by default. Never a `window.confirm()`. |

> **Slot 4 wording amended 2026-07-20** (§11). It previously read "The input
> control, if any." That phrasing did not say where a *displayed* current value
> belongs, and slot 3 forbids it (§4.3.2), so the question had no answer.
> Body is the answer. **This is a clarification, not a widening:** still seven
> slots, same order, same classes, no change to any `.setting*` rule in
> `tokens.md` §3.

### 4.2 Markup contract

Planner should treat this as the literal template. `{id}` is a per-setting
kebab-case identifier (`account`, `client-id`, …).

```html
<section class="setting" id="setting-{id}">
  <h3>{Title}</h3>
  <p class="setting-desc">{Description}</p>

  <!-- 3. status (optional) -->
  <p class="setting-status is-{ok|warn|err|unknown}" id="{id}Status" role="status">
    <span class="dot" aria-hidden="true"></span>
    <span>{Status headline}<span class="sub">{optional second line}</span></span>
  </p>

  <!-- 4. body (optional) -->
  <div class="setting-body" id="{id}Body">…control…</div>

  <!-- 5. actions (optional) -->
  <div class="setting-actions" id="{id}Actions">
    <button class="btn primary" id="{id}Primary">{Primary label}</button>
    <button class="btn" id="{id}Secondary">{Secondary label}</button>
  </div>

  <!-- 6. feedback (always present, hidden until needed) -->
  <div class="msg-box err hidden" id="{id}Msg" role="alert"></div>

  <!-- 7. confirmation (optional, hidden by default) -->
  <div class="setting-confirm hidden" id="{id}Confirm" role="group"
       aria-labelledby="{id}ConfirmText">
    <p id="{id}ConfirmText">{Confirmation question and consequences}</p>
    <div class="setting-actions">
      <button class="btn ghost" id="{id}ConfirmNo">{Cancel label}</button>
      <button class="btn primary" id="{id}ConfirmYes">{Confirm label}</button>
    </div>
  </div>
</section>
```

### 4.3 Rules that make it durable

1. **Slot order is fixed.** Never reorder for one setting. Predictable vertical
   rhythm is the whole value — the user learns "the buttons are under the
   explanation" once and it holds forever.
2. **Status is a sentence, not a value.** "Connected to Yoto", not
   `connected: true`. Never surface a raw stored value.
3. **The confirm slot replaces the actions slot while open.** When
   `.setting-confirm` is shown, the setting's own `.setting-actions` is
   `hidden`. There is never more than one live set of choices in a section.

   **Scope, clarified 2026-07-20 (§11): "choices" means controls that commit
   something.** A control that only changes how existing information is
   *displayed* — a disclosure toggle, an expander — is not a choice, changes no
   state the confirmation is about, and **stays enabled while a confirmation is
   open.** The concrete case: a user reading "Yoto Maker will start using the
   Client ID you pasted" may reasonably want to check what the current one is
   before answering. Disabling the only control that answers that question, at
   the exact moment she asks it, would be the opposite of what this rule is for.
4. **One primary button per setting, maximum.** If a setting seems to need two
   primaries, it's two settings.
5. **Feedback is scoped to its section.** A failure in one setting must never
   render a message inside another. This is what makes sections independent
   enough to add and remove freely.
6. **A section never depends on its neighbours' markup.** Adding setting #7
   between #2 and #3 must require zero edits to #2 or #3.

### 4.4 Adding a future setting — the whole procedure

1. Copy the §4.2 template, pick an `{id}`.
2. Fill the required slots; delete the optional ones you don't need.
3. Drop it into `#settingsView` wherever it belongs in priority order.
4. Wire its buttons.

No CSS. No layout work. No coordination with other sections. That is the test
this primitive was designed to pass.

---

## 5. Entry and exit

### 5.1 Entry point A — the header status pill (primary)

The `#yotoPill` in the header **becomes the way in**, and its behavior is
simplified rather than extended.

Today the pill's click handler is:

```js
if (STATUS.yoto.configured && !STATUS.yoto.connected) connectYoto();
```

…which means it is a **dead click** whenever the user is connected, and (because
`configured` is permanently `true` — see §7.1) is really just "connect if not
connected". So the everyday state of the pill is: looks like a button, says
something about Yoto, does nothing.

New behavior: **the pill always navigates to Settings.** Regardless of state.

This is the right entry point because it needs no discovery. The user whose
upload just failed looks for the thing on screen that talks about her Yoto
connection, and there is exactly one — a pill that says "Yoto not connected" in
the header. She clicks it because it's the only thing that looks relevant, and
it takes her to the screen where she fixes it. We are not teaching her where
settings live; we're letting her follow the symptom.

It also *removes* a control-behavior branch instead of adding one, and turns a
dead click into a live one.

**Accepted trade-off:** a not-yet-connected user who clicks the pill now takes
two clicks to reach Yoto's sign-in instead of one. Acceptable — the pill was
never the intended first-time path. Step 3's big `🔗 Connect my Yoto account`
button is, and it is untouched.

Markup changes: add `aria-label` and make the state legible to assistive tech.

```html
<button id="yotoPill" class="pill" aria-label="Yoto connection settings">
```

The pill keeps its existing dot + text rendering from `renderStatus()`.

### 5.2 Entry point B — the footer link (deliberate)

The footer becomes:

> Made with Yoto Maker · v0.1.8 · **Settings** · About · Start a new card

For the user who isn't reacting to a symptom but has been told "go into
settings and paste this Client ID". Same destination.

Two entry points, mapping to the two real intents: *something is wrong* (pill)
and *I was told to change something* (footer). Neither adds visual weight —
the pill already exists, and the footer is a `.tiny` text row.

### 5.3 Exit

- A `← Back to my card` button at the top-left of the settings view, above the
  title. Always visible, never scrolled past (it's the first thing in the view,
  and the view is short enough that this is sufficient — no sticky positioning).
- Browser Back, via the `#settings` hash.

**No Escape-to-exit.** Deliberate: this is a page, not a dialog, and the user
may be mid-way through typing a Client ID into a text field. Losing that to a
stray keypress is a bad trade for an exit affordance that's already visible on
screen. Escape *is* bound inside this surface, but only to dismiss an open
confirmation — see `interactions.md`.

### 5.4 Routing

`#settings` in the URL hash. `hashchange` drives which view is visible, so Back
and Forward work, and a reload keeps the user where they were.

The card draft is server-side (`/api/draft`), so switching views loses nothing.

---

## 6. The two settings, as instances

Verbatim copy for every string is in [`copy.md`](copy.md). State machines are in
[`interactions.md`](interactions.md). This section is the structural mapping
only — the proof that the primitive expresses both.

### 6.1 Setting 1 — Your Yoto account

| Slot | Used | Content |
|------|------|---------|
| Title | ✅ | "Your Yoto account" |
| Description | ✅ | What connecting does, and the two reasons you'd redo it |
| Status | ✅ | Five states: checking / connected / not connected / broken / can't check |
| Body | ❌ | No input — this setting is a single action |
| Actions | ✅ | **One** button. Label varies by state. |
| Feedback | ✅ | Sign-in failures |
| Confirmation | ✅ | Only when currently connected |

**The single action.** Per Mark's explicit direction there is one button, not a
"sign out" and a "fix connection" pair. The copy carries both intents by
splitting the work between two slots:

- The **button** stays short and scannable: `🔗 Sign in to Yoto again`
- The **description** does the disambiguating: "Use this if Yoto Maker has
  stopped being able to send cards, **or** if you want to use a different Yoto
  account."

This is the right split. A button label that tried to carry both intents
("Sign out and sign in again, or switch accounts") is unscannable, and the user
in the broken-connection case doesn't know which of the two she needs — she just
knows it's broken. She should be able to press the obvious button without first
having to diagnose herself. That is precisely what two buttons would have forced
her to do, and why one is correct here.

When *not* connected, the same button reads `🔗 Connect my Yoto account` —
matching step 3's existing label word-for-word, so the two places that do this
never look like different features.

### 6.2 Setting 2 — Yoto Client ID

| Slot | Used | Content |
|------|------|---------|
| Title | ✅ | "Yoto Client ID (advanced)" |
| Description | ✅ | Plain-language explanation + link to the setup guide |
| Status | ✅ | Four states: built-in / your own / set by env var / saving |
| Body | ✅ | The value in effect + a disclosure toggle (`saved` / `env` only), then text input + Save button. Two parallel `.row.wrap` + `.grow` rows — see §11. |
| Actions | ✅ | "Go back to the built-in one" (only when a custom one is saved) |
| Feedback | ✅ | Save failures / success |
| Confirmation | ✅ | On both save-a-new-one and reset (both sign the user out — §7.3) |

The primitive holds for both without strain, and the two settings exercise
different optional slots (one has no Body, one has no state where Actions are
empty), which is a reasonable sanity check that the slots are actually
independent.

### 6.3 What leaves step 3

Step 3 gets **smaller**, which directly serves the "don't make the everyday path
heavier" constraint:

- **`#setupRow` is deleted from `index.html`.** The entire Client ID input,
  its `.msg-box.info` explainer, and `#setupError` move to the settings view.
  (Note this block is currently *unreachable by its own logic* — see §7.1.)
- **`#advToggle` changes target.** It stops revealing an inline row and becomes
  a link to the settings view. Its copy changes from "⚙️ Use a different Yoto
  account (advanced)" to "⚙️ Yoto connection settings" — because the settings
  view now covers both switching accounts *and* repairing, and the old label
  only advertises one of those.
- **`#connectRow` and `#connectBtn` stay exactly as they are.** The first-time
  path is untouched.

---

## 7. Backend implications — Planner must scope these

Seven items. Items 1–4 are **required** for the specified design to be honest;
5 and 6 are pre-existing bugs this surface will expose; 7 is explicitly
recommended *against*.

### 7.1 `configured` is dead and cannot be used — CORRECTION TO THE BRIEF

The brief states `/api/yoto/status` "only reports a `configured` boolean". Two
corrections:

**(a)** `connection_status()` (`yoto_maker/yoto/auth.py:175`) already returns
**both** `configured` and `connected`, and `/api/status` already surfaces them
under `yoto`. `connected` exists today and is already consumed by
`renderStatus()`. There is no work to do to get it.

**(b) More importantly, `configured` is permanently `true` and carries zero
information.** It is defined as:

```python
"configured": bool(config_mod.resolve_client_id()),
```

and `resolve_client_id()` (`yoto_maker/config.py:47`) falls back to the baked-in
`DEFAULT_YOTO_CLIENT_ID` constant, which is never empty. So the expression can
never be `False`.

The consequence in the current UI: `renderStatus()` does
`show($("#setupRow"), !configured)` — so **the Client ID setup row can never
appear on its own**, and `#advToggle` is the only way to reach it. That's a
latent dead-code path that this PR removes anyway, but Planner should know the
existing behavior is not what `index.html`'s comment claims ("shown
automatically only if the app has none baked in").

**What this surface needs instead of `configured`:** the *source* of the
effective Client ID (§7.2). `configured` should be left in the payload for
compatibility but must not drive any new UI.

### 7.2 `/api/status` must report the Client ID source and a masked value — NEW

The Client ID section can't state its status honestly without knowing which of
the three precedence tiers won. Extend the `yoto` object:

```jsonc
"yoto": {
  "connected": true,
  "configured": true,                  // legacy, unused by new UI
  "client_id_source": "builtin",       // "env" | "saved" | "builtin"
  "client_id_masked": "a8OG…oU1"       // first 4 + last 3, for recognition only
}
```

`client_id_source` is computed by the same precedence chain as
`resolve_client_id()` and must not drift from it — Planner should have Builder
derive both from one function so they cannot disagree.

The masked value exists so a user on the phone with whoever set this up can
confirm *which* ID is in effect without the full string being displayed. It is
not a secret (PKCE public client, per `config.py:38-44`), so masking is for
scannability, not security.

### 7.3 Changing the Client ID must clear the saved sign-in — NEW, and important

**This is a correctness bug the current UI already has**, and the settings
surface will make it much easier to hit.

Tokens are minted for a specific `client_id`. `get_access_token()`
(`auth.py:149`) refreshes by POSTing the *currently resolved* client ID
alongside the *previously stored* refresh token. Change the Client ID and those
two no longer belong to each other — Auth0 rejects the refresh.

The user-visible result today: she saves a new Client ID, the pill still says
"Yoto connected" (because `connected` only checks that a token file exists on
disk), and every single upload fails with an unexplained error. That is exactly
the broken state this feature is supposed to *rescue* people from, so shipping a
settings screen that can *cause* it would be a bad outcome.

**Required:** `POST /api/yoto/client-id` must call `logout()` after a successful
save. The design accounts for this — the confirmation copy in `copy.md` tells
the user she'll need to sign in again, and the account section drops to
"not connected" immediately afterwards.

### 7.4 Resetting to the built-in Client ID needs a way to clear the setting — NEW

There is currently **no code path that can remove `yoto_client_id`**:

- `settings.py` exposes `get` / `set` / `all` — there is no `delete`, and `set`
  can only write a value.
- `POST /api/yoto/client-id` rejects an empty string with a 400
  (`app.py:469-470`).
- `_DEFAULTS` has no `yoto_client_id` key, so a saved value is only ever present
  because it was explicitly written.

So "Go back to the built-in one" is not implementable against today's backend.
Planner needs:

- `settings.delete(key)` (or `set(key, None)` treated as removal), and
- `DELETE /api/yoto/client-id`, which removes the saved key **and** calls
  `logout()` for the same reason as §7.3.

**And a constraint on what "reset" is allowed to promise.** Because env beats
saved in `resolve_client_id()`, deleting the saved value returns the app to
*whatever the chain resolves to next* — which is the env var if one is set, and
only otherwise the built-in default. The spec therefore:

- **hides the reset action entirely when `client_id_source == "env"`**, since
  there is no saved value in effect to reset, and
- labels it "Go back to the built-in one" **only** when it will genuinely land
  on the built-in one.

This is the specific case the brief warned about — a control whose behavior
contradicts the resolution order. The design resolves it by not offering the
control in the situation where it would lie.

### 7.5 `connected` means "a file exists", which is untrustworthy here — NEW

```python
"connected": _load_tokens() is not None
```

That is true for a token file containing a long-dead refresh token. So in the
**exact scenario this feature targets** — the connection has silently broken —
the app confidently reports "Yoto connected".

A settings screen whose headline status is wrong precisely when the user needs
it is worse than no settings screen. So:

**Required:** a `POST /api/yoto/check` that actually calls `get_access_token()`
and reports the real outcome:

```jsonc
{ "state": "connected" }                       // refresh succeeded
{ "state": "broken" }                          // NotConnectedError / AuthError
{ "state": "not_connected" }                   // no token file at all
{ "state": "unknown", "reason": "offline" }    // couldn't reach Yoto
```

Called on entering the settings view (§`interactions.md`). The `unknown` state
matters: no internet must not be reported as "your connection is broken", or
she'll disconnect a perfectly good account trying to fix a Wi-Fi problem.

This endpoint is small — `get_access_token()` already does all the work and
already distinguishes the failure types — but it must be **timeboxed** (~8s) so
an offline user isn't left on a spinner.

### 7.6 The sign-in poller never stops — PRE-EXISTING BUG

`connectYoto()` (`app.js:466-469`) starts a 2-second `setInterval` that is
cleared **only on success**. If the user closes the Yoto tab, cancels, or the
sign-in fails, the interval polls `/api/status` forever until the page is
reloaded — and the UI sits with no indication that anything went wrong.

The settings surface makes this far more visible, because "start the sign-in
flow" becomes an explicit, prominently-placed action rather than a one-time
first-run step. `interactions.md` specifies a bounded poll (3 minutes) with a
timeout state and a user-cancellable waiting state. Planner should fix this in
`connectYoto()` itself so step 3 benefits too.

### 7.7 Showing *which* account is connected — RECOMMENDED AGAINST for this PR

The brief asks what "connected" should look like and flags account identity as a
possible backend need. Having checked: **it is not cheap, and it is not worth
it here.**

`YOTO_SCOPES` is `"user:content:manage offline_access"` (`config.py:64`) — no
`openid` / `profile` / `email`. So there is no ID token, and no email address
available anywhere in the current flow. Getting one would mean:

1. adding scopes, which
2. triggers a **fresh consent prompt for every existing user** on their next
   refresh, and
3. requires the Yoto dashboard client to permit those scopes — including every
   user who followed `SETUP-YOTO-CONNECTION.md` and configured their own client
   with only the two documented scopes. Their sign-in would start failing.

Breaking every self-configured user's connection in order to display a nicer
status line on a settings page is a bad trade, and it is grimly funny that the
change would break connections on the screen designed to repair them.

**What the design does instead:** trust comes from *recency and verification*,
not identity. The status line is backed by a live check (§7.5), so "Connected to
Yoto" means "we just asked Yoto and it said yes" rather than "a file exists".
For a single-family app on one home computer, "is it working right now" is the
question actually being asked — "which account" is a question that only arises
if you have more than one, and if you do, you know which one you just signed
into thirty seconds ago.

If Mark wants account identity later, it should be its own PR gated on a Yoto
API check for a scope-free identity endpoint.

### 7.8 `/api/status` must also report the full Client ID — NEW (amendment, 2026-07-20)

Required by §11. The `yoto` object gains one field:

```jsonc
"yoto": {
  "connected": true,
  "configured": true,                  // legacy, unused by new UI
  "client_id_source": "saved",         // "env" | "saved" | "builtin"
  "client_id_masked": "a8OG…oU1",      // first 4 + last 3
  "client_id_full": "a8OGO6Ef…QoU1"    // NEW — the whole string, or null
}
```

`client_id_full` is **`null` when `client_id_source == "builtin"`**, and the
complete string otherwise. All three come from `_resolve_client_id_with_source()`
in `config.py`, which already returns the value and the source together, so
adding this cannot introduce drift — the same guarantee §7.2 relies on.

**Why the value goes on `/api/status` rather than behind a reveal endpoint.**
This was a real fork; the reasoning is recorded because the obvious instinct
(a dedicated endpoint, fetched on demand) is the wrong one here.

1. **There is nothing for a second endpoint to gate.** The app binds to
   `127.0.0.1` (`config.py:111`) and has no authentication of any kind. The
   browser, the server, the OS account and the person are all the same. A reveal
   endpoint would be exactly as unauthenticated as `/api/status`, so it would
   gate the value against nobody.
2. **The value is not a secret** — it is a PKCE public client ID, transmitted in
   plaintext in every sign-in URL, present in the shipped `.exe`, and shown
   openly in the Yoto dashboard the user is comparing it against
   (`config.py:38-44` already says so). Guarding it would be theatre, and the
   design elsewhere in §11 spends real effort *not* implying it needs guarding.
3. **A fetch introduces a failure mode the toggle otherwise cannot have.** An
   on-demand endpoint means the disclosure can fail — needing a spinner, an
   error string, and a decision about what the toggle shows when the request
   times out. That is three new states of copy and interaction bought with zero
   benefit. With the value already in hand, the toggle is synchronous and cannot
   fail.
4. **`/api/status` is already the place this concept lives.** It carries
   `client_id_source` and `client_id_masked` today. Splitting one question —
   "what Client ID is in effect?" — across two endpoints so that half of it can
   be fetched separately makes the contract worse, not safer.

**Anticipated objection, addressed here so a reviewer need not raise it:**
`/api/status` is polled every 2s during sign-in (`app.js`), so `client_id_full`
rides along on those responses. That is ~32 bytes over loopback to the same
user's own browser, carrying a value that is public by construction. It is not a
disclosure concern and must not be treated as one. Do **not** add redaction,
special logging handling, or a "sensitive field" wrapper — doing so would
contradict the framing this whole amendment rests on.

**Why `null` for `builtin` rather than always populated.** §11.3 decides the UI
renders no value in that state. Sending a populated field the UI is specified
never to display invites a future contributor to display it, quietly undoing
that decision without anyone revisiting the reasoning. The `null` carries the
rule at the layer that owns the precedence chain.

**Nothing else changes.** No new route, no new method, no change to
`POST` / `DELETE /api/yoto/client-id`, no change to `mask_client_id()`. One
field, one function.

---

## 8. Documentation updates required in this PR

Both of these go stale the moment `#setupRow` moves, and both are read by the
least technical users:

- **`docs/SETUP-YOTO-CONNECTION.md`**, "Option A" (lines 51–54) — currently
  instructs the reader to "go to step 3 … click **⚙️ Use a different Yoto
  account (advanced)**". Must be rewritten for the new location. Also worth
  adding a note that saving a Client ID signs you out (§7.3).
- **`docs/INSTALL-FOR-MOM.md`**, step 3️⃣ note (lines 81–83) — mentions the same
  "advanced" link by its old name.

---

## 9. Out of scope

Explicitly **not** in this PR, to keep it to one PR's worth:

- Moving `remove_sponsors` (the SponsorBlock checkbox) out of step 1. It is a
  per-card decision made in context; it belongs where it is.
- An AI image API key setting. It's a plausible setting #3 and the primitive
  handles it, but nothing about today's AI path is broken.
- Account identity (§7.7).
- Dark mode. Not present anywhere in the app today.
- Any change to steps 1, 2 and 4.

---

## 10. Success criteria

1. A user whose connection has broken can, with no instruction, get from a
   failed upload to a working connection using only what's on screen.
2. A first-time user completing steps 1–4 never needs to notice this surface.
3. Adding a third setting requires no CSS and no edits to the existing two
   sections.
4. Every string on the surface passes the `INSTALL-FOR-MOM.md` register test.
5. The whole surface is operable by keyboard, with a visible focus indicator.

---

## 11. Amendment: showing the Client ID in effect (2026-07-20)

**Status:** proposed, awaiting Mark's approval. Amends §4.1, §4.3.3, §6.2, adds
§7.8; `copy.md` §4, `interactions.md` §3.5/§4, `tokens.md` §3a.
**Relationship:** **extends** this package. Deviates from nothing.

Shipped in PR #10, the Client ID section identifies the value in effect as
`Ends in oU1.` and offers no way to see more. Mark has used it and wants to see
the actual value, proposing a masked display with a control to reveal it.

### 11.1 What the user is actually doing

There is essentially one reason to look at this value: **to check it against
what dashboard.yoto.dev shows.** Either she is on the phone with whoever set it
up, or she has the dashboard open beside the app. Every decision below is scored
against that task and nothing else.

Two things follow immediately, and both matter more than the reveal control:

**(a) The collapsed display is throwing away half of what it has.**
`mask_client_id()` (`config.py:80-90`) returns first-4 + last-3 — `a8OG…oU1` —
and `/api/status` already sends it. `renderClientId()` (`app.js:499-508`) then
slices off the last 3 and discards the rest. For the comparison task, 7 anchored
characters at both ends is far stronger than 3 at one end: it catches a
transposed or truncated paste that a suffix match sails straight past. **Showing
the whole mask is a strict improvement available for free, independent of
everything else in this amendment.** It was not in the request; nobody had
noticed.

**(b) Proportional type is a worse problem than truncation.** The built-in ID is
`a8OGO6EfbWit5tDUUrOz0g49s49NQoU1`. It contains `O` four times, `0` twice, and a
lowercase `o` — in a face where `O` and `0` are near-identical and `l`/`I`/`1`
collapse. A user comparing this against a dashboard in Segoe UI will make
exactly the error this feature exists to prevent, and she will make it
*confidently*, because the strings will look the same. **A monospace treatment
does more for the stated use case than the reveal control does** (`tokens.md`
§3a). Also not in the request.

### 11.2 The reveal control: yes, but not an eye icon

Mark chose "masked + eye icon to reveal" over always-full and over
full-plus-copy-button. **The masking is right. The eye icon is not, and the
recommendation is to drop it.**

An eye icon is not decoration; it is a word. It is the password-field
convention, and it says one specific thing: *this value is secret and you are
choosing to expose it.* That statement is false — this is a PKCE public client
ID, sent in plaintext in every sign-in URL, compiled into the shipped `.exe`,
and displayed openly on the dashboard the user is comparing it against.

The brief for this amendment was explicit that the copy must not imply the value
is sensitive, because doing so would make a non-technical user anxious about a
string she is *supposed* to paste from a public web page. An eye icon carries
that implication more forcefully than any sentence would, and it carries it
past anyone who does not read the sentence. Banning the word while shipping the
icon bans nothing.

The distinction the design needs to make is **truncation, not censorship** —
the same distinction between a short git SHA (`a8OG…`, obviously an
abbreviation, nobody thinks it is redacted) and a masked password
(`••••••••`, obviously withheld). So:

| | Rejected | Chosen |
| --- | --- | --- |
| Collapsed value | `••••••••••••••••••••••••••oU1` | `a8OG…oU1` |
| Control | 👁 icon button | text button, `Show the whole thing` |
| Pattern | password reveal | **disclosure** (`aria-expanded`) |
| What it says | "this is secret" | "this is shortened" |

The disclosure pattern is also the better engineering answer. A password reveal
has a genuinely awkward accessibility contract — the accessible name and the
state disagree about what is being described. A disclosure is the textbook
`aria-expanded` case with a settled contract and no focus management at all
(`interactions.md` §3.5).

### 11.3 Was always-full considered? Yes. Here is why masking survived.

Honest accounting, because the two stated justifications for masking are thin
and one of them is backwards:

- *"A 32-char string would dominate the row."* Measured: at the `.sub` size
  inside `<main>`'s 720px column, 32 characters is roughly a third of the line.
  It fits. This justification is real but small.
- *"It keeps the full ID out of screenshots."* **This one cuts the other way.**
  The screenshot this user takes is the one she sends to whoever is helping her,
  and its entire purpose is to show what her setting says. Masking makes that
  support flow worse. Discard this argument; do not let it reappear.

What actually saves the mask is neither of those. It is that **`a8OG…oU1` is
usually sufficient**, so the collapsed row answers the question outright most of
the time — 7 anchored characters distinguish any realistic set of IDs one person
holds. The full string is needed only for transcription, or when the short
compare fails and she needs to find *where* it diverges. That is a textbook
progressive-disclosure shape: the common case answered inline, the precise case
one click away. The mask earns its place as **the summary form of a value**, not
as a curtain.

If Mark prefers always-full after reading this, the change is small and
contained: render `client_id_full` into `#clientIdValue`, drop the toggle, and
delete `interactions.md` §3.5. Everything else in this amendment — monospace,
the full mask, `/api/status`, the `builtin` decision, the slot placement — stands
unchanged and is worth shipping either way.

### 11.4 The three sources, decided separately

The request did not distinguish them. They are not the same case.

**`saved` — show the block, toggle enabled.** The assumed core case. A person
deliberately put this value here and may need to verify it.

**`env` — show the block, toggle enabled. This is the strongest case, not
`saved`.** It is the one state where the value is **not discoverable by the user
anywhere else**: in `builtin` it is a constant in a public repo, in `saved` she
typed it herself, but an env var was set by somebody else, possibly months ago,
and the app is the only place she can see it. The status line already tells her
"they'll need to change it there" (`copy.md` §4) — and the very first thing that
person will ask is *"what does it say?"*

Therefore, and this is a real exception to the shipped spec: `interactions.md`
§3.4 disables the input and Save in the `env` state and removes
`#clientIdActions` from the DOM. **The value block and its toggle are exempt.**
They are read-only — there is nothing to disable, and disabling them would be
cargo-culting "env means read-only" onto a control that is already read-only,
in the exact state where it is most needed.

**`builtin` — no value block at all.** The deliberate call, and the one worth
arguing.

The built-in ID belongs to the app author's Yoto developer registration. The
user has no dashboard entry to compare it against, so the comparison task — the
only reason this feature exists — **does not exist in this state**. Nor is there
a diagnostic gap: `client_id_source` fully determines the value, so
"Using the built-in Client ID" is already a complete and unambiguous answer to
"what is it using?". Rendering 32 characters and a disclosure control directly
beneath the sentence *"This is what most people use. Nothing to do here."*
would contradict that sentence for every user who ever opens this screen, to
serve no task.

This is also the state ~every user is in, which makes it the one place the
section's weight actually matters. It stays exactly as heavy as it is today.

The rule this establishes, which setting #7 should inherit:

> **Show a value back to the user when a person deliberately set it.** If the
> app chose it, the source label is the whole answer and the value is noise.

Consistent with the section's existing behavior: `#clientIdActions` is already
state-conditional (shown in `saved`, hidden in `builtin`, removed in `env`).

### 11.5 Where it goes, and why the primitive is not touched

Slot 3 (Status) is closed to this by rule §4.3.2 — *"never surface a raw stored
value"* — which is the rule that stops a 32-character string being jammed into a
status sentence, and it is correct. **Slot 4 (Body) is the answer**: the body is
the setting's value area, and the current value belongs directly above the input
that replaces it.

The markup nests inside the existing `#clientIdBody` and produces two
structurally parallel rows:

```
The one you’re using now
[ a8OG…oU1                        ]  [ Show the whole thing ]
Paste a different Client ID
[                                 ]  [ Save                 ]
```

Both rows are the existing `.row.wrap` + `.grow`, which `interactions.md` §5
already certifies as collapsing correctly at narrow widths.

**Nothing in the `.setting` primitive changes.** Seven slots, same order, same
classes, and `tokens.md` §3's `.setting*` block is untouched — no new rule, no
edited rule, and in particular no id selector and no positional selector, which
is the property that was verified adversarially at merge. The only new CSS is
`.mono-value` (`tokens.md` §3a), a standalone utility that touches nothing in
the `.setting*` block.

Two wording clarifications were needed and are marked in place (§4.1 slot 4,
§4.3.3 scope). Both answer questions the primitive did not previously answer.
Neither adds a slot, and if Mark reads either as a widening rather than a
clarification, that is the thing to push back on.

### 11.6 Knock-on fix: the status sub-line stops carrying the value

With the value shown in the body where it belongs, `copy.md` §4's `saved`
sub-line drops its value fragment and becomes simply
`Saved on this computer only.`

Worth noting for the record: `Ends in {last3}.` was always a mild breach of
§4.3.2 — a stored-value fragment inside a status sentence — tolerable as prose
when it was the only way to identify the value at all. This amendment removes
the need, so the breach goes with it, along with the `last3` slicing and its
empty-string degradation at `app.js:499-508`. **The feature leaves the primitive
more consistent than it found it**, which is the bar an extension should clear.
