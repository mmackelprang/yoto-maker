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
| `env` | invalid | **red `is-err`** | `Set outside the app, and it isn't a Client ID` | `Yoto Maker can't sign in to Yoto until this is fixed. YOTO_CLIENT_ID on this computer holds something that isn't a Client ID, and only whoever set it can change it.` |
| `builtin` | invalid | **red `is-err`** | `Something's wrong with the built-in Client ID` | `Yoto Maker can't sign in to Yoto. This shouldn't be possible — the details at the bottom of this page are what someone will need to help you.` |

*(The `builtin` + `invalid` row is unreachable in a correct build and is guarded by
§A.0.3's required test. It exists so the table is total — every reachable
combination of source and verdict has a row, which is the completeness discipline
`tokens.md` §4 adopted after an unmeasured pair shipped a 2.56:1 label.)*

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
| 4 | `Redirect URL` | `http://127.0.0.1:8777/yoto/callback` | ✅ |
| 5 | `Where Yoto Maker keeps its files` | `C:\Users\…\AppData\Local\Yoto Maker` | ✅ |

**Row 4's label is `Redirect URL` — the guide's words, and the one label here that
is not plain English.** *(Decided 2026-07-21.)*

`Sign-in address` was drafted first and reads better for the primary user. It was
rejected. This row exists for **one moment**: she is on the phone, and the helper
is looking at `dashboard.yoto.dev` and at `SETUP-YOTO-CONNECTION.md`, which calls
it *"the redirect URL"* and warns *"This must match exactly"*. At that moment
§12.2's lesson governs — **a string is only findable if it contains the word the
person is holding** — and the person holding a word here is the helper.

The register rule bends because the section title already says who it is for.
*"If you need to ask for help"* is the frame that licenses one helper-addressed
label; a parent not in that occasion never needs to parse it. Same narrowly-scoped
exception `copy.md` §4's `env` sub-line takes, for the same reason: the sentence is
addressed to her about them.

Carrying both (`Sign-in address (redirect URL)`) was rejected as a hedge — two
names for one value is worse than either alone on a phone call.

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

### A.4.2 All tiers block uniformly — the recovery is what varies

> **Decided by Mark 2026-07-21: "block all tiers uniformly, keep it simple."**
> **This reverses an earlier recommendation in this spec to exempt `env`.**

**One gate. No tier condition in the blocking decision.** If the resolved verdict
is `invalid`, the sign-in is blocked, whichever tier supplied the value.

#### The deny-list decision is what makes "keep it simple" safe — and this is the second time it has paid out

Uniform blocking is only viable because §A.0.2 chose a deny-list over the strict
32-character rule. `tests/conftest.py` injects `YOTO_CLIENT_ID="test_client_id"` —
14 characters, with an underscore. It contains no `@`, no whitespace, no `/`, no
`:`, so it **passes the gate and the test suite is unaffected.**

Had the gate been the strict allow-list, this instruction would have blocked every
test run in the repo, and the failure would have arrived as a wall of unrelated
red rather than as a design objection anyone could argue with.

**Record this as load-bearing.** §A.0.2 justified the deny-list against a
hypothetical (Yoto changing its ID format someday). It has now twice protected
something concrete instead: a legitimate in-tree value, and the ability to take a
"keep it simple" instruction without a fight. A rule that keeps paying out in cases
it was not designed for is usually a rule that identified the right invariant.

#### The structural objection was real, and it is resolved in copy rather than in control flow

The earlier exemption argued: on `env` the reset control **cannot exist**, because
deleting the saved value falls through to the env var and the label would lie
(`overview.md` §7.4). That fact has not changed, and the guard rail it served —
**every blocked state must be honest about its own way out** — still holds.

What was wrong was the conclusion. The guard rail says a blocked state must carry
a *recovery*; it does not say the recovery must be a **button**. On `env` the
recovery is real, it is simply not something the app can perform:

> **Uniform gate, tier-specific recovery line.**
> The blocking decision has no tier condition. The recovery sentence does.

| `source` | Recovery |
| --- | --- |
| `saved` | The one-press `Put back the built-in Client ID` button, which opens the reset confirmation (§A.4.3). |
| `env` | **No button.** The fix named in words: `YOTO_CLIENT_ID` must be cleared or corrected in the shell, then Yoto Maker restarted. |
| `builtin` | No button — see below. |

This is strictly better than the exemption it replaces. Under the exemption, a
developer with a broken env var got a doomed authorize request and an Auth0 error
page; now they get a sentence naming the exact variable and the exact fix, which
is faster than debugging it.

**Copy — `env` + `invalid`, blocking, `.msg-box err`, no button:**

> Yoto Maker can't sign in to Yoto. The Client ID it's using comes from outside
> the app — the YOTO_CLIENT_ID environment variable on this computer — and what's
> in there isn't a Client ID.
>
> There's no button here that can fix it, because Yoto Maker didn't set it.
> Whoever did will need to clear or correct YOTO_CLIENT_ID and then start Yoto
> Maker again.

