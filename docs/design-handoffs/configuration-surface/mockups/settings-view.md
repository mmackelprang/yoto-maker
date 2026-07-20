# Mockups — Configuration surface

ASCII, because no rendered mockup exists for this surface. Proportions are
indicative; the authoritative geometry is the existing `styles.css` plus
[`../tokens.md`](../tokens.md).

---

## 1. Entry — the header, unchanged except for where the pill goes

```
┌───────────────────────────────────────────────────────────────────┐
│  🎵  Yoto Maker                            ( ● Yoto connected )   │  ← existing
└───────────────────────────────────────────────────────────────────┘        │
                                                                             │
                        clicking the pill — in any state — goes to Settings ─┘
```

No new header control. The pill already occupied this space and, when connected,
previously did nothing on click.

---

## 2. Settings view — the everyday healthy state

```
┌───────────────────────────────────────────────────────────────────┐
│  🎵  Yoto Maker                            ( ● Yoto connected )   │
└───────────────────────────────────────────────────────────────────┘

   ← Back to my card

   Settings                                             ← h2, focus target

   ┌─────────────────────────────────────────────────────────────┐
   │ Your Yoto account                                    h3     │
   │                                                             │
   │ Yoto Maker sends the cards you make to your Yoto account.   │  .setting-desc
   │ You sign in once, on Yoto's own website, and it remembers   │
   │ you on this computer.                                       │
   │                                                             │
   │ Use the button below if Yoto Maker has stopped being able   │  ← the sentence
   │ to send cards, or if you want to use a different Yoto       │    that lets ONE
   │ account.                                                    │    button do two
   │                                                             │    jobs
   │ ● Connected and working                              .setting-status (is-ok)
   │   We just checked with Yoto and everything's fine.          │
   │                                                             │
   │ ┌──────────────────────────┐                                │  .setting-actions
   │ │ 🔗 Sign in to Yoto again │                                │
   │ └──────────────────────────┘                                │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │ Yoto Client ID (advanced)                                   │
   │                                                             │
   │ Most people never need to change this. Yoto Maker comes     │
   │ with everything it needs already built in.                  │
   │                                                             │
   │ A Client ID is a code from Yoto's developer website that    │
   │ tells Yoto which app is asking to sign in. You'd only       │
   │ paste your own here if someone has asked you to.            │
   │ How to get one ↗                                            │
   │                                                             │
   │ ● Using the built-in Client ID                              │
   │   This is what most people use. Nothing to do here.         │
   │                                                             │
   │ Paste a Client ID                                    .setting-body
   │ ┌───────────────────────────────────────┐  ┌──────┐         │
   │ │ Paste your Yoto Client ID here        │  │ Save │         │
   │ └───────────────────────────────────────┘  └──────┘         │
   └─────────────────────────────────────────────────────────────┘

           ← no reset action here: source is "builtin",
             so there is nothing to go back from
```

Note the two sections use different optional slots — the account section has no
Body, the Client ID section has no Actions in this state — which is the check
that the slots are genuinely independent.

---

## 3. The state that matters — a broken connection

This is what the user sees on the visit that motivated the whole feature.

```
   ┌─────────────────────────────────────────────────────────────┐
   │ Your Yoto account                                           │
   │                                                             │
   │ …description…                                               │
   │                                                             │
   │ ● There's a problem with this connection        (red dot)   │
   │   Yoto Maker can't send cards right now. Signing in again   │
   │   usually fixes it.                                         │
   │                                                             │
   │ ┌──────────────────────────┐                                │
   │ │ 🔗 Sign in to Yoto again │                                │
   │ └──────────────────────────┘                                │
   └─────────────────────────────────────────────────────────────┘
```

The status line names the problem, and the very next thing on screen is the
single button that fixes it. No diagnosis required of the user.

This state is only reachable because of the live check in `overview.md` §7.5 —
today the app would render "Yoto connected" here.

---

## 4. Confirmation, inline

