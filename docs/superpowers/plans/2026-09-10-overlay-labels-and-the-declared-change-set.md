# Plan — `overlayLabel` on a declared change-set (issue #31)

**Date:** 2026-09-10
**Author:** Planner
**Queue items:** **28** (commit 0, its own PR) and **29** (commits 1–3, one PR)
**Design basis:** [ADR `2026-09-10-overlay-labels-and-the-declared-change-set.md`](../../architecture/decisions/2026-09-10-overlay-labels-and-the-declared-change-set.md)
— **approved by the maintainer 2026-09-10, including the full declared-change-set
refactor (§3.1), not the minimal Option 4 variant.** This plan implements it. It does
not re-decide it.
**Issue:** [#31](https://github.com/mmackelprang/yoto-maker/issues/31)
**Branches:** `fix/repair-cli-console-encoding` (item 28), then
`feat/overlay-labels` (item 29). Both off `main`. **Never commit either to `main`.**
**Ships in:** **v0.1.14** — item 29's last task owns the bump. See §2.6; this
**corrects ADR §3.6**, which says "no version bump".
**Type:** one correctness fix on a live-card-mutating maintainer CLI (item 28), then
a create-path field addition plus a safety-invariant generalisation (item 29). No new
user-facing surface, no CSS, no markup, **no Designer pass needed** (ADR §4.4).

**Baseline, measured 2026-09-10:** `python -m pytest -q` → **401 passed in 16.19s**.
Every test count in this plan is relative to 401.

---

## 0. What this plan settles before Builder starts

Three things were open when the ADR was written. All three are now closed, two of
them against the ADR. **Read §1 before reading any task** — it changes which blocker
bites and it deletes the ADR's own opening warning.

| # | Question | Answer | Effect on the build |
| --- | --- | --- | --- |
| 1 | Are the three cards `opus` or `mp3`? Has any repair write landed? | **`opus`. The July writes landed.** 24/24 tracks, all three cards. Verified live 2026-09-10 | **Commit 3 IS to be built.** ADR §4.2.3's "do not build it" branch is dead |
| 2 | Does Yoto persist a client-supplied track field? | **Yes** — that is what (1) proves | `overlayLabel` is **not** inert. ADR §1.1 readings (A) and (B) are both dead |
| 3 | Why did July's "ASCII-safe CLI output" not stop the crash? | **It never could have.** It swept em-dashes out of *source literals*; the crash comes from *Yoto's JSON* | Commit 0's fix is `errors=` on the stream, **not** another literal sweep |

---

## 1. Findings that correct the ADR

### 1.1 ⚠ The ADR's §1.1 is falsified. Its opening warning must be deleted, not softened.

The ADR opens (`:20-24`) with a boxed warning that *"the evidence on this machine says
they are not [opus], and that no repair write has ever landed,"* and raises the
possibility that *"this entire feature is inert."* **That is wrong.** Run read-only on
2026-09-10 (no `--apply`, so it cannot write):

```
cd D:/prj/yoto-maker && PYTHONUTF8=1 python -m yoto_maker.repair --card-id gzP2B,1WCvI,7FcVe --dry-run
```

```
Phoebe The Fashion Fairy (gzP2B) - 1 track
  [=] track 0.0 "RAINBOW MAGIC, PHOEBE,The Fashion Fairy": already 'opus'
  RESULT: already correct (all 1 track(s) 'opus') - nothing to do
Wild Robot (1WCvI) - 5 tracks
  [=] track 0.0 "The Wild Robot 🤖 … (part 1)": already 'opus'     (×5, all 'opus')
  RESULT: already correct (all 5 track(s) 'opus') - nothing to do
The BFG (7FcVe) - 18 tracks
  [=] … ×18, all 'opus'
  RESULT: already correct (all 18 track(s) 'opus') - nothing to do
```

**All 24 tracks across all three cards are `opus`.** So the July write landed, and
**Yoto persists a client-supplied `format`** — which is precisely the mechanism
`overlayLabel` depends on. Readings (A) and (B) are both dead, and the feature is not
inert.

**Why the ADR went wrong, stated so it cannot recur.** Two facts about the backup
mechanism, both code facts:

1. **A backup is the *pre-write* snapshot.** `_write_backup` runs at `repair.py:637`,
   *before* the POST at `:648`. So the newest backup per card is the state
   **immediately before the last write that landed** — never the state after it.
   The ADR read "the newest backup says `mp3`" as "the card is `mp3`".
2. **A repaired card stops producing backups.** Once every track is `opus`,
   `plan.outcome` is `"already"` and `repair_card` returns at `:626` — *before*
   `_write_backup` at `:637`. So **the absence of any backup newer than 2026-07-22
   08:56 is the signature of a successful repair**, not evidence that nothing ran.
   The ADR `:70-72` read that absence the other way.

**And the timeline the ADR called unexplained is fully explained.** Ten backups on
disk; `edc3c6d` (*"canonicalize display.icon16x16 to yoto:#&lt;mediaId&gt;"*) was committed
**2026-07-22 08:42:13 local**:

| Run | Cards | Before/after `edc3c6d` (08:42) | Outcome |
| --- | --- | --- | --- |
| 07:50:16–07:50:33 | all three | **before** | Yoto 400 on resolved icon URLs (`repair.py:24-27`) — nothing landed |
| 07:51:22–07:51:25 | all three | **before** | same 400 — nothing landed |
| **08:25:17** | `gzP2B` only (the staged-rollout "smallest card first" advice at `:816-821`) | **before, by 17 minutes** | same 400 — nothing landed. **This is the ADR's "unexplained" run** |
| **08:54:00 / 08:54:51 / 08:56:07** | `gzP2B`, `1WCvI`, `7FcVe` — in exactly the documented `--card-id` order | **after** | **landed.** Hence `already 'opus'` today, and hence no eleventh backup |

Every data point is accounted for without appeal to (A) or (B). **Nothing is left
unexplained, and no open question remains here.**

### 1.2 Blocker 1 is confirmed live, not defensively. The second decision axis is mandatory.

ADR §1.3's blocker 1 carries a ⚠ hedge (`:128-131`) saying its premise is what §1.1
disputes and that it *"does not bite on them today."* **It bites on all three, today.**
Every one of the three reports `already correct … nothing to do`, so without ADR §3.2's
second decision axis the widened repair is a **silent no-op on every card that needs
it** — including the only three cards that can test the hypothesis. The hedge must go.

### 1.3 Two tests in circulation as "will break" do not break. Trust ADR §4.1.

Verified individually:

- `tests/test_models_and_settings.py:25` — `assert "display" not in chapters[1]`
- `tests/test_yoto_client.py:159` — `assert "display" not in chapters[0]`

Adding `overlayLabel` adds no `display` key. **Both keep passing and must be
*extended*, not fixed.** ADR §4.1's table has this right; any other list is wrong.

### 1.4 ⚠ ADR §4.1's "only exact-equality assertion" claim is imprecise — and the precise version is a stronger argument

The ADR says *"The only exact-equality assertion in the suite is
`tests/test_repair.py:141`."* That is false as written. `tests/test_repair.py:257` is
`assert out == expected` — a whole-card-body structural equality. There are others
(`test_api.py:274`, `test_export.py:127`, `test_yoto_auth.py:106`, …).

The real distinction is **absolute** versus **relative** equality, and it makes the
case better:

- `test_repair.py:257` compares `apply_format_corrections`' output against a
  **deepcopy of the test's own input** plus one known delta. It pins the *corrector's
  narrowness* perfectly and is **structurally blind to a field the fixture never
  had** — because the fixture is `_card()`, the test's own invention.
- `test_repair.py:141` is an absolute equality, but against an **empty** chapter list.

**Nothing in the suite is an absolute equality against a *populated* chapter or track
object.** That is the gap, and it is exactly how a schema-**required** field stayed
missing for the life of the project. Task 1.4 closes it, and its docstring says so.

### 1.5 July's "ASCII-safe CLI output" did not regress. It was never the right fix.

`516cbf7` (*"fix(repair): ASCII-safe CLI output (avoid Windows-console
mojibake/UnicodeEncodeError)"*, 2026-07-22 00:06, inside PR #20 / item 18) was **26
insertions, 26 deletions, one file**: it replaced `—`/`–`/`…`/curly quotes with ASCII
**in `repair.py`'s own string literals**. There is no `_safe()` helper, no `print()`
wrapper, no `reconfigure` call anywhere in the repo, then or now.

It could not have covered this crash, for two independent reasons:

1. **The crashing text is runtime server data.** `d.ref.title` is assigned at
   `repair.py:317` straight out of the `GET /card` JSON. A sweep over source literals
   cannot reach it.
2. **Different character class.** Every character `516cbf7` removed *is* encodable in
   cp1252 (em-dash `0x97`, ellipsis `0x85`, curly quotes `0x91`–`0x94`) — it was
   fixing **mojibake on an OEM console** (cp437/cp850), which is what its message
   says. `U+1F916` is encodable in **no** single-byte Windows codepage.

**What has actually been keeping the tool alive is `$env:PYTHONUTF8=1`, and it lives
only in prose** — `SESSION_STATE.md:245` and the ADR's own command at `:77`. The
original runbook (`plans/2026-07-21-repair-existing-cards.md:1316`) omits it, which is
why the command in issue #31's report crashes. Nothing in the code sets or checks it.

**And the gap entered the record as *cleared*.** `0240cbb`'s pre-merge review, under
"Reviewed and cleared, not changed":

> - Unicode track titles are safe - the rotating handler pins encoding="utf-8"
>   (logging_setup.py:22), which matters given this codebase's cp1252 history.

That is **correct for the log file and only the log file** (`logging_setup.py:22` does
pin UTF-8). The console `print()` path was never in its scope. A reviewer asked the
right question and a true answer about the wrong stream closed it.

⚠ **Therefore: do not "fix" this with another literal sweep, and do not fix it with
the env var.** §Commit 0 fixes the stream.

### 1.6 The CLI output layer has never been executed by a test

`tests/test_repair.py` has 47 tests and imports 13 names from `yoto_maker.yoto.repair`.
**Neither `_print_card_result` nor `main` is among them.** There is no `capsys`,
`capfd` or `capsysbinary` anywhere in `tests/`. And `tests/fixtures/card_sample.json`
is **100% ASCII**, so even adding a capture test against the existing fixture would
not exercise a non-ASCII title. Three layers of invisibility, which is why CI is green
while the tool crashes after a live write.

### 1.7 Findings the ADR's §4.1 table omits, which Builder will hit

| What breaks | Why the ADR missed it |
| --- | --- |
| `tests/test_repair.py:758` — `build_repair_payload(inner, {"0.0"}, {"0.0": canon})` | The signature changes from `correct_keys` to `edits` in commit 2. ADR §4.1 names `:145` and the fixture but not this call |
| `tests/test_repair.py:29` — `from …repair import verify_only_format_changed` | ADR §3.1 renames it to `verify_only_declared_changed`. The import is the break; the test body never calls it |
| `_find_chapters` has **three** candidate paths (`repair.py:74`) | A `FieldEdit.path` must address the path *this* body actually uses, or `apply_change_set` raises on a still-wrapped body that `_find_chapters` handles today. Needs `_chapters_path()` — Task 2.2 |

### 1.8 A decision the ADR leaves ambiguous, settled here

ADR §3.4 says a multi-track chapter is `declined`. It does not say whether the
**chapter-level** label is still written. **Decision: decline both levels.** Writing
the chapter label alone would leave the schema-**required** track field missing while
making a later run's idempotency check see a labelled chapter and skip it — a partial
job that permanently hides itself. Decline the whole chapter, format intent unaffected.

### 1.9 Not in scope, filed instead

- **`yoto_maker/main.py:43`, `:74`, `:89`** carry em-dashes and print `cfg.data_dir`
  (which holds the Windows username). Same class, different entry point, no card data.
  → **item 30.**
- **`client.py:587-590` and `:594-597`** carry `U+2019`/`U+2014` and are reachable from
  the repair CLI via `repair.py:804` and `:828`. Commit 0's `errors=` guard makes them
  **safe** without touching them. **Do not edit this copy** — it is the family whose
  ownership is item 26's open question, and ADR §4.2.5 says not to open a second one.
  `client.py:550-554`'s `📁` is unreachable from repair (`too_big=` is passed only from
  `_put_audio`, the send path) — a loaded gun pointed elsewhere. Note in the PR; change
  nothing.

