# Copy — Save-to-a-folder mode

**Every user-visible string, verbatim.** Nothing here is a placeholder. Builder
should copy these exactly; deviations are a Polisher finding.

Register: `docs/INSTALL-FOR-MOM.md`. Second person, present tense, short
sentences. No banned vocabulary (see [`../README.md`](../README.md)), and this
package **adds no exception to that list**. In particular the words **export**,
**directory**, **path**, **file format**, **codec**, **transcode**, **MP3
encoding** and **metadata** appear nowhere a user can see them. The verb is
*save*, the noun is *files*, the destination is *a folder*.

`MP3` on its own is permitted and used: it is the name of a thing she has heard
of and can see in her own file names, not a technical concept she has to
understand.

Typographic apostrophes (`’`) throughout, matching existing markup
(`index.html:264`, `app.js:408`).

---

## 1. The one existing string that changes

`index.html:173`, inside `#connectRow`.

| | String |
| --- | --- |
| Shipped | `You'll need to connect your Yoto account first.` |
| **New** | `To send cards straight to your Yoto, connect your account first.` |

**Why it must change.** Once saving exists, *"you'll need to connect first"* is
false — connecting is a prerequisite for sending **from the app**, not for
finishing a card. Leaving a string that no longer matches what the screen can do,
directly in front of the user who needs the other answer, is the defect
configuration-surface §12.3 recorded and named.

**Why it does not mention saving.** Advertising the alternative inside the
connect box would bury the connect intent, which is still the right first answer
for most people. The save button's own caption (§2) sits twelve pixels below and
says *"You don't need to be signed in for this."* — that is the second half of
the same visual scan, and it is where the alternative belongs.

**Rejected variants**

| Rejected | Why |
| --- | --- |
| `You'll need to connect your Yoto account first — or save the files and put them on Yoto's website yourself.` | Two intents in one sentence inside a box whose job is the first one. Unscannable, and it demotes connecting for the ~200 visits where connecting is correct. |
| `You'll need to connect your Yoto account to send cards from Yoto Maker.` | *"from Yoto Maker"* reads oddly to someone who is looking at Yoto Maker. |
| Leave it alone | It is now false. |

**Explicitly unchanged in `#connectRow`:** `🔗 Connect my Yoto account`. The
first-time path keeps its exact words, as it has through every prior amendment.

---

## 2. The save button and its caption

Rendered in `#exportRow`, always, in both connection states.

| Element | String |
| --- | --- |
| Button (`.btn`, `#exportBtn`) | `📁 Save the files to a folder` |
| Caption (`.tiny`, below the button) | `You’ll put them on Yoto’s website yourself. You don’t need to be signed in for this.` |

**The split between the two is configuration-surface §6.1's rule**, applied
unchanged: the button stays short and scannable, and the line beneath it does the
disambiguating. A label that tried to carry both — `Save the files so I can
upload them myself on Yoto's website` — is not a button label.

**Why these words.** configuration-surface §12.2's lesson governs: *a string is
only findable if it contains the word the person is holding.* The person holding
a word here has been told, by whoever set this up, some version of *"save the
files and put them on the Yoto website yourself."* The words she is carrying are
**save**, **files**, **folder**, **website**, **myself**. All five appear across
the two strings, and four of the five are in the first eight words.

**Rejected labels**

| Rejected | Why |
| --- | --- |
| `📁 Export to a folder` | *Export* is the word this package is named after and the one word the user must never see. It is a developer's word for the operation, not a person's word for the outcome. |
| `📁 Save the files to a folder instead` | *instead* is the caption's job, and it stops being quite true in the not-connected state where there is nothing live to do instead of. Making one word state-dependent to fix that would be ceremony for a word the caption already covers. |
| `💾 Save the files to a folder` | The floppy disk is a **learned convention** — the same objection configuration-surface §12.6 raised against the gear (*"not a picture of anything"*). `📁` is a picture of the thing the button produces. |
| `📁 Save my files` | Loses *folder*, which is half of what she is looking for, and "my files" is not how anyone refers to the audio they just added. |
| `📁 Save the audio files to a folder` | Accurate but longer, and the folder also holds pictures and a page of instructions, so *audio* narrows it wrongly. |
| `📁 Upload it myself` | Names a thing the button does not do. The button saves; she uploads, later, elsewhere. |

**Why the caption's second sentence is always present.** `You don’t need to be
signed in for this.` is eight words and is close to irrelevant to a connected
user — and it is the single most valuable sentence on the screen for the user who
is stuck at the sign-in wall. It is never false in any state, so unlike §1a of
the configuration surface there is no case for making it conditional.

**Why `Yoto’s website` and not `my.yotoplay.com`.** The caption is 13px on the
everyday path; an address there is noise. The address appears once, as a real
clickable link, in the instruction sheet (§6.2) — at the moment she needs to go
there.

---

## 3. Refusals — pressed with nothing to save

Rendered in `#exportError` (`.msg-box err`, `role="alert"`). Both are server-side
refusals raised before anything is written, mirroring `app.py:634-638`.

| Guard | String |
| --- | --- |
| No tracks | `Add some audio before saving it.` |
| No card name | `Give your card a name before saving it.` |

**These are deliberate near-copies of the send path's two refusals** —
`Add some audio before sending to Yoto.` and `Give your card a name before
sending it.` Two sentences that differ by two words is not duplication to be
refactored away: it is how the user learns that the two buttons are peers doing
the same job by different means.

**The button is not disabled in either case.** configuration-surface §13.5:
*"Disabling it with no visible reason is the dead-end antipattern… Pressing it is
the fastest path to the explanation."* Here the reason is visible (step 1 says
`No audio added yet.`), which makes the refusal a confirmation rather than a
surprise.

---

## 4. Working

Rendered in `#exportMsg` (`role="status"`), beneath `#exportProgress`'s bar.

| Phase | String |
| --- | --- |
| Starting | `Making the folder…` |
| Per track | `Saving “{track title}” ({n} of {total})…` |
| Converting a track | `Turning “{track title}” into an MP3 ({n} of {total})…` |
| Pictures | `Saving the pictures…` |
| Instructions | `Writing the instructions…` |

**Per-track messages, not a single "Saving…".** `index.html:102-106` already
argues this for the add batch and the argument is unchanged: *"the progress text
is the ONLY signal of liveness a non-sighted user has, and hearing nothing for
forty seconds is indistinguishable from a hung app."*

**The title is quoted with typographic quotes**, matching the app's existing
prose. If a title is long it is not truncated here — the message wraps.

**`Turning “…” into an MP3`** is the only place the conversion is narrated as it
happens. It is phrased as something being done *for* her, with no explanation:
the *why* belongs in the note that survives on screen afterwards (§5.4), not in a
line that flashes past.

**There is no Cancel string** because there is no Cancel button
(`overview.md` §10.2).

---

## 5. Success

### 5.1 The result box

`#exportDone`, `.msg-box ok`.

**All tracks saved:**

> `🎉 All {n} tracks are saved, in a folder called “{folder name}” — in your Documents, under Yoto Maker.`

**Some tracks saved (partial — see §5.6):**

> `{k} of your {n} tracks are saved, in a folder called “{folder name}” — in your Documents, under Yoto Maker.`

**One track:**

> `🎉 Your track is saved, in a folder called “{folder name}” — in your Documents, under Yoto Maker.`