```
   ┌─────────────────────────────────────────────────────────────┐
   │ Your Yoto account                                           │
   │                                                             │
   │ …description…                                               │
   │                                                             │
   │ ● Connected and working                                     │
   │   We just checked with Yoto and everything's fine.          │
   │                                                             │
   │      ┌── .setting-actions is HIDDEN while this is open ──┐  │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │  Sign in to Yoto again?                    --warn-soft  │ │
   │ │                                                         │ │
   │ │  This forgets the Yoto account on this computer, then   │ │
   │ │  opens Yoto's website so you can sign in — with the     │ │
   │ │  same account, or a different one.                      │ │
   │ │                                                         │ │
   │ │  Nothing in your Yoto account changes. The cards        │ │ ← answers the
   │ │  you've already made are safe.                          │ │   unasked
   │ │                                                         │ │   question
   │ │                    ┌────────────┐ ┌───────────────────┐ │ │
   │ │                    │ Never mind │ │ Yes, sign in again│ │ │
   │ │                    └────────────┘ └───────────────────┘ │ │
   │ │                          ▲                              │ │
   │ │                    focus lands here                     │ │
   │ └─────────────────────────────────────────────────────────┘ │
   └─────────────────────────────────────────────────────────────┘
```

---

## 5. Waiting for the sign-in

```
   │ ● Waiting for you to sign in…                  (amber dot)  │
   │   We opened Yoto's website in another tab. Sign in there,   │
   │   then come back here.                                      │
   │                                                             │
   │ ┌────────────────────┐  ┌────────┐                          │
   │ │ Waiting for Yoto…  │  │ Cancel │                          │
   │ └────────────────────┘  └────────┘                          │
   │      (disabled)                                             │
```

Bounded at 3 minutes, and cancellable — see `interactions.md` §2.4. The current
implementation polls forever with no way out.

---

## 6. The `env` state — the honest dead end

```
   │ ● Set outside the app                          (amber dot)  │
   │   Someone set this up on this computer using YOTO_CLIENT_ID,│
   │   and that takes priority. To change it, they'll need to    │
   │   change it there.                                          │
   │                                                             │
   │ Paste a Client ID                                           │
   │ ┌───────────────────────────────────────┐  ┌──────┐         │
   │ │                                       │  │ Save │         │
   │ └───────────────────────────────────────┘  └──────┘         │
   │            (disabled)                       (disabled)      │
   │                                                             │
   │ You can still type one here, but it won't be used while     │
   │ the one above is set.                                       │
   │                                                             │
   │        ← "Go back to the built-in one" is ABSENT here:      │
   │          deleting the saved value would fall through to     │
   │          the env var, not the built-in one, so the label    │
   │          would be a lie                                     │
```

---

## 7. Step 3, after the move

```
   ┌─────────────────────────────────────────────────────────────┐
   │ (3) Send it to your Yoto                                    │
   │ This uploads your card to your Yoto account. You only sign  │
   │ in the first time.                                          │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ You'll need to connect your Yoto account first.          │ │  unchanged
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │           🔗 Connect my Yoto account                    │ │  unchanged
   │ └─────────────────────────────────────────────────────────┘ │
   │ ⚙️ Yoto connection settings                                 │  ← relabelled,
   │                                                             │    now a link
   │ ┌─────────────────────────────────────────────────────────┐ │    to settings
   │ │              🚀 Send to Yoto                            │ │
   │ └─────────────────────────────────────────────────────────┘ │
   └─────────────────────────────────────────────────────────────┘

   REMOVED from this step: the whole #setupRow block —
   the Client ID input, its explainer box, and #setupError.
```

Step 3 ends up **shorter** than it is today. The everyday path gets lighter, not
heavier, which is the constraint this placement was chosen to satisfy.

---

## 8. Adding setting #3 later

```
   ┌─────────────────────────────────────────────────────────────┐
   │ Your Yoto account                    …                      │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │ Yoto Client ID (advanced)            …                      │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │ Pictures drawn by AI                        ← new .setting  │
   │ …description…                                               │
   │ ● Turned off                                                │
   │ [ paste a key ]  [ Save ]                                   │
   └─────────────────────────────────────────────────────────────┘

   Cost: copy the template, fill the slots, append.
   No CSS. No layout change. No edits to the sections above.
```