---

## 2. Global constraints

**2.1 Branch per item, PR per item.** Item 28 merges before item 29 starts. Auto-merge
is permitted per the maintainer's policy once tests pass, review is clean and important
findings are addressed — **except** where §2.7 says pause.

**2.2 Item 28 is a hard prerequisite for any `--apply` run.** `main` prints the
per-card result at `:831`, **after** `repair_card` has POSTed at `:648`. A crash there
means the write landed and the operator cannot tell whether it verified, whether a
backup exists, or which card to roll back. Wild Robot (`1WCvI`) is one of the three
cards this arc repairs and has `U+1F916` in all five track titles.

**2.3 Commit 2 is behaviour-neutral and is never reverted.** Every existing
`tests/test_repair.py` safety test must still pass — re-expressed where the signature
moved, **never weakened**. Commit 2 is the backout design (ADR §8): reverting 3 must
not require reverting 2.

**2.4 `_VOLATILE_TOP_KEYS` (`repair.py:400`) gains no entry in this work.** Not one.
ADR §1.3 and §4.2.1 explain why; §3.5's rollback tolerance is **not** a precedent —
it is rollback-path-only, single-field, presence-only, report-line-only.

**2.5 `overlayLabel` is only ever written where absent or empty.** Never a value
clobber. A user who typed `"Chapter 1"` in the Yoto app keeps it.

**2.6 ⚠ ADR §3.6's "No version bump" is wrong about the release, right about the cache
key.** No file under `yoto_maker/server/static/` is touched, so the `__ASSET_V__` key
(`server/app.py:968`) need not move *for cache reasons*. But commit 1 is a **shipped,
user-facing change to every card made from here on**, and `updater.py` can only see a
tagged GitHub release — so **v0.1.14 must exist**, and something must bump
`pyproject.toml:7` and `yoto_maker/__init__.py:3` from `0.1.13`. Item 29's last task
owns it, per item 19's precedent. Bumping with no static change is a harmless no-op
cache bust.

**2.7 Pause and ask the maintainer, do not auto-merge, if:** any gate is red; the
commit-2 refactor cannot keep an existing safety test passing without weakening it;
`apply_change_set` needs to create an intermediate container to make a real card work;
or the staged rollout's first `--apply` returns anything but `applied`.

**2.8 No `git -C`.** `cd D:/prj/yoto-maker && git <cmd>`.

---

# ITEM 28 — the repair CLI crashes after it has already written

**Branch:** `fix/repair-cli-console-encoding` · **PR:** its own · **No version bump**
(pure CLI robustness; ships inside v0.1.14's cut) · **Commit 0 of the arc**

## Task 1.1 — A failing test first: the CLI output layer, executed for the first time

New file `tests/test_repair_cli_output.py`. It must **fail** before Task 1.2.

The encoding is **forced**, not inherited. The project's own precedent
(`tests/test_static_cache.py:99-127`) warns that a behavioural encoding test *"cannot
fail on a UTF-8-locale machine"* and pairs it with a canary plus a source assertion.
Forcing the codec is strictly better: it fails on Linux CI too.

```python
"""The repair CLI's console output layer — executed here for the first time.

WHY THIS FILE EXISTS. `tests/test_repair.py` has 47 tests and imports 13 names from
`yoto_maker.yoto.repair`; neither `_print_card_result` nor `main` is among them, and
nothing in `tests/` captures stdout at all. So the layer that reports whether a live
write landed had no coverage, and `tests/fixtures/card_sample.json` is 100% ASCII, so
even a capture test against it would not have exercised a non-ASCII title.

Issue #31's report: `python -m yoto_maker.repair --card-id 1WCvI --dry-run` raises
UnicodeEncodeError at `_print_card_result`, because Wild Robot's five track titles
each carry U+1F916 ROBOT FACE and they arrive from Yoto's JSON (`repair.py:317`).
In APPLY mode that print happens at `main`'s `:831`, AFTER `repair_card` POSTed at
`:648` - so the operator is left unable to tell whether the write landed.
"""
from __future__ import annotations

import ast
import inspect
import io
import textwrap
from pathlib import Path

import pytest

from yoto_maker.yoto import repair as repair_mod
from yoto_maker.yoto.repair import CardPlan, CardResult, TrackDecision, TrackRef

ROBOT = "\U0001f916"          # U+1F916; encodable in NO single-byte Windows codepage
TITLE = f"The Wild Robot {ROBOT} By Peter Brown (part 1)"


def _cp1252_stdout() -> io.TextIOWrapper:
    """A real text stream whose codec cannot encode U+1F916, with the strict-ish
    error handler a fresh interpreter gives a redirected stdout. Forced rather
    than inherited so this test fails on a UTF-8 machine and on Linux CI too."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                            write_through=True)


def _result(outcome="already", *, title=TITLE, card_title="Wild Robot", problems=()):
    ref = TrackRef(cid=0, tid=0, key="0.0", title=title,
                   declared_format="opus", artifact_url="https://x/a")
    decision = TrackDecision(ref, "already", "already 'opus'")
    plan = CardPlan(card_id="1WCvI", title=card_title, decisions=[decision])
    return CardResult("1WCvI", card_title, outcome, plan, None, list(problems))


def test_print_card_result_survives_a_track_title_the_console_cannot_encode(monkeypatch):
    """THE issue #31 crash. Must not raise, and must not silently print nothing."""
    stream = _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result())

    written = stream.buffer.getvalue().decode("cp1252")
    assert "already 'opus'" in written          # the line was really emitted
    assert "Wild Robot" in written
    assert ROBOT not in written                 # it could not be; it was escaped
    assert "\\U0001f916" in written             # losslessly, not dropped to '?'
```

⚠ **`TrackDecision` / `CardPlan` / `CardResult` are reshaped in commit 3.** This file
is written against their **item 28** shapes. Task 3.3 updates it.

## Task 1.2 — Fix the stream, not the literals

Add to `yoto_maker/yoto/repair.py`, directly above `main`:

```python
def _make_console_safe() -> None:
    """Never let a card's own text crash the CLI. Call this FIRST in `main`.

    Card and track titles come straight out of Yoto's JSON (`iter_tracks` at :317,
    `_card_title` via :585 and :677), and `_diff_paths` (:460-478) `repr()`s
    arbitrary card field values into the problem strings - and Python 3's `repr()`
    does NOT escape printable non-ASCII, so `{a!r}` is no protection. When stdout is
    a pipe, a file, or a legacy Windows console, its codec is the locale's (cp1252
    on the maintainer's box) and the write raises UnicodeEncodeError.

    THIS IS NOT COSMETIC. `main` prints each card's result at :831, AFTER
    `repair_card` has already POSTed at :648. A crash here means the write landed
    and the operator cannot tell whether it verified, whether a backup was written,
    or which card to roll back. Wild Robot (1WCvI) carries U+1F916 in all five
    track titles (issue #31).

    WHY `errors=` AND NOT `encoding=`. Setting only the error handler cannot make
    any currently-working output worse: where the stream is already UTF-8 the
    handler never fires, and where it is not, an unencodable character becomes
    `\\U0001f916` instead of an exception. Forcing `encoding="utf-8"` would also fix
    the crash but can turn a real OEM console's correct output into mojibake, so it
    is rejected. `backslashreplace` over `replace` because `?` destroys information
    an operator may be using to identify which track is which.

    WHY NOT THE 2026-07-22 APPROACH. `516cbf7` ("ASCII-safe CLI output") replaced
    em-dashes with hyphens in THIS FILE'S OWN LITERALS - 26 lines, one file. Every
    character it removed is encodable in cp1252; it was fixing OEM-console mojibake.
    A literal sweep cannot reach text that arrives over the wire, so it never
    covered this and a second sweep would not either. `0240cbb`'s pre-merge review
    then cleared "Unicode track titles are safe" on the strength of
    `logging_setup.py:22`'s `encoding="utf-8"` - true of the LOG FILE, and the
    console `print()` path was never in its scope.

    WHY NOT `$env:PYTHONUTF8=1`. It works, and it is the only reason this tool has
    ever completed a run - but it lives in two prose lines (`SESSION_STATE.md:245`
    and the 2026-09-10 ADR's own command at :77) and in no code. The original
    runbook omits it, which is exactly how issue #31 was filed. A fix that depends
    on the operator remembering an env var is not a fix.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:          # already-replaced stream, or a frozen build
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):    # a stream that refuses reconfiguration
            pass
```

Then make it the **first statement** of `main` — before `parse_args`, so `--help` and
`parser.error` at `:798` are covered too:

```python
def main(argv: list[str] | None = None) -> int:
    _make_console_safe()          # BEFORE any print, including argparse's own
    parser = argparse.ArgumentParser(
```

**Verified mechanism** (2026-09-10, piped stdout, cp1252): `reconfigure(errors=...)`
with no `encoding` keeps `encoding='cp1252'`, flips `errors` from `surrogateescape` to
`backslashreplace`, and the 🤖 line prints as `\U0001f916` instead of raising.

## Task 1.3 — Cover the other card-derived emit sites, in one test each

Every site below can carry text from Yoto. Add a test per row to
`tests/test_repair_cli_output.py`, each forcing `_cp1252_stdout()`.

| `repair.py` | What leaks | Test |
| --- | --- | --- |
| `:740` | `res.title` — the card's own title | fold into Task 1.1 (`card_title=f"Wild Robot {ROBOT}"`) |
| `:742` | `res.backup_path` — carries the Windows username | `backup_path=Path(f"C:/Users/{ROBOT}/b.json")` |
| `:745` | `d.ref.title` | Task 1.1 |
| `:762` | **the widest hole** — `res.problems`, built by `_diff_paths`'s `f"{path}: {a!r} -> {b!r}"`. `repr()` does not escape printable non-ASCII | `problems=[f"/title: 'a' -> {TITLE!r}"]`, assert no raise |
| `:793` | `s.title` on `--list`, from `GET /content/mine` | drive `main(["--list"])` with a fake client whose `CardSummary.title` carries `ROBOT` |
| `:804` | `str(exc)` from `resolve_targets` — the ambiguous-title raise at `:723` interpolates **every** candidate's `m.title` | two `CardSummary`s with `ROBOT` titles, assert exit code 2 and no raise |
| `:828` | `{exc}` — `YotoError` text, i.e. `_friendly_http`'s sentences (`client.py:587-590`, `:594-597` carry `U+2019`/`U+2014`) | raise `YotoError("Yoto wouldn\u2019t take that \u2014 too big.")` from `repair_card`; assert no raise. **Do not edit `client.py`** — §1.9 |

For the `main()`-driving tests, monkeypatch `repair_mod.YotoClient` to a fake with
`is_connected()` → `True`, and `repair_mod.get_config` if the backup dir is reached.

## Task 1.4 — Pin the guard at the source level, the way this repo already does

`tests/test_static_cache.py:114-127` carries the warning to honour verbatim: *"Match
the call itself, not the bare string: the route's docstring explains the encoding trap
and therefore contains `encoding="utf-8"` as prose, so a looser assertion passes on the
documentation while the actual argument is gone. (It did, when this test was first
written.)"* `_make_console_safe`'s docstring names `errors=`, `backslashreplace`,
`encoding="utf-8"` and `PYTHONUTF8` as prose. **A substring test would be vacuous.**

```python
def test_main_calls_the_console_guard_before_anything_can_print():
    """The behavioural tests above force cp1252, so they hold on any machine - but
    they call `_make_console_safe()` themselves. This asserts `main` does too, and
    that it does so FIRST, since argparse prints `--help` and `parser.error` before
    any of our own output.

    Assert on the CALL, not on a substring: `_make_console_safe`'s own docstring
    contains `errors=`, `backslashreplace` and `PYTHONUTF8` as prose, so a bare
    substring check would pass on the documentation with the call deleted - the
    exact trap `tests/test_static_cache.py:114-127` records hitting.
    """
    fn = ast.parse(textwrap.dedent(inspect.getsource(repair_mod.main))).body[0]
    first = fn.body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        first = fn.body[1]          # tolerate a docstring being added later
    assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call), (
        f"main's first statement is {ast.dump(first)[:80]}, not a call")
    assert getattr(first.value.func, "id", None) == "_make_console_safe"


def test_the_guard_sets_only_the_error_handler_and_not_the_encoding():
    """Forcing `encoding="utf-8"` would also stop the crash but can turn a real OEM
    console's correct output into mojibake. The `errors`-only form cannot make any
    working output worse. Pin the choice, or a future 'improvement' silently widens
    the blast radius of a tool that mutates live cards."""
    src = inspect.getsource(repair_mod._make_console_safe)
    assert 'reconfigure(errors="backslashreplace")' in src
    assert 'reconfigure(encoding=' not in src
```

## Task 1.5 — Re-label the prose workaround; do not delete it

The env var is no longer needed to avoid a **crash**, but it is still the only way to
get **correct** glyphs rather than escapes on a redirected stream. Leaving it unexplained
implies the crash is still live; deleting it loses a real benefit.

- `SESSION_STATE.md:245` — keep `$env:PYTHONUTF8=1` and append:
  *"(optional since item 28 — the CLI no longer crashes without it; it only changes
  `\U0001f916` back into `🤖`.)"*