**Why the folder is named in words rather than shown as a path.** *"In your
Documents, under Yoto Maker"* is a sentence she can follow on a machine that is
not in front of her, and it is what a person says out loud. The full path is not
clutter she needs on the happy path — it appears only when the folder cannot be
opened for her (§5.5), where it stops being clutter and becomes the answer.

**The `🎉` matches the app's existing success register** — `copy.md` §3 of the
configuration surface uses it for the completed sign-in, and `INSTALL-FOR-MOM.md`
uses it twice. **It is dropped from the partial message**, deliberately:
celebrating an incomplete result is the kind of small dishonesty that costs
trust, and the missing track is named directly below.

**There is deliberately no `0 of your 5 tracks are saved` variant, and this is a
specification, not an omission** *(confirmed 2026-09-05 — Planner had inferred
it correctly and it was not written down)*.

> **The boundary between §5.6 (partial) and §5.7 (total failure) is whether at
> least one track was written. Zero tracks written is a total failure**: no
> success box, no action buttons, and **the folder is removed**, even when the
> card picture and the instruction sheet could have been written successfully.

A folder holding a picture, a page of instructions and no audio is worse than no
folder at all. She would open it, find a sheet listing nothing, and have to work
out for herself that the thing she asked for did not happen — while the green box
above told her it had. `#exportDone` must never render a zero.

The reason the picture and the sheet do not rescue the run is that **neither is
the deliverable.** The audio is. §5.7's *"Nothing was saved"* stays literally
true because the folder goes with it.

### 5.2 The actions

`#exportActions`, `.done-actions` — the construction `#labelDone` already uses.

| Order | Element | String |
| --- | --- | --- |
| 1 | `<a class="btn primary" target="_blank">` | `📄 What to do next` |
| 2 | `<button class="btn">` | `📂 Open the folder` |

**The instructions are the primary action** — `overview.md` §7.1 argues why the
obvious ordering is inverted here.

**`What to do next` is the same string as the file in the folder**
(`What to do next.html`), deliberately. One name in two places costs nothing and
removes the need for a bridging sentence. `Read me first.html` was drafted first
— it is the stronger convention *inside a folder* — and was rejected because it
would have needed the panel to explain that the button and the file are the same
thing.

**Rejected labels:** `Instructions` (names the contents, not the occasion —
configuration-surface §13.4's rule), `Help` (collides with Settings' *"If you
need to ask for help"*), `How to upload these` (contains a task word she has not
been given yet).

### 5.3 Note — a long track was split

`#exportNote`, `.msg-box info`. Shown only when at least one track's title ends
in `(part N)`.

**One track was split** — the common case:

> `One of your tracks was too long for a Yoto card, so it’s saved as more than one file — “{title}” is in {n} parts. Add them all, in number order, and they’ll play one after the other.`

**Two or more tracks were split** *(added 2026-09-05 — this had no wording)*:

> `{n} of your tracks were too long for a Yoto card, so each one is saved as more than one file: {list}. Add them all, in number order, and they’ll play one after the other.`

`{list}` is `“{title}” ({n} parts)`, comma-separated — e.g.
`“Chapter Three” (2 parts), “Chapter Twelve” (4 parts)`.

**One paragraph, never one per split group.** Planner planned a paragraph per
group as a stopgap; **this replaces it.** Two reasons:

1. **It is one fact about the card, not N facts.** She does not act on each split
   separately — the action is the same sentence either way, *add them all in
   number order*, and repeating it three times reads as three problems with three
   fixes. Same reasoning that factored the recovery out of §5.9's ceiling lines.
2. **It would blow the note box's budget.** `overview.md` §10.3 fixes the box at
   five paragraphs, one of which is the split. A card with four split tracks
   would push the conversion and ceiling notes off the bottom of a user's scan.

**The singular string already handles many parts, and that is the case that
matters most.** *The Wild Robot* — the maintainer's first real test card — is a
single ~3h50m source that splits into **five** parts. That is
`“The Wild Robot” is in 5 parts`, the singular string, working exactly as
written. The plural above is for a different and rarer shape: **several distinct
tracks** each splitting, which happens when someone adds a folder of hour-long
CD rips.

**Why she is told at all.** On the send path the split is invisible and she never
needs to know. Here she will open the folder and see five files where she added
one, and unexplained extra files read as a bug. The sentence also pre-empts the
wrong recovery — deleting them.

**It says what to do, not just what happened.** *"Add them all, in number
order"* is the whole action.

### 5.4 Note — files were saved as MP3s

`#exportNote`, `.msg-box info`. Shown only when at least one track was converted
(`overview.md` §8.4).

> `Yoto Maker saved MP3 copies of {n} of your files, because Yoto’s website is fussier about this than the app is. They’re the same audio, and nothing else changed: {list}.`

Where `{list}` is the affected tracks by number and title, e.g.
`02 - The Sea, 05 - Rain`.

**Singular variant:**

> `Yoto Maker saved an MP3 copy of one of your files, because Yoto’s website is fussier about this than the app is. It’s the same audio, and nothing else changed: {list}.`

**Amended 2026-09-05.** This sentence previously opened *"{n} of your files
weren't MP3s, so…"*. With `.m4a` and `.aac` now copied as-is
(`overview.md` §8.4), that phrasing could be **quietly misleading**: a card with
one `.m4a` (kept) and one `.flac` (converted) would read *"1 of your files wasn't
an MP3"* while two of them weren't. Each individual statement was true; the
implication was not. Leading with what Yoto Maker did, rather than with a claim
about her files, removes the inference entirely.

**When both §5.3 and §5.4 apply**, they render as two paragraphs in the one
`#exportNote` box, split first. `.msg-box p` and `.msg-box p:last-child` already
exist for exactly this (`styles.css:257-258`).

**Why she is told.** She is not being asked to act. She is being told because a
file with her track's name and an extension she did not choose is exactly the
kind of surprise that makes a person stop and call someone. One sentence
pre-empts the call.

**Why *"fussier about this than the app is"*.** It gives the difference a cause
she can hold without a single technical word, and it is true. Rejected:
*"because Yoto's website only accepts MP3 files"* — an assertion about a third
party's behaviour that the app cannot verify and that would become false the day
it changes (the same conservatism configuration-surface §13.2 applied to the
32-character Client ID rule).

**And it stays rejected now that the accepted set is known.** `overview.md` §8.2
resolved it to `MP3 / M4A / AAC`, so naming the three here is finally *possible*.
It is still wrong, for two reasons that both got stronger rather than weaker:

- **The evidence is documentation, not tested behaviour** (§8.2's provenance
  box), and whether the *server* accepts more is explicitly unresolved (§16.3).
  Printing three acronyms as a rule would state as settled the one thing that
  isn't.
- **Three acronyms is a register cost with no payoff.** She cannot act on the
  list — the app has already done the acting. The sentence's whole job is to stop
  her worrying about a file name she didn't choose, and *"fussier about this than
  the app is"* does that in words a person uses.

The numbers she *can* act on — Yoto's size and count limits — do get printed, in
§5.9 and in the sheet's troubleshooting list, because those have a recovery she
can perform.

**Never `.msg-box err`, never red.** Nothing failed. configuration-surface
`tokens.md` §1 refused to add a `.msg-box.warn` and this is not the amendment
that overturns it; `.info` — *"neutral instruction"* — is what this is.

### 5.5 When the folder cannot be opened for her

`📂 Open the folder` is **omitted, not disabled** (`overview.md` §7.3). In its
place, appended to `#exportDone`:

> `The folder is here: {full path}`

with the path in `.mono-value` — the utility that exists precisely so a
machine-generated string can be read character by character
(configuration-surface `tokens.md` §3a).

