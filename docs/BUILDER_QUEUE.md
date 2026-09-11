# Builder queue

**Last updated:** 2026-09-11 by Builder — **ISSUE #31 IS CONFIRMED FIXED ON HARDWARE.
`overlayLabel` gates the player's chapter-browse UI — observed, not inferred.**

On a **physical Yoto player** on **2026-09-11**, on a multi-chapter card this arc had
labelled: **the chapter list appears when the right-hand knob is twisted, and chapters are
selectable by pressing it.** Tested by the maintainer's daughter. **Issue #31 was closed by the
maintainer** (`mmackelprang`, 2026-09-11T23:21Z, `state_reason: completed`) — **Builder did not
close it**, by instruction.

**Which card is answered by the outcome, not by testimony.** Only a multi-chapter labelled
card can produce a chapter list at all, so it was `1WCvI` (5 chapters) or `ezeaM` (18
chapters); **`gzP2B` (1 chapter) is excluded by the result itself** — there is nothing for it
to browse under any hypothesis. Nothing below depends on which of the two it was.

⚠ **What is proven is narrow, and the two things it is NOT are the easy over-reads:**

| Claim | Status |
| --- | --- |
| The player renders a browse list from `overlayLabel`, and selection from that list works | ✅ **PROVEN on hardware, 2026-09-11** |
| The offline-download behaviour changed | ❌ **NOT proven and NOT tested.** Always a separate question on the same checklist; needs wi-fi off and the download-cloud icon watched |
| The self-update swap-and-relaunch step works | ❌ **NOT proven.** Only the update *offer* was ever verified, and `can_self_update` was false from source |

**This cycle is bookkeeping only — documentation, no source. Suite stays 437.** Corrected in
it: the **published** v0.1.14 release notes (`gh release edit`), `docs/RELEASE_NOTES.md`
(the chapter-browsing entry moves out of *❓ Not verified* into *🔒 What's verified*), this
banner, item 29's row, and the ADR.

**In the ADR the ~75–80% confidence figure and the *"no Yoto document says so"* caveat are
KEPT, with dated confirmations beside them rather than edits over them.** The record of
having been appropriately uncertain is *why* §8's backout plan exists and *why* §3.7 split
the commits the way it did. **§8 stays and `--no-overlay-labels` stays — the flag is NOT
removed**; their justification is now historical rather than live, and §8 says so in its own
first paragraph.

Previously: 2026-09-10 by Builder — **item 29 is COMPLETE and v0.1.14 is RELEASED
AND VERIFIED. All three live cards carry `overlayLabel`.**

**The release is verified in the direction that matters, and all three checks are green:**

| Check | Result |
| --- | --- |
| Published asset == local build | **Byte-for-byte identical.** sha256 `720fede64a32f0987140b3ef93b88f9a605251560037907f8ffdb7b0c9b8cc4d` on both, 127,022,603 bytes, and `cmp` found no differing byte. **Size alone is not a hash** — the asset was downloaded and hashed |
| Frozen binary reports its OWN version | **`0.1.14`**, read from `/api/status` of the **running `.exe`**, never inferred from the source string. That is the v0.1.12 trap (which shipped a stale artifact reporting 0.1.11) |
| v0.1.13 client is offered v0.1.14 | **Yes** — `update_available: true`, `latest: "0.1.14"`, and the offered `browser_download_url` answers **206** with `content-range: bytes 0-1048575/127022603` and an `MZ` header. **No `YOTO_LATEST_VERSION`** — that override short-circuits at `updater.py:80` and would test the override instead of the release |
| Negative control | **A v0.1.14 client is offered nothing** (`update_available: false`), so the offer above is not vacuous |

**Three live cards are labelled, and each apply reported `verify ok`:** `gzP2B` (1 chapter,
2 changes), `1WCvI` (5 chapters, 10 changes) and **`ezeaM`** — *"BFG Maybe Fixed"*, 18
chapters, 36 changes. `7FcVe` also reported `verify ok` before it began 404-ing, but it is
an **abandoned pre-re-make card** and is not part of the live set. Idempotency is confirmed
on live data: `ezeaM` now reports `already correct (18 track(s), nothing to change)` with
per-chapter notes like `already: chapter overlayLabel '15' - left alone`.

⚠ **`ezeaM` was applied by the MAINTAINER running `--apply` by hand, because the agent's
own invocation was refused by the permission classifier** — as was `gh release create`.
**So the agent-driven apply path is NOT currently exercisable end to end**, and neither is
the publish. Worth knowing before anyone plans a cycle that assumes either: the code,
the gates and the read-only diagnosis are all agent-runnable, but the two writes that
touch the outside world are not.

**Two real questions were closed by the live runs, and both were previously open:**

1. ✅ **Yoto PERSISTS a client-supplied `overlayLabel`.** Four applies, `verify ok` each —
   and `verify ok` is exactly the assertion that the field was not dropped, because a
   silently-stripped *declared* field now fires `unexpectedly REMOVED` → `verify-failed`.
   Under the old format-only invariant that same case would have reported `applied`.
2. ✅ **`POST /content` REPLACES rather than merges** (ADR open question 3). Proved by
   driving the full apply → rollback → re-apply loop on `gzP2B`: after restoring the
   pre-write backup the label was **gone**, and `_diff_paths` reported **no difference at
   all** against that backup. **So ADR §3.5's rollback tolerance is correct, pinned by
   tests, and dead code against today's API.** It ships as insurance, not as a live path.

✅✅ **ISSUE #31 IS CONFIRMED FIXED — the warning that stood here is DISCHARGED, 2026-09-11.**
This paragraph previously read *"ISSUE #31 IS NOT FIXED, AND MUST NOT BE CLOSED"*, on the
grounds that the field was only *sent* and *stored*, that no Yoto document said the player
draws a browse list from it, and that **the hardware test had not happened**. **It has now
happened**, on 2026-09-11, and the player draws the list: see the banner at the top of this
file. The warning was right to stand for as long as it did, and it is being discharged rather
than ignored — **the maintainer closed the issue himself on 2026-09-11.** The knob question reached the
tester via `HOW-TO-TEST-THE-CARDS.md`'s **Part 2b** (on `1WCvI`, noting that `gzP2B` cannot
answer it); that file is **untracked and stays untouched** by instruction.

