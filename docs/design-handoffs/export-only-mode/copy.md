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
saying what. Both render there, `.msg-box err`, `role="alert"`.

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
> It doesn’t have to match — but it’s what’s on your printed label, so it’s
> easier if it does.

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
`#sendBtn`; `#sendError`, `#sendDone` and every message rendered into them;
`#connectWarn` and all of `copy.md` §4d; `#advRow`/`#advToggle` in both variants;
the header pill; the footer; the About modal; every string in the settings view
except the one row in §7.

This feature appends. It edits exactly one shipped string (§1), and that string
is edited because the feature makes it false.