**Rejected:** a disabled button. configuration-surface §3.5.2 and §13.5 both
apply the same discipline — *a control is omitted, never disabled, whenever it
could do nothing* — because a disabled button invites her to keep pressing it.

### 5.5a When the button is pressed and opening fails *(added 2026-09-05)*

§5.5 covers the case the app knows about **in advance** — the button is never
drawn. These two are failures that happen at the press, and
`interactions.md` §4.4 said only that they *"render into `#exportError`"* without
saying what.

> **They do not render into `#exportError`. They render into `#exportOpenError`,
> a second `.msg-box err role="alert"` region placed immediately *below*
> `#exportActions`** *(ruled 2026-09-05 — see `interactions.md` §4.4, which
> carries the full contract).*
>
> **Why a second region and not a composition rule in the shared one.**
> `#exportError` is the **save button's** feedback region: it holds a refusal
> (§3), a partial-save notice (§5.6) or a total failure (§5.7), and every one of
> those is a record of the run that must survive until the next run. A reveal
> failure is feedback on a *different* button, with a different lifetime — it is
> transient, and it should clear the moment the folder does open. Two lifetimes
> in one region is what forced a flag to protect one from the other, and a flag
> is a thing that can be forgotten.
>
> **The sentence it was destroying is the one that matters most.** After a
> partial save, `#exportError` holds *"Everything else is in the folder. The page
> in the folder lists what's actually there."* — the sentence §6.8's
> missing-track notice depends on, and **the only pointer she has to the
> authority on what is actually in that folder.** A reveal failure overwriting it
> deletes that pointer at the exact moment she is trying to open the folder. This
> is not a tidiness argument; it is the specific harm.
>
> **And the placement is `overview.md` §4.3 point 1's own rule.** That rule
> refused to put `#exportRow` between `#sendBtn` and `#sendProgress` because it
> would *"make feedback appear below a different button"*. A reveal failure
> rendering into `#exportError` makes feedback appear **above** a different
> button — the same defect, in the other direction, inside the panel this package
> built. Putting the message directly beneath the button that raised it is the
> rule applied rather than a new one invented.

**(a) The folder is gone, or Yoto Maker has forgotten it.**

> `Yoto Maker can’t open that folder any more — it may have been moved or deleted, or Yoto Maker may have been restarted since you saved it. Press “📁 Save the files to a folder” again to make a fresh one.`

**Planner's `"There's nothing saved to open yet."` is replaced, not ratified**,
and the reason is worth recording because the string reads fine until you ask
when it can appear. **`yet` is false in every state that can reach this message.**
`#exportActions` is `.hidden` until a run succeeds, and `#startOver` clears it
(`interactions.md` §9.3), so the button does not exist before a save. The only
ways to press it and have the server come up empty are that the folder was moved
or deleted, or that the server has restarted since — both of which mean she
*did* save, and telling her she hasn't invites her to doubt her own memory.

**One string for both**, because the recovery is identical: press save again. Two
states with one action get one sentence — the same reasoning that factored the
recovery out of §5.9's ceiling lines. The restart clause reads slightly technical
and stays: it is the difference between *"the app lost my work"* and *"the app
forgot where it put it"*, and the folder is still there.

**(b) The folder is there and Windows refused to open it.**

> `Yoto Maker couldn’t open the folder for you. It’s here:`
>
> `{full path}`

**Planner's first sentence is ratified verbatim**; the path is added, in
`.mono-value`, because a bare "couldn't open" is a dead end and the app is
holding the one thing that resolves it. This is §5.5's degraded rendering reached
by a different route — *we knew we couldn't* versus *we tried and it failed* —
and the user gets the same information either way.

**The button stays on screen after a failure of type (b).** Removing a control
the user just pressed is disorienting, and the path is now on screen, so a second
press costs her nothing. After type (a) the whole panel is stale anyway and her
next action is the save button above.

**Neither string changes as a result of the region ruling, and both were checked
against the message they can now sit beneath.** A partial save leaves
*"4 of your 5 tracks are saved…"* in `#exportDone` and *"One track couldn't be
saved: …Everything else is in the folder."* in `#exportError`; underneath the two
buttons, (b) then reads *"Yoto Maker couldn't open the folder for you. It's
here:"* and (a) reads *"Yoto Maker can't open that folder any more…"*. Both are
consistent with what is above them — (b) plainly, and (a) because it describes
something that happened **after** the save, which its own *"may have been moved
or deleted, or Yoto Maker may have been restarted"* clause already says. No
combined string is needed, and none is specified: **a combined string would be
the composition rule this ruling rejected, arriving as copy instead of markup.**

### 5.6 Partial failure — which track, and why

`#exportError`, `.msg-box err`, `role="alert"`, rendered **alongside** the
success box, not instead of it.

**One track:**

> `One track couldn’t be saved: “{title}”. {reason}`
>
> `Everything else is in the folder. The page in the folder lists what’s actually there.`

**More than one:**

> `{n} tracks couldn’t be saved:`
>
> `{numbered list of titles, each with its reason}`
>
> `Everything else is in the folder. The page in the folder lists what’s actually there.`

`{reason}` uses the app's existing plain-language file errors where they apply,
e.g. `sources/audiofile.py:41` — `We couldn’t read that file — it may be open in
another program.`

**The second paragraph is load-bearing.** It is the sentence that stops her
uploading a card with a hole in it: it tells her the instruction sheet is the
authority on what actually exists. `overview.md` §10.4 requires the sheet to be
generated from what landed, and this sentence is the readable form of that
requirement — **if the sheet stops matching the folder, this string becomes a
lie.**

**Why a red box beside a green one.** That is the honest rendering of a partial
outcome, and it is what the multi-file add already does
(`RELEASE_NOTES.md:39-46`). The success box's own count has already dropped from
`All 5` to `4 of your 5`, so the two boxes agree.

### 5.7 Total failure — nothing was saved

`#exportError` only. No success box, no buttons, no folder left behind.

> `Yoto Maker couldn’t save the files.`
>
> `{reason}`
>
> `Nothing was saved, and nothing on this card has changed. You can try again, or send it to your Yoto instead.`

`{reason}`, by cause:

| Cause | Line |
| --- | --- |
| Disk full | `This computer looks like it’s out of space.` |
| Permission denied | `Windows wouldn’t let Yoto Maker write to your Documents folder.` |
| Name/path too long | `The card name is very long, and that made the file names too long for Windows. Try a shorter name in step 2.` |
| **Every track failed individually** *(added 2026-09-05)* | `None of your {n} tracks could be saved:` followed by the same numbered list §5.6 uses, each with its own reason. |
| Anything else | `Something went wrong while writing the files.` |

**The every-track-failed row is the zero case from §5.1**, and it is the one that
needed writing down: the run did not fail at the folder, it failed at every file
in turn, so a single cause line would be a guess. It reuses §5.6's list rather
than inventing a format — the same reasons, the same numbering, in the box that
says nothing was saved instead of the box that says most of it was.

*(The realistic trigger is not exotic: an external drive unplugged, or a network
folder gone offline, between adding the audio and pressing save. Every source
path fails at once, each with the same reason.)*

**The recovery is carried in words**, which is `copy.md` §4d's established
pattern for the states the app cannot fix by itself: *"offering a control that
cannot act is the failure §7.4 already ruled against."* Two of the four causes
name an action she can actually take; the other two name the thing to tell
whoever is helping her.

