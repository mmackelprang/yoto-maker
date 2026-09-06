# Design spec — save the files to a folder, and upload them by hand

**Date:** 2026-09-05
**Status:** **approved by Mark, 2026-09-05.** Planned and queued as
[BUILDER_QUEUE item 19](../../BUILDER_QUEUE.md); the implementation plan is
[`plans/2026-09-05-export-only-mode.md`](../plans/2026-09-05-export-only-mode.md).
**The blocking check is done (§0).**
**Ships as:** one PR. §7 argues against splitting it.
**Amended 2026-09-05** after research into Yoto's public documentation: §0
question 1 resolved, a per-track **size** limit found that changes §2.4's
argument structure, §1.1's Opus claim softened to match its evidence, §6.1
decided.

**Amended again 2026-09-05 (second pass)** after Planner found five copy gaps.
**Nothing in this spec changed — every fix landed in the handoff package**, and
Builder should read `copy.md` rather than work from this file's summaries:

| Gap | Resolution |
| --- | --- |
| `mockups/step-3.md` §7 carried the **pre-amendment** MP3 note | Corrected, and the mockup file now states in its header that `copy.md` wins and a divergence is the mockup's bug. |
| No plural for the split note | `copy.md` §5.3 — **one aggregated paragraph, never one per split group.** This **replaces** Planner's stopgap. *The Wild Robot*'s five parts are one split track and were always the singular case. |
| No `0 of your 5` variant | Confirmed as Planner inferred. `copy.md` §5.1 and `overview.md` §10.5 now state the rule: **zero tracks written is a total failure and the folder is removed**, and `copy.md` §5.7 gains the every-track-failed case. |
| Three Planner-authored strings | `copy.md` §5.5a and §5.9. Two ratified (one verbatim, one extended with the path); **`"There's nothing saved to open yet."` is replaced** — `yet` is false in every state that can reach it. |
| Two cross-reference drifts | Fixed: `copy.md` §6.7 → §6.8, and the everyday-path ledger now counts elements and rendered lines separately. |

**Recorded, not chased:** Planner sums card duration from the draft's
already-probed values rather than re-probing the written files, diverging from
§3.3. Conversion cannot change duration and re-probing costs an `ffprobe` per
track — an implementation decision, documented in the plan, and Designer has no
objection. §3.3's *"measured from the files as written"* remains the requirement
for **size**, which conversion very much does change.

**Relationship to existing handoffs:**

| Package | Declaration |
| --- | --- |
| [`export-only-mode/`](../../design-handoffs/export-only-mode/) | **NEW.** The handoff package for this feature. Four files: `overview.md`, `copy.md`, `interactions.md`, `mockups/`. **No `tokens.md`** — nothing new is introduced. |
| [`configuration-surface/`](../../design-handoffs/configuration-surface/) | **extends.** Deviates from nothing. Every rule it borrows is cited at the top of the new package's `overview.md`. §3's placement decision, §4's `.setting` primitive and §12's entry-point work are all untouched. |

**Zero new CSS. Zero new tokens. Zero edits to existing rules.** Every state is
built from `.btn`, `.btn.primary`, `.tiny`, `.progress`, `.bar`, `.msg`,
`.msg-box` (+`.err`/`.ok`/`.info`), `.done-actions`, `.mono-value` and `.hidden`
— all shipped. Per the configuration surface's own §13, that is the strongest
available evidence an extension fits the primitives rather than straining them.

---

## 0. The gate — answered

> **Copy-as-is set: `{".mp3", ".m4a", ".aac"}`. Everything else is re-encoded to
> 192 kbps MP3.**