**The env var's real name appears verbatim, twice, deliberately.** `copy.md` §4
already licenses exactly this exception for exactly this tier — *"the only place
in the app where an environment variable name is spoken to the user… a deliberate,
narrow exception"* — and the reasoning applies with more force here than it did
there: the name **is** the recovery instruction. A user who cannot act on it will
read it out to someone who can, which is the same phone call setting 3 exists to
serve.

**The second paragraph exists to stop her hunting.** Every other blocked state in
this app has a button. Without a sentence saying *why there isn't one here*, she
will scroll looking for it and conclude the screen is broken.

**`builtin` + `invalid` — blocked, with no button, and deliberately not designed
for.** It is unreachable in a correct build and is prevented by §A.0.3's required
test. Note it would be **wrong** to show `Put back the built-in Client ID` here:
the built-in one is the broken one, so the button would promise to restore the
thing that is already failing. Its recovery line points at setting 3 instead:

> Yoto Maker can't sign in to Yoto, and the Client ID it came with is the problem —
> which shouldn't be possible. The details at the bottom of this page are what
> someone will need to help you.

*(Minor divergence from Mark's instruction, which grouped `builtin` with `saved`
for the button. Flagged rather than silently applied: the button is nonsensical in
this state, and the state is unreachable anyway, so the cheapest correct thing is a
sentence.)*

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

**The button is absent on `env` and `builtin`** (there is nothing for it to do —
§A.4.2), which is the same "omitted, not disabled" discipline `interactions.md`
§3.5.2 and `overview.md` §7.4 both already apply. Those tiers get a recovery
*sentence* in place of the button, never a disabled one.

### A.4.4 Server-side gate

`start_login()` (`auth.py:74`) must refuse whenever the resolved verdict is
`invalid`, raising an `AuthError` carrying the reason code — defense in depth
against a stale `app.js`, which this project has shipped before
(`overview.md` §12.1).

**No tier condition, matching §A.4.2.** This is one of the places uniform blocking
genuinely does buy simplicity: `start_login()` needs the verdict only, not the
source, so it can call the §A.0.3 function and branch once.

The frontend already has the pattern for consuming it:
`SIGNIN_ERRORS[e.data && e.data.reason]` at `app.js:1033`. Reuse it; do not invent
a second error-mapping mechanism.

**The server gate and the frontend gate must agree exactly.** They now do so
trivially, because both are "verdict is `invalid`". A server that refused what the
frontend permitted would produce a button that fails with no explanation — worse
than either behavior alone.

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
   │ Redirect URL                                                │  ← the guide's
   │ http://127.0.0.1:8777/yoto/callback                         │    words, not
   │                                                             │    ours: must
   │ Where Yoto Maker keeps its files                            │    match the
   │ C:\Users\mandy\AppData\Local\Yoto Maker                     │    dashboard
   └─────────────────────────────────────────────────────────────┘    exactly

   No Status slot. No Actions slot. No Confirmation slot.
   Slot 6 (.msg-box) present but hidden — the template is copy-paste.