- The ADR's command at `:77` — same note. Do this in Task 3.7's ADR pass, not here,
  to keep item 28's diff to code + tests + `SESSION_STATE.md`.

## Task 1.6 — Close item 28

Mark the row ✅ with the PR link. In the PR body, state plainly: **`516cbf7` did not
regress — it was never the right fix**, with §1.5's two reasons, so the next reader does
not re-apply a literal sweep. Record the new test count (401 + the tests added).

---

# ITEM 29 — `overlayLabel` on a declared change-set

**Branch:** `feat/overlay-labels` off `main` **after item 28 merges** · **one PR,
three commit stacks in order 1 → 2 → 3**, following item 13's discipline · **owns the
v0.1.14 bump**

## COMMIT 1 — the create path

Reverts in a handful of lines with zero coupling to `repair.py`. ADR §8 lever 3.

### Task 2.1 — `overlay_label()` in `models.py`

Append to `yoto_maker/yoto/models.py`:

```python
def overlay_label(ordinal: int) -> str:
    """The label Yoto shows when browsing a card's chapters and tracks.

    1-based and UNPADDED - deliberately NOT the zero-padded `key`. Three reasons,
    heaviest first:

      1. Yoto's own sample app writes `overlayLabel: "1"` in the SAME object
         literal as `key: "01"` (yotoplay/examples, vanilla-js-html/src/upload.js,
         fetched 2026-09-10). The padded identifier and the unpadded label coexist
         deliberately.
      2. The field is display text, not an identifier - Yoto describes it as "used
         in the app for track numbering". Rendering `01 02 ... 18` where
         `1 2 ... 18` belongs would be a visible regression on an 18-chapter card.
      3. Zero-padding is a property of OUR `key` scheme (`key = f"{i:02d}"` below),
         not Yoto's. Copying it into a user-visible string exports an internal
         convention.

    THIS IS THE ONLY PLACE THE VALUE IS COMPUTED. The create path below and the
    repair path's `overlay-label` intent (`yoto/repair.py`) both call it, so the two
    cannot drift - and `tests/test_repair.py`'s round-trip agreement test proves it
    for N > 9, where a padding difference would show.

    The ordinal is the chapter's 1-based position; a single track inherits its
    chapter's label. NEVER derive it from the card's own `key` field - `key` is
    "01" and the label is "1", so a path that read `key` and a path that computed
    from the index would disagree and the two could flip-flop forever.

    Reversing the decision is one line (ADR 2026-09-10 open question 4).
    """
    return str(ordinal)
```

### Task 2.2 — Emit it at both levels in `build_content_payload`

Replace the loop body (`models.py:31-53`). `overlayLabel` sits **immediately after
`key`** at both levels, so the one place a reader could conflate the padded and
unpadded fields is the one place both are visible (ADR §3.4).

```python
    for i, t in enumerate(tracks, start=1):
        key = f"{i:02d}"
        label = overlay_label(i)        # UNPADDED "1" beside the PADDED key "01"
        display = {"icon16x16": t.icon_ref} if t.icon_ref else {}
        track = {
            "key": key,
            "overlayLabel": label,      # REQUIRED by Yoto's track schema (issue #31)
            "title": t.title,
            "trackUrl": f"yoto:#{t.transcoded_sha}",
            "type": "audio",
            "format": t.fmt,
            "duration": round(t.duration_s),
            "fileSize": t.file_size,
            "channels": t.channels,
        }
        if display:
            track["display"] = dict(display)
        chapters.append(
            {
                "key": key,
                "overlayLabel": label,  # optional at chapter level; Yoto's sample sets it
                "title": t.title,
                "tracks": [track],
                **({"display": display} if display else {}),
            }
        )
```

Also update `build_content_payload`'s docstring: after *"with the per-track pixel icon
on the chapter's display"*, add *"and `overlayLabel` at both levels — the label Yoto
shows when the player's knob browses chapters (see `overlay_label`)."*

### Task 2.3 — The test that would have caught this bug

Add to `tests/test_models_and_settings.py`:

```python
def test_build_content_payload_pins_one_full_chapter_and_track_exactly():
    """EXACT equality on a whole chapter and its whole track. Every key spelled out.

    WHY THIS TEST EXISTS, and why it must stay an `==` and never soften into `in`
    checks: `overlayLabel` is REQUIRED by Yoto's published track schema, and this
    app never sent it for the entire life of the project - the player's knob brought
    up no chapter list on any card it ever made (issue #31). Nothing caught it,
    because every other assertion in the suite indexes into keys it already expects
    to be there, and a missing key is invisible to that.

    The two near-misses, so nobody thinks this duplicates them. `test_repair.py:257`
    does compare a whole card body, but against a deepcopy of its OWN INPUT plus one
    known delta - it pins the corrector's narrowness and is structurally blind to a
    field its fixture never had. `test_repair.py:141` is an absolute equality, but
    against an EMPTY chapter list. This is the suite's only absolute equality
    against a POPULATED chapter and track.

    Consequence, deliberately: any future field added to or removed from the
    create-path payload must be STATED here. A payload change that cannot be stated
    here is a payload change nobody reviewed.
    """
    p = build_content_payload("My Card", [
        TrackMeta("Intro", "sha1", 30.4, 1000, icon_ref="yoto:#i1"),
    ])
    assert p["content"]["chapters"][0] == {
        "key": "01",
        "overlayLabel": "1",
        "title": "Intro",
        "display": {"icon16x16": "yoto:#i1"},
        "tracks": [
            {
                "key": "01",
                "overlayLabel": "1",
                "title": "Intro",
                "trackUrl": "yoto:#sha1",
                "type": "audio",
                "format": "mp3",
                "duration": 30,
                "fileSize": 1000,
                "channels": "stereo",
                "display": {"icon16x16": "yoto:#i1"},
            }
        ],
    }


def test_build_content_payload_pins_the_top_level_shape():
    """No test pinned the POST body's TOP-LEVEL keys either - `test_yoto_client.py`
    and the test above both index into `["content"]["chapters"]` - so a create-path
    change could add or drop a top-level key and ship green.

    `content` carries `chapters` and nothing else. Yoto ADDS `playbackType`,
    `version`, `activity`, `availability`, `cover` and `config` server-side (ADR
    2026-09-10 §1.4, measured against the real gzP2B body); we must not start
    sending them.
    """
    p = build_content_payload("My Card", [TrackMeta("Intro", "sha1", 30.4, 1000)])
    assert set(p) == {"title", "content", "metadata"}
    assert set(p["content"]) == {"chapters"}
    assert set(p["metadata"]) == {"media"}
    assert set(p["metadata"]["media"]) == {"duration", "fileSize"}


def test_overlay_label_is_one_based_and_unpadded():
    """Pin the VALUE as well as the plumbing. A shared helper stops the create and
    repair paths disagreeing; it does not stop both being wrong. N > 9 is the case
    that distinguishes unpadded from padded."""
    from yoto_maker.yoto.models import overlay_label
    assert overlay_label(1) == "1"
    assert overlay_label(9) == "9"
    assert overlay_label(10) == "10"
    assert overlay_label(18) == "18"
```

