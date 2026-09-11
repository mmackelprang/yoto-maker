# ADR — `overlayLabel`: widening `repair.py` past format-only, on a declared change-set

**Date:** 2026-09-10
**Status:** **accepted** — approved by the maintainer 2026-09-10, including the **full**
declared-change-set refactor (§3.1), not the minimal Option 4 variant. Planned as
[`plans/2026-09-10-overlay-labels-and-the-declared-change-set.md`](../../superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md)
(queue items **28** and **29**). Sections marked *Corrected 2026-09-10* were falsified by
evidence gathered during the planning pass — see §1.1.
**Amends:** [`2026-07-21-repair-existing-cards.md`](2026-07-21-repair-existing-cards.md)
(its Addendum's format-only clause). **Does not supersede it** — §7.
**Issue:** [#31](https://github.com/mmackelprang/yoto-maker/issues/31) — twisting the
player's right-hand knob brings up no chapter list on a multi-segment card.

**Decision in one line:** Replace `repair.py`'s **format-only** safety invariant with an
explicit **declared change-set** — one ordered list of addressed field writes from which
**both** the POST body and the verify's expectation are derived — then add `overlayLabel`
as a **second intent** on that machinery. The label value is **unpadded 1-based decimal**
(`"1"`, `"2"`, …), written at **chapter and track level**, produced by **one shared helper**
in `models.py` that both the create path and the repair path call, **only where the field is
absent or empty**. Ship the refactor and the intent as **two independently revertible
commits**, and gate the whole thing behind a `--no-overlay-labels` flag so the unproven half
backs out without a revert.

> ✅✅ **THE HYPOTHESIS IS CONFIRMED, ON HARDWARE — 2026-09-11.** `overlayLabel` **does**
> gate the player's chapter-browse UI. On a **physical Yoto player**, on a multi-chapter card
> this arc had labelled: **twisting the right-hand knob brings up the chapter list, and
> pressing the knob selects a chapter.** Observed by the maintainer's daughter, 2026-09-11.
> The result is **self-validating as to which card was used** — only a multi-chapter labelled
> card can produce a chapter list at all under any hypothesis, so `gzP2B` (1 chapter) is
> excluded by the outcome itself.
>
> - **Open question 2 is CLOSED — §6.2.**
> - **§4.2.2 — *"we are writing an unproven field to live production cards"* — is
>   DISCHARGED.** The field is no longer unproven.
> - **The ~75–80% confidence figure is left standing wherever it appears** (§1.2, §6.2, §8)
>   and is now **historical rather than live**. It was the right confidence to hold on
>   2026-09-10, it is why §8 exists and why §3.7 split the commits the way it did, and
>   deleting it would erase the only record that the uncertainty was handled properly. Read
>   those figures as *"what was known then"*.
> - **§8's backout plan stays, and `--no-overlay-labels` stays.** Their justification is now
>   historical, not live. **Do not remove the flag.**
>
> ⚠ **What this test does NOT prove, and must not be read as proving:** that the
> **offline-download** behaviour changed (§8's closing ⚠ still stands in full), or anything
> about the self-update swap-and-relaunch step. The proven claim is narrow and exact: *the
> player renders a browse list from `overlayLabel`, and selection from that list works.*
>
> ✅ **Open question 1 is CLOSED and §1.1 has been CORRECTED — 2026-09-10.** This box
> originally warned that no repair write had ever landed and that this feature might
> therefore be **inert**. **That was wrong.** The live read-only check reports
> `already 'opus'` for **all 24 tracks across all three cards**, so July's write landed and
> Yoto **does** persist a client-supplied `format` — which is the mechanism `overlayLabel`
> relies on. Readings (A) and (B) in §1.1 are both dead, **blocker 1 (§1.3) bites on all
> three cards today**, and **commit 3 is to be built.** §1.1 carries the evidence and the
> reason the original on-disk inference failed; it is still worth reading first, but as a
> correction rather than a warning.

---

## 1. Context

### 1.1 ✅ SETTLED 2026-09-10 — the cards ARE `opus`, and the reasoning originally here was wrong

This section originally argued that the briefing's premise did not survive the evidence. It
is **corrected rather than deleted**, because the *way* it went wrong is a trap the next
reader of this repo can fall into twice.

**What the live check returns.** Run read-only — no `--apply`, so it cannot write — on
2026-09-10, **twice**: once by the maintainer, once independently by Planner.

```
python -m yoto_maker.repair --card-id gzP2B,1WCvI,7FcVe --dry-run
```

| Card | tracks `opus` | `RESULT:` line |
| --- | --- | --- |
| `gzP2B` (1 chapter × 1 track) | **1 / 1** | `already correct (all 1 track(s) 'opus') - nothing to do` |
| `1WCvI` (5 × 1) | **5 / 5** | `already correct (all 5 track(s) 'opus') - nothing to do` |
| `7FcVe` (18 × 1) | **18 / 18** | `already correct (all 18 track(s) 'opus') - nothing to do` |

**All 24 tracks are `opus`. So July's write landed, and Yoto persists a client-supplied
`format`** — which is precisely the mechanism `overlayLabel` depends on. **Readings (A) and
(B) below are both dead, and this feature is not inert.**

#### Why the original inference failed — two code facts, stated so it cannot recur

1. **A backup is the *pre-write* snapshot.** `_write_backup` runs at `repair.py:637`,
   **before** the POST at `:648`. So the newest backup per card is the state *immediately
   before the last write that landed* — never the state after it. This section read "the
   newest backup says `mp3`" as "the card is `mp3`".
2. **A repaired card stops producing backups.** Once every track is `opus`, `plan.outcome`
   is `"already"` and `repair_card` returns at `:626` — **before** `_write_backup` at `:637`.
   So **the absence of any backup newer than 2026-07-22 08:56 is the signature of a
   successful repair**, not evidence that nothing ran. This section read that absence the
   other way.

The ten files in `%LOCALAPPDATA%\YotoMaker\repair-backups\` are genuine and the table below
is accurate — it was the *caption* that was wrong. Each is one apply-mode run's **pre-write**
snapshot, which is exactly why every one still says `mp3` and why `updatedAt` on every one is
still the card's **creation** timestamp.

| Card | newest backup | that snapshot's `format` | `updatedAt` | `content.version` |
| --- | --- | --- | --- | --- |
| `gzP2B` (1 × 1) | `2026-07-22 08:54:00` | `mp3` — **pre-write** | `2026-07-20T22:50:47.447Z` | `"1"` |
| `1WCvI` (5 × 1) | `2026-07-22 08:54:51` | `mp3` — **pre-write** | `2026-07-20T22:48:55.106Z` | `"1"` |
| `7FcVe` (18 × 1) | `2026-07-22 08:56:07` | `mp3` — **pre-write** | `2026-07-20T23:05:11.823Z` | `"1"` |

The two readings this section originally weighed, both now falsified and kept only so a
future reader does not re-derive them:

- **(A) No write ever landed.** Dead: the cards are `opus`.
- **(B) A write landed and Yoto did not persist the client-supplied `format`.** Dead for the
  same reason — and this was the architecturally dangerous one, because it generalises: a
  `POST /content` that ignored a client-supplied track field would not honour `overlayLabel`
  either. **It does honour it.**

#### And the run this section called unexplained is explained

`edc3c6d` (*"canonicalize display.icon16x16 to yoto:#&lt;mediaId&gt; before POST"*) was committed
**2026-07-22 08:42:13 local**. Every run before it hit the Yoto 400 recorded at
`repair.py:24-27`; the runs after it landed:

| Run | Cards | vs. `edc3c6d` (08:42:13) | Outcome |
| --- | --- | --- | --- |
| 07:50:16 – 07:50:33 | all three | **before** | icon 400 — nothing landed |
| 07:51:22 – 07:51:25 | all three | **before** | icon 400 — nothing landed |
| **08:25:17** | `gzP2B` only — the "smallest card first" advice at `:816-821` | **before, by 17 minutes** | icon 400 — nothing landed. **This is the run originally left unexplained** |
| **08:54:00 / 08:54:51 / 08:56:07** | `gzP2B`, `1WCvI`, `7FcVe` — in the documented `--card-id` order | **after** | **landed.** Hence `already 'opus'` today, and hence no eleventh backup |

Every data point is now accounted for without appeal to (A) or (B).

⚠ **The check command needs a workaround, and that workaround was itself an unreported bug.**
Run as written it raises `UnicodeEncodeError` at `repair.py:745` against `1WCvI`, whose five
track titles each carry `U+1F916`. The only reason this command has ever completed is
`$env:PYTHONUTF8=1` — which lives in prose at `SESSION_STATE.md:245` and in this ADR's own
command line, and **in no code**. That is now **queue item 28**, a prerequisite *commit 0*
ahead of §3.7's sequence. After it lands the env var is optional: it only turns
`\U0001f916` back into `🤖`.

`SESSION_STATE.md:232-236` still lists the physical-player test as **never closed** — that
remains true, and it is Open question 2, not this one. What has changed is that a
**repaired** card demonstrably exists to test.

✅ **Superseded 2026-09-11: that test has now been run, and the chapter-list half of it passed
(§6.2).** The sentence above is kept because it dates correctly to 2026-09-10. The
offline-download half of the same checklist is still never-closed.

### 1.2 The finding this ADR acts on (established elsewhere; verified here only where cited)

Yoto's published schema — `https://yoto.dev/myo/how-playlists-work.md`, fetched 2026-09-10 —
carries, verbatim:

| Level | Field | Schema |
| --- | --- | --- |
| track | `overlayLabel` | `z.string()` — **required** |
| track | `overlayLabelOverride` | `z.string().nullable().optional()` |
| chapter | `overlayLabel` | `z.string().optional()` |
| chapter | `overlayLabelOverride` | `z.string().nullable().optional()` |

The document contains **no prose** about what `overlayLabel` does, where it renders, or any
relationship to the knob / chapter browsing. That absence is load-bearing: the hypothesis
that this field gates the knob-browse UI is **inference from a required field plus an official
example**, not a documented contract. It is ~75–80%, and §8 is written accordingly.

✅ **CONFIRMED ON HARDWARE 2026-09-11 — and the paragraph above is left exactly as written.**
The inference was correct: on a physical player, a multi-chapter card carrying `overlayLabel`
brings up the chapter list when the right-hand knob is twisted, and pressing the knob selects
a chapter. **Both facts in that paragraph remain true** — Yoto still documents nothing about
this field's relationship to the knob, and the decision to ship it *was* taken on inference
rather than on a contract. What has changed is only the last sentence's ~75–80%: that was the
honest confidence on 2026-09-10 and it is **kept as the record of having been appropriately
uncertain**, not as a live estimate. It is also why §8 exists at all, and §8 stays.

`yoto_maker/yoto/models.py` sends neither level. Verified independently here: `git log --all -S
overlayLabel` returns **nothing**, and a repo-wide grep for `overlayLabel|overlay_label`
returns **no matches**. The string has never existed in this repository.

Yoto's own sample app (`yotoplay/examples`, `vanilla-js-html/src/upload.js`, fetched
2026-09-10) sets `overlayLabel: "1"` at **both** chapter and track level, in objects whose
`key` is `"01"` — i.e. the padded identifier and the unpadded label sit side by side in the
same literal. That is the single strongest signal on §5's value question.

**Confirmed dead ends, not revisited:** `playbackType` (the server stamps `"linear"` on all
three cards regardless of chapter count — visible in every backup); missing `chapter.display`
(`yoto_maker/server/app.py:646-656` — `_resolve_icon` ends in an unconditional `return
icon_path("music")` at `:656`, and every chapter and track in all ten bodies carries a
resolved `display.icon16x16`); and "the segments never became chapters" (the bodies prove
5, 18 and 1 chapters respectively). The N-chapters × 1-track structure is canonical per
Yoto's own examples and is **not** restructured by this ADR.

### 1.3 The two blockers — verified against the code, not taken on trust

**Blocker 1 — an already-correct card never POSTs. CONFIRMED as a code fact.**
`CardPlan.outcome` (`repair.py:528-538`) returns `"already"` when `self.correct_keys` is empty
and nothing is blocked; `correct_keys` (`:520-521`) collects only decisions with
`status == "correct"`, and `plan_card` assigns `"already"` to every track whose
`declared_format == CORRECT_FORMAT` (`:568-569`). `repair_card` then returns at `:626-630`
— **before** `_write_backup` at `:637` and before the POST at `:648`. So a card needing only
a label would write nothing.

✅ **Its premise is CONFIRMED, and the blocker bites on all three cards TODAY** (§1.1).
Every one of them reports `already correct … nothing to do`, so without the second decision
axis the widened repair is a **silent no-op on exactly the three cards that can test the
hypothesis** — and on every future card the app creates correctly. **The second decision axis
is mandatory**, and for precisely the reason originally given.

**Blocker 2 — the verify fails every card. CONFIRMED, in both directions.**
`verify_only_format_changed` (`:481-498`) builds its expectation as
`_strip_volatile(apply_format_corrections(before, correct_keys))` at `:496`.
`apply_format_corrections` (`:328-344`) writes **only** `tr["format"]`. So `intended` never
contains `overlayLabel`, and:

- **If Yoto persists the field:** `_diff_paths` iterates `sorted(set(a) | set(b))` at `:463`,
  finds `overlayLabel` in `b` but not `a`, and emits `"unexpectedly ADDED"` at `:465` →
  `repair_card` returns `"verify-failed"` at `:657`. Every card, every run.
- **If Yoto strips the field:** `after == intended`, the diff is empty, the run reports
  `"applied"` — and the fix silently did not land. **This is the worse half**, and §3.1 is
  designed specifically to make it loud.

**The trap, confirmed and refused.** Adding `overlayLabel` to `_VOLATILE_TOP_KEYS` (`:400`)
would blind `_strip_volatile` to the field in **both** bodies, so the verify could no longer
see the field it exists to control — including a value Yoto changed on its own. Two prior
agents flagged it independently. This ADR does not do it, and §4.2 explains why the narrow
rollback tolerance in §3.5 is a different thing.

### 1.4 Evidence that `POST /content` is not a store-what-I-sent endpoint

Measured by diffing `build_content_payload`'s output (`models.py:30-64`) against the real
`gzP2B` body. Yoto **adds 16 keys we never send**:

| Object | We send | Real body has | Server-added |
| --- | --- | --- | --- |
| `content` | `chapters` | + `playbackType`, `version`, `activity`, `availability`, `cover`, `config` | **6** |
| each chapter | `key`, `title`, `tracks`, `display` | + `availableFrom`, `ambient`, `fileSize`, `duration` | **4** |
| each track | `key`, `title`, `trackUrl`, `type`, `format`, `duration`, `fileSize`, `channels`, `display` | + `ambient` | **1** |
| `metadata` | `media` | + `abridged`, `authors`, `narrators`, `copyrights`, `accents` | **5** |

The endpoint demonstrably enriches and derives. That is the factual basis for treating
"Yoto ignored our field" as a live possibility rather than paranoia, and for §3.1's
requirement that the verify catch a **removal** as loudly as an addition.

### 1.5 Where the format-only invariant is ratified

Three places, all verified:

1. `yoto_maker/yoto/repair.py:11` — *"FORMAT-ONLY correction (fileSize/duration self-correct
   server-side, channels already right)"*, in the module docstring's safety list.
2. `docs/architecture/decisions/2026-07-21-repair-existing-cards.md:514-517` — *"`format` is
   the only field that needed correcting … `apply_metadata_corrections` became a
   `format`-only overwrite"*; and `:526-528` — *"The ADR's core principles were kept:
   … deep-copy-and-overwrite-only, verify-after …"*.
3. `docs/BUILDER_QUEUE.md:468` (item 18's row) — *"**`format` is the only field ever
   written**"*.

Two notes on the record itself. The 2026-07-21 ADR's **Status line (`:4`) still reads
`proposed — needs Mark's approval`** although the feature shipped as PR #20 — stale, and
worth correcting in the same pass (§7). And the repair CLI's user-visible strings are already
known to be **owned by no handoff package**: `BUILDER_QUEUE.md` item 26 records that three of
`_friendly_http`'s sentences are reachable only from `yoto/repair.py`. §4.2.5 inherits that.

### 1.6 No `docs/ROADMAP.md` in this repo

`docs/BUILDER_QUEUE.md` is the roadmap. Items **21–27** are queued; none of them touches
`repair.py` or `models.py`, so this work does not collide with in-flight queue state. Item 14
(`⛔`) touches `jobs.py` and `server/app.py`, not these two files.

---

## 2. Options considered

**Option 1 — Do nothing; re-make the three cards by hand.** The knob bug stays for every card
the app has ever made and every card it makes next. Rejected, but note it is *survivable* and
is the honest fallback if Open question 1 returns reading (B).

**Option 2 — Fix only the create path (`models.py`), leave `repair.py` alone.** Cheapest, and
it is the half we are most confident about. But it does nothing for the three cards on the
granddaughter's player, which is the only place the hypothesis can be **tested**. Rejected as
a standalone, **retained as the first commit** of the two-commit split (§3.7) — it is exactly
what survives a revert of the repair half.

**Option 3 — A separate `labels.py` module / a second CLI beside `repair.py`.** Keeps
format-only intact and untouched. Rejected by the user's decision, and it is the wrong
structure anyway: it would duplicate `get_card` → canonicalize → backup → POST → re-GET →
verify, i.e. **two independent paths mutating live cards**, each with its own chance of a
canonicalization bug. The existing path's value is that it is the *only* writer.

**Option 4 — Widen `apply_format_corrections` to also write labels, in place.** The minimal
diff. Rejected: it leaves the POST body (`build_repair_payload`, `:347-372`) and the verify's
expectation (`apply_format_corrections`, `:328-344`) as **two separate functions that must be
kept in agreement by hand**. That is precisely the defect that makes blocker 2 possible. A
third intent later would reopen it.

**Option 5 — Widen by adding `overlayLabel` to `_VOLATILE_TOP_KEYS`.** Rejected outright,
§1.3.

**Option 6 (recommended) — Generalise the invariant to a declared change-set, then add
`overlayLabel` as a second intent on it.** §3. One list, two derived artefacts, verify
derived from the same list. Costs a refactor of the safety-critical core; buys an invariant
that survives a third intent.

---

## 3. Decision

### 3.1 The new safety invariant: a **declared change-set**

**The invariant, stated:** *after == before + the declared change-set, and nothing else.*

Today's guarantee is strong because it is narrow, and it is narrow because the *intent* is
hard-coded into the shape of the corrector. Generalise the intent into **data** and the
narrowness survives having more than one of them.

```python
# yoto_maker/yoto/repair.py
@dataclass(frozen=True)
class FieldEdit:
    path: tuple[str | int, ...]   # ("content","chapters",0,"tracks",0,"overlayLabel")
    old: object                   # value observed in the GET body; _ABSENT if the key is missing
    new: object                   # the value to write
    intent: str                   # "format" | "overlay-label"  — groups the report
    reason: str                   # printed per-track in the CLI report

ChangeSet = list[FieldEdit]       # ordered; at most one edit per path (asserted)
```

Three functions, and the relationship between them **is** the invariant:

```python
def apply_change_set(body: dict, edits: ChangeSet) -> dict:
    """Deep-copy `body`, then set exactly the declared paths. Nothing else changes.
    Creates a missing leaf key; never creates a missing intermediate container
    (a path whose parent is absent is a planning bug and must raise, not guess)."""

def build_repair_payload(body, edits: ChangeSet, canonical_urls) -> dict:
    """apply_change_set(), PLUS the media-reference canonicalization (§3.2)."""

def verify_only_declared_changed(before, after, edits: ChangeSet) -> list[str]:
    intended = _strip_volatile(apply_change_set(before, edits))
    return _diff_paths(intended, _strip_volatile(after))
```

**What this buys, precisely:**

- **One source of truth.** The POST body and the verify's expectation are both derived from
  `edits`. You cannot add an intent to one and forget the other, because there is only one
  place to add it. `apply_format_corrections` becomes the special case
  `apply_change_set(body, [FieldEdit(("…","format"), "mp3", "opus", "format", …)])` — and
  should be **kept as a thin wrapper** so the existing format-only tests keep a target.
- **`_diff_paths`' `k not in a` branch (`:465`) stops being a bug and becomes the feature.**
  A declared addition is already in `intended`, so it does not fire. An **undeclared**
  addition still does. No `_VOLATILE_TOP_KEYS` widening, anywhere.
- **The silent-failure half of blocker 2 is closed, and this is the part that is strictly
  better than today.** If Yoto strips `overlayLabel`, `intended` has the key and `after` does
  not, so `_diff_paths`' `k not in b` branch at `:467` fires **`"unexpectedly REMOVED"`** →
  `verify-failed`. Given §1.4, that is the branch most likely to fire in the field, and under
  today's code it would have reported `applied`.
- **The guarantee stays field-level.** It is still a path-addressed structural diff over the
  whole body, not "we trust the corrector."

**One boundary, stated so nobody folds it in:** the change-set carries **semantic field
writes only**. Media-reference canonicalization (`trackUrl` → `yoto:#<sha>`, `display.icon16x16`
→ `yoto:#<mediaId>`, `:347-372`) stays a **separate pre-POST rewrite**, because the verify
deliberately neutralises it on both sides via `_normalize_url` (`:403-428`) — the re-GET
returns a freshly *resolved* URL, not the canonical ref we posted. Declaring canonicalization
as edits would make `intended` canonical and `after` resolved, and the existing
normalize-then-compare would have to be undone. Leave the split exactly as it is.

### 3.2 `plan_card` / `CardPlan.outcome`: the second decision axis

The current `TrackDecision.status ∈ {"already","correct","blocked"}` (`:504-508`) conflates
*what we decided* with *which intent decided it*. Replace the single status with **per-track
edits plus per-intent notes**:

```python
@dataclass
class TrackDecision:
    ref: TrackRef
    edits: ChangeSet                 # 0, 1 or 2 declared writes for THIS track
    blocked_reason: str | None       # card-fatal (all-or-nothing) when set
    notes: list[str]                 # one per intent: already / planned / declined

@dataclass
class CardPlan:
    card_id: str
    title: str
    decisions: list[TrackDecision]
    canonical_urls: dict[str, str]
    card_edits: ChangeSet = field(default_factory=list)   # chapter-level writes
    card_problems: list[str] = field(default_factory=list)

    @property
    def change_set(self) -> ChangeSet:
        return [e for d in self.decisions for e in d.edits] + self.card_edits

    @property
    def blocked(self) -> list[TrackDecision]:
        return [d for d in self.decisions if d.blocked_reason]

    @property
    def outcome(self) -> str:
        if self.blocked or self.card_problems:   # unchanged: ANY blocker skips the card
            return "blocked"
        if not self.decisions:
            return "empty"
        if self.change_set:                      # <-- the second axis lives here
            return "apply"
        return "already"
```

`CardPlan.correct_keys` (`:519-521`) is **retired**. Its three consumers —
`apply_format_corrections`, `build_repair_payload`, and the report at `:749-751` — all take
`change_set` instead. Retiring it rather than keeping it alongside is deliberate: a card can
now need a write with `correct_keys` empty, so any surviving caller of `correct_keys` is a
latent "writes nothing" bug of exactly the kind blocker 1 is.

**Per-intent note vocabulary — and only one of these is card-fatal:**

| Note | Meaning | Card-fatal? |
| --- | --- | --- |
| `already` | the field already holds the expected value | no |
| `planned` | an edit is declared | no |
| `declined` | this intent cannot compute a value here, and that is not a correctness hazard | **no** |
| `blocked` | this intent cannot proceed safely | **yes** — all-or-nothing |

**`format` uses `already` / `planned` / `blocked`. `overlay-label` uses `already` / `planned`
/ `declined` and never blocks.** An unprobeable artifact is a correctness hazard and must stop
the card; a label we cannot confidently number is not. Without `declined`, a card with an
unusual structure would lose access to the *proven* format fix because of the *unproven* label
one. That inversion is the reason this row exists.

**The outcome vocabulary itself does not change.** `already | empty | dry-run | applied |
blocked | verify-failed | write-uncertain | restored` (`:596`) stays as-is. Every new value
is a new branch in the summary map (`:746-759`) and in `main`'s exit-code logic (`:832`), and
nothing here needs one. What changes is **semantics**: `already` now means *every declared
intent is already satisfied*, not *every track is already `opus`*.

That makes the **report strings at `:746-760` wrong, not merely stale**, and they must change
with it:

| Outcome | Today (`:747-751`) | Must become |
| --- | --- | --- |
| `already` | `already correct (all {n} track(s) '{CORRECT_FORMAT}') - nothing to do` | `already correct ({n} track(s), nothing to change) - nothing to do` |
| `dry-run` | `WOULD correct {len(correct_keys)} track(s)` | `WOULD make {len(change_set)} change(s) across {k} track(s) - re-run with --apply to write` |
| `applied` | `corrected {len(correct_keys)} track(s); POST ok; verify ok` | `made {len(change_set)} change(s); POST ok; verify ok` |

A card whose format is already right but whose labels are missing would otherwise print
*"already correct (all 18 tracks 'opus')"* **and then write** — a report that contradicts
itself. Pin the new strings with a test (§4.1), because this is a string that a future intent
will silently re-falsify.

### 3.3 Idempotency

**Detected by value comparison against a computed expectation**, exactly as `format` is
compared against `CORRECT_FORMAT` (`:568`). For the chapter at positional index `ci` and its
track at `ti`:

```
expected = models.overlay_label(ci + 1)      # §3.4
chapter needs an edit  <=>  not _is_set(chapter.get("overlayLabel"))
track needs an edit    <=>  not _is_set(track.get("overlayLabel"))
where _is_set(v) == isinstance(v, str) and v.strip() != ""
```

Three properties make this idempotent **by construction**, with no "was this card labelled?"
bookkeeping — the same reasoning as the 2026-07-21 ADR §3.5:

1. **The expected value is a pure function of position.** `iter_tracks` (`:305-322`) already
   walks positionally and keys on `f"{ci}.{ti}"`, explicitly *"not the card's own key
   strings"* (`:306-307`). Run 2 computes the same value, finds it equal, declares zero
   edits, `outcome == "already"`, no POST.
2. **⚠ The value must never be derived from the card's own `key` field.** `key` is `"01"`;
   the label is `"1"`. If one code path read `key` and the other computed from the index, two
   runs could disagree and flip-flop. **Forbidden**: the only input is the positional ordinal,
   through the one shared helper.
3. **An existing non-empty `overlayLabel` is never overwritten.** It is reported `already` and
   left alone. This is not only idempotency — it stops the tool from flip-flopping against
   *another* editor. A user who sets `"Chapter 1"` in the Yoto app would otherwise have it
   reset to `"1"` on every run, forever. It also means our edit is always an **absent-or-empty
   → value** write, never a value clobber, which keeps both the verify and the rollback story
   simple.

### 3.4 The label value, and the shared helper

**Decision: `overlayLabel = str(ordinal)` — unpadded, 1-based — at BOTH chapter and track
level; for the canonical 1-chapter-1-track shape, both carry the same value.**

Justification, heaviest first:

1. **Yoto's own sample sets `overlayLabel: "1"` in the same object literal as `key: "01"`**
   (`vanilla-js-html/src/upload.js`). The padded identifier and the unpadded label coexist
   deliberately. That is the best evidence available, and it points one way.
2. **The field is display text, not an identifier.** Yoto's own description calls it *"used
   in the app for track numbering"*. `key` is stable, sortable, padded — an identifier.
   Rendering `01 02 03 … 18` where `1 2 3 … 18` belongs would be a visible regression on
   `7FcVe`.
3. **Zero-padding is a property of *our* `key` scheme, not Yoto's.** `models.py:32`'s
   `key = f"{i:02d}"` is this app's convention. Copying it into `overlayLabel` exports an
   internal convention into a user-visible string.

**Both levels, and this is not hedging:**

- **Track level is required by the schema** (`z.string()`). It is the field we are missing;
  it is not optional.
- **Chapter level is optional, but Yoto's sample sets it**, and the hypothesis under test is
  that the **chapter list** is what the knob browses. Writing only the required level would
  test half the hypothesis and leave a negative result uninterpretable. The marginal cost is
  one more `FieldEdit` per chapter.

**The ordinal is the chapter's 1-based position; a single track inherits its chapter's label.**
One rule, stated once, so create and repair cannot diverge.

**Multi-track chapters are `declined`, not guessed.** All three live cards are 1:1 (5×1, 18×1,
1×1 — read from the bodies), and `build_content_payload` emits one track per chapter by
construction (`models.py:30-53`), so this case does not occur on any card this app has made.
For a card that has one — hand-assembled, or edited in the Yoto app — we have **zero evidence**
for the within-chapter numbering convention, and the repair path mutates live data. So the
label intent reports *"chapter has N tracks; overlayLabel numbering convention unknown -
skipped"* and the **format intent proceeds unaffected**. That is what `declined` is for
(§3.2).

**The shared helper — one function, in `models.py`:**

```python
# yoto_maker/yoto/models.py
def overlay_label(ordinal: int) -> str:
    """The label Yoto shows when browsing a card's chapters/tracks.
    1-based and UNPADDED - deliberately NOT the zero-padded `key`. Yoto's own
    sample writes `overlayLabel: "1"` beside `key: "01"` in the same object."""
    return str(ordinal)
```

`models.py` is the right home: it is already the "pure logic, no network, unit-tested
directly" module (its own docstring, `models.py:1-5`; and the 2026-07-21 ADR §3.2 placed the
corrector there for the same reason), and `repair.py` already imports from the `yoto` package
(`:58-60`).

In `build_content_payload`, the call sits **beside** the existing key computation, inside the
loop that already has `i` from `enumerate(tracks, start=1)` (`models.py:31`):

```
key          = f"{i:02d}"
overlayLabel = overlay_label(i)
```

so the one place a future reader could conflate the two fields is the one place both are
visible. `repair.py` calls `overlay_label(ci + 1)` off the positional walk.

### 3.5 Rollback: removing the field **is** the correct undo

`rollback_from_backup` (`:661-679`) reads a backup, canonicalizes its media refs, re-POSTs it
with its `cardId`, and diffs `_strip_volatile(body)` against `_strip_volatile(after)` at
`:676`.

**Every backup written before this change — including the ten on disk — contains no
`overlayLabel`. Restoring one therefore POSTs a body without the field, and that is correct
and deliberate.** A backup is the verbatim pre-write state; undo means *put the card back
exactly as it was*. `overlayLabel` was absent before our write, so absent is the correct
post-rollback state. A rollback that preserved an unproven field we had just added would not
be a rollback. **Stated here so it is a decision and not an accident.**

**⚠ But the restore's own verify may now fire, and that is a new hazard.** If `POST /content`
**merges** rather than **replaces** — i.e. if Yoto keeps a key omitted from the body — then
`after` still carries `overlayLabel`, the backup does not, and `_diff_paths` at `:676` emits
`"unexpectedly ADDED"` → the restore reports **`verify-failed`** on a card that is in fact
fine. That turns a recovery action into a false alarm at the worst possible moment. §1.4 makes
merge-vs-replace a genuinely open question (Open question 3).

**Decision: a single, named, one-directional tolerance in the rollback path only.**
`rollback_from_backup` post-processes `problems`: a problem whose path ends in
`/overlayLabel` **and** whose shape is `unexpectedly ADDED` is re-reported as a distinct,
explanatory line — *"the card still carries overlayLabel; Yoto's POST /content does not delete
keys omitted from the body. Everything else is restored."* — and does **not** flip the outcome
to `verify-failed`.

The cost, stated: the rollback verify can no longer distinguish *our residual label* from
*a label Yoto wrote itself*. Accepted, because `canonicalize_body_media_refs` (`:375-381`)
already establishes the principle that **a restore never blocks — a restore is a recovery
action**, and a rollback that cries wolf is worse than one that under-reports a field the
operator is deliberately abandoning.

**This is not the `_VOLATILE_TOP_KEYS` trap, and the difference is structural** (see §4.2.1):
it lives **only** in the rollback path, never in `verify_only_declared_changed`; it is scoped
to **one field**; it tolerates only **residual presence**, never a changed value; and it
changes a *report line*, not the diff the repair path acts on.

**Do not post `overlayLabel: null` to clear it.** Track-level `overlayLabel` is `z.string()`,
not `.nullable()` — a null would fail validation and take the whole restore with it.
`overlayLabelOverride` is the nullable one, and we never write it.

### 3.6 What actually changes, by file

| File | Change | Risk |
| --- | --- | --- |
| `yoto_maker/yoto/models.py` | `overlay_label()`; two lines in `build_content_payload`'s loop | Low — pure, no network. **Commit 1.** |
| `yoto_maker/yoto/repair.py` | `FieldEdit` / `ChangeSet` / `apply_change_set`; `build_repair_payload` and `verify_only_declared_changed` re-derived from it; `apply_format_corrections` kept as a wrapper | **Highest in the arc** — it is the safety-critical core. **Commit 2, behaviour-neutral.** |
| `yoto_maker/yoto/repair.py` | the `overlay-label` intent in `plan_card`; `TrackDecision`/`CardPlan` reshape; `correct_keys` retired | Medium. **Commit 3.** |
| `yoto_maker/yoto/repair.py` | `--no-overlay-labels` flag; the three rewritten summary strings; the rollback tolerance | Low. **Commit 3.** |
| `yoto_maker/yoto/repair.py:1-45` | docstring: `FORMAT-ONLY` → the declared-change-set statement | Record. **Commit 3.** |
| `tests/test_repair.py`, `tests/test_models_and_settings.py`, `tests/test_yoto_client.py` | §4.1 | — |
| `docs/DESIGN.md:94` | the one-line `POST /content` shape description gains `overlayLabel` | Record. |
| the three ratification sites (§1.5) | §7 | Record. |

⚠ **Corrected 2026-09-10: "no version bump" was right about the cache key and wrong about the
release.** Nothing under `yoto_maker/server/static/` is touched, so the `__ASSET_V__` key
(`server/app.py:968`) need not move **for cache-busting reasons**. But commit 1 is a shipped,
user-facing change to every card the app makes from here on, and `updater.py` can only see a
**tagged GitHub release** — so **v0.1.14 must exist**, which means `pyproject.toml:7` and
`yoto_maker/__init__.py:3` must move off `0.1.13`. Left as written, this clause would have
produced a release the auto-updater cannot see. The arc's last task owns the bump, per item
19's precedent. Bumping with no static change is a harmless no-op cache bust.

### 3.7 Sequencing — four commits, and the split is the backout plan

⚠ **Corrected 2026-09-10: this sequence was originally three commits. It is four.** A
prerequisite **commit 0** is prepended — the `UnicodeEncodeError` in the repair CLI's own
report (§1.1's footnote; queue **item 28**). It must land **before any `--apply` run**,
because `main` prints each card's result *after* `repair_card` has already POSTed, so today
an apply run against `1WCvI` writes to the live card and then dies before saying whether it
verified. Commits 1–3 keep their numbers, so §8's revert levers are unaffected.

0. **The repair CLI's console encoding.** `sys.stdout.reconfigure(errors="backslashreplace")`
   at the top of `main`. Independently valuable, its own PR, and a hard gate on the staged
   rollout below. **Not** a literal sweep — see item 28.
1. **Create path.** `overlay_label()` + `build_content_payload`. Reverts in 3 lines with zero
   coupling to `repair.py`. This is the half we are most confident about and the half that
   survives a revert of the rest.
2. **The change-set refactor, behaviour-neutral.** Format-only re-expressed as a one-intent
   change-set. **Provable**: every existing `test_repair.py` safety test must still pass,
   re-expressed but not weakened. Nothing about `overlayLabel` lands here.
3. **The `overlay-label` intent**, the flag, the strings, the rollback tolerance, the record
   amendments.

Splitting 2 from 3 is what makes the unproven half revertible **without** also reverting the
invariant machinery. `BUILDER_QUEUE.md` item 13's row already records this discipline —
*"three commit stacks in order 0 → A → B → C … Item A must revert independently"* — and it
applies for the same reason.

**Staged rollout, reusing the advice already printed at `:816-821`:** `gzP2B` (1 track) first,
confirm on the physical player, then `1WCvI`, then `7FcVe`.

---

## 4. Consequences

### 4.1 Required tests — including one the briefing's list gets wrong

**⚠ Lane A's gap is confirmed and is worse than "a test is missing".** No test anywhere
asserts the **full** shape of a chapter or a track in the POST body.
`tests/test_models_and_settings.py:14-28` indexes into named keys
(`chapters[0]["tracks"][0]["trackUrl"]`, `["duration"]`, `chapters[0]["display"]["icon16x16"]`);
`tests/test_yoto_client.py:107-117`, `:240`, `:284-295`, and `:159` do the same against
`last_content`.

⚠ **Corrected 2026-09-10.** This paragraph originally read *"the only exact-equality
assertion in the suite is `tests/test_repair.py:141`."* **That is false** — there are
several (`test_repair.py:257`, `test_api.py:274`, `test_export.py:127`,
`test_yoto_auth.py:106`, …). The real distinction is **absolute** versus **relative**
equality, and it is a *stronger* argument for the test this section requires:

- **`tests/test_repair.py:257` — `assert out == expected` — is a whole-card-body structural
  equality, but a RELATIVE one.** `expected` is `copy.deepcopy(before)` with `format`
  flipped, and `before` is the test's own `_card()` helper. So it pins the corrector's
  narrowness perfectly and is **structurally blind to a field its fixture never had**. It
  cannot fail because `overlayLabel` is missing from both sides.
- **`tests/test_repair.py:141` — `inner == {"cardId": "C1", "title": "T", "content":
  {"chapters": []}}` — is an ABSOLUTE equality, but against an EMPTY chapter list**, so it
  pins nothing about a chapter or a track.

**Nothing in the suite is an absolute equality against a *populated* chapter or track
object.** That — not a simple absence of `==` — is the gap, and it is exactly how a
schema-**required** field stayed missing for the life of the project.

**Consequence: a create-path field addition ships green with nothing holding it — and that is
exactly how `overlayLabel` came to be missing from a required field for the life of the
project.** That is the strongest argument for the test, and it should be written down next to
it.

**REQUIRED — the one test that would have caught this bug:**

- **An exact-equality assertion on one full chapter and its full track** from
  `build_content_payload`. Every key spelled out, `==` not `in`. Any future field addition or
  removal must then be *stated* in the test rather than slipping past it.

**REQUIRED — the create/repair agreement test.** Build a card with `build_content_payload` for
N tracks (N > 9, so padding differences are visible), feed the result to `plan_card`, and
assert **zero label edits are declared**. This is a round-trip equality test, not a value
test: it catches an off-by-one in *either* direction and a structural disagreement (repair
reading the wrong nesting level) that two literal value assertions would both miss. Pair it
with one literal test on `overlay_label` itself (`overlay_label(1) == "1"`,
`overlay_label(10) == "10"`). §6 of the brief asked shared-helper *or* pinning test; the
answer is **both**, because a shared helper does not stop a caller passing the wrong ordinal.

**REQUIRED — the strip case.** A `FakeClient` whose `after` override drops `overlayLabel`
must produce `verify-failed` with an `unexpectedly REMOVED` problem. This is the branch §3.1
exists for and the one §1.4 says is most likely in the field. Without it, the "silently did
not land" failure mode is untested.

**REQUIRED — the report strings.** Assert the `already` / `dry-run` / `applied` summaries do
**not** name `format` or `opus`. ⚠ Write this as an assertion on what the new string
*contains*, not as `"opus" not in msg`: `SESSION_STATE.md:175-178` records item 20's guard
going **vacuous and still passing** when a ruling deleted the number it was negating. Same
trap, same file, same shape.

**Breaks by design — verified individually:**

| Test | Verdict |
| --- | --- |
| `test_repair.py:247-258` `test_corrector_sets_only_format_everything_else_byte_identical` | **Breaks / must be re-expressed.** It *is* the format-only invariant. Re-aim it at `apply_change_set` with a one-intent change-set, and add a sibling for a two-intent set. |
| `test_repair.py:296-301` `test_idempotent_already_opus_no_post` | **Breaks; its premise inverts.** Split into two: all-opus **with** labels → `already`, no POST; all-opus **without** labels → `apply` and exactly one POST. The second test is blocker 1's regression guard. |
| `test_repair.py:336-355` `test_verify_passes_when_only_format_changed` | **Breaks.** Its `after` is `_card("C1", ("opus","opus"))`, which carries no labels, so `intended` and `after` diverge. The `_card()` helper must produce labels. |
| `test_repair.py:184-208` `_card()` helper | **Must be widened** — an `overlay_labels=True/False` parameter, because both states are now fixtures (a labelled card is `already`; an unlabelled one is `apply`). |
| `test_models_and_settings.py:25` — `assert "display" not in chapters[1]` | **❌ Does NOT break.** Adding `overlayLabel` to a chapter does not add a `display` key. The briefing is wrong about this line. It should be **extended** (to assert the label) rather than fixed. |
| `test_yoto_client.py:159` — `assert "display" not in chapters[0]` | **❌ Does NOT break**, for the same reason. Same correction. |
| `test_repair.py:758` — `build_repair_payload(inner, {"0.0"}, {"0.0": canon})` | **Breaks. ADDED 2026-09-10 — this table originally omitted it.** §3.1 changes the signature's second parameter from `correct_keys` to `edits`. Update to `build_repair_payload(inner, format_edits(inner, {"0.0"}), {"0.0": canon})`. |
| `test_repair.py:29` — `from …repair import verify_only_format_changed` | **Breaks. ADDED 2026-09-10.** §3.1 renames it `verify_only_declared_changed`. The **import** is the break; the test body never calls it. Add `format_edits` to the same import while there. |
| `_find_chapters` (`:68-82`) has **three** candidate paths | **Not a test, but a real trap this table should have named. ADDED 2026-09-10.** A `FieldEdit.path` must address the path *this* body actually uses — `apply_change_set` refuses to create a missing intermediate container, so a hard-coded `("content","chapters")` would **raise** on exactly the un-unwrapped bodies the three-candidate fallback exists to tolerate. Needs a `_chapters_path(body)` helper that `_find_chapters`, `_chapter_path` and `_track_path` all share. |

Also in scope: `test_repair.py:145` `test_real_fixture_pins_shape_trackurl_and_format` and
`tests/fixtures/card_sample.json` — the fixture is a real unlabelled body, which makes it the
*right* fixture for the `apply` case; it needs a labelled sibling, not a modification.

### 4.2 Bad — the parts that are the reason this file exists

1. **The refactor touches the most safety-critical code in the repo, and it is the code
   nothing else guards.** `verify_only_declared_changed` is the last line of defence before a
   live card in a real account is rewritten. A bug there does not fail loudly; it **approves a
   bad write**. Mitigations: commit 2 is behaviour-neutral and must leave every existing
   safety test green; the change-set is asserted to hold at most one edit per path; and
   `apply_change_set` **raises** rather than creating a missing intermediate container.
   ⚠ **`_VOLATILE_TOP_KEYS` (`:400`) must not gain an entry in this work.** If a future agent
   proposes it, the answer is in §1.3, and §3.5's rollback tolerance is **not** a precedent
   for it: rollback-path-only, single-field, presence-only, report-line-only.
2. ✅ **~~We are writing an unproven field to live production cards.~~ DISCHARGED
   2026-09-11 — the field is proven.** The original concern is preserved below because it is
   the reason §8 and the flag exist, but it no longer describes the present: *"§1.2: no Yoto
   document says `overlayLabel` gates the knob UI, and the official description says app, not
   player. §8 is the answer, and it is why commit 1 is separable and why the flag exists."*
   **A physical player has now been driven** (2026-09-11): the knob brings up the chapter list
   on a labelled multi-chapter card and selects from it. The field written to those live cards
   is **schema-required, correctly valued, and now demonstrably load-bearing**. Yoto still
   documents nothing about it — so the *documentation* gap in §1.2 is unchanged; what is
   discharged is the *risk*, which was the cost this item was recording.
3. ✅ **~~If Open question 1 returns reading (B), this feature is inert.~~ SETTLED
   2026-09-10 — it does not.** Yoto demonstrably persists a client-supplied track `format`
   (§1.1: all 24 tracks on all three cards read `opus`), so the mechanism `overlayLabel`
   relies on is confirmed and **commit 3 IS to be built**. What remained unproven was not the
   *mechanism* but the *hypothesis* — whether the field gates the knob-browse UI — which was
   item 2 above and was settleable only on a physical player. The distinction mattered: a
   mechanism failure would have made this work pointless, whereas a hypothesis failure would
   have left a schema-required field correctly populated and cost only levers 1 and 3 (§8).
   ✅ **Both halves are now closed: the mechanism on 2026-09-10 (here) and the hypothesis on
   2026-09-11 (item 2 above, §6.2).** Neither failure branch was taken.
4. **`already` changes meaning in a shipped, user-visible report.** Someone who has read
   *"already correct (all 18 tracks 'opus')"* before will read a different sentence. Small, but
   it is the operator's only window into a tool that mutates live cards.
5. **The new report strings land in copy that no handoff package owns.** `BUILDER_QUEUE.md`
   item 26 records exactly this for `_friendly_http`'s sentences — three of them reachable
   only from `yoto/repair.py` — and notes it is *"not plain LOW because `repair.py` mutates
   live production cards, where a misleading error is read by someone deciding whether a write
   landed."* The three strings in §3.2 inherit that, verbatim. **Cross-reference item 26;
   do not open a second ownership question.**
6. **Rollback gains a tolerance, and a tolerance is a blind spot.** §3.5 names its exact
   cost. It is the smallest blind spot that keeps a recovery path from false-alarming, but it
   is not zero.
7. **The ten existing backups predate the field.** They remain valid rollback sources for the
   format fix and are unaffected by this change — but a rollback to one of them after a label
   write is precisely the §3.5 case, so the tolerance must land **in the same commit** as the
   intent, not after it.

### 4.3 Good

- **One invariant that survives a third intent.** The next field Yoto turns out to require is
  a `FieldEdit`, not another hand-kept pair of functions.
- **Blocker 2's silent half is closed, and that is a net safety gain over today.** A server
  that strips a field we declared now reports `verify-failed` instead of `applied` (§3.1).
- **The create path and the repair path cannot drift**, by construction plus a round-trip test
  (§3.4, §4.1).
- **The three live cards become testable.** The knob hypothesis cannot be falsified without a
  card that has the field, and the repair path is the only way to get one onto the
  granddaughter's player without re-making cards by hand. ✅ **This is what actually happened:
  a repaired multi-chapter card settled the hypothesis on hardware 2026-09-11 (§6.2). The
  repair path was the load-bearing half — without it there would have been nothing to test.**
- **The create path ships value alone** (commit 1), for every card made from here on, whatever
  happens to the repair half.
- **`declined` keeps the proven fix available** on a card the unproven one cannot number.

### 4.4 Neutral

- No UX. This is a maintainer CLI (2026-07-21 ADR Addendum `:523-525`). **Designer is not
  needed** — with the §4.2.5 caveat that the three report strings are copy, in a file item 26
  already has an open ownership question about.
- The local draft is untouched; `draft.py` does not change.
- All three live cards are 1 chapter : 1 track, so `declined` never fires on them.

---

## 5. Related

- **Amends:** [`2026-07-21-repair-existing-cards.md`](2026-07-21-repair-existing-cards.md) —
  its Addendum `:514-517` and `:526-528`. §7 has the exact text. **Not superseded.**
- **Beside, not depending on:**
  [`2026-07-21-file-upload-on-job-system.md`](2026-07-21-file-upload-on-job-system.md) — no
  overlap; this work adds no job-backed route.
- **Code this designs against:** `yoto_maker/yoto/repair.py` (`apply_format_corrections`
  `:328`, `build_repair_payload` `:347`, `_VOLATILE_TOP_KEYS` `:400`, `_normalize_url` `:403`,
  `_diff_paths` `:460`, `verify_only_format_changed` `:481`, `TrackDecision` `:504`,
  `CardPlan` `:511`, `CardPlan.outcome` `:528`, `plan_card` `:541`, `CardResult` `:592`,
  `repair_card` `:615`, `rollback_from_backup` `:661`, the summary map `:746-759`, `main`'s
  exit codes `:832`); `yoto_maker/yoto/models.py` (`TrackMeta` `:11`,
  `build_content_payload` `:24`, `key = f"{i:02d}"` `:32`); `yoto_maker/yoto/client.py`
  (`get_card` `:403`, `update_card` `:425`, `probe_artifact` `:457`);
  `yoto_maker/server/app.py` (`_resolve_icon` `:646-656`).
- **Implementation plan:**
  [`plans/2026-09-10-overlay-labels-and-the-declared-change-set.md`](../../superpowers/plans/2026-09-10-overlay-labels-and-the-declared-change-set.md)
  — 26 tasks across commits 0–3, the Test Plan, and a §4 list of this ADR's own corrections.
- **Queue:** items **28** (commit 0 — the CLI-crash prerequisite) and **29** (commits 1–3);
  `docs/BUILDER_QUEUE.md` item 18 (`:468`, the clause this amends) — and **item 26**,
  which already owns the ownerless-copy question §4.2.5 inherits.
- **Ground truth read for this ADR:** the ten real `GET /card` bodies in
  `%LOCALAPPDATA%\YotoMaker\repair-backups\` (§1.1, §1.4); `https://yoto.dev/myo/how-playlists-work.md`
  and `yotoplay/examples` `vanilla-js-html/src/upload.js`, both fetched 2026-09-10 (§1.2).
- **Doc to update:** `docs/DESIGN.md:94`'s one-line `POST /content` shape description.
- ✅ **CLOSED 2026-09-11 — the physical-player test, which was the gate on the whole
  hypothesis, has been run.** This line previously read *"Open and still the gate on the whole
  hypothesis: `SESSION_STATE.md:215-255` — the physical-player test. Never closed."* It ran on
  2026-09-11 and the knob brings up the chapter list (§6.2). ⚠ **Only the chapter-list half of
  that checklist is answered.** Its offline-download question (wi-fi off, watch the
  download-cloud icon) is **untouched by this result** and is still open.

---

## 6. Open questions

1. ✅ **CLOSED 2026-09-10 — the cards are `opus`, July's write landed, and Yoto persists a
   client-supplied track field.** Run read-only twice (the maintainer, then Planner
   independently): all 24 tracks across `gzP2B`, `1WCvI` and `7FcVe` report
   `already 'opus'`, and all three print `already correct … nothing to do`. Readings (A) and
   (B) are both dead, the feature is **not** inert, **commit 3 is to be built**, and
   **blocker 1 (§1.3) bites on all three cards today** — which is what makes the second
   decision axis (§3.2) mandatory rather than defensive. Full evidence, plus the two code
   facts that explain why the original on-disk inference failed: **§1.1**.
2. ✅ **CLOSED 2026-09-11 — YES, on hardware. `overlayLabel` gates the knob-browse UI.**
   The question as asked was *"Does `overlayLabel` actually gate the knob-browse UI? ~75–80%,
   and no Yoto document says so (§1.2). Settled only by the physical-player test
   (`SESSION_STATE.md:232-236`); the granddaughter's household decides it. §8 is what happens
   on a negative."* It was settled exactly there, by exactly them.

   **The evidence, stated as what was observed rather than as a conclusion:** on a physical
   Yoto player, on a multi-chapter card this arc had labelled, **twisting the right-hand knob
   brought up the chapter list, and pressing the knob selected a chapter.** Tested by the
   maintainer's daughter, 2026-09-11. The before state is issue #31 itself — the same class of
   card, unlabelled, produced no list at all — so this is a genuine before/after on the one
   variable this arc changed.

   **Which card: answered by the outcome, not by testimony.** A chapter list can only appear on
   a multi-chapter card, so the card was `1WCvI` (5 chapters) or `ezeaM` (18 chapters), and
   `gzP2B` (1 chapter) is **excluded by the result itself** — under any hypothesis there is
   nothing for it to browse. No claim is made here about which of the two it was, because the
   answer does not depend on it.

   ⚠ **The negative branch of §8 was not taken, but §8 stays and so does the flag** — see the
   box at the top of this file. And **nothing here speaks to the offline download**: that was
   always a separate question on the same checklist and it remains open.
3. **Is `POST /content` a replace or a merge for the inner card object?** Drives whether
   §3.5's rollback tolerance ever fires. **Cheap test:** after the first successful label
   apply on `gzP2B`, immediately `--rollback` the fresh backup and read the outcome.
   `restored` → replace; `verify-failed` naming `overlayLabel` → merge. **Builder verifies
   during the staged rollout; the tolerance ships either way.**
4. **Does Yoto render `"1"` or would it accept `"01"`?** §3.4 decides unpadded on the
   strength of Yoto's own sample, and the decision is **reversible in one line** of
   `overlay_label()`. Worth a look on the player during the test of question 2, but it does
   not gate anything. **Partially informed 2026-09-11, still open:** the unpadded form
   demonstrably *works* — a list built from it rendered and was selectable — and nothing about
   its appearance was reported as wrong. But the two forms were **not compared**, so `"01"` is
   untested rather than ruled out. Unchanged conclusion, one line if it ever matters.
5. **Should `overlayLabelOverride` ever be written?** Both levels have it, both
   `.nullable().optional()` (§1.2). **No** — out of scope, and named here only so a future
   reader knows it was seen and declined, not missed.
6. ✅ **CLOSED 2026-09-10 — fold it in.** The 2026-07-21 ADR's Status line (`:4`) still reads
   `proposed` though PR #20 shipped. The maintainer directed that it be corrected in this
   arc's implementation PR, alongside §7(a)–(d). It becomes
   `accepted — shipped as PR #20 (2026-07-22); amended 2026-09-10 by
   2026-09-10-overlay-labels-and-the-declared-change-set.md`, and both `README.md` Index
   rows move to `accepted` (§7(d)).

---

## 7. The record: **amend**, not supersede

**Amend.** The 2026-07-21 ADR's decisions all still hold — account-first discovery,
update-in-place with `cardId`, all-or-nothing per card, deep-copy-and-overwrite-only,
backup-then-write, verify-after, dry-run-by-default, honest per-card reporting. Exactly **one
clause** changes, and it is a statement of *scope*, not of *mechanism*: "format is the only
field ever written." Superseding would retire a document whose conclusions are correct and
would force a reader to reconcile two files to find the icon-canonicalization and
body-shape findings that only live in its Addendum.

**This ADR is the authority on the scope of `repair.py`'s writes from commit 3 onward.**

The three edits below land **with the implementation PR, not before it** — the format-only
clause is *true of the shipped code today*, and amending the record ahead of the code would
make it wrong in the other direction.

**(a) Appended to `docs/architecture/decisions/2026-07-21-repair-existing-cards.md`:**

> ## Addendum 2 — 2026-09-10: format is no longer the only field written
>
> **Amended by [`2026-09-10-overlay-labels-and-the-declared-change-set.md`](2026-09-10-overlay-labels-and-the-declared-change-set.md).**
>
> The first Addendum's *"`format` is the only field that needed correcting"* (§above) was
> true of what shipped in PR #20, and is **no longer the scope of `repair.py`**. GitHub
> issue #31 found that the app has never sent `overlayLabel`, which Yoto's published schema
> marks **required** at track level. Repairing the three existing cards means writing a
> second field.
>
> **What changed:** the safety invariant. *"Only `format` changed"* is replaced by *"only
> what we **declared** changed"* — an explicit ordered change-set of addressed field writes,
> from which **both** the POST body and the round-trip verify's expectation are derived. The
> narrowness that made format-only valuable is preserved, because the intent now lives in
> data rather than in the shape of the corrector.
>
> **What did not change:** every other principle this ADR established. Account-first
> discovery, update-in-place with `cardId`, all-or-nothing per card,
> deep-copy-and-overwrite-only, backup-then-write, verify-after, dry-run-by-default, honest
> per-card reporting — all retained, and all now expressed over the change-set.

**(b) `yoto_maker/yoto/repair.py:11`** — in the module docstring's safety list, replace

> FORMAT-ONLY correction (fileSize/duration self-correct server-side, channels already right)

with

> DECLARED-CHANGE-SET correction: every write is an explicit `FieldEdit` naming its path, its
> observed value and its intended value, and the round-trip verify's expectation is derived
> from that SAME list - so "only what we declared changed" holds however many intents there
> are. Two intents today: `format` (mp3 -> opus, confirmed by probing the served artifact)
> and `overlay-label` (the missing, schema-REQUIRED `overlayLabel`, written only where absent
> or empty). fileSize/duration self-correct server-side and channels was already right, so
> neither is ever written.

**(c) `docs/BUILDER_QUEUE.md:468`** — item 18 is shipped (✅), and a queue that doubles as a
history must not have its shipped rows rewritten. **Annotate, do not replace.** Change

> **`format` is the only field ever written.**

to

> **`format` was the only field ever written *as of this PR*** — **widened 2026-09-10 by
> [ADR `2026-09-10-overlay-labels-and-the-declared-change-set.md`](architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md)**,
> which replaces the format-only invariant with a declared change-set and adds `overlayLabel`
> as a second intent (issue #31).

**(d)** `docs/architecture/README.md`'s Index gains this ADR's row. **Done with this ADR** —
it is the index of the directory, not a claim about shipped code.

⚠ **Amended 2026-09-10: the row exists, but the Index's *Status* column is still wrong in two
places.** This ADR's own row reads `proposed` though it is now approved, and the
2026-07-21 row reads `proposed (shipped as PR #20; status line is stale)` — a parenthetical
that documents the staleness instead of fixing it. Both move to `accepted` with the
implementation PR, alongside (b) and (c): set 2026-07-21 to
`accepted (shipped as PR #20; amended 2026-09-10)`, dropping the parenthetical, and this ADR
to `accepted`. That closes open question 6 in the same pass, which is what the maintainer
directed on 2026-09-10.

---

## 8. Backout plan

✅ **HISTORICAL AS OF 2026-09-11 — and kept in full, deliberately.** The hypothesis this plan
hedged against is **confirmed on hardware** (§6.2), so no lever below is expected to fire. The
section is **not** deleted and **`--no-overlay-labels` is NOT removed**, for three reasons
worth stating so nobody re-derives them as an argument for deletion:

1. **It is the record of having hedged correctly.** The confidence was ~75–80% when the
   decision was made; that it came up on the right side does not make the hedge wrong, and a
   file that quietly erases its own caution teaches the next reader nothing.
2. **Levers 2 and 4 are not hypothesis-specific.** The third branch of the decision rule below
   — *anything on a repaired card regresses* — is still live, because `repair.py` still writes
   to live cards and something unrelated can still go wrong on one.
3. **The flag is cheap and load-bearing in tests.** Removing it is a code change with no
   benefit, and it is the only way to exercise the format-only path.

**Read everything below as "what was planned for, and why", not as "what is about to happen".**

The hypothesis is ~75–80%. **Four levers, cheapest first, and the commit split in §3.7 is what
makes levers 1 and 3 cheap.**

| # | Lever | Cost | Undoes |
| --- | --- | --- | --- |
| 1 | **`--no-overlay-labels`** on the repair CLI | **zero** — one flag, no deploy, no revert | future repair runs go back to format-only |
| 2 | **`--rollback <backup.json>`** per card | one command per card, backups already written before every POST (`:637`) | the field on that card (§3.5) |
| 3 | **`git revert` commit 1** | ~3 lines, no coupling to `repair.py` | the create path for all future cards |
| 4 | **`git revert` commit 3** | moderate; leaves commit 2's invariant machinery in place | the intent, everywhere |

**Lever 1 is the reason the flag exists.** It is not a convenience: it is the in-code backout,
and it is why the flag must ship **with** the intent rather than being added later if needed.
`--no-overlay-labels` defaults **off** (labels on), so the tool's default behaviour is the
intended one and the lever is explicit.

**Commit 2 is deliberately not on this list.** The change-set invariant is worth keeping
whatever happens to the hypothesis — it closes blocker 2's silent half (§3.1) and it is
behaviour-neutral for format-only. **Never revert 2 to back out 3**, and keeping them separate
is what makes that possible.

**The decision rule, so nobody re-derives it under pressure.** The trigger is the
physical-player test at `SESSION_STATE.md:215-255`, run on a label-repaired card:

- ✅ **The knob brings up a chapter list →** hypothesis confirmed. Keep everything; close issue
  #31; the ratification amendments in §7 stand. **⬅ THIS IS THE BRANCH THAT FIRED, 2026-09-11.**
  Everything is kept, the §7 amendments stand, and issue #31 is closed by the maintainer.
- **The knob still brings up nothing, and the card is otherwise healthy →** hypothesis
  falsified. **Lever 1** immediately (stop writing the field to anything else) and **lever 3**
  (stop writing it on create). **Lever 2 is optional and probably unnecessary** — a schema-
  required field with a correct value is not a defect, and removing it re-introduces the schema
  violation. Leave the three cards labelled, record the negative result in this ADR, and
  re-open the investigation with `playbackType` and the two confirmed dead ends already
  eliminated.
- **Anything on a repaired card regresses — playback, icons, ordering, offline download that
  previously worked →** **lever 2 immediately, per card**, then 1 and 3. This is the only
  branch where rollback is urgent, and it is the branch §3.5's tolerance exists to keep from
  false-alarming.

⚠ `SESSION_STATE.md:254-255`: **streaming in the phone app will likely work even on a
malformed card.** A card that plays in the app is **not** evidence of a fix. The question that
settles the **offline-download** half is *does the offline download complete* — with wifi off,
watching the download-cloud icon. And `SESSION_STATE.md:247-249`'s **Wild Robot confound is
still live**: do not test `1WCvI` against a second Wild Robot card.

⚠ **This paragraph is UNAFFECTED by the 2026-09-11 confirmation and stays exactly as live as it
was.** The chapter list was watched appearing on the hardware; **the offline download was not**.
Those were always two questions on one checklist, and only the first is answered.
