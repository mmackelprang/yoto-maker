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
| Header pill `aria-label` | `Yoto connection settings` |
| Header pill `title` | `Yoto connection settings` |
| Footer link | `Settings` |
| Step 3 advanced link (replaces `#advToggle` copy) | `⚙️ Yoto connection settings` |

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
| User cancelled on Yoto's site | `.msg-box info` | `Sign-in was cancelled. You can try again whenever you're ready.` |
| Yoto rejected the sign-in | `.msg-box err` | `Yoto couldn't complete the sign-in. Please try again.` |
| Couldn't reach Yoto | `.msg-box err` | `We couldn't reach Yoto. Check your internet connection, then try again.` |
| Waiting timed out (3 min) | `.msg-box info` | `We stopped waiting for the sign-in. If you finished signing in on Yoto's website, press "Sign in to Yoto again" — otherwise you can try again now.` |
| User pressed Cancel while waiting | `.msg-box info` | `Stopped waiting. You can close the Yoto tab if it's still open.` |

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
| `saved` | green | `Using your own Client ID` | `Ends in {last3}. Saved on this computer only.` |
| `env` | amber | `Set outside the app` | `Someone set this up on this computer using YOTO_CLIENT_ID, and that takes priority. To change it, they'll need to change it there.` |

**The `env` sub-line is the only place in the app where an environment variable
name is spoken to the user.** That is a deliberate, narrow exception: the state
is otherwise inexplicable (a saved value would appear to be silently ignored),
and the person who can act on it is by definition technical enough to recognize
the name. The sentence is addressed to *her* about *them* — "they'll need to
change it" — so she knows the fix isn't hers to make.

### Body — the input

| Element | String |
| --- | --- |
| Label (`.tiny`, above input) | `Paste a Client ID` |
| Input placeholder | `Paste your Yoto Client ID here` |
| Save button | `Save` |

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
| `index.html:140` | `⚙️ Use a different Yoto account (advanced)` | Replaced by §1 step-3 link |

## 6. Strings explicitly unchanged

`index.html` steps 1, 2, 4; the `#connectRow` info box and `#connectBtn`; the
About modal; the update banner; `#startOver`'s `window.confirm()`. This PR does
not touch them.