```

---

## A.6 Decisions

**1. Three-paragraph refusal messages — resolved 2026-07-21: render as
paragraphs.** `clientIdMsg()` sets `textContent` today; it takes an array instead.
In-tree precedent is `CLIENT_ID_CONFIRM.body` in the same file, so this extends an
existing shape rather than inventing one. The three paragraphs stand as written —
the reassurance line keeps its own visual separation, which matters because it is
the sentence doing the most work (§A.1.1).

Item B needs the same capability for its grouped error box (§B.3.3). **One small
extension serves both items** — worth Planner knowing so it is not built twice.

**2. Config summary row 4's label — resolved 2026-07-21: `Redirect URL`,** the
setup guide's words, no hedge. Reasoning now inline at §A.3.3.

**3. `env` + `invalid` — resolved 2026-07-21: block, like every other tier.** Mark
overruled the warn-and-proceed recommendation: *"block all tiers uniformly, keep it
simple."* §A.4.2 is the re-spec. The structural objection behind the exemption was
real and is preserved — it is now resolved in **copy** (a tier-specific recovery
line) rather than in **control flow** (a tier-specific gate), which satisfies both
"uniform" and the guard rail that every blocked state names its own way out.

**4. Config summary placement — Settings, not the About modal.** Recorded because
it was never explicitly ruled out. About is a credits screen; burying diagnostics
there makes them harder to talk someone through, and the summary belongs beside the
Client ID it explains.

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

**Resolved 2026-07-21: do not mint a package.** This spec section carries the
surface, on the strength of the zero-new-vocabulary argument above.

**Logged as deliberate docs debt.** `design-handoffs/README.md` says every surface
gets a package, and step 1 still does not have one — that is a known gap, accepted
because the alternative is a package that would mostly transcribe what already
exists. **Revisit when the upload surface next grows**: drag-and-drop, per-byte
progress, or any change to the track list would each push it past the point where a
spec section is the right home. Whoever picks up that work should mint
`docs/design-handoffs/audio-add-surface/` first and fold this section into it.

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

### B.3.1 Retry — classify the failure, and let the classification decide

> **Decision: `Try again` appears for transient failures and does not appear for
> deterministic ones. Re-specced 2026-07-21, reversing an earlier blanket "no
> retry" call.**

**The earlier call was wrong, and the way it was wrong is worth recording.** It
argued: *a retry sends the same bytes through the same code path, so it produces
the same failure; a button that reliably fails teaches the user that this app's
controls do not work.* That reasoning is sound — **for deterministic failures.** It
was then applied to all failures, which silently assumed the deterministic case is
the only case. It is not, and it is probably not even the common one: dropped
connections, timeouts and 5xx dominate real upload flows. Under a blanket no-retry
rule, a network blip on file 3 of 12 forces her to re-pick that file by hand —
which is precisely the friction Item B exists to remove.

**The underlying principle is unchanged and is now the reason for the split:**

> **Never show a control that reliably fails.**
> A retry on a transient failure has a real chance of succeeding, which is what
> makes offering it honest. A retry on a deterministic failure has none, which is
> what makes offering it a lie.

### B.3.1.1 The classification rule

Everything needed is already observable. `api()` (`app.js:7-28`) throws a plain
`Error` with **no `.status`** when `fetch()` rejects, and otherwise attaches
`.status` and `.data`.

| Observation | Class |
| --- | --- |
| `err.data.reason` is present | **whatever the server says** — see below |
| `.status` is `undefined` (fetch rejected: connection refused, dropped, DNS) | **transient** |
| Request aborted by our own timeout | **transient** |
| `.status` is 5xx | **transient** |
| `.status` is 408 or 429 | **transient** |
| `.status` is any other 4xx | **deterministic** |
| Skipped by the pre-check (§B.3.2) — never uploaded | **deterministic** |
| **Anything else, unclassifiable** | **transient — see §B.3.1.2** |

**The server's own tag wins when present.** `app.js:1033` already consumes
`e.data.reason` for sign-in errors, so the pattern is in-tree. Nothing needs it on
day one — the status-code rule stands alone — but it is the hook that lets the
server later say *"this 500 was a full disk, do not offer a retry"* without any
frontend change. Planner should treat the status-code table as the **fallback**,
not the authority.

**Why the 400 case is reliably deterministic here.** `app.py:99-109` maps
`SourceError` / `AudioError` / `ImageError` and friends to **400 with a
plain-language `error` string**, and the module docstring (`app.py:5-6`) states
those messages are written to be shown verbatim. So a 400 from this endpoint means
*the server looked at this file and rejected it*, and it arrives with the sentence
explaining why already written. That is exactly the branch that must not offer a
retry — and exactly the branch that can explain itself instead.

### B.3.1.2 The unknown case defaults to transient — stated plainly

**An unclassifiable failure is treated as transient and gets the retry control.**

The principle says *never show a control that **reliably** fails.* An unknown
failure is by definition not reliably anything, so the principle does not forbid
offering a retry — it forbids offering one where we know it will fail. Beyond
that, the two wrong guesses cost wildly different amounts:

| Wrong guess | What it costs her |
| --- | --- |
| Unknown treated as **transient**, actually deterministic | One press and about two seconds. She is exactly where she was. |
| Unknown treated as **deterministic**, actually transient | **She is told to change the file.** She opens a file that is fine, finds nothing wrong, and concludes the app is broken — or re-encodes or deletes a perfectly good file on the app's bad advice. |

The second is not a slower path to the same place; it is **wrong advice**, and
wrong advice from a tool aimed at a non-technical user is the most expensive
failure in this whole spec. So the default goes to transient.

**The copy for this branch must not claim to know.** It says
`Something went wrong.` — it does not assert that the connection dropped and does
not assert the file is bad (§B.3.3).

**A retry is also a diagnostic, and this makes the default self-correcting.**
Pressing `Try again` is the cheapest way to resolve an unknown into a
classification:

- The retry succeeds → done, and the guess was right.
- The retry returns a 400 → **it is now classified deterministic.** The file moves
  into the "can't be added" group, the specific server sentence replaces
  `Something went wrong.`, and **the retry control disappears** for it. The app has
  corrected itself in front of her.
- The retry fails the same unknowable way → still unknown, control stays.

### B.3.1.3 Retry is the same flow, not a second one

The earlier rejection's third argument — *"it is a second batch flow"* — was the
one real cost, and it dissolves:

> **`Try again` re-enters the batch flow of §B.2 with the failed subset as its
> file list.** Same sequential loop, same progress bar, same `#addMsg` format,
> same disabling of `#filePick` and `#ytAdd`, same summary rendering at the end.

There is no second progress state and no second partial-failure state, because a
retry that half-fails simply produces the batch summary again over a smaller `n`.
Everything below follows from that one sentence.

The `File` objects are held from the original `FileList`, so nothing is re-read
from disk and she is never re-prompted.

### B.3.1.4 One button per group, not one per file

`Try again` retries **every file in the transient group**, and there is exactly one
of it.

- A network blip takes out a **contiguous run** of files, not one. Per-file buttons
  would mean three presses for one cause.
- Per-file buttons put a control on every row of a list that can hold twelve —
  twelve tab stops, and a visually heavy error box.
- The deterministic failures sit in their own group **with no control beside them**,
  which is the "explain, don't offer" branch made visible rather than merely
  described.

