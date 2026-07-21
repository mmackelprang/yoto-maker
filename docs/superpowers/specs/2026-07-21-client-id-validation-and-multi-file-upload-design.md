# Design spec — Client ID validation + multi-file audio upload

**Date:** 2026-07-21
**Status:** proposed — needs Mark's approval before Planner picks it up
**Ships as:** one PR, two separable sections. Item A first.

**Relationship to existing handoffs:**

| Item | Package | Declaration |
| --- | --- | --- |
| **A** — Client ID validation, bad-value flagging, config summary | [`configuration-surface/`](../../design-handoffs/configuration-surface/) | **extends.** Deviates from nothing. All three layers are expressed inside the existing `.setting` primitive (`overview.md` §4) with **zero new CSS and zero new tokens**. |
| **B** — multi-file audio upload | *none exists* | **follows** the card view's shipped vocabulary (`.progress`, `.msg-box`, `.tracks`, `.tiny`). Introduces no new visual vocabulary. **See §B.0 — this surface has no handoff package and that needs a decision from Mark.** |

---

# The incident this spec answers

A real user this week. Her authorize URL was:

```
https://login.yotoplay.com/authorize?response_type=code&client_id=mandydeogie%40gmail.com&…
```

She typed her **email address** into `Yoto Client ID (advanced)`. The app accepted
it (`app.py:515` validates only non-emptiness), saved it, and called `logout()` —
**destroying a working sign-in** and dropping her on an Auth0 error page in a
different browser tab, on a domain Yoto Maker does not control, with copy neither
she nor the app can interpret.

## The insight the design is built on

**Visibility already existed, and it still failed.**

PR #10 and the `884fa6a` amendment put the Client ID on screen: masked, with a
`Show the whole thing` disclosure. That shipped. It did not help, and the reason
is specific and instructive:

```
mask_client_id("mandydeogie@gmail.com")  →  "mand…com"
```

The mask deleted **`@gmail.com`** — the exact substring that would have made the
mistake self-evident — and what survived (`mand…com`) reads as *more* code-like
than the original, not less. A user checking her own setting would have looked at
`mand…com`, recognised nothing wrong, and moved on.

So "show the value" is not the fix. **Detection is.** Everything below follows
from that.

It also produces a rule that generalises, and §A.3.2 applies it:

> **The mask is the summary form of a value that has the expected shape.**
> Applied to a value that does not, it is not a summary — it is camouflage.
> Any value that fails the shape check renders **in full, unmasked, with no
> disclosure control.**

---

# ITEM A — malformed Client ID detection, blocking, and config visibility

## A.0 The validation rule — two tiers, two consequences

> **Decision: the hard gate uses a deny-list of definitely-wrong shapes. The
> strict 32-character rule is used only as advice.**

This is the single most important decision in Item A, because the gate is now
**hard** (Mark, this session: *"this is def a place where fail fast wins"*), and
a hard gate's failure mode is a lockout.

### A.0.1 The two verdicts

Every resolved Client ID gets exactly one verdict.

| Verdict | Rule | Consequence |
| --- | --- | --- |
| **`invalid`** | Contains `@`, or interior whitespace, or `/`, or `:`, or `<`, or `>`; or is empty after trimming; or is longer than 128 characters. | **Hard.** Save refused. Sign-in blocked before the request is constructed. Red status. |
| **`unusual`** | Passes the above, but does **not** match `^[A-Za-z0-9]{32}$`. | **Soft.** Save allowed after a confirmation that names the concern. Sign-in proceeds. Amber status. Value rendered unmasked. |
| *(ok)* | Matches `^[A-Za-z0-9]{32}$`. | Today's behavior, unchanged. |

### A.0.2 Why the hard gate is the deny-list and not the 32-char rule

The 32-character alphanumeric shape is **confirmed against the shipping default**
(`config.py:44`, `a8OGO6EfbWit5tDUUrOz0g49s49NQoU1` — 32 chars, all alphanumeric).
It is correct *today*. It is knowledge about a third party's current format, and
the app has no way to learn that it has changed.

A hard gate must only fire on things that are wrong **regardless of format**.
`@` is not a character in an opaque identifier; it is the character that means
*address*. `/` and `:` mean *URL* — and this matters concretely, because
`SETUP-YOTO-CONNECTION.md:30` prints `http://127.0.0.1:8777/yoto/callback`
directly beside the Client ID the user is told to copy, so pasting the wrong one
is a live, designed-in risk. Interior whitespace means *a phrase, or a paste that
grabbed a line break*. None of these can become valid if Auth0 changes its format.

**Stated plainly, as asked — what breaks under each:**

| | Strict allow-list as the hard gate | **Deny-list as the hard gate (recommended)** |
| --- | --- | --- |
| Catches the incident (`mandydeogie@gmail.com`) | ✅ | ✅ — the `@` alone catches it |
| Catches a pasted URL | ✅ | ✅ — `/` and `:` |
| Catches a truncated paste (`a8OGO6EfbWit5tDUU`) | ✅ blocks | ◻ warns, then allows |
| **Yoto issues 40-char IDs tomorrow** | ❌ **Every legitimate new ID is hard-blocked. A self-configured user cannot sign in at all, and the app tells her — confidently, in red — that her correct value is wrong. Recovery requires a code change and a release.** | ✅ Nothing breaks. New IDs save and sign in normally. |
| **Yoto issues IDs containing `-` or `_`** (UUID / base64url shapes, both common in this industry) | ❌ hard-blocked | ✅ nothing breaks |
| Yoto issues IDs containing `@` or `/` | ❌ blocked | ❌ blocked — accepted, because no identifier format in the OAuth world does this; those characters are reserved for addresses and URLs |
| Cost of a **false positive** | **Total lockout with no override.** | **None** — the value lands in `unusual`, which warns and proceeds. |
| Cost of a **false negative** | n/a | A truncated paste fires one doomed request. She saw the `unusual` warning and pressed through, so the Auth0 error is expected rather than mystifying. |

The deny-list is deliberately **narrow**. Two exclusions worth naming, because
they demonstrate the principle rather than merely applying it:

- **`.` is NOT on the deny-list.** A domain (`yotoplay.com`) has a dot and no `@`,
  so the temptation is real. But dotted identifiers exist elsewhere in this
  industry (`…apps.googleusercontent.com`), and the cost of being wrong is a
  lockout. A dotted value lands in `unusual`, gets warned about, and can be
  pushed through.
- **`-` and `_` are NOT on the deny-list.** They are the two most common
  characters in machine identifiers. Denying them would be the fastest possible
  way to build the lockout this section exists to prevent.

