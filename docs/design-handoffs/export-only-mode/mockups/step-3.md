# Mockups — step 3, with the save-to-a-folder path

ASCII, because no rendered mockup exists for this surface. Proportions are
indicative; the authoritative geometry is the existing `styles.css`.

Structure and ordering are [`../overview.md`](../overview.md) §4.3.

> ### ⚠️ [`../copy.md`](../copy.md) is the authority on every string in this file
>
> The strings below are reproduced for layout only. **Where a mockup and
> `copy.md` disagree, `copy.md` wins and the mockup is the bug** — implement from
> `copy.md`, then fix the mockup.
>
> This is not a formality. §7's MP3 note carried the **pre-amendment** wording of
> `copy.md` §5.4 from 2026-09-05 until Planner caught it, and an implementer
> reading the picture rather than the copy file would have re-shipped the exact
> misleading sentence that amendment removed. Corrected 2026-09-05.

---

## 1. The everyday state — connected, nothing pressed

```
   ┌─────────────────────────────────────────────────────────────┐
   │ (3) Send it to your Yoto                                    │
   │ This uploads your card to your Yoto account. You only sign  │
   │ in the first time.                                          │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │              🚀 Send to Yoto                            │ │  .btn primary big
   │ └─────────────────────────────────────────────────────────┘ │  UNCHANGED
   │                                                             │
   │ ┌──────────────────────────────┐                            │  ← NEW
   │ │ 📁 Save the files to a folder│                            │  .btn (not primary,
   │ └──────────────────────────────┘                            │   not big)
   │ You’ll put them on Yoto’s website yourself. You don’t       │  .tiny
   │ need to be signed in for this.                              │
   │                                                             │
   │ ⚙️ Connect a different Yoto account                          │  UNCHANGED, still last
   └─────────────────────────────────────────────────────────────┘
```

**The whole everyday-path cost of this feature is what is drawn between the two
arrows: one `.btn` and two lines of 13px text.** Everything else in the spec is
`.hidden` until the button is pressed.