The two groups are what keep this legible: the button is inside the group it acts
on, so *"I pressed Try again, why is `cover.jpg` still failing?"* cannot arise.
**Render only the groups that have members** — the common cases (all transient, all
deterministic) show one group and read as simply as before.

### B.3.1.5 Where a retried file lands — the ordering promise survives

This was the third unanswered question in the earlier rejection, and it has a cheap
answer.

The server appends, so a file retried after files 4–12 would land **last** — she
picked twelve, one failed, and the fix drops it at position 12 instead of 3. She
would then press `▲` nine times, which is the friction this feature exists to
remove.

> **Rule: when a retry succeeds, issue exactly one `/api/tracks/reorder` at the end
> of the retry, placing this batch's tracks in natural-sort order and leaving every
> pre-existing track untouched and ahead of them.**

`/api/tracks/reorder` already exists and already takes a full order array
(`app.js:876`), so the call is `[…ids that existed before the batch, in their
current order, …this batch's ids in natural-sort order]`.

Three constraints, each load-bearing:

1. **Never re-sort the whole draft.** Tracks she added earlier — YouTube tracks,
   an earlier batch — may have been ordered by hand. Re-sorting them would destroy
   deliberate work to fix an incidental problem. Only indices belonging to this
   batch are permuted.
2. **Fire it only if a retry actually succeeded.** On the happy path and on a batch
   with no successful retry, the sequential upload already produced the right
   order, so the call is skipped entirely. The reorder is a **repair**, not a step.
3. **Once, at the end** — not after each retried file. One write, one re-render.
4. **Never after a cancelled batch** — §B.3.4.5.

**One file can produce several tracks, and the reorder must handle that.**
`_add_result_as_tracks` (`app.py:213-240`) splits anything over
`MAX_TRACK_SECONDS` (50 minutes, `normalize.py:191`) into `Title (part 1)`,
`(part 2)`… — each its own track. So the mapping is **one file → one *or more*
track ids**, and `POST /api/tracks/file` already returns `count` for exactly this
reason.

Two consequences Planner must not miss:

- The batch's id set is the **union** of every file's tracks, and within a file the
  parts must stay in their part order. Sorting the batch by filename therefore sorts
  *groups*, not individual tracks.
- **Counts in the copy are files, not tracks.** `11 of your 12 files were added` is
  correct even when the list gained seventeen rows. §B.3.3's strings say "files"
  throughout, deliberately — the user picked files, and the part-splitting is
  pre-existing behavior she has already met on the single-file path.

### B.3.1.6 Timeouts — recommendation REVERSED: do not add one

An earlier draft of this section recommended a per-file timeout, classified
transient, with the number left to Planner. **That recommendation is withdrawn.**

New information (Mark, 2026-07-21): **large split audio files already run for
multiple minutes today**, on the existing single-file path. The code confirms why —
`add_file` (`app.py:278-296`) is fully synchronous. It reads the whole upload,
transcodes via `adapter.fetch()`, then splits via `split_audio()` at
`MAX_TRACK_SECONDS = 50 minutes` (`normalize.py:191`), all inside one held-open
request. A three-hour audiobook is a legitimately multi-minute call.

So a timeout is not a safety net here; it is **a guess that would abort working
uploads.** Any threshold generous enough to survive a real audiobook is far too
long to rescue a hang, and any threshold short enough to rescue a hang would kill
audiobooks. There is no good number, which is the signal that the mechanism is
wrong.

**Cancel replaces it (§B.3.4), and is strictly better:** it is user-driven, so it
needs no threshold, and it cannot fire on a working upload because the user decides
what "too long" means for the file she chose.

The `timeout` row stays in §B.3.1.1's classification table for the case where a
future PR does add one — it costs nothing to leave the rule defined — but nothing
in this PR produces it.

**Cancellation is not a failure and is classified separately** — see §B.3.4.3.

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

**Pre-check skips are always deterministic and never enter the retry set.** They
never reached the network, so there is nothing about them a retry could change —
they land straight in the "can't be added" group with no control beside them.

This is the one part of Item B not strictly required by the brief. If the PR gets
large, **cut this first**; everything else stands without it. Cutting it does not
touch the classification rule — those files would then fail with a 400 and be
classified deterministic anyway, just more slowly and with a less specific
sentence.

### B.3.3 Copy — verbatim, arity-dependent, and grouped by class

`#addError` renders, in this order: **one summary line**, then **up to two
groups**, each with a heading and one line per file. Only groups with members are
rendered.

**Summary line.** Counts are always against the **original** batch size, so the
number is stable across retries — after a successful retry of one file, `10 of
your 12` simply becomes `11 of your 12`.