Three independent sources agree on those three: Yoto's product FAQ
(`us.yotoplay.com/make-your-own` — *"any content that you own that is in MP3 or
AAC/M4A format"*), the uploader's own server-side error string quoted by a user
on Yoto's community site (*"Make Sure it's a valid MP3, M4A or AAC audio"*), and
— read against the grain — the live site bundle's file-picker `accept` filter,
which is much broader but is a browser hint with no validation behind it.

> ### ⚠️ This is documentation, not tested behaviour
>
> All of it came from Yoto's public web pages. **It has not been observed against
> a live upload**, and nothing in this spec may cite it as a measured fact. If a
> later empirical test disagrees, the test wins — the rule
> configuration-surface `tokens.md` §2b adopted when derived contrast figures met
> measured ones.
>
> The genuinely unresolved part: **whether the *server* accepts more than these
> three is unknown.** §0.2 carries the test as a follow-up, not a gate.

**`.m4b` is deliberately excluded** — it exists in the site bundle only as a dead
fallback default, overridden before it reaches any file input. Reading a
variable's initial value as a product decision is not evidence.

### 0.1 The constraint that arrived with the answer

`support.yotoplay.com` (published/updated 2026-07-20): **100 tracks per card ·
100 MB / 60 minutes per track · 500 MB / 5 hours per card.**

**The repo splits on duration only** — `MAX_TRACK_SECONDS = 3000`
(`normalize.py:191`), 50 minutes — which clears the 60-minute limit and says
nothing about the 100 MB one. At that same 50-minute bound: a WAV is **~529 MB**
(five times over), a FLAC ~320 MB, a 320 kbps MP3 ~120 MB, a 192 kbps MP3 ~72 MB.

This lands as a requirement on the conversion and it is the useful part:

> **The conversion bitrate must keep a track at the splitter's 50-minute bound
> under 100 MB. 192 kbps gives ~72 MB and is already the app's own YouTube
> bitrate (`youtube.py:44`).**

At that bitrate the size cap is **solved by construction** for everything the
conversion touches. Only files it doesn't touch can still be oversized — §2.4's
advisory case.

### 0.2 Follow-up, not a gate

> **Does the *server* accept more than `.mp3` / `.m4a` / `.aac`?** One upload
> settles it: put a small WAV through the website and watch for
> `Transcode failed`.

Not a gate, because the shipping rule is safe under either answer — a needless
re-encode is the cheap failure. And a permissive result would widen the set by
very little: §0.1's arithmetic argues against copying WAV and FLAC anyway.

### 0.3 Still open — none blocking

| # | Question | What it changes |
| --- | --- | --- |
| 2 | **Can a user attach a picture to an individual track?** | Nothing structural — nothing public found, and §2.5's subfolder plus `copy.md` §6.6's paragraph are written true under both answers. |
| 3 | **Can a user set a card cover picture, and what does the site call it?** | Nothing public found. One word in the sheet; the file name stays `Card picture.png` either way. |
| 4 | **How does the site order uploaded tracks?** | Nothing. Zero-padded naming and *"pick them all at once"* are correct under all three possibilities. |
| 5 | **Does `os.startfile` behave in the frozen `.exe`?** | §2.7. Expected yes; the degraded path covers a no. |

*(Question 6 — a persistent preference — is **decided: no**. §6.1.)*

---

## 1. What this is, and the defect it answers

A second way to get a finished card out of Yoto Maker: instead of sending it over
the connection, the app **writes the finished files to a folder**, and the user
adds them by hand on `my.yotoplay.com`.

It is **a mode the user chooses, one card at a time.** Not a stage of the send
pipeline, not a replacement for it, nothing automatic. The signed-in path is
untouched.

### 1.1 Why

Yoto transcodes every upload server-side, and `format` is the one field Yoto
**preserves from what the client POSTs**. `yoto/client.py:174-187` silently falls
back to a *local* probe when the transcode poll returns nothing usable, so a card
can claim `mp3` while Yoto serves something else — the leading suspect for a
physical player's offline download never completing (`SESSION_STATE.md:37-45`,
`RELEASE_NOTES.md:12-36`).

> **On "something else", stated as precisely as the evidence allows.** In July
> 2026 this repo captured `transcodedInfo: {"codec":"opus","format":"opus"}` from
> the live API — direct observation, the strongest evidence there is. But **Yoto
> does not publicly document that MYO uploads become Ogg Opus**; a support
> article since removed (Wayback 2025-12-07) described an Opus migration and said
> it applied *"only to certain Yoto titles, and not your Make Your Own
> playlists."* The repo's capture is eight months newer and is observation rather
> than description, so the article reads as **stale, not contradictory.**
>
> **The rationale is unaffected: the defect is the *mismatch*, and a mismatch
> does not care which codec is on the other side.** This is written down because
> the Opus claim used to be load-bearing in §2.4, and it no longer is — see
> reason 4 there.

**Uploading through the website removes the app's authorship of that field
entirely.** That is worth stating plainly because it changes what success means
here: this is not a convenience path, it is a path whose correctness does not
depend on the app getting a metadata field right.

### 1.2 The second benefit, which is worth as much

**This mode needs no sign-in at all.** A user who has never connected, or whose
connection is broken, or whose Client ID is malformed and has hard-blocked
sign-in (configuration-surface §13.5), can still finish a card. Today all three
are stopped dead at step 3.

---

## 2. The decisions

Full argument for each in
[`export-only-mode/overview.md`](../../design-handoffs/export-only-mode/overview.md).
This section is what Planner needs to build against.

### 2.1 Placement — one button in step 3, appended, never inserted

> **One `.btn` plus one `.tiny` caption inside step 3, always rendered,
> positioned after `#connectWarn` and before `#advRow`.**