**`Nothing was saved, and nothing on this card has changed.`** is the reassurance
sentence this package owes, and it is the same construction as
configuration-surface §4c's *"Nothing was changed, and you're still signed in to
Yoto."* **It is true only because a failed run removes the folder it created**
(`overview.md` §10.5). If that ever stops being true, this string must change
with it.

### 5.8 Saved again

When the folder name collided and became `(2)`, `(3)`, … the success box says so
by simply naming the folder she got:

> `🎉 All 5 tracks are saved, in a folder called “Bedtime Stories (2)” — in your Documents, under Yoto Maker.`

**No extra sentence, and no warning.** Naming the real folder is the whole
explanation; the `(2)` convention is one she already knows from copying files in
Windows. A line saying *"you already saved this card, so…"* would be
explaining a thing that has explained itself.

### 5.9 Notes — over one of Yoto's limits *(added 2026-09-05)*

`#exportNote`, `.msg-box info`, paragraphs 3–5 of the five in `overview.md`
§10.3's table. **Advisory, never blocking** — the app converts on format and only
*advises* on size, and `overview.md` §8.6 argues why that split sits where it
does.

Yoto's published limits (`support.yotoplay.com`, 2026-07-20): **100 tracks per
card · 100 MB / 60 minutes per track · 500 MB / 5 hours per card.**

**A single track is over the per-track limit** — measured after any conversion:

> `One of your tracks is bigger than Yoto allows for a single track — Yoto’s limit is 100 MB. Yoto’s website may refuse it. If it does, tell whoever set Yoto Maker up for you which one it is: {list}.`

*Plural:*

> `{n} of your tracks are bigger than Yoto allows for a single track — Yoto’s limit is 100 MB each. Yoto’s website may refuse them. If it does, tell whoever set Yoto Maker up for you which ones they are: {list}.`

**`{list}` format — Planner's shape, ratified** *(2026-09-05)*: the file's number
and title, then its size in parentheses, comma-separated.

> `09 - Chapter Nine (118 MB)`
> `09 - Chapter Nine (118 MB), 14 - Chapter Fourteen (104 MB)`

Three things it settles, each a small decision:

- **Number-and-title, not a quoted title.** It is the same list format §5.4
  already uses (`04 - The Sea, 11 - Rain`), and it is **the file name she will
  have to find in a file dialog** — which is more use to her than the track title
  alone. The two strings that name a single thing in prose (§5.3's split note,
  §5.5a) keep quoted titles, because there is no list to scan.
- **Whole MB, decimal (10⁶)** — the same reading `overview.md` §8.3 takes of
  Yoto's own figure. `118 MB`, never `118.4 MB` and never MiB; a decimal place
  adds a digit to compare and changes nothing she can act on.
- **The list moved to the end of the sentence**, so both variants finish on the
  actionable thing. *"Tell whoever set Yoto Maker up for you which one it is:
  09 - Chapter Nine (118 MB)"* **is the sentence she reads aloud on the phone** —
  which is the same use case `configuration-surface` §13.4 built its whole help
  section around. The earlier draft buried the file in the middle and ended on
  *"that track needs making smaller"*, which is advice she cannot act on.

**The card is over a card-level ceiling** — one line per ceiling exceeded, stating
the fact only:

| Ceiling | Line |
| --- | --- |
| 500 MB | `This card is {size} MB altogether, and Yoto allows 500 MB on one card.` |
| 5 hours | `This card is {duration} altogether, and Yoto allows 5 hours on one card.` |
| 100 tracks | `This card has {n} tracks, and Yoto allows 100 on one card.` |

…followed by **one** closing sentence, shown once however many of the three
fired:

> `Yoto’s website may refuse some of it. If it does, make two shorter cards instead of one.`

**Why the recovery is factored out.** Two ceilings very often fire together — at
about 192 kbps, 500 MB and 5 hours are the same card (`overview.md` §8.3) — and
repeating *"make two shorter cards"* underneath each would read as two separate
problems with two separate fixes. One fact per ceiling, one fix for all of them.

**Why *"may refuse"* and not *"will refuse"*.** These numbers are a third party's
current policy, read off a support page and not tested against an upload. The app
cannot verify them and cannot learn that they have changed. Overstating them
would produce exactly the false-positive lockout configuration-surface §13.2's
conservatism exists to prevent — and unlike the format rule, here the app is not
acting on the number, only reporting it.

**Why the per-track line has no button and a different recovery.** There is
nothing the app can do: re-encoding an MP3 to shrink it is a quality decision it
has no basis to make for her (`overview.md` §8.6). So the recovery is carried in
words and points at the person who can act — `copy.md` §4d's established pattern
for the states the app cannot fix.

**Why the figures are printed and the accepted-format list is not** (§5.4): these
have a recovery she can perform. `MP3 / M4A / AAC` does not — the app has already
done that acting on her behalf.

### 5.10 Contact with a running save is lost *(added 2026-09-05)*

`#exportError`, `.msg-box err`, `role="alert"`. **This state replaces §5.7's
three paragraphs whenever the save job had already started** — see the boundary
rule below, which is the whole point of the section.

> `Yoto Maker stopped answering while it was saving, so it can’t tell you whether it finished. Nothing on this card has changed.`
>
> `Look in your Documents, under Yoto Maker, for a folder named after this card. If there’s a page in it called “What to do next”, the save finished — that page lists what’s actually there.`
>
> `If there’s no folder, or no “What to do next” page in it, make sure Yoto Maker is still running — look for the 🎵 icon near the clock — then press “📁 Save the files to a folder” again. Nothing you already have will be written over.`

**The defect this replaces.** When a status poll failed, the panel rendered
§5.7 — head, the transport error, and *"Nothing was saved, and nothing on this
card has changed."* **Both the head and the first half of the tail are
assertions the app is in no position to make**, and they are false in the
direction that makes her act on them: told nothing happened, she presses save
again while a folder is being written. §5.7's reassurance sentence carries its
own warning about exactly this — *"it is true only because a failed run removes
the folder it created"* — and a failed run only removes it while something is
alive to do the removing. A save the app has lost contact with may be running,
may have finished, or may have died mid-write with a half-finished folder still
on disk. **The app knows which of those it is in none of these cases.**

**The exact boundary, because blurring it re-introduces the defect.** The
uncertainty begins the moment a job id exists.

| When the failure happens | What renders |
| --- | --- |
| `POST /api/export` never returned a job id | **§5.7, unchanged.** No job was started, so *"Nothing was saved"* is true. |
| A refusal — no tracks, no card name | **§3, unchanged.** |
| The job reported an error | **§5.7, unchanged.** The app was told the outcome. |
| **A status poll failed after a job id existed** | **This section.** |

**Paragraph 1 keeps the half of §5.7's tail that is still true and drops the half
that isn't.** *"Nothing on this card has changed"* is true however the save ended
— nothing on this path writes to the draft — and it answers the fear she actually
has, which is whether she must rebuild the card. Dropping *"Nothing was saved"*
is the entire correction.

**Paragraph 2 gives her a test rather than a judgement.** *"Does it look
finished?"* is not a question she can answer about a folder of audio files.
*"Is there a page called 'What to do next' in it?"* is one she can, and the
answer is reliable:

