# Copy — Configuration surface

**Every user-visible string, verbatim.** Nothing here is a placeholder. Builder
should copy these exactly; deviations are a Polisher finding.

Register: `docs/INSTALL-FOR-MOM.md`. Second person, present tense, short
sentences. No banned vocabulary (see `../README.md`). "Client ID" is the one
permitted technical term and is always explained where it appears.

Typographic apostrophes (`'`) throughout, matching existing markup
(`app.js:408`, `index.html:51`).

---

## 1. Entry points

| Location | String |
| --- | --- |
| Header pill, connected | `Yoto connected` *(unchanged)* |
| Header pill, not connected | `Yoto not connected` *(unchanged)* |
| Header pill, checking | `Checking…` *(unchanged)* |
| Header pill `aria-label` | ~~`Yoto connection settings`~~ — **removed 2026-07-20, see §1a** |
| Header pill `title` | `Yoto connection settings` |
| Footer link | `Settings` |
| Step 3 link (`#advToggle`) | **state-dependent as of 2026-07-20 — see §1a** |

## 1a. Entry points — amendment (2026-07-20)

`overview.md` §12. Ships in v0.1.10.

### The step 3 link (`#advToggle`) — now state-dependent, and always rendered

`#advRow` moves out of `#connectRow` and becomes the last child of step 3, so
the link exists in **both** connection states. Its text is set by
`renderStatus()` from `STATUS.yoto.connected`:

| State | String, verbatim |
| --- | --- |
| connected | `⚙️ Connect a different Yoto account` |
| not connected | `⚙️ Yoto connection settings` |

**Why the connected variant names the account, not the destination.** The user
who reported this was searching, in his own words, for *"the option to connect to
a different account."* No string on the connected screen contained *account*,
*different* or *change* — the pill names a **state**, the footer names a
**category**, and this link named a **destination**. A link is only findable by
scanning if it contains a word the scanner is holding, and none of the three did.
Full argument in `overview.md` §12.2–12.3.

**Why not one string for both states.** `a different` is **false** before there
is a current one — she hasn't connected any account yet — and in that state the
big `🔗 Connect my Yoto account` button directly above already owns that intent.
This is the same rule already applied in §4 to the Client ID label
(`Paste a Client ID` / `Paste a different Client ID`), for the same reason, in the
`884fa6a` amendment. It is not a new pattern.

**Why `Connect` rather than v0.1.8's `Use`.** Closer to the words the user
actually used, and it is the app's established verb — `#connectBtn`, the settings
view's `🔗 Connect my Yoto account` (§3). "Use" was never wrong; "Connect" simply
matches better.

**The `⚙️` stays on both variants.** The glyph is the constant and the words are
the variable, so a user who found the control in one state can recognise it in the
other. If the icon tracked the copy there would be nothing stable to recognise.

**`(advanced)` is not restored.** PR #10 dropped it correctly: it labelled a link
that revealed a Client ID input inline, which this link no longer does, and it is
a discouragement marker pointed at exactly the user we now need to click. The
Client ID section carries its own `(advanced)` in §4 where it is still true.

### Strings retired by this amendment

| Location | Old string | Fate |
| --- | --- | --- |
| `index.html:129` | `⚙️ Yoto connection settings` *(as the only variant)* | Kept, but now the **not-connected** variant only |
| `index.html:16` | `aria-label="Yoto connection settings"` | **Deleted.** It overrode the visible text as the accessible name, so the name did not contain the label — WCAG 2.1 AA **2.5.3 Label in Name**. With the attribute gone, the pill's text content becomes the name and `title` becomes the description: *"Yoto connected, button, Yoto connection settings."* `overview.md` §12.6. |

### The pill's chevron carries no string

The trailing `›` (`tokens.md` §2b) is `aria-hidden="true"` and has no accessible
text. It is an affordance mark, not a label — the pill's own text names the state
and `title` names the destination, so there is nothing left for it to say. Do not
give it an `aria-label`; anything it said would duplicate one of those two.

**Explicitly not a gear.** An icon is a string (§4a makes the same argument about
👁). `⚙️` on the pill would say *settings* — the category vocabulary that already
failed to match above — and to a reader who has not learned the convention it says
*machinery, technical, don't touch*, which repels the `INSTALL-FOR-MOM.md` user.
`›` claims only that there is somewhere to go, which is true and is the one thing
that was missing. Full reasoning in `overview.md` §12.6.