```
  h2, hint, #connectRow, #sendBtn, #sendProgress,
  #sendError, #sendDone, #connectWarn          ← all unchanged
  ── new ──────────────────────────────────────────────────────
  #exportRow  #exportProgress  #exportError
  #exportDone  #exportNote  #exportActions
  ── end ──────────────────────────────────────────────────────
  #advRow                                      ← unchanged, STILL LAST
```

**Rejected:** a fifth step (breaks the four-step promise
`INSTALL-FOR-MOM.md:44` teaches verbatim — configuration-surface §3.1's argument,
already accepted once); a `Send it | Save the files` choice control at the top of
step 3 (taxes the everyday path with a decision, and overloads `.tab` at a third
scope); a `— or —` divider (costs ~40px on every visit and asserts a peerhood
that is not true); a Settings mode toggle (§6.1); a folder picker (not
implementable — the browser cannot hand the server a directory path, and the app
has never had a native dialog).

**Why after `#connectWarn` and not next to `#sendBtn`:**

1. Inserting between `#sendBtn` and `#sendProgress` would make the send button's
   own feedback appear below a *different* button. Action→feedback adjacency on
   the everyday path is worth more than proximity for the alternative.
2. Appended, it lands **directly beneath `#sendError` on a failed send** — the
   follow-the-symptom adjacency configuration-surface §12.4 chose `#advRow`'s
   position for.
3. It also lands **directly beneath `#connectWarn`**, so the user whose sign-in
   is hard-blocked by a bad Client ID meets a live way forward for the first
   time. That falls out of appending; it cost nothing.

**Everyday-path ledger: one `.btn` and two lines of 13px text.** The five
`#export*` regions beneath are `.hidden` until pressed.

### 2.2 The word "export" never reaches the user

The package is named `export-only-mode` and the DOM ids are `#export*`. **No
user-visible string contains "export", "directory", "path", "file format",
"codec", "transcode" or "metadata".** `../README.md`'s ban list gains no
exception. The verb is *save*, the noun is *files*, the destination is *a
folder*.

| Element | String |
| --- | --- |
| Button | `📁 Save the files to a folder` |
| Caption | `You’ll put them on Yoto’s website yourself. You don’t need to be signed in for this.` |

The split is configuration-surface §6.1's rule: short scannable button, caption
does the disambiguating. Rejected labels and why, including why `💾` loses to
`📁`, are in `copy.md` §2.

### 2.3 The folder

> **`<Documents>\Yoto Maker\<card name>\`, one folder per card, never
> overwritten.**

```
Documents\Yoto Maker\Bedtime Stories\
├─ 01 - Chapter One.mp3
├─ 02 - Chapter Two.mp3
├─ 03 - Chapter Three.mp3
├─ Card picture.png
├─ What to do next.html
└─ Track pictures\
   ├─ 01 - Chapter One.png
   └─ …