### Task 2.4 — Extend the two tests that do **not** break

Neither of these fails; both must be widened or they keep asserting less than they
could (§1.3).

- `tests/test_models_and_settings.py:25` — keep `assert "display" not in chapters[1]`
  and add beneath it:
  ```python
      # `overlayLabel` is present at both levels regardless of whether an icon is
      # (issue #31) - the two are independent, which is why the line above still holds.
      assert chapters[1]["overlayLabel"] == "2"
      assert chapters[1]["tracks"][0]["overlayLabel"] == "2"
      assert [c["key"] for c in chapters] == ["01", "02"]      # padded, unchanged
  ```
- `tests/test_yoto_client.py:159` — keep `assert "display" not in chapters[0]` and add:
  ```python
      assert chapters[0]["overlayLabel"] == "1"                # survives a failed icon
      assert chapters[0]["tracks"][0]["overlayLabel"] == "1"
  ```
- `tests/test_yoto_client.py:107-117` — add `assert track["overlayLabel"] == "1"` beside
  the existing `track["format"] == "opus"` assertion, so the end-to-end create path
  pins it too.

**Gate for commit 1:** whole suite green. Commit 1 is revertible on its own.

---

## COMMIT 2 — the change-set refactor, behaviour-neutral

⚠ **This is the most safety-critical code in the repo and nothing else guards it.**
`verify_only_declared_changed` is the last line of defence before a live card in a real
account is rewritten, and a bug there does not fail loudly — **it approves a bad
write.** Commit 2 adds **no** `overlayLabel` anywhere.

### Task 2.5 — `FieldEdit`, `ChangeSet`, and the absent sentinel

Insert above `apply_format_corrections` (`repair.py:328`):

```python
# --------------------------------------------------------------------------- #
# The declared change-set: the safety invariant, expressed as data.
#
# "after == before + the declared change-set, and NOTHING else."
#
# Before 2026-09-10 the invariant was "only `format` changed", and it was strong
# because it was narrow - narrow because the intent was hard-coded into the shape of
# the corrector. Generalising the intent into DATA keeps the narrowness while allowing
# more than one intent: the POST body and the round-trip verify's expectation are both
# derived from the SAME list, so an intent cannot be added to one and forgotten in the
# other. ADR 2026-09-10 §3.1.
# --------------------------------------------------------------------------- #
class _Absent:
    """Sentinel for 'this key was not present in the GET body'. A real `None` is a
    value Yoto could legitimately have sent, so it cannot stand in for absence."""
    def __repr__(self) -> str:
        return "<absent>"


_ABSENT = _Absent()


@dataclass(frozen=True)
class FieldEdit:
    """One declared field write.

    `old` is carried for the CLI report and is DELIBERATELY NOT CHECKED by
    `apply_change_set`: `plan_card` and `repair_card` read the body once and plan
    from that same object, so `old` cannot have gone stale between planning and
    applying. It is documentation of why the edit was declared, not a guard - do not
    add a caller that assumes it is one.
    """
    path: tuple            # ("content","chapters",0,"tracks",0,"overlayLabel")
    old: object            # value observed in the GET body; _ABSENT if the key was missing
    new: object            # the value to write
    intent: str            # "format" | "overlay-label" - groups the report
    reason: str            # printed per-track in the CLI report


ChangeSet = list          # list[FieldEdit]; ordered, at most one edit per path (asserted)
```

### Task 2.6 — `_chapters_path()`, so an edit addresses the body's real shape

`_find_chapters` (`:68-82`) tries **three** candidate paths. A `FieldEdit` must address
whichever one this body uses, or `apply_change_set` raises on a still-wrapped body that
`_find_chapters` handles today (§1.7). Replace `_find_chapters` with:

```python
_CHAPTER_PATHS = (("content", "chapters"), ("card", "content", "chapters"), ("chapters",))


def _chapters_path(body: dict) -> tuple:
    """The path at which THIS body's chapter list actually lives - the same three
    candidates, in the same order, that `_find_chapters` has always tried. `()` when
    there is no chapter list.

    A `FieldEdit.path` must be built from this, never from the confirmed
    ("content","chapters") path alone: `apply_change_set` refuses to create a missing
    intermediate container, so a hard-coded path would RAISE on exactly the
    un-unwrapped bodies the three-candidate fallback exists to tolerate."""
    for path in _CHAPTER_PATHS:
        node: object = body
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list):
            return path
    return ()


def _find_chapters(body: dict) -> list[dict]:
    """The chapter list inside a (unwrapped) GET /card body. Confirmed path first.

    ``client.get_card`` already unwraps the ``{"card": ...}`` envelope, so the
    confirmed path is ``content.chapters``. The ``card.content.chapters`` and
    bare ``chapters`` fallbacks stay so this survives an un-unwrapped body."""
    path = _chapters_path(body)
    node: object = body
    for key in path:
        node = node[key]
    return node if isinstance(node, list) else []


def _chapter_path(body: dict, ci: int) -> tuple:
    return _chapters_path(body) + (ci,)


def _track_path(body: dict, ci: int, ti: int) -> tuple:
    return _chapters_path(body) + (ci, "tracks", ti)
```

### Task 2.7 — `apply_change_set`

```python
def _assert_one_edit_per_path(edits: ChangeSet) -> None:
    """Two edits for one path would make the POST body depend on list order while the
    verify's expectation depended on it identically - so it would pass while writing
    something nobody declared twice over. Refuse instead."""
    seen: set = set()
    for e in edits:
        if e.path in seen:
            raise ValueError(f"change-set declares two edits for the same path: {e.path}")
        seen.add(e.path)


def _descend(node: object, step, so_far: tuple) -> object:
    """One step along a FieldEdit path. RAISES rather than creating a container."""
    if isinstance(node, dict):
        if not isinstance(step, str) or step not in node:
            raise ValueError(
                f"FieldEdit path {so_far} does not exist in the body; apply_change_set "
                "never creates an intermediate container (guessing a container shape is "
                "how a corrector silently writes the wrong thing into a live card)")
        return node[step]
    if isinstance(node, list):
        if not isinstance(step, int) or not 0 <= step < len(node):
            raise ValueError(f"FieldEdit path {so_far} is out of range for a list of {len(node)}")
        return node[step]
    raise ValueError(f"FieldEdit path {so_far} descends into a {type(node).__name__}")


def apply_change_set(body: dict, edits: ChangeSet) -> dict:
    """Return a NEW body (input untouched) with EXACTLY the declared paths set.

    Nothing else changes - not title/trackUrl/duration/fileSize/channels/keys/
    display/order, not the card-level metadata or media aggregates.

    A missing LEAF key is CREATED: that is the point, since `overlayLabel` is absent
    on every card this app has ever made (verified against all ten real GET bodies in
    %LOCALAPPDATA%\\YotoMaker\\repair-backups\\). A missing INTERMEDIATE container
    RAISES - see `_descend`.

    This is the single source of truth `verify_only_declared_changed` derives its
    expectation from, which is what closes the silent half of the old design: a
    declared write that Yoto DROPS shows up as `unexpectedly REMOVED` instead of
    passing as `applied`."""
    _assert_one_edit_per_path(edits)
    out = copy.deepcopy(body)
    for e in edits:
        if not e.path:
            raise ValueError("FieldEdit with an empty path")
        node: object = out
        for i, step in enumerate(e.path[:-1]):
            node = _descend(node, step, e.path[: i + 1])
        leaf = e.path[-1]
        if isinstance(node, dict):
            if not isinstance(leaf, str):
                raise ValueError(f"dict at {e.path[:-1]} addressed with non-str key {leaf!r}")
            node[leaf] = e.new
        elif isinstance(node, list):
            if not isinstance(leaf, int) or not 0 <= leaf < len(node):
                raise ValueError(f"list at {e.path[:-1]} has no index {leaf!r}")
            node[leaf] = e.new
        else:
            raise ValueError(f"cannot set {leaf!r} on a {type(node).__name__} at {e.path[:-1]}")
    return out
```

### Task 2.8 — `format_edits`, and `apply_format_corrections` as a thin wrapper

Keeping the wrapper is deliberate: it gives the existing format-only safety tests a
target, so commit 2 can be **proved** behaviour-neutral rather than argued to be.

```python
def format_edits(body: dict, correct_keys: set[str], fmt: str = CORRECT_FORMAT) -> ChangeSet:
    """The `format` intent as declared edits, for the tracks named in `correct_keys`
    (positional 'cid.tid', exactly as before)."""
    edits: ChangeSet = []
    for ci, chapter in enumerate(_find_chapters(body)):
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if isinstance(tr, dict) and f"{ci}.{ti}" in correct_keys:
                edits.append(FieldEdit(
                    path=_track_path(body, ci, ti) + ("format",),
                    old=tr.get("format", _ABSENT),
                    new=fmt,
                    intent="format",
                    reason=f"{tr.get('format') or '?'} -> {fmt}",
                ))
    return edits


def apply_format_corrections(body: dict, correct_keys: set[str], fmt: str = CORRECT_FORMAT) -> dict:
    """BACK-COMPAT WRAPPER, kept on purpose. `format` is now one intent on the
    declared change-set (ADR 2026-09-10 §3.1); this is the one-intent special case,
    and it stays so the format-only safety tests keep a target and commit 2 can be
    PROVED behaviour-neutral rather than argued to be."""
    return apply_change_set(body, format_edits(body, correct_keys, fmt))
```

### Task 2.9 — Re-derive the payload and the verify from the change-set