### Strings explicitly unchanged by this amendment

The pill's own text (`Yoto connected` / `Yoto not connected` / `Checking…`), its
`title`, and the footer `Settings` link. The pill reports state and must keep
doing so; the footer's weakness is vocabulary, not visibility, and adding weight
to it would be permanent chrome for a twice-ever surface (`overview.md` §12.7).

## 2. View chrome

| Element | String |
| --- | --- |
| Back button | `← Back to my card` |
| Page title (`h2#settingsTitle`) | `Settings` |
| Browser tab title while in settings | `Settings · Yoto Maker` |
| Browser tab title otherwise | `Yoto Maker` *(unchanged)* |

---

## 3. Setting 1 — Your Yoto account

### Fixed copy

**Title**

> Your Yoto account

**Description**

> Yoto Maker sends the cards you make to your Yoto account. You sign in once,
> on Yoto's own website, and it remembers you on this computer.
>
> Use the button below if Yoto Maker has stopped being able to send cards, or if
> you want to use a different Yoto account.

*(Two paragraphs. The second is the one doing the work — it is the single
action's disambiguation, and it must not be shortened.)*

### Status line, by state

| State | Dot | Headline | Sub-line |
| --- | --- | --- | --- |
| `checking` | grey | `Checking your Yoto connection…` | — |
| `connected` | green | `Connected and working` | `We just checked with Yoto and everything's fine.` |
| `not_connected` | grey | `Not connected yet` | `Connect your Yoto account to send cards to it.` |
| `broken` | red | `There's a problem with this connection` | `Yoto Maker can't send cards right now. Signing in again usually fixes it.` |
| `unknown` | grey | `We couldn't check right now` | `This computer doesn't seem to be online. Check your internet, then come back.` |
| `signing_in` | amber | `Waiting for you to sign in…` | `We opened Yoto's website in another tab. Sign in there, then come back here.` |

**Why "Connected and working" rather than "Connected":** the extra word is the
whole point of the live check (`overview.md` §7.5). "Connected" is what the app
says today, and today it says it while broken.

### Button label, by state

| State | Label |
| --- | --- |
| `connected` / `broken` / `unknown` | `🔗 Sign in to Yoto again` |
| `not_connected` | `🔗 Connect my Yoto account` |
| `signing_in` | `Waiting for Yoto…` *(disabled)* |

The `not_connected` label is word-for-word identical to step 3's existing
`#connectBtn`, deliberately.

### Secondary action, `signing_in` state only

> `Cancel`

### Confirmation — shown only when state is `connected`, `broken` or `unknown`

**Question and consequences**

> Sign in to Yoto again?
>
> This forgets the Yoto account on this computer, then opens Yoto's website so
> you can sign in — with the same account, or a different one.
>
> Nothing in your Yoto account changes. The cards you've already made are safe.

**Buttons**

| Role | Label |
| --- | --- |
| Cancel (`.btn ghost`) | `Never mind` |
| Confirm (`.btn primary`) | `Yes, sign in again` |

**Why the third paragraph exists:** the fear this user brings to a button that
says "forget" is *"will I lose the cards I made?"*. Answering that unprompted,
in the confirmation itself, is the difference between a user who proceeds and a
user who closes the app and calls someone. It is the most load-bearing sentence
on the surface.

No confirmation is shown when the state is `not_connected` — there is nothing to
forget, so the button goes straight to Yoto.

### Feedback messages

| Trigger | Class | String |
| --- | --- | --- |
| Sign-in finished successfully | `.msg-box ok` | `🎉 You're signed in. Yoto Maker can send cards again.` |
| Yoto rejected the sign-in | `.msg-box err` | `Yoto couldn't complete the sign-in. Please try again.` |
| Couldn't reach Yoto | `.msg-box err` | `We couldn't reach Yoto. Check your internet connection, then try again.` |
| Waiting timed out (3 min) | `.msg-box info` | `We stopped waiting for the sign-in. If you finished signing in on Yoto's website, press "Sign in to Yoto again" — otherwise you can try again now.` |
| User pressed Cancel while waiting | `.msg-box info` | `Stopped waiting. You can close the Yoto tab if it's still open.` |

**Deliberately no "user cancelled on Yoto's site" message** *(removed 2026-07-20)*.
An earlier draft of this table specified
`Sign-in was cancelled. You can try again whenever you're ready.` for that
trigger. It has no reachable path and never did: cancellation is rendered on the
**callback page in the other browser tab** (`app.py:533-535`), which already
says `Sign-in was cancelled. You can close this tab and try again.` — the same
message, in the tab the user is actually looking at, with better advice about
the stray tab. The settings view in the original tab has no
way to learn about it and stays pending until the 3-minute `timed_out` message
above takes over.

Making it reachable would require new server-side callback state that this
handoff never specified. That was raised with the user, who did not ask for it
to be wired. The row is removed rather than left in place so that this file
describes the surface as shipped — a specced string with no renderer reads to a
future maintainer as an unimplemented requirement and invites someone to "fix"
a gap that was a decision.

If a future PR does add cross-tab callback state, this is the string to use and
`.msg-box info` is the right class; treat it as new scope, not as a bug being
paid down.

---

## 4. Setting 2 — Yoto Client ID

### Fixed copy

**Title**

> Yoto Client ID (advanced)

*(The "(advanced)" is a load-bearing signal: it tells the primary user this
section is not for her without hiding it from the person helping her.)*

**Description**

> Most people never need to change this. Yoto Maker comes with everything it
> needs already built in.
>
> A Client ID is a code from Yoto's developer website that tells Yoto which app
> is asking to sign in. You'd only paste your own here if someone has asked you
> to. [How to get one ↗](https://github.com/mmackelprang/yoto-maker/blob/main/docs/SETUP-YOTO-CONNECTION.md)

*(The link keeps the existing target and `↗` convention from `index.html:180`.)*

### Status line, by state

| `client_id_source` | Dot | Headline | Sub-line |
| --- | --- | --- | --- |
| `builtin` | green | `Using the built-in Client ID` | `This is what most people use. Nothing to do here.` |
| `saved` | green | `Using your own Client ID` | `Saved on this computer only.` |
| `env` | amber | `Set outside the app` | `Someone set this up on this computer using YOTO_CLIENT_ID, and that takes priority. To change it, they'll need to change it there.` |

**The `saved` sub-line changed 2026-07-20** (`overview.md` §11.6). It was
`Ends in {last3}. Saved on this computer only.` The value fragment moves to the
body (§4a), where the whole mask is shown instead of three characters — so the
sentence is not losing information, it is losing a worse copy of it. This also
retires a mild breach of the primitive's rule §4.3.2 (*never surface a raw
stored value* in the status slot) and the `last3` slicing at `app.js:499-508`,
including its empty-string fallback, which no longer has anything to fall back
from.

**The `env` sub-line is the only place in the app where an environment variable
name is spoken to the user.** That is a deliberate, narrow exception: the state
is otherwise inexplicable (a saved value would appear to be silently ignored),
and the person who can act on it is by definition technical enough to recognize
the name. The sentence is addressed to *her* about *them* — "they'll need to
change it" — so she knows the fix isn't hers to make.

### 4a. Body — the value in effect *(amendment, 2026-07-20)*

Shown only when `client_id_source` is `saved` or `env`; absent for `builtin`
(`overview.md` §11.4). Behavior in [`interactions.md` §3.5](interactions.md).

| Element | String |
| --- | --- |
| Label (`.tiny`, above the value) | `The one you're using now` |
| Value, collapsed | *(the masked value, e.g.* `a8OG…oU1` *— rendered, not written)* |
| Value, revealed | *(the full Client ID)* |
| Toggle, collapsed | `Show the whole thing` |
| Toggle, revealed | `Show the short version` |

**One label for both sources.** `The one you're using now` is true whether she
saved it or someone set it in an env var, and the status line directly above has
already said which. A second variant would add a conditional to buy nothing.

**Why not an eye icon, and why these two strings.** Full argument in
`overview.md` §11.2; the copy consequence is the part that belongs here. This
value is **not a secret** — it is a public client ID, sent in plaintext in every
sign-in URL and displayed openly on the Yoto dashboard the user is comparing it
against. So no string in this section may imply otherwise, and **an icon is a
string**: 👁 is the password-field convention and states "this is secret" more
forcefully, and to more people, than any sentence here could walk back.

The pair above is chosen to say **shortened, not hidden** — the difference
between an abbreviation and a redaction. Both name a length, neither names
visibility. Specifically rejected:

| Rejected | Why |
| --- | --- |
| 👁 icon, no text | States "secret". Also unlabelled for screen readers without inventing an `aria-label` that would have to say something. |
| `Reveal` | The verb of exposing something concealed. |
| `Hide it again` | Pairs "show" with "hide", which frames the default state as concealment. |
| `Show more` / `Show less` | Neutral and safe, but generic — reads as a paragraph expander, not as *this string is abbreviated*. |
| `Show the full Client ID` | Accurate, but "Client ID" already appears three times in this section; a fourth is noise. |

**Register note.** `Show the whole thing` is deliberately colloquial. This
section is `(advanced)` and its readers are the helper and the user relaying to
the helper — but the register still has to hold for the primary user who wanders
in, and "the whole thing" is what a person says out loud.

### Body — the input

| Element | String |
| --- | --- |
| Label (`.tiny`, above input) — `builtin`, `env` | `Paste a Client ID` |
| Label (`.tiny`, above input) — `saved` | `Paste a different Client ID` |
| Input placeholder | `Paste your Yoto Client ID here` |
| Save button | `Save` |

**The label became state-dependent 2026-07-20.** With the current value now
displayed directly above it, the `saved` state stacks two Client-ID-shaped
things, and `Paste a Client ID` no longer distinguishes the one you have from
the one you would replace it with. `a different` is three words and removes the
ambiguity the amendment introduced. `builtin` and `env` are unchanged — in
neither case is there a saved value of hers to differ from.

When `client_id_source` is `env`: the input and Save button are **disabled**,
and this line appears below them in `.tiny`:

> You can still type one here, but it won't be used while the one above is set.

*(Disabled + explained, not hidden. Hiding it would make the section look broken
to the person who came here specifically to change this.)*

### Actions

Shown **only** when `client_id_source == "saved"`:

| Role | Label |
| --- | --- |
| `.btn` | `Go back to the built-in one` |

Hidden when `builtin` (nothing to go back from) and when `env`
(`overview.md` §7.4 — it would not do what it says).

### Confirmation — saving a new Client ID

> Use this Client ID?
>
> Yoto Maker will start using the Client ID you pasted. Because this changes how
> the app signs in, you'll need to sign in to Yoto again afterwards.
>
> Nothing in your Yoto account changes.

| Role | Label |
| --- | --- |
| Cancel (`.btn ghost`) | `Never mind` |
| Confirm (`.btn primary`) | `Yes, use it` |

### Confirmation — going back to the built-in one

> Go back to the built-in Client ID?
>
> Yoto Maker will forget the Client ID you pasted and use the one it came with.
> You'll need to sign in to Yoto again afterwards.
>
> Nothing in your Yoto account changes.

| Role | Label |
| --- | --- |
| Cancel (`.btn ghost`) | `Never mind` |
| Confirm (`.btn primary`) | `Yes, use the built-in one` |

### Feedback messages

| Trigger | Class | String |
| --- | --- | --- |
| Saved | `.msg-box ok` | `Saved. Now sign in to Yoto again using the button above.` |
| Reset to built-in | `.msg-box ok` | `Done — back to the built-in Client ID. Now sign in to Yoto again using the button above.` |
| Empty input on Save | `.msg-box err` | `Please paste a Client ID first.` |
| Save failed | `.msg-box err` | `We couldn't save that. Please try again.` |
| App unreachable | `.msg-box err` | *(inherit the existing `api()` message from `app.js:15-17` — unchanged)* |

Both success messages point the user at the very next thing she must do. After
either action she is signed out, and the account section above will already have
flipped to `Not connected yet` — the message tells her that's expected and where
to go, rather than leaving her to discover a scary red state on her own.

---

## 5. Strings removed

| Location | Old string | Fate |
| --- | --- | --- |
| `index.html:126-127` | `Paste a Yoto Client ID to use your own Yoto app…` | Replaced by §4 description |
| `index.html:130` | `Paste Yoto Client ID here` | Replaced by §4 placeholder |
| `index.html:140` | `⚙️ Use a different Yoto account (advanced)` | Replaced by §1 step-3 link — **and that was a mistake; see §1a.** The user later went looking for almost exactly this sentence. `(advanced)` stays retired, but the *account* vocabulary is restored in the connected-state variant. |

## 6. Strings explicitly unchanged

`index.html` steps 1, 2, 4; the `#connectRow` info box and `#connectBtn`; the
About modal; the update banner; `#startOver`'s `window.confirm()`. This PR does
not touch them.