> **`What to do next.html` is written last, after every audio file and every
> picture** (`export/runner.py:247` — `say("sheet", 92, …)`, the final phase in
> §4's list). **Its presence is therefore the completeness signal, and this
> string is what makes that write order a contract rather than an accident.** If
> the sheet is ever written earlier, this paragraph becomes a lie and must change
> with it — the same standing condition §5.7's reassurance sentence carries.

It also does one thing no other string in this package has to: **she has no
buttons in this state.** No result arrived, so `#exportActions` never rendered
and `📄 What to do next` was never drawn. Naming the page in words is the only
way she reaches the sheet at all. That the words match §5.6's *"The page in the
folder lists what's actually there"* is deliberate — one page, one description of
what it is for.

**Paragraph 3 checks the app is alive before telling her to press anything.** The
likeliest reason a poll fails is that Yoto Maker is no longer running — quit from
the tray, crashed, or the machine slept — and in that state pressing save again
does nothing at all. The 🎵-near-the-clock wayfinding is lifted verbatim from the
transport string this message displaces (`app.js:26-27`) and from
`INSTALL-FOR-MOM.md:30`; she may have met it in both places, and varying it would
cost more than repeating it.

**Why she is told it is safe to press again**, rather than left to work it out:
this is the one state where she has been told to check first, so the instruction
to press anyway needs its own permission. *"Nothing you already have will be
written over"* is §5.2's invariant in her words. It is not a new promise — it is
the existing one, said out loud at the only moment she has a reason to doubt it.

**Rejected**

| Rejected | Why |
| --- | --- |
| Leave §5.7 in place | It states an outcome the app does not know, in the direction that costs her work. This is the deferral. |
| `Something went wrong while saving. Please try again.` | *"Went wrong"* is an outcome claim, and *"try again"* is the instruction that is unsafe until she has looked. |
| A silent retry that eventually shows §5.7 anyway | Retrying is right (`interactions.md` §4a) and changes nothing about what the message may claim once the retries are spent. |
| Naming the folder — `a folder called “Bedtime Stories”` | **The panel has no result, so it does not know the folder's name.** The card name is not it: the folder is sanitized and may be `(2)`. Naming it would be the JS-side reconstruction `overview.md` §11.3 forbids, arriving as a helpful-looking sentence. *"Named after this card"* is what the app can honestly say. |
| Showing the progress bar while she reads it | A bar on screen says the app is still watching. It is not — `#exportProgress` is hidden with this message (`interactions.md` §4a). |

---

## 6. `What to do next.html` — the instruction sheet, verbatim

Written into the folder and served by the app at the URL the job result carries.
**One file, one rendering, both routes** (`overview.md` §6.3).

Substitutions in `{braces}` are filled from what was actually written to disk,
never from the draft (`overview.md` §6.2).

### 6.1 Head

> # What to do next
>
> ## {card name}
>
> *{picture, if the card has one — about 180px, embedded}*
>
> `{n} tracks · {total length}`
>
> Everything for your card is in this folder. Here’s how to put it on your Yoto —
> it takes about five minutes, and there’s nothing here you can break.

*(The closing clause is lifted from `INSTALL-FOR-MOM.md:8` — "There's nothing
here you can break." She may have read it there, and repeating the reassurance in
the same words is worth more than varying it.)*

### 6.2 Step 1

> ### 1. Open Yoto’s website
>
> Go to **[my.yotoplay.com](https://my.yotoplay.com)** and sign in with your
> normal Yoto email and password — the same one you use in the Yoto app on your
> phone.
>
> Click **Make Your Own**, then start a new card.

*(`Make Your Own` is Yoto's own name for the feature and is the string she will
see on the site. It is also already in `INSTALL-FOR-MOM.md:76`.)*

### 6.3 Step 2

> ### 2. Give it this name
>
> **{card name}**
>
> It doesn’t have to match — but it’s easier if your card, your label and this
> folder all say the same thing.

### 6.4 Step 3

> ### 3. Add the audio files
>
> Add these files from this folder. **Pick them all at once** — they’re numbered
> so they stay in the right order.
>
> ```
> 01 - Chapter One.mp3
> 02 - Chapter Two.mp3
> 03 - Chapter Three.mp3
> ```
>
> If you add them one at a time, add them in number order — 01 first, then 02,
> and so on.

*(**"Pick them all at once"** is deliberately the instruction rather than an
option: it is correct whether the site orders by file name, by the order you
picked them, or by dragging them around afterwards. See `overview.md` §16.2 item 4
— this string is what makes that question non-blocking.)*

**When a track was split, this section gains one line above the file list:**

> One of your tracks was too long for a Yoto card, so it’s in more than one
> piece. That’s normal — add all the pieces and they’ll play one after the other.

**Plural** *(added 2026-09-05)*, when two or more tracks were split:

> Some of your tracks were too long for a Yoto card, so they’re each in more than
> one piece. That’s normal — add all the pieces and they’ll play one after the
> other.

*(The sheet's line names no titles and no counts, unlike §5.3's. It sits
immediately above the file list, where every part is already printed with its own
number — repeating them in prose would be the same information twice, six inches
apart.)*

**When files were saved as MP3s, this section gains one line above the file
list:**

> Some of these are MP3 copies that Yoto Maker made, because Yoto’s website is
> fussier about this than the app is. They’re the same audio.

**When a track or the card is over one of Yoto's limits (§5.9), this section
gains one line above the file list:**

> One of these is bigger than Yoto usually allows on a card. If the website
> refuses it, that’s why — the numbers are at the bottom of this page.

*(The line flags it; the numbers live once, in §6.9's troubleshooting list. A
user reading step 3 needs to know a refusal is possible and is not her fault; she
does not need three limits recited mid-procedure.)*

### 6.5 Step 4

> ### 4. Add the picture *(if you want one)*
>
> **Card picture.png**, in this folder, is the picture from your card. Add it
> wherever the website asks for a picture.

*(Omitted entirely when the card has no picture — no placeholder, no "you didn't
pick one".)*

### 6.6 The little pictures

> ### The little pictures on the Yoto screen
>
> There’s a folder here called **Track pictures**, with a small picture for each
> track — the ones that show on the Yoto player’s screen. They’re named to match
> the audio files.
>
> If Yoto’s website asks you for a picture for each track, they’re in there. If
> it doesn’t ask, you don’t need them.

**This paragraph is written to be true under both answers to `overview.md` §16.2
item 2**, and asserts nothing about what the site supports. It is the copy that
makes an unverified assumption safe rather than papered over.

### 6.7 Step 5 and 6

> ### 5. Save it on the website

> ### 6. Put it on a card
>
> Open the Yoto app on your phone, tap a blank **Make Your Own** card to link it,
> and press play. 🎶
>
> This last bit is a Yoto step — no app can do it for you, and it’s the same
> whether you upload by hand or send straight from Yoto Maker.

*(Step 6 is not optional and must never be dropped for brevity. Without it she
finishes a correct upload and has a card that does nothing —
`SETUP-YOTO-CONNECTION.md:100-104`. The wording matches
`INSTALL-FOR-MOM.md:76-77` on purpose. The second sentence pre-empts the
reasonable suspicion that this step is a penalty for not using the app's own
button.)*

### 6.8 The missing-track notice — partial runs only

Rendered **at the top of the sheet, above the card name**, in the sheet's own
warning treatment. This is the requirement `overview.md` §10.4 point 3 and
`copy.md` §5.6 both depend on.

> ⚠️ **One of your tracks isn’t here.** Yoto Maker couldn’t save
> **“{title}”**, so it isn’t in this folder and isn’t in the list below. If you
> want it on the card, go back to Yoto Maker and try again.

**Plural variant:** `{n} of your tracks aren’t here.` with the titles listed.

### 6.9 Footer

> ### If something doesn’t work
>
> - **The website won’t take one of the files.** Tell whoever set Yoto Maker up
>   for you which file it was — that’s the useful thing to say.
> - **The website says something is too big, or won’t take them all.** Yoto
>   allows **100 MB and an hour** for any one track, and **500 MB, five hours and
>   100 tracks** for a whole card. If you’ve gone over, make two shorter cards
>   instead of one.
> - **The tracks came out in the wrong order.** Remove them and add them again,
>   picking them all at once, or drag them into number order on the website.
> - **You can’t find the folder.** It’s in your **Documents**, in a folder called
>   **Yoto Maker**.

*(The size bullet is shown **always**, not conditionally. It is the one place the
limits are written down, it costs three lines in a footer nobody reads until
something goes wrong, and it is the only bullet here whose answer she cannot get
from the app — the app never sees the website's refusal.)*
>
> ---
>
> Made by Yoto Maker {version} on {date}. Not affiliated with Yoto.

*(`{date}` in long form — `5 September 2026` — never a numeric format that means
different things in different countries.)*

*(`Not affiliated with Yoto.` matches the About modal, `index.html:453`. The page
carries Yoto's name and links to Yoto's site; it should say the same thing the
app already says.)*

---

## 7. The Settings row — if `overview.md` §14.2 ships

One row appended to setting 3, *"If you need to ask for help"*
(`index.html:397-441`), after the existing `Where Yoto Maker keeps its files`.

| Label (`.tiny`) | Value |
| --- | --- |
| `Where saved files go` | *(rendered — e.g.* `C:\Users\mark\Documents\Yoto Maker` *,* `.mono-value` *)* |

**Two rows that both look like folders, and they are different folders.** The
existing row is where the app keeps *its* files; this one is where it puts
*hers*. The labels already say which is which — *"Yoto Maker keeps"* against
*"saved files go"* — and lengthening either to disambiguate would make both worse
to read aloud on the phone, which is the only thing this section is for.

**Rendered from the server**, alongside `config.data_dir`, and never constructed
in JS — configuration-surface §13.4's rule for the redirect URL, for the same
reason: the one moment the value matters is the moment a guess would be wrong.

---

## 8. Strings explicitly unchanged

`index.html` steps 1, 2 and 4 in full; step 3's `h2` and `.hint`; `#connectBtn`;
`#sendBtn`; `#sendDone`; **every message rendered into `#sendError` except the
two in §10** *(§9 is specified but not shipped — see §9's banner)*; `#connectWarn`
and all of configuration-surface `copy.md` §4d; `#advRow`/`#advToggle` in both
variants; the header pill; the footer; the About modal; every string in the
settings view except the one row in §7.

This feature appends. It **edits** exactly one shipped string (§1), and that
string is edited because the feature makes it false. It **specifies** one string
for the send path (§9), in a state that previously had no send-path string at
all, and **does not ship it**.

*Amended 2026-09-05.* This section previously listed `#sendError` and *"every
message rendered into it"* as untouched. §9 makes that false and the list is
corrected rather than quietly outgrown — which is the defect §1 exists to fix,
applied to this file. *Ruling appended 2026-09-05: §9 did not ship, so the
original wording is restored above — the correction stands as the record of what
§9 will require when it does.*

*Amended again 2026-09-06, and this time the exception ships.* §10 rules two
strings rendered into `#sendError` — the per-track 413 and the generic one —
so the blanket claim is now false for a second and different reason, and the
carve-out is written into the list rather than left to a reader who finds §10
later. **The two amendments are not the same event and neither supersedes the
other:** §9 is a *dropped-poll* message, still written and still unshipped; §10
is a *size refusal*, ruled and shipping. They touch the same region and nothing
else in common. **The strings §10 changes do not originate with this feature** —
they ship from queue item 20 — and they are ratified here because one of them
quotes this package's button label and depends on this package's placement
(§10.3). If `📁 Save the files to a folder` is ever relabelled, §10.1's string
is the thing that must be found, and this is where a relabeller will look.

---

## 9. The one send-path string this feature adds *(added 2026-09-05)*

> **NOT SHIPPED. Written, ruled out of this PR, and kept here as the follow-up.**
> *(Maintainer's ruling, 2026-09-05 — §9.1's stated fallback, taken.)* The send
> path does not opt into the retry: verifying one needs a live authenticated
> send against a real Yoto account, which is the thing this feature exists to
> avoid needing, and it was not verifiable on the night. `#sendError` keeps
> today's generic transport line and **nothing on the send path changes**.
> §9.1 already names what that gives up — the duplicate-card protection — and it
> is given up knowingly. Everything below stands as written, for the pass that
> ships it.
>
> Worth recording that this is §9.1's *"The fallback, stated so it survives being
> rejected"* paragraph working exactly as designed: the document anticipated its
> own rejection, and the anticipation is what made the ruling cheap.

`#sendError`, `.msg-box err`. Rendered when a status poll fails after
`POST /api/send` has returned a job id — §5.10's boundary table, on the other
path.

> `Yoto Maker stopped answering while it was sending, so it can’t tell you whether your card went through. Nothing on this card has changed.`
>
> `Open the Yoto app on your phone and look for your card. If it’s there, it worked.`
>
> `If it isn’t there, make sure Yoto Maker is still running — look for the 🎵 icon near the clock — then press “🚀 Send to Yoto” again. Press it just once, so you don’t end up with two copies of the same card.`

### 9.1 Why the send path is in this package at all

The honest fix for §5.10 is retry logic in `pollJob` (`app.js:81-89`), and
`pollJob` has **four** call sites — the self-update, the YouTube add, the send
and the save.

**But sharing the helper does not by itself drag the send path in, and it should
not be claimed that it does.** The retry has to be **opt-in per call site**
regardless, because of the self-update: `doUpdate()` (`app.js:167-171`) *catches
every poll failure and reports success*, since the server exits mid-restart and
the last poll failing is the expected end of the operation. Retrying there would
freeze a bar for the length of the retry window before showing a message that was
already correct. **The same transport event means different things on different
paths, so the retry belongs to the caller that means *"I don't know"*, not to the
helper.** Once that is true, `saveToFolder()` could opt in alone.

So including the send path is a **choice**, and it is made for three reasons:

1. **The send path's current instruction is the more dangerous of the two.**
   Today a dropped send poll shows the generic transport line, which ends
   *"…then try again."* Pressing 🚀 Send to Yoto again while the first send is
   still uploading puts **a second card in her Yoto account** — a thing she must
   then find and delete on a website this app does not control. The save path's
   equivalent mistake produces `Bedtime Stories (2)` in her Documents, which
   §5.8 already treats as needing no explanation. Fixing the milder one and
   leaving the sharper one is backwards.
2. **The generic line is not wrong, it is silent about the outcome** — and that
   is what makes it dangerous here. It is the right string for a failed
   *request*; it becomes the wrong string the moment there is a job behind it.
3. **A shared helper whose capability one long-running caller declines is a
   thing someone later "fixes" without knowing why.** If the send path opts out,
   that opt-out needs a comment nobody will trust as much as they trust a
   symmetry.

**The fallback, stated so it survives being rejected.** If the maintainer would
rather keep the send path out of this PR's diff, the cost is one line: the send
path does not opt in, keeps today's generic transport line, and §8's original
wording stands. **What is given up is the duplicate-card protection**, and it is
given up on the path where the duplicate is hardest to undo. That is the trade,
and it is the maintainer's to take.

### 9.2 Why this is not one string shared with §5.10

§5.5a established *"one string for both, because the recovery is identical"*.
**That principle does not extend here, and the reason it does not is the test the
principle itself states: the recoveries are not identical.**

| | Save | Send |
| --- | --- | --- |
| Where she looks to find out | Her Documents, under Yoto Maker | The Yoto app on her phone |
| What acting wrongly costs | A second folder, `(2)`, which §5.8 says needs no explanation | **A second card in her Yoto account** |
| So the second and third paragraphs | differ | differ |

What governs instead is **§3's rule**, which this package already applies to the
two refusals: *"Two sentences that differ by two words is not duplication to be
refactored away — it is how the user learns that the two buttons are peers doing
the same job by different means."* The two messages here are built to that
pattern deliberately: the same three-paragraph shape, the same opening clause,
the same 🎵 wayfinding, the same closing structure — differing only where the
world differs.

**The first sentence is nearly but not exactly shared, and the difference is
load-bearing.** *"while it was saving"* / *"while it was sending"* and
*"whether it finished"* / *"whether your card went through"* are what tell her
which of the two she is reading — and **both boxes can be on screen at once**: a
failed send leaves `#sendError` populated, and `#exportRow` sits directly beneath
it by design (`overview.md` §4.3 point 2). A single shared sentence would put the
same words in two red boxes fourteen pixels apart.

### 9.3 What is deliberately *not* changed on the send path

- **`#sendError` gains no `role` and no `tabindex`.** It has neither today
  (`index.html:195`), so this message is announced no worse than every other send
  failure — but it is announced no *better* either, and that is a pre-existing
  gap this package is standing next to rather than closing. Making `#sendError` a
  live region changes announcement behaviour for every shipped send failure and
  deserves its own pass and its own UAT. Recorded, not fixed.
- **`#sendDone`, `#sendBtn`, `#sendProgress` and the send flow's control logic.**
  Unchanged.
- **The YouTube add path (`app.js:1251`) does not opt in.** Its dropped-poll
  message is the generic transport line, which asserts nothing false, and the
  outcome it leaves uncertain is visible on the same screen — the track list she
  is already looking at. Widening the diff to a third shipped path to replace an
  honest-but-unhelpful string is not justified here. Worth doing later; not
  worth doing now.

---

## 10. When Yoto refuses something for being too big *(added 2026-09-06)*

**This section ships.** Unlike §9, which is written and deliberately unshipped,
§10 rules on two strings that are in flight on
[queue item 20](../../BUILDER_QUEUE.md) (PR #27) and blocked on that ruling.

`#sendError`, `.msg-box err`. Both strings below are produced server-side, in
`yoto_maker/yoto/client.py`'s `_friendly_http` 413 branch, and reach the box as
`e.message` through `showError()` — **one text node, so one paragraph each.**
That is a rendering fact, not a preference: `showError()` sets `textContent`
(`app.js:55`), and a multi-paragraph message here would mean changing how the
send path carries errors, which is not a copy change.

### 10.1 A single track was refused

Raised by the audio PUT — the only caller that knows *which* limit a 413 can
mean.

**The track has a title** — the shipped case:

> `Yoto wouldn’t take “{title}” — it’s bigger than Yoto allows for a single track. No card was made in your Yoto account. There’s another way to finish this card: press “📁 Save the files to a folder” below.`

**The track has no title** — reachable only through a direct call:

> `Yoto wouldn’t take one of your tracks — it’s bigger than Yoto allows for a single track. No card was made in your Yoto account. There’s another way to finish this card: press “📁 Save the files to a folder” below.`

The three sentences do three jobs, in the order she needs them: **which track**,
**what it cost her**, **what to do**. §5.9's ordering rule applied — *finish on
the actionable thing.*

**Where it borrows.** *"bigger than Yoto allows for a single track"* is §5.9's
ratified clause, **verbatim and unshortened.** The plan that authored the blocked
string shortened it to *"one track"* to avoid repeating a word; naming the track
in quotes removes the repetition without touching a ratified phrase, and the two
paths now say the same words about the same limit — §3's peer-strings principle,
not duplication to be refactored away.

**`No card was made in your Yoto account.` is the reassurance this package
owes**, and it is the narrowest true form of it. `create_card()` uploads every
track first and calls `_create_content()` only after the loop
(`client.py:166-215`), so a refusal at track 3 of 5 leaves **no card**. It
deliberately does *not* say *"nothing was added to your Yoto account"*: tracks 1
and 2 reached Yoto's staging, and a custom icon for them may have been uploaded
(`client.py:198-200`). A sentence a determined reader could falsify is the kind
of small dishonesty §5.1 refused the `🎉` for.

> **Standing condition.** This sentence is true only while the card is created
> after every track uploads. If the send path is ever restructured to create the
> card first, or incrementally, **this sentence must change with it** — the same
> obligation §5.7's reassurance carries.

**The rejected first draft is the string that was blocked**, and both of its
defects are worth keeping written down, because each reads as a detail and
neither is:

| Rejected | Why |
| --- | --- |
| `…Yoto’s limit is 100 MB, and this one is {n} MB.` | §10.2 |
| `…If you have a shorter recording of it, try that instead…` | §10.3 |

### 10.2 No number is printed, and that is the ruling

**Neither Yoto's ceiling nor the file's size appears.** Three independent
reasons, any one of which is sufficient:

1. **The sentence refuted itself.** Whole MB at 10⁶ (§5.9's ratified rule) means
   every size in 100,000,001–100,500,000 renders *"Yoto's limit is 100 MB, and
   this one is 100 MB"* — immediately after asserting the file is bigger than the
   limit, and a file just over a ceiling is the **modal** refusal. §5.9's rule is
   safe there because it prints the size in a **list parenthetical**, several
   words away from the ceiling. Borrowing it into a single comparative clause is
   a construction §5.9 never ratified, and the clause is where it breaks.
2. **§5.9 hedges, and this string cannot.** *"Yoto's website **may** refuse it"*
   is what makes naming an unverified number honest there. Here Yoto has already
   refused, so the hedge would be false in the other direction — and naming the
   number **without** the hedge is weaker evidence-handling than §5.9 itself
   permits. The blocked string borrowed §5.9's number and left §5.9's hedge
   behind; the hedge was the load-bearing half.
3. **She cannot act on it.** §5.4's ratified test is that figures are printed
   *"because those have a recovery she can perform."* On the advisory path
   (§5.9) *100 MB* is that recovery — it is the number she reads down the phone.
   Here the recovery is a button on the same screen, and the number does no work.

**What survives the probe, and this is the point.** The 100 MB figure is Yoto's
published documentation, not observed behaviour, and `overview.md` §8.6's
provenance discipline applies. The live probe that would settle it
([item 20's plan §8](../../superpowers/plans/2026-09-05-per-track-size-limit.md))
**has not been run.** The refusal itself *is* observed — this string only ever
renders after Yoto has returned a 413 — so *"Yoto wouldn't take it"* and *"bigger
than Yoto allows for a single track"* stand whatever the probe finds. **Only the
number could have been falsified, and it is the one thing not printed.** The
probe can now change item 21 without touching a shipped string.

**Explicitly rejected fixes**, so none is re-proposed later as an improvement:

| Rejected | Why |
| --- | --- |
| Round up rather than to nearest | Buys arithmetic safety by overstating her file by up to 1 MB. A rounding direction chosen to make a sentence work is a number the app no longer means. |
| One decimal place | Overturns §5.9's whole-MB rule for one sentence, and *"100.3 MB against 100 MB"* is still a comparison she cannot act on. |
| Compare the bytes, print the number only when it is clear | A byte comparison in `client.py` is what plan §2 forbids and calls the design. The send path advises; it does not measure. |
| Print her size but not the ceiling | Removes the contradiction and leaves a bare figure with nothing to compare it against. |

### 10.3 The recovery is the save button, and this is the part that needed a ruling

**The blocked string's recovery named the wrong variable.** *"If you have a
shorter recording of it"* aims at **duration**, and `server/app.py:263` already
splits every source at 50 minutes unconditionally, so duration cannot be the
cause of a size refusal. The advice could not work for anybody.

**The remedy that does work is on the same screen.** The population that reaches
this message is a local `.wav`, `.flac`, `.ogg`, `.opus` or `.mp4` — the send
path copies those untouched, and CD-quality stereo WAV crosses 100 MB at about
9½ minutes. `📁 Save the files to a folder` converts every one of them to
192 kbps MP3, **~72 MB at the same 50-minute bound** (`export/rules.py:26-32`).
For the modal case, the other button is solved-by-construction.

**Why this is a Designer ruling and not a wording tweak.** §5.7 ratifies the
cross-path pointer in one direction only — *"You can try again, or send it to
your Yoto instead."* The mirror image had **no ratified string in either
package**, and re-framing a send failure as *use the other button* changes what
the two controls mean to each other.

**Adjacency was already ratified; the words are what was missing.**
`mockups/step-3.md` §3 has drawn this exact state since 2026-09-05 — a red
`#sendError` with `📁 Save the files to a folder` directly beneath it — and
`overview.md` §4.3 point 2 chose `#exportRow`'s position for that property;
`index.html:219-220` states it in the markup. **But adjacency only puts the
button in her eyeline; it does not tell her it helps.** Nothing about a button
labelled *save the files to a folder* suggests it is the answer to *too big*.
The pointer is what turns a nearby control into a recovery, and without it the
box is a dead end sitting fourteen pixels above its own answer.

**Why this does not contradict §1.** §1 refused to advertise saving inside
`#connectRow` — *"two intents in one sentence inside a box whose job is the first
one… it demotes connecting for the ~200 visits where connecting is correct."*
That rule is scoped to the **pre-press** box on the everyday path. Here there is
no competing first answer left: she is connected, the send has already failed,
and pressing it again cannot succeed, because the file will be the same size.
**§1's cost does not exist in this state**, so §1's rule does not reach it.

**Why the pointer promises nothing, and why it is not conditional.** A file
*already* in the copy-as-is set — `overview.md` §8.6's *"50-minute MP3 at
320 kbps is ~120 MB"* — is copied untouched by the save path
(`export/rules.py:46-47`: *"it never returns True because a file is large"*), so
saving would not shrink it. The string therefore says *"There's another way to
finish this card"* and **never says the files will be smaller.**

> **The pointer needs no file-type condition, because the destination already
> carries the warning.** A user in that minority presses the button, the save
> succeeds, and §5.9's advisory fires on the other side — *"Yoto's website may
> refuse it… tell whoever set Yoto Maker up for you which one it is"* — naming
> her exact file. The two paths compose: the send path points, and the save path
> tells the truth about the specific file. Conditioning the pointer on an
> extension would put a rule in `client.py` that `export/rules.py` already owns,
> and would guess in the one place the app does not have to.

**Why there is no *"otherwise tell whoever set Yoto Maker up for you"* here.**
§5.9 needs that fallback because it has no other route to offer. This string has
one, and the fallback is delivered by the screen that knows whether it is needed
(the paragraph above). One error box, one action — which is how every other
`_friendly_http` branch reads.

**Rejected phrasings**

| Rejected | Why |
| --- | --- |
| `…press “📁 Save the files to a folder” below, and put the files on Yoto’s website yourself.` | The button's own caption says exactly that, twelve pixels lower (§2). configuration-surface §6.1's split — short label, caption disambiguates — is not re-litigated inside an error box. |
| `…which saves smaller copies.` | False for the copy-as-is set (`overview.md` §8.6). A promise the app cannot keep on the path it is sending her down. |
| `…try “📁 Save the files to a folder” instead.` | *instead* was rejected on the button itself (§2) for going stale by state; in a sentence that has just described a failure it also reads as a shrug. |
| Say nothing, and let the adjacency do the pointing | The finding this section exists for. See above. |

### 10.4 The other arm of the same branch — a 413 from anywhere else

`_friendly_http`'s 413 branch is one `if` with two outcomes, and **ruling one arm
while orphaning the other is how drift starts.** The default arm — every 413
that is not the track PUT — is:

> `Yoto wouldn’t take that — it was too big to send. Tell whoever set Yoto Maker up for you.`

**Naming no ceiling is correct and stays.** The helper is shared by six call
sites; the shipped string named the card-level 5-hour ceiling for all of them,
including the per-track PUT where that ceiling is certainly the wrong thing to
say. A sentence that names no limit is the honest reading of *"we cannot tell
which one it was."*

**The second sentence is added, and closes the app's only dead-end error.** Every
other branch in this family ends in something she can do — reconnect, try again,
check the connection. Without it, this is the one red box in Yoto Maker that
offers nothing at all. configuration-surface `copy.md` §4d's *"no button, and the
recovery is carried in words instead"* is the ratified pattern for a state the
app cannot fix, and the phrasing is the one §5.9 already ships (`app.js:2267`).

**No retry hedge**, deliberately. *"If it keeps happening"* invites a press that
will fail identically — the realistic generic 413 is a card body that is too
large, and it is the same size next time.

**`{doing}` is deliberately not interpolated**, unlike the 5xx and timeout
branches. Two of the six call sites are reads (`listing your cards`, `reading the
card`), and *"Yoto wouldn't take that while listing your cards"* is a sentence
about nothing. This branch's job is to say *we cannot tell you which limit — here
is who can.*

> **This string's real home does not exist yet, and that is recorded rather than
> quietly assumed.** `_friendly_http`'s five sentences — the 401/403, the 413,
> the 5xx, the timeout and the fallback — are shipped user-facing copy owned by
> **no** handoff package, and this one is reached from the repair path as well as
> the send path. It is ruled here because it is the other half of the branch
> §10.1 changes. Adopting that family into a package of its own is worth a queue
> row and is **not** done here.

### 10.5 What §10 deliberately does not do

- **No new region and no new markup.** Both strings render into `#sendError`,
  which is the send button's own feedback region. `interactions.md` §4b carries
  the contract and the reason.
- **`#exportRow` is not touched** — not highlighted, not scrolled to, not
  focused, not moved, and the button gains no state. The string points; the
  layout already delivers. `interactions.md` §1.1's *"`#exportRow` is never
  touched by `renderStatus()`"* stands unamended.
- **`#sendError` still gains no `role` and no `tabindex`.** §9.3 declined it and
  the decline stands — making it a live region changes announcement behaviour
  for every shipped send failure. **The cost is higher than when §9.3 wrote it
  down**: a pointer that is never announced does not point, for a screen-reader
  user. Recorded against `interactions.md` §11 item 3; not fixed in this pass.
- **Nothing is said before the send.** Telling her a track is over a limit
  *before* she presses 🚀 Send to Yoto is queue item 21, which is blocked on the
  live probe and may close unshipped.
- **The 100 MB figure keeps its provenance comment in the code.** `_track_too_big`
  no longer prints the number, but the constant's evidence tier still governs
  item 21, and deleting the note would lose the reason this string prints no
  figure at all.