```python
def build_repair_payload(body: dict, edits: ChangeSet, canonical_urls: dict[str, str]) -> dict:
    """The NEW body to POST (input untouched): the declared change-set applied, PLUS
    the media-reference canonicalization - every `trackUrl` rewritten to its canonical
    `yoto:#<sha>` and every `display.icon16x16` (chapter- AND track-level) to its
    `yoto:#<mediaId>`, because POST /content rejects a resolved form of either.

    THE CANONICALIZATION IS DELIBERATELY NOT IN THE CHANGE-SET, and folding it in
    would break the verify (ADR 2026-09-10 §3.1's stated boundary). The verify
    neutralises media refs on BOTH sides via `_normalize_url`, because the re-GET
    returns a freshly RESOLVED URL and not the canonical ref we posted. Declaring
    canonicalization as edits would make `intended` canonical while `after` is
    resolved, and the existing normalize-then-compare would have to be undone."""
    out = apply_change_set(body, edits)
    for ci, chapter in enumerate(_find_chapters(out)):
        if isinstance(chapter, dict):
            _canonicalize_display_icon(chapter.get("display"))       # chapter-level icon
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if not isinstance(tr, dict):
                continue
            _canonicalize_display_icon(tr.get("display"))            # track-level icon
            canon = canonical_urls.get(f"{ci}.{ti}")
            if canon is not None:
                tr["trackUrl"] = canon
    return out


def verify_only_declared_changed(before: dict, after: dict, edits: ChangeSet) -> list[str]:
    """Return UNEXPECTED differences between `after` (the re-GET) and the intended
    result (`before` + the DECLARED change-set). [] == verified.

    Renamed from `verify_only_format_changed`: the guarantee is no longer
    format-shaped, and leaving the old name on a function that tolerates a second
    intent would be the most misleading identifier in the file.

    Unchanged: the re-GET re-resolves every `trackUrl` to a fresh pre-signed URL (new
    signature, new `<policy>~` prefix), so media refs are compared by their extracted
    sha / mediaId and never by the raw string; volatile server fields (`updatedAt`,
    `content.version`) are ignored on both sides; everything else must be identical.

    What the change-set buys, and it is a net SAFETY GAIN over format-only:

      * A DECLARED addition is already in `intended`, so `_diff_paths`' `k not in a`
        branch (:465) does not fire on it - no `_VOLATILE_TOP_KEYS` widening, which
        would have blinded the verify to the very field it exists to control.
      * An UNDECLARED addition still fires. The guarantee stays field-level.
      * ⚠ A declared write that Yoto SILENTLY DROPS now fires `unexpectedly REMOVED`
        (:467) -> `verify-failed`. Under format-only that case reported `applied` and
        the fix had not landed. Given that POST /content demonstrably enriches and
        derives (it adds 16 keys we never send - ADR §1.4), this is the branch most
        likely to fire in the field."""
    intended = _strip_volatile(apply_change_set(before, edits))
    got = _strip_volatile(after)
    return _diff_paths(intended, got)
```

### Task 2.10 — Update the three in-tree callers and the two test breaks

- `repair.py:641` → `build_repair_payload(body, plan.change_set, plan.canonical_urls)`.
  Until commit 3 adds `change_set`, use `format_edits(body, plan.correct_keys)` so
  commit 2 stands alone and green.
- `repair.py:656` → `verify_only_declared_changed(body, after, <the same edits>)`.
  **Compute the edit list once** and pass the identical object to both the payload
  build and the verify — that single shared value *is* the invariant; deriving it twice
  reintroduces exactly the hand-kept agreement this refactor removes.
- `tests/test_repair.py:29` — import `verify_only_declared_changed`, and add
  `format_edits` (§1.7).
- `tests/test_repair.py:758` — `build_repair_payload(inner, format_edits(inner, {"0.0"}), {"0.0": canon})`.

### Task 2.11 — Commit 2's own tests

Add to `tests/test_repair.py`:

```python
def test_apply_change_set_creates_a_missing_leaf_and_touches_nothing_else():
    before = _card("C1", ("mp3", "mp3"))
    expected = copy.deepcopy(before)
    expected["content"]["chapters"][0]["tracks"][0]["overlayLabel"] = "1"
    edits = [FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                       _ABSENT, "1", "overlay-label", "absent -> '1'")]
    out = apply_change_set(before, edits)
    assert out == expected
    assert "overlayLabel" not in before["content"]["chapters"][0]["tracks"][0]  # input untouched


def test_apply_change_set_refuses_to_create_an_intermediate_container():
    """Guessing a container shape is how a corrector silently writes the wrong thing
    into a live card. A path whose parent is absent is a PLANNING bug and must raise."""
    with pytest.raises(ValueError, match="does not exist"):
        apply_change_set({"content": {"chapters": []}},
                         [FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                                    _ABSENT, "1", "overlay-label", "x")])


def test_apply_change_set_refuses_two_edits_for_one_path():
    path = ("content", "chapters", 0, "tracks", 0, "format")
    with pytest.raises(ValueError, match="two edits"):
        apply_change_set(_card("C1", ("mp3",)), [
            FieldEdit(path, "mp3", "opus", "format", "a"),
            FieldEdit(path, "mp3", "aac", "format", "b"),
        ])


def test_change_set_addresses_a_still_wrapped_body_at_its_real_path():
    """`_find_chapters` tolerates three shapes; an edit must address the one this body
    actually uses, or apply_change_set raises on a body the walker handles fine."""
    wrapped = {"card": {"content": {"chapters": [{"tracks": [{"format": "mp3"}]}]}}}
    out = apply_change_set(wrapped, format_edits(wrapped, {"0.0"}))
    assert out["card"]["content"]["chapters"][0]["tracks"][0]["format"] == "opus"


def test_verify_catches_a_declared_write_the_server_silently_dropped(tmp_path):
    """⚠ THE branch this whole refactor exists for, and the one ADR §1.4 says is most
    likely in the field. Under format-only this case reported `applied` while the fix
    had NOT landed - the silent half of blocker 2. It must now be LOUD."""
    after = _card("C1", ("opus", "opus"))        # server kept format, dropped the label
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)
    before = copy.deepcopy(fake._body)
    edits = format_edits(before, {"0.0", "1.0"}) + [
        FieldEdit(("content", "chapters", 0, "tracks", 0, "overlayLabel"),
                  _ABSENT, "1", "overlay-label", "absent -> '1'")]
    problems = verify_only_declared_changed(before, after, edits)
    assert any("overlayLabel" in p and "REMOVED" in p for p in problems)


def test_verify_still_catches_an_undeclared_addition():
    """The `k not in a` branch must stay armed for fields we did NOT declare -
    otherwise the change-set would have bought narrowness by giving up coverage."""
    before = _card("C1", ("mp3",))
    after = copy.deepcopy(before)
    after["content"]["chapters"][0]["tracks"][0]["format"] = "opus"
    after["content"]["chapters"][0]["tracks"][0]["somethingYotoInvented"] = "x"
    problems = verify_only_declared_changed(before, after, format_edits(before, {"0.0"}))
    assert any("somethingYotoInvented" in p and "ADDED" in p for p in problems)
```

**Gate for commit 2 — the one that matters:** the whole suite green, and **every
pre-existing `tests/test_repair.py` safety test passing in a form no weaker than
before.** `test_corrector_sets_only_format_everything_else_byte_identical` (`:247`)
must pass **unmodified**, via the `apply_format_corrections` wrapper. If it cannot,
**stop and ask** (§2.7) — that is the signal the refactor changed behaviour.

---

## COMMIT 3 — the `overlay-label` intent

### Task 3.1 — `_is_set` and `overlay_label_edits`

```python
def _is_set(value: object) -> bool:
    """An `overlayLabel` we must leave alone: a non-empty string. Absent, None, "" and
    "   " all mean the field needs writing."""
    return isinstance(value, str) and value.strip() != ""


def overlay_label_edits(body: dict) -> tuple[ChangeSet, dict[str, list[str]]]:
    """The `overlay-label` intent: declare the missing `overlayLabel` at chapter AND
    track level, keyed on POSITION.

    Returns `(edits, notes)` where `notes` maps a positional key - "c{ci}" for a
    chapter, "{ci}.{ti}" for a track - to this intent's per-object notes.

    IDEMPOTENT BY CONSTRUCTION, with no "was this card labelled?" bookkeeping:

      1. The expected value is a pure function of POSITION, through the one shared
         helper `models.overlay_label`. Run 2 computes the same value, finds it
         equal, declares zero edits, and `outcome` is "already" - so no POST.
      2. ⚠ The value is NEVER derived from the card's own `key` field. `key` is "01"
         and the label is "1"; a path that read `key` and a path that computed from
         the index would disagree, and two runs could flip-flop forever.
      3. An existing NON-EMPTY `overlayLabel` is never overwritten - reported
         `already` and left alone. That is not only idempotency: it stops this tool
         flip-flopping against ANOTHER editor. A user who sets "Chapter 1" in the
         Yoto app would otherwise have it reset to "1" on every run, forever. It
         also means our edit is always absent-or-empty -> value, never a clobber,
         which is what keeps both the verify and the rollback story simple.

    MULTI-TRACK CHAPTERS ARE DECLINED, NOT GUESSED - and BOTH levels are declined.
    All three live cards are 1 chapter : 1 track (5x1, 18x1, 1x1 - read from the real
    bodies) and `build_content_payload` emits one track per chapter by construction,
    so this never fires on a card this app made. For a hand-assembled card we have
    ZERO evidence for the within-chapter numbering convention, and this path mutates
    live data. Declining the CHAPTER label too (not just the tracks) is deliberate:
    writing it alone would leave the schema-REQUIRED track field missing while making
    a later run's idempotency check see a labelled chapter and skip - a partial job
    that permanently hides itself. The `format` intent proceeds unaffected, which is
    the entire reason `declined` is not `blocked`: an unprobeable artifact is a
    correctness hazard and must stop the card; a label we cannot confidently number
    is not, and must never cost a card the PROVEN format fix."""
    from .models import overlay_label

    edits: ChangeSet = []
    notes: dict[str, list[str]] = {}
    for ci, chapter in enumerate(_find_chapters(body)):
        if not isinstance(chapter, dict):
            continue
        tracks = [t for t in (chapter.get("tracks") or []) if isinstance(t, dict)]
        if len(tracks) > 1:
            note = (f"chapter has {len(tracks)} tracks; overlayLabel numbering "
                    "convention unknown - skipped")
            notes.setdefault(f"c{ci}", []).append(f"declined: {note}")
            for ti in range(len(tracks)):
                notes.setdefault(f"{ci}.{ti}", []).append(f"declined: {note}")
            continue

        expected = overlay_label(ci + 1)
        if _is_set(chapter.get("overlayLabel")):
            notes.setdefault(f"c{ci}", []).append(
                f"already: chapter overlayLabel {chapter['overlayLabel']!r} - left alone")
        else:
            edits.append(FieldEdit(
                path=_chapter_path(body, ci) + ("overlayLabel",),
                old=chapter.get("overlayLabel", _ABSENT),
                new=expected,
                intent="overlay-label",
                reason=f"chapter overlayLabel absent -> {expected!r}"))
            notes.setdefault(f"c{ci}", []).append(f"planned: chapter overlayLabel -> {expected!r}")

        for ti, tr in enumerate(tracks):
            if _is_set(tr.get("overlayLabel")):
                notes.setdefault(f"{ci}.{ti}", []).append(
                    f"already: overlayLabel {tr['overlayLabel']!r} - left alone")
                continue
            edits.append(FieldEdit(
                path=_track_path(body, ci, ti) + ("overlayLabel",),
                old=tr.get("overlayLabel", _ABSENT),
                new=expected,
                intent="overlay-label",
                reason=f"overlayLabel absent -> {expected!r}"))
            notes.setdefault(f"{ci}.{ti}", []).append(f"planned: overlayLabel -> {expected!r}")
    return edits, notes
```

### Task 3.2 — Reshape `TrackDecision` / `CardPlan`; retire `correct_keys`

Replace `repair.py:504-538` per ADR §3.2. `blocked_reason` replaces the `"blocked"`
status; `notes` carries one line per intent.

```python
@dataclass
class TrackDecision:
    ref: TrackRef
    edits: ChangeSet = field(default_factory=list)   # 0, 1 or 2 declared writes for THIS track
    blocked_reason: str | None = None                # card-fatal (all-or-nothing) when set
    notes: list[str] = field(default_factory=list)   # one per intent: already / planned / declined


@dataclass
class CardPlan:
    card_id: str
    title: str
    decisions: list[TrackDecision]
    canonical_urls: dict[str, str] = field(default_factory=dict)
    card_edits: ChangeSet = field(default_factory=list)       # chapter-level writes
    card_problems: list[str] = field(default_factory=list)
    card_notes: list[str] = field(default_factory=list)

    @property
    def change_set(self) -> ChangeSet:
        """The ONE list from which both the POST body and the verify's expectation are
        derived. `CardPlan.correct_keys` is RETIRED (ADR §3.2): a card can now need a
        write with no format corrections at all, so any surviving `correct_keys`
        caller would be a latent 'writes nothing' bug - which is exactly blocker 1."""
        return [e for d in self.decisions for e in d.edits] + self.card_edits

    @property
    def blocked(self) -> list[TrackDecision]:
        return [d for d in self.decisions if d.blocked_reason]

    @property
    def tracks_changed(self) -> int:
        return sum(1 for d in self.decisions if d.edits)

    @property
    def outcome(self) -> str:
        # Blocked FIRST, so a card-level blocker is reported even on a card the
        # walker found no tracks on - otherwise it reads as "empty" and its reason
        # goes unprinted.
        if self.blocked or self.card_problems:   # all-or-nothing: ANY blocker skips the card
            return "blocked"
        if not self.decisions:
            return "empty"
        if self.change_set:                      # <-- the SECOND DECISION AXIS lives here
            return "apply"
        return "already"                         # every declared intent already satisfied
```

⚠ **`already` changes meaning** — from *every track is `opus`* to *every declared
intent is already satisfied*. The outcome **vocabulary** is unchanged (`already | empty
| dry-run | applied | blocked | verify-failed | write-uncertain | restored`), so
`main`'s exit-code logic at `:832` and the summary map need no new branch.

### Task 3.3 — Wire both intents into `plan_card`, behind the flag

This function holds the all-or-nothing gate, so it is given in full rather than as a
diff. **The canonicalize-then-probe logic is unchanged** — what changes is only how a
decision is *recorded* (`blocked_reason`/`notes`/`edits` instead of `status`/`reason`)
and the label intent merged in afterwards. Replace `repair.py:541-586` with:

```python
def plan_card(client, body: dict, card_id: str, *, overlay_labels: bool = True) -> CardPlan:
    """Diagnose one card against every declared intent and decide what to write.

    Canonicalization runs FIRST and blocks the whole card (all-or-nothing) if ANY
    track's resolved trackUrl can't be reduced to a validated `yoto:#<sha>` ref - we
    must never re-POST an expiring signed URL, and we never guess a sha. Probing
    remains the ONLY place we decide a track is Opus; we never infer it from the
    declared value.

    TWO INTENTS, and only ONE of them can block (ADR 2026-09-10 §3.2):
      * `format`        - already / planned / BLOCKED. An unprobeable or non-Opus
                          artifact is a correctness hazard and must stop the card.
      * `overlay-label` - already / planned / DECLINED, and it NEVER blocks. A label
                          we cannot confidently number is not a correctness hazard,
                          and it must never cost a card the PROVEN format fix. That
                          inversion is the whole reason `declined` exists.
    """
    decisions: list[TrackDecision] = []
    canonical: dict[str, str] = {}
    for ref in iter_tracks(body):
        # 1) Canonicalize the trackUrl we'd POST back. A failure blocks the card.
        canon, err = canonical_track_url(ref.track_url_raw)
        if err:
            decisions.append(TrackDecision(ref, blocked_reason=err))
            continue
        if canon is None and ref.artifact_url and ref.artifact_url.startswith("http"):
            # A resolved (expiring) artifact URL exists but is not on the rewritable
            # top-level `trackUrl` field - refuse rather than re-POST it verbatim.
            decisions.append(TrackDecision(
                ref, blocked_reason="resolved artifact URL is not on the top-level "
                                    "trackUrl field; cannot canonicalize it safely"))
            continue
        if canon is not None:
            canonical[ref.key] = canon

        # 2) The `format` intent. Decision logic byte-for-byte as before; only the
        #    recording shape changed.
        if ref.declared_format == CORRECT_FORMAT:
            decisions.append(TrackDecision(ref, notes=[f"already: '{CORRECT_FORMAT}'"]))
            continue
        if not ref.artifact_url:
            decisions.append(TrackDecision(
                ref, blocked_reason="no resolvable artifact URL on the card"))
            continue
        probe = client.probe_artifact(ref.artifact_url)
        if not probe.is_opus:
            decisions.append(TrackDecision(
                ref, blocked_reason=f"artifact not confirmed Opus: {probe.detail}"))
            continue
        decisions.append(TrackDecision(ref, edits=[FieldEdit(
            path=_track_path(body, ref.cid, ref.tid) + ("format",),
            old=ref.declared_format if ref.declared_format is not None else _ABSENT,
            new=CORRECT_FORMAT,
            intent="format",
            reason=f"{ref.declared_format or '?'} -> {CORRECT_FORMAT} ({probe.detail})",
        )], notes=[f"planned: {ref.declared_format or '?'} -> {CORRECT_FORMAT} "
                   f"({probe.detail}); trackUrl -> {canon}"]))

    # 3) The `overlay-label` intent, off the SAME positional walk. Never blocks.
    card_edits: ChangeSet = []
    card_notes: list[str] = []
    if overlay_labels:
        label_edits, label_notes = overlay_label_edits(body)
        by_key = {d.ref.key: d for d in decisions}
        # Track-level label edits attach to their own TrackDecision so the CLI report
        # groups by track; chapter-level ones are card_edits.
        for e in label_edits:
            key = _key_of_track_path(e.path)       # None for a chapter-level path
            if key is None:
                card_edits.append(e)
            elif key in by_key and not by_key[key].blocked_reason:
                by_key[key].edits.append(e)
            # else: a BLOCKED (or unwalked) track - drop the edit. The card will not
            # be written at all (all-or-nothing), and carrying it would both
            # misreport the intent and smuggle a track write into card_edits.
        for key, notes in label_notes.items():
            if key in by_key:
                by_key[key].notes.extend(notes)
            else:
                card_notes.extend(f"chapter {key[1:]}: {n}" for n in notes)

    # 4) Card-level guard: POST /content requires canonical yoto:#<mediaId> icons. Any
    #    icon whose 43-char mediaId can't be extracted/validated blocks the whole card.
    card_problems = icon_problems(body)
    return CardPlan(card_id=card_id, title=str(_card_title(body) or card_id),
                    decisions=decisions, canonical_urls=canonical,
                    card_edits=card_edits, card_problems=card_problems,
                    card_notes=card_notes)
```

Thread the flag through `repair_card`, and collapse Task 2.10's temporary
`format_edits(...)` call into the plan's own single list — **this is the line where the
invariant actually lands**, so compute it once and pass the *same object* to both:

```python
def repair_card(client, card_id: str, *, apply: bool, backup_dir: Path,
                now: datetime | None = None, overlay_labels: bool = True) -> CardResult:
    body = client.get_card(card_id)
    plan = plan_card(client, body, card_id, overlay_labels=overlay_labels)
    ...
    edits = plan.change_set          # ONE list: the POST body and the verify's
    corrected = build_repair_payload(body, edits, plan.canonical_urls)
    ...
    problems = verify_only_declared_changed(body, after, edits)   # expectation BOTH
```

Add the small path decoder beside `_track_path`:

```python
def _key_of_track_path(path: tuple) -> str | None:
    """The positional 'cid.tid' key a track-level FieldEdit path addresses, or None
    for a chapter-level one. Paths are built by `_track_path` / `_chapter_path`, so
    the tail is ("tracks", ti, <field>) exactly when it is track-level."""
    if len(path) >= 4 and path[-3] == "tracks" and isinstance(path[-2], int):
        return f"{path[-4]}.{path[-2]}"
    return None
```

**Also update `tests/test_repair_cli_output.py`** (Task 1.1) for the reshaped
`TrackDecision` — `TrackDecision(ref, notes=["already: 'opus'"])`.

### Task 3.4 — `--no-overlay-labels`

ADR §8 lever 1. It ships **with** the intent, not later: it is the in-code backout.

```python
    parser.add_argument("--no-overlay-labels", action="store_true",
                        help="Do not write the missing overlayLabel; correct only the "
                             "declared format. The label fix is the unproven half "
                             "(issue #31) - this is how it backs out without a revert.")
```

Thread it through: `repair_card(..., overlay_labels=not args.no_overlay_labels)` →
`plan_card(..., overlay_labels=overlay_labels)`. Default **off** (labels **on**), so
the tool's default is the intended behaviour and the lever is explicit.

### Task 3.5 — The three report strings, and the per-track marks

The existing strings at `:746-751` become **self-contradicting**, not merely stale: a
card whose format is already right but whose labels are missing would print *"already
correct (all 18 tracks 'opus')"* **and then write.**

```python
        "already": f"already correct ({n} track(s), nothing to change) - nothing to do",
        "dry-run": (f"WOULD make {len(res.plan.change_set)} change(s) across "
                    f"{res.plan.tracks_changed} track(s) - re-run with --apply to write"),
        "applied": f"made {len(res.plan.change_set)} change(s); POST ok; verify ok",
```

The per-track line (`:743-745`) now prints the notes, and `mark` comes from the
decision's own state:

```python
    for d in res.plan.decisions:
        mark = "x" if d.blocked_reason else (">" if d.edits else "=")
        detail = d.blocked_reason or "; ".join(d.notes) or "nothing to change"
        print(f'  [{mark}] track {d.ref.key} "{d.ref.title}": {detail}')
    for note in res.plan.card_notes:
        print(f"  [-] {note}")
```

**Pin them with a test — and assert on what the new string CONTAINS.** ⚠ Not
`"opus" not in msg`: `SESSION_STATE.md:175-178` and item 20's row record a guard that
asserted `"100 MB" not in msg`, then a ruling **deleted that number**, so the guard went
**vacuous and still passed**. Same file, same trap, same shape.

```python
def test_report_strings_describe_changes_not_formats(tmp_path, capsys):
    """⚠ Assert on what the new strings CONTAIN, never on what they lack. A negative
    guard goes vacuous the moment the thing it negates is deleted, and still passes -
    item 20's `"100 MB" not in msg` did exactly that (SESSION_STATE.md:175-178).

    `already` here means EVERY DECLARED INTENT is satisfied, not "every track is
    opus". A card that is already opus but unlabelled must NOT print `already`."""
    labelled = _card("C1", ("opus", "opus"), overlay_labels=True)
    res = repair_card(FakeClient(labelled), "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "already"
    _print_card_result(res)
    out = capsys.readouterr().out
    assert "already correct (2 track(s), nothing to change)" in out

    unlabelled = _card("C1", ("opus", "opus"), overlay_labels=False)
    res = repair_card(FakeClient(unlabelled), "C1", apply=False, backup_dir=tmp_path / "b")
    assert res.outcome == "dry-run"
    _print_card_result(res)
    out = capsys.readouterr().out
    assert "WOULD make 4 change(s) across 2 track(s)" in out   # 2 chapter + 2 track labels
```

### Task 3.6 — The rollback tolerance

`rollback_from_backup` (`:661-679`). **Every backup written before this change — all ten
on disk — contains no `overlayLabel`, so restoring one POSTs a body without the field,
and that is correct and deliberate**: a backup is the verbatim pre-write state, and
`overlayLabel` was absent before our write. A rollback that preserved an unproven field
we had just added would not be a rollback.

But if `POST /content` **merges** rather than **replaces**, `after` still carries the
label, the backup does not, and `_diff_paths` at `:676` emits `unexpectedly ADDED` →
the restore reports `verify-failed` **on a card that is in fact fine**, turning a
recovery action into a false alarm at the worst possible moment.

```python
_OVERLAY_RESIDUE = (
    "the card still carries overlayLabel; Yoto's POST /content does not delete keys "
    "omitted from the body. Everything else is restored.")


def _tolerate_overlay_residue(problems: list[str]) -> tuple[list[str], bool]:
    """Re-report a RESIDUAL `overlayLabel` after a restore as explanation, not failure.

    ⚠ THIS IS NOT THE `_VOLATILE_TOP_KEYS` TRAP, and the difference is structural:
    it lives ONLY in the rollback path and never in `verify_only_declared_changed`;
    it is scoped to ONE field; it tolerates only residual PRESENCE and never a
    changed VALUE; and it changes a REPORT LINE, not the diff the repair path acts
    on. `_VOLATILE_TOP_KEYS` would have blinded the verify to the field in BOTH
    bodies, including a value Yoto changed on its own. Do not cite this as a
    precedent for widening that tuple (ADR §1.3, §4.2.1).

    The cost, stated: a restore can no longer distinguish OUR residual label from a
    label Yoto wrote itself. Accepted, because `canonicalize_body_media_refs`
    already establishes that a restore never blocks - a restore is a recovery action,
    and a rollback that cries wolf is worse than one that under-reports a field the
    operator is deliberately abandoning.

    DO NOT "fix" this by posting `overlayLabel: null` to clear it. Track-level
    `overlayLabel` is `z.string()`, not `.nullable()` - a null would fail validation
    and take the whole restore down with it. `overlayLabelOverride` is the nullable
    one, and we never write it.
    """
    kept, tolerated = [], False
    for p in problems:
        if "/overlayLabel:" in p and "unexpectedly ADDED" in p:
            tolerated = True
            kept.append(f"{p.split(':')[0]}: {_OVERLAY_RESIDUE}")
        else:
            kept.append(p)
    return kept, tolerated
```

In `rollback_from_backup`, after `:676`:

```python
    problems = _diff_paths(_strip_volatile(body), _strip_volatile(after))
    problems, tolerated = _tolerate_overlay_residue(problems)
    real = [p for p in problems if _OVERLAY_RESIDUE not in p]
    outcome = "restored" if not real else "verify-failed"
```

and `main`'s rollback return at `:789` must use the same rule, or a tolerated residue
would still set exit code 1: `return 0 if outcome == "restored" else 1`.

Tests: a restore whose `after` retains `overlayLabel` reports **`restored`** with the
explanatory line; a restore whose `after` has a **changed** `overlayLabel` **value**
still reports `verify-failed`.

### Task 3.7 — The record amendments

All of these land **in this PR**, per ADR §7 — the format-only clause is true of the
code shipped today, so amending the record ahead of the code would make it wrong in
the other direction.

1. **`repair.py:11`** — in the module docstring's safety list, replace the
   `FORMAT-ONLY correction (...)` line with ADR §7(b)'s `DECLARED-CHANGE-SET
   correction:` paragraph, **verbatim**.
2. **`docs/architecture/decisions/2026-07-21-repair-existing-cards.md`** — append ADR
   §7(a)'s *"Addendum 2 — 2026-09-10: format is no longer the only field written"*
   verbatim at the end of the file (after `:558`). **And correct its Status line
   (`:4`)** from `proposed — needs Mark's approval before Planner picks it up` to
   `accepted — shipped as PR #20 (2026-07-22); amended 2026-09-10 by
   2026-09-10-overlay-labels-and-the-declared-change-set.md` (ADR open question 6;
   the maintainer folded it into this arc).
3. **`docs/BUILDER_QUEUE.md:468`** — item 18 is shipped; **annotate, do not replace.**
   Apply ADR §7(c)'s exact substitution for *"`format` is the only field ever
   written."*
4. **`docs/architecture/README.md`** Index — the ADR's own row and the 2026-07-21 row
   both still say `proposed`. Set the 2026-07-21 row to `accepted (shipped as PR #20;
   amended 2026-09-10)` — deleting the *"status line is stale"* parenthetical, which
   is no longer true — and the 2026-09-10 row to `accepted`.
5. **`docs/DESIGN.md:94`** — in the `**Upload:**` bullet, change
   `(chapters/tracks referencing \`yoto:#<sha>\`, per-track \`display.icon16x16\`)` to
   `(chapters/tracks referencing \`yoto:#<sha>\`, per-track \`display.icon16x16\`, and
   \`overlayLabel\` at both levels — the label the player's knob browses)`.
6. **The ADR itself** — the §1 corrections. See §4 below; they are listed separately
   because the maintainer may prefer them in the planning PR.

### Task 3.8 — v0.1.14

Per §2.6. Bump `pyproject.toml:7` and `yoto_maker/__init__.py:3` to `0.1.14`. Rewrite
`docs/RELEASE_NOTES.md`'s H1 and sections for v0.1.14.

⚠ **Write the release note honestly.** The knob hypothesis is ~75–80% and **no physical
player has confirmed it.** The mom-facing note must describe what the app now *sends*,
not a behaviour nobody has observed — e.g. *"New cards now carry the chapter numbers
Yoto's own player software expects"* — **not** *"twisting the knob now brings up your
chapter list."* `SESSION_STATE.md:254-255`'s rule applies with full force: a card that
plays in the phone app is not evidence of anything.

### Task 3.9 — Close item 29

Mark ✅ with the PR link, add the Shipped row, and record the test count. The row moves
to 🚢 only when `gh release view v0.1.14` returns a release with an uploaded `.exe`
asset — paste that output into the row (queue `:440-448`).

---

## 3. Test Plan

### 3.A Automated — Builder runs, and these are the gates

| # | Command | Expect |
| --- | --- | --- |
| A1 | `cd D:/prj/yoto-maker && python -m pytest -q` | green at every commit boundary, never only at the end |
| A2 | `python -m pytest tests/test_repair.py -q` | every pre-existing safety test passes; `:247` passes **unmodified** |
| A3 | `python -m pytest tests/test_repair_cli_output.py -q` | all new; **must fail before Task 1.2** |
| A4 | `python -m pytest tests/test_models_and_settings.py tests/test_yoto_client.py -q` | green; `:25` and `:159` still pass **and** now assert labels |

**A5 — the round-trip agreement test** (ADR §4.1, required). Build a card with
`build_content_payload` for **N = 12** tracks (N > 9, so a padding difference is
visible), feed the result to `plan_card`, assert **zero** `overlay-label` edits are
declared. This is an equality test, not a value test: it catches an off-by-one in
*either* direction and a structural disagreement (repair reading the wrong nesting
level) that two literal value assertions would both miss.

**A6 — idempotency, two halves.** Run `repair_card` twice against a `FakeClient` whose
`get_card` returns the posted body: the second run declares zero edits,
`outcome == "already"`, and `len(fake.posts) == 1`. Separately: a chapter with a
pre-existing `overlayLabel` of `"Chapter 1"` is **never** overwritten — assert the
posted body still reads `"Chapter 1"`.

**A7 — blocker 1's regression guard.** Split `test_idempotent_already_opus_no_post`
(`:296`) in two, as ADR §4.1 requires: all-`opus` **with** labels → `already`, **no**
POST; all-`opus` **without** labels → `apply` and **exactly one** POST. The second is
the test that proves the silent-no-op is gone.

**A8 — `declined` keeps the proven fix available.** A card with one multi-track chapter
and a correctable `format`: the label intent declines **both** levels of that chapter,
the format edit is still declared, the card is **not** blocked, and the POST happens.

**A9 — the `_card()` helper gains `overlay_labels: bool = True`** (ADR §4.1). Both
states are now fixtures. `test_verify_passes_when_only_format_changed` (`:336`) breaks
until the helper produces labels on the `after` body — re-express it, do not weaken it.

**A10 — a labelled sibling fixture.** `tests/fixtures/card_sample.json` is a real
**unlabelled** body, which makes it the right fixture for the `apply` case; it needs a
labelled **sibling**, not a modification. Keep `:145`'s test pointed at the original.

**A11 — `--no-overlay-labels`.** With the flag, an unlabelled all-`opus` card reports
`already` and issues **no** POST; without it, the same card reports `apply`.

### 3.B Tester — executable without hardware

All of these are CLI runs on the maintainer's box. **Every one is read-only unless the
step says `--apply`.**

| # | Step | Pass |
| --- | --- | --- |
| B1 | After item 28: `python -m yoto_maker.repair --card-id 1WCvI --dry-run` **with no `PYTHONUTF8`**, stdout **piped** (`\| cat`) | Completes, exit 0. Prints five track lines. The 🤖 appears as `\U0001f916`. **No traceback.** This is issue #31's exact reproduction |
| B2 | Same, **with** `PYTHONUTF8=1` | Identical, except the 🤖 renders as `🤖` |
| B3 | `python -m yoto_maker.repair --list` piped | Every card title prints; no crash on any non-ASCII title |
| B4 | `python -m yoto_maker.repair --title "wild"` piped | The ambiguous-title message prints both candidates, exit 2, **no crash** |
| B5 | After item 29: `--card-id gzP2B,1WCvI,7FcVe --dry-run` | All three now report `WOULD make N change(s) across K track(s)` — **not** `already correct`. `gzP2B` N=2/K=1; `1WCvI` N=10/K=5; `7FcVe` N=36/K=18 |
| B6 | Same with `--no-overlay-labels` | All three report `already correct (N track(s), nothing to change) - nothing to do`. **This is the before/after proof that the second decision axis is what unblocks them** |
| B7 | Create a new 2-track card in the app, save to a folder, inspect nothing — then run the unit suite's A5 | Create path and repair path agree |
| B8 | **Staged rollout, step 1:** `--card-id gzP2B --apply` | `RESULT: made 2 change(s); POST ok; verify ok`. A backup is written and its path printed. **If this is anything other than `applied`, STOP and ask** (§2.7) |
| B9 | Immediately re-run B8 without `--apply` | `already correct … nothing to do`. Idempotency confirmed on live data |
| B10 | **ADR open question 3, settled here for free:** immediately `--rollback <the backup from B8>` | `restored` → `POST /content` **replaces**. `verify-failed` naming `overlayLabel` → it **merges**, and Task 3.6's tolerance is what keeps that from reading as a failure. **Record which.** Then re-apply B8 |
| B11 | `--card-id 1WCvI --apply`, then `--card-id 7FcVe --apply` | `applied` each; only after B8 and the hardware check below |

### 3.C ⚠ Verifiable **only** on physical hardware — and nobody on this project has a player

> ✅ **RUN ON HARDWARE 2026-09-11 — C1 PASSED. C3 WAS NOT RUN.** The maintainer's daughter
> tested on the physical player: **twisting the right-hand knob brings up the chapter list,
> and pressing it selects a chapter.** So **C1 is answered YES** and ADR open question 2 is
> closed. ⚠ **C3 — the offline download — was NOT exercised and is still the open question**;
> it was always separate from C1 and nothing was watched with wi-fi off. **C4 is partially
> informed**: the unpadded form rendered and worked, but the two forms were not compared.
> **C2 and C5 were not reported on.** The section below is left exactly as written, because it
> is the test design that produced the answer.

**The entire hypothesis is unfalsifiable in this repo.** `overlayLabel` gating the
knob-browse UI is **inference from a required field plus an official example** — no
Yoto document says it, and Yoto's own description says *"used in the app"*, not *the
player*. ~75–80% (ADR §1.2, §4.2.2).

Who can close it: **the maintainer's daughter**, whose household has the player
(`SESSION_STATE.md:215-255`). She can run the whole loop herself.

| # | Only hardware can answer | How |
| --- | --- | --- |
| C1 | **Does twisting the right-hand knob bring up a chapter list?** | On repaired `1WCvI` (5 real chapters). **`gzP2B` is useless for this** — 1 chapter, and it would show nothing under any hypothesis |
| C2 | Does the card still play, in order, with the right icons? | Play it through |
| C3 | **Does the offline download complete?** | Wifi off, watch the download-cloud icon. ⚠ **This is the question that matters.** Streaming in the phone app will likely work even on a malformed card — *a card that plays in the app is NOT evidence of a fix* |
| C4 | Does Yoto render `"1"` or would `"01"` have looked better? | Look at the screen (ADR open question 4). Reversible in one line of `overlay_label`; gates nothing |
| C5 | Did anything regress — playback, icons, ordering, a download that previously worked? | Compare against before. **This is the only branch where rollback is urgent** — lever 2 immediately, per card, then 1 and 3 |

⚠ **The Wild Robot confound is still live** (`SESSION_STATE.md:247-249`): do **not**
test `1WCvI` against a second Wild Robot card made by the save-to-folder path. Two Wild
Robot cards make the result unattributable. Use a different title for one of them.

**The decision rule, so nobody re-derives it under pressure** (ADR §8):

- **Chapter list appears →** confirmed. Keep everything; close issue #31.
- **Still nothing, card otherwise healthy →** falsified. **Lever 1** (`--no-overlay-labels`)
  immediately and **lever 3** (revert commit 1). **Lever 2 is optional and probably
  unnecessary** — a schema-required field with a correct value is not a defect, and
  removing it re-introduces the schema violation. Leave the three cards labelled,
  record the negative in the ADR, and re-open with `playbackType` and the two confirmed
  dead ends already eliminated. **Never revert commit 2 to back out commit 3.**
- **Anything regressed →** **lever 2 immediately, per card**, then 1 and 3.

---

## 4. ADR edits this plan requires — drafted, **not yet applied**

I have **not** edited the ADR. §1's findings falsify parts of its own analysis, and
rewriting an approved document's reasoning is the maintainer's call, not Planner's.
Seven edits, in descending order of how misleading they are today:

| # | ADR location | Why | Land in |
| --- | --- | --- | --- |
| 1 | **`:20-24`, the opening ⚠ box** | Says no write ever landed and the feature may be inert. **The most-read text in the file and it is false.** Replace with §1.1's finding | **planning PR** |
| 2 | **§1.1 entirely** (`:30-82`) | Both readings dead. Keep the backup table, recaption it as *pre-write snapshots*, and add §1.1's mechanism + the `edc3c6d` timeline | **planning PR** |
| 3 | **Open question 1** (`:702-707`) | Closed. Record the verbatim output, the date, and that it was run twice (maintainer, then Planner) | **planning PR** |
| 4 | **§4.2.3** (`:626-630`) | *"commit 3 must not be built"* is now unreachable. Rewrite as *settled: Yoto persists client-supplied track fields* | **planning PR** |
| 5 | **§1.3 blocker 1's ⚠** (`:128-131`) | Inverts the truth: blocker 1 bites on all three cards **today**. §1.2 | **planning PR** |
| 6 | **§4.1's** *"only exact-equality assertion"* | False as written; the precise version is a **stronger** argument. §1.4. Also add the three omissions in §1.7 to the breaks-by-design table | **planning PR** |
| 7 | **§3.6 / §3.7's** *"No version bump"* | Right about `__ASSET_V__`, wrong about the release. §2.6. Also §3.7 says "three commits"; the arc is **four** | **planning PR** |

Two more, smaller: ADR `:77`'s command should note `PYTHONUTF8=1` became optional at
item 28 (Task 1.5); and §7(d) claims the `architecture/README.md` row is *"Done with
this ADR"* — the row exists, but it and the 2026-07-21 row both still read `proposed`
(Task 3.7 item 4).

**Open question 3** (replace vs merge) stays open and is answered for free by B10.
**Open question 2** stays open and only hardware closes it. **Open question 5**
(`overlayLabelOverride`) stands declined.

---

## 5. Success criteria

1. `python -m yoto_maker.repair --card-id 1WCvI --dry-run` completes with **no**
   `PYTHONUTF8`, on a **piped** stdout. (Item 28.)
2. A test executes `_print_card_result` and `main` — for the first time in the
   project's life — under a **forced** cp1252 stream, so it fails on Linux CI too.
3. `build_content_payload` emits `overlayLabel` at chapter **and** track level,
   unpadded, 1-based, and an **absolute** equality test pins one full chapter and its
   full track, with a comment saying why it exists.
4. A test pins the POST body's **top-level** `content` keys.
5. `apply_format_corrections`' existing safety test (`:247`) passes **unmodified**
   through the wrapper — commit 2 proved behaviour-neutral, not argued to be.
6. A declared write that the server drops produces `verify-failed` with
   `unexpectedly REMOVED`. An **undeclared** addition still produces
   `unexpectedly ADDED`.
7. `_VOLATILE_TOP_KEYS` has **exactly** its five pre-existing entries.
8. An all-`opus` but unlabelled card reports `apply` and POSTs **once**; the same card
   with `--no-overlay-labels` reports `already` and POSTs **nothing**.
9. A second run writes nothing. A pre-existing non-empty `overlayLabel` is never
   overwritten.
10. A multi-track chapter declines **both** label levels, does **not** block the card,
    and the format fix still applies.
11. The create path and the repair path agree for N = 12 by round-trip, not by two
    literal assertions.
12. The report strings name **changes**, asserted by what they **contain**.
13. All three live cards move from `already correct` to `WOULD make N change(s)`, and
    back to `already correct` under `--no-overlay-labels`.
14. v0.1.14 is tagged with an `.exe` asset, and the release note claims **only** what
    the app now sends — never a knob behaviour nobody has observed.
15. Every §3.7 record amendment landed; both `architecture/README.md` rows read
    `accepted`.
16. The whole suite green. Baseline 401.

---

## 6. Deviations, judgement calls, and what stays open

- **Two queue rows, not one.** Commit 0 is a different kind of work with an
  open-ended investigation behind it, and it **gates a live write**. Separating it means
  the arc is not hostage to archaeology and the crash fix can be verified on its own.
  Commits 1–3 stay in one PR as three ordered stacks, following item 13's discipline.
- **`errors=` only, never `encoding=`.** The minimal change that cannot make any
  working output worse. Pinned by a test so it is not "improved" later.
- **`client.py`'s non-ASCII copy is left alone** even though it reaches the repair
  console. The `errors=` guard makes it safe, and the family is item 26's open
  ownership question. Do not open a second one (ADR §4.2.5).
- **`declined` declines both label levels** — ADR §3.4 did not say; §1.8 argues it.
- **`FieldEdit.old` is informational and unchecked** — documented in the dataclass so
  nobody later assumes it is a guard.
- **Still open, and neither is this plan's to close:** whether `overlayLabel` gates the
  knob UI (hardware only, §3.C) and whether `POST /content` replaces or merges (B10
  answers it for free during the rollout; the tolerance ships either way).