| Case | String |
| --- | --- |
| `n = 1`, failed | *(the server's message alone, **unchanged from today** — no summary, no groups, no heading)* |
| `n ≥ 2`, some failed | `{k} of your {n} files were added.` |
| `n ≥ 2`, all failed | `None of your {n} files could be added.` |

**The `n = 1` case is deliberately untouched.** `1 of your 1 files were added.` is
what a naive template produces and it is the failure mode this table exists to
prevent. A single file that fails shows exactly what it shows today. If it failed
transiently it still gets a `Try again` button — that is the one change to the
single-file path, and it is additive.

**Group headings.**

| Group | `m = 1` | `m ≥ 2` |
| --- | --- | --- |
| Transient | `This one didn't work, but trying again might fix it:` | `These {m} didn't work, but trying again might fix them:` |
| Deterministic | `This one can't be added:` | `These {m} can't be added:` |

*"trying again **might** fix it"* is deliberate. It sets the expectation honestly
— a retry is a real chance, not a promise — and it is the sentence that keeps the
control truthful even when the retry fails. `can't be added` is deliberately final:
it tells her not to wait, and not to press anything.

**Per-file lines**, one per line, never a comma-run:

```
{filename} — {reason}
```

| Class | Trigger | Reason string |
| --- | --- | --- |
| deterministic | 4xx from the server | *(the server's sentence verbatim — e.g. `That file type isn't supported. Try an MP3, M4A or WAV file.`)* |
| deterministic | pre-check skip (§B.3.2) | `That isn't an audio file.` |
| transient | `fetch()` rejected — no `.status` | `Yoto Maker stopped responding.` |
| transient | our timeout | `This one took too long.` |
| transient | 5xx / 408 / 429 | `Yoto Maker had a problem with this one.` |
| transient | **unclassifiable (the default)** | `Something went wrong.` |

**The server's 400 sentences are already user-ready.** `app.py:5-6` states the
plain-language errors are written to be shown verbatim, and `app.py:99-109` maps
every one of them to a 400. Do not rewrite them and do not wrap them.

**The unknown string claims nothing.** `Something went wrong.` deliberately does
not assert that the connection dropped and does not assert the file is bad —
§B.3.1.2 defaults this branch to transient precisely *because* we do not know, and
a reason string that guessed would undo that honesty.

**The button.**

| Element | String |
| --- | --- |
| `.btn` inside the transient group, below its list | `Try again` |
| `.btn` beside the progress bar, while a batch or retry runs | `Cancel` |

One `Try again` per group, never per file (§B.3.1.4). It is absent entirely when
the transient group is empty.

### The cancelled end state

A cancel adds a **third group** and changes the summary line. §B.3.4.

| Case | Summary line |
| --- | --- |
| `n = 1`, cancelled, nothing landed | `Stopped. Nothing was added.` |
| `n ≥ 2`, cancelled | `Stopped. {k} of your {n} files were added.` |

Followed by, when the in-flight file's outcome is unknown (§B.3.4.6):

> The one that was still going may still finish — it'll turn up in your list if it
> does.

Then the **not-started group**, which has **no button**:

| Group | `m = 1` | `m ≥ 2` |
| --- | --- | --- |
| Not started | `You stopped before this one:` | `You stopped before these {m}:` |

followed by the filenames alone — **no reason string**, because there is no reason
beyond her own decision, and inventing one would read as blame.

**`You stopped before…` rather than `These didn't work`.** These files did not
fail; she chose. The wording is factual and carries no fault, and it deliberately
does not offer to resume — she can re-pick if she changes her mind, and a control
that restarts what she just stopped is a confusing thing to put in front of
someone who has just pressed Cancel (§B.3.4.3).

Genuine failures from before the cancel still render their own groups, with
`Try again` intact where the transient group has members.

**Class is `.msg-box err` even for a mostly-successful batch.** Eleven of twelve is
mostly a success, but a silently missing track is a real problem she must notice,
and `tokens.md` §1 already made this argument: `.info` is *"too quiet to slow
anyone down"*. The copy carries the proportionality by **leading with what
worked** — the count comes first, the failures second.

*Planner constraint:* `#addError` must render this as structured children — a
summary paragraph, group headings, per-file lines, and a button — not one text
node. `.msg-box` has no rule forbidding child elements, and `.setting-confirm`
already sets the precedent for a box with a heading, body lines and actions.

**Worked example — the mixed case:**

```
   ┌─────────────────────────────────────────────────────────────┐
   │ 9 of your 12 files were added.              .msg-box err    │
   │                                                             │
   │ These 2 didn't work, but trying again might fix them:       │
   │   lullaby-03.mp3 — Yoto Maker stopped responding.           │
   │   lullaby-04.mp3 — Yoto Maker stopped responding.           │
   │                                                             │
   │   ┌────────────┐                                            │
   │   │ Try again  │  ← acts on THIS group only, which is why   │
   │   └────────────┘    the groups exist                        │
   │                                                             │
   │ This one can't be added:                                    │
   │   cover.jpg — That isn't an audio file.                     │
   │              ▲ no control beside it: "explain, don't offer" │
   └─────────────────────────────────────────────────────────────┘
```

### B.3.4 No success message

When all files succeed, **nothing appears**. The tracks in the list are the success
message. A "12 files added!" box would be a box that lingers or must be dismissed,
carrying information already on screen in a more useful form.

This is the current single-file behavior, preserved. Stating it so it reads as a
decision rather than an omission.

## B.3.4 Cancel — required, and it must abort the in-flight request

> **Decided by Mark 2026-07-21: cancel is required, not deferred to UAT.**

### B.3.4.1 Why the earlier sketch was wrong

An earlier draft deferred cancel to UAT behind a "~30 second batch" threshold, and
sketched it as *"stop after the current file, never mid-file."* **Both halves were
wrong, and for the same reason:** large split audio files already run for multiple
minutes today on the single-file path (§B.3.1.6). The long wait is not a risk
multi-select might introduce — it is the current everyday reality, and batching and
retry stack on top of it.

So stop-after-current is barely distinguishable from no cancel at all. She presses
it, and still waits minutes. **That is worse than having no button**, because a
control that appears to do nothing reads as broken, and the button would be
lying about what it just did.

> **Cancel aborts the request that is in flight.** It does not merely decline to
> start the next file.

### B.3.4.2 `api()` can carry an `AbortController` — with one required change

`api(path, opts)` passes `opts` straight to `fetch(path, opts)` (`app.js:7-10`), so
**`opts.signal` already works today.** No signature change.

**But `api()`'s catch block must learn about aborts, and this is not optional:**

```js
} catch (e) {
  // turns EVERY fetch rejection into "Couldn't reach the Yoto Maker app…"
```

An `AbortError` is a fetch rejection, so today a deliberate cancel would be
reported to the user as *"Couldn't reach the Yoto Maker app. Make sure it's still
running"* — alarming and false. Worse, §B.3.1.1 classifies a rejection with no
`.status` as **transient**, so the cancelled file would be offered a `Try again`
button. **The user's own cancel would be presented to her as a network failure she
should retry.**

**Required:** `api()` re-throws `AbortError` distinctly — check `e.name ===
"AbortError"` before the existing branch — so callers can tell *"I stopped this"*
from *"the app is gone."* This is a small change to a shared helper, so Planner
should confirm no other caller regresses; today no caller passes a signal, so
nothing can hit the new branch except this one.

### B.3.4.3 Cancellation is not a failure

A cancelled file goes in **neither** the transient nor the deterministic group. She
stopped on purpose; classifying her decision as a failure and offering to retry it
would be presumptuous, and it would blur `Try again` into meaning two different
things.

**Genuine failures that happened before the cancel are unaffected.** If file 3
failed transiently and she cancelled at file 7, the transient group still lists
file 3 and still offers `Try again` for it. That failure is real and unrelated to
her decision.

### B.3.4.4 What happens to already-uploaded tracks — they stay

**Completed tracks are kept.** She waited for them, they are valid, and silently
discarding finished work to honor a cancel is the worst available reading of the
button — it would turn "stop" into "undo", which is not what she pressed.

This also matches how the batch already behaves: each file is committed server-side
as it lands (§B.2), so there is no transaction to roll back and nothing to invent.

**The summary must then state the draft's exact state**, because a cancelled batch
is the one end state where she cannot infer it — she stopped partway and does not
know where. §B.3.4.6 names what landed and what did not, by name.

### B.3.4.5 Cancel must not fire the reorder

§B.3.1.5's `/api/tracks/reorder` sends a **full order array** built from the
batch's expected ids. After a cancel, files that never arrived have no ids, so the
array would be built against an incomplete set — permuting real tracks against
positions that do not exist.

> **Rule: a cancelled batch never issues the reorder call.** Set a flag on cancel
> and skip it unconditionally.

Nothing is lost. The files that *did* land arrived sequentially in sorted order, so
they are already correct — the reorder exists only to repair a retry (§B.3.1.5),
and a cancelled batch has no repair to make.

### B.3.4.6 The in-flight file may still land — and the copy must say so

**This is the one place the design cannot be exact, and the honest move is to say
so rather than guess.**

Reading `add_file` (`app.py:278-296`): after `await file.read()` there are **no
further `await` points** before `return`. `adapter.fetch()` and
`_add_result_as_tracks()` are synchronous calls inside an `async def`. Since
asyncio cancellation can only take effect at an `await`, a client disconnect
**cannot interrupt the transcode or the split**, so the handler runs to completion
and `draft.add_track()` executes.

**Consequences, in order of importance:**

1. **Aborting during the transcode does not prevent that file from landing.** The
   track appears in the draft seconds or minutes after she pressed Cancel.
2. **Aborting during `await file.read()` does prevent it.** `write_bytes` never
   runs, so there is no file on disk and no track.
3. **Either way, no broken or partial track is created.** The file either never
   started or completed fully. `add_track` is the last statement, so there is no
   window in which a half-made track is registered. **No cleanup path is needed.**

Point 3 is the reassuring one and it is the direct answer to the question asked.
Points 1 and 2 mean the outcome is genuinely uncertain from the client's side, so
the copy tells the truth:

> The one that was still going may still finish — it'll turn up in your list if it
> does.

Without that sentence, a track appearing thirty seconds after she pressed Cancel
looks like the button failed.

> **⚠️ Planner / Architect — verify, and consider the real fix.**
>
> The analysis above is read from the code, not observed. **Planner should confirm
> it** by cancelling mid-transcode and checking whether the track appears.
>
> **The proper fix is to move `/api/tracks/file` onto the existing job system.**
> `POST /api/tracks/youtube` (`app.py:246-273`) already does this — it returns a
> `job_id` immediately and reports progress through `update()`, and `app.js`
> already has `pollJob()` to consume it. Moving file uploads to the same shape
> would:
> - free the request instantly, so there is no multi-minute held connection at all;
> - give **real** per-file progress, retiring the fake 40% bar (§B.2);
> - make cancel **exact**, deleting the "may still finish" sentence above.
>
> **This is an architecture decision, not mine to make** — it changes an endpoint's
> contract and touches the job system. Escalating to Architect/Planner rather than
> specifying it. The design above ships correctly without it; the awkward sentence
> is the visible cost of not doing it, which makes it a decent forcing function.

### B.3.4.7 Cancel is available during a retry round too

Same button, same behavior, same reasoning: a retry round is the batch flow
re-entered (§B.3.1.3), and a retried large file takes exactly as long as it did the
first time. Withholding cancel from the retry would strand her in precisely the
wait she just escaped.

### B.3.4.8 Placement and label

**`Cancel`**, a plain `.btn`, beside the progress bar — the exact string and shape
`copy.md` §3 already uses for the `signing_in` state, where `interactions.md` §2.4
puts `Cancel` next to a disabled primary during a long wait. Same problem, same
answer, no new vocabulary.

It appears whenever `#addProgress` is visible, **including for a single file** —
that is where the multi-minute waits actually live today, so excluding `n = 1`
would withhold the button from the case that motivated it.

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
| Single file in flight | shown **+ `Cancel`** | 40% | `Adding your file…` | cleared | unchanged | **disabled** |
| Batch in flight | shown **+ `Cancel`** | `done/total` % | `Adding {i} of {n} — {name}` | cleared | **grows after each success** | **disabled** |
| **Cancel pressed, abort in flight** | shown, `Cancel` **disabled** | frozen | `Stopping…` | cleared | unchanged | disabled |
| **Cancelled** | hidden | — | — | **shown, `err`** | successes kept | enabled |
| Batch done, all ok | hidden | — | — | hidden | all rows | enabled |
| Batch done, partial | hidden | — | — | **shown, `err`** | successes present | enabled |
| Batch done, none ok | hidden | — | — | **shown, `err`** | unchanged | enabled |
| **Retry in flight** | shown **+ `Cancel`** | `done/retried` % | `Adding {i} of {n} — {name}` | **stays visible**, `Try again` **disabled** | grows | **disabled** |
| **Retry done, all recovered** | hidden | — | — | hidden | reordered (§B.3.1.5) | enabled |
| **Retry done, some still failing** | hidden | — | — | shown, `err`, recomputed | successes present | enabled |

Three notes on the retry rows, each a place this is easy to build wrong:

- **`#addError` stays visible during a retry**, with `Try again` **disabled rather
  than removed**. Removing it would collapse the box under the user's cursor and
  drop focus (§B.6). Disabling it keeps the layout still and the focus target
  alive.
- **`n` in the retry's progress message is the retry count, not the original batch
  size.** She is watching two files go by, and `Adding 1 of 12` would be a lie.
  The *summary* count stays against the original batch (§B.3.3) — different
  numbers, different questions.
- **`Batch done, all ok` covers a retry that recovered everything**: the box is
  hidden entirely, because the end state is indistinguishable from a batch that
  never failed. Nothing lingers to explain a problem that no longer exists.

And two on cancel:

- **`Stopping…` is a real state, not a flourish.** The abort is not instantaneous —
  the request has to unwind — and the multi-minute file that provoked the cancel is
  exactly the case where a frozen bar with no acknowledgement reads as a second
  failure. `Cancel` is **disabled rather than removed** while it resolves, for the
  same focus reason as `Try again` (§B.6).
- **`Cancelled` uses `.msg-box err`** despite nothing having failed. This is
  consistent with the partial-batch row above and rests on `tokens.md` §1's
  argument that `.info` is *"too quiet to slow anyone down"* — and here the box is
  carrying the only statement of what the draft now contains, which she must read.

## B.6 Accessibility

**`#addMsg` gets `role="status"`** (polite). During a batch it announces once per
file. That is twelve announcements, which is a lot — and it is correct: the
progress text is the **only** signal of liveness a non-sighted user has, and
hearing nothing for forty seconds is indistinguishable from a hung app. They are
polite, so they queue behind whatever she is doing.

**`#addError` gets `role="alert"` and `tabindex="-1"`.** It has neither today —
a pre-existing gap against the pattern every `.msg-box` in the settings view
follows.

**After the initial batch, focus does not move to `#addError`.** This is a
deliberate divergence from `interactions.md` §3.2 step 4, which *does* move focus
to the message box after a save. The difference: that is a synchronous response to
a press the user just made. This lands up to a minute after her click, by which
time she may have moved on, and yanking focus then is disorienting. `role="alert"`
announces it without stealing focus, which is exactly what the role is for.
`tabindex="-1"` is added anyway so the box is programmatically reachable.

**After a retry, focus IS managed** — and the distinction is principled, not
inconsistent. A retry result *is* a synchronous response to a press she just made,
which is exactly the condition under which §3.2 step 4 moves focus. So:

1. On pressing `Try again`, **disable the button rather than removing it**, so
   focus stays on it for the duration of the retry.
2. When the retry finishes and `#addError` re-renders:
   - a `Try again` button still exists → **focus it** (she may want to press again);
   - it does not (everything recovered, or everything reclassified deterministic)
     → **focus `#addError`** via its `tabindex="-1"`, so the outcome is announced
     and she is not dropped at the top of the document.

Without rule 1 the button is destroyed while focused and focus falls to `<body>`,
which is the single most common way a keyboard user gets lost in a flow like this.

**Cancel follows the same two rules.** It is disabled rather than removed while the
abort resolves (§B.5), and when `#addProgress` hides and `#addError` renders the
cancelled summary, **focus moves to `#addError`** — a cancel is a synchronous
response to a press she just made, so §3.2 step 4's condition is met exactly as it
is for retry. Announcing the cancelled state matters more than most: it is the one
end state where she cannot infer what the draft now contains (§B.3.4.4).

**Announcement ordering is consistent with §4.3.** The final polite progress
message, then the assertive error. The assertive one jumps the queue, which is
correct — it is the outcome.

## B.7 Out of scope, explicitly

- **`#picUploadInput` stays single-select.** Named in the brief; restated here so
  nobody "finishes the job."
- Drag-and-drop of files onto the page.
- Per-byte upload progress.
- Any change to the reorder controls (`▲` / `▼`).
- **Per-file retry buttons** — §B.3.1.4. One button per group is in scope; twelve
  buttons on twelve rows is not.
- **Retrying a deterministic failure** — §B.3.1. Not an omission; the control is
  absent by design, and adding it later would need this section's reasoning
  overturned first.

## B.8 Decisions

**1. Retry — resolved 2026-07-21, reversing my earlier call.** Classification
decides: transient gets `Try again`, deterministic gets an explanation instead,
unknown defaults to transient. §B.3.1 is the re-spec, not a patch. The principle I
originally argued from — *never show a control that reliably fails* — is preserved
and is now the reason for the split rather than the reason for a blanket ban.

**2. `.msg-box` renders paragraphs — resolved 2026-07-21: yes.** In-tree precedent
is `CLIENT_ID_CONFIRM.body`. Item B needs the same capability for the grouped error
box (§B.3.3), so the two items share one small extension rather than each getting
their own.

**3. The `.tiny` ordering line — resolved 2026-07-21: include it.** One 13px line
on the everyday path, accepted because natural sort is only *safe* on the strength
of reordering existing, and that is only true for her if she knows it. Without the
line a wrong-looking order reads as a bug rather than as something she can fix.

**4. Handoff package for this surface — resolved 2026-07-21: do not mint one.**
§B.0 carries it. Logged as deliberate docs debt.

**5. Cancel — resolved 2026-07-21: required, and it aborts the in-flight
request.** §B.3.4 is the spec. My earlier deferral was wrong on both counts: the
~30-second threshold was the wrong test (multi-minute waits are today's reality,
not a risk multi-select introduces), and *"stop after the current file"* was the
wrong mechanism (indistinguishable from no cancel when one file takes minutes).

**6. Per-file timeout — withdrawn** (§B.3.1.6). It was recommended in an earlier
draft and is now actively wrong: any threshold that survives a real audiobook is
too long to rescue a hang. Cancel replaces it and needs no number.

**Still open — escalated to Architect, not blocking this PR.** `POST
/api/tracks/file` is synchronous and holds the request for the whole
transcode-and-split, which is why cancel cannot be exact (§B.3.4.6). The proper fix
is to move it onto the job system `POST /api/tracks/youtube` already uses. That is
an endpoint-contract change and an architecture call. **This spec ships correctly
without it** — the cost is one hedging sentence in the cancelled summary.

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
10. The single-file path is byte-for-byte what it is today, except that a
    transient single-file failure now offers `Try again`.
11. **A network blip on file 3 of 12 costs one button press, not a re-pick.**
    Verified by killing the server mid-batch, restarting it, and pressing
    `Try again`.
12. **No control is ever offered that cannot succeed.** A file rejected by format
    or size shows an explanation and **no** `Try again`; a file that failed
    transiently shows one. Verified by mixing an unsupported file into a batch
    interrupted by a network failure and confirming the two land in different
    groups with only one button between them.
13. **A retried file lands in its natural-sort position, not at the end** — and no
    track that existed before the batch is moved.
14. **`Cancel` stops a multi-minute file in seconds, not minutes.** Verified by
    cancelling during a long transcode and confirming the UI returns promptly. A
    cancel that leaves her waiting has failed even if it eventually works.
15. **A cancelled batch keeps everything that landed, and says exactly what
    landed and what didn't — by name.** She never has to diff her file picker
    against the track list to find out where it stopped.
16. **Her own cancel is never presented to her as a network error**, and never
    offers `Try again` (§B.3.4.2 — the `AbortError` branch in `api()` is what
    prevents this, and it is the one change without which cancel actively
    misinforms).