```

- **Not `work/`.** It is the app's scratch space, it is flat, it holds thirteen
  kinds of intermediate file under fixed overwritten names, and it has **no
  cleanup of any kind** — verified: no purge, no TTL, no size cap anywhere in
  `yoto_maker/`; `DraftCard.reset()` (`draft.py:86-91`) deletes nothing from
  disk. A deliverable there can be clobbered by the next card's scratch, and an
  uninstall takes her files with it.
- **Documents, because of the phone call.** *"In your Documents, under Yoto
  Maker"* is a sentence a person can say and follow about a computer that is not
  in front of them. `%LOCALAPPDATA%` is not.
- **Resolve it through the OS** (`SHGetKnownFolderPath` / `FOLDERID_Documents`),
  never by joining `%USERPROFILE%\Documents`. OneDrive redirects it and localized
  installs rename it. **The panel must display the path actually used, never a
  reconstructed one** — configuration-surface §13.4's redirect-URL rule, for the
  same reason.
- **Collisions get ` (2)`, ` (3)`** — the convention Windows itself uses, so it
  needs no explanation. **Nothing is ever overwritten**; she may be halfway
  through uploading the previous copy.
- **Card name required**, exactly as it already is for sending
  (`app.py:637-638`). Export raises the parallel refusal rather than inventing a
  fallback.
- **Path length is a real risk.** A long card name + long title + a redirected
  Documents path can exceed 260 chars. User-visible requirement: **a long title
  is truncated in the file name, never dropped, and the numbering is never
  disturbed.**

**File naming: `NN - <title>.<ext>`**, zero-padded to two digits (three past 99),
matching the `key` the API path already writes (`models.py:31`). Filename sort
must equal play order — that is the only property that matters, and it is robust
to every ordering behaviour the website might have.

### 2.4 Formats and sizes — what the folder is allowed to contain

**Verified:** the app does **not** transcode local files. `AudioFileAdapter.fetch`
(`sources/audiofile.py:26-61`) is a `shutil.copy2` + ffprobe + tag read;
`normalize_to_mp3()` (`normalize.py:155-186`) is dead code whose only caller is
`tests/test_audio_images_labels.py:26`. `SUPPORTED_EXT`
(`sources/audiofile.py:14`) is:

```python
{".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".mp4", ".opus"}
```

— including `.mp4`, a **video container**. YouTube sources are always `.mp3`
(`youtube.py:44`, `:150`). So a folder can hold any of eight extensions, and
Yoto's API tolerates that only because Yoto transcodes server-side. A web upload
form has no such obligation.

> **The folder contains only files Yoto's website will accept, at a size it will
> accept. Anything outside `{".mp3", ".m4a", ".aac"}` is written as a 192 kbps
> MP3 copy instead, automatically, and the panel and the sheet each say so in one
> sentence.**

Concretely: `.mp3`, `.m4a`, `.aac` copied; `.wav`, `.flac`, `.ogg`, `.opus`,
`.mp4` converted. The common YouTube path is always `.mp3` and is never touched.

**Re-encode the formats in the site's broad `accept` filter too**, rather than
trusting it. The trade is asymmetric and the asymmetry is the whole argument: a
pointless re-encode is the cheap failure; **a rejected upload in front of a
non-technical user, mid-task, on a website the app does not control, is the
expensive one.**

**Why convert rather than warn and hope** — four reasons, and deliberately not
all of them rest on Opus:

1. **She cannot act on a warning.** The only recovery would be: go back to step 1,
   remove the track, find an MP3 of it, start again. That is not a recovery for
   this audience, it is a dead end with a sentence attached —
   configuration-surface §2.2's *"never dead-end her"* forbids exactly this shape.
2. **The format is documented as unacceptable**, by three independent sources
   (§0). This is now the load-bearing reason, and it is the one that changed with
   the answer: before it, converting was a hedge against an unknown; now it is
   compliance with a documented set.
3. **Conversion is also what brings an oversized track under the 100 MB cap**
   (§0.1). This reason is **independent of anything Yoto documents about
   formats** — it is arithmetic on file sizes, and it would hold even if the
   uploader accepted WAV cheerfully. A 529 MB track is refused on size whatever
   the codec, and the app's duration-only splitter does not catch it.
4. **Little is lost that Yoto was going to keep.** Yoto transcodes server-side,
   so extra fidelity carried through the website is largely discarded seconds
   later. **This is now supporting rather than decisive** — §1.1's box explains
   why the exact output codec is observed rather than documented, and an argument
   leaning on it alone would be leaning on the softest evidence in the spec.
   Reasons 2 and 3 stand without it.
5. **It removes a decision she has no information to make** (`DESIGN.md` §8 —
   *"sensible defaults everywhere"*).

**The note is `.msg-box info`, never red, and never a new `.msg-box.warn`.**
Nothing failed. configuration-surface `tokens.md` §1 deliberately refused a warn
variant (*"a variant that can only be used incorrectly is a trap"*) and this is
not the amendment that overturns it.

#### The app acts on format and advises on size

Conversion fixes format, and fixes size for everything it touches. One real gap
remains: **a file already in the copy-as-is set that is over a limit anyway** — a
50-minute MP3 at 320 kbps is ~120 MB and is copied untouched.

> **Decision: convert on format, advise on size. Never silently re-encode an MP3
> to make it smaller.**

This is configuration-surface §13.2's two-tier discipline — *a hard rule that
acts, a soft rule that advises* — applied to a new pair, and the boundary sits in
the same place for the same reason:

| | Format | Size |
| --- | --- | --- |
| Evidence | Three sources agree; a wrong-format file is **certainly** refused | One support page; a third party's current policy |
| Cost of acting wrongly | A pointless re-encode | **Her audio is quietly made worse** |
| Verdict | **Act** | **Advise**, naming the actual figure |

**The three card ceilings get the same treatment** — 100 tracks, 500 MB, 5 hours.
The app knows all three the moment the folder is written; each gets one sentence
naming the real figure against the limit, plus **one** shared closing sentence
carrying the only real recovery: *make two shorter cards instead of one.* Strings
in `copy.md` §5.9; the recovery is factored out because at ~192 kbps the 500 MB
and 5-hour ceilings are the same card and would otherwise read as two problems.

**These ceilings apply to the send path too and it does not surface them
either.** Pre-existing gap, out of scope (§6.3) — but the export path is where a
user will now find out, which is a small argument for the send path borrowing
these strings later.

#### Two inputs deliberately not used

Recorded so nobody "improves" the rule with either.

- **Yoto's card-content schema `format` enum**
  (`yoto.dev/reference/card-content-schema/`: `mp3`, `aac`, `alac`, `flac`,
  `pcm_s16le`, `opus`, `ogg`, `x-m4a`, `wav`, `aiff`, `mpeg`) is **track metadata
  on a card object**, covering streaming tracks that point at arbitrary external
  URLs. It describes what a card can *reference*, not what the MYO uploader will
  *ingest*. **It must not widen the copy-as-is set by a single extension.**
- **The removed Opus support article is not evidence against §1.1.** It predates
  the repo's own live capture and describes a migration it says did not apply to
  MYO. Stale, not contradictory — and §2.4's reasons are now ordered so that
  nothing decisive depends on it either way.

### 2.5 Icons and the card picture — designed around an unanswered question

> **Track pictures go in a `Track pictures\` subfolder, named to match their
> audio file. The sheet mentions them in one paragraph written to be true under
> both answers.**

The subfolder is what makes §0 question 2 non-blocking:

- If the site supports per-track pictures, they are one click away, matched 1:1
  by name.
- If it does not, she never opens the subfolder — and crucially they do **not**
  appear in the file-open dialog she uses to select the audio, where five loose
  16×16 PNGs would put a decoy beside every file she is trying to click.

**One picture per track, even when byte-identical.** `_resolve_icon`
(`app.py:618-628`) derives most cards' icons from the card picture, so on a
typical card all of them are the same image. De-duplicating breaks the 1:1 name
match that makes the folder usable without thought.

**`_resolve_icon` must be called, not reimplemented.** It is lazy and has a
filesystem side effect (`make_device_icon` writes `work/icon_<id>.png`), and it
is the reason a card saved to a folder carries the same pictures as the same card
sent to Yoto.

**`Card picture.png`** at the top level — a copy of `work/card_picture.png`
(`app.py:376`). Note that `draft.picture_path` is **not** passed to
`send_to_yoto()` at all; it reaches Yoto only as the source image for 16×16
icons. So this is genuinely new capability, not a port (§4.2).

### 2.6 The instruction sheet is the feature

> **A single self-contained `What to do next.html`, written into the folder, and
> also openable from a button in the app.**

A folder of correctly-named files is not the deliverable. **A user who ends up
with a working card is**, and the distance between those two things is entirely
covered by instructions she has never been given.

The medium follows from **where she is standing when she needs it**: in a
browser, at Yoto's site, with an Explorer window open, and *not* looking at Yoto
Maker. That kills an on-screen-only panel outright. `README.txt` was rejected
(Notepad, no link, no picture, reads as a developer artifact); a PDF was rejected
(puts a viewer between her and a link she should click, and means reportlab
layout for a page of text).

Four hard requirements:

1. **Generated from what actually landed on disk, never from the draft.** On a
   partial run a draft-derived sheet lists files that are not there, and she
   uploads a card with a hole in it. The on-screen string *"The page in the
   folder lists what's actually there."* (`copy.md` §5.6) is the readable form of
   this invariant — **if it stops being true, that string must change.**
2. **Self-contained.** Inline `<style>`, no web font, no script, **card picture
   embedded rather than linked** (a relative `<img>` works from the folder and
   breaks when the same file is served over `http://`), and nothing that needs
   the app running. She may open it a week later on another computer.
3. **It carries her actual card name, her actual track titles, her actual file
   names in order** — that specificity is most of its value.
4. **It ends at tapping the blank card in the Yoto app.** Not at "press Save on
   the website". This is the manual step that exists on both paths and that no
   third-party app can do (`SETUP-YOTO-CONNECTION.md:100-104`), and omitting it
   is the single most likely way this feature fails a real user: a correct
   upload, a blank card, and no idea why. The wording is lifted from
   `INSTALL-FOR-MOM.md:76-77` on purpose.

Full text verbatim: `copy.md` §6. Layout: `mockups/instruction-sheet.md`.

### 2.7 Getting her to the folder

**Two buttons in `.done-actions`, the construction step 4 already uses for the
label** (`index.html:222-225`):

| Order | Label |
| --- | --- |
| `.btn primary` | `📄 What to do next` |
| `.btn` | `📂 Open the folder` |

**The instructions are primary and the folder is secondary — deliberately
inverted.** A user who opens the folder first meets a pile of files and no basis
for a decision; a user who reads the page first is told to open the folder as
step 3 of 6.

**`📄 What to do next`** is an `<a target="_blank" rel="noopener">` whose `href`
the job result supplies with a `?t=` cache-buster — byte-for-byte the pattern
`#labelOpen` uses (`app.js:2011-2022`). The user has already learned this
interaction in step 4.

**`📂 Open the folder` needs a new server capability**, and it is the one
genuinely new mechanism in the feature. Verified: **zero occurrences** of
`os.startfile`, `explorer`, `xdg-open` or `open -R` anywhere in the repository.

- A `file:///` link **cannot** do it — browsers silently refuse `file://`
  navigation from an `http://` page. Must not be shipped, must not be "tried
  first".
- A ZIP download cannot either — it lands in Downloads, and unzipping is exactly
  the file management `DESIGN.md` §2 promises she never faces.
- **So the server opens it**, which is configuration-surface §7.8's argument
  unchanged: the app binds to `127.0.0.1` (`config.py:111`) with no
  authentication, so *"the browser, the server, the OS account and the person are
  all the same."*

> **Safety property, and it is a design requirement rather than an implementation
> detail: the route reveals the folder the server last wrote, remembered
> server-side. The browser must not be able to name a path.** Even on loopback,
> handing an arbitrary caller-supplied string to the shell is a foot-gun with no
> upside, and the UI never needs it.

**It must degrade.** If reveal is unavailable, the button is **omitted, never
disabled** (configuration-surface §3.5.2, §13.5) and the full path is appended to
the result box in `.mono-value`.

`os.startfile` is stdlib and needs no PyInstaller hook — confirm in the frozen
`.exe` rather than take it on trust.

### 2.8 States

| State | Treatment |
| --- | --- |
| **Empty** (no tracks / no name) | Button **never disabled**; pressing it produces the explanation (configuration-surface §13.5). Two refusals worded as near-copies of the send path's — `copy.md` §3. |
| **Working** | `.progress` + `role="status"`, **per-track** messages. Not a single "Saving…" — `index.html:102-106` already argues why. |
| **Success** | `.msg-box ok` naming the folder **in words**, then optional `.msg-box info` notes, then the two buttons. Reading order is importance order; the actions come last. |
| **Notes** | Up to **five** paragraphs in one `.msg-box info`, fixed order: split → converted → track over 100 MB → card over 500 MB / 5 hours → card over 100 tracks, then one shared recovery sentence if any card ceiling fired. Advisory, never blocking. Box omitted entirely when nothing fired. `copy.md` §5.9, `overview.md` §10.3. |
| **Partial** | Green box with the real count (`4 of your 5`, no 🎉) **and** a red box naming the failed tracks. The sheet lists only what landed. Same shape the multi-file add already produces (`RELEASE_NOTES.md:39-46`). |
| **Total failure** | Red box only, cause-specific line, and **the folder that was created is removed.** A folder that exists but is wrong is worse than none — she will find it and use it. |
| **Pressed twice** | `(2)`, named in the result box. No warning, no extra sentence. |

**No Cancel button, and this is a decision.** `jobs.py` has **no cancellation**;
the `#addCancel` precedent (`index.html:108`) aborts a frontend `fetch` on the
*synchronous* file-upload path and has no equivalent for a job. Specifying one
would require new job-runner capability — an Architect decision — for a job that
is mostly local file copying. Revisit if UAT finds cards where the copy takes
long enough to want a way out.

### 2.9 One shipped string becomes false and must be corrected

`index.html:173`:

| | String |
| --- | --- |
| Shipped | `You'll need to connect your Yoto account first.` |
| **New** | `To send cards straight to your Yoto, connect your account first.` |

Once saving exists, connecting is a prerequisite for **sending from the app**,
not for finishing a card. A string that no longer matches what the screen can do,
sitting in front of the user who needs the other answer, is the defect
configuration-surface §12.3 recorded and named.

**It does not advertise the alternative** — that would bury the connect intent,
which is still the right first answer for most people. The save button's caption
twelve pixels below already says *"You don't need to be signed in for this."*

---

## 3. Backend implications — Planner must scope these

Design-relevant only; shapes and mechanisms are Planner's and Architect's.

**3.1 A new job, forking `send_to_yoto()` above its connection check.**
`app.py:631-661` assembles a complete, network-free description of the card at
lines 643-647 (`list[TrackInput]` + `card_name`). Export needs the two guards at
634-638 and **not** the one at 640. The track list, icons and card name must be
produced by the **same code** as the send path, so that a card saved and the same
card sent are the same card.

**3.2 Use the existing job runner.** `Job.view()` (`jobs.py:18-37`) and
`pollJob()` (`app.js:80-89`, 500ms) are sufficient and already have three call
sites. Copying a multi-hundred-megabyte audiobook will block, so this must not be
synchronous the way `POST /api/label` is.

**3.3 The job result carries everything the panel renders**, and the panel
reconstructs nothing in JS: the folder's display name, its full path, the number
of tracks written, the failures, whether anything was split, **which tracks were
converted**, **which tracks exceed 100 MB and by how much**, **the card's total
size, total duration and track count**, and the instruction page's URL. The label
precedent is `{"ok": true, "label_url": "/api/label.pdf"}` (`app.py:683`).

The three card totals must be measured **from the files as written** — after any
conversion. Testing the sources would report a ceiling breach the export itself
had just fixed (a 529 MB WAV becomes a ~72 MB MP3).

**3.4 A route serving the instruction page**, so `📄 What to do next` can be a
plain anchor. Same shape as `GET /api/label.pdf`.

**3.5 A route opening the folder** — §2.7's safety property applies.

**3.6 `/api/status` gains one field** if §6.2's Settings row ships: the root
saved-files folder, alongside the existing `config.data_dir` (`app.py:154`),
which is already sent to the browser as a string.

---

## 4. Corrections to the brief

Both were found while checking the code and both change the design.

### 4.1 Splitting is already done before export sees the draft

The brief states export must carry track splitting through. **It is already
carried, upstream.** `split_audio` has exactly one production caller, in
`_add_result_as_tracks` at **add time** (`app.py:235`), and each returned part
becomes its own `Track` with a title suffixed `(part N)` (`app.py:243`).

Three consequences, all simplifying:

- **Export never calls `split_audio`.** It writes what the draft holds.
- **The "splitting can be slow" progress state does not exist.**
- The user still has to be told (`copy.md` §5.3) — on the send path the split is
  invisible, but here she will *see* two files where she added one, and an
  unexplained extra file reads as a bug with an obvious wrong recovery (deleting
  one).

*(For anyone reading file names later: three numbering conventions coexist in
this codebase — the on-disk part suffix `_part000` is 0-based 3-digit, the
user-visible title `(part 1)` is 1-based, and the API `key` `"01"` is 1-based
2-digit. Export uses the card's track order, matching `key`.)*

### 4.2 The card picture never reaches Yoto as a card picture

`draft.picture_path` is **not** passed to `send_to_yoto()`. It reaches Yoto only
indirectly, as the source image from which `_resolve_icon` derives 16×16 track
icons. So `Card picture.png` in the folder is new capability, not a port — which
strengthens §2.5's decision to include it, and means §0 question 3 has no in-repo
precedent to lean on.

---

## 5. What is deliberately not changing

**The send path.** `#sendBtn`, `#sendProgress`, `#sendError`, `#sendDone`,
`connectYoto()`, `sendToYoto()`, `POST /api/send`, `YotoClient` — none of it is
touched. This feature appends; it does not fork.

**Step 3's title and hint.** *"Send it to your Yoto"* names the goal, not the
mechanism, and stays true — so `INSTALL-FOR-MOM.md`'s step numbering and
`SETUP-YOTO-CONNECTION.md`'s instructions are unaffected.

**`#advRow`, the footer Settings link, the header pill.** Unchanged in position,
copy and behaviour. Everything configuration-surface §12 settled stays settled.

**The `.setting` primitive and `styles.css`.** No slot added, no rule edited, no
token introduced.

---

## 6. Out of scope, recorded rather than dropped

### 6.1 A persistent "always save to a folder" preference — **decided: no**

> **Decided by Mark, 2026-09-05: per-card choice only, no setting.** This
> confirms what §2.1 specifies and closes the last open question that needed
> direction rather than investigation.

This is the reading of "a separate mode" that this spec did **not** take, and
someone will ask.

The case is real: a user who is never going to sign in sees the connect box, a
dead `🚀 Send to Yoto` and a live save button on every card, forever. A
preference could turn step 3 into "save the files" outright.

Out of scope because (a) the brief scoped Settings out, (b) it is not what makes
the feature work — the per-card action is the primitive and a preference would
only change which button is emphasised, and (c) it needs its own decision about
what happens to the connection UI, which is a bigger question than this PR.

**Declined outright, not deferred.** If it is ever revived it is `.setting` #4
and it costs no CSS — but **it must not be built as a second mechanism.** It
would reorder the two controls §2.1 already specifies, and nothing more.

### 6.2 A row in Settings' help section

`Where saved files go` → `C:\Users\…\Documents\Yoto Maker`. The **one** Settings
change this package proposes: one row appended to setting 3
(`index.html:397-441`), zero CSS, and it answers the exact question that section
exists to answer on the phone (configuration-surface §13.4). Optional — the
success panel already shows the path, and this row serves only the *later* call.
Ship it if Planner has room. Copy: `copy.md` §7.

### 6.3 Everything else

- **The label PDF in the folder.** Tempting; rejected. The label is step 4's
  action and may never have been made, and coupling them lets one step's failure
  reach into another's deliverable.
- **Cleaning up old folders.** They are hers. The app does not delete her files.
- **A combined "save and send".** Not asked for, and it reintroduces the "always
  export then upload" shape that was explicitly rejected.
- **Cancelling a save.** §2.8 — needs job-runner support.
- **`work/`'s lack of cleanup.** Pre-existing, unrelated, and this feature
  deliberately writes nowhere near it.

---

## 7. Why this is one PR

Every part of it is useless without the others:

- The folder without the sheet is a pile of files and a stuck user — §2.6 is not
  a follow-up, it *is* the feature.
- The sheet without the reveal button still works (§2.7 degrades), but the button
  is four lines of Python once the route exists.
- The UI block without the job has nothing to press.
- The one-string edit (§2.9) is a correctness fix the feature causes; shipping
  the feature without it ships a false string.

The only genuinely separable piece is §6.2's Settings row, and it is one row.

**Docs to update in the same PR** — both go stale the moment this ships, and both
are read by the least technical users:

- **`docs/INSTALL-FOR-MOM.md`**, step 3️⃣ — needs a short note that there is
  another way, written in the register that file establishes. It currently says
  *"even without connecting, adding audio, pictures, and printing labels all
  work"* (`:83`), which is now incomplete.
- **`docs/RELEASE_NOTES.md`** — a user-facing entry.
- **`docs/SETUP-YOTO-CONNECTION.md`** — no change needed; verify.

---

## 8. Acceptance criteria

1. **A user who has never signed in can get from audio to a folder of files
   without meeting the sign-in wall as a blocker.** Verified with no saved
   sign-in, using only what is on screen.
2. **Files sorted by name — in Windows Explorer and in a browser's file-open
   dialog — are in the order the card should play**, including when a long track
   was split.
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
   "export" appears nowhere the user can see.**
7. **The folder is never overwritten and its real path is never guessed.**
   Verified by saving the same card twice, and on a machine whose Documents
   folder is redirected to OneDrive.
8. **A card saved to a folder and the same card sent to Yoto contain the same
   tracks, in the same order, with the same pictures.** This is what stops the
   two paths drifting into two products.
9. **A failed run leaves no folder behind.** This is what makes *"Nothing was
   saved, and nothing on this card has changed."* true; if the ordering changes,
   the string must change with it.
10. **`styles.css` is unmodified.** If the PR touches it, something in §2 was
    reinterpreted and should come back to Designer.
11. **A card mixing `.mp3`, `.m4a` and `.flac` produces a folder holding the
    first two untouched and an MP3 copy of the third**, and the panel names only
    the third. Verified with one card and three source files. The `.m4a` staying
    put is the specific thing to check — it is the case `copy.md` §5.4's amended
    wording exists for.
12. **A 50-minute source at the splitter's bound lands under 100 MB after
    conversion.** This is §0.1's property and it is what makes the size cap
    solved-by-construction rather than advisory for converted files. A 192 kbps
    target gives ~72 MB; anything above ~265 kbps breaks it.
13. **The advisories fire on the real figures and never block.** Verified with a
    card over 500 MB: the folder is complete, both buttons are live, the note is
    `.msg-box info`, and the recovery sentence appears **once** even though two
    ceilings fired.

---

## 9. Handoff

Package: [`docs/design-handoffs/export-only-mode/`](../../design-handoffs/export-only-mode/)

| File | Contents |
| --- | --- |
| `overview.md` | The decisions, the rejected alternatives, the backend implications, the open questions |
| `copy.md` | Every user-visible string verbatim, including the full instruction-sheet text |
| `interactions.md` | Markup contract, state machine, focus, announcements, keyboard, responsive |
| `mockups/step-3.md` | Every card-view state, ASCII |
| `mockups/the-folder.md` | Explorer and file-open-dialog views |
| `mockups/instruction-sheet.md` | The sheet's layout, visual treatment and conditional sections |
| *`tokens.md`* | **Absent, deliberately.** Nothing new is introduced. |

**The blocking check is done, and the spec is approved (2026-09-05).** Planner
has picked it up: the implementation plan is
[`plans/2026-09-05-export-only-mode.md`](../plans/2026-09-05-export-only-mode.md)
and it is queue item 19.

Two things Planner should carry forward rather than rediscover:

- **§0's format evidence is documentation, not tested behaviour.** It is good
  enough to build on and it is not good enough to cite as measured. §0.2's
  one-upload test is worth doing at some point; it is not worth waiting for.
- **§2.4's act-on-format / advise-on-size split is a decision, not an
  inconsistency.** A reviewer who notices that the app re-encodes a FLAC but only
  warns about a 120 MB MP3 has found the design, not a bug.