The hierarchy is carried by the button classes alone — `primary big` above,
plain `.btn` below — with no divider and no label saying which is which. A
`— or —` rule (step 1's `.or`) was rejected: it costs ~40px on every visit and
asserts that the two are peers, which they are not (`../overview.md` §4.1).

---

## 2. The state this feature exists for — never signed in

```
   ┌─────────────────────────────────────────────────────────────┐
   │ (3) Send it to your Yoto                                    │
   │ …hint…                                                      │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ To send cards straight to your Yoto, connect your        │ │  ← EDITED
   │ │ account first.                          .msg-box info    │ │    (copy.md §1)
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │           🔗 Connect my Yoto account                    │ │  unchanged
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │              🚀 Send to Yoto        (disabled)          │ │  app.js:288
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│  ← LIVE                    │
   │ └──────────────────────────────┘                            │
   │ You’ll put them on Yoto’s website yourself. You don’t       │
   │ need to be signed in for this.                              │
   │                                                             │
   │ ⚙️ Yoto connection settings                                 │
   └─────────────────────────────────────────────────────────────┘
```

Two things are doing the work here, and neither needed designing.

- **The dead grey primary above a live button below** is a stronger signal than
  any sentence: the thing that needs a sign-in is off, the thing that doesn't is
  on. It falls out of `app.js:288` already disabling `#sendBtn` and this feature
  never disabling `#exportBtn` (`../overview.md` §4.7).
- **The edited info box no longer claims connecting is a prerequisite for
  finishing a card** — only for sending from the app. It does not advertise the
  alternative; the caption twelve pixels below already does.

---

## 3. After a failed send — the adjacency

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ ⚠ …send error…                             .msg-box err │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌──────────────────────────────┐                            │  ← directly
   │ │ 📁 Save the files to a folder│                            │    beneath the
   │ └──────────────────────────────┘                            │    symptom
   │ You’ll put them on Yoto’s website yourself. You don’t       │
   │ need to be signed in for this.                              │
   │                                                             │
   │ ⚙️ Connect a different Yoto account                          │
   └─────────────────────────────────────────────────────────────┘
```

This is the same property `../overview.md` §4.3 point 2 chose the position for,
and the same one configuration-surface §12.4 chose `#advRow`'s position for. The
user's eyes are on the red box; the recovery is the next thing they meet.

Note the pairing that results: **one recovery repairs the connection
(`⚙️ Connect a different Yoto account`), the other goes around it.** Neither
crowds the other, because they are 13px apart in weight.

---

## 4. Blocked by a bad Client ID — two recoveries, one below the other

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Yoto Maker can’t sign in to Yoto, because the Client ID │ │  #connectWarn
   │ │ saved on this computer isn’t one.        .msg-box err   │ │  (shipped,
   │ │ ┌───────────────────────────────────┐                   │ │   unchanged)
   │ │ │ Put back the built-in Client ID   │                   │ │
   │ │ └───────────────────────────────────┘                   │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│                            │
   │ └──────────────────────────────┘                            │
   │ You’ll put them on Yoto’s website yourself. You don’t       │
   │ need to be signed in for this.                              │
   │                                                             │
   │ ⚙️ Yoto connection settings                                 │
   └─────────────────────────────────────────────────────────────┘
```

configuration-surface §13.5 hard-blocks sign-in whenever the Client ID verdict is
`invalid`, in every tier. In the `env` tier that block has **no button at all** —
the app cannot perform the fix, so `copy.md` §4d carries the recovery in words.

**Appending the save row after `#connectWarn` gives that state a live way
forward for the first time**, and it costs nothing: it is a consequence of
appending rather than inserting.

---

## 5. Working

```
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│  (disabled)                │
   │ └──────────────────────────────┘                            │
   │ …caption…                                                   │
   │                                                             │
   │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  .progress .bar
   │ Saving “Chapter Three” (3 of 5)…                            │  role="status"
```

Per-track messages, not one "Saving…". `index.html:102-106` already makes this
argument for the add batch: the progress text is the only signal of liveness a
non-sighted user has.

**No Cancel button.** `jobs.py` has no cancellation, and the `#addCancel`
precedent works by aborting a frontend `fetch` on a synchronous path that has no
equivalent here (`../interactions.md` §3.4).

---

## 6. Saved — the everyday success

```
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│                            │
   │ └──────────────────────────────┘                            │
   │ …caption…                                                   │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 🎉 All 5 tracks are saved, in a folder called “Bedtime   │ │  #exportDone
   │ │ Stories” — in your Documents, under Yoto Maker.         │ │  .msg-box ok
   │ └─────────────────────────────────────────────────────────┘ │  focus lands here
   │                                                             │
   │ ┌────────────────────────┐  ┌────────────────────┐          │  .done-actions
   │ │ 📄 What to do next     │  │ 📂 Open the folder │          │
   │ └────────────────────────┘  └────────────────────┘          │
   │       .btn primary                .btn                      │
   │                                                             │
   │ ⚙️ Connect a different Yoto account                          │
   └─────────────────────────────────────────────────────────────┘
```

**The instructions are primary and the folder is secondary — deliberately
inverted.** A user who opens the folder first meets a pile of files and no basis
for a decision; a user who reads the page first is told to open the folder as
step 3 of 6 (`../overview.md` §7.1).

**The folder is named in words, not as a path.** *"In your Documents, under Yoto
Maker"* is a sentence she can follow on a machine that is not in front of her.
The full path appears only when the folder cannot be opened for her (§9).

---

## 7. Saved, with something to say

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 🎉 All 19 tracks are saved, in a folder called “The BFG”│ │  .msg-box ok
   │ │ — in your Documents, under Yoto Maker.                  │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ One of your tracks was too long for a Yoto card, so     │ │  #exportNote
   │ │ it’s saved as more than one file — “Chapter Eighteen”   │ │  .msg-box info
   │ │ is in 2 parts. Add them all, in number order, and       │ │
   │ │ they’ll play one after the other.                       │ │
   │ │                                                         │ │
   │ │ Yoto Maker saved MP3 copies of 2 of your files, because │ │  second <p>
   │ │ Yoto’s website is fussier about this than the app is.   │ │  in the SAME box
   │ │ They’re the same audio, and nothing else changed:       │ │
   │ │ 04 - The Sea, 11 - Rain.                                │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌────────────────────────┐  ┌────────────────────┐          │
   │ │ 📄 What to do next     │  │ 📂 Open the folder │          │
   │ └────────────────────────┘  └────────────────────┘          │
```

All notes are `.msg-box info` — **neutral instruction, never red, never a
`.msg-box.warn`.** Nothing failed. configuration-surface `tokens.md` §1 refused
to add a warn variant and this is not the amendment that overturns it.

Paragraphs in one box, in the fixed order `../overview.md` §10.3's table gives,
using `.msg-box p` / `.msg-box p:last-child` (`styles.css:257-258`), which
already exist for exactly this. **The box is omitted entirely when nothing
fired** — an empty `.msg-box` renders as a stray grey bar.

**Reading order is importance order, and the actions come last** — she cannot
reach the buttons without the notes being in her scan path.

---

## 7a. Over one of Yoto's limits

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 🎉 All 62 tracks are saved, in a folder called “Harry    │ │  .msg-box ok
   │ │ Potter” — in your Documents, under Yoto Maker.          │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ This card is 604 MB altogether, and Yoto allows 500 MB  │ │  #exportNote
   │ │ on one card.                                            │ │  .msg-box info
   │ │                                                         │ │
   │ │ This card is 8 hours 40 minutes altogether, and Yoto    │ │  one line per
   │ │ allows 5 hours on one card.                             │ │  ceiling…
   │ │                                                         │ │
   │ │ Yoto’s website may refuse some of it. If it does, make  │ │  …and ONE
   │ │ two shorter cards instead of one.                       │ │  shared fix
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌────────────────────────┐  ┌────────────────────┐          │
   │ │ 📄 What to do next     │  │ 📂 Open the folder │          │
   │ └────────────────────────┘  └────────────────────┘          │
```

**The folder is still complete and the buttons are still live.** Nothing failed;
the app is reporting a number it read off Yoto's support page
(`../overview.md` §8.3) and cannot verify. That is why the box is `info`, why the
verb is *may*, and why there is no block.

**The recovery is factored out into one closing sentence.** At about 192 kbps
Yoto's 500 MB and 5-hour ceilings are the same card, so these two lines very
often fire together — repeating *"make two shorter cards"* under each would read
as two problems with two fixes. **One fact per ceiling, one fix for all of them.**

**The per-track case reads differently**, deliberately (`../copy.md` §5.9): it
names the track and its size, and its recovery points at a person rather than an
action, because re-encoding an MP3 to shrink it is a quality decision the app has
no basis to make for her.

```
   │ │ One of your tracks is bigger than Yoto allows for a      │ │
   │ │ single track — Yoto’s limit is 100 MB. Yoto’s website    │ │
   │ │ may refuse it. If it does, tell whoever set Yoto Maker   │ │
   │ │ up for you which one it is: 09 - Chapter Nine (118 MB).  │ │
```

This is `../overview.md` §8.6's split made visible: **the app acts on format and
advises on size**, because a wrong format is certainly refused while a size limit
is a third party's current policy, and because acting wrongly on format costs a
pointless re-encode while acting wrongly on size quietly degrades her audio.

---

## 8. Partial — one track didn't make it

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 4 of your 5 tracks are saved, in a folder called        │ │  no 🎉
   │ │ “Bedtime Stories” — in your Documents, under Yoto Maker.│ │  .msg-box ok
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ One track couldn’t be saved: “Chapter Four”. We couldn’t│ │  #exportError
   │ │ read that file — it may be open in another program.     │ │  .msg-box err
   │ │                                                         │ │  focus lands HERE
   │ │ Everything else is in the folder. The page in the folder│ │  (overrides §6)
   │ │ lists what’s actually there.                            │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌────────────────────────┐  ┌────────────────────┐          │
   │ │ 📄 What to do next     │  │ 📂 Open the folder │          │
   │ └────────────────────────┘  └────────────────────┘          │
```

Three things are true here at once and all three are required.

1. **The count in the green box has already dropped** from `All 5` to
   `4 of your 5`, and the `🎉` is gone. The two boxes agree with each other.
2. **The failure names the track and the reason**, reusing the app's existing
   plain-language file errors (`sources/audiofile.py:41`).
3. **The instruction sheet lists only what actually landed** and carries the
   missing-track notice at the top (`../copy.md` §6.8). The second paragraph
   above is the readable form of that requirement — if the sheet stops matching
   the folder, that sentence becomes a lie.

A red box beside a green one is the honest rendering of a partial outcome, and it
is what the multi-file add already produces.

**The box drawn above is `#exportError`, and it survives a press of
`📂 Open the folder`.** §8a draws what happens when that press fails.

---

## 8a. Partial, and then the folder won’t open — two red boxes, two regions

*(Added 2026-09-05. This state is the deferral that produced
[`../interactions.md`](../interactions.md) §4.4's ruling: before it, the reveal
failure overwrote the box above and destroyed the pointer to the instruction
sheet.)*

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 4 of your 5 tracks are saved, in a folder called        │ │  #exportDone
   │ │ “Bedtime Stories” — in your Documents, under Yoto Maker.│ │  .msg-box ok
   │ └─────────────────────────────────────────────────────────┘ │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ One track couldn’t be saved: “Chapter Four”. We couldn’t│ │  #exportError
   │ │ read that file — it may be open in another program.     │ │  .msg-box err
   │ │                                                         │ │
   │ │ Everything else is in the folder. The page in the folder│ │  ← THIS SENTENCE
   │ │ lists what’s actually there.                            │ │    IS THE POINT
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌────────────────────────┐  ┌────────────────────┐          │  .done-actions
   │ │ 📄 What to do next     │  │ 📂 Open the folder │← pressed │
   │ └────────────────────────┘  └────────────────────┘          │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Yoto Maker couldn’t open the folder for you. It’s here: │ │  #exportOpenError
   │ │ C:\Users\mark\OneDrive\Documents\Yoto Maker\Bedtime      │ │  .msg-box err
   │ │ Stories                                                 │ │  .mono-value
   │ └─────────────────────────────────────────────────────────┘ │  focus lands here
   │                                                             │
   │ ⚙️ Connect a different Yoto account                          │
```

**Three boxes, and each one is about a different thing.** Green: what the save
achieved. First red: what the save could not do. Second red: what the button she
just pressed could not do. The order on screen is the order the events happened.

**The new region is below `#exportActions`, not above `#exportDone`.** Feedback
sits beneath the control that raised it — `../overview.md` §4.3 point 1's own
rule, which refused a placement precisely because it would make one button's
feedback appear next to a different button.

**Why the middle box may not be overwritten.** *"The page in the folder lists
what's actually there"* is the only pointer she has to the instruction sheet,
which is the authority on what actually landed (`../overview.md` §10.4 point 3)
and which carries the missing-track notice (`../copy.md` §6.8). Destroying it at
the moment she is trying to open that folder is the specific harm the ruling
prevents — not a tidiness concern.

**The reveal box, and only the reveal box, clears on a successful open.** The two
above it are a record of the run and live until the next run
(`../interactions.md` §4.4.2).

---

## 9. Degraded — the folder can’t be opened for her

```
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ 🎉 All 5 tracks are saved, in a folder called “Bedtime   │ │
   │ │ Stories” — in your Documents, under Yoto Maker.         │ │
   │ │                                                         │ │
   │ │ The folder is here:                                     │ │
   │ │ C:\Users\mark\OneDrive\Documents\Yoto Maker\Bedtime      │ │  .mono-value,
   │ │ Stories                                                 │ │  word-break
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ┌────────────────────────┐                                  │
   │ │ 📄 What to do next     │      ← 📂 Open the folder is     │
   │ └────────────────────────┘        ABSENT, not disabled      │
```

**Omitted, never disabled.** The same discipline configuration-surface §3.5.2
applies to the reveal toggle and §7.4 applies to the reset action: a control that
could do nothing is removed, because a disabled button invites her to keep
pressing it.

The path is `.mono-value` so a long redirected OneDrive path wraps inside the
column rather than pushing the card wide. That is the specific regression to look
for in UAT, because it appears only in this state and only when narrow.

---

## 10. Failed — nothing was saved

```
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│  ← still live               │
   │ └──────────────────────────────┘                            │
   │ …caption…                                                   │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Yoto Maker couldn’t save the files.                     │ │  .msg-box err
   │ │                                                         │ │
   │ │ This computer looks like it’s out of space.             │ │
   │ │                                                         │ │
   │ │ Nothing was saved, and nothing on this card has changed.│ │  ← true only
   │ │ You can try again, or send it to your Yoto instead.     │ │    because a
   │ └─────────────────────────────────────────────────────────┘ │    failed run
   │                                                             │    removes the
   │ ⚙️ Connect a different Yoto account                          │    folder it made
   └─────────────────────────────────────────────────────────────┘
```

No success box, no buttons, and **no half-written folder left behind** — a folder
that exists but is wrong is worse than no folder, because she will find it and
use it.

The last paragraph is this package's reassurance sentence, built the same way
configuration-surface `copy.md` §4c's is: **a readable statement of an
invariant.** If a refactor stops deleting the folder on failure, that string must
change with it.

> ⚠️ **This is the picture of a failure the app was *told* about.** It is not the
> picture of every red box after a save press. When the app loses contact with a
> job instead — a dropped status poll — it does not know the outcome and may not
> claim one. **§10a is that state, and these words are wrong for it.**

---

## 10a. Lost contact — the app does not know what happened

*(Added 2026-09-05. This state used to render §10 above, asserting "Yoto Maker
couldn't save the files" and "Nothing was saved" about a job that might have been
writing files at that moment. `../copy.md` §5.10 replaces it.)*

```
   │ ┌──────────────────────────────┐                            │
   │ │ 📁 Save the files to a folder│  ← live again               │
   │ └──────────────────────────────┘                            │
   │ …caption…                                                   │
   │                                                             │
   │        (the progress bar is GONE — the app has stopped       │
   │         watching, and a bar on screen would say it hadn’t)   │
   │                                                             │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Yoto Maker stopped answering while it was saving, so it │ │  #exportError
   │ │ can’t tell you whether it finished. Nothing on this card │ │  .msg-box err
   │ │ has changed.                                            │ │  focus lands here
   │ │                                                         │ │
   │ │ Look in your Documents, under Yoto Maker, for a folder  │ │
   │ │ named after this card. If there’s a page in it called   │ │  ← the test she
   │ │ “What to do next”, the save finished — that page lists  │ │    can actually
   │ │ what’s actually there.                                  │ │    perform
   │ │                                                         │ │
   │ │ If there’s no folder, or no “What to do next” page in   │ │
   │ │ it, make sure Yoto Maker is still running — look for    │ │
   │ │ the 🎵 icon near the clock — then press “📁 Save the     │ │
   │ │ files to a folder” again. Nothing you already have will │ │
   │ │ be written over.                                        │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                             │
   │ ⚙️ Connect a different Yoto account                          │
```

**No success box and no buttons — and that is what the copy is written around.**
No result arrived, so `📄 What to do next` was never drawn. **Naming the page in
words is her only route to the sheet**, which is why paragraph 2 spells out the
file's name rather than pointing at a control.

**Three paragraphs, three questions.** What happened · how do I find out · what
do I do. It is the longest string in this package, and it is the state with the
most ways to go wrong and the least information available.

**Paragraph 1 keeps half of §10's last sentence and drops the other half.**
*"Nothing on this card has changed"* is true however the save ended. *"Nothing
was saved"* is not knowable. That single deletion is the whole correction.

**The folder is not named**, and must not be. The panel has no result, so it does
not know the folder's name — the card name is not it (sanitized, possibly `(2)`).
Naming it would be the JS-side reconstruction `../overview.md` §11.3 forbids,
arriving as a helpful-looking sentence.

**Paragraph 2 leans on a write-order contract.** `What to do next.html` is
written **last** (`export/runner.py:247`), so its presence is a reliable
completeness signal. **If that write order ever changes, this string becomes a
lie** — the same standing condition §10's reassurance sentence carries.

The send path gets the parallel message in `#sendError` — `../copy.md` §9, and
§9.2 for why the two are near-identical rather than shared. **It did not ship:**
the maintainer took §9.1's stated fallback on 2026-09-05, so `#sendError` keeps
today's generic transport line and §9 is a written follow-up. See §9's banner
and `../interactions.md` §11 item 5.