The 128-character bound is a sanity limit (she pasted a document), not a format
rule. Any real paste that long almost certainly contains whitespace already; the
bound exists so `settings.json` cannot be filled with prose.

**There is no lower length bound in the deny-list.** A 3-character value is
obviously wrong, but "obviously" there is format knowledge, and format knowledge
does not get to hard-block. It lands in `unusual`.

### A.0.3 Where the rule lives

**One function, in `config.py`, beside `_resolve_client_id_with_source()`** — the
same anti-drift discipline `overview.md` §7.2 already relies on. It returns the
verdict **and** a reason code, because the copy differs by reason:

```
verdict ∈ { "ok", "unusual", "invalid" }
reason  ∈ { null, "email", "url", "spaces", "length", "charset", "too_long" }
```

Planner: the frontend and the two server call sites (`POST /api/yoto/client-id`,
`start_login()`) must all read this one function. A second implementation is how
the save gate and the sign-in gate come to disagree, and a user who is allowed to
save a value she is then not allowed to use is in a worse state than the one this
spec is fixing.

**Required test, and it is not optional:** assert `DEFAULT_YOTO_CLIENT_ID` scores
`ok`. A validator that rejects the shipped default bricks the app for every user
on first run, and it is the one failure this whole design cannot recover from —
"Go back to the built-in one" would go back to a value the app refuses.

---

## A.1 Layer 1 — refuse at save, before `logout()`

> **The critical property: the refusal must run before anything is written and
> before `logout()` fires, so a user with a working sign-in never loses it to a
> typo.**

### A.1.1 The ordering is the feature, and the copy is its contract

`app.py:515` today:

```python
cid = body.client_id.strip()
if not cid: raise HTTPException(400, "Please paste a Client ID first.")
get_settings().set("yoto_client_id", cid)   # ← writes
logout()                                     # ← destroys the working sign-in
```

The verdict check goes **above the `set()`**. Nothing else moves.

The refusal copy ends with a reassurance line (§A.1.3) that says *nothing was
changed and you're still signed in*. **That sentence is only true because of the
ordering.** If a future refactor moves the check below `set()` or `logout()`, the
copy silently becomes a lie — so the copy is the readable statement of the
invariant. Planner should carry this note into the plan verbatim: **if the
reassurance line is true, the ordering is correct; if the ordering changes, the
line must change with it.**

### A.1.2 Never confirm an action that will be refused

The client validates with the same rule **before opening the save confirmation.**

This is not a new rule — it **extends** `interactions.md` §3.2 step 1, which
already says: *"Empty → show `Please paste a Client ID first.`, focus the input,
stop. **No confirmation for an empty save** — never confirm a no-op."*

