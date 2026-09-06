# Save-to-a-folder mode — design spec

**Status:** **Approved 2026-09-05. Shipped 2026-09-06** as BUILDER_QUEUE item 19,
[PR #24](https://github.com/mmackelprang/yoto-maker/pull/24) (`7574d0d`), in
v0.1.13 (plan: `docs/superpowers/plans/2026-09-05-export-only-mode.md`).
*(This line read "Not yet shipped" until 2026-09-06. Corrected when §10 of
`copy.md` was added, because that section's whole argument is that the button
this package built is **already on the screen** when a send fails.)*
**Date:** 2026-09-05, amended 2026-09-06
**Relationship to prior handoffs:** **extends** [`configuration-surface/`](../configuration-surface/).
Deviates from nothing.

Specifically, it inherits and re-uses:

- §3's placement decision — no tab strip, no fifth step, no modal. Nothing here
  moves toward any of them (§4.4).
- §12.4's *follow-the-symptom* placement rule for step 3, and §12.4's structural
  ordering (`#advRow` stays last). §4.3.
- §13.5's *"the button stays enabled; pressing it is the fastest path to the
  explanation"* rule. §10.1.
- §13.6's *"recovery is never a dead end"* guard rail. §10.5.
- §6.1's split between a **short scannable button** and a **description that
  disambiguates**. §4.5.
- copy.md §4d's *"no button, and the recovery is carried in words instead"*
  pattern, for the states the app cannot fix. §10.5.
- tokens.md §1's refusal to add a `.msg-box.warn` variant. §8.5.
- §13.2's split between a **hard rule that acts** and a **soft rule that
  advises**, applied here to format (acts) versus size (advises). §8.6.

**It introduces no new CSS and no new tokens.** There is no `tokens.md` in this
package, and that absence is deliberate — §13 of the configuration surface calls
exactly that *"the strongest available evidence this extension fits the primitive
rather than straining it."* Every state below is built from `.btn`, `.tiny`,
`.progress`, `.msg-box` (`err` / `ok` / `info`), `.done-actions`, `.mono-value`
and `.hidden`, all shipped.

---

## 1. What this is

A second way to get a finished card out of Yoto Maker: instead of sending it to
Yoto over the connection, the app **writes the finished files to a folder on this
computer**, and the user adds them by hand on Yoto's own website
(`my.yotoplay.com` → *Make Your Own*).

It is a **mode the user chooses, one card at a time.** It is not a stage of the
send pipeline, not a replacement for it, and not something that happens
automatically. The existing signed-in path is untouched — §13 enumerates exactly
what does and does not change on it.

### 1.1 Why it exists

Yoto transcodes every upload server-side. `format` is the one field Yoto
**preserves from what the client POSTs**, and `yoto_maker/yoto/client.py:174-187`
silently falls back to a *local* probe when the transcode poll returns nothing
usable — so a card can claim `mp3` while Yoto is serving something else. That
mismatch is the leading suspect for a physical player's offline download never
completing (`SESSION_STATE.md:37-45`, `docs/RELEASE_NOTES.md:12-36`).

> **What "something else" is, stated as precisely as the evidence allows.** In
> July 2026 this repo captured `transcodedInfo: {"codec":"opus","format":"opus"}`
> from the live API — **direct observation, and the strongest evidence there is.**
> But Yoto does **not** publicly document that MYO uploads become Ogg Opus; they
> document only that transcoding happens. A support article since removed
> (Wayback snapshot 2025-12-07, content ~Nov 2025) described an Opus migration
> and said explicitly that it applied *"only to certain Yoto titles, and not your
> Make Your Own playlists."*
>
> The repo's capture is eight months newer than that article and is observation
> rather than description, so the article reads as **stale**, not as a
> contradiction. **The conclusion is unchanged and the feature's rationale is
> unaffected** — the defect is the *mismatch*, and a mismatch does not care which
> codec is on the other side.
>
> It is written down this way because the Opus claim is load-bearing in one other
> place (§8.5 reason 4), and a reader who later finds the removed article should
> meet this paragraph rather than conclude the spec was built on a mistake. What
> is certain: Yoto transcodes, the app does not always learn what to, and it
> writes its local guess anyway. That is enough.

**Uploading through the website removes the app's authorship of that field
entirely.** That is the point of the feature, and it is worth stating plainly
because it changes what "success" means here: this mode is not a convenience, it
is a path whose correctness does not depend on the app getting a metadata field
right.

A second, independent benefit falls out of it and is worth just as much: **this
mode needs no sign-in at all.** A user who has never connected — or whose
connection is broken, or whose Client ID is bad and has hard-blocked sign-in
(configuration-surface §13.5) — can still finish a card. Today those users are
stopped dead at step 3.

---

## 2. Who uses it, and when

Three users, in descending order of how much the design owes them.

**(a) The user whose send just failed.** She is at the bottom of step 3 looking
at a red box. She needs a way forward *from where she is standing*. This is the
same person configuration-surface §12.4 designed `#advRow`'s placement for, and
the answer is the same one: put the alternative directly beneath the symptom.

**(b) The user who has never signed in, and isn't going to.** Either she can't
(the connection is broken in a way Settings can't repair) or she was told not to
bother. Step 3 currently presents her with a wall: an info box saying she'll
"need to connect first" and a **disabled** `🚀 Send to Yoto`
(`app.js:288` — `$("#sendBtn").disabled = !connected;`). Right now that wall is
the end of the road. §4.6 makes it not be.

**(c) Mark, deliberately choosing the hand-upload path** because he does not yet
trust what the app writes into `format`. He knows exactly what he wants and will
find any control that exists.

**The constraint that governs all of them** is the one configuration-surface §2
established and this package inherits without weakening: *the visits where she is
just making a card must not get heavier.* The ledger for this feature is
**one `.btn` and one `.tiny` paragraph** added to step 3 — §13's ledger keeps the
accounting.

---

## 3. The word "export" never reaches the user

This package is named `export-only-mode` and the code identifiers below are
`#export*`. **No user-visible string in this feature contains the word "export",
"folder path", "directory", "transcode", "codec", or "format".**

`../README.md` bans a specific vocabulary and permits exactly one exception
("Client ID"). This adds no exception. The user-facing verb is **save**, the
user-facing noun is **files**, and the destination is **a folder**. Those are the
words a person says out loud, and — per configuration-surface §12.2's lesson —
they are the words the user is holding when she goes looking for this.

`copy.md` is the authority on every string. A string that does not appear there
is a Polisher finding.

---

## 4. Placement decision

> **Decision: one `.btn` plus one `.tiny` caption inside step 3, always
> rendered, positioned after `#connectWarn` and before `#advRow`. No new step,
> no tab strip, no mode switch, no Settings toggle.**

### 4.1 What was rejected, and why

**A fifth step — rejected, for configuration-surface §3.1's exact reason.** The
numbered sequence `1 2 3 4` is a promise about completion, taught verbatim in
`docs/INSTALL-FOR-MOM.md:44` (*"You'll see **four numbered steps**"*). A `5` that
most users must not do breaks that promise on every visit and makes the printed
guide wrong. Nothing about this feature is strong enough to justify that, and the
argument has already been made and accepted once.

**A choice control at the top of step 3 (`Send it` | `Save the files`) —
rejected.** Two reasons, and the first is the same one that killed the top-level
tab strip.

1. **It taxes the everyday path with a decision.** A user who has never heard of
   this feature would have to resolve a navigation choice before reaching the big
   button she came for. That cost is paid on every visit to serve a minority
   path.
2. **It overloads `.tab` at a third scope.** `.tab` today means "pick which kind
   of picture you want" — a within-step, instantly reversible choice among peers
   (`index.html:134-139`). configuration-surface §3.1 spent real effort keeping
   `.tab` meaning exactly one thing. A pill strip that swaps how the card is
   delivered is not that, and giving it its own visual treatment would forfeit
   the consistency that motivated reusing `.tab` in the first place.

**A `— or —` divider above the button (the `.or` class from step 1) —
rejected, narrowly.** It is tempting: step 1 already uses `— or —` to separate
two peer ways of doing the same thing (`index.html:64`), and this is
structurally the same situation. It is rejected because it costs ~40px on every
visit **and** because it asserts peerhood. Sending is the happy path; saving is
the alternative. The visual hierarchy of `.btn.primary.big` above a plain `.btn`
already says that, for free, and says it more accurately than a divider would.

**A persistent "always save to a folder" preference in Settings — rejected for
this PR, and recorded so it is not reinvented.** See §14.1. It is a coherent
future setting and the `.setting` primitive would express it without strain; it
is simply not what makes this feature work, and the brief scoped Settings out.

**A folder picker ("let her choose where") — rejected, and it is not
implementable as drawn.** The browser cannot hand the server a directory path: a
`<input type="file" webkitdirectory>` yields file contents, not a location, and
the File System Access API yields an opaque handle to the *page*, not a path the
Python process could write to. The app would need a native dialog it does not
have and has never had (§12.5). The design instead picks one predictable place
(§5.1) and shows the user exactly where it went.

### 4.2 Why step 3 is the right home, even though it is titled "Send it to your Yoto"

The step's **goal** is getting the card onto her Yoto. Sending is one mechanism;
uploading it herself is another. The title names the goal and stays true, so it
does not change — which also means `INSTALL-FOR-MOM.md` and
`SETUP-YOTO-CONNECTION.md` keep their step numbering and their words.

What *does* become false is one sentence inside step 3, and §4.6 fixes it.

### 4.3 Exact position, and why it is not next to `#sendBtn`

Step 3's children, after this feature:

```
  h2 "3 Send it to your Yoto"
  p.hint                            unchanged
  #connectRow                       unchanged in structure; ONE string edited (§4.6)
  #sendBtn                          unchanged
  #sendProgress                     unchanged
  #sendError                        unchanged (copy.md §9 designed, NOT shipped)
  #sendDone                         unchanged
  #connectWarn                      unchanged
  ── new ───────────────────────────────────────────────
  #exportRow          .btn + .tiny caption   ← the only weight added
  #exportProgress     .progress             hidden until pressed
  #exportError        .msg-box err          hidden
  #exportDone         .msg-box ok           hidden
  #exportNote         .msg-box info         hidden
  #exportActions      .done-actions         hidden
  #exportOpenError    .msg-box err          hidden   ← the REVEAL button's own
                                                       feedback region
  ── end ───────────────────────────────────────────────
  #advRow                           unchanged, and STILL LAST
```

*(Both 2026-09-05 amendments. `#exportOpenError` is the only structural change
since approval: it adds no CSS, no token and no tab stop, and it exists because
a reveal failure sharing `#exportError` destroyed the partial-save notice —
[`interactions.md`](interactions.md) §4.4 carries the ruling, and **point 1
immediately below is the rule that decided its placement.** `#sendError` gains
one message and no markup change; [`copy.md`](copy.md) §9.1 carries why the send
path is in this package at all, and the fallback if it should not be.)*

Three things about that position are load-bearing.

1. **Not between `#sendBtn` and `#sendProgress`.** Putting it there would insert
   an unrelated control between the primary button and its own progress bar and
   error box — so pressing `🚀 Send to Yoto` would make feedback appear *below a
   different button*. Action→feedback adjacency on the everyday path is worth
   more than proximity for the alternative.

2. **Directly beneath `#sendError` when a send fails.** All of
   `#sendProgress` / `#sendError` / `#sendDone` are `.hidden` in the resting
   state, so in the everyday view `#exportRow` renders immediately under
   `#sendBtn` anyway — and on a failure it renders immediately under the red box.
   This is the same property configuration-surface §12.4 chose `#advRow`'s
   position for, and it is the whole reason that position was chosen there.

3. **Beneath `#connectWarn`, deliberately.** `#connectWarn` is the hard sign-in
   block for a malformed Client ID (configuration-surface §13.5). In that state
   the user has been told, in a red box, that Yoto Maker cannot sign in. The very
   next thing on screen is now a live button that does not need a sign-in. That
   is the strongest single placement argument in this spec and it costs nothing —
   it falls out of appending rather than inserting.

4. **`#advRow` stays last.** `interactions.md` §1.4 of the configuration surface
   states this as a rule and gives the reason (its position must never move as
   transient boxes come and go). Nothing here changes it.

### 4.4 What this is *not* a step toward

Recorded because configuration-surface §12.7 recorded the equivalent, and for the
same reason: so a future pass does not read this as precedent.

This adds **one button and one `.tiny` paragraph to the bottom of the third card**.
Nothing appears above step 1. Nothing intercepts steps 1, 2 or 4. No persistent
chrome is added anywhere. `.tab` still means one thing. The four-step promise is
intact.

### 4.5 The label carries the action; the caption carries the consequence

configuration-surface §6.1 established this split and it applies unchanged: a
button label that tries to carry both intents is unscannable, so the button stays
short and the line beneath it does the disambiguating.

| Slot | String |
| --- | --- |
| Button | `📁 Save the files to a folder` |
| Caption (`.tiny`) | `You’ll put them on Yoto’s website yourself. You don’t need to be signed in for this.` |

Full rationale for both, and every rejected alternative, in [`copy.md` §2](copy.md).

**On the `📁` glyph.** configuration-surface §12.6 rejected a gear on the ground
that *"a gear is not a picture of anything — it is a learned convention"*. A
folder passes that test: it is a **picture of the thing this button produces**.
The reuse of `📁` from step 1's `📁 Choose audio files` is accepted rather than
overlooked — in both places the glyph means *files on this computer*, which is
consistent rather than colliding, and the paired `📂` on the post-run
`📂 Open the folder` button (open variant, open action) completes the vocabulary.

### 4.6 One existing string becomes false, and must be corrected

`index.html:173`, inside `#connectRow`:

> `You'll need to connect your Yoto account first.`

Once saving exists, that is not true: connecting is a prerequisite for *sending
from the app*, not for finishing a card. Leaving it would be the same class of
defect configuration-surface §12.3 recorded — a string that no longer matches
what the screen can do, sitting in front of the exact user who needs the other
answer.

**The correction is a scope narrowing, not an advertisement:**

> `To send cards straight to your Yoto, connect your account first.`

It does **not** mention saving. Advertising the alternative inside the connect
box would bury the connect intent, which is still the right first answer for most
people. The export row's own caption twelve pixels below already says
*"You don't need to be signed in for this."* — that is where the alternative
belongs, and it is the second half of the same visual scan.

Verbatim string and rejected variants: [`copy.md` §1](copy.md).

### 4.7 The disabled Send button does half the work for free

`app.js:288` disables `#sendBtn` whenever not connected. `#exportBtn` is
**never** disabled by connection state (§10.1). So in the not-connected state the
user sees a dead grey primary button and, directly beneath it, a live one. That
contrast is a stronger signal than any copy, and it required no design at all —
it is worth writing down only so nobody "fixes" the inconsistency by disabling
both.

---

## 5. The folder

### 5.1 Where it goes

> **Decision: `<Documents>\Yoto Maker\<card name>\`, one folder per card,
> never overwritten.**

**Not `work/`.** `%LOCALAPPDATA%\YotoMaker\work\` is the app's scratch space. It
is flat, it has **no cleanup of any kind** — verified: no bulk purge, no TTL, no
size cap anywhere in `yoto_maker/`; `DraftCard.reset()` (`draft.py:86-91`) clears
memory and deletes nothing — and it already holds thirteen different kinds of
intermediate file under fixed, overwritten names (`card_picture.png`,
`label.pdf`, `icon_<id>.png`, …). Putting the user's deliverables in there means
a deliverable can be silently clobbered by the next card's scratch, and it puts
*her* files inside the app's private area, where an uninstall or a bad update
takes them with it.

**Not the Desktop.** Too intrusive for a folder-per-card feature.

**Documents, because of the phone call.** The use case that decides this is the
same one configuration-surface §13.4 built setting 3 around: she is on the phone
with whoever set this up, and he asks *"where did it put them?"*. `Documents`
→ `Yoto Maker` is a sentence a person can say and a person can follow, on a
machine that is not in front of them. `%LOCALAPPDATA%` is not.

**Implementation constraint, and it has a user-visible consequence.** The
Documents folder is **not** `%USERPROFILE%\Documents` on every machine — OneDrive
redirects it, and localized Windows installs rename it. It must be resolved
through the OS (`SHGetKnownFolderPath` / `FOLDERID_Documents`), never by joining
strings. **The success panel must display the path the app actually used, never
a reconstructed one** — the same rule configuration-surface §13.4 applied to the
redirect URL (*"never constructed in JS"*), for the same reason: the one moment
the value matters is the moment the guess is wrong.

### 5.2 The folder's name, and collisions

The folder is named after the card, sanitized for Windows (`/ \ : * ? " < > |`,
trailing dots and spaces). If the resulting name is already taken, the app
appends ` (2)`, ` (3)`, … — **the convention Windows itself uses when you copy a
file**, so it needs no explanation.

**Nothing is ever overwritten.** She may be halfway through uploading the
previous copy. The success panel always names the folder she actually got
(`copy.md` §5), so a `(2)` is stated rather than discovered.

**Timestamped folder names were rejected.** `Bedtime Stories 2026-09-05 14-03`
answers a question nobody asked and makes the folder harder to say out loud on
the phone. `(2)` is both familiar and sufficient.

**Card name is required**, exactly as it already is for sending
(`app.py:637-638` — *"Give your card a name before sending it."*). Export raises
the parallel refusal rather than inventing a fallback name; §10.1.

**Path length is a real risk and Planner must handle it.** A long card name plus
a long track title plus a redirected Documents path can exceed Windows' 260-char
limit, and the failure mode is a partial export. The user-visible requirement:
**a long title is truncated in the file name, never dropped, and the numbering is
never disturbed.** The instruction sheet lists the file names as written, so a
truncation is visible rather than confusing.

### 5.3 What is in it

```
Documents\Yoto Maker\Bedtime Stories\
│
├─ 01 - Chapter One.mp3
├─ 02 - Chapter Two.mp3
├─ 03 - Chapter Three.mp3
├─ Card picture.png
├─ What to do next.html
└─ Track pictures\
   ├─ 01 - Chapter One.png
   ├─ 02 - Chapter Two.png
   └─ 03 - Chapter Three.png
```

Four rules govern that listing.

**(a) The numbering is the card's track order, and it is the ordering
mechanism.** A web upload orders by file name or by selection; a zero-padded
prefix survives all of it. The width matches the `key` the API path already
writes (`models.py:31` — `key = f"{i:02d}"`, 1-based), widening to three digits
only past 99 tracks so the sort never breaks.

**(b) Non-audio files sort below the audio, and are named in words.**
`Card picture.png` and `What to do next.html` both sort after every `NN - ` entry
(digits precede letters), so the audio she is selecting is a contiguous block at
the top of the list. Neither is named cryptically: she is going to meet these
files in a file-open dialog with no help text.

**(c) The track pictures are in a subfolder, and that is the whole point.** See
§9 — it is what makes this design safe against an unverified assumption.

**(d) No `.txt`, no `.json`, no log, no leftovers.** Everything in the folder is
something she might legitimately open or upload. `work/` is where the app's
plumbing lives and it stays there.

### 5.4 File naming

`NN - <track title>.<ext>` — space-hyphen-space, the audiobook and music-library
convention, and the most legible of the candidates at a glance. `NN_title` and
`NNtitle` were rejected as harder to read; a bare `NN.mp3` was rejected because
the title is the only thing that tells her which file is which when the website
asks her to name a track.

Track titles are sanitized the same way folder names are.

**Split parts need no special handling, and this is a correction to the brief —
see §12.1.** A track over the limit has *already* been split by the time it
reaches the draft, and each part is already its own track with a title ending
`(part 1)`, `(part 2)` (`app.py:235`, `app.py:243`). Export numbers them flat
alongside everything else, because on the card they genuinely are separate
tracks:

```
02 - The BFG (part 1).mp3
03 - The BFG (part 2).mp3
04 - The Twits.mp3
```

Filename sort still equals play order, which is the only property that matters.
The user is told this happened (`copy.md` §5.3) — on the send path the split is
invisible, but here she will *see* two files where she added one, and an
unexplained extra file reads as a bug.

---

## 6. The instruction sheet — this is the actual feature

A folder of correctly-named files is not the deliverable. **The deliverable is a
user who ends up with a working card**, and the distance between those two things
is entirely covered by instructions she has never been given.

### 6.1 Medium: an HTML page in the folder, opened from a button in the app

> **Decision: a single self-contained `What to do next.html`, written into the
> folder, and also openable directly from the app's success panel. Not a
> `README.txt`, not an on-screen-only panel, not a PDF.**

The decision follows from **where she is standing when she needs it**: in a
browser, at Yoto's website, with an Explorer window open — and *not* looking at
Yoto Maker. That kills the on-screen-only option outright: an in-app panel is on
the wrong screen at the moment of need, and she will have to alt-tab back and
forth between three windows to follow it.

| Candidate | Verdict |
| --- | --- |
| **HTML file in the folder** | ✅ **Chosen.** Opens in the browser she is already using, beside the site she is already on. Survives the app being closed, the folder being copied, the computer being restarted. Can be styled in the app's own voice and colours, can carry a real clickable link to `my.yotoplay.com`, can list her actual file names, and prints with Ctrl+P if she wants it beside her. |
| `README.txt` | ❌ Opens in Notepad, unstyled, no link, no picture, and it reads as a developer artifact. The one thing it does better — being unmissable — is bought back by the app's success panel naming the file. |
| A printable PDF, reusing the label pattern | ❌ The label PDF pattern (`app.py:667-691`) is the right *interaction* precedent and §7 borrows it. But the destination here is a **website**, and a PDF puts a viewer between her and a link she should be able to click. It also means reportlab layout work for a document that is a page of text. |
| On-screen panel only | ❌ Wrong screen at the moment of need, and lost the instant she closes the tab. |
| All of the above | ❌ Three copies of one instruction is three things to drift. |

**Two-tier, not duplicated.** The app's success panel carries *orientation* —
what just happened, where it went, and two buttons. The sheet carries the
*procedure*. The panel never restates the steps, so there is exactly one place
the procedure lives and no possibility of the two disagreeing.

### 6.2 The sheet is generated, not templated-and-hoped

It contains her actual card name, her actual track titles, her actual file names
in her actual order, and — if she chose one — her card picture. That specificity
is most of its value: a generic page saying "add your audio files" is a page she
still has to translate.

**It is generated from what was actually written to disk, not from the draft.**
This is a hard requirement, not a nicety: on a partial failure (§10.4) a sheet
generated from the draft would list files that are not there, and she would
upload a card with a hole in it and not know why. `copy.md` §6.8 carries the
missing-track notice that a partial run puts at the top of the sheet.

### 6.3 It must be self-contained

No external requests — the app makes none anywhere today (`DESIGN.md` §8) and
must not gain one for this. Inline `<style>`, no web fonts, and **the card
picture embedded rather than linked**. A relative `<img src="Card picture.png">`
would work from the folder and break when the same page is served over `http://`
from the app (§7.2), and a page that is subtly different in two places is a page
that will drift. One file, one rendering, both routes.

### 6.4 It ends where `INSTALL-FOR-MOM.md` ends

The last step is not "press Save on the website". It is **tapping the blank card
in the Yoto app** — the manual step that exists on the send path too and that no
third-party app can do for her (`SETUP-YOTO-CONNECTION.md:100-104`,
`INSTALL-FOR-MOM.md:76-77`). Omitting it would leave her with a finished upload
and a card that does nothing, which is the single most likely way this feature
fails a real user.

The wording is lifted from `INSTALL-FOR-MOM.md` deliberately — she may have read
it there, and two different phrasings of one step is two steps as far as she is
concerned.

Full text of the sheet, verbatim: [`copy.md` §6](copy.md). Layout:
[`mockups/instruction-sheet.md`](mockups/instruction-sheet.md).

---

## 7. Getting her to the folder

**There is no affordance for this anywhere in the app today.** Verified: zero
occurrences of `os.startfile`, `explorer`, `xdg-open` or `open -R` in the
repository. The only "show the user something outside the page" mechanism that
exists is `webbrowser.open` (`app.py:755-759`), and the only place a filesystem
path is shown at all is Settings' help section, as un-clickable
`.mono-value` text.

### 7.1 Two buttons, and the instructions are the primary one

`.done-actions`, the exact construction step 4 already uses for the label
(`index.html:222-225`):

| Order | Class | Label |
| --- | --- | --- |
| 1 | `.btn primary` | `📄 What to do next` |
| 2 | `.btn` | `📂 Open the folder` |

**The instructions are primary, and the folder is secondary. This inverts the
obvious ordering deliberately.** A user who opens the folder first meets a pile
of files and a decision she has no basis for; a user who reads the page first is
told to open the folder as step 3 of 6. The folder is useless without the
procedure, and the procedure tells her when to want the folder. Ordering them the
other way round optimises for the button that *sounds* more concrete at the cost
of the one that actually unblocks her.

`.setting-actions`' rule — **primary first, at most one primary** — carries over
unchanged.

### 7.2 `📄 What to do next` opens in a new tab, exactly like the label

`#labelOpen` is an `<a class="btn primary" target="_blank" rel="noopener">` whose
`href` the job result supplies, with a cache-busting query string
(`app.js:2011-2022`). This is the same shape: the export job's result carries the
URL, the anchor's `href` is set from it, and the page opens in a new browser tab
— which is where she needs to be anyway.

The user has already learned this exact interaction in step 4. Reusing it costs
nothing and teaches nothing new.

### 7.3 `📂 Open the folder` needs a new server capability — Planner must scope it

This is the one genuinely new mechanism in the feature.

**A `file:///` link cannot do it.** Browsers refuse `file://` navigation
initiated from an `http://` page, silently. It must not be shipped and must not
be "tried first".

**A ZIP download cannot do it either.** It lands in Downloads, and unzipping is
precisely the file management `DESIGN.md` §2 promises she will never face.

**So: the server opens the folder**, because the server is the same machine, the
same OS account, and the same person. This is configuration-surface §7.8's
argument applied unchanged — the app binds to `127.0.0.1` (`config.py:111`) and
has no authentication of any kind, so *"the browser, the server, the OS account
and the person are all the same."* There is nothing for a gate to gate.

**One safety property is a design requirement, not an implementation detail:**
the route must reveal a folder **remembered server-side**. The browser must not
be able to name a path. Even on loopback, an endpoint that hands an arbitrary
caller-supplied string to the shell is a foot-gun with no upside.

*Amended: "**the** folder the server last wrote" was too narrow.* There can be
more than one panel — two tabs, or a reload during a save — and a single "last
folder" serves whichever job finished **last** to all of them, so one tab's
buttons act on another tab's card. Each completed save therefore gets an **opaque
id** the server mints, carried inside the URLs the job result hands the panel, and
kept in a small capped map. That is not a relaxation of the rule above: an id is
looked up in a map the server itself populated, never joined onto anything, so an
id nobody minted — a path included — resolves to nothing and takes the same
"folder is gone" failure a deleted folder does (`copy.md` §5.5a).

**Packaging.** `os.startfile` is stdlib, imports nothing, and needs no hook, so a
PyInstaller-frozen build is not a concern. Planner should still confirm it in the
frozen `.exe` rather than take that on trust.

**It must degrade.** If the reveal fails or is unavailable, the panel shows the
full path in `.mono-value` and a short line telling her where to look
(`copy.md` §5.5). The button is **omitted, never disabled** — the discipline
configuration-surface §3.5.2 and §13.5 both apply: a control is removed when it
could do nothing, so it never invites a press that goes nowhere.

---

## 8. What Yoto's website will and won't take

*Resolved 2026-09-05 for format; a second, harder constraint arrived with the
answer. §8.2's provenance box governs how much weight any of it carries.*

### 8.1 What the app actually produces — verified

**The app does not transcode local files.** `AudioFileAdapter.fetch`
(`sources/audiofile.py:26-61`) is a `shutil.copy2`, an ffprobe and a tag read;
the file keeps its extension and its codec. `normalize_to_mp3()`
(`normalize.py:155-186`) exists and is **dead code** — its only caller anywhere
is `tests/test_audio_images_labels.py:26`.

`SUPPORTED_EXT` (`sources/audiofile.py:14`) is:

```python
{".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".mp4", ".opus"}
```

YouTube sources are always `.mp3`, because yt-dlp's `FFmpegExtractAudio`
postprocessor runs unconditionally (`sources/youtube.py:44`) and `_locate` only
looks for `.mp3` (`youtube.py:150`).

**So an export folder can contain `.flac`, `.wav`, `.ogg`, `.opus`, `.aac`,
`.m4a` — and `.mp4`, which is a video container.** Yoto's API tolerates all of
it because Yoto transcodes server-side. A web upload form has no such obligation.

### 8.2 What Yoto accepts — resolved, and how far the answer goes

> **Copy-as-is set: `{".mp3", ".m4a", ".aac"}`. Everything else is re-encoded to
> MP3.**

Three independent sources agree on exactly those three:

| Source | Tier | What it says |
| --- | --- | --- |
| Yoto's product FAQ, `us.yotoplay.com/make-your-own` (undated marketing page) | Vendor documentation | *"You can make Yoto cards with any content that you own that is in MP3 or AAC/M4A format."* |
| The uploader's own server-side error string, quoted by a user on Yoto's community site | Hearsay — a user quoting a UI | *"Failed to process file. Make Sure it's a valid MP3, M4A or AAC audio"* |
| The live `my.yotoplay.com` bundle's file-picker `accept` filter | Observed, but weak | Much broader — 15 MIME types including wav / flac / ogg / opus / webm / wma |

> ### ⚠️ Provenance — this is **documentation, not tested behaviour**
>
> Every row above came from Yoto's public web pages, fetched by a research agent.
> It is accurate as far as it goes and it has **not been observed against a live
> upload.** Nothing in this section may be cited as a measured fact, and if a
> later empirical test disagrees, **the test wins** — the same rule
> configuration-surface `tokens.md` §2b adopted when derived contrast figures met
> measured ones.
>
> The genuinely unresolved part, stated plainly: **whether the *server* accepts
> more than these three is not known.** The broad `accept` filter is a browser
> hint with no client-side validation behind it — the file is PUT straight to a
> signed URL and the server transcodes — so it records an *intention*, not a
> guarantee. §16 carries the empirical test as a follow-up rather than a gate.

**`.m4b` is deliberately excluded.** It appears in the site bundle only as a dead
fallback default, overridden before it reaches any file input. Adding it on that
evidence would be reading a variable's initial value as a product decision.

### 8.3 The constraint that arrived with the answer — a per-track size cap

`support.yotoplay.com` (published/updated 2026-07-20), verbatim:

> 100 tracks per card
> 100 MB / 60 minutes maximum file size of any single track
> 500 MB / 5 hours maximum total file size of the audio content for any one card

**The repo splits on duration only.** `MAX_TRACK_SECONDS = 3000`
(`normalize.py:191`) is 50 minutes, which clears the 60-minute limit with margin
and says **nothing at all** about the 100 MB one. Do the arithmetic at that same
50-minute bound:

| A 50-minute track, as… | Size | Against Yoto's 100 MB |
| --- | --- | --- |
| WAV, 16-bit / 44.1 kHz stereo | **~529 MB** | ❌ five times over |
| FLAC (typical ~60% of WAV) | ~320 MB | ❌ |
| MP3 320 kbps | ~120 MB | ❌ over, narrowly |
| MP3 192 kbps | ~72 MB | ✅ |
| MP3 128 kbps | ~48 MB | ✅ |

**This produces a requirement on the conversion, and it is the useful part:**

> **The conversion bitrate must be chosen so that a track at the splitter's
> 50-minute bound lands under 100 MB. 192 kbps gives ~72 MB and is already the
> app's own YouTube bitrate (`youtube.py:44`).**

At that bitrate the size cap is **solved by construction** for every file the
conversion touches — the duration split bounds the length, and the bitrate bounds
the rate. Only files the conversion *doesn't* touch can still be oversized, which
is §8.6's advisory case.

*(One consistency check worth recording: 5 hours at 192 kbps is ~432 MB, so
Yoto's two card ceilings coincide at roughly 192 kbps. Above that, the 500 MB cap
binds before the 5-hour one. "MB" is read as 10⁶ throughout, the conservative
reading.)*

### 8.4 The rule

> **The folder contains only files Yoto's website will accept, at a size it will
> accept. Anything outside `{".mp3", ".m4a", ".aac"}` is written as a 192 kbps
> MP3 copy instead, automatically, and the panel and the sheet each say so in one
> sentence.**

Concretely, of the eight extensions `SUPPORTED_EXT` admits: `.mp3`, `.m4a` and
`.aac` are copied; `.wav`, `.flac`, `.ogg`, `.opus` and `.mp4` are converted. The
common YouTube path is always `.mp3` and is never touched.

**Re-encode the formats in the broad `accept` filter too**, rather than trusting
it. The trade is asymmetric and that asymmetry is the whole argument: a pointless
re-encode is the cheap failure; **a rejected upload in front of a non-technical
user, mid-task, on a website the app does not control, is the expensive one.**

### 8.5 Why converting beats warning — four reasons, and not all of them rest on Opus

1. **She cannot act on a warning.** *"Yoto's website may not take
   `01 - Song.flac`"* leaves her with a folder and a problem whose only recovery
   is: go back to step 1, remove the track, find an MP3 of it, start again. That
   is not a recovery for this audience; it is a dead end with a sentence
   attached, and configuration-surface §2.2's *"never dead-end her"* forbids
   exactly this shape.

2. **The format is documented as unacceptable.** Three independent sources
   (§8.2). This is now the load-bearing reason and it is the one that changed
   with the answer — before it, converting was a hedge against an unknown; now it
   is compliance with a documented set.

3. **Conversion is also what brings an oversized track under the 100 MB cap**
   (§8.3). This reason is **independent of anything Yoto documents about
   formats** — it is arithmetic on file sizes, and it would hold even if the
   uploader accepted WAV cheerfully. A 529 MB track is refused on size whatever
   the codec, and the app's duration-only splitter does not catch it.

4. **Little is lost that Yoto was going to keep.** Yoto transcodes server-side,
   so extra fidelity carried through the website is largely discarded seconds
   later. **This reason is now supporting rather than decisive** — §1.1's
   provenance box explains why the exact output codec is observed rather than
   documented, and an argument that leaned on it alone would be leaning on the
   softest evidence in the spec. Reasons 2 and 3 stand without it.

5. **It removes a decision she has no information to make** (`DESIGN.md` §8 —
   *"sensible defaults everywhere"*). A "convert these for me?" button would be a
   second flow, a second confirmation, and a question with no answer she could
   reach.

**No `.msg-box.warn`.** The note is `.msg-box info` — neutral instruction, which
is what it is. configuration-surface `tokens.md` §1 deliberately refused to add a
warn variant (*"a variant that can only be used incorrectly is a trap"*), and
this is not the amendment that overturns it.

### 8.6 Where the design advises instead of acting, and why that split is principled

Conversion fixes format, and fixes size for everything it touches. It leaves one
real gap: **a file already in the copy-as-is set that is over a limit anyway.** A
50-minute MP3 at 320 kbps is ~120 MB and would be copied untouched.

> **Decision: the app converts on format, and advises on size. It does not
> silently re-encode an MP3 to make it smaller.**

This is configuration-surface §13.2's two-tier discipline — *a hard rule that
acts, a soft rule that advises* — applied to a new pair, and the boundary sits in
the same place for the same reason:

| | Format | Size |
| --- | --- | --- |
| Evidence | Three sources agree; a wrong-format file is **certainly** refused | One support page; the number is a third party's current policy |
| Recovery cost if we act wrongly | A pointless re-encode | **Her audio is quietly made worse** |
| Verdict | **Act** | **Advise**, naming the actual number |

Re-encoding an MP3 to shrink it is a quality decision the app has no basis to
make on her behalf, and the trigger for it would be a number the app cannot
verify and cannot learn has changed. That is precisely the case §13.2 reserved
for advice.

**Three card-level ceilings get the same treatment** — 100 tracks, 500 MB,
5 hours. The app knows all three the moment the folder is written, and each gets
a sentence naming the real figure against the limit, with the only real recovery
carried in words: **make two cards instead of one.** Copy: [`copy.md` §5.9](copy.md).

**These ceilings apply to the send path too**, and it does not surface them
either. That is a pre-existing gap this feature merely stands next to. Fixing it
on the send path is not in scope (§14.2) — but it is worth knowing that the
export path is where a user will now *find out*, and that is a small argument for
the send path borrowing these strings later.

> **Resolved 2026-09-06, and in the opposite direction to the guess above.** The
> send path does **not** borrow §5.9's strings, and it cannot: they say *"Yoto's
> **website** may refuse it"*, which is false where the app itself is sending,
> and their `{list}` form is ratified for a file dialog that does not exist
> there ([item 20's plan
> §1.4](../../superpowers/plans/2026-09-05-per-track-size-limit.md)). **What the
> send path borrows is this section's own conclusion, and the button.** When
> Yoto refuses one track, `copy.md` §10.1 points at `📁 Save the files to a
> folder` — because for the population that hits it (a local `.wav` or `.flac`)
> conversion at 192 kbps is exactly the *acting* this section declined to do on
> the send path, already done, on the other button. **The advise/act split is
> unchanged: the send path still advises, and the act happens only where the
> user chose it.**
>
> The pre-send advisory this paragraph imagined is queue item 21, still blocked
> on a live probe and still able to close unshipped.

### 8.7 The panel and the sheet always name what was converted

By number and title. Not because she needs to act on it, but because a file whose
name she recognises with an extension she did not choose is exactly the kind of
surprise that makes a person stop and call someone. One sentence pre-empts the
call.

### 8.8 Two inputs deliberately not used

Recorded so a future pass does not "improve" §8.4 with either of them.

**Yoto's card-content schema `format` enum is not the uploader's accept list.**
`yoto.dev/reference/card-content-schema/` lists `mp3`, `aac`, `alac`, `flac`,
`pcm_s16le`, `opus`, `ogg`, `x-m4a`, `wav`, `aiff`, `mpeg`. That is **track
metadata on a card object**, and it covers streaming tracks pointing at arbitrary
external URLs — it describes what a card can *reference*, not what the MYO
uploader will *ingest*. It must not widen §8.4 by a single extension.

**The removed Opus support article is not evidence against §1.1.** See §1.1's
provenance box. It is older than the repo's own live capture and describes a
migration it says did not apply to MYO. It is stale, not contradictory, and §8.5
has been restructured so that nothing decisive depends on it either way.

---

## 9. Icons and the card picture

### 9.1 The open question, stated as a question

> **Does `my.yotoplay.com` let a user attach a custom 16×16 picture to an
> individual track?**

**Needs verification.** The API path does it (`display.icon16x16`,
`models.py:36`), which says nothing about the web form. If the site supports it,
exporting the icons preserves a feature the user deliberately used
(`POST /api/tracks/{id}/icon`, `app.py:330-338`). If it does not, the icons are
clutter in the exact file-open dialog she is trying to use.

### 9.2 The design does not need the answer

> **Decision: track pictures go in a `Track pictures\` subfolder, named to match
> their audio file. The sheet mentions them conditionally, in one short
> paragraph.**

The subfolder is what makes the question non-blocking:

- **If the site supports per-track pictures**, they are one click away, already
  matched 1:1 to the audio by name, and the sheet points at them.
- **If it does not**, she never opens the subfolder and it costs her nothing —
  crucially, it does **not** appear in the file dialog she uses to select the
  audio, which is where loose 16×16 PNGs would do real harm.

The sheet's paragraph is written to be true under both answers: *"If Yoto's
website asks you for a picture for each track, they're in this folder. If it
doesn't, you don't need them."* (`copy.md` §6.6). No copy anywhere asserts that
the site does or does not support it.

### 9.3 One picture per track, even when they are identical

`_resolve_icon` (`app.py:618-628`) always returns something — its final fallback
is the bundled `music` icon — and its middle branch derives the icon from the
*card* picture. So on a typical card **every track's picture is byte-identical**.

Exporting one file per track anyway is deliberate. De-duplicating would break the
1:1 name match that makes the folder usable without thought, and would require
the sheet to explain a mapping. Eighteen copies of a 16×16 PNG is about four
kilobytes.

**Note for Planner:** `_resolve_icon` is lazy and has a filesystem side effect —
it writes `work/icon_<track.id>.png` via `make_device_icon`. Until
`POST /api/send` or `POST /api/label` runs, those files do not exist. Export must
call the same function, not reimplement the resolution order, so that a card
saved to a folder carries the same pictures as the same card sent to Yoto.

### 9.4 The card picture

`Card picture.png` at the top level — a copy of `work/card_picture.png`
(`app.py:376`), an aspect-preserving RGB PNG of at most 1024px (`picture.py:14`).

It is at the top level rather than in the subfolder because it is a **single**
file she will plausibly be asked for, and burying a single file is worse than
listing it. It sorts after every numbered audio file.

**Named in the app's own vocabulary, not the website's.** Step 2 says *"Name it
& pick a picture"*; the app calls it a picture everywhere. If verification shows
`my.yotoplay.com` calls it something else prominently — "cover image" is the
likely candidate — configuration-surface §7's *Redirect URL* precedent applies
and the **sheet's** wording should adopt the site's word while the **file name**
stays in the app's. One string changes; nothing structural does.

**Omitted entirely when the card has no picture.** No placeholder, no empty file.

---

## 10. States

Full state machine, focus and keyboard behavior in
[`interactions.md`](interactions.md). Every string in [`copy.md`](copy.md). This
section is the design decision behind each state.

### 10.1 Empty — nothing to save yet

**The button is never disabled, and pressing it produces the explanation.**

This is configuration-surface §13.5's rule (*"the connect button stays enabled…
pressing it is the fastest path to the explanation"*) and it also happens to be
exact parity with `#sendBtn`, which is disabled **only** by connection state
(`app.js:288`) and answers an empty draft with a plain-language refusal from the
server (`app.py:634-638`).

Export raises the same two refusals, worded in parallel:

| Guard | Send says (shipped) | Save says (new) |
| --- | --- | --- |
| no tracks | `Add some audio before sending to Yoto.` | `Add some audio before saving it.` |
| no card name | `Give your card a name before sending it.` | `Give your card a name before saving it.` |

Two sentences that differ by two words is not duplication to be refactored away —
it is how the user learns that the two buttons are peers.

**`#exportBtn` is never disabled by `STATUS.yoto.connected`.** Doing so would
delete the feature's main reason to exist.

### 10.2 Working

A `.progress` bar and a `role="status"` message, the exact construction
`#sendProgress` and `#addProgress` already use. Per-track messages
(`Saving “Chapter Three” (3 of 5)…`), because — as `index.html:102-106` argues
for the add batch — *"the progress text is the ONLY signal of liveness a
non-sighted user has, and hearing nothing for forty seconds is indistinguishable
from a hung app."*

**No Cancel button, and this is a decision rather than an omission.**
`yoto_maker/server/jobs.py` has **no cancellation** — the `#addCancel` precedent
(`index.html:108`) works by aborting a frontend `fetch` on the *synchronous*
file-upload path, which has no equivalent here. Specifying a Cancel would require
new job-runner capability, i.e. an Architect decision, for a job that is mostly
local file copying. If UAT finds real cards where the copy takes long enough to
want a way out, cancellation is a follow-up and it is a job-runner change, not a
UI one.

**Splitting does not appear in this state, and that is a correction to the
brief — §12.1.**

### 10.3 Success

`#exportDone` (`.msg-box ok`) names what happened and where it went, then
`#exportActions` carries the two buttons. Between them, `#exportNote`
(`.msg-box info`) appears only when there is something true to say. There are now
**seven** things it can say, each its own paragraph, in this fixed order:

| # | Paragraph | Shown when |
| --- | --- | --- |
| 1 | One or more long tracks were split into parts — **one paragraph however many were split** (`copy.md` §5.3, singular and plural) | any title ends `(part N)` |
| 2 | Files were saved as MP3 copies | anything was converted (§8.4) |
| 3 | A single track is over Yoto's 100 MB limit | after conversion, any file > 100 MB (§8.6) |
| 4 | The card is over 500 MB | card ceiling exceeded |
| 5 | The card is over 5 hours | card ceiling exceeded |
| 6 | The card has more than 100 tracks | track count > 100 |
| 7 | The shared recovery sentence for rows 4–6 — shown **once**, however many of the three fired | any card ceiling exceeded |

Ordered by how likely she is to meet it and by how early in her upload it
matters. Paragraphs 3–7 are **advisory, never blocking** — the numbers are a
third party's current policy, not something the app can verify (§8.6) — and each
names the real figure against the limit rather than saying "too big".

`.msg-box p` / `.msg-box p:last-child` (`styles.css:257-258`) already carry
multi-paragraph bodies. Seven is the theoretical maximum and would need a card
that is simultaneously split, converted, oversized, over-500-MB, over-five-hours
and over-count; realistically one or two appear. (The count is seven and not five
because `copy.md` §5.9 gives the three card ceilings **a line each** and then one
shared recovery sentence — the recovery is factored out precisely so that two
ceilings firing together do not read as two problems with two fixes.)

The box names the folder **in words** (`a folder called “Bedtime Stories”, in
your Documents, under Yoto Maker`), not as a path. The full path appears only
when the reveal button cannot (§7.3), where it is the answer rather than clutter.

### 10.4 Partial failure — some tracks are saved, one is not

**Allowed, loudly, and the sheet must tell the truth.**

The precedent is v0.1.11's multi-file add (`RELEASE_NOTES.md:39-46`): *"If one of
them doesn't work, the rest still get added and Yoto Maker tells you which one it
was and why."* Failing the whole export because one source file is locked would
throw away seventeen successful copies to protect against a problem she can see.

Three things must all be true in this state:

1. `#exportDone` states the real count — `4 of your 5 tracks are saved` — never
   an unqualified success.
2. `#exportError` names which track failed and why, by number and title.
3. **The instruction sheet is generated from what landed**, lists only the files
   that exist, and carries the missing-track notice at the top (`copy.md` §6.8).
   Without this, she uploads a card with a hole in it and has no way to know.

A red box beside a green one is the honest rendering of a partial outcome, and it
is what the add batch already does.

### 10.5 Total failure — nothing was saved

> **The boundary between §10.4 and this state is whether at least one track was
> written.** Zero tracks written is a **total** failure, and the folder is
> removed — even when the card picture and the instruction sheet could have been
> written successfully. Neither of those is the deliverable; the audio is, and a
> folder holding a picture, a page of instructions and no audio is worse than no
> folder at all. `#exportDone` must never render `0 of your 5`.
> *(Specified 2026-09-05. Planner had inferred exactly this and was right; it was
> not written down, which is the defect.)*

`#exportError` only; no success box, no action buttons, no half-written folder
left behind. The causes are disk, permissions, path length, or **every track
failing individually** — none of which the app can repair — so the recovery is
**carried in words**, which is copy.md §4d's established pattern for exactly this
situation (*"offering a control that cannot
act is the failure §7.4 already ruled against"*).

**Nothing is left behind.** If the folder was created and then the run failed, it
is removed. A folder that exists but is wrong is worse than no folder, because
she will find it and use it.

### 10.5a The one state where that invariant cannot be honoured *(added 2026-09-05)*

**A cleanup only runs while something is alive to run it.** If Yoto Maker itself
goes away mid-write — quit from the tray, crashed, the machine slept — the job
dies with the process that would have removed its folder, and a half-finished
folder is left on disk with no instruction sheet in it.

The app cannot fix this from inside the failure, and it must not pretend
otherwise. What it can do is **stop claiming an outcome it does not have**, and
give her a test that distinguishes the two folders:

> `What to do next.html` is written **last**, after every audio file and every
> picture (`export/runner.py:247`). **Its presence is the completeness signal.**
> `copy.md` §5.10 is built on that, and `interactions.md` §4a renders it.

**This makes the write order a contract.** §10.4 point 3 already required the
sheet to be generated from what landed; this adds that it must also be written
**after** what landed. If a refactor moves it earlier — for a preview, say —
§5.10's second paragraph becomes a lie and must change with it, exactly as
§10.5's reassurance sentence must change if the folder stops being removed.

### 10.6 Pressed twice

A second run makes `Bedtime Stories (2)` and says so. Nothing is overwritten; see
§5.2.

---

## 11. Backend implications — Planner must scope these

Design-relevant only. Shapes and mechanisms are Planner's and Architect's.

**11.1 A new job, forking `send_to_yoto()` above its connection check.**
`app.py:631-661` assembles a complete, network-free description of the card at
lines 643-647 — `list[TrackInput]` plus `card_name` — and the only auth
precondition is line 640. Export needs the two guards at 634-638 and **not** the
one at 640.

**The track list, the icons and the card name must be produced by the same code
as the send path**, so that a card saved to a folder and the same card sent to
Yoto are the same card. In particular `_resolve_icon` must be *called*, not
reimplemented (§9.3).

**11.2 A job, using the existing runner.** `jobs.py`'s `Job.view()` and
`app.js`'s `pollJob()` (500ms, `app.js:80-89`) are sufficient and already have
three call sites. Copying a multi-hundred-megabyte audiobook will block, so this
should not be synchronous the way `POST /api/label` is.

**11.3 The job result must carry what the panel renders.** The label precedent is
`{"ok": true, "label_url": "/api/label.pdf"}` (`app.py:683`). The export result
needs at least: the folder's display name, its full path, the number of tracks
written, the failures (if any), whether anything was split, **which tracks were
converted**, **which tracks exceed 100 MB and by how much**, **the card's total
size, total duration and track count**, and the URL for the instruction page. The
panel must render *only* from that result — nothing about the folder may be
reconstructed in JS.

The three card totals are what §10.3's paragraphs 4 and 5 test against, and they
must be measured **from the files as written** — after any conversion, which is
the whole point (a 529 MB WAV becomes a ~72 MB MP3, so testing the source would
report a ceiling breach that the export itself just fixed).

**11.4 A route that serves the instruction page**, so `📄 What to do next` can be
a plain `target="_blank"` anchor. Same shape as `GET /api/label.pdf`.

**11.5 A route that opens the folder**, revealing the last folder the server
wrote and taking no path from the browser (§7.3).

**11.6 `/api/status` gains one field** if §14.2's Settings row ships: the root
saved-files folder, alongside the existing `config.data_dir` (`app.py:154`),
which is already sent to the browser as a string. One field, resolved on the
server, never constructed in JS.

**11.7 The Documents folder must be resolved through the OS**, not by string
joining (§5.1).

---

## 12. Corrections to the brief

Both were found while checking the code and both change the design.

### 12.1 Splitting is already done before export sees the draft

The brief states: *"Track splitting still applies… Export must carry this through
or a long audiobook fails on the website too."*

**It is already carried, upstream.** `split_audio` is called once in production,
in `_add_result_as_tracks` at **add time** (`app.py:235`), and each returned part
is turned into its own `Track` with a title suffixed `(part N)` at
`app.py:243`. By the time a track is in the draft, the split has happened and the
parts are already separate tracks.

Three consequences, all simplifying:

- Export never calls `split_audio`. It writes what the draft holds.
- The "splitting can be slow" progress state does not exist. §10.2.
- The user still has to be told (`copy.md` §5.3), because she will see two files
  where she added one — but it is a note in the success panel, not a phase.

*(Worth noting for anyone reading the file names later: three numbering
conventions coexist in this codebase — the on-disk part suffix `_part000` is
0-based and 3-digit, the user-visible title `(part 1)` is 1-based, and the API
`key` `"01"` is 1-based 2-digit. Export uses the **card's track order**, which
matches the `key` convention.)*

### 12.2 The card picture never reaches Yoto as a card picture

The brief's fact #4 concerns per-track icons and is answered in §9. Alongside it:
`draft.picture_path` is **not** passed to `send_to_yoto()` at all. It reaches
Yoto only indirectly, as the *source image* from which `_resolve_icon` derives
16×16 track icons.

So `Card picture.png` in the export folder is genuinely new capability, not a
port of something the send path does — which strengthens §9.4's decision to
include it, and means the "does the website accept a cover picture, and what does
it call it?" question has no in-repo precedent to lean on.

---

## 13. What is deliberately not changing

**The send path.** `#sendBtn`, `#sendProgress`, `#sendError`, `#sendDone`,
`connectYoto()`, `sendToYoto()`, `POST /api/send`, `YotoClient` — none of it is
touched. This feature appends; it does not fork the existing path.

> **Amended 2026-09-05, and the amendment is narrow.** The send path gains
> **one message and nothing else**: when a status poll fails after a send job has
> started, `#sendError` renders `copy.md` §9 instead of the generic transport
> line, because that line ends *"then try again"* and pressing 🚀 Send to Yoto
> during a live send puts a second card in her Yoto account. No markup, no
> control logic, no route and no shipped string is edited —
> `sendToYoto()` asks the shared `pollJob()` for the retry behaviour
> `interactions.md` §4a specifies, and renders one new message when it is spent.
> **`copy.md` §9.1 carries the argument, including the one-line fallback that
> keeps the send path out of the diff entirely and what that gives up.**
>
> **Not taken.** The maintainer took that fallback on 2026-09-05: the send path
> stays out of this PR's diff entirely. **The unamended paragraph above the
> blockquote is therefore what shipped, and it is accurate as written** — none
> of `#sendBtn`, `#sendProgress`, `#sendError`, `#sendDone`, `connectYoto()`,
> `sendToYoto()`, `POST /api/send` or `YotoClient` is touched. What is given up
> is the duplicate-card protection. §9 is a written follow-up.

> **Amended again 2026-09-06 — and this change is not this feature's.** Queue
> item 20 edits two strings rendered into `#sendError`, both inside
> `YotoClient._friendly_http`'s 413 branch, so the paragraph above is no longer
> literally true of `#sendError` or `YotoClient`. **This package did not make
> that change and does not own the send path.** It ratifies the strings —
> `copy.md` §10, `interactions.md` §4b — for one reason: the per-track refusal
> **names `📁 Save the files to a folder` and relies on where this package put
> it.** A string that quotes this package's button label must be findable from
> this package, or a future relabel silently breaks a recovery on another path.
>
> **Everything else in the paragraph stands.** No markup, no control logic, no
> route, no CSS, no token, no region and no tab stop changes; `#exportRow` is
> not touched in any way (`copy.md` §10.5). The everyday-path ledger below is
> unaffected — this is an error path reached only after Yoto has refused.

**Step 3's title and hint.** *"Send it to your Yoto"* names the goal, not the
mechanism, and stays true (§4.2). `INSTALL-FOR-MOM.md`'s step numbering and
`SETUP-YOTO-CONNECTION.md`'s instructions are unaffected.

**`#advRow`, the Settings link, and the header pill.** Unchanged in position,
copy and behavior. The configuration surface's three entry points keep doing what
configuration-surface §12 settled.

**The `.setting` primitive.** §14.2's one added row inside setting 3 is
configuration-surface §4.4's *"copy the template, fill the slots, append"*
procedure applied to a row rather than a section. No slot is added, no rule is
edited, no `.setting*` CSS changes.

**`styles.css`.** Zero new rules, zero edited rules, zero new tokens. See the
header of this file.

**The everyday-path ledger.** One `.btn` and one `.tiny` paragraph — **two
elements, rendering as roughly three lines at 720px** — both at the bottom of
step 3, both below the primary action and below every existing feedback box. The
**six** `#export*` regions beneath them are `.hidden` until the button is
pressed, so a user who never presses it sees exactly two added elements, ever.

*(Five until 2026-09-05, when `#exportOpenError` was added. The ledger this
section keeps is the **everyday-path** one, and a sixth hidden `.msg-box`
changes nothing in it: no CSS, no token, no tab stop, and nothing rendered until
a button is pressed. Counted here rather than left stale, because a number in a
ledger that quietly stops matching is the drift this section exists to catch.)*

*(Stated as elements and as rendered lines, because saying "one 13px line" was
ambiguous between the two and the mockups and spec had already resolved it the
other way. The caption is one `<p>` carrying two sentences, which wrap to two
lines at 720px — `mockups/step-3.md` §1 draws it. Corrected 2026-09-05.)*

---

## 14. Out of scope

### 14.1 A persistent "always save to a folder" preference — **decided: no**

> **Decided by Mark, 2026-09-05: per-card choice only, no setting.** This
> confirms what §4 specifies and closes §16's question 6.

Recorded rather than silently dropped, because it is the reading of the phrase
"a separate mode" that this spec did **not** take, and someone will ask.

The case for it is real: a user who is never going to sign in sees step 3's
connect box, a dead `🚀 Send to Yoto`, and a live save button on every single
card, forever. A preference could turn step 3 into "save the files" outright and
hide the connection chrome.

It is out of scope because (a) the brief scoped Settings out, (b) it is not what
makes the feature work — the per-card action is the primitive, and a preference
would only change which button is emphasised, and (c) it would need its own
decision about what happens to the connection UI, which is a bigger question than
this PR.

**It is now also declined outright**, not merely deferred. If it is ever revived
it is `.setting` #4 and it costs no CSS — but **it must not be built as a second
mechanism.** It would reorder the two controls §4 already specifies, and nothing
more.

### 14.2 Everything else

- **A row in Settings' help section** — `Where saved files go` →
  `C:\Users\…\Documents\Yoto Maker`. This is the **one** Settings change this
  package proposes, it is one row in setting 3 (`index.html:397-441`), it costs
  no CSS, and it answers the exact question that section exists to answer on the
  phone (configuration-surface §13.4). It is listed here rather than in §11
  because it is optional: the success panel already shows the path, and this row
  only serves the *later* call. Ship it if Planner has room.
- **Putting the label PDF in the folder.** Tempting — the folder would then hold
  everything for one card. Rejected for this pass: the label is step 4's action
  and may never have been made, and coupling them means one step's failure
  reaches into another's deliverable.
- **Cleaning up old export folders.** They are hers. The app does not delete the
  user's files.
- **A "save and send" combined action.** Not asked for, and it would reintroduce
  the "always export then upload" shape the user explicitly rejected.
- **Cancelling a save in progress.** §10.2 — needs job-runner support.
- **Any change to `work/`'s lack of cleanup.** Pre-existing, unrelated, and this
  feature deliberately writes nowhere near it.

---

## 15. Success criteria

1. **A user who has never signed in can get from audio to a folder of files
   without meeting the sign-in wall as a blocker.** Verified by loading the app
   with no saved sign-in and completing steps 1, 2 and the new button using only
   what is on screen.
2. **The files, sorted by name in Windows Explorer and in a browser's file-open
   dialog, are in the order the card should play** — including when a long track
   was split into parts.
3. **A user who opens the folder and nothing else can finish the job.** The
   procedure is in the folder, names her card and her files, links to the
   website, and ends at tapping the physical card.
4. **A user who never presses the new button sees step 3 gain exactly one button
   and two lines of 13px text**, both below `🚀 Send to Yoto` and below every
   existing feedback box.
5. **A partial failure never produces an instruction sheet describing files that
   are not there.** Verified by making one source file unreadable mid-run and
   reading the generated sheet.
6. **Every user-visible string passes the `INSTALL-FOR-MOM.md` register test, and
   the word "export" appears nowhere the user can see.**
7. **The folder is never overwritten and its real path is never guessed.**
   Verified by saving the same card twice, and by running on a machine whose
   Documents folder is redirected to OneDrive.
8. **A card saved to a folder and the same card sent to Yoto contain the same
   tracks, in the same order, with the same pictures.** This is what stops the
   two paths drifting into two products.

---

## 16. Open questions

**Nothing here blocks Planner any more.** Question 1 was the gate and it is
answered; question 6 is decided. What remains changes a sentence, not a design.

### 16.1 Closed

| # | Question | Resolution |
| --- | --- | --- |
| 1 | Which audio file types does the uploader accept? | **`{".mp3", ".m4a", ".aac"}`** (§8.2). Everything else re-encoded to 192 kbps MP3 (§8.4). Provenance is **documentation, not tested behaviour** — §8.2's box governs how far it may be cited. Brought a second constraint with it: §8.3's size caps. |
| 6 | Is a persistent "always save to a folder" preference wanted? | **No.** Per-card choice only (§14.1). |

### 16.2 Still open — none blocking

| # | Question | Where it lands |
| --- | --- | --- |
| 2 | **Does the website let a user attach a picture to an individual track?** | §9.2. Nothing public found. The subfolder and `copy.md` §6.6's paragraph are written true under both answers, so this stays a nice-to-know. |
| 3 | **Does it let a user set a card cover picture, and what does it call it?** | §9.4. Nothing public found. Changes one word in the sheet, never the file name. |
| 4 | **How does the website order uploaded tracks?** | Zero-padded naming is robust to all three possibilities and `copy.md` §6.4's *"pick them all at once"* is correct under all three. Confirming would let the sheet be more specific; not confirming costs nothing. |
| 5 | **Does `os.startfile` behave in the PyInstaller-frozen `.exe`?** | §7.3. Expected yes; the degraded path covers a no. |

### 16.3 Follow-up worth doing, but not before shipping

> **Does the *server* accept more than `.mp3` / `.m4a` / `.aac`?**

§8.2 records this as the genuinely unresolved part: the site's own file-picker
`accept` filter is much broader, there is no client-side validation behind it,
and the file is PUT straight to a signed URL where the server transcodes. So the
broad list is an intention, not a guarantee, and nothing public confirms which
one the server honours.

**The empirical test is one upload:** put a small WAV through the website and
watch for a `Transcode failed` state.

It is a **follow-up, not a gate**, because the current rule is safe under either
answer — a needless re-encode is the cheap failure (§8.4). If the test comes back
permissive, `.wav` / `.flac` / `.ogg` / `.opus` could move into the copy-as-is
set and §8.3's size arithmetic immediately argues against moving `.wav` and
`.flac` anyway. **A permissive result would widen the set by very little and
should not be assumed to widen it at all.**