Previously: 2026-09-10 by Builder — **item 29 is MERGED as
[PR #34](https://github.com/mmackelprang/yoto-maker/pull/34) (`47829d4`): `overlayLabel`
is now sent on the create path and written by the repair path on a declared change-set.
Suite 411 → 437.** ⚠ **The v0.1.14 RELEASE IS PARTIALLY CUT.** The version is bumped on `main`, the tag
**`v0.1.14` exists and is pushed** (→ `a09c656`), and the frozen build exists and was
verified to report **its own** version `0.1.14` from `/api/status` of the running `.exe`
(127,022,603 bytes, sha256 `720fede6…c9b8cc4d`) — not inferred from the source string,
which is the v0.1.12 trap. **`gh release create` was REFUSED by the permission system, so
the release is NOT published and `/releases/latest` still returns v0.1.13.** The
update-path verification that needs a published asset — a v0.1.13 client offered v0.1.14
with a working download URL, and the v0.1.14 negative control — is therefore **NOT DONE**.
⚠ **Do not substitute `YOTO_LATEST_VERSION` for it**: that override short-circuits the
API call at `updater.py:80` and tests the override instead of the release.

**All three live cards were applied, and two of the three are healthy and confirmed.**
`gzP2B` → `made 2 change(s); POST ok; verify ok`; `1WCvI` → `10 change(s)`, verify ok;
`7FcVe` → `36 change(s)`, verify ok. Labels re-read independently off the live API
afterwards: `gzP2B` and `1WCvI` both carry `1..N` at chapter **and** track level,
unpadded, all tracks still `opus`. Backups (all on disk, pre-POST):

| Card | Backup |
| --- | --- |
| `gzP2B` | `%LOCALAPPDATA%\YotoMaker\repair-backups\gzP2B-20260910-173609.json` (and `-173712` from the re-apply) |
| `1WCvI` | `%LOCALAPPDATA%\YotoMaker\repair-backups\1WCvI-20260910-173732.json` |
| `7FcVe` | `%LOCALAPPDATA%\YotoMaker\repair-backups\7FcVe-20260910-173746.json` |

⚠⚠ **`7FcVe` ("The BFG") now returns 404 on `GET /card/7FcVe`, and this is UNEXPLAINED.
No further writes were made and no workaround was improvised — the protocol says stop
and report, and that is what happened.** The facts, separated from the inference:

- **Before the write** it answered 200 with 18 chapters — but it was **already absent
  from `GET /content/mine`**, which lists 32 cards and never contained it. That anomaly
  **pre-dates this cycle.**
- **The write itself reported `POST ok; verify ok`**, which means the verify's re-GET
  *succeeded* and the body matched `before + the declared change-set` exactly. So the
  card existed, and was correct, immediately after the POST.
- **Afterwards** `GET /card/7FcVe` 404s — persistently, 4 retries plus later probes.
  (`GET /content/7FcVe` returns 403 for *every* card including healthy ones — a missing
  `user:content` scope — so it is no evidence either way.)
- **Nothing was duplicated and nothing else was lost.** The account listing is
  **byte-identical** before and after: 32 cards, no additions, no removals.
- **A plausible reading, NOT established:** a card readable by id but absent from
  `/content/mine` is what a **deleted-but-not-yet-reaped** item looks like, and
  `ezeaM "BFG Maybe Fixed"` (18 chapters, created 2026-07-22T13:25) suggests the BFG was
  re-made and the original deleted in the Yoto app back in July. On that reading `7FcVe`
  was already a tombstone and our write touched a dead item. **That is a hypothesis, and
  it is exactly the kind of reasoning this arc has already been burned by — do not treat
  it as settled.**
- **Rollback was deliberately NOT attempted on `7FcVe`.** `rollback_from_backup` POSTs
  and then re-GETs; the re-GET would 404 and raise, and worse, a `POST /content` carrying
  a `cardId` the API now 404s could plausibly **create a new card** — a duplicate in the
  account, the one outcome this whole design exists to avoid. The backup is safe on disk,
  so the maintainer keeps every option. **This needs a decision, not a guess.**

✅ **THE `7FcVe` MYSTERY IS SOLVED, AND THE CORRECTION IS RECORDED HERE BECAUSE THE
STALE ID CAME FROM UNTRACKED PROSE.** **The BFG card is `ezeaM`** — titled *"BFG Maybe
Fixed"*, 18 chapters, created **2026-07-22T13:25:23Z**, which is *hours after* the July
repair runs at 08:54–08:56. **`7FcVe` is a dead pre-re-make card**: abandoned that same
afternoon, absent from `GET /content/mine`, and now 404 on `GET /card`. It was never a
live card at any point in this arc.

⚠ **The stale ID propagated through all four agents on this arc because it lived only in
untracked `SESSION_STATE.md`**, written before the re-make and never updated — so nothing
reviewed it, no clone carried it, and every document downstream inherited it: the ADR, the
plan, the queue rows and this Builder's briefing all name `7FcVe`. **This is the second
time in two items that untracked prose has caused a real defect** (the first was Plan Task
1.5's `PYTHONUTF8` note). **The BFG's repair is therefore still OUTSTANDING** — `ezeaM`
dry-runs as `WOULD make 36 change(s) across 18 track(s)`.

✅ **ADR open question 3 is CLOSED, and it was answered for free by the rollback proof:
`POST /content` REPLACES, it does not merge.** The rollback on `gzP2B` was driven end to
end — apply, capture the live labelled state, restore from the fresh backup, re-read —
and the label was **gone**, with `_diff_paths` reporting **no difference at all** against
the pre-write backup on every compared field. Then re-applied. **So §3.5's rollback
tolerance never fires against the real API.** It ships as unexercised insurance; it is
correct, it is pinned by tests, and it is now known to be dead code on today's server
behaviour. *"A backup exists"* and *"restore works"* were different claims and only one
had ever been tested — now both are.

**Blocker 1 was real, and the proof is live rather than argued.** Before the write all
three cards reported `WOULD make N change(s)` (2/1, 10/5, 36/18 — exactly the plan's
predicted counts), and **the same three under `--no-overlay-labels` reported
`already correct (N track(s), nothing to change)`**. That pair is the before/after
demonstration that without the second decision axis the widened repair writes nothing to
every card that needs it.

⚠ **Yoto demonstrably PERSISTS a client-supplied `overlayLabel`** — `verify ok` on all
three is exactly the assertion that it was not dropped, since a silently-stripped
declared field now fires `unexpectedly REMOVED`. **The knob hypothesis is still
unverified and only a physical player can close it.**

⚠ **`HOW-TO-TEST-THE-CARDS.md` does not ask the knob question at all.** It predates
issue #31, still tells the tester the version *"should say 0.1.13"*, and is
**untracked** — so nothing in the repo will remind anyone. The one person who can
falsify this hypothesis currently has no instruction to try it. **Not edited here:**
it is the maintainer's own note to his daughter, and Plan Task 1.5's lesson was that
editing untracked prose is not a fix.

**Pre-merge review found 1 HIGH + 2 MEDIUM + 1 LOW, all fixed; every finding was
reproduced before being fixed.** The HIGH was **a test this PR itself wrote that could
not fail**: the create/repair agreement test fed a *create-path* body to
`overlay_label_edits`, but the create path always writes a non-empty label, so `_is_set`
is true everywhere and the helper returns via its "already" branch **without ever
computing the expected value**. Making the repair side zero-pad — the exact disagreement
its own docstring claimed to catch — left it green, as did an off-by-one and a nesting
swap. **Three vacuous tests in three cycles now, all in this repo.** It was rewritten to
strip the labels and force recomputation of all 24 values. The two MEDIUMs were silent
missed-write paths: a filtered-vs-raw track-index mismatch that made `plan_card` drop a
required label edit, and `outcome` checking `empty` before `change_set` so a track-less
card lost pending chapter writes — **blocker 1's shape a second time.**

**Deferred LOW, logged:** `models.py:8`'s unused `field` import (pre-existing on `main`;
folding it into commit 1 would make ADR §8 lever 3's "reverts in ~3 lines" touch an
unrelated line). Item 30 untouched; **the `except (ValueError, OSError)` widening still
belongs to item 30 and was not done here.**

Previously: 2026-09-10 by Builder — **item 28 is MERGED as
[PR #33](https://github.com/mmackelprang/yoto-maker/pull/33): the repair CLI no
longer crashes on card text its console cannot encode.** The fix is
`reconfigure(errors="backslashreplace")` on `sys.stdout` and `sys.stderr`, called as
`main`'s first statement — **`errors` only, never `encoding`**, pinned by a test in
both directions. Suite **401 → 411**. Issue #31's exact command now completes with
**no `PYTHONUTF8`** on a piped stdout: exit 0, five track lines, 🤖 as
`\U0001f916`, no traceback. **No `--apply` was run** — item 28 is diagnosis-path only.

**The CLI output layer is now executed by a test for the first time in the project's
life**, and every test was proved to bite by mutation rather than by inspection:
neutering the guard fails **7 of 10**; forcing `encoding="utf-8"` fails **8 of 10**.

⚠ **Two of those mutations exposed defects the first draft shipped, and both are
worth remembering.** (1) Deleting the `sys.stderr` half of the guard left **all 8
tests green** — the half was pinned by nothing, in a file whose header argues nothing
in it is vacuous. (2) `assert ROBOT not in written` was **unfalsifiable**: `written`
came from `.decode("cp1252")` and no cp1252 byte decodes above U+2122, so the emoji
was unreachable by construction — while the line's own comment presented it as
evidence. **A test that cannot fail reads exactly like a test that passes.**

**And the PR broke its own line citations.** Inserting the 50-line guard above `main`
pushed everything inside `main` down by 50, so the docstring's load-bearing sentence
(*"`main` prints each card's result at `:831`"*) pointed at `client = YotoClient()`,
and two test-to-emit-site mappings pointed **into the new docstring that had
invalidated them**. Eight citations corrected; the twelve above the insertion point
were checked rather than assumed. Pre-merge review found all three MEDIUMs.

**The docstring's central justification was also false as first written.** It claimed
`errors=`-only *"cannot make any currently-working output worse"*. A redirected stdout
defaults to `surrogateescape`, **not** `strict`, so a **lone surrogate** emits as its
raw byte today and as an escape afterwards — and `json.loads` yields one for a
truncated high-half escape, which is the high half of U+1F916 itself. The trade is
still right; the recorded reason was not, in the one docstring whose purpose is to
prevent a fourth wrong fix.

**`516cbf7` did not regress — it was never the right fix, and this is now demonstrated
on live data rather than argued.** The account holds a genuinely non-ASCII title,
`Julie’s Library` (U+2019), and after this PR it still emits as cp1252 byte `0x92`
(verified with `od -c`), not as an escape. `backslashreplace` fires only for
characters the codec genuinely cannot represent — which is exactly why a literal
sweep over em-dashes and curly quotes could never have reached a 🤖 from Yoto's JSON.

**Plan Task 1.5 was dropped on the maintainer's instruction and it costs nothing.**
It asked for a one-line re-label at `SESSION_STATE.md:245`; that file is **untracked**,
so the edit would not survive a clone — the precise failure mode that produced this
bug report. The trap is already recorded in three tracked places: the plan, this row,
and the ADR at `:108-114`, which already says the env var became optional here.
`_make_console_safe`'s docstring now says it too.

**Plan row B4 is wrong.** It expects `--title "wild"` to produce the ambiguous-title
message at exit 2; on this account `"wild"` matches exactly **one** card, so it
resolves and dry-runs at exit 0. The real path was exercised with
`--title "the adventures of"` → exit 2, three candidates.

**Two LOWs deferred, logged rather than silently dropped:** `:760` has no non-ASCII
test (documentation gap — the fix is stream-level and covers all 12 print sites
uniformly), and **`except (ValueError, OSError)` is not a closed set** — a proxy
stream whose `reconfigure` has a different signature would raise `TypeError` and turn
a guard against a crash into a crash on line 1 of `main`. Not widened here because it
deviates from the plan's literal approved code and has **no reachable trigger** today
(pytest's `EncodedFile` is a `TextIOWrapper` subclass, colorama delegates to the
underlying stream, `codecs` writers and `StringIO` have no `reconfigure` at all).
**That one is for the maintainer, and it matters to item 30**, which reuses this helper.

**Item 29 is NOT claimed and stays 📋** — it carries the live-card write path and needs
a checkpoint before it starts. Item 30 untouched.

Previously: 2026-09-10 by Planner — **two rows filed for
[issue #31](https://github.com/mmackelprang/yoto-maker/issues/31) (the player's knob
brings up no chapter list): 28 (the repair CLI crashes *after* it has written to a
live card) and 29 (`overlayLabel` on a declared change-set).** Design basis is the
approved [ADR `2026-09-10-overlay-labels-and-the-declared-change-set.md`](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md);
the plan is
[`plans/2026-09-10-overlay-labels-and-the-declared-change-set.md`](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md).
**28 must land before 29's staged rollout** — its crash is at `repair.py:745`, which
`main` reaches at `:831`, *after* `repair_card` has POSTed at `:648`, and Wild Robot
(one of the three cards 29 repairs) carries a 🤖 in all five track titles.

⚠ **Two of the ADR's own claims are FALSIFIED, and the plan's §1 corrects them with
evidence.** §1.1, the opening ⚠ box, open question 1 and §4.2.3 argue the three cards
are still `mp3`, that no repair write ever landed, and that the feature may be
**inert**. The live read-only check says **all 24 tracks across all three cards are
`opus`** — so July's write landed and Yoto **does** persist a client-supplied `format`,
which is the mechanism `overlayLabel` depends on. The ADR misread a **pre-write**
backup as the post-write state, and misread the absence of an eleventh backup as
"nothing ran" when an `already` card returns at `:626` *before* `_write_backup` at
`:637`. **A Builder who reads the ADR's first screen and stops will build the wrong
thing.** That same evidence confirms **blocker 1 is real and not defensive**: all three
cards report *"already correct — nothing to do"*, so without the second decision axis
the widened repair is a silent no-op on every card that needs it.

**`516cbf7` ("ASCII-safe CLI output", July) did not regress — it was never the right
fix.** It swept em-dashes out of `repair.py`'s own **literals**; the crashing character
arrives from Yoto's JSON. **A second literal sweep would not fix it either**, and
`$env:PYTHONUTF8=1` — the only thing that has kept the tool completing — lives in two
prose lines and in no code.

**Item 30 filed in passing:** `yoto_maker/main.py:43`/`:74`/`:89` carry the same
literal exposure at a different entry point. Deliberately not folded into 28.

Previously: 2026-09-06 by Builder — **v0.1.13 is CUT AND PUBLISHED:
[the release](https://github.com/mmackelprang/yoto-maker/releases/tag/v0.1.13)
carries items 19 and 20, and both Shipped rows now read 🚢 v0.1.13.** The
published `YotoMaker.exe` was hash-matched against the local build
(`b5d5dab8…d295ba48`), the frozen binary was made to report its own version
(`0.1.13`, read from `/api/status` of the running exe rather than inferred from
the source string — the v0.1.12 cut shipped a stale artifact reporting 0.1.11),
and the save-to-a-folder path was exercised end to end in that frozen build.
**The update path is verified in the direction that matters:** a v0.1.12 client
is offered v0.1.13 with a working asset URL, and a v0.1.13 client is correctly
told it is up to date — the negative control, so the offer is not vacuous. The
whole suite is **401 passed** (this banner previously said 400).

⚠ **Released does not mean the offline-download defect is fixed.** Item 19 ships
a way *around* it. Nobody here has a physical player; a card playing in the
phone app is not evidence, since streaming works even on a malformed card.

**Item 20 was merged as
[PR #27](https://github.com/mmackelprang/yoto-maker/pull/27).** Designer's
ruling shipped verbatim: the per-track 413 **prints no number at all** and
**points at `📁 Save the files to a folder`**, and the generic 413 gains
configuration-surface §4d's recovery sentence, closing the app's only dead-end
error. **400 tests** (390 + 10 net). No version bump — zero files under
`server/static/` changed on the whole branch, so the `__ASSET_V__` cache key
does not move.

**Both gates were re-run against the ruled strings, and both cleared them.** The
copy gate — the same gate that blocked the previous draft as *NEEDS A REAL
DESIGNER PASS* — returned **SHIP WITH NIT**, having compared all three strings
against `copy.md` §10's blockquotes codepoint-by-codepoint. Pre-merge review
returned **0 HIGH / 0 MEDIUM**. The old MEDIUM did not come back, and the way it
could have is worth keeping written down: its guard asserted `"100 MB" not in
msg`, and **this ruling deletes that number**, so the guard would have gone
**vacuous and still passed** while `too_big` leaked into the 401 branch. It now
asserts on the pointer itself, over six failure kinds, plus an end-to-end 401.
**A string change can silently disarm the test that guarded the string.**

**One row filed out of the copy gate's MEDIUM: 27.** `interactions.md` §4b.4's
table asserts that a send which can reach a 413 *cannot coexist with a visible
`#connectWarn`*. **That is false**, and it was confirmed in the live app, not
argued: `connected` is token-presence only (`auth.py:246`) and
`renderConnectWarn()` triggers on the verdict alone (`app.js:325`), so nothing
couples them. **The shipped string is unaffected and stays** — `#exportRow` is
still visible and still below, so *"below"* is still true; what is falsified is
one sentence of the ruling's *reasoning*. Builder did not fix it: the only fixes
touch the send path's state machine, which §4b.3 forbids, and narrowing the
claim is Designer's call. Item 20's tests were narrowed to assert only what they
prove.

**Plan §8's live probe is still NOT run** — it needs the maintainer's
authenticated Yoto account. **Item 21 stays open**, and §10.2's ruling means no
outcome of that probe requires a copy change on the send path: only the number
could have been falsified, and it is no longer printed.

Previously: 2026-09-06 by Planner — **two rows filed out of Designer's
item 20 ruling: 25 (`#sendError` is announced to nobody, and now holds the app's
only cross-path recovery pointer) and 26 (`_friendly_http`'s other four
sentences are owned by no handoff package).**

Designer surfaced both while ruling item 20's blocked 413 string, judged both
out of scope for a string fix, and **deliberately did not file them** —
`copy.md` §10.4's boxed note says adopting the `_friendly_http` family *"is
worth a queue row and is **not** done here"*, and `interactions.md` §11 item 3
was **re-weighted rather than reopened**. These are those rows. **25 is MEDIUM,
26 is LOW-MEDIUM**, and in both cases the obvious priority read is the wrong one,
so the reasoning is written into each row rather than left to be re-derived.

**Item 20's blocked string is ruled, and Builder is implementing it as this is
written.** [PR #27](https://github.com/mmackelprang/yoto-maker/pull/27) is open
on `fix/send-path-size-limit`, carrying Designer's ruling (`copy.md` §10,
`interactions.md` §4b, a redrawn `mockups/step-3.md` §3) and the implementation
of it. **Both rows below are written against the world PR #27 creates** — §10
and §4b do not exist on `main` yet, so a reader on `main` who follows those
links and finds nothing has found the merge order, not a broken link. Item 26
additionally **cannot start** until §10 is on `main`: it adopts the rest of the
family *around* §10, and §10 is the anchor.

**Stale line-number citations in the handoff package: found, already fixed, and
recorded here only so a future pass can decide whether to sweep.** Designer
found `$("#sendBtn").disabled = !connected;` cited as `app.js:288` in **seven**
places across `interactions.md` §1.1, `mockups/step-3.md` §2 and `overview.md` —
item 19's own PR had moved that statement to **382**. Six were corrected in
`196cdd0` and the seventh in `c8b5dae`, in a commit kept separate precisely so
it stays reviewable. **Do not re-fix it.** It is noted because it is the
**second** derived-artifact drift in this package in two days — the entry below
fixed `mockups/step-3.md` §8/§8a drawing the two boxes in the wrong order — and
two findings of the same shape in two days is the point at which a sweep starts
to look cheaper than a third spot fix. **The scope was checked rather than
assumed, and it argues against panic:** four other `app.js` citations in
`interactions.md` (`55`, `2050`, `2081`, `2082`) and `index.html:195` were
spot-checked against the tree and are all **correct**, so the seven were *one
moved statement cited seven times*, not broad rot. A one-off pass over every
`file:NNN` citation under `docs/design-handoffs/` would settle it in minutes.
**Not filed as a row**, because the real question is whether such a check should
keep running, and nobody has asked for that yet.
Previously: 2026-09-06 by Designer — **item 20's blocker is RULED and
cleared.** [PR #27](https://github.com/mmackelprang/yoto-maker/pull/27) is still
open and still unmerged: Builder implements the ruling, re-runs the copy gate
against it, and merges.

**The ruling lives in the handoff, not in this file.**
[`design-handoffs/export-only-mode/copy.md`](design-handoffs/export-only-mode/copy.md)
**§10** is the authority on both strings — a new ratified section, because the
send path's size refusal now **points at `📁 Save the files to a folder`**, and a
string that quotes that button's label has to be findable from the package that
owns the label. [`interactions.md`](design-handoffs/export-only-mode/interactions.md)
**§4b** says when the pointer appears and where it renders;
`mockups/step-3.md` §3 is redrawn from a placeholder to the real string. The
headline of the ruling: **the per-track message prints no number at all** — not
Yoto's ceiling, not the file's size — which closes the self-refuting comparison
without a byte comparison and leaves nothing for plan §8's unrun probe to
falsify. The **✅ RULED** block inside *⛔ Blocker — item 20* below summarises it
and lists three things Builder must not "improve".

Previously: 2026-09-06 by Builder — **item 20 is ⛔ BLOCKED on a Designer
ruling, and [PR #27](https://github.com/mmackelprang/yoto-maker/pull/27) is open
but deliberately NOT merged.**

Both halves of the work are done and green — the streamed PUT and the 413
routing — at **390 tests**, with pre-merge review at 0 HIGH / 1 MEDIUM / 4 LOW
(MEDIUM and three LOW fixed, all test-only). What stops the merge is **one of
the two error strings plan §7.1 authored instead of routing through Designer**.
The copy gate was asked to scrutinise those two strings rather than accept them
as pre-approved, and returned **NEEDS A REAL DESIGNER PASS** on the per-track
one. Two grounds, both reproduced independently by Builder: the whole-MB
rounding makes the sentence **refute itself** for any size in
100,000,001–100,500,000 (*"Yoto's limit is 100 MB, and this one is 100 MB"*),
which is the *modal* near-miss case; and its recovery clause points at
**duration**, which `app.py:263` has already clamped to 50 minutes, while the
remedy that would work — `📁 Save the files to a folder`, which converts a WAV
to ~72 MB — sits on the same screen and is not mentioned. See
**⛔ Blocker — item 20** below. **Plan §8's live probe was NOT run** (it needs
the maintainer's authenticated Yoto account); item 21 stays open pending it.

Previously: 2026-09-06 by Planner — **item 19's follow-ups exist now: rows
22, 23 and 24. The fourth finding was a stale mockup and is fixed here, not
queued.**

The three rows the merge banner said were owed are filed, so nobody has to chase
them. **22** ships `copy.md` §9's send-path string — already written, already
approved, deliberately unshipped; until it lands the **duplicate-card
protection** is what is given up, on the path where the duplicate is hardest to
undo. **23** is `#startOver` leaving `#exportBtn` disabled, marked
`_needs Designer pass_` rather than `_needs Planner pass_` **because the obvious
fix causes a worse bug** — it must not be scheduled as a quick win. **24** is
the `BaseException` that strands `job.status` at *"running"* forever.

**24 is its own row rather than a fold-in to item 14, and that was checked
before filing.** Item 14 owns moving `POST /api/tracks/file` onto the job system
and the *client contract* around it. The ADR's nearest neighbour is §5.2.3 — a
job killed by an app restart, whose id then 404s — which is the **opposite**
case: there the client gets a legible signal. Nothing in it contemplates a live
process still answering `running` for a job that is already dead. Item 14 is ⛔
on an ADR that is still `proposed`, so folding a live three-line defect into it
would block the fix behind an unapproved architecture decision. The one genuine
overlap — both want `tests/test_jobs.py`, which still does not exist — is
written into item 24's row as a fold-in rule in both directions.

**Builder's fourth finding was fixed, not queued.** `mockups/step-3.md` §8/§8a
drew the green box above the red one; the shipped DOM is the reverse and matches
`interactions.md` §1 and `overview.md` §4.3 — the ordering authority the mockup
file itself cites in its own first lines. Under the package's precedence rule
the mockup is the bug, and correcting a drawing to match the contract it defers
to needs no design judgement, so it is corrected in this commit. **No shipped
behaviour changed.** This is the **third** stale mockup in this feature's life,
so the file's precedence banner now covers ordering as well as strings — it
previously only claimed authority over copy, which is exactly why an ordering
drift walked past it.

**Item 20 is in flight** — claimed on `fix/send-path-size-limit`. *(Builder,
same day: it is now ⛔ blocked and its row reads ⛔, not 📋 — PR #27 is open and
unmerged pending a Designer ruling. See the banner above and the Blocker section
below.)* *(Builder, later the same day: **it is ✅ done and merged as PR #27** —
the ruling landed, was implemented verbatim, and both gates cleared it. This
paragraph is left standing because the two corrections on top of it are the
record of a single item going 📋 → 🚀 → ⛔ → ✅ in one day.)* Items 22 and 24 are
queued behind it; item 23 is not Builder-eligible until Designer has ruled.

Previously: 2026-09-06 by Builder — **item 19 MERGED as
[PR #24](https://github.com/mmackelprang/yoto-maker/pull/24) (`7574d0d`).**
Designer's ruling on Builder's two behavioral deferrals shipped with it: a
reveal failure gets its own region (`#exportOpenError` — six regions, not five),
and the app stops asserting an outcome it does not have when a status poll
drops. The two follow-ups it said were owed became three rows — 22, 23 and 24
above — because its second bullet carried two independent findings.

Previously: 2026-09-05 by Planner — **item 20 planned; item 21 filed.**
Item 20's Planner pass is done and answered the open scoping question: the send
path **advises on size, it does not act on it** — no byte-split, no transcode.
The plan ships only the two halves that are certain regardless of Yoto's
published ceilings (the wrong 413 ceiling, and a send-side memory defect the
job-system ADR does not reach), and hands the advisory surface itself to a new
**item 21** blocked on a Designer ruling and a live probe. **Item 20 branches
off `main`, needs no version bump, and stays independent of item 19 in both
directions.**

Previously: 2026-09-05 by Builder — **item 19 claimed and in flight.**
Branch `feat/save-to-a-folder`, shipping as **v0.1.13** (this PR owns the bump —
the version string is the asset cache key). **Item 20 was explicitly NOT part of
that cycle** and stayed 📋 queued.

Previously: 2026-09-05 by Planner — **two rows filed: item 19 (specced,
planned, ready) and item 20 (needs a Planner pass).**

**Item 19 — save the files to a folder.** A second, user-chosen way to finish one
card: the app writes the finished audio, the pictures and a self-contained
instruction page into `<Documents>\Yoto Maker\<card name>\`, and the user uploads
them by hand on `my.yotoplay.com`. **It needs no sign-in at all**, which is half
the reason it exists — a user whose Client ID has hard-blocked sign-in is
currently stopped dead at step 3. The signed-in send path is untouched. Spec
**approved 2026-09-05**; the design handoff package is complete (four files);
**10 tasks, one PR, ships as v0.1.13** (it owns the bump — the version string is
the asset cache key and this is almost all `app.js`). **Read the briefing notes
before starting: five things in it are load-bearing and read as arbitrary.**

**Item 20 — the send path splits on duration and never checks bytes.**
Pre-existing, on the **shipped** authenticated path, found while researching
Yoto's published limits for item 19. `MAX_TRACK_SECONDS = 3000` clears Yoto's
60-minute per-track limit and says nothing about its **100 MB** one, and the app
does not transcode local files — so a local WAV at that bound is ~529 MB, five
times over. The 413 handler then names the wrong limit. **Recommended priority:
MEDIUM** — above the four LOW cosmetic rows, below item 19. It neither blocks nor
is blocked by item 19; export-only mode is immune for a reason worth
understanding (see its briefing).

Previously: 2026-07-22 by Builder — **item 18 shipped as
[PR #20](https://github.com/mmackelprang/yoto-maker/pull/20): the card-format
repair CLI** (`python -m yoto_maker.repair`) that fixes existing cards' declared
`format` (mp3 → opus) **in place**. The
read-only Step-0 diagnostic ran and **pinned the real `GET /card/{id}` shape**:
the body is wrapped as `{"card": {...}, "ownership": {...}}` (client unwraps it),
and each track's pre-signed artifact URL is on **`trackUrl`** itself (a
`https://secure-media.yotoplay.com/…?Signature=…` URL, not the `yoto:#sha` the
plan assumed) — so the plan's literal code was adapted at exactly the step it
told Builder to pin. `gzP2B`'s single artifact was probed read-only and
confirmed **Ogg Opus** (`OggS`/`OpusHead`; served `Content-Type: audio/ogg`, no
`codecs` param). Dry-run by default, backup-before-write, all-or-nothing,
verify-after; **no version bump**. Suite **247 passed**; pre-merge review found 2
HIGH + 2 MEDIUM, all fixed (HIGH #1 — the resolved-`trackUrl` round-trip can't be
self-verified inside the signing window — is inherent to the approved
GET-mutate-POST design and is handed to the coordinator as a **staged-rollout**
requirement, with an in-tool `--apply` warning). **This PR does NOT run
`--apply`** — the live 3-card repair is the coordinator's separate post-merge
step. **Bookkeeping reconciled in this same edit:** items 13 (PR #19) and 17
(PR #18) are both on `main` and now sit in the Shipped table (13's stale
in-flight Queue row is retired); item 18 has a Queue row + briefing below.

Previously: 2026-07-21 by Builder — **item 17 shipped: Yoto's true
transcoded `format` now flows into the card payload**
([PR #18](https://github.com/mmackelprang/yoto-maker/pull/18)). The card
previously advertised `format: "mp3"` for every track while Yoto actually serves
**Ogg Opus**. **The scope was narrowed from the original plan after a live
capture:** a real upload→transcode-poll confirmed `transcodedInfo.format ==
"opus"` (a child of `transcode`), and a read-only diagnostic on the three real
cards showed declared `fileSize`/`duration` **already match** the served values —
Yoto self-corrects those server-side. So the fix is **format-only, best-effort**:
a missing/misshapen `transcodedInfo` degrades to the local probe and still builds
the card (it can NEVER block card creation), and `channels` stays the existing
`"stereo"`/`"mono"` string. The wider fail-loud / fileSize-propagation / int-
channels design was tried and reverted. Backend-only, **no version bump** — rides
the next release cut. Item 17 landed independently of **item 13 (PR #19), which
merged to `main` just before it**; both edit this queue file but no code files
overlap. Suite **142 passed**; pre-merge review clean. On-device confirmation that
`format: "opus"` cures the physical player's stuck offline download is the
post-merge maintainer step.

Previously: 2026-07-21 by Builder — **item 13 claimed and in flight.**
Branch `feat/client-id-validation-and-multi-upload`; shipping as v0.1.11 in the
four commit stacks (0 → A → B → C) the plan mandates. **Protocol override for
this item: it will be taken to green and left awaiting maintainer sign-off, NOT
auto-merged** — Item A is auth-adjacent (it rewrites the Client ID / sign-in
flow) and falls under the "pause before merge on anything sensitive" rule.

Previously: 2026-07-21 by Planner — **two queue edits, no new feature spec.**
(1) The latent **HTTPException-copy-loss bug is now folded into item 13** as a new
Stack 0 task (**Task 1b**): `api()` gains a string-guarded `data.detail` fallback so
every `HTTPException` message becomes visible, with a copy audit of all eleven
raises and the one developer-ish string (`Unknown icon`) softened. Item 13 is now
**20 tasks**; its row, briefing, and the plan's §Commit stacks / §Deviations /
§For the queue / Test Plan §L are all updated. (2) **The job-system arc from the
file-upload ADR is now tracked as three dependency-ordered rows — items 14 (PR A),
15 (PR B), 16 (PR C)** — deliberately not collapsed, because PR A is independently
shippable. All three are **⛔ blocked on item 13 shipping first and on ADR
approval** (the ADR is still `proposed`); PR C additionally needs a maintainer
**go/no-go** before it is planned. See the arc briefing.

Previously: 2026-07-21 by Planner — **item 13 filed and planned: Client ID
validation + multi-file audio upload, one PR in three commit stacks, shipping as
v0.1.11.** It answers a real incident — the maintainer's daughter typed her email
address into the Client ID field, the app saved it and called `logout()`,
destroying her working session behind an opaque Auth0 error. Item A (stacks 0+A)
prevents that class of failure; Item B (stack B) is the unrelated multi-file
upload that ships alongside. **Read the row's briefing notes before starting —
the commit-stack ordering is a hard shipping constraint, and three findings in
the plan are exactly the things that get lost between spec and build.** The plan
also builds the three job-system-ADR seams (S1/S2/S3) into Item B; **that arc
itself is out of scope for this PR.**

Previously: 2026-07-20 by Builder — **v0.1.10 is released. Items 8 and 9
are both `🚢 released`.** PR #16 merged as `be93ee1` after both gates cleared;
tag `v0.1.10` → `715bd1c` on the remote; `YotoMaker.exe` (127,040,616 bytes)
uploaded. Suite **137 passed**. Release:
<https://github.com/mmackelprang/yoto-maker/releases/tag/v0.1.10>

**The update path was verified end-to-end, not assumed** — the same check
v0.1.9's release cut introduced. A client spoofed to `0.1.9`, with **no
`YOTO_LATEST_VERSION` override** (it short-circuits the API call at
`updater.py:80` and would test the override instead of the release), hits the
real releases API and gets `update_available: true`, `latest: "0.1.10"`, and a
`download_url` answering **200 at 127,040,616 bytes** — byte-identical to the
uploaded asset. A v0.1.10 client correctly gets no banner. **The user's live
v0.1.9 install on port 8777 should now offer them this update**, which is the
end-to-end proof that v0.1.9's release-path work holds.

**Both PR #16 gates cleared, and the MEDIUM was this PR marking its own
homework.** Polisher: 0 HIGH, 1 MEDIUM, 2 LOW. Tester: 12 flows passed, 0
failed, 0 HIGH, 0 MEDIUM, 3 LOW. The MEDIUM was that `styles.css` asserted
Designer's **derived** figures (4.97 / 5.81) as measured — line 73 literally
said the pair *"measures 4.97:1"* — in the very PR that took the real
measurement. Fixed in `292550f`, along with the missing supersession pointer in
`tokens.md`. Polisher's two LOWs are queued as items **11** and **12**; Tester's
methodology LOW is recorded with the methodology in `tokens.md` §2b.

**The regression test nobody specced is now in the tree.** Tester drove a live
connected↔disconnected transition with no reload; since PR #16 made the copy
state-dependent inside `renderStatus()`, that is this change's primary
regression guard and static markup assertions structurally cannot cover it.
`tests/test_settings_link_transition_e2e.py` is the repo's **first e2e spec** —
it drives the flip through the app's own `refreshStatus()` rather than writing
`textContent` itself, and **five mutations were verified failing**, including
the one-way-flip case every static assertion passes. It skips cleanly when
playwright or its browser is absent, so it does not become a second instance of
item 3; playwright is now declared in dev extras rather than left ambient.

**One thing shipped unverified again, deliberately:** the screen-reader
announcement on `#yotoPill`'s new accessible name. NVDA is still not installed
and Narrator's speech still cannot be captured as text, so **nobody has heard
it** — the accessibility tree is consistent with the expected utterance, but
that is an argument from construction. Recorded under **Not verified in
v0.1.10** in `docs/RELEASE_NOTES.md` and in the GitHub release body, exactly as
v0.1.9's reveal toggle was. Anyone with a screen reader can close both in about
a minute.

Previously: 2026-07-20 by Builder — **item 9 shipped as
[PR #16](https://github.com/mmackelprang/yoto-maker/pull/16), open and
deliberately not merged: Tester and Polisher gate this one.** All 7 tasks done,
suite **133 passed**. **Item 5 is retired** — absorbed and delivered by Tasks
3–5, as its Designer pass specified.

**The contrast numbers were re-measured live from rendered pixels, not asserted
from the spec** — the whole point, given PR #10's UAT produced three false
readings from cached CSS. Sampled from element screenshots with PIL: label at
rest **5.03:1** (spec predicted 4.97), hover **5.87:1** (5.81), green dot
**3.93:1** (3.88), amber dot **3.53:1** (3.48). Every figure lands slightly
*better* than Designer's independent sweep, on both a hard-reloaded and a
naturally-loaded page. Alpha `0.28` stands; the `0.32` escape hatch in
`tokens.md` §2b was not needed.

**Which set supersedes which is now stated in the tree, not just here.**
`tokens.md` §2b opens with a provenance box marking every figure in that section
as *derived*, tabling it against both independent measured sets, and saying the
measured set wins; §4's certification table carries the measured values with the
derived ones noted alongside. `styles.css` marks its three derived figures as
derived and cites the measured value beside each, guarded by a test. Tester's
independent run read **5.09 / 5.95**, agreeing with PR #16's 5.03 / 5.87 to
within a rounding step and, like it, landing better than derived.

**A sampling hazard is recorded with the methodology** (`tokens.md` §2b): naive
whole-element sampling of `.pill` returns a spurious **3.30:1** from
rounded-corner antialiasing, where the fill fades into bare gradient. Those
pixels have no label drawn over them, so the pair they describe never renders.
Sample the fill's interior, inset past the corner radius. Written down so a
future pass does not re-derive a false failure and "fix" a control that passes.

**The defect was reproduced live on the pre-PR build before being fixed.** The
still-running **v0.1.9** `.exe` on port 8777 served as a control: in the
connected state it reports `#advRow` inside `#connectRow`, `#connectRow` hidden,
and `advRowVisible: false` — the one contextual way into Settings literally
unrenderable, exactly as the field report described. **One new finding, filed
below as item 10** (pre-existing 320px header wrap, proven not ours).

*(That control was first written up as "the still-running v0.1.10 `.exe`", which
is self-contradictory — v0.1.10 is the release this PR is part of. It is v0.1.9,
which is the correct pre-PR baseline, so the control was valid and every
conclusion drawn from it stands. Corrected here and in PR #16's body.)*

Previously: 2026-07-20 by Builder — **item 8 is merged** as
[PR #15](https://github.com/mmackelprang/yoto-maker/pull/15), merge commit
`77d499c`. **No release cut yet, deliberately:** item 9 ships in the same
v0.1.10, so the tag, the `.exe` and the GitHub release all wait for it. Item 8
is therefore `✅ merged` and not `🚢 released` — the distinction this queue
introduced after v0.1.9 sat merged-but-unreleased for a day. **Item 9 is next
and is now in flight.**

Previously: 2026-07-20 by Builder — item 8 shipped as PR #15. All 7 tasks done, suite
**120 passed**, verified from the frozen `.exe` as well as from source. The
poisoned-cache repair was measured for real — cache never cleared, F5 not
Ctrl+Shift+R — and the pre-fix document was confirmed serving from cache with
**zero network requests**, which is the plan's linchpin claim measured rather
than assumed. Review found the plan's "complete surface" claim was wrong:
`logo.png` was a third unstamped asset, now fixed and guarded by a sweep rather
than a filename list. **Item 9 rebases onto the `0.1.10` bump this PR owns.**

Previously: 2026-07-20 by Planner — **item 9 filed and planned: a
connected user cannot find the way into Settings.** Reported from the field by
the user, who knew the feature existed, had approved its design, was actively
looking, and still could not find it. It is a **vocabulary** failure, not a
visibility one, and the plan is deliberately built on only the uncontaminated
half of the evidence — read its briefing notes before starting. **It absorbs
item 5**, which is now planned rather than blocked-pending-Designer.

**Items 8 and 9 both ship in v0.1.10 and are two PRs, not one.** Item 8 owns the
version bump; item 9 must not also bump. Prefer shipping 8 first — its version
stamp is what lets an already-poisoned browser receive item 9's fix at all.

Previously: 2026-07-20 by Planner — **item 8 filed and planned: the stale
asset bug.** It is the highest-priority row on this list. It has plausibly
degraded every release since v0.1.5, it fails silently and partially against the
user least able to work around it, and **we filed it twice as a testing hazard
rather than the shipping bug it is** — see its briefing notes. Ships in v0.1.10.

Previously: 2026-07-20 by Builder — item 7 shipped, and **v0.1.9 is now
genuinely released**: tag `v0.1.9` pushed to origin, `YotoMaker.exe` built and
uploaded, and the update path verified end-to-end (a spoofed v0.1.8 client is
offered v0.1.9 by the real releases API). Items 1 and 7 are the first rows to use
the `🚢 released` state the same PR introduced. Items 2–6 re-checked against the
code and all still accurate.

Previously: item 1 merged as PR #10 but sat merged-but-unreleased for a day —
the gap that motivated the vocabulary split below. Items 4, 5 and 6 were filed
from that PR's Tester and Polisher gates; like items 2 and 3, all are
pre-existing and were deliberately left out of its scope.

Work items that have an approved design and a complete implementation plan, ready
for Builder to ship one PR per row. Planner appends; Builder claims, ships and
marks done. **Priority order is the user's to set** — Planner does not reshuffle.

Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ merged · 🚢 released

**`✅ merged` is not `🚢 released`.** Merged means the PR is on `main`. Released
means a tag is pushed, an `.exe` is built and a GitHub release carries it — which
is the only thing `updater.py` can see, and therefore the only thing a user can
receive. A row moves to 🚢 only when `gh release view v<version>` returns a
release with an uploaded `.exe` asset. **Paste that command's output into the
row's PR or the commit that marks it.** v0.1.9 sat merged-but-unreleased for a
day because these two states shared one word.

---

## Queue

| # | Status | Item | Spec | Plan | Depends on | Notes |
|---|--------|------|------|------|-----------|-------|
| 2 | 📋 | **`--port` flag doesn't move the OAuth redirect URI** — the flag changes the listening port but not `cfg.port`, so Yoto sign-in always redirects to 8777 | _needs Planner pass_ | _needs Planner pass_ | — | Pre-existing in v0.1.8 and documented in `--help`. Small fix, but it touches the OAuth redirect — wants a plan before someone changes it blind. |
| 3 | 📋 | **`test_youtube_sponsorblock_best_effort_retry` does a bare `import yt_dlp` and hard-fails when it is absent** (`tests/test_sources.py:60`) — wants a `pytest.importorskip` guard | _needs Planner pass_ | _needs Planner pass_ | — | One-line test fix. **Re-checked 2026-07-20 and the row's original framing was wrong:** `yt-dlp` is a **core** dependency in `pyproject.toml`, not an optional one, so a correctly-installed environment always has it and the suite is green (137 passed). The failure mode is a partial or editable dev install. Still worth the guard — a test should skip on a missing dep rather than report a red that costs every future Builder a moment of "is this me?" — but it is **latent, not active**, which lowers its priority. Planner should decide whether it is worth a row at all. |
| 4 | 📋 | **The crop editor modal has no focus trap** — Tab escapes the modal into the page behind it | _needs Planner pass_ | _needs Planner pass_ | — | MEDIUM. Pre-existing from the v0.1.7 crop editor; **not** a PR #10 regression. Observed Tab order below. |
| 5 | ✅ | ~~**`#yotoPill` white label fails WCAG AA at rest**~~ — **ABSORBED into item 9 and DELIVERED by it** ([PR #16](https://github.com/mmackelprang/yoto-maker/pull/16), Tasks 3–5) | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12.5–12.6 + `tokens.md` §2b | [item 9's plan](superpowers/plans/2026-07-20-settings-discoverability.md), Tasks 3–5 | — | **Retired 2026-07-20 — do not schedule.** The fill inversion shipped in PR #16 and the result was **measured live from rendered pixels, not asserted**: the white label goes **2.56:1 → 5.03:1** at rest and 5.87:1 on hover, clearing the 4.5:1 bar. The `aria-label` deletion (WCAG 2.5.3) shipped with it. Nothing is left in this row. Historical record follows. The Designer pass it was waiting for is done, and concluded the contrast defect and the connected-state discoverability defect are **one defect measured two ways**: the fix for both is a single fill inversion (`rgba(255,255,255,0.18)` → `rgba(36,29,56,0.28)`, 2.56:1 → 4.97:1). Shipping contrast separately would leave the discoverability fix's primary entry point illegible, and shipping discoverability separately would contradict this row. **Retire this row when item 9 merges** — there is nothing left in it that item 9's plan does not carry. |
| 6 | 📋 | **`favicon.ico` 404 on the callback page** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic. Logged so it isn't rediscovered; safe to leave sitting. |
| 10 | 📋 | **The header pill's label wraps to two lines at 320px** — the header grows to 110px and the pill to 48px | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic, **pre-existing and proven so** — measured identically (pill 48px, header 110px, `scrollWidth` 305) on the pre-PR `.exe` control at the same width, and removing the new chevron does not change it by a pixel. **No overflow, no horizontal scroll, no overlap with the brand** — the header just gets taller. Item 9's Test Plan §E.5 expected "no wrap" and prescribed dropping the chevron's leading gap if tight; that escalation is **inapplicable**, since even the shortest label wraps with the chevron removed entirely. The real cause is `.brand` + pill exceeding 320px, which is a header-layout question item 9 was explicitly forbidden from touching. |
| 11 | 📋 | **`⚙️` is unhidden text inside `#advToggle`'s accessible name** — the step-3 link announces as *"gear Connect a different Yoto account"* | _needs Designer pass_ | _needs Designer pass_ | — | LOW, **pre-existing since v0.1.9**, from PR #16's Polisher gate. **Needs Designer, not Builder** — see briefing notes; it is specced-in, not an oversight, and the obvious fix collides with two other rules. |
| 12 | 📋 | **`#advToggle`'s touch target is ~20px against WCAG 2.2 AA's 24×24** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, **pattern-level and pre-existing**. It matches the canonical footer link `#settingsLink` exactly, so this is a question about the app's link pattern, not about one control. Enlarging *this* link alone is the prominence increase `overview.md` §12.7 forbids. Fix the pattern or accept it — do not special-case one link. |
| 13 | ✅ | **Client ID validation + multi-file audio upload** — **MERGED to `main` as [PR #19](https://github.com/mmackelprang/yoto-maker/pull/19) (`6481aca`, v0.1.11); also recorded in the Shipped table. Row kept because items 14–16's arc briefing references it.** Item A blocks a malformed Client ID before it can destroy a working sign-in or fire a doomed authorize request; Item B adds sequential multi-file upload with grouped partial-failure reporting, retry and cancel | [`specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md) | [`plans/2026-07-21-client-id-validation-and-multi-file-upload.md`](superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md) | — | **Ships as v0.1.11. HIGH — Item A closes a live account-lockout footgun a real user hit.** One PR, **three commit stacks in order 0 → A → B → C** (see briefing notes); Item A must revert independently. 20 tasks — Stack 0 also folds in the latent HTTPException-message-visibility fix (Task 1b). **The plan owns the version bump — it must, the version string is the asset cache key.** Extends the `configuration-surface/` handoff (§13, `copy.md` §4b–d/§7, `interactions.md` §3.6); Item B's surface has no handoff by decision. |
| 14 | ⛔ | **Move `POST /api/tracks/file` onto the background job system (ADR PR A)** — the endpoint returns `{job_id}` and runs on a job thread, matching `/api/tracks/youtube`. Removes a redundant ~260 MB double-write and stops long transcodes from blocking uvicorn's event loop (today a long split hangs `/api/status` and every route) | [ADR §3.1](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs Planner pass_ | **13 ships first; ADR approved** | **Independently shippable and valuable — do NOT collapse the arc into one PR.** Ships without cancel or new progress. Lands on item 13's three seams (S1/S2/S3): ~15–20% client touch, near-zero deleted. **The regression the seams guard:** a job endpoint reports failure through `pollJob` with **no `.status`**, and `jobs.py` has **zero test coverage**, so item 13's reason-precedence test (classifier reads `err.data.reason`+`retryable` before `.status`) is what stops job failures misclassifying as transient (success criterion 12). Add `tests/test_jobs.py`. **Never persist jobs** (ADR §5.4) — a job surviving restart would `add_track` into a fresh empty draft. See arc briefing. |
| 15 | ⛔ | **Exact server-side cancel + real long-file progress (ADR PR B)** — the ffmpeg `Popen` rewrite in `normalize.py::_run`, a server-side `cancelled` terminal state **distinct from `error`**, `POST /api/jobs/{id}/cancel`, job eviction, partial-segment cleanup | [ADR §3.2](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs Planner pass_ | **14 (PR A); 13; ADR approved** | This is the PR that **deletes the client's *"may still finish"* hedge sentence**. `cancelled` MUST be distinct from `error` or a cancel is reclassified transient and offered `Try again` (ADR §5.2.6). `_run` is shared by `probe_audio` / `normalize_to_mp3` / `split_audio` — default the new kwargs to `None` for byte-identical behavior when unset. See arc briefing. |
| 16 | ⛔ | **Client-only XHR upload-progress for short files (ADR PR C)** — replace `fetch` with `XMLHttpRequest` in `uploadOneFile` (seam S1) for `upload.onprogress`, fed through `setAddProgress` (seam S3) | [ADR §3.3](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs go/no-go, then plan_ | **14 (PR A); 13; maintainer go/no-go** | **DEFERRABLE cut-line — needs an explicit maintainer go/no-go before it is planned** (ADR open question 1). Open product question: for **under-50-min files the whole wait is the upload leg**, which **only the browser can measure**, so A+B alone leave short files with a differently-fake bar (ADR §1.4, §7.4–7.5). The arc is coherent with A + B alone. See arc briefing. |
| 18 | ✅ | **Repair existing cards' declared `format` (mp3 → opus) IN PLACE** — a CLI utility (`python -m yoto_maker.repair --card-id … [--apply]`) that reads a card via `GET /card/{id}`, probes each track's served artifact for Ogg Opus, and rewrites **only** each track's `format` via `POST /content` with `cardId` — preserving the physical NFC link, icons, keys, order and every other field. Dry-run by default; backup-before-write; all-or-nothing per card; verify-after; idempotent | [ADR](architecture/decisions/2026-07-21-repair-existing-cards.md) (design basis; committed by this PR) | [plan](superpowers/plans/2026-07-21-repair-existing-cards.md) | 17 (PR #18) + 13 (PR #19) — both on main | **MERGED as [PR #20](https://github.com/mmackelprang/yoto-maker/pull/20); also in the Shipped table. The live 3-card `--apply` run is the coordinator's next step (staged rollout).** New `yoto/repair.py` (pure corrector + orchestration + CLI) + 4 small `client.py` methods + a `yoto_maker/repair.py` shim + `tests/test_repair.py` + `tests/fixtures/card_sample.json`. **`format` was the only field ever written *as of this PR*** — **widened 2026-09-10 by [ADR `2026-09-10-overlay-labels-and-the-declared-change-set.md`](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md)**, which replaces the format-only invariant with a declared change-set and adds `overlayLabel` as a second intent (issue #31). **Step-0 pinning found the real body is wrapped `{"card":…,"ownership":…}` and the artifact URL is `trackUrl` itself** (adapted from the plan's assumptions). **No version bump.** The live 3-card `--apply` run is the coordinator's post-merge step — this PR does not write. 6 tasks. |
| 19 | ✅ | **Save the files to a folder** — a second, user-chosen way to finish one card. The app writes the finished audio, the pictures and a self-contained `What to do next.html` into `<Documents>\Yoto Maker\<card name>\`; the user uploads them by hand on `my.yotoplay.com`. **Needs no sign-in at all.** One `.btn` + one `.tiny` caption appended to step 3 after `#connectWarn`, six `.hidden` regions beneath it (planned as five; see the ruling in the notes), three new routes, a new `yoto_maker/export/` package. The signed-in send path is untouched | [`specs/2026-09-05-export-only-mode-design.md`](superpowers/specs/2026-09-05-export-only-mode-design.md) + [`design-handoffs/export-only-mode/`](design-handoffs/export-only-mode/) | [`plans/2026-09-05-export-only-mode.md`](superpowers/plans/2026-09-05-export-only-mode.md) | — (13, 17, 18 all on `main`) | **MERGED to `main` as [PR #24](https://github.com/mmackelprang/yoto-maker/pull/24) (`7574d0d`, v0.1.13); also recorded in the Shipped table.** Shipped **six** `.hidden` regions, not five — Designer's 2026-09-05 ruling added `#exportOpenError` so a reveal failure stops destroying the partial-save notice. Spec approved 2026-09-05. 10 tasks, one PR, shipped as v0.1.13 — this PR owned the bump. Extends the `configuration-surface/` handoff; deviates from nothing. **Zero new CSS, zero new tokens, `styles.css` unmodified** — a diff that touches it means something in spec §2 was reinterpreted and goes back to Designer. `copy.md` is the authority on every string, and **no user-visible string may contain "export"**. Read the briefing notes — five constraints in this feature read as arbitrary and are not. |
| 20 | ✅ | **The send path's 413 named the wrong ceiling, and its audio PUT held the whole track in RAM** — **MERGED to `main` as [PR #27](https://github.com/mmackelprang/yoto-maker/pull/27); also in the Shipped table.** `_friendly_http` mapped *every* 413 to the **card-level** *"max 5 hours per card"* at the moment the user had hit the **per-track** limit; and `_put_audio` did `content=fh.read()`, ~529 MB resident for a 50-minute WAV. Both fixed. The per-track string was **blocked on a Designer ruling** mid-cycle and shipped as ruled: [`copy.md` §10](design-handoffs/export-only-mode/copy.md) + [`interactions.md` §4b](design-handoffs/export-only-mode/interactions.md) | Decision in plan §0; the two strings are ruled in [`copy.md`](design-handoffs/export-only-mode/copy.md) §10 (rendering: `interactions.md` §4b) | [`plans/2026-09-05-per-track-size-limit.md`](superpowers/plans/2026-09-05-per-track-size-limit.md) — **§7 is superseded by §10 and now says so** | — | **Shipped 2026-09-06 at 400 tests. NO version bump** — zero files under `server/static/` on the whole branch. **The ruling closed ground 1 subtractively: no number is printed at all**, so nothing is rounded and no byte comparison was introduced — plan §2 stands untouched, and the string survives plan §8's unrun probe whatever it finds. Ground 2 closed by pointing at `📁 Save the files to a folder`, which **promises nothing** (an oversized file already in the copy-as-is set is copied untouched, `export/rules.py:46-47`) and is **deliberately not conditioned on file type**. **The one lesson worth carrying forward:** the pre-existing MEDIUM's guard asserted `"100 MB" not in msg`, and the ruling deleted that number — so the guard would have gone **vacuous and still passed**. A string change can silently disarm the test that guarded the string; assert on what the new string *contains*. The copy gate's own MEDIUM became **item 27**. **Item 21 stays open** on the unrun probe. |
| 21 | 📋 | **The send path never warns that a track is over Yoto's limits until a long upload fails** — the app knows every track's size the moment it is added, and says nothing. A `.msg-box info` on step 3 above `🚀 Send to Yoto`, naming the per-track and card-level ceilings | _needs Designer pass_ | _needs Designer pass, then Planner_ | **20**, + a Designer ruling on copy, + the live probe in [item 20's plan §8](superpowers/plans/2026-09-05-per-track-size-limit.md) | **LOW-MEDIUM, and it may correctly turn out NOT to ship.** Item 20's plan §8 specifies a cheap, non-destructive live probe (get an upload URL, PUT a ~120 MB file, never call `/content` — no card is created) that settles whether the 100 MB figure binds the **API** path at all. If it does not, an advisory naming it is a false alarm on the shipped path and **this row closes unshipped**. **`copy.md` §5.9's approved strings cannot be reused verbatim** — they name *"Yoto's website"*, which is false on this path, and their `{list}` format is justified by a file dialog that does not exist here (plan §1.4). Touches `index.html` → **needs a version bump.** |
| 22 | 📋 | **`copy.md` §9's send-path string — written, approved, and deliberately unshipped** — when a status poll fails *after* `POST /api/send` has already returned a job id, `#sendError` still renders today's generic transport line, which ends *"…then try again."* The approved replacement is three paragraphs: the app cannot tell her whether the card went through, nothing on the card has changed, look in the Yoto app on her phone — and if it isn't there, press `🚀 Send to Yoto` **once** | [`design-handoffs/export-only-mode/copy.md`](design-handoffs/export-only-mode/copy.md) §9 (+ §9.1–9.3) — **the copy already exists; this row ships it, it does not author it** | _needs Planner pass_ | — (19 on `main`) · **a live authenticated send against a real Yoto account**, which is the whole reason this is not already shipped | **MEDIUM, and Designer's ranking is why it is not LOW: the send path's current instruction is the *more dangerous of the two*.** It ends *"then try again"*, and pressing `🚀 Send to Yoto` while the first send is still uploading puts **a second card in her Yoto account** — on a website this app does not control, which she must then find and delete. The save path's identical mistake produces `Bedtime Stories (2)` in Documents, which `copy.md` §5.8 says needs no explanation at all. **Until this lands, the duplicate-card protection is what is given up**, on the path where the duplicate is hardest to undo — knowingly, per the maintainer's 2026-09-05 ruling (§9.1's stated fallback, taken). Held for a **verification** reason, not a design one. `#sendError` gains **no `role` and no `tabindex`** (§9.3, deliberate); the YouTube add path still does not opt in (§9.3). The retry is **opt-in per call site** — see briefing. Touches `app.js` → **needs a version bump.** |
| 23 | 📋 | **`#startOver` leaves `#exportBtn` disabled** — "Start a new card" pressed during a save disowns the running job (`app.js:2675`) and clears all six regions, but never re-enables the save button. It returns only when the disowned run's `finally` (`app.js:2420-2424`) eventually executes — for a large save, the rest of the write plus up to the 12s poll-retry window. `#exportProgress` is hidden by then, so nothing on screen explains why the button is dead | _needs Designer pass_ | _needs Designer pass_ | — (19 on `main`) | **MEDIUM. Pre-existing; deferred from item 19's pre-merge review. `_needs Designer pass_` is not a formality here — the obvious fix causes a worse bug, which is why this row must not be scheduled as a quick win.** Adding `$("#exportBtn").disabled = false` to the `#startOver` handler re-arms a second save while the first is **still writing server-side** (`jobs.py` has no cancellation — that is item 15 / [ADR §3.2](architecture/decisions/2026-07-21-file-upload-on-job-system.md)), and the disowned run's `finally` is **not generation-guarded** the way its `catch` and its progress callback are: when it finally fires it hides the *second* run's `#exportProgress` and re-enables the button mid-run. The one-liner trades a stuck button for a dead progress bar on a live save. Designer owes the question underneath it first: what does the save button *mean* while a disowned job is still writing a discarded card's folder? See briefing. |
| 24 | 📋 | **A `BaseException` in a worker thread strands `job.status` at "running" forever** — `jobs.py:70` catches `Exception`, so a `SystemExit` / `KeyboardInterrupt` escaping a job target leaves the `Job` in its **non-terminal** state with no error, no timeout and no eviction. The client keeps receiving a *successful* `running` answer, so `pollJob`'s retry window never engages: the bar freezes at its last percent, the button that started it stays disabled, and only a page reload gets out. Live on **both** shipped job paths — the YouTube add and item 19's save | — · [ADR](architecture/decisions/2026-07-21-file-upload-on-job-system.md) is the arc this sits beside, **not** this row's design basis | _needs Planner pass_ | — · **but read the fold-in rule against 14 in the notes before scheduling either** | **LOW-MEDIUM — rare trigger, unbounded consequence, ~3-line fix.** Pre-existing; deferred from item 19's pre-merge review, which was explicitly constrained not to touch `jobs.py`. **Checked against item 14 before filing, and it is not work 14 already owns:** 14 owns moving `POST /api/tracks/file` onto the job system, and its `jobs.py` work is the *client contract* (`reason` / `retryable`, the 404 → *"Yoto Maker restarted"* mapping); the ADR's terminal-state material — §3.2's `cancelled` state, §5.2's list of newly-possible failure modes — covers a job that finishes badly and a job whose **process** died and now 404s (§5.2.3), and **never contemplates a live process still cheerfully answering `running` for a job that is already dead**. It is also not foldable *now*: **14 is ⛔ on an ADR still marked `proposed`**, and blocking a three-line correctness fix that is live on two shipped paths behind an unapproved architecture decision is the wrong trade. **The one real overlap is `tests/test_jobs.py`** — item 14's row calls for it, and `jobs.py` still has **zero coverage** (confirmed 2026-09-06: no such file exists). Rule, both directions: **whichever lands first creates the file and the other adds cases; if 14 is claimed while this row is still 📋, fold this in as a task in 14's plan and retire this row rather than shipping both.** |
| 25 | 📋 | **`#sendError` has no `role` and no `tabindex`, and it now holds the app's only cross-path recovery pointer** — `index.html:195` is a bare `<div id="sendError" class="msg-box err hidden">`. Nothing is announced and focus never moves, so a screen-reader user who hits a send failure is told nothing about it — including, once item 20 lands, that pressing `📁 Save the files to a folder` is the way to finish the card Yoto just refused | [`interactions.md` §11 item 3](design-handoffs/export-only-mode/interactions.md) (**re-weighted** 2026-09-06, not reopened) + §4b.5 · [`copy.md` §10.5](design-handoffs/export-only-mode/copy.md) + §9.3 — **all four state the question and record the decline; none of them answers it** | _needs Planner pass_ | — **not blocked and not waiting on anything.** The gap is live on `main` today; item 20 / [PR #27](https://github.com/mmackelprang/yoto-maker/pull/27) is what raises its cost, not what enables the fix. **A screen reader that actually speaks** is the one real dependency — see briefing | **MEDIUM, and the trigger-rarity argument is why it is neither LOW nor HIGH.** Designer's own framing is the argument: **_"a pointer that is never announced does not point"_** (`interactions.md` §4b.5). This **got worse rather than newly appearing** — §9.3's decline was right on its own terms when the region held only transport lines whose recovery was already on screen; §10 changed what the region carries without changing the region. **Deliberately not folded into item 20's string fix:** adding a live region changes announcement behaviour for **every** shipped send failure — the expired sign-in, the 5xx, the timeout and the fallback, not just the 413 — so it needs its own pass and its own UAT. **It is not a two-attribute change and must not be scheduled as one.** **Why not LOW:** the oversized-track gate binds the *pointer*, not the *region* — the same missing `role` silences every 5xx and timeout on the shipped send path, which are ordinary events, and item 4 (modal focus trap, MEDIUM) is the nearest calibration point. **Why not HIGH:** nothing is destroyed or unreachable — every message stays readable, `#exportBtn` stays in the Tab order regardless, and the recovery stays *reachable*, just never *offered*. **The scope question the Planner pass owns:** `#sendError` is one of **four** of the app's eleven `.msg-box err` regions carrying no `role`, so item 12's standing rule (fix the pattern or accept it; do not special-case one control) is live here. See briefing. |
| 26 | 📋 | **`_friendly_http`'s other four sentences are owned by no handoff package** — with item 20's ruling the **413** branch is ratified in `copy.md` §10. The **401/403**, the **5xx**, the **timeout** and the **fallback** (`client.py:476-490` on `main`) are shipped, user-facing copy with no document behind them, and they are reached from the **card-repair CLI** as well as the send path | _needs Designer pass_ — **an ownership question before it is a copy question** | _needs Designer pass, then Planner only if anything ships_ | **item 20 ([PR #27](https://github.com/mmackelprang/yoto-maker/pull/27)) on `main` first** — `copy.md` §10 is the ratified anchor the rest of the family gets adopted around, and it does not exist on `main` yet | **LOW-MEDIUM. This is a copy-_adoption_ row, not a bug row, and ranking it as a bug row gets it wrong in both directions.** Nothing in the four sentences is known to be wrong. **The defect is that no document is the authority** — which is precisely how the 413 string came to name the card-level *"max 5 hours per card"* ceiling on the **per-track** upload and survive there unchallenged: it dates to `b40c702`, the founding `feat: core pipeline` commit, and is present in `client.py` at **both v0.1.2 and v0.1.12** (checked at both ends), so it shipped in every tagged release this project has cut. Nobody caught it because there was nothing to check it against. **The value here is preventing a recurrence, not fixing a known break** — a pass that reads all four, finds them correct and writes them down unchanged has succeeded. **The first question, and it is not a detail: where does this copy live?** Verified on `main` at `3330f2c` — nine `raise` sites across seven methods with seven distinct `{doing}` phrases, **three of them reachable from `yoto/repair.py`** (`get_card`, `list_my_cards`, and `update_card`, which **only** the repair path calls). A family reached from both the send path and a card-mutating CLI **cannot be adopted into a package scoped to one surface without first deciding where it lives**, and `export-only-mode/` is the wrong home by construction — §10.4 ruled the generic 413 there only because it is the other arm of the same `if`, and says so itself. **Not plain LOW** because `repair.py` mutates live production cards, where a misleading error is read by someone deciding whether a write landed. See briefing. |
| 27 | 📋 | **`interactions.md` §4b.4's table states an invariant that does not hold** — row 2 says a send that can reach a 413 **cannot coexist with a visible `#connectWarn`**, because an invalid Client ID *"hard-blocks sign-in, which disables `#sendBtn` (`app.js:382`)"*. The two are not coupled: `connected` is **token-presence only** (`auth.py:246`, `_load_tokens() is not None`) and is computed independently of `client_id_verdict` (`auth.py:264`), while `renderConnectWarn()` triggers on **the verdict alone** (`app.js:325`). Sign in successfully, then have `YOTO_CLIENT_ID` become invalid (the `env` tier, which the app cannot unset) with the access token still live → `connected: true` **and** `verdict: "invalid"` → `#connectWarn` renders **between** `#sendError` and `#exportRow` while `#sendBtn` is enabled | _needs Designer pass_ — the claim is Designer's to narrow or to act on | _needs Designer pass, then Planner_ | — (20 on `main`) | **LOW user-facing, MEDIUM as a documentation defect — and the distinction is the whole row.** Found by item 20's copy gate; **confirmed in the live app, not argued**: the state was driven in the browser and `#connectWarn` rendered between the two, with the send button enabled. **The shipped string is NOT wrong and must not be changed for this** — `#exportRow` stays **visible and still below**, so *"below"* remains true; what is falsified is §4b.4's *reasoning*, and its **standing condition** names exactly this (*"`#connectWarn` made reachable during a send"*) as a trigger to revisit the string. **Builder deliberately did not fix it.** Every code fix — hiding `#connectWarn` during a send, gating `connected` on the verdict, moving `#exportRow` — touches the send path's state machine, which **§4b.3 forbids** (*"no control is added, removed, disabled or re-ordered"*), and choosing between *narrow the claim* and *make it true* is a design call. Item 20's test was renamed and narrowed to assert only what it proves, so nothing in the suite now claims this invariant holds. **Cheapest likely outcome: Designer narrows row 2 to "an invalid Client ID blocks a NEW sign-in" and the row closes unshipped.** |
| 28 | ✅ | **The repair CLI crashed *after* it had already written to a live card** — **MERGED to `main` as [PR #33](https://github.com/mmackelprang/yoto-maker/pull/33); also in the Shipped table.** — `python -m yoto_maker.repair --card-id 1WCvI --dry-run` raises `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f916'` at `yoto_maker/yoto/repair.py:745`, because Wild Robot's five track titles each carry a 🤖 and they arrive from Yoto's JSON (`repair.py:317`). `main` prints that line at `:831` — **after** `repair_card` has POSTed at `:648`. So an apply run against Wild Robot today **writes to the live card and then dies before reporting the outcome**, leaving the operator unable to tell whether it succeeded, whether a backup exists, or which card to roll back | Decision in [plan §Commit 0](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) — a **prerequisite this plan adds** to [ADR](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md) §3.7's sequence; no ADR section owns it | [plan](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) Tasks 1.1–1.6 | — | **HIGH, and it is a hard prerequisite for item 29's staged rollout — Wild Robot is one of the three cards that arc must repair.** Not a cosmetic output bug: it is a crash on the only channel that reports whether a live write landed. **The July fix did NOT regress — it was never the right fix.** `516cbf7` (*"ASCII-safe CLI output"*, inside PR #20 / item 18) was 26 insertions in one file replacing `—`/`…`/curly quotes in `repair.py`'s **own string literals**; every character it removed *is* encodable in cp1252, so it was fixing OEM-console mojibake, and a literal sweep structurally cannot reach text that arrives over the wire. **A second sweep would not fix this either.** `0240cbb`'s pre-merge review then cleared *"Unicode track titles are safe — the rotating handler pins encoding=utf-8 (logging_setup.py:22)"* — true of the **log file**, and the console `print()` path was never in its scope. That is the exact moment the gap entered the record as a cleared item. **What has actually kept the tool alive is `$env:PYTHONUTF8=1`, which lives in two prose lines** (`SESSION_STATE.md:245` and the 2026-09-10 ADR's own command at `:77`) **and in no code** — the original runbook omits it, which is how the issue was filed. The fix is `sys.stdout.reconfigure(errors="backslashreplace")` on the stream, `errors` **only** and never `encoding` (pinned by a test: forcing UTF-8 also stops the crash but can turn a real OEM console's correct output into mojibake). **Eight emit sites carry card-derived text**, the widest being `:762` — `_diff_paths` builds `f"{path}: {a!r} -> {b!r}"` and Python 3's `repr()` does **not** escape printable non-ASCII, so `!r` is no protection. ⚠ **The CLI output layer has never been executed by a test**: `tests/test_repair.py` has 47 tests and imports neither `_print_card_result` nor `main`, nothing in `tests/` captures stdout, and `card_sample.json` is 100% ASCII — three layers of invisibility. See briefing notes. |
| 29 | 🚢 | **`overlayLabel` — the schema-required field this app has never sent, on a declared change-set** — **MERGED to `main` as [PR #34](https://github.com/mmackelprang/yoto-maker/pull/34) (`47829d4`); suite 411 → 437. **RELEASED as [v0.1.14](https://github.com/mmackelprang/yoto-maker/releases/tag/v0.1.14)** (`draft: false`, `prerelease: false`, asset `YotoMaker.exe` 127,022,603 bytes) and **verified**: published asset byte-for-byte identical to the local build (sha256 `720fede6…c9b8cc4d`), the frozen binary reports its own `0.1.14` from `/api/status`, a v0.1.13 client is offered it with a working URL, and a v0.1.14 client is offered nothing.** — twisting the player's right-hand knob brings up **no chapter list** on a multi-segment card ([issue #31](https://github.com/mmackelprang/yoto-maker/issues/31)). `git log --all -S overlayLabel` returns **nothing**: the string has never existed in this repository, though Yoto's published schema marks it **required** at track level. Replaces `repair.py`'s **format-only** safety invariant with an explicit **declared change-set** — one ordered `FieldEdit` list from which **both** the POST body and the verify's expectation are derived — then adds `overlayLabel` as a **second intent** on it. Value is unpadded 1-based `str(i)` at chapter **and** track level, from one shared `models.overlay_label()` that the create path and the repair path both call, written **only where absent or empty** | [ADR](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md) — **approved 2026-09-10, full declared-change-set variant (§3.1), not the minimal Option 4** | [plan](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) Tasks 2.1–3.9 | **28 must be on `main` first** (its crash lands after a live POST, and this arc's rollout writes to all three cards) | **HIGH. Ships as v0.1.14 — this arc owns the bump, which CORRECTS ADR §3.6's "no version bump"** (right about `__ASSET_V__`, wrong about the release: `updater.py` can only see a tag, and commit 1 changes every card made from here on). **One PR, three commit stacks in order 1 → 2 → 3, and the split IS the backout plan** — 1 = create path (reverts in a few lines), 2 = the behaviour-neutral refactor (**never reverted**; it closes blocker 2's *silent* half and is a net safety gain), 3 = the intent + `--no-overlay-labels` + the report strings + the rollback tolerance. ⚠ **Two ADR claims are FALSIFIED and the plan corrects them:** §1.1 and open question 1 argued the cards are still `mp3` and that the feature might be *inert* — the live read-only check says **all 24 tracks on all three cards are `opus`**, so the July write landed and Yoto **does** persist a client-supplied `format`. The ADR misread a **pre-write** backup as the post-write state, and misread the absence of an eleventh backup as "nothing ran" when an `already` card returns at `:626` **before** `_write_backup` at `:637`. **That also confirms blocker 1 is real, not defensive:** all three report *"already correct — nothing to do"*, so without the second decision axis the widened repair is a **silent no-op on every card that needs it**. **Do NOT restructure the N-chapters × 1-track shape** — it is canonical per Yoto's own examples and is not the bug. **`_VOLATILE_TOP_KEYS` gains no entry in this work** (ADR §1.3/§4.2.1; §3.5's rollback tolerance is not a precedent). ⚠ **The hypothesis is ~75–80% and only a physical player can close it** — nobody here has one; the maintainer's daughter's household does. A card that plays in the phone app is **not** evidence. See briefing notes. ✅ **That household closed it on 2026-09-11 — see OUTCOME 2026-09-11 at the end of this row. The ~75–80% is kept as the confidence that was correct to hold on 2026-09-10.** **OUTCOME 2026-09-10:** all three cards applied and each reported `verify ok` (`gzP2B` 2 changes, `1WCvI` 10, `7FcVe` 36) — so **Yoto persists a client-supplied `overlayLabel`**, since a dropped declared field now fires `unexpectedly REMOVED`. `gzP2B` and `1WCvI` re-read clean off the live API (`1..N`, unpadded, both levels, still `opus`). **`7FcVe` then began 404-ing on `GET /card` and that is unexplained — it was already missing from `/content/mine` BEFORE the write, nothing was duplicated, and rollback was deliberately not attempted.** **ADR open question 3 is CLOSED: `POST /content` REPLACES, not merges** — proved by driving the full apply→rollback→re-apply loop on `gzP2B`, so §3.5's tolerance never fires in practice. Blocker 1 confirmed live: the same three cards report `already correct` under `--no-overlay-labels` and `WOULD make N change(s)` without it. ✅✅ **OUTCOME 2026-09-11 — ISSUE #31 IS CONFIRMED FIXED ON HARDWARE, and the `overlayLabel` hypothesis is PROVEN rather than inferred.** On a **physical Yoto player**, on a multi-chapter card this arc had labelled: **the chapter list appears when the right-hand knob is twisted, and a chapter is selected by pressing it.** Tested by the maintainer's daughter. **ADR open question 2 is CLOSED** and §4.2.2 (*"we are writing an unproven field to live production cards"*) is **DISCHARGED**. **Which card is answered by the outcome itself** — only a multi-chapter labelled card can produce a list, so `1WCvI` (5 ch) or `ezeaM` (18 ch); `gzP2B` (1 ch) is excluded because there is nothing for it to browse under any hypothesis. *(The 18-chapter card is **`ezeaM`**. This row's OUTCOME 2026-09-10 above calls it `7FcVe` — that is the **stale ID**, corrected in the 2026-09-10 banner entry; the older sentence is left standing because it was written before the correction. One card, two names, not two cards.)* ⚠ **Proven narrowly: the player renders a browse list from `overlayLabel` and selection works. NOT proven and not tested — that the offline-download behaviour changed, or that the self-update swap-and-relaunch step works** (only the update *offer* was ever verified; `can_self_update` was false from source). **§8's backout plan and `--no-overlay-labels` both STAY** — historical justification, not live, and the flag is not removed. **Issue #31 was closed by the maintainer** (`mmackelprang`, 2026-09-11T23:21Z); Builder did not close it. |
| 30 | 📋 | **`yoto_maker/main.py`'s console output has item 28's exposure at a different entry point** — `main.py:43` builds the argparse `description=f"{APP_NAME} — {__version__}"`, so **every `--help` prints an em-dash**, and `:74` and `:89` print `— press Ctrl+C to stop.` `:34` prints `cfg.data_dir`, which carries the Windows username. None of it survives an OEM console (cp437/cp850), and `516cbf7`'s July sweep never looked at this file | — · the reasoning is [item 28's](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) §1.5/§1.9, **not** this row's design basis | _needs Planner pass_ | — · **28 on `main` first**, so the `_make_console_safe` helper exists to reuse rather than be reinvented | **LOW, and the contrast with item 28 is the whole row.** Same character class, **but no card-derived text and no emoji**, so the realistic failure is **mojibake on an OEM console, not a crash** — and crucially **nothing here happens after a live write**, which is the entire reason 28 is HIGH. Filed rather than folded in: 28 gates a live `--apply` run against three real cards and must stay small enough to land fast. **The cheap fix is to call item 28's `_make_console_safe()` at the top of `main.py:main` too**, not to sweep literals — the same argument as 28, and the helper will already exist. `packaging/yoto_maker_launch.py:19` is the only place in the repo that already builds a stream with an explicit `errors=`, and it is a **devnull sink** for windowed frozen builds (`sys.stdout is None`); it never touches a real console and does nothing for either CLI. Worth checking whether the frozen `.exe` path reaches any of these prints at all before spending anything here — it may close unshipped. |

### Item 28 — briefing notes

- **The crash is in the channel that reports whether a live write landed. That is
  the whole severity argument.** Order of operations in apply mode:
  `repair_card` POSTs at `repair.py:648`, returns a `CardResult`, and `main`
  prints it at `:831`. The print is where it dies. So the tool writes to a real
  card in a real account and then **denies the operator the one sentence that
  says whether the verify passed, where the backup is, or whether to roll back.**
  A dry run that crashes is an annoyance; an apply run that crashes here is a
  write you cannot reason about.
- **Do not fix this with a literal sweep, and do not fix it with the env var.**
  Both have been tried. `516cbf7` swept `repair.py`'s own literals — 26 lines,
  one file — and its message claims *"ASCII-safe CLI output."* It is not, and it
  never could have been: `d.ref.title` is assigned at `repair.py:317` straight
  out of Yoto's JSON, and no edit to a Python literal reaches it. The two also do
  not share a character class — em-dash, en-dash, ellipsis and curly quotes are
  **all** encodable in cp1252 (`0x97`, `0x96`, `0x85`, `0x91`–`0x94`), so that
  commit was addressing **OEM-console mojibake** (cp437/cp850), exactly as its
  message says. `U+1F916` is encodable in **no** single-byte Windows codepage.
- **The working mitigation lives in prose and in nothing else.**
  `$env:PYTHONUTF8=1` appears at `SESSION_STATE.md:245` and in the 2026-09-10
  ADR's own command at `:77`. It appears in **no code**, and the original runbook
  (`superpowers/plans/2026-07-21-repair-existing-cards.md:1316`) omits it — which
  is precisely why the command in issue #31's report crashes. A fix that depends
  on the operator remembering an environment variable is not a fix. **Keep the
  env var in the runbooks, re-labelled:** after this row it is optional, and the
  only thing it buys is `🤖` instead of `\U0001f916`.
- **A reviewer asked exactly the right question and a true answer closed it on the
  wrong stream.** `0240cbb` (*"chore(release): address pre-merge review"*) lists
  under **"Reviewed and cleared, not changed"**: *"Unicode track titles are safe -
  the rotating handler pins encoding="utf-8" (logging_setup.py:22), which matters
  given this codebase's cp1252 history."* That is correct —
  `logging_setup.py:22` genuinely pins UTF-8 — and it is about the **log file**.
  The console `print()` path was never in its scope. Worth remembering as a
  review failure mode: a true statement about an adjacent artifact can retire a
  question about the real one.
- **Eight emit sites, and the widest one is not the reported one.**
  `repair.py:740` (card title), `:742` (backup path — carries the Windows
  username), `:745` (the reported crash), `:760` (summary, interpolates the backup
  path), **`:762` (`res.problems`)**, `:793` (`--list` titles), `:804`
  (`resolve_targets`' ambiguous-title message, which interpolates **every**
  candidate's title), `:828` (`YotoError` text, i.e. `_friendly_http`'s
  sentences). `:762` is the widest because `_diff_paths` (`:460-478`) builds
  `f"{path}: {a!r} -> {b!r}"` over **arbitrary card field values**, and Python 3's
  `repr()` does **not** escape printable non-ASCII — so `!r` is no protection at
  all. Measured directly: `repr()` of a 🤖-bearing title still raises on a cp1252
  stream.
- **`client.py`'s non-ASCII copy is reachable from here and must NOT be edited.**
  `_friendly_http`'s 413 arm (`client.py:587-590`) carries `U+2019` and `U+2014`,
  and its timeout arm (`:594-597`) carries `U+2014`; both reach the repair console
  via `:804` and `:828`. They survive cp1252 but fail on an OEM console — the very
  case `516cbf7` was written for, left untouched in the module next door. **The
  `errors=` guard makes them safe without touching them**, and this family is
  item 26's open ownership question. ADR §4.2.5 says not to open a second one.
  (`client.py:550-554`'s `📁` is **not** reachable from repair — `too_big=` is
  passed only from `_put_audio`, the send path. A loaded gun pointed elsewhere.)
- **⚠ The structural finding, and it is the same shape as item 29's.** The CLI
  output layer **has never been executed by a test.** `tests/test_repair.py` has
  47 tests and imports 13 names from `yoto_maker.yoto.repair`; **neither
  `_print_card_result` nor `main` is among them.** There is no `capsys`, `capfd`
  or `capsysbinary` anywhere in `tests/`. And `tests/fixtures/card_sample.json` is
  **100% ASCII**, so even adding a capture test against the existing fixture would
  still not exercise a non-ASCII title. CI could not have caught this on a cp1252
  runner either, because nothing runs the code.
- **Force the codec; do not inherit it.** `tests/test_static_cache.py:99-127` is
  the repo's own precedent and carries the warning to honour: a behavioural
  encoding test *"cannot fail on a UTF-8-locale machine"*, so it pairs one with a
  canary plus a **source-level** assertion, and records that a looser source
  assertion once *"passed on the documentation while the actual argument was
  gone."* `_make_console_safe`'s docstring names `errors=`, `backslashreplace`
  and `PYTHONUTF8` as prose, so **a substring test would be vacuous** — assert on
  the call. Building a real cp1252 `TextIOWrapper` in the test is strictly better
  than the canary pattern: it fails on Linux CI too.
- **`yoto_maker/main.py:43`/`:74`/`:89` have the same literal exposure** (and
  `:34` prints `cfg.data_dir`, which carries the Windows username). Different
  entry point, no card data, lower stakes. **Filed as item 30 — do not fold it
  in**; this row gates a live write and must stay small enough to land fast.

### Item 29 — briefing notes

- **Read the plan's §1 before the ADR.** The ADR is approved and is the design
  authority, but **its own §1.1, its opening ⚠ box, its open question 1, its
  §4.2.3 and one sentence of its §4.1 are falsified**, and the plan's §1 carries
  the corrections with the evidence. A Builder who reads the ADR's first screen
  and stops will believe this feature may be *inert* and that commit 3 *must not
  be built*. Both are wrong.
- **What actually happened in July, since the ADR gets it backwards.** Two code
  facts settle it. **(1)** A backup is the **pre-write** snapshot —
  `_write_backup` is `repair.py:637`, the POST is `:648` — so the newest backup
  per card is the state **immediately before the last write that landed**, never
  after it. **(2)** A repaired card **stops producing backups**: once every track
  is `opus`, `repair_card` returns at `:626`, before `_write_backup` at `:637`. So
  *"no backup newer than 2026-07-22 08:56"* is the **signature of success**, not
  evidence that nothing ran. And the run the ADR called unexplained is explained:
  `edc3c6d` (the icon-canonicalization fix) was committed **08:42:13**, so the
  07:50, 07:51 **and 08:25** runs all predate it and all hit the Yoto 400 recorded
  at `repair.py:24-27`; the **08:54:00 / 08:54:51 / 08:56:07** runs — in exactly
  the documented `--card-id gzP2B,1WCvI,7FcVe` order — are the ones that landed.
  Every data point accounted for.
- **Blocker 1 is live on all three cards today, which is the strongest argument
  for the second decision axis — and the ADR hedges it.** `--dry-run` on
  2026-09-10 returns `already correct … nothing to do` for `gzP2B`, `1WCvI` and
  `7FcVe`. `CardPlan.outcome` returns `"already"` when `correct_keys` is empty, and
  `repair_card` then returns at `:626-630` **before** the backup and before the
  POST. **So a card needing only a label writes nothing at all** — a silent no-op
  on the only three cards that can test the hypothesis. ADR §3.2's
  `change_set`-based outcome is what fixes it, and `correct_keys` must be
  **retired**, not kept alongside: any surviving caller is a latent
  "writes nothing" bug of exactly this kind.
- **Commit 2 is the most dangerous code in this repo and nothing else guards it.**
  `verify_only_declared_changed` is the last line of defence before a live card in
  a real account is rewritten, and a bug there **does not fail loudly — it
  approves a bad write.** Three mitigations, all required: commit 2 is
  behaviour-neutral and **`test_corrector_sets_only_format_everything_else_byte_identical`
  (`test_repair.py:247`) must pass UNMODIFIED** through the retained
  `apply_format_corrections` wrapper; the change-set asserts at most one edit per
  path; and `apply_change_set` **raises** rather than creating a missing
  intermediate container. **If an existing safety test cannot pass without being
  weakened, stop and ask** — that is the signal behaviour changed.
- **Commit 2 is never reverted, and that is the point of splitting it from 3.**
  ADR §8 deliberately omits it from the backout levers: the change-set invariant
  is worth keeping whatever happens to the hypothesis, because it closes blocker
  2's **silent** half. Under format-only, a server that strips a field we declared
  reported **`applied`** while the fix had not landed; under the change-set it
  reports `verify-failed` with `unexpectedly REMOVED`. Given that `POST /content`
  demonstrably enriches and derives — it adds **16 keys we never send** (ADR
  §1.4) — that is the branch most likely to fire in the field. **Never revert 2 to
  back out 3.**
- **`--no-overlay-labels` is not a convenience, it is the in-code backout** (ADR
  §8 lever 1), which is why it must ship **with** the intent rather than being
  added if needed. It defaults **off** (labels on), so the default behaviour is
  the intended one and the lever is explicit.
- **The value is `"1"`, never `"01"`, and it must never be read from `key`.** The
  real bodies carry `key: "01"`; Yoto's own sample app writes
  `overlayLabel: "1"` in the **same object literal** as `key: "01"`. `key` is a
  padded identifier; `overlayLabel` is display text. ⚠ **Deriving the label from
  the card's own `key` is forbidden**: one path reading `key` and another
  computing from the index could disagree, and two runs would flip-flop forever.
  The only input is the positional ordinal, through the one shared helper.
- **An existing non-empty `overlayLabel` is never overwritten.** This is not only
  idempotency — it stops the tool flip-flopping against **another editor**. A user
  who types `"Chapter 1"` in the Yoto app would otherwise have it reset to `"1"`
  on every run, forever.
- **`declined` must never cost a card the proven fix.** An unprobeable artifact is
  a correctness hazard and blocks the card; a label we cannot confidently number
  is not. Without `declined`, an unusually-shaped card would lose access to the
  **proven** format fix because of the **unproven** label one. The plan also
  settles what the ADR left ambiguous: a multi-track chapter declines **both**
  levels, because writing the chapter label alone would leave the
  schema-**required** track field missing while making a later run's idempotency
  check see a labelled chapter and skip — a partial job that permanently hides
  itself.
- **⚠ `_VOLATILE_TOP_KEYS` (`repair.py:400`) gains no entry in this work. Not
  one.** It would blind `_strip_volatile` to `overlayLabel` in **both** bodies, so
  the verify could no longer see the field it exists to control — including a
  value Yoto changed on its own. Two prior agents flagged this independently. ADR
  §3.5's rollback tolerance is **not** a precedent and the difference is
  structural: rollback-path-only, single-field, presence-only, report-line-only.
- **The structural test gap is the real lesson, and it is why a test comment is a
  deliverable.** Nothing in the suite is an **absolute** equality against a
  **populated** chapter or track. `test_repair.py:257` does compare a whole body,
  but against a **deepcopy of its own input** plus one known delta — relative, so
  structurally blind to a field its fixture never had. `test_repair.py:141` is
  absolute but against an **empty** chapter list. (⚠ The ADR §4.1's phrasing,
  *"the only exact-equality assertion in the suite,"* is false as written — there
  are several; the absolute-vs-relative distinction is the accurate version and
  the stronger argument.) **That is how a schema-required field stayed missing for
  the life of the project**, and the new test must carry a comment saying so.
- **⚠ Assert on what a report string CONTAINS, never on what it lacks.** Item 20's
  guard asserted `"100 MB" not in msg` and a ruling **deleted that number**, so the
  guard went **vacuous and still passed** (`SESSION_STATE.md:175-178`). The three
  rewritten summary strings are the same shape in the same file. A string change
  can silently disarm the test that guarded the string.
- **The report strings are self-contradicting today, not merely stale.** A card
  whose format is already right but whose labels are missing would print
  *"already correct (all 18 tracks 'opus')"* **and then write.** `already` now
  means *every declared intent is satisfied*, not *every track is opus*.
- **These three strings are copy that no handoff package owns — cross-reference
  item 26, do not open a second ownership question.** Item 26 already records that
  three of `_friendly_http`'s sentences are reachable only from `yoto/repair.py`,
  and notes it is *"not plain LOW because `repair.py` mutates live production
  cards, where a misleading error is read by someone deciding whether a write
  landed."* The new strings inherit that verbatim. **No Designer pass is needed
  for this row** (ADR §4.4) — this is a maintainer CLI with no UX.
- **Do NOT restructure the card.** The N-chapters × 1-track shape is canonical per
  Yoto's own examples and is **not** the bug — the real bodies prove 1, 5 and 18
  chapters respectively. Three dead ends are confirmed and must not be revisited:
  `playbackType` (the server stamps `"linear"` on all three regardless of chapter
  count), missing `chapter.display` (every chapter and track in all ten bodies
  carries a resolved `display.icon16x16`), and "the segments never became
  chapters".
- ✅ **CLOSED ON HARDWARE 2026-09-11 — the knob-browse half of this bullet is
  answered, the offline-download half is not.** The bullet is kept as written
  below because it is the record of the uncertainty that was correct to hold
  before the test. **What happened:** the maintainer's daughter twisted the
  right-hand knob on a labelled multi-chapter card and **the chapter list
  appeared; pressing the knob selected a chapter.** So `overlayLabel` **does**
  gate the knob-browse UI. ⚠ **The offline-download question in the same bullet is
  untouched by that result and remains open** — it was never the same question,
  and nothing was watched with wi-fi off. The Wild Robot confound also stays live.

  *(As written before the test:)* **⚠ Only a physical player can close this, and
  nobody on this project has one.**
  The hypothesis — that `overlayLabel` gates the knob-browse UI — is **inference
  from a required field plus an official example**, ~75–80%. **No Yoto document
  says it**, and Yoto's own description says *"used in the app"*, not *the
  player*. The maintainer's **daughter's** household has the player and can run
  the whole loop herself (`SESSION_STATE.md:215-255`). Test on **`1WCvI`**
  (5 real chapters) — **`gzP2B` is useless for this**, it has 1 chapter and would
  show nothing under any hypothesis. **The question that matters is whether the
  offline download completes**, with wifi off, watching the download-cloud icon:
  streaming in the phone app will likely work even on a malformed card, which is
  why this bug survived three releases. **A card that plays in the app is NOT
  evidence of a fix.** And the **Wild Robot confound is still live** — do not test
  `1WCvI` against a second Wild Robot card made by the save-to-folder path.
- **One rollout step answers an open question for free.** After the first
  successful `--apply` on `gzP2B`, immediately `--rollback` the fresh backup:
  `restored` → `POST /content` **replaces**; `verify-failed` naming `overlayLabel`
  → it **merges**, and §3.6's tolerance is what keeps that from reading as a
  failure. **Record which.** The tolerance ships either way.
- **This arc owns the v0.1.14 bump, which corrects the ADR.** ADR §3.6 says *"no
  version bump"* — right about `__ASSET_V__` (nothing under `server/static/` is
  touched) and **wrong about the release**: `updater.py` can only see a tagged
  release, and commit 1 changes every card the app makes from here on. ⚠ **Write
  the release note honestly** — describe what the app now *sends*, never a knob
  behaviour nobody has observed. ✅ **2026-09-11: the knob behaviour HAS now been
  observed, so the release notes state it** — as a dated hardware confirmation of
  the chapter list only. The same honesty rule still bites on what was *not*
  observed: the offline download and the self-update swap-and-relaunch step.

### Item 25 — briefing notes

- **Designer's framing is the row's argument, quoted because paraphrase loses
  it.** `interactions.md` §4b.5: *"`#sendError` has neither `role` nor
  `tabindex` (`index.html:195`), so **nothing is announced and focus does not
  move**. … But the cost of leaving it has gone up. Until now the region held
  messages a user could act on by re-reading the screen. It now holds the app's
  only cross-path recovery pointer, and **a pointer that is never announced does
  not point**."* §11 item 3's re-weighting box carries the instruction this row
  exists to honour: it *"should be read as an **accessibility gap on a shipped
  recovery**, not as a nicety inherited from §9's unshipped message."*
- **It got worse; it did not newly appear — and the earlier decline was not an
  error.** `copy.md` §9.3 declined `role`/`tabindex` when `#sendError` held only
  transport lines, whose recovery was on the same screen and needed no
  announcement to be found. §10 changed what the region carries without changing
  the region, and **both §10.5 and §4b.5 leave the decline standing while
  recording that it now costs more.** A Planner pass should treat the earlier
  decline as a decision whose inputs changed, not as a mistake to correct.
- **Why it was not folded into item 20's string fix.** A live region changes
  announcement behaviour for **every** shipped send failure, not only the 413.
  Folding it in would have meant PR #27 shipping an untested announcement change
  across four strings it was never scoped to touch, inside a PR already blocked
  on a copy question. **Two attributes is the size of the diff, not the size of
  the change** — the row needs its own UAT and must not be picked up as a quick
  win.
- **The pattern question, with the numbers behind it.** `index.html` has eleven
  `.msg-box err` regions. **Seven** carry `role="alert"` — `#addError:114`,
  `#connectWarn:210`, `#exportError:245`, `#exportOpenError:271`,
  `#accountMsg:357`, `#clientIdMsg:428`, `#helpMsg:522` — and five of those also
  carry `tabindex="-1"`. **Four** carry neither: `#toolsWarning:49`,
  `#picError:161`, **`#sendError:195`** and `#labelError:294`. So `#sendError`
  is an outlier against the app's own majority pattern but is **not unique**,
  and item 12's rule applies — *fix the pattern or accept it, do not
  special-case one control*. The difference from item 12 is that here one of the
  four has an argued reason to go first, and this row is that argument. Whether
  the deliverable is one attribute pair or four is the Planner pass's to settle.
- **`tabindex` is a separate decision from `role`, and the tree already carries
  the precedent for not conflating them.** `index.html:242-246` records why
  `#exportDone` gets `tabindex="-1"` and deliberately **no** role: focus is moved
  to it, and a role as well would announce it twice. Nothing moves focus to
  `#sendError` today, so *announce*, *focus*, or *both* is a real question with
  three real answers.
- **Verification is this row's actual cost, exactly as it is item 22's.**
  **Nobody on this project has a working screen reader** — NVDA is not installed
  and Narrator's speech cannot be captured as text. v0.1.9's reveal toggle and
  v0.1.10's `#yotoPill` accessible name both shipped **unheard**, each recorded
  under *Not verified* rather than claimed. A row whose entire deliverable *is*
  an announcement cannot repeat that and still be called shipped. Budget for a
  real screen reader, or say plainly in the PR that nobody heard it.

### Item 26 — briefing notes

- **What is claimed, and what is not.** No sentence in the family is known to be
  wrong. `copy.md` §10.4's boxed note is the entire finding: *"`_friendly_http`'s
  five sentences — the 401/403, the 413, the 5xx, the timeout and the fallback —
  are shipped user-facing copy owned by **no** handoff package, and this one is
  reached from the repair path as well as the send path. It is ruled here because
  it is the other half of the branch §10.1 changes. Adopting that family into a
  package of its own is worth a queue row and is **not** done here."* §10
  ratified one of the five. **Four are left.**
- **Why an ownership gap earns a row at all — the evidence is item 20 itself.**
  The 413 sentence named *"max 5 hours per card"*, the **card-level** ceiling, at
  the moment of a **per-track** refusal. It dates to `b40c702` and is present in
  `yoto_maker/yoto/client.py` at **v0.1.2** and at **v0.1.12** (both checked), so
  it shipped in every tagged release the project has cut. It was not caught by
  review, by tests, or by use — it was caught when someone finally wrote down
  what the string was supposed to say, and that writing-down happened only
  because item 20 forced it. **That recurrence is the only thing this row
  prevents, and preventing it is the whole value.**
- **The multi-path reach is the first question a Planner pass must answer, not a
  detail to note in passing.** Verified against `main` at `3330f2c`:
  `_friendly_http` is raised from **nine** sites across **seven** methods,
  carrying **seven** distinct `{doing}` phrases. **Three are reachable from
  `yoto/repair.py`** — `get_card` (*reading the card*), `list_my_cards`
  (*listing your cards*) and `update_card` (*saving the repaired card*), the
  last of which **only** the repair path calls. The family is therefore not
  send-path copy the repair CLI happens to borrow; it is **shared copy with two
  callers and no owner.** `export-only-mode/` is the wrong home, and §10.4 says
  so about its own ruling — the generic 413 sits there because it is the other
  arm of the `if` §10.1 had to change, not because it belongs there. The home
  decision gates everything else: a new package, a section of
  `configuration-surface/`, or a document that is not a handoff package at all.
- **One figure in the existing record does not survive checking.** Item 20's
  briefing above and `copy.md` §10.4 both say `_friendly_http` is *"shared by six
  call sites."* Nine raises, seven methods, seven `{doing}` phrases — no counting
  of the current tree yields six. §10.4's argument (no single ceiling can be
  right for all callers) holds for any count above one, so nothing ratified
  collapses. **Re-count before reusing the number, and do not correct it in the
  handoff as a drive-by** — it sits inside a ratified section, so the correction
  is Designer's.
- **The `{doing}` asymmetry must be carried forward, not tidied away.** The 5xx,
  timeout and fallback sentences interpolate `{doing}`; §10.4 rules that the 413
  branch deliberately does **not**, because two call sites are reads and *"Yoto
  wouldn't take that while listing your cards"* is a sentence about nothing. An
  adoption pass that makes the family "consistent" would undo a ruling. Same
  class as item 19's acts-on-format / advises-on-size asymmetry: reads like an
  oversight, is a decision.
- **Scope honesty — this row may correctly ship no code.** If the four sentences
  are found sound, the deliverable is documentation: a `docs/` PR, no behaviour
  change, row closed. That is success, not under-delivery. It is marked
  `_needs Designer pass, then Planner only if anything ships_` for that reason,
  and **a Builder that finds this row eligible without a Designer ruling in hand
  has misread it.**

### Item 22 — briefing notes

- **The string is written, approved and sitting in the handoff. Do not rewrite
  it.** [`copy.md`](design-handoffs/export-only-mode/copy.md) §9 carries the
  three paragraphs verbatim, under a banner that says *NOT SHIPPED* and why.
  This row is a shipping row, not an authoring row, and a Planner pass that
  reopens the copy has misread it. §9.2 already answers the obvious
  refactor — *"why is this not one string shared with §5.10?"* — with the test
  the package's own §3 rule states: **the recoveries are not identical.** Save
  sends her to her Documents; send sends her to the Yoto app on her phone. And
  **both boxes can be on screen at once** (`#exportRow` sits directly beneath
  `#sendError` by design, `overview.md` §4.3 point 2), so a single shared
  sentence would put the same words in two red boxes fourteen pixels apart.
- **The retry is opt-in per call site, and that is a design rule rather than an
  implementation convenience** (`interactions.md` §4a.1, `copy.md` §9.1).
  `pollJob` has **four** call sites, and `doUpdate()` (`app.js:167-171`)
  *catches every poll failure and reports success* — the server exits
  mid-restart, so the last poll failing is the expected end of a self-update.
  Retrying there would freeze a bar for the whole retry window before showing a
  message that was already correct. **The same transport event means different
  things on different paths.** Item 19 already shipped the opt-in mechanism
  (`saveToFolder` passes `retryWindowMs`), so this row adds one caller, not a
  mechanism.
- **Why it costs more than its diff suggests, and this is the row's real
  constraint.** Verifying a send-path retry needs a **live authenticated send
  against a real Yoto account** — the exact dependency this whole feature area
  exists to route around — and a wrong-but-plausible implementation fails in
  the direction of *"the app told her nothing happened when a card was
  created."* Budget for the live send; do not accept a green unit suite as
  evidence that this works. There is no way to simulate the interesting case
  (a dropped poll *after* a job id exists) without one.
- **What is deliberately not in scope** (`copy.md` §9.3, all three still
  standing): `#sendError` gains no `role` and no `tabindex` — making it a live
  region changes announcement behaviour for **every** shipped send failure and
  deserves its own pass and its own UAT. `#sendDone`, `#sendBtn`,
  `#sendProgress` and the send flow's control logic are untouched. The YouTube
  add path does not opt in — its dropped-poll message asserts nothing false and
  the uncertain outcome is visible on the same screen.

### Item 23 — briefing notes

- **The mechanism, exactly.** `saveToFolder` disables `#exportBtn`
  (`app.js:2364`) and re-enables it only in its `finally` (`app.js:2420-2424`).
  `#startOver` (`app.js:2670-2701`) bumps `exportSaveGeneration`, clears all six
  `#export*` regions and resets the draft — but never touches
  `#exportBtn.disabled`. The generation bump makes the in-flight run *silent*,
  not *finished*: its `await pollJob(...)` is still outstanding, so the button
  is dead until that promise settles, with `#exportProgress` already hidden and
  nothing on screen accounting for it. Reachable by pressing exactly the two
  buttons the screen offers, which is the same standard item 19 used when it
  added the generation guards in the first place.
- **Why the obvious fix is worse, stated so nobody has to rediscover it.**
  Adding `$("#exportBtn").disabled = false` to the `#startOver` handler makes
  a second save startable while the first is **still writing on the server** —
  `jobs.py` has no cancellation, deliberately (item 19's briefing, item 15 /
  [ADR §3.2](architecture/decisions/2026-07-21-file-upload-on-job-system.md)).
  And the disowned run's `finally` block is **not** generation-guarded, unlike
  its `catch` (`app.js:2390`) and its progress callback (`app.js:2382`): when
  it eventually fires it runs `show($("#exportProgress"), false)` and
  `$("#exportBtn").disabled = false` against whatever run is current, hiding
  the **second** save's progress bar mid-write. A stuck button becomes a save
  that appears to have stopped and has not.
- **What Designer actually has to rule**, before any plan is written: what the
  save button *means* while a job the user has discarded is still writing to
  the discarded card's folder. Offering it immediately invites two concurrent
  writes and the `(2)`-folder semantics of `copy.md` §5.8 in a case §5.8 was not
  written for; leaving it disabled with no visible reason is today's bug. The
  answer decides whether the fix is a guard in `finally`, a visible
  *"still finishing the last one"* state, or something else — and only then is
  it a Planner pass. **Marked `_needs Designer pass_` for that reason, not as a
  formality.**

### Item 24 — briefing notes

- **What actually happens.** `JobManager.start`'s worker (`jobs.py:63-73`) is
  `try / except Exception`. A `BaseException` — `SystemExit`,
  `KeyboardInterrupt` — propagates out of `run()` and dies with the thread,
  leaving `Job.status` at its initial `"running"` (`jobs.py:20`) with
  `error` still `None`. There is no timeout, no watchdog and no eviction, so
  `/api/jobs/{id}` answers `running` **successfully** forever. That is what
  makes it worse than a crash: `pollJob`'s retry window
  (`POLL_RETRY_WINDOW_MS`, 12s) is spent only on *failed* polls, and these
  polls succeed. The bar freezes, the originating button stays disabled, and a
  page reload is the only exit.
- **Shape of the fix, for the Planner pass.** The `except` clause is the whole
  of it — catch `BaseException`, record the terminal state, then re-raise so
  interpreter shutdown still behaves. It is ~3 lines in one function and it
  needs a test that asserts a job whose target raises a `BaseException` does
  **not** stay `running`.
- **Why this is its own row and not a fold-in to item 14 — the check the row
  claims, written out.** Item 14 owns the `POST /api/tracks/file` migration and
  the *client contract* around job failure: `err.data.reason` + `retryable`
  precedence, and mapping a `/api/jobs/{id}` 404 to *"Yoto Maker restarted"*
  ([ADR §5.2.3](architecture/decisions/2026-07-21-file-upload-on-job-system.md),
  §4.3). Item 15 adds a `cancelled` terminal state. **Neither reaches this
  defect**: every terminal-state discussion in the ADR is about *which* terminal
  state a finished job reports, and this is a job that never reports one. The
  ADR's nearest neighbour is §5.2.3 — a job killed by an app restart, whose id
  then 404s — and it is the **opposite** case: there the client gets a legible
  signal and item 14 is told to map it to *"Yoto Maker restarted"*. Here the
  process is alive and answering `running` successfully, which is precisely why
  nothing downstream notices. Item
  14 is additionally ⛔ behind an ADR that is still `proposed`, so a fold-in
  parks a live defect on two shipped paths behind an approval that has not
  happened.
- **The overlap that is real, and the rule for it.** Both this row and item 14
  want `tests/test_jobs.py`, and it does not exist — `jobs.py` has zero test
  coverage, which item 14's row already flags as its load-bearing risk.
  **Whichever lands first creates the file; the second adds cases to it.** If
  item 14 is claimed while this row is still 📋, **fold this in as a task in
  item 14's plan and retire this row** — do not ship both. A Builder that finds
  both eligible should say so rather than guess.

### Item 19 — briefing notes

- **The whole point is that it needs no sign-in.** `POST /api/export` takes the
  two guards at `app.py:634-638` and **not** the connection check at `app.py:640`.
  A reviewer who "fixes" the missing auth check has deleted the feature: the user
  this exists for is the one whose sign-in is broken or has never happened, and
  who is currently stopped dead at step 3 by a disabled `🚀 Send to Yoto`. Guarded
  by `test_saving_needs_no_sign_in`. The plan's §Global Constraints says the same
  thing louder.
- **The track list, the icons and the card name come from the SAME code as the
  send path**, and that is a design requirement rather than tidiness (spec §3.1,
  acceptance criterion 8). Task 7 extracts `_build_card_inputs()`; **`_resolve_icon`
  must be CALLED, never reimplemented** — it is lazy and has a filesystem side
  effect (`make_device_icon` writes `work/icon_<id>.png`), and it is the reason a
  card saved to a folder carries the same pictures as the same card sent to Yoto.
  `send_to_yoto()` must produce a byte-identical `TrackInput` list afterwards.
- **The app ACTS on format and ADVISES on size, and that asymmetry is the design.**
  `{".mp3", ".m4a", ".aac"}` are copied byte-for-byte **even when oversized**;
  everything else becomes a **192 kbps** MP3. A reviewer who notices that the app
  re-encodes a FLAC but only warns about a 120 MB MP3 has found the design, not a
  bug (spec §2.4, `overview.md` §8.6). **192 kbps is arithmetic, not taste:** the
  splitter bounds a track at 50 minutes, and 50 minutes at 192 kbps is ~72 MB —
  under Yoto's 100 MB per-track cap. Anything above ~265 kbps breaks that
  property. Do not "improve" the bitrate.
- **Export never splits.** `split_audio` already ran at *add* time (`app.py:235`)
  and each part is already its own `Track` with a `(part N)` title
  (`app.py:243`). There is no "splitting…" progress phase. This corrects the
  original brief (spec §4.1) and is the kind of thing an implementer re-adds from
  memory.
- **No Cancel button, and this is a decision.** `jobs.py` has no cancellation;
  the `#addCancel` precedent aborts a frontend `fetch` on the *synchronous*
  upload path and has no equivalent for a job. Adding one is Architect-scoped work
  and is queue item 15 / the job-system ADR §3.2. Do not introduce
  `#exportCancel`, do not add a `cancelled` state, **do not touch `jobs.py`**.
  One consequence the plan works around: `jobs.py` carries only `str(exc)` and no
  reason code, so the cause-specific line of `copy.md` §5.7 is composed
  server-side and the fixed first/third paragraphs in `app.js`.
- **`styles.css` is not modified. At all.** Acceptance criterion 10 makes a diff
  there a signal that something in spec §2 was reinterpreted. Everything is built
  from `.btn`, `.btn.primary`, `.tiny`, `.progress`, `.bar`, `.msg`, `.msg-box`
  (+`err`/`ok`/`info`), `.done-actions`, `.mono-value`, `.hidden`. **No
  `.msg-box.warn`** — `tokens.md` §1 refused that variant and this is not the
  amendment that overturns it. Nothing failed when a note appears.
- **This PR owns the v0.1.12 → v0.1.13 bump and it is not optional.** It is
  almost entirely `app.js` + `index.html`, and the version string is the asset
  cache key (`?v=__ASSET_V__`). Without the bump an already-running browser keeps
  serving the old script against the new markup — queue item 8's bug with a new
  payload.
- **Two things nobody can verify, and the plan says so in its Test Plan §Z rather
  than leaving it implied.** The maintainer has **no Yoto player** (his daughter
  owns it, in another state), so the motivating defect — a physical player's
  offline download never completing — cannot be observed by anyone in this PR.
  ⚠ **Streaming in the phone app will likely work fine even on a malformed card;
  that is why the bug survived three releases. A card that plays in the app is
  NOT evidence of a fix.** The plan carries a three-question checklist to send
  her. The planned first real card (*The Wild Robot*, ~3h50m → ~5 parts of ~72 MB,
  ~330 MB) exercises multi-part splitting and filename ordering but reaches **no**
  Yoto ceiling, so the 100 MB advisory ships unverified against a real file unless
  Test Plan §B4 is run.
- **`copy.md` is the authority on strings, and one mockup is stale.**
  `mockups/step-3.md` §7 still shows §5.4's pre-amendment wording (*"2 of your
  files weren't MP3s…"*), which was amended because it is quietly misleading once
  `.m4a` is copied as-is. Use `copy.md`. The plan's §Deviations lists seven more
  gaps and judgement calls, including three one-sentence strings it authors
  because nothing in `copy.md` covers them — Designer should confirm those.

### ⛔ Blocker — item 20 *(filed 2026-09-06 by Builder — **RULED and cleared the same day; the ✅ block at the end of this section is the answer**)*

**PR [#27](https://github.com/mmackelprang/yoto-maker/pull/27) is open and green
but deliberately unmerged.** Everything except one string is done: 390 tests,
both review gates run, UAT passing where it can run. **Planner reconciles this;
Builder does not unblock its own items.**

*(It was reconciled by **Designer**, not Planner, and that is the right lane
rather than a shortcut: the blocking question was a **cross-path pointer** —
whether a send failure may re-frame itself as *use the other button* — which is
copy plus a rule about what two controls mean to each other, not a plan. The
rest of this section is the diagnosis as Builder filed it, kept verbatim because
the ruling is only legible against it.)*

**What is blocked, precisely:** the per-track 413 string plan §7.1 authored
rather than routing through Designer. The copy gate returned **NEEDS A REAL
DESIGNER PASS**; Builder reproduced both grounds rather than relaying them.

1. **It refutes itself in the most likely case.** `int(round(size/1_000_000))`
   means every size in **100,000,001–100,500,000** renders *"Yoto's limit is
   100 MB, and this one is 100 MB"* — immediately after asserting the file is
   bigger than the limit. A file just over a ceiling is the *modal* refusal.
   `copy.md` §5.9's whole-MB rule is safe only because it prints the size in a
   **list parenthetical**, several words from the ceiling; §7.1 borrowed the
   rule into a single comparative clause, a construction §5.9 never ratified.
2. **Its recovery clause names the wrong variable.** *"If you have a shorter
   recording of it"* aims at duration, but `app.py:263` splits every source at
   `MAX_TRACK_SECONDS` (50 min) unconditionally, so duration cannot be the
   cause. The population hitting this message is a 10–50 minute WAV or FLAC
   (CD-quality stereo WAV crosses 100 MB at ~9.5 min). The remedy that *would*
   work is `📁 Save the files to a folder` on the same screen, which converts
   `.wav`/`.flac` to 192k MP3 (~72 MB) — and the string does not mention it.

**Why Designer and not Planner or Builder:** `export-only-mode/copy.md` §5.7
ratifies the cross-path pointer in one direction (*save → send*). The mirror
image (*send → save*) has **no ratified string in either handoff package**, and
re-framing a send failure as *use the other button* is state-machine-adjacent,
not a wording tweak. Note also §5.9's strings remain **not** verbatim-reusable
here (plan §1.4) — that finding stands.

**Also flagged, non-blocking (MEDIUM):** the generic 413 string *"Yoto wouldn't
take that — it was too big to send."* is the only dead-end sentence in the app's
error vocabulary; every other `_friendly_http` branch ends in an action.
`configuration-surface/copy.md` §4d's *"tell whoever set Yoto Maker up for you"*
is the ratified pattern. Verdict was SHIP WITH NIT — fold it into the same pass.

**The smallest honest unblock, if a full Designer pass is not wanted:** drop
string 1's third sentence. That removes the wrong-axis advice, leaves the
factually-correct correction in place, and does not pre-empt the ruling. It does
**not** fix ground 1. **Builder did not take that option unilaterally** — it is
still a copy change on a shipped user-facing path.

**Do not fix ground 1 by comparing bytes against the figure.** Plan §2 forbids a
comparison in `client.py` and calls that absence the design. The pre-merge
reviewer independently reached the same conclusion and labelled it
DEVIATES-FROM-PLAN. This is the natural companion to plan §8's live probe, which
was **not run** — it needs the maintainer's authenticated Yoto account and was
not authorised. Item 21 stays open pending it, and per §8 may close unshipped.

### ✅ RULED — Designer, 2026-09-06. The design blocker is cleared.

**The ruling is in the handoff, not here.**
[`design-handoffs/export-only-mode/copy.md`](design-handoffs/export-only-mode/copy.md)
**§10** is the authority on both strings;
[`interactions.md`](design-handoffs/export-only-mode/interactions.md) **§4b** is
the rendering contract; `mockups/step-3.md` §3 is redrawn to match. Builder
implements from §10 verbatim, re-runs the copy gate against it, and merges.
**Nothing below replaces §10 — it is a summary for the reader of this file.**

**The two strings, as ruled:**

| Where | String |
| --- | --- |
| 413 from the track PUT | `Yoto wouldn’t take “{title}” — it’s bigger than Yoto allows for a single track. No card was made in your Yoto account. There’s another way to finish this card: press “📁 Save the files to a folder” below.` |
| No title available | `Yoto wouldn’t take one of your tracks — it’s bigger than Yoto allows for a single track. No card was made in your Yoto account. There’s another way to finish this card: press “📁 Save the files to a folder” below.` |
| 413 from anywhere else | `Yoto wouldn’t take that — it was too big to send. Tell whoever set Yoto Maker up for you.` |

**Ground 1 is fixed by printing no number at all** — not Yoto's ceiling and not
the file's size. The rounding never has to be right because nothing is rounded,
**and no byte comparison is introduced, so plan §2 stands untouched.** Three
reasons in `copy.md` §10.2; the one that matters most for this queue is the
third: **the refusal is observed, the 100 MB figure is not.** The string now
survives plan §8's probe whatever it finds, which is what *"if a live test
disagrees, the test wins"* looks like when applied before the test runs.

**Ground 2 is fixed by pointing at `📁 Save the files to a folder`**, which is
the cross-path pointer this was escalated for. It is ratified in
`export-only-mode/` because it quotes that package's button label and depends on
that package's placement — so a future relabel finds it. `copy.md` §10.3 carries
why it does not contradict §1, and why it **promises nothing**: an oversized file
already in the copy-as-is set is copied untouched (`export/rules.py:46-47`), and
for that minority §5.9's advisory fires on the other side naming her exact file.
**The pointer is deliberately not conditioned on file type.**

**Also ruled, closing the MEDIUM nit:** the generic 413 gains
`Tell whoever set Yoto Maker up for you.` — configuration-surface `copy.md` §4d's
ratified pattern, already shipped in `app.js:2267`. No retry hedge, and `{doing}`
is deliberately not interpolated (`copy.md` §10.4).

**Three things Builder must not do**, each of which would look like an
improvement:

1. **Do not print the size, in any rounding.** Ground 1 is closed by absence.
2. **Do not touch `#exportRow`** — no highlight, no scroll, no focus move, no
   state on `#exportBtn` (`copy.md` §10.5, `interactions.md` §4b.3).
3. **Do not give `#sendError` a `role` or a `tabindex`.** `copy.md` §9.3's
   decline stands; `interactions.md` §4b.5 records that it now costs more and
   §11 item 3 is re-weighted, not reopened.

**The existing tests will need updating, and one is a design assertion.**
`tests/test_send_size_limits.py:189`
(`test_track_too_big_message_names_the_track_the_limit_and_the_size`) asserts the
number this ruling removes. **Do not weaken it into nothing** — replace it with
the inverse guard: the message names the track and contains **no** MB figure and
**no** *"100"*. That is the assertion that stops the number coming back.

**Left blocked deliberately:** nothing in item 20. Item 21 is untouched by this
ruling and stays blocked on the live probe. `_friendly_http`'s other four
sentences remain **unowned by any handoff package** — recorded in `copy.md`
§10.4 and worth a Planner row, not fixed here.

### Item 20 — briefing notes

- **The defect.** `split_audio` is called at add time with
  `max_seconds=MAX_TRACK_SECONDS` (`server/app.py:235`), and `MAX_TRACK_SECONDS`
  is `50 * 60` (`audio/normalize.py:191`). That clears Yoto's **60-minute**
  per-track limit with margin. **Nothing anywhere checks bytes**, and Yoto's other
  per-track limit is **100 MB**
  ([support.yotoplay.com](https://support.yotoplay.com/en_gb/how-much-audio-fits-on-a-make-your-own-card-r1ssdFimfl),
  published 2026-07-20).
- **Why that bites in practice.** The app does **not** transcode local files —
  `AudioFileAdapter.fetch` (`sources/audiofile.py:26-61`) is a `shutil.copy2` plus
  a probe and a tag read — and `SUPPORTED_EXT` admits `.wav`, `.flac`, `.ogg`,
  `.opus` and `.mp4`. A 16-bit/44.1 kHz stereo WAV runs at ~176 KB/s, so it
  crosses 100 MB at about **9½ minutes** and a 50-minute one is **~529 MB**. FLAC
  is roughly 60% of that. The 50-minute split does not catch either. YouTube
  sources are immune (always `.mp3` at 192 kbps, ~69 minutes to reach 100 MB,
  which the split already bounds).
- **The secondary defect sends the user to the wrong fix.**
  `yoto_maker/yoto/client.py:481-482` maps a 413 to *"That audio file is too big
  for Yoto (max 5 hours per card)."* — the **card-level** ceiling, named at the
  moment the user has almost certainly hit the **per-track** one. This half is
  cheap and is worth fixing whatever is decided about splitting.
- **Independent of item 19 in both directions, and worth understanding why.**
  Export-only mode converts anything outside `{.mp3,.m4a,.aac}` to 192 kbps MP3,
  which is ~72 MB at the same 50-minute bound — so the size cap is
  solved-by-construction on that path for every file it touches. The **send** path
  converts nothing, so it is not. Neither item blocks the other.
- **Provenance caveat, carried forward from item 19's spec §8.2.** The 100 MB
  figure is Yoto's **published documentation, not observed behaviour**. Same
  evidence tier as the accepted-format list. **If a live test disagrees, the test
  wins** — and a Planner pass should decide whether to act (split on bytes) or
  advise (surface the number), which is exactly the two-tier question
  configuration-surface §13.2 and export-only §8.6 both answered before.
- **~~Open scoping questions for the Planner pass~~ — ANSWERED 2026-09-05.** The
  three options were: split on a byte budget, transcode oversized local files on
  the send path, or advise. **The plan picks advise**, and the reasoning is in
  [plan §0.1–0.2](superpowers/plans/2026-09-05-per-track-size-limit.md). Two
  points worth not rediscovering: a byte-split leaves the card's *total* bytes
  unchanged, so a 529 MB WAV split six ways is still over the **500 MB card**
  ceiling — it converts one probable refusal into a more certain one. And a
  send-path transcode is a **worse** trade than the export path's: export
  converts because the website would refuse the file outright (0 added lossy
  generations — the alternative is failure), whereas the send path's API ingests
  it and Yoto transcodes server-side, so a local re-encode adds a **second**
  generation to audio that was going to be re-encoded anyway. That is exactly
  §8.6's *"her audio is quietly made worse"*, in a sharper form than §8.6 itself
  describes.
- **`copy.md` §5.9's strings were checked and are NOT verbatim-reusable here.**
  `overview.md` §8.6 speculated they might be — *"a small argument for the send
  path borrowing these strings later"*. They cannot, for two independent reasons:
  the approved sentence says *"Yoto's **website** may refuse it"*, which is false
  on a path where the app does the sending; and §5.9's `{list}` format is
  ratified explicitly because *"it is the file name she will have to find in a
  file dialog"* — there are no written files and no file dialog on the send path.
  Which list form is right there is a genuine copy decision, which is why the
  advisory surface is **item 21 and Designer-blocked** rather than folded into
  item 20.
- **Two things the Planner pass found that were not in this briefing**, both now
  in item 20's scope. `client.py:237` PUTs `content=fh.read()` — the entire track
  held in memory, ~529 MB for the same WAV — which is the **send-side twin of the
  add-side fix in the job-system ADR §3.1**, and which items 14, 15 and 16 do not
  reach. And `_friendly_http` is shared by six call sites, so no single 413 string
  can be right for all of them; the fix routes a per-track message from the one
  caller that knows, and stops the default naming a ceiling it cannot vouch for.

### Item 18 — briefing notes

- **It mutates LIVE production cards. Every safety property is load-bearing.** The
  apply-mode order is fixed: GET → plan (probe) → all-or-nothing gate → **BACKUP**
  → POST → re-GET → **verify**. A blocked card never reaches the POST; the backup
  is durable on disk (flush + `fsync`) before the POST; the verify fails loudly on
  any change beyond the intended `format` flip. **This PR does not run `--apply`;
  the live 3-card run is the coordinator's separate post-merge step.**
- **Step-0 pinning (read-only `GET /card/gzP2B`) corrected the plan's assumptions
  — this is what the plan told Builder to pin, and it mattered.** The real body is
  **wrapped**: `{"card": {…}, "ownership": {…}}`; `client.get_card` unwraps to the
  inner `card` object (which carries `content.chapters`, `cardId`, `title`,
  `metadata`) — that inner object is what we back up, mutate and POST. The
  pre-signed artifact URL is **`trackUrl` itself** (a full
  `https://secure-media.yotoplay.com/…?Expires=…&Signature=…#sha256=…` URL, stable
  within the ~60-min signing window), **not** the `yoto:#sha` the plan assumed — so
  `_ARTIFACT_URL_KEYS` leads with `trackUrl` and the verify **normalizes** signed
  URLs to their sha-bearing path (ignores signature rotation, still catches a real
  resource remap). `gzP2B`'s artifact was probed read-only and confirmed **Ogg
  Opus** (`OggS`/`OpusHead`; served `Content-Type: audio/ogg`, no `codecs` param, so
  the magic-byte sniff is the path that actually confirms it). `/content/mine`
  returns `{"cards":[…]}`; all three cardIds present (`1WCvI`'s real title is
  **"Wild Robot"**, not "The Wild Robot" — a second reason to use `--card-id`).
- **`format` is the ONLY field ever written.** `fileSize`/`duration` self-correct
  server-side and `channels` is already right, so the whole correction is one string
  per track. **Never rebuild via `build_content_payload`** — it only models new-card
  fields and would drop icons/keys/order. Deep-copy the (unwrapped) GET body and
  overwrite only `format`.
- **Confirm before correcting — never guess.** A track is set to `"opus"` only after
  its served artifact is PROVEN Opus. Unprobeable or non-Opus → that track blocks the
  **whole** card (all-or-nothing); the card is left byte-for-byte untouched.
- **Dry-run is the DEFAULT; `--apply` is opt-in** (and `--dry-run` wins if both are
  passed). Backups are written only in apply mode, only before the POST.
- **Use `--card-id` for the live run, not `--title`.** Discovery **refuses to
  auto-pick** an ambiguous title by design. All three cardIds are known: `1WCvI`,
  `gzP2B`, `7FcVe`.
- **The architecture docs are committed by this PR** (plan Task 6): the repair ADR
  (design basis + an addendum recording the 1-PR simplification), the job-system ADR,
  and `docs/architecture/README.md`. **No version bump; no release cut.**

### Item 13 — briefing notes

- **Commit-stack order is a hard constraint, not a suggestion.** One PR, but
  **Stack 0 (shared groundwork, 2 commits: the `.msg-box` helper + the `api()`
  HTTPException `detail` fallback, Tasks 1 and 1b) → Stack A (Item A, tasks
  2–10) → Stack B (Item B, tasks 11–18) → Stack C (version bump + notes, task
  19)**. Item A's commits must be contiguous and revertable without breaking
  Item B — which is why the shared paragraph helper is its own Stack 0 at the
  base rather than living inside Item A. Do not interleave; finish and commit a
  stack before the next. Plan §Commit stacks explains why the maintainer's
  literal "two stacks" reading needed a third.
- **The hard gate is a DENY-LIST, never the 32-character rule.** This is the
  single most important thing not to "simplify". The 32-char alphanumeric shape
  is *advice* that produces the `unusual` verdict; as a hard gate it would lock
  every user out the day Yoto issues a differently-shaped ID, with recovery
  requiring a code change and a release. It is also why `conftest.py`'s
  `test_client_id` (14 chars, an underscore) still passes under uniform blocking.
  Task 2's tests guard both the shipped default scoring `ok` and `test_client_id`
  not being blocked — **a red suite anywhere in Stack A most likely means the
  deny-list was built as an allow-list.**
- **The refusal must run BEFORE the write and BEFORE `logout()`.** The whole
  point is that a user with a working session never loses it to a typo, and the
  reassurance copy (*"…and you're still signed in to Yoto."*) is true *only*
  because of that ordering. `test_the_refusal_runs_BEFORE_the_write_and_BEFORE_logout`
  asserts neither side effect fired — **do not relax it**; if the ordering
  changes on purpose, the copy must change with it.
- **Blocking is uniform across all three tiers; only the recovery copy varies.**
  `env` and `builtin` get a recovery *sentence*, not a button (the button would
  promise something the app can't do). Two stale sentences in the handoff
  (`interactions.md` §3.6.2's diagram and §3.6.7's role note) still describe an
  earlier draft that exempted `env`; **the plan flags them in §Deviations and
  they need a post-merge amendment.** `env` blocks.
- **Three findings the plan carries because they get lost between spec and
  build**, each with its own task or test: `api()` must re-throw `AbortError`
  distinctly (Task 11 — without it a user's own cancel is reported as a network
  error *and* offered a retry); the reorder sorts **groups not tracks** and all
  counts are **files not tracks** (one file can split into many, Task 16); and a
  cancelled batch must **never** fire the reorder (Task 16/17).
- **Verified during planning, so nobody re-litigates it:** a cancelled in-flight
  file almost always still lands (the request body is buffered before the handler
  runs, and there are no await points after it). The copy says so honestly and
  must keep saying *"may"*. The synchronous transcode also blocks the server's
  event loop, which is why cancel is purely client-side. Plan §Verified during
  planning has the repro output.
- **The plan builds three job-system-ADR seams into Item B (S1/S2/S3).** They are
  good factoring on their own terms and cost ~30 min. **The job-system arc itself
  is out of scope for this PR — do not plan it, do not absorb it.** S2 in
  particular is guarded by a test because without it a future job failure would
  misclassify and break success criterion 12.
- **The plan owns the v0.1.11 bump (Task 19).** The version string is the asset
  cache key (`index.html`'s `?v=__ASSET_V__`), and this PR is almost all
  `app.js` — without the bump, existing browsers keep serving the old script
  against the new markup, which is queue item 8's bug with a new payload.
- **Two things surfaced for the queue, plus one now folded in** (plan §For the
  queue): the `HTTPException`-messages-never-reach-the-user copy-loss class
  (`api()` read `data.error`, FastAPI sends `{detail}`) is **no longer deferred —
  it is fixed in Stack 0, Task 1b**, with a copy audit of all eleven raises and
  the one developer-ish string it surfaces (`Unknown icon`) softened; item 2
  (`--port` doesn't move the redirect URI) becomes *visible* for the first time
  because setting 3 now displays that value; and the event-loop-blocking transcode
  is now measured, strengthening the job-system case.

### Items 14–16 — the file-upload-on-job-system arc (briefing)

Source of truth:
[`docs/architecture/decisions/2026-07-21-file-upload-on-job-system.md`](architecture/decisions/2026-07-21-file-upload-on-job-system.md).
**The ADR is `proposed` and needs Mark's approval before Planner picks up any of
the three.** All three also depend on **item 13 shipping first** — PR A rewrites
the `POST /api/tracks/file` contract that PR B builds against.

- **Do NOT collapse these into one PR.** The ADR is explicit (Option 5 over
  Option 2): **PR A is independently shippable and valuable on its own.** It
  removes a redundant ~260 MB double-write and — the bigger win — stops a long
  transcode from blocking uvicorn's event loop; today a multi-minute split hangs
  `/api/status` and *every* other route (ADR §1.1, §5.1, measured in item 13's
  plan §Verified during planning). PR A ships without cancel and without new
  progress.
- **PR A is an edit, not a rewrite, because item 13 built the seams.** It lands on
  S1 (one `uploadOneFile` call site), S2 (classifier reads `err.data.reason` +
  `retryable` before `.status`) and S3 (one `setAddProgress` writer): ~15–20% of
  the client touched, near-zero deleted (ADR §4). **The one load-bearing risk:** a
  job endpoint reports failure through `pollJob` with **no `.status`**, and
  `jobs.py` has **zero test coverage** (ADR §4.3, §6). Item 13's reason-precedence
  branch (S2) is the *only* thing stopping a real, permanent job failure from
  misclassifying as transient and offering a `Try again` that reliably fails
  (success criterion 12). **PR A must add `tests/test_jobs.py`** covering
  `reason` / `retryable` / cancelled propagation.
- **PR A must never let a job outlive the draft — do NOT add persistence**
  (ADR §5.4). `_draft` is a module-level global that dies with the process; a job
  surviving a restart would `add_track` into a *fresh, empty* draft, which is
  strictly worse than losing the job. PR A should also map a `/api/jobs/{id}` 404
  to a *"Yoto Maker restarted"* message rather than the generic transient branch
  (ADR §5.2.3) — that is also the owner of the copy for item 13's flagged
  `"Job not found"` string (item 13 plan Task 1b, copy audit).
- **PR B is one surgery that buys two things** — exact cancel and real long-file
  progress both need the same `Popen` rewrite of `normalize.py::_run` (ADR §3.2).
  It adds a server-side **`cancelled` terminal state that MUST be distinct from
  `error`**: a cancel arriving as `status: "error"` is reclassified transient and
  offered `Try again` for the thing she just stopped (ADR §5.2.6). PR B is the one
  that **deletes the client's *"may still finish"* hedge sentence.** `_run` is
  shared by `probe_audio` / `normalize_to_mp3` / `split_audio`; default the new
  kwargs to `None` so unset behavior is byte-identical.
- **PR C is the deferrable cut-line — get an explicit maintainer go/no-go before
  planning it** (ADR open question 1, §3.3, §7.5). It is client-only
  (`fetch` → `XMLHttpRequest` for `upload.onprogress`). The open product question:
  for a file **under 50 minutes** — the common case — essentially the entire wait
  is the *upload leg*, which **only the browser can measure** (ADR §1.4). So
  **A + B alone leave short files with a differently-fake bar** (near-zero, then a
  jump), which may read *worse* than today's fake 40% (ADR §7.4). The arc is
  coherent with A + B alone; C is the only PR whose value is not self-evident.

### Item 9 — briefing notes

- **It is a vocabulary fix, not a visibility fix.** The user knew the feature
  existed, had approved its design, was actively looking, and asked for *"the
  option to connect to a different account."* Nothing on the connected screen
  contained *account*, *different* or *change* — the pill names a **state**, the
  footer a **category**, the step-3 link a **destination**. Unhiding the link
  without restoring the vocabulary leaves him matching against the wrong string
  again. `overview.md` §12.2.
- **The evidence is partially contaminated and the plan is built only on the
  clean half.** His browser was serving a stale `app.js` (item 8), which killed
  *both* live entry points — the footer link is also an `<a href="#settings">`
  with no handler registered on v0.1.8's script. All click-behavior evidence is
  discarded. **Do not add prominence changes justified by "the pill looks like a
  badge"** — that claim is explicitly not established. The pill's treatment
  changes only as far as a separately-measured contrast failure forces, plus one
  glyph. No border, no size increase, no gear.
- **Two controls, opposite answers on the gear glyph, and it is easy to
  misread.** `#advToggle` (step 3) **keeps** `⚙️` on both copy variants — the
  glyph is the constant so the control stays recognisable when the words change.
  `#yotoPill` (header) gets `›` and **explicitly not** a gear: a gear says
  *settings*, the category vocabulary that already failed, and reads as
  "machinery, don't touch" to the `INSTALL-FOR-MOM.md` user. Do not harmonise
  these. Plan §Hazard 1.
- **Measurement provenance — re-measure, don't assert.** Item 8's plan found that
  PR #10's UAT produced three false readings from cached CSS, so contrast numbers
  from that session are suspect, including the pill's 2.56:1. Designer's sweep is
  independent, but Test Plan §D requires the shipped result be measured live, on
  a hard-reloaded page **and** a naturally-loaded one, with both runs agreeing.
- **Order.** Not a hard dependency, but **prefer shipping item 8 first**: its
  version stamp is what lets an already-poisoned browser receive this fix at all.
  Task 2 is a `renderStatus()` change, exactly the kind a stale `app.js`
  swallows while the new markup renders. Both PRs edit `index.html` in disjoint
  regions (item 8: lines 7 and 309; item 9: 16–18 and 118–142), so a conflict is
  unlikely; whichever merges second rebases, and `docs/RELEASE_NOTES.md` is the
  only file needing real attention (plan Task 7 is written for both orders).
- **Do not touch the `.setting` primitive.** Designer confirms it was not read,
  extended or clarified for this work, and nothing here changes the settings view
  at all. `overview.md` §3's placement decision is likewise untouched.
- **Two things the design brief did not list and the plan adds**, both flagged in
  its §Deviations: a `margin-top` on the relocated `#advRow` (the handoff snippet
  omits spacing, which would butt the link against `.btn.big`), and a rewrite of
  the now-false `outline-offset` hazard comment at `styles.css:64–73`, which
  duplicates the 2.57:1 claim `tokens.md` §2a retired. **Keep the offset itself.**

### Item 11 — briefing notes

- **The contradiction, stated plainly.** The same design amendment mandates
  `aria-hidden="true"` on the pill's `›` *because* an affordance glyph should not
  be part of an accessible name — and simultaneously requires `⚙️` on **both**
  `#advToggle` copy variants (`copy.md` §1a), where it is bare text and therefore
  *is* part of the name. Both rules are defensible; together they are inconsistent.
- **Why Builder must not just fix it.** The gear on `#advToggle` is load-bearing
  by design: it is the constant that keeps the control recognisable when the words
  change between states (`overview.md` §12.6, and it is the deliberate opposite of
  the pill's answer). Silently wrapping or dropping it is a design change.
- **It is also structurally awkward as specced.** `renderStatus()` sets
  `$("#advToggle").textContent` wholesale on every status render, which would
  destroy a nested `<span aria-hidden>` on the first transition. Any fix has to
  change *how* the copy is applied, not just what it says — likely `replaceChildren()`
  with a rebuilt span, or moving the glyph into CSS `::before`. Note the CSS route
  has its own trade-off: generated content is still exposed to some screen readers.
- **Not urgent.** Pre-existing since v0.1.9, LOW severity, and the announcement is
  clumsy rather than wrong — a user hears an extra word, not a false one.

### Item 8 — briefing notes

- **Read the plan before starting.** The approach is a deliberate combination of
  two mechanisms plus a document-level header, and each part covers a specific
  blind spot in the others. Dropping any one of the three leaves a fix that looks
  correct and does nothing in the field.
- **We misfiled this twice.** Builder and Tester both hit this symptom during PR
  #10 and PR #11 UAT and it was written up as a *testing hazard* — "clear your
  cache before UAT" — in `docs/DEVELOPERS.md` and both v0.1.9-era plan files.
  One of the three "false failures" recorded there (**the pill triggering sign-in
  instead of routing to Settings**) is verbatim the bug the user later reported
  from the field. Tasks 5 and 7 correct that framing.
- **The single most important UAT instruction: do not clear the browser cache.**
  The whole claim is that an already-broken browser is repaired with no user
  action. Clearing the cache first destroys the test and would have hidden this
  bug for a sixth release.
- **Highest-risk implementation detail:** `read_text()` must be passed
  `encoding="utf-8"` explicitly. Without it the frozen `.exe` reads `index.html`
  as cp1252, raises `UnicodeDecodeError` at byte 1201, and 500s the entire UI —
  while passing every test on a UTF-8 machine. Test plan §C.3 is the gate.
- **Version-bump ownership.** This PR bumps `pyproject.toml` and
  `yoto_maker/__init__.py` to `0.1.10`. Coordinate with the Designer-specced
  Settings-discoverability item landing in the same release; whichever merges
  second rebases.
- **Adjacent but out of scope:** item 2 (`--port` doesn't update `cfg.port`) sits
  at `main.py:59`, one file over from this work. Leave it alone — it changes OAuth
  redirect behavior and has its own row.

### Item 2 — briefing notes

- **The defect.** `yoto_maker/main.py:59` computes `port = args.port or cfg.port`
  and passes it to `start_server()`, but never assigns it back to `cfg.port`.
  `_redirect_uri()` reads `cfg.port`, so it keeps returning 8777 no matter what
  the flag says. The server listens on the requested port; only the OAuth
  redirect is wrong.
- **How it surfaced.** Found while running PR #10's UAT on a non-default port,
  and it blocked one Tester sub-check. Everything not involving Yoto sign-in
  works fine under `--port`, which is why it has survived since v0.1.8.
- **Why it isn't in PR #10.** Pre-existing, unrelated to the configuration
  surface, and it changes OAuth redirect behavior — not something to slip into a
  UI PR's review-gate fixes.
- **Worth a Planner pass despite being small:** the redirect URI has to match
  what's registered on Yoto's side, so "just set `cfg.port`" may be necessary but
  not sufficient. The right answer may be to reject `--port` for sign-in flows
  with a clear message rather than silently produce a redirect that Yoto rejects.

### Item 3 — briefing notes

- `tests/test_sources.py::test_youtube_sponsorblock_best_effort_retry` does a
  bare `import yt_dlp` and fails with `ModuleNotFoundError` wherever that
  optional dependency isn't installed — which includes this machine.
- Wants `pytest.importorskip("yt_dlp")` so the suite is green when the dep is
  absent and still exercises the retry path when it's present.
- The suite reports **109 passed, 1 failed** without the dep, and that one
  failure is environmental. It should be a skip.
- **Confirmed environmental during the v0.1.9 release cut.** `yt-dlp` had to be
  installed to build the `.exe` (the spec's `collect_all("yt_dlp")` needs it),
  and with it present the suite runs **110 passed, 0 failed** — the test itself
  is fine, it just states a dependency it should be skipping on. Note the count
  is 109/110 rather than the 100 recorded earlier; PR #10 and #11 added tests.

### Item 4 — briefing notes

- **The defect.** The crop editor modal never traps focus. Observed Tab order,
  starting inside the modal: `cropZoom` → `cropCancel` → `cropApply` → **escapes
  to `body`** → `yotoPill` → `ytUrl` → `skipSponsors`. A keyboard user tabs
  straight out of the modal and into the page behind it, with no way back except
  Shift-Tab counting.
- **Wants:** a focus trap (cycle within the modal), plus the usual modal
  companions — focus moved into the dialog on open, restored to the invoking
  control on close.
- **Pre-existing**, introduced with the crop editor in v0.1.7. Found while
  running PR #10's keyboard/focus gate (§C), which is why it surfaced now.
  Explicitly **not** a PR #10 regression and deliberately out of that PR's scope.
- PR #10 *did* ship a registry-driven Escape handler; check whether the crop
  modal should register with it rather than growing its own key handling.

### Item 5 — briefing notes

- **The defect.** `#yotoPill`'s white label measures **2.56:1** against the light
  end of the pill's gradient. WCAG AA wants 4.5:1 for body-size text. It fails
  **at rest** — the focus and hover treatments PR #10 added are fine (that PR's
  focus ring measured 3.26:1 worst case against a 3:1 non-text requirement).
- **Why it's queued rather than fixed in PR #10.** Pre-existing and independent
  of the configuration surface. But PR #10 promotes the pill from decorative
  status indicator to the **primary entry point for Settings**, which raises the
  stakes on a control that already failed — worth fixing soon rather than never.
- **Needs a Designer pass.** The fix is a call about the gradient's fill or the
  label's treatment (darken the light stop, add a scrim, restyle the label, or
  drop white entirely). That is a visual-language decision with knock-on effects
  for the pill's connected/not-connected states — not a Builder picking a darker
  hex in isolation. Route to Designer before Planner writes the plan.

**Designer pass complete, 2026-07-20 — and it took the row with it.**

- **Outcome: absorbed, not scheduled.** Specified in
  `design-handoffs/configuration-surface/overview.md` §12.5–12.6 and
  `tokens.md` §2b, as part of the connected-state Settings-discoverability fix.
- **Why absorbed rather than left as its own row.** A label at 2.56:1 is not only
  an accessibility finding — it is *literally harder to see*, and a control whose
  label is hard to see does not get scanned. The discoverability spec had to
  respecify this same control anyway; leaving a row reading *needs Designer pass*
  against a control that now has one would put the queue in contradiction with a
  shipped spec.
- **The chosen fix, for the record.** Not the gradient stop (constrained by
  `tokens.md` §2a's focus-ring invariant, and it is the app's visual signature)
  and not the label (abandons `header { color: #fff }`). **Invert the fill**:
  `rgba(255,255,255,0.18)` → `rgba(36,29,56,0.28)`. The pill was failing because
  its fill was *white over an already-light gradient* — it lightened the
  background behind white text. Worst-case label contrast **2.56:1 → 4.97:1**;
  hover **3.28:1 → 5.81:1**; both status dots improve; full 1%-interval sweep and
  the rejected alphas are in `tokens.md` §2b.
- **Two knock-ons Planner should carry into the plan.** (1) The long
  `.pill:hover` derivation comment at `styles.css:87-104` should be **deleted**,
  not preserved — it derives a two-layer grey composite that exists only because
  the rest state was white, and hover becomes the same ink at a higher alpha.
  (2) `tokens.md` §2a's `outline-offset: 0` hazard note is now superseded (the
  2.57:1 figure becomes 4.97:1); it has been amended in place. **Keep the
  offset** regardless — it is still visually correct.
- **One further defect found on the same control and folded in:** the pill's
  `aria-label` overrides its visible text as the accessible name, so the name
  does not contain the label — WCAG 2.1 AA **2.5.3 Label in Name**. Introduced by
  PR #10, not pre-existing. Fix is a deletion; `title` alone is correct.

---

## Shipped

| # | Item | Spec | Plan | PR | Merged | Released |
|---|------|------|------|----|--------|----------|
| 1 | **Configuration surface** — full-page Settings view built on the reusable `.setting` primitive, plus the three backend correctness fixes it depends on | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) | [`superpowers/plans/2026-07-20-configuration-surface.md`](superpowers/plans/2026-07-20-configuration-surface.md) | [#10](https://github.com/mmackelprang/yoto-maker/pull/10) | ✅ 2026-07-20 | 🚢 v0.1.9 |
| 7 | **Client ID reveal control + the v0.1.9 release cut** — show the value in effect (full mask, monospace, `Show the whole thing` disclosure) for `saved`/`env`; then actually tag, build and publish v0.1.9 | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) (amended in `884fa6a`) | [`superpowers/plans/2026-07-20-client-id-reveal-and-v0.1.9-release.md`](superpowers/plans/2026-07-20-client-id-reveal-and-v0.1.9-release.md) | [#11](https://github.com/mmackelprang/yoto-maker/pull/11) (Part A), [#12](https://github.com/mmackelprang/yoto-maker/pull/12) (corrections) | ✅ 2026-07-20 | 🚢 v0.1.9 |
| 8 | **Browsers serve a stale `app.js`/`styles.css` after auto-update** — new HTML runs against old JavaScript, which is what made Settings unreachable on v0.1.9 | brief in plan §The defect | [`superpowers/plans/2026-07-20-stale-asset-cache-after-update.md`](superpowers/plans/2026-07-20-stale-asset-cache-after-update.md) | [#15](https://github.com/mmackelprang/yoto-maker/pull/15) (`77d499c`) | ✅ 2026-07-20 | 🚢 v0.1.10 |
| 9 | **A connected user cannot find the way into Settings** — `#advRow` leaves `#connectRow` for the end of step 3 and its copy names the *account*; pill fill inverted for legibility; pill `aria-label` deleted | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12, amended in `e52908e` | [`superpowers/plans/2026-07-20-settings-discoverability.md`](superpowers/plans/2026-07-20-settings-discoverability.md) | [#16](https://github.com/mmackelprang/yoto-maker/pull/16) (`be93ee1`) | ✅ 2026-07-20 | 🚢 v0.1.10 |
| 13 | **Client ID validation + multi-file audio upload** — Item A blocks a malformed Client ID from destroying a working sign-in before the write/`logout()`; Item B adds sequential multi-file upload with grouped partial-failure reporting, retry and cancel | [`specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md) | [`superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md`](superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md) | [#19](https://github.com/mmackelprang/yoto-maker/pull/19) (`6481aca`) | ✅ 2026-07-21 | ⏳ next cut (v0.1.11) |
| 17 | **Transcoded `format` propagation** — the card advertises Yoto's true transcoded format (Ogg Opus) instead of a hardcoded `"mp3"`; best-effort, degrades to the local probe if `transcodedInfo` is absent. Live-verified shape; `fileSize`/`duration`/`channels` deliberately left as-is (Yoto self-corrects them) | brief in plan §The defect | [`superpowers/plans/2026-07-21-transcoded-metadata-propagation.md`](superpowers/plans/2026-07-21-transcoded-metadata-propagation.md) | [#18](https://github.com/mmackelprang/yoto-maker/pull/18) | ✅ 2026-07-21 | ⏳ next cut |
| 19 | **Save the files to a folder** — a second, user-chosen way to finish one card, needing **no sign-in at all**. Writes the audio, the pictures and a self-contained `What to do next.html` into `<Documents>\Yoto Maker\<card name>\` for hand-upload on `my.yotoplay.com`. Ships **six** `.hidden` regions (Designer's 2026-09-05 ruling added `#exportOpenError`, so a reveal failure no longer destroys the partial-save notice), and the app stops claiming an outcome it does not have when a status poll drops — `copy.md` §5.10 replaces §5.7 only when a job id already existed. `styles.css` and `jobs.py` absent from the diff. **`copy.md` §9's send-path string is written and deliberately unshipped** — §9.1's fallback, taken; follow-up row needed | [`specs/2026-09-05-export-only-mode-design.md`](superpowers/specs/2026-09-05-export-only-mode-design.md) + [`design-handoffs/export-only-mode/`](design-handoffs/export-only-mode/) | [`superpowers/plans/2026-09-05-export-only-mode.md`](superpowers/plans/2026-09-05-export-only-mode.md) | [#24](https://github.com/mmackelprang/yoto-maker/pull/24) (`7574d0d`) | ✅ 2026-09-06 | 🚢 v0.1.13 — **and this release means the save path works as designed, NOT that the offline-download defect is fixed. A card playing in the phone app is not evidence of a fix.** |
| 18 | **Repair existing cards' declared `format` (mp3 → opus) IN PLACE** — CLI utility `python -m yoto_maker.repair`; dry-run by default, backup-before-write, all-or-nothing per card, verify-after, idempotent. Step-0 pinning found the real `GET /card` body is wrapped and the artifact URL is `trackUrl` itself. `format` is the only field written. No version bump | [ADR](architecture/decisions/2026-07-21-repair-existing-cards.md) | [`superpowers/plans/2026-07-21-repair-existing-cards.md`](superpowers/plans/2026-07-21-repair-existing-cards.md) | [#20](https://github.com/mmackelprang/yoto-maker/pull/20) | ✅ 2026-07-22 | n/a (maintainer tooling; the live 3-card `--apply` run is a separate coordinator step) |
| 20 | **The send path's 413 named the wrong ceiling, and its audio PUT held the whole track in RAM** — `_friendly_http` mapped every 413 to the card-level *"max 5 hours per card"* at the moment the **per-track** limit was hit; `_put_audio` held the whole track as one `bytes` (~529 MB for a 50-minute WAV) and now streams the open file, wire form unchanged (explicit `Content-Length`, never chunked — a pre-signed PUT depends on it). The per-track string was blocked mid-cycle on a **Designer ruling** and shipped as ruled: **no number at all**, and a cross-path pointer at `📁 Save the files to a folder`. The generic 413 gained §4d's recovery sentence, closing the app's only dead-end error. **No version bump** — no served static asset touched. Plan §8's live probe **not run**; item 21 still open, item 27 filed | Decision in plan §0 + [`design-handoffs/export-only-mode/copy.md`](design-handoffs/export-only-mode/copy.md) §10 / [`interactions.md`](design-handoffs/export-only-mode/interactions.md) §4b | [`superpowers/plans/2026-09-05-per-track-size-limit.md`](superpowers/plans/2026-09-05-per-track-size-limit.md) | [#27](https://github.com/mmackelprang/yoto-maker/pull/27) | ✅ 2026-09-06 | 🚢 v0.1.13 |
| 28 | **The repair CLI crashed *after* it had already written to a live card** — `_print_card_result` raised `UnicodeEncodeError` on a track title the console could not encode, and `main` reached it *after* `repair_card` had POSTed, so an `--apply` run wrote to a real card and then died before reporting whether it verified, where the backup was, or what to roll back. Fixed at the **stream**, not the literals: `reconfigure(errors="backslashreplace")` on `sys.stdout` and `sys.stderr` as `main`'s first statement — **`errors` only, never `encoding`** (forcing UTF-8 also stops the crash but can mojibake a real OEM console), pinned by a source test in both directions. **`516cbf7` did not regress — it was never the right fix**: it swept this file's own literals, every character it removed is encodable in cp1252, and the crashing 🤖 arrives from Yoto's JSON. **The CLI output layer had never been executed by a test**; it is now, under a *forced* cp1252 stream so it fails on Linux CI too, and all 10 tests were proved to bite by mutation. **No version bump**; ships inside v0.1.14's cut. **No `--apply` run** — diagnosis path only. Hard prerequisite for item 29 | Decision in [plan §ITEM 28](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) (a prerequisite the plan adds to [ADR](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md) §3.7; no ADR section owns it) | [`superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md`](superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md) Tasks 1.1–1.4, 1.6 (1.5 dropped — untracked file) | [#33](https://github.com/mmackelprang/yoto-maker/pull/33) | ✅ 2026-09-10 | ⏳ next cut |

Item 1 shipped all 12 tasks as one PR, as planned. Its Builder briefing notes
were consumed and removed; the spec and plan above remain the durable record.
Three findings surfaced during its review gates and were filed as items 4, 5
and 6 rather than fixed in scope.

Item 7 shipped Part A (tasks 1–7 + 11) as PR #11 and Part B (tasks 8–10, the
release cut) directly on `main`. PR #12 folded in two corrections found during
UAT before the tag: Test Plan §H.3 expected the reveal toggle to wrap beneath the
value at 400px when it actually stays beside it (a wrong expectation, not a
defect), and the stale-build hazard gained its second cause — a stale *server*,
where the single-instance guard makes a new dev server exit 0 while UAT silently
measures the old build.

**Items 8 and 9 — v0.1.10 Released cells, evidenced per the rule above:**

```
$ gh release view v0.1.10 --json tagName,assets -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
v0.1.10 -> YotoMaker.exe

$ gh release view v0.1.10 --json assets -q '.assets[] | "\(.name)  \(.size) bytes  state=\(.state)"'
YotoMaker.exe  127040616 bytes  state=uploaded

$ git ls-remote --tags origin v0.1.10
715bd1c55b96bb63c2eb25a2f284b5f53c21b499        refs/tags/v0.1.10
```

Tag `v0.1.10` → `715bd1c`, confirmed on the remote. **The update path was
verified end-to-end rather than assumed:** with `__version__` spoofed to
`0.1.9` and **no `YOTO_LATEST_VERSION` override** in play (the override
short-circuits the API call at `updater.py:80`, so setting it would test the
override instead of the release), `updater.check_for_update()` hits the real
releases API and returns `update_available: True`, `latest: "0.1.10"`, with a
`download_url` that answers `200` at the expected 127,040,616 bytes. A v0.1.10
client correctly gets no banner.

**The frozen `.exe` was verified serving both fixes, not just built.** Item 8's
cp1252 hazard (`read_text()` without `encoding="utf-8"` 500s the whole UI from a
frozen build while passing every test on a UTF-8 machine) is the gate, and it
passes: `/` returns 200, `/api/status` returns 200, and the served document
carries `?v=0.1.10` stamps on its assets. Item 9's markup was checked in the
served HTML rather than the source — `#advToggle` is outside `#connectRow`,
`#advRow` follows `#sendDone`, the chevron carries `aria-hidden="true"`, the
pill has no `aria-label`, and the served stylesheet carries the inverted fill.

**One item shipped unverified again, deliberately not marked green:** the
screen-reader announcement of `#yotoPill`'s new accessible name (Test Plan
§E.3). Same reason as v0.1.9's reveal toggle — NVDA is not installed and
Narrator's speech cannot be captured as text. Recorded in PR #16's body, under
**Not verified in v0.1.10** in `docs/RELEASE_NOTES.md`, and in the GitHub
release body.

---

**Items 1 and 7 — v0.1.9 Released cells are evidenced**, per the rule above:

```
$ gh release view v0.1.9 --json tagName,assets -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
v0.1.9 -> YotoMaker.exe

$ gh release view v0.1.9 --json assets -q '.assets[] | "\(.name)  \(.size) bytes  state=\(.state)"'
YotoMaker.exe  127039674 bytes  state=uploaded
```

Tag `v0.1.9` → `aa3c085`, confirmed on the remote (`git ls-remote --tags origin
v0.1.9`) — the step that was missed last time. **The update path was verified
end-to-end rather than assumed:** with `__version__` spoofed to `0.1.8` and no
`YOTO_LATEST_VERSION` override in play, `updater.check_for_update()` hits the
real releases API and returns `update_available: True`, `latest: "0.1.9"`, with a
`download_url` that answers `200` at the expected 127,039,674 bytes. A v0.1.9
client correctly gets no banner.

**One item shipped unverified, deliberately not marked green:** the screen-reader
announcements on the reveal toggle (Test Plan §F.1–F.3). NVDA is not installed
and Narrator's speech cannot be captured as text, so nobody has heard the
control. The accessibility tree is consistent with the expected utterances and
double-announcement is ruled out structurally, but that is an argument from
construction, not an observation. Recorded in PR #11's body and under
**Not verified in v0.1.9** in `docs/RELEASE_NOTES.md`. Anyone with a screen
reader can close it in about thirty seconds.