Showing the existing confirmation for a value that will be refused would ask the
user to accept a frightening consequence (*"you'll need to sign in to Yoto
again"*) that is never going to happen, and then error at her. Same rule,
extended from *no-op* to *no-op or refusal*.

The client check is for the honesty of the confirmation flow. **The server check
is the actual safety property** and is non-negotiable — it is what protects a
user running a stale `app.js`, which is a failure mode this project has already
been bitten by (`overview.md` §12.1).

### A.1.3 Refusal copy — verbatim

Rendered in the section's existing feedback slot, `#clientIdMsg`
(`.msg-box err`, `role="alert"`). **No new region** — `interactions.md` §4.3
prohibits a second live region in one section, and this needs none.

Three paragraphs each: *what you entered* / *what it should be* / *reassurance*.
The `.msg-box` renders one text node today; Planner will need it to take an array
of paragraphs. Precedent exists in the same file — `CLIENT_ID_CONFIRM.body` is
already `[…]` of paragraphs.

---

**Case 1 — `reason: "email"` (contains `@`). The observed real failure.**

> That looks like an email address, not a Client ID.
>
> A Client ID is a code from Yoto's developer website — letters and numbers, with
> no @ sign. It isn't the email address you sign in to Yoto with.
>
> {reassurance}

---

**Case 2 — `reason: "url"` (contains `/` or `:`).**

> That looks like a web address, not a Client ID.
>
> The setup page shows a web address and a Client ID next to each other, and it's
> easy to copy the wrong one. The Client ID is the shorter one — just letters and
> numbers.
>
> {reassurance}

---

**Case 3 — `reason: "spaces"` (interior whitespace) or `"too_long"`.**

> That doesn't look like a Client ID.
>
> A Client ID is one unbroken run of letters and numbers, with no spaces. It may
> help to copy it again from Yoto's developer website.
>
> {reassurance}

---

**The reassurance line is state-dependent**, following the rule this package
already applies twice (`copy.md` §1a and §4 both make a string conditional
because a word would otherwise be false):

| `STATUS.yoto.connected` | Line |
| --- | --- |
| `true` | `Nothing was changed, and you're still signed in to Yoto.` |
| `false` | `Nothing was changed.` |

*"You're still signed in"* is false when she isn't, and a reassurance that is
audibly wrong about her situation costs more trust than it buys.

### A.1.4 The `unusual` save — allowed, with the concern named

An `unusual` value is **saved**, but the existing confirmation gains one
paragraph, inserted **first**, above `Yoto Maker will start using the Client ID
you pasted.`:

> Just so you know: a Client ID is usually 32 letters and numbers, and this one
> isn't. If you're sure it's right, go ahead.

No new UI. The confirmation slot already exists and already carries multi-paragraph
bodies. Buttons unchanged: `Never mind` / `Yes, use it`.

### A.1.5 Focus and input handling on refusal

Mirrors `interactions.md` §3.2 exactly — this case does not get its own rules:

1. Show the message. 2. Focus `#clientIdInput`. 3. **Leave the input's value
intact** (§3.2 step 5: *"so nothing the user pasted is lost"*). 4. Do not open the
confirmation. 5. Do not touch the value display, the actions, or the account
section.

**Select-all on focus was considered and rejected.** It would make a corrected
paste a single action, but §3.2's existing behavior is focus-only, and the user's
first job here is to *read* what she typed and recognise it. Consistency wins over
a marginal keystroke.

---

## A.2 Layer 2 — flag an already-saved bad value

This is the layer that helps the user who is broken **right now**. Layer 1 only
prevents recurrences; her `settings.json` already holds an email address.

Today her Settings screen renders a **green dot** and *"Using your own Client ID /
Saved on this computer only."* — the same class of untruth as the `connected`
field that `overview.md` §7.5 had to replace with a live check.

### A.2.1 Status line — the full state table

Replaces `copy.md` §4's three-row table. `#clientIdStatus`, the existing
`role="status"` region. **No second live region** — `interactions.md` §4.3.

| `source` | verdict | Dot | Headline | Sub-line |
| --- | --- | --- | --- | --- |
| `builtin` | ok | green `is-ok` | `Using the built-in Client ID` | `This is what most people use. Nothing to do here.` |
| `saved` | ok | green `is-ok` | `Using your own Client ID` | `Saved on this computer only.` |
| `saved` | unusual | amber `is-warn` | `Using your own Client ID` | `Saved on this computer only. It isn't the usual 32 letters and numbers, so signing in to Yoto may not work.` |
| `saved` | invalid, `reason: "email"` | **red `is-err`** | `That's an email address, not a Client ID` | `Yoto Maker can't sign in to Yoto until this is fixed. Press "Go back to the built-in one" below.` |
| `saved` | invalid, any other reason | **red `is-err`** | `This isn't a Client ID` | `Yoto Maker can't sign in to Yoto until this is fixed. Press "Go back to the built-in one" below.` |
| `env` | ok **or unusual** | amber `is-warn` | `Set outside the app` | *(unchanged from `copy.md` §4)* |
| `env` | invalid | **red `is-err`** | `Set outside the app, and it isn't a Client ID` | `YOTO_CLIENT_ID on this computer holds something that isn't a Client ID, so signing in to Yoto will probably fail. To change it, they'll need to change it there.` |

Three notes on the table's shape:

**The email case gets its own headline.** This spec's thesis is that *naming* the
mistake is what visibility failed to do. Being explicit in the save refusal while
being coy in the status line would be inconsistent, and this is the exact user in
the incident.

**`env` + `unusual` deliberately gets no row of its own.** On a value a developer
set on purpose, "that isn't the usual shape" is precisely the false-positive noise
§A.0.2's conservative principle says to suppress. We speak up on `env` only when
the value is definitely wrong.

**The sub-line points at the recovery by its literal label.** This is the house
pattern — `copy.md` §4's two success messages both do exactly this (*"Now sign in
to Yoto again using the button above."*). It makes the affordance obvious without
moving it, which matters because §4.3.1 fixes slot order and the recovery lives in
slot 5, below slot 4.

### A.2.2 The value renders in full — the mask is suppressed

The rule from the top of this document, applied:

| verdict | `#clientIdValue` | `#clientIdReveal` toggle |
| --- | --- | --- |
| ok | masked (`a8OG…oU1`) | shown |
| **unusual** | **full** | **omitted** |
| **invalid** | **full** | **omitted** |

This is a **fourth and fifth row in `interactions.md` §3.5.2's existing table**,
using the mechanism that table already establishes: *the toggle is omitted, never
disabled, whenever it could do nothing.* Here it could do nothing because the
whole value is already displayed — the same logic as that table's `masked === full`
row, reached by a different route.

`unusual` matters as much as `invalid` here. A truncated paste of 17 characters
masks to `a8OG…tDU`, which **hides the truncation completely** and looks entirely
plausible. The mask would actively conceal the one thing she needs to see.

`.mono-value` is unchanged and does the rest: monospace makes `@` and `.`
unmistakable, and `word-break: break-all` wraps a long value inside the column
(`tokens.md` §3a).

### A.2.3 How the bad entry is visibly flagged

Mark asked for the bad entry to be visibly flagged. It is, by three things
already on screen and one that is now unhidden:

1. A **red dot** in the status line — `is-err`, an existing modifier.
2. A **headline that names the problem** rather than the state.
3. **The value in full, unmasked**, directly beneath it.
4. The recovery named by its literal label in the sub-line.

**Red text on `.mono-value` was considered and rejected.** `--err` on `--card`
measures 5.62:1 (`tokens.md` §4) so it would pass AA — but this package reserves
status colors for **dots and borders, never body text**, and `tokens.md` §1 argued
that position at length for `--warn` (*"a variant that can only be used
incorrectly is a trap for whoever adds setting #5"*). A 32-character monospace
string set in red is also simply harder to read, at the exact moment reading it is
the task.

**The `The one you're using now` label stays constant across all verdicts.** A
second problem-naming string 20px below the headline is the duplication §11.6 was
pleased to remove; one conditional avoided.

### A.2.4 Recovery is never a dead end

In `saved`-invalid the user has **two** working recoveries, and both must stay
live:

- **`Go back to the built-in one`** — slot 5, promoted to `.btn primary` in this
  state. This does not breach §4.3.4 (*one primary per setting*): the Client ID
  section has **no** primary today (`Save` and the reset are both plain `.btn`),
  so promoting one is within budget. It is the only state in which this section
  has a primary action.
- **Pasting a correct Client ID** — the input and `Save` remain fully enabled. The
  block is on *signing in*, never on *fixing it*.

### A.2.5 Zero new CSS

Every state above is `is-err` / `is-warn` / `.btn primary` / `.mono-value` /
`.hidden` — all shipped. **Item A introduces no new token, no new utility, and no
new rule.** `tokens.md` needs no amendment, which is the strongest available
evidence that this extension fits the primitive rather than straining it.

---

## A.3 Layer 3 — the config summary

Mark asked to "show the current values on the config screen." The use case, stated
as a scenario because it decides every question below: **a parent on the phone
with whoever set this up, being asked to read out what the app says.**

### A.3.1 Which values earn a place

| Value | In? | Why |
| --- | --- | --- |
| App version | ✅ | First question anyone asks. In the footer and About modal, but a summary without it is not a summary. |
| Effective Client ID (masked) | ✅ | The value this whole spec is about. |
| Which tier supplied it | ✅ | The second question the helper asks, and the one `client_id_source` exists to answer. |
| **OAuth redirect URI** | ✅ | **The highest-value row.** `SETUP-YOTO-CONNECTION.md:30` requires this exact string in the Yoto dashboard, and warns *"This must match exactly"*. A mismatch produces an Auth0 error page — **the same failure mode as the incident, from a different cause.** Nothing in the app displays it today. |
| Port | ❌ **folded in** | `http://127.0.0.1:8777/yoto/callback` contains the port. A separate row would repeat it. |
| Data dir | ✅ | Where `settings.json`, the token file and the log live. "Where is the log file" is the support question. |
| ffmpeg / yt-dlp status | ❌ | The card view already has a tools warning banner. Out of scope; do not grow this section. |

### A.3.2 Placement and disclosure

> **Decision: a third `.setting` section, placed last, always visible. No
> disclosure.**

`overview.md` §2's *"must not get one pixel heavier"* constraint governs the
**card view**, which this does not touch. Within the settings view the real
question is whether a technical block distracts the frustrated user who came to
repair her connection — and **being last answers that without a control.** She
never scrolls there. Position does the work a disclosure would have done.

And a disclosure would actively hurt the one use case: on the phone, a collapsed
block turns *"read me what it says at the bottom"* into *"no, first press the grey
button that says…"*.

Per `overview.md` §4.4 this is *copy the template, fill the slots, append* — the
procedure the primitive was designed to pass. Slots used: Title, Description,
Body. Status, Actions and Confirmation are omitted.

**One note on slot 6.** §4.1 marks Feedback as required-in-markup, but this is the
first **read-only** section and it has no action that could produce feedback.
**Include the empty hidden `.msg-box` anyway.** §4.2 says *"treat this as the
literal template"*, and amending the primitive to carve out an exception for one
section would be exactly the kind of widening §11.5 worked to avoid. One empty div
is cheaper than a clarification to a rule that has held twice.

### A.3.3 Copy — verbatim

**Title**

> If you need to ask for help

**Description**

> If something isn't working and you're asking someone for help, these are the
> details they'll ask for. Nothing here can be changed — it's just what Yoto Maker
> is using right now.

*(The second sentence is doing real work. A parent who scrolls into a block of
technical values needs to be told immediately that she cannot break anything by
looking at it. Same instinct as `copy.md` §3's "Nothing in your Yoto account
changes.")*

**The rows** — label in `.tiny` above the value, stacked, matching the
`The one you're using now` construction exactly (`interactions.md` §3.5.1). Not a
two-column table: values wrap under `break-all`, and a two-column layout at 720px
with wrapping values produces ragged rows.

| # | Label | Value | `.mono-value`? |
| --- | --- | --- | --- |
| 1 | `Version` | `0.1.10` | ✅ |
| 2 | `Client ID in use` | `a8OG…oU1` | ✅ |
| 3 | `Where that came from` | `Built in` / `Saved on this computer` / `Set outside the app` | ❌ prose |
| 4 | `Sign-in address` | `http://127.0.0.1:8777/yoto/callback` | ✅ |
| 5 | `Where Yoto Maker keeps its files` | `C:\Users\…\AppData\Local\Yoto Maker` | ✅ |

**Row 4's label.** `SETUP-YOTO-CONNECTION.md` calls it *"the redirect URL"* and
*"redirect/callback URL"*. `Sign-in address` is plainer and passes the register
test, but it must be **matchable** against the guide — that is the §12.2 lesson,
and it is the one thing here I would not want to get wrong on my own judgement.
See **§A.6, decision 2.**

**Row 2 obeys the mask suppression rule.** When the verdict is `unusual` or
`invalid`, this row shows the **full** value, exactly as §A.2.2 specifies for
setting 2. A summary that re-masks a bad value would undo, 200px lower, the fix
directly above it.

**No drift risk between this section and setting 2.** Both render from the same
`STATUS.yoto` object in the same pass — the same guarantee `overview.md` §7.2
relies on. Row 2 shows the masked form only; **there is exactly one reveal toggle
on this surface**, and it stays in setting 2 where the value's controls live.

### A.3.4 A copy button was considered and rejected

`tokens.md` §3a already rejected one for the Client ID: *"a copy button would need
its own transient 'Copied!' state and clipboard-failure path"*. That reasoning
carries. The stated use case is **reading aloud**, which a copy button does not
serve at all, and the block is five short lines she can select with a mouse.

If Mark wants the *email-the-details* flow instead, that is a different feature
with a different justification, and it should be scoped on its own.

### A.3.5 Backend — Planner must scope

`/api/status` gains a `config` object. Values must come from the server; none may
be constructed in JS (the port is not a constant — `config.py:108` notes it is
"chosen at runtime if busy", so a hardcoded frontend string would be wrong exactly
when it matters most).

```jsonc
"config": {
  "version": "0.1.10",
  "redirect_uri": "http://127.0.0.1:8777/yoto/callback",
  "data_dir": "C:\\Users\\…\\AppData\\Local\\Yoto Maker"
}
```

`redirect_uri` should come from `auth.py:56`'s `_redirect_uri()` — the same
function `start_login()` uses — so the displayed string and the sent string cannot
disagree. That is the whole point of showing it.

And on `yoto`, two fields derived from the §A.0.3 function:

```jsonc
"client_id_verdict": "ok" | "unusual" | "invalid",
"client_id_reason":  null | "email" | "url" | "spaces" | "length" | "charset" | "too_long"
```

---

## A.4 Layer 4 — the hard block on the sign-in flow

> **Settled by Mark this session: if the resolved Client ID is `invalid`, prevent
> the sign-in flow completely. Never construct or fire the authorize request.**

### A.4.1 Why this is the layer that actually rescues the broken user

Layers 1–3 are prevention and repair-once-you-look. This is the one that reaches
the user in the incident, and the reasoning is the package's own:

1. **Her `settings.json` is already bad.** Layer 1 arrives too late for her.
2. **She has no reason to open Settings.** Her symptom is "connecting doesn't
   work", and the error is on *Auth0's page in another tab*. Nothing in Yoto Maker
   says anything is wrong.
3. **`overview.md` §5.1 and §12.4 both established: follow the symptom.** The
   symptom is the connect button. The recovery must be adjacent to it, not two
   navigations away — this is the same argument §12.4 used to move `#advRow` to
   sit beneath `#sendError`.
4. **The alternative is the worst outcome available**, and it is the one that
   actually happened: a doomed request produces an Auth0 error page on a foreign
   domain, with copy Yoto Maker cannot control and the user cannot interpret.
5. **It costs the healthy path nothing.** The check is a string test on a value
   already in `STATUS`, and it renders nothing when the verdict is `ok`.

### A.4.2 The env tier is treated differently — recommendation and justification

> **Recommendation: hard-block on `saved`. On `env`, warn loudly and proceed.**

This is an asymmetry and it needs to earn its place. Four reasons, the first
decisive:

**1. The block's entire value is that it comes with a recovery, and on `env` there
is none.** Mark's own guard rail says every blocked state must carry the recovery
affordance inline. On `saved` that is one button. On `env` the reset control is
**absent by design** — `overview.md` §7.4 removed it because deleting the saved
value falls through to the env var, not the built-in one, so the label would lie.
A hard gate whose recovery affordance cannot exist is not fail-fast; it is a wall.
The honest response to *"I cannot satisfy the guard rail in this state"* is to not
ship the block there — not to ship a block that violates it.

**2. The env tier is authenticated by construction.** Setting an environment
variable requires a terminal or a system dialog. It is not something a confused
parent does by accident. Whoever set it knows what a Client ID is, will read the
warning and understand it immediately, and **has shell access** — which is exactly
the recovery mechanism the app cannot offer them.

**3. This repo already contains a legitimate non-conforming env value.**
`tests/conftest.py` injects `YOTO_CLIENT_ID="test_client_id"` — 14 characters with
an underscore. It passes the deny-list, so it is not blocked under the
recommendation. But it is a live, in-tree demonstration that this tier carries
values the app should not be opinionated about, and it is precisely the kind of
value a strict uniform gate would have broken.

**4. The consequence is asymmetric, so the gating should be.** A developer who
fires a doomed authorize request sees an Auth0 error and knows what it means. The
parent who sees that page does not — she calls someone. The block exists to
protect the person who cannot interpret the failure.

**What "warn loudly" means on `env`, concretely:**

- Settings: **red dot**, and a headline that names the problem (§A.2.1's last row).
  This is a genuine escalation from today's amber — `env` currently never goes red.
- Card view: **nothing proactively.** When `🔗 Connect my Yoto account` is pressed,
  show an advisory in `#connectWarn` (below) **and send the request anyway.**

**Copy — `env` + `invalid`, advisory, `.msg-box info`:**

> Heads up: YOTO_CLIENT_ID on this computer doesn't hold a Client ID, so Yoto will
> probably refuse this sign-in. Yoto Maker is trying anyway, because that value
> was set on purpose.

*Register exception, and it is licensed.* This string names an environment
variable and addresses a developer. `copy.md` §4 already established that exact
exception for this exact tier: *"the only place in the app where an environment
variable name is spoken to the user… a deliberate, narrow exception"*.

**`builtin` + `invalid` is not designed for.** It is unreachable in a correct
build and the recovery ("go back to the built-in one") would be meaningless. It is
prevented by the required test in §A.0.3, which is the right layer for it.

### A.4.3 The block, on `saved` + `invalid`

**The connect button stays enabled.** Disabling it with no visible reason is the
dead-end antipattern `interactions.md` §2.2 warns against (*"Never dead-end her"*).
Pressing it is the **fastest path to the explanation** — the press does not send a
request, it renders the block. Follow-the-symptom, completed.

**Where the block renders.** A new `.msg-box err` in step 3, `#connectWarn`,
placed as the **second-to-last child — immediately above `#advRow`**, so it sits
directly above the ⚙️ link it refers to.

Two constraints on the element, both load-bearing:

- It must **not** be `#sendError`. Both `connectYoto()` and `sendToYoto()` call
  `clearError($("#sendError"))` on entry, so a config warning parked there would be
  wiped by an unrelated action.
- Placing it above `#advRow` rather than below preserves §12.4's rule that
  `#advRow` is the last child and never moves.

Rendered by `renderStatus()`, proactively — this state is never the everyday path,
so §2's weight constraint is not engaged. In the `ok` state it renders nothing.

**Copy — `saved` + `invalid`, blocking, `.msg-box err`:**

> Yoto Maker can't sign in to Yoto, because the Client ID saved on this computer
> isn't one.
>
> `[ Put back the built-in Client ID ]`

The button is the **inline recovery** Mark's guard rail requires. It does **not**
perform the reset. It navigates to Settings **and opens the reset confirmation
already showing**, scrolled to the Client ID section.

**Why not perform the reset directly.** The reset signs her out and forgets her
value — `copy.md` §4 gives it a confirmation, and that confirmation carries the
sentence answering the fear she actually has (*"Nothing in your Yoto account
changes."*). A one-press control on the card view would skip it. Routing to the
armed confirmation is **one press from symptom to consequences**, and it composes
with the existing flow rather than bypassing it.

*Planner note:* this is a deep link. A module-level `pendingIntent` set before
`gotoSettings()` and consumed by the settings-view open handler is sufficient —
`interactions.md` §1.1 already runs an on-open sequence this can hook into. Do not
add a second hash route.

**The button is absent on `env`** (there is nothing for it to do — §A.4.2), which
is the same "omitted, not disabled" discipline `interactions.md` §3.5.2 and
`overview.md` §7.4 both already apply.

### A.4.4 Server-side gate

`start_login()` (`auth.py:74`) must refuse when the resolved verdict is `invalid`
**and** the source is `saved`, raising an `AuthError` carrying the reason code —
defense in depth against a stale `app.js`, which this project has shipped before
(`overview.md` §12.1).

The frontend already has the pattern for consuming it:
`SIGNIN_ERRORS[e.data && e.data.reason]` at `app.js:1033`. Reuse it; do not invent
a second error-mapping mechanism.

**The server gate must match the frontend gate exactly** — `saved` + `invalid`
only, never `env`. A server that refuses what the frontend permits produces a
button that fails with no explanation, which is worse than either behavior alone.

### A.4.5 Out of scope for the block

**`sendToYoto()` is not gated.** An invalid Client ID with a stale token fails at
refresh, which is a different failure with its own existing error path. Adding a
second gate there is scope this PR does not need.

---

## A.5 Mockups

### A.5.1 Settings — `saved` + `invalid` (the daughter's screen, today)

```
   ┌─────────────────────────────────────────────────────────────┐
   │ Yoto Client ID (advanced)                                   │
   │                                                             │
   │ Most people never need to change this. …                    │
   │                                                             │
   │ ● That's an email address, not a Client ID       (red dot)  │
   │   Yoto Maker can't sign in to Yoto until this is fixed.     │
   │   Press "Go back to the built-in one" below.                │
   │                                                             │
   │ The one you're using now                                    │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ mandydeogie@gmail.com                       .mono-value │ │  ← IN FULL.
   │ └─────────────────────────────────────────────────────────┘ │    No toggle.
   │        ▲ no "Show the whole thing" — the whole thing is     │    The mask
   │          already here, and mask_client_id() would have      │    said
   │          rendered this as "mand…com"                        │    "mand…com"
   │                                                             │
   │ Paste a different Client ID                                 │
   │ ┌───────────────────────────────────────┐  ┌──────┐         │
   │ │ Paste your Yoto Client ID here        │  │ Save │         │
   │ └───────────────────────────────────────┘  └──────┘         │
   │        ▲ still fully enabled — the block is on signing in,  │
   │          never on fixing it                                 │
   │                                                             │
   │ ┌───────────────────────────────┐                           │
   │ │ Go back to the built-in one   │  ← .btn primary in this   │
   │ └───────────────────────────────┘    state only             │
   └─────────────────────────────────────────────────────────────┘
```

### A.5.2 Save refused — the session survives

```
   │ Paste a different Client ID                                 │
   │ ┌───────────────────────────────────────┐  ┌──────┐         │
   │ │ mandydeogie@gmail.com                 │  │ Save │         │
   │ └───────────────────────────────────────┘  └──────┘         │
   │        ▲ value LEFT INTACT, focused                         │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ That looks like an email address, not a Client ID.      │ │
   │ │                                            .msg-box err │ │
   │ │ A Client ID is a code from Yoto's developer website —   │ │
   │ │ letters and numbers, with no @ sign. It isn't the       │ │
   │ │ email address you sign in to Yoto with.                 │ │
   │ │                                                         │ │
   │ │ Nothing was changed, and you're still signed in to      │ │  ← true ONLY
   │ │ Yoto.                                                   │ │    because the
   │ └─────────────────────────────────────────────────────────┘ │    check runs
   │                                                             │    before
   │   NO confirmation was shown. NO write. NO logout().         │    logout()
```

### A.5.3 Step 3 — the hard block, with recovery inline

```
   ┌─────────────────────────────────────────────────────────────┐
   │ (3) Send it to your Yoto                                    │
   │ …hint…                                                      │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ You'll need to connect your Yoto account first.          │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │           🔗 Connect my Yoto account                    │ │  ← STAYS
   │ └─────────────────────────────────────────────────────────┘ │    enabled
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │              🚀 Send to Yoto        (disabled)          │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Yoto Maker can't sign in to Yoto, because the Client ID │ │  #connectWarn
   │ │ saved on this computer isn't one.          .msg-box err │ │  (new)
   │ │                                                         │ │
   │ │  ┌──────────────────────────────────┐                   │ │
   │ │  │ Put back the built-in Client ID  │ ← goes to Settings│ │
   │ │  └──────────────────────────────────┘   with the reset  │ │
   │ └─────────────────────────────────────────┘  confirmation │ │
   │                                              already open │ │
   │ ⚙️ Yoto connection settings                                 │  ← #advRow
   └─────────────────────────────────────────────────────────────┘    stays last

   In the "ok" state #connectWarn renders nothing at all.
   The everyday path is byte-for-byte what it is today.
```

### A.5.4 The config summary — setting 3, last

```
   ┌─────────────────────────────────────────────────────────────┐
   │ If you need to ask for help                          h3     │
   │                                                             │
   │ If something isn't working and you're asking someone for    │  .setting-desc
   │ help, these are the details they'll ask for. Nothing here   │
   │ can be changed — it's just what Yoto Maker is using right   │
   │ now.                                                        │
   │                                                             │
   │ Version                                              .tiny  │
   │ 0.1.10                                         .mono-value  │
   │                                                             │
   │ Client ID in use                                            │
   │ a8OG…oU1                                                    │
   │                                                             │
   │ Where that came from                                        │
   │ Built in                                          (prose)   │
   │                                                             │
   │ Sign-in address                                             │
   │ http://127.0.0.1:8777/yoto/callback                         │  ← must match
   │                                                             │    the Yoto
   │ Where Yoto Maker keeps its files                            │    dashboard
   │ C:\Users\mandy\AppData\Local\Yoto Maker                     │    exactly
   └─────────────────────────────────────────────────────────────┘

   No Status slot. No Actions slot. No Confirmation slot.
   Slot 6 (.msg-box) present but hidden — the template is copy-paste.
```

---

## A.6 Decisions I need from Mark

**1. Three-paragraph refusal messages need `.msg-box` to render paragraphs.**
`clientIdMsg()` sets `textContent` today. The precedent for an array of paragraphs
already exists in the same file (`CLIENT_ID_CONFIRM.body`). Confirm you're happy
extending `.msg-box` to take one, or say the word and I'll compress each refusal to
a single paragraph — it will lose the reassurance line's visual separation, which
is the sentence doing the most work.

**2. Row 4's label: `Sign-in address` vs the guide's vocabulary.**
`SETUP-YOTO-CONNECTION.md` says *"redirect URL"* and *"redirect/callback URL"*.
`Sign-in address` reads better for the parent; *"Redirect URL"* is what the helper
and the Yoto dashboard say. The §12.2 lesson was that **matchability beats
plainness** when a user is comparing against another screen — which argues for the
guide's words here. My inclination is `Sign-in address (redirect URL)` carrying
both, but that is a hedge and hedges are usually the wrong answer. Your call.

**3. `env` + `invalid` — is warn-and-proceed acceptable?** §A.4.2 is my
recommendation with the reasoning laid out. It is the one place I have deliberately
made the gate non-uniform, and it is the place most likely to be argued with.

**4. Does the config summary belong on this surface at all, or in the About
modal?** I've placed it in Settings because that is where you asked for it and
because it sits beside the Client ID it explains. The About modal is the other
plausible home and already carries the version. I do not think it is the right
one — About is a credits screen, and burying diagnostics in it makes them harder to
talk someone through — but flagging it because it was never explicitly ruled out.

---
---

# ITEM B — multi-file audio upload

## B.0 This surface has no design handoff — flagging before proceeding

`docs/design-handoffs/` contains exactly one package, `configuration-surface/`.
**Step 1 (Add your audio) has no handoff.** Per my standing guard rail I should not
invent a visual language for an unspecced surface without telling you.

I have proceeded on the narrowest available basis: **Item B introduces no new
visual vocabulary at all.** Every state below is built from `.progress`,
`.msg-box err`, `.tracks`, `.tiny`, `.btn` and `.hidden` — all shipped, all already
used on this exact step. There are no new tokens, no new CSS rules, and no new
components. On that basis the drift risk is close to zero.

**Decision needed:** do you want a `docs/design-handoffs/audio-add-surface/`
package minted — before this ships, after it ships, or not at all? I lean *after*:
the surface is stable and this change is small, so a package written now would
mostly be a transcription of what already exists.

## B.1 The decided part, specified precisely

`multiple` is added to `#fileInput` (`index.html:67`). `#picUploadInput`
(`index.html:108`) is **explicitly untouched and stays single-select.**

### B.1.1 The natural-sort rule

Decided already and not relitigated: **upload order is natural sort by filename**,
so `track9` precedes `track10`. Safe because tracks can be reordered after upload.

**The rule, precisely:**

```
new Intl.Collator(undefined, { numeric: true, sensitivity: "base" })
  .compare(a.name, b.name)
```

applied to `[...fileInput.files]` **before any upload begins**.

Five properties this pins down, each of which a hand-rolled implementation
typically gets wrong:

1. **Compare `File.name` including extension** — never a path (the browser gives
   none) and never a stripped stem.
2. **`numeric: true` is the natural sort.** Digit runs compare as numbers, so
   `track9 < track10`, and `07` and `7` compare equal in value.
3. **`sensitivity: "base"` makes it case-insensitive**, so `Track2.mp3` and
   `track2.mp3` do not straddle a case boundary — the behavior a user expects from
   a file manager.
4. **Ties keep the browser's `FileList` order.** `Array.prototype.sort` has been
   stable by specification since ES2019, so equal keys (`07` vs `7`, `Track` vs
   `track`) are deterministic without a tiebreak rule.
5. **It handles non-ASCII digits and locale collation correctly**, which
   hand-rolled digit-run splitting does not.

**Use the platform. Do not hand-roll digit-run splitting** — it is the obvious
implementation, it is what gets written, and it gets `07` vs `7`, unicode digits,
and case wrong in ways that only show up on a user's machine.

### B.1.2 Uploads are sequential, and that is not a performance decision

One `POST /api/tracks/file` at a time, awaited.

**The reason is correctness, not throughput.** `_add_result_as_tracks`
(`app.py:295`) appends. Parallel uploads complete in nondeterministic order, so
they would land in the draft in nondeterministic order — **destroying the sort
order this feature just promised the user.** Sequential upload is what makes the
natural-sort rule true rather than approximately true.

Two supporting reasons: the server transcodes each file with ffmpeg, so
parallelism buys little and may thrash; and partial-failure reporting stays
comprehensible.

**During a batch, both `#filePick` and `#ytAdd` are disabled**, for the same
reason — a YouTube add or a second file batch landing mid-sequence would interleave
and break the order. Re-enable in `finally`.

*Pre-existing gap, worth fixing here:* today `#filePick` is **not** disabled during
a YouTube add, so the interleave is already possible. This is the same class of
thing `overview.md` §7.6 handled (a pre-existing bug that a new feature makes much
easier to hit), and the fix is symmetric and one line.

## B.2 What the user sees with 12 files in flight

> **Decision: the track list is the per-file progress display. `#addProgress`
> carries only the counter.**

`refreshDraft()` runs after each successful file, so rows appear one by one as she
watches. This is better than a purpose-built per-file UI for three reasons:

1. **It already exists.** No new component, no 12 nested bars to lay out or parse.
2. **It is the app's own model of truth** — the list is what she is building, and
   watching it grow is the most direct possible feedback.
3. **On a partial failure it does the hardest job for free:** the successes are
   already on screen and obviously safe, which is the single most important thing
   to communicate in that state.

Cost is 12 `/api/draft` round-trips over loopback. Acceptable.

**`#addBar` becomes real.** Today it is a fake 40%. For a batch it is
`(completed / total) × 100%` — completed **files**, not bytes. The honest unit here
is *how many of my files are in*, which is exactly what she is asking, and the
endpoint has no byte-progress events wired today.

**`n = 1` keeps today's behavior exactly** — bar at 40%, `Adding your file…`. It is
the overwhelmingly common case, it works, and changing it is a regression risk for
no gain. The rule is clean: **the batch treatment appears only when there is a
batch.**

## B.3 Partial failure — the state most likely to be built wrong

> **Decision: on a file failure, continue. Never stop the batch.**

File 3 of 12 fails. Files 4–12 upload normally.

**Why continue.** Stopping strands nine files she already chose, for a reason she
did not cause, and forces her to re-pick a subset she now has to compute by hand.
That is the worst available outcome. The failures here are properties of individual
files — unsupported type, corrupt, too long — and one bad file says nothing
whatsoever about the next one.

**What she has at the end:** eleven tracks in the list, in natural order, minus the
gap. One `.msg-box err` in `#addError` naming what failed and why.

### B.3.1 Can she retry just the failed one? — No, and this is deliberate

**Recommendation: no retry button.**

The browser still holds the `File` objects, so a retry is technically trivial. That
is exactly what makes this the wrong instinct to follow:

1. **A retry sends the same bytes through the same code path, so it produces the
   same failure.** The dominant failures here are properties of the file. A button
   that reliably fails is worse than no button — it teaches the user that this
   app's controls do not work, which is a far more expensive lesson than one
   re-pick.
2. **The failures that would benefit from a retry are transient** — a server
   hiccup, a full disk. Those are rare against a loopback server, and they would
   take the whole batch, not one file.
3. **It is a second batch flow.** Retry needs its own progress state, its own
   partial-failure state (retry 3, 2 fail again), and a decision about whether a
   retried file lands at its natural-sort position or at the end. That is real
   complexity bought to serve a case that mostly cannot succeed.

**What the design invests in instead: making the re-pick cheap.** Name the exact
filenames, one per line, so she can reopen the picker and select precisely those.

### B.3.2 Client-side pre-check — recommended, and cuttable

The likely real scenario is not one corrupt MP3. It is **she selected everything in
a folder**, which included `cover.jpg`, `AlbumArt.ini` and `notes.txt`. Each of
those costs a round-trip and returns a server error, turning one mistake into
several confusing lines.

**Recommendation: skip non-audio files before uploading**, and report them as a
distinct reason in the same summary.

The test mirrors the `accept` attribute's own semantics exactly:
`file.type.startsWith("audio/")` **or** the extension is in the explicit list.
**Read the list from `#fileInput`'s `accept` attribute rather than restating it in
JS** — then there is literally one list and it cannot drift.

This is the one part of Item B not strictly required by the brief. If the PR gets
large, **cut this first**; everything else stands without it.

### B.3.3 Copy — verbatim, and arity-dependent

The message shape changes with the number of files. This is a named rule, not an
implementation detail — `1 of your 1 files were added` is the failure mode to
avoid, and it is what a naive template produces.

| Case | String |
| --- | --- |
| `n = 1`, failed | *(the server's message, **unchanged** — e.g. `That file type isn't supported. Try an MP3, M4A or WAV file.`)* |
| `n ≥ 2`, `m = 1` failed | `{k} of your {n} files were added. This one didn't work:` |
| `n ≥ 2`, `m ≥ 2` failed | `{k} of your {n} files were added. These {m} didn't work:` |
| `n ≥ 2`, all failed | `None of your {n} files could be added:` |

Followed by **one line per failed file**, never a comma-run:

```
{filename} — {reason}
```

| Reason source | String |
| --- | --- |
| Server rejection | *(the server's sentence verbatim, e.g. `That file type isn't supported. Try an MP3, M4A or WAV file.`)* |
| Pre-check skip (§B.3.2) | `That isn't an audio file.` |

**Class is `.msg-box err` even for a mostly-successful batch.** Eleven of twelve is
mostly a success, but a silently missing track is a real problem she must notice,
and `tokens.md` §1 already made this argument: `.info` is *"too quiet to slow
anyone down"*. The copy carries the proportionality by **leading with what
worked** — the count comes first, the failures second.

*Planner constraint:* `#addError` must render the failed-file list as a list, one
file per line. `.msg-box` has no rule forbidding child elements.

### B.3.4 No success message

When all files succeed, **nothing appears**. The tracks in the list are the success
message. A "12 files added!" box would be a box that lingers or must be dismissed,
carrying information already on screen in a more useful form.

This is the current single-file behavior, preserved. Stating it so it reads as a
decision rather than an omission.

## B.4 Copy — the affordance

| Element | String |
| --- | --- |
| `#filePick` | `📁 Choose audio files` *(was `📁 Choose an audio file`)* |
| New `.tiny` line, below the file row | `You can pick more than one. They go in order by file name, and you can move them around afterwards.` |
| `#addMsg`, `n ≥ 2` | `Adding {i} of {n} — {filename}` |
| `#addMsg`, `n = 1` | `Adding your file…` *(unchanged)* |
| `#noTracks` | `No audio added yet.` *(unchanged)* |

**The plural in the button is what advertises the feature.** §12.2's lesson: a user
who wants to add twelve files needs a string on screen containing the words she is
holding. `Choose an audio file` states the opposite of the new capability.

**The `.tiny` line earns its 13px on the everyday path**, and the ledger is worth
being honest about since `overview.md` §2 makes weight a first-class constraint:

- It states the ordering rule in plain words, so the order is a **promise** rather
  than a surprise.
- It pre-answers the panic. Natural sort is only safe *because* tracks can be
  reordered afterwards — the brief says so explicitly — and that safety is only
  real if she knows it. This sentence is what converts the decision from safe-in-
  principle to safe-in-fact.
- The failure case is concrete, not hypothetical: an audiobook named
  `Chapter One.mp3` / `Chapter Three.mp3` / `Chapter Two.mp3` sorts wrong under any
  filename rule, and she needs to know both that it happened and that it is fixable.

**Rejected: putting it in a `title` attribute.** Invisible to scanning and to
touch — it would be a promise nobody reads.

**Rejected: showing it only after a multi-file batch completes.** Cheaper, but it
reveals the promise *after* she has been surprised by it. A promise has to precede
the action it governs.

## B.5 State table

| State | `#addProgress` | `#addBar` | `#addMsg` | `#addError` | Track list | `#filePick` / `#ytAdd` |
| --- | --- | --- | --- | --- | --- | --- |
| Idle, no tracks | hidden | — | — | hidden | `#noTracks` shown | enabled |
| Idle, has tracks | hidden | — | — | hidden | rows | enabled |
| Single file in flight | shown | 40% | `Adding your file…` | cleared | unchanged | **disabled** |
| Batch in flight | shown | `done/total` % | `Adding {i} of {n} — {name}` | cleared | **grows after each success** | **disabled** |
| Batch done, all ok | hidden | — | — | hidden | all rows | enabled |
| Batch done, partial | hidden | — | — | **shown, `err`** | successes present | enabled |
| Batch done, none ok | hidden | — | — | **shown, `err`** | unchanged | enabled |

## B.6 Accessibility

**`#addMsg` gets `role="status"`** (polite). During a batch it announces once per
file. That is twelve announcements, which is a lot — and it is correct: the
progress text is the **only** signal of liveness a non-sighted user has, and
hearing nothing for forty seconds is indistinguishable from a hung app. They are
polite, so they queue behind whatever she is doing.

**`#addError` gets `role="alert"` and `tabindex="-1"`.** It has neither today —
a pre-existing gap against the pattern every `.msg-box` in the settings view
follows.

**Focus does not move to `#addError`.** This is a deliberate divergence from
`interactions.md` §3.2 step 4, which *does* move focus to the message box after a
save. The difference: that is a synchronous response to a press the user just made.
This lands up to a minute after her click, by which time she may have moved on, and
yanking focus then is disorienting. `role="alert"` announces it without stealing
focus, which is exactly what the role is for. `tabindex="-1"` is added anyway so
the box is programmatically reachable.

**Announcement ordering is consistent with §4.3.** The final polite progress
message, then the assertive error. The assertive one jumps the queue, which is
correct — it is the outcome.

## B.7 Out of scope, explicitly

- **`#picUploadInput` stays single-select.** Named in the brief; restated here so
  nobody "finishes the job."
- Drag-and-drop of files onto the page.
- Per-byte upload progress.
- Any change to the reorder controls (`▲` / `▼`).
- A retry button (§B.3.1 — rejected with reasoning, not merely omitted).

## B.8 Decisions I need from Mark

**1. Cancel during a batch?** I have specified **none**. Twelve songs on a local
machine is well under a minute, each file is committed server-side as it lands so
nothing breaks if she closes the tab, and she can delete unwanted tracks with
controls that already exist. But `interactions.md` §2.4 set a precedent that long
waits should be escapable. **If UAT shows a 12-file batch running longer than ~30
seconds, add a Cancel** — it would sit beside the progress bar and stop after the
current file, never mid-file.

**2. The `.tiny` ordering line on the everyday path.** §B.4 argues it earns its
place. It is one 13px line added to step 1, which is the step every single user
sees on every single visit, and §2's weight constraint is the one you have called
overriding. Confirm you're happy, or I'll move the ordering rule into the multi-file
progress message instead and accept the later reveal.

**3. §B.0 — does the audio-add surface get a handoff package?**

---

## Success criteria

**Item A**

1. A user with a working sign-in cannot lose it by pasting a wrong value. The
   refusal runs before the write and before `logout()`.
2. A user already in the broken state sees, without instruction, what is wrong and
   what to press — and the value that is wrong is legible, not masked into
   plausibility.
3. No doomed authorize request is ever constructed on `saved` + `invalid`.
4. Every blocked state carries its recovery inline. Where the recovery cannot
   exist (`env`), the state is not blocked.
5. A parent on the phone can read out the version, the Client ID and its source,
   the sign-in address, and the folder — from one place, without pressing anything.
6. A legitimate Client ID in a shape Yoto has not used before is **never**
   hard-blocked. It may be warned about; it must always be usable.
7. No new CSS, no new tokens, no change to the `.setting` primitive.

**Item B**

8. Twelve files picked at once arrive in natural filename order, and the user was
   told that would happen before she picked them.
9. One bad file among twelve costs her that one file, and she is told which one and
   why — by name.
10. The single-file path is byte-for-byte what it is today.
