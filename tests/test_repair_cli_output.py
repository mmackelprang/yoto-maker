"""The repair CLI's console output layer — executed here for the first time.

WHY THIS FILE EXISTS. `tests/test_repair.py` has 47 tests and imports 13 names from
`yoto_maker.yoto.repair`; neither `_print_card_result` nor `main` is among them, and
nothing in `tests/` captures stdout at all. So the layer that reports whether a live
write landed had no coverage, and `tests/fixtures/card_sample.json` is 100% ASCII, so
even a capture test against it would not have exercised a non-ASCII title.

Issue #31's report: `python -m yoto_maker.repair --card-id 1WCvI --dry-run` raises
UnicodeEncodeError at `_print_card_result`, because Wild Robot's five track titles
each carry U+1F916 ROBOT FACE and they arrive from Yoto's JSON (`repair.py:317`).
In APPLY mode that print happens at `main`'s `:881`, AFTER `repair_card` POSTed at
`:648` - so the operator is left unable to tell whether the write landed.

⚠ LINE CITATIONS IN THIS FILE POINT AT `repair.py` AFTER the guard was inserted.
Adding `_make_console_safe` pushed everything inside `main` down by 50 lines, and the
first draft of this file shipped the pre-insertion numbers - two of which landed
inside the very docstring that had invalidated them. If you move code in `main`,
re-check every `:NNN` here. The emit sites themselves (`:740`, `:742`, `:745`, `:760`,
`:762`) sit above the insertion point and did not move.
"""
from __future__ import annotations

import ast
import inspect
import io
import textwrap
from pathlib import Path

import pytest

from yoto_maker.yoto import repair as repair_mod
from yoto_maker.yoto.client import CardSummary, YotoError
from yoto_maker.yoto.repair import CardPlan, CardResult, TrackDecision, TrackRef

ROBOT = "\U0001f916"          # U+1F916; encodable in NO single-byte Windows codepage
TITLE = f"The Wild Robot {ROBOT} By Peter Brown (part 1)"
ROBOT_UTF8 = ROBOT.encode("utf-8")          # what `encoding="utf-8"` would emit


def _cp1252_stdout() -> io.TextIOWrapper:
    """A real text stream whose codec cannot encode U+1F916.

    `errors="strict"` is FORCED, and deliberately stricter than reality: a fresh
    interpreter gives a redirected stdout `surrogateescape`, not `strict`. Strict is
    what makes the unencodable character raise here rather than depend on the host,
    so this test fails on a UTF-8 machine and on Linux CI too. (U+1F916 raises under
    `surrogateescape` as well - verified - so the reproduction is genuine either way.)
    """
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                            write_through=True)


def _force_cp1252_streams(monkeypatch):
    """Force BOTH streams, and return them.

    stderr is forced too because the guard covers it and nothing else in this file
    would notice if that half were deleted. On a real process that half is a no-op:
    CPython forces `errors="backslashreplace"` on `sys.stderr` and ignores even
    `PYTHONIOENCODING=cp1252:strict` (both measured). So a forced-strict stream is the
    ONLY way to pin it, and before this helper existed
    `for stream in (sys.stdout,):` passed every test in the file.
    """
    out, err = _cp1252_stdout(), _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", err)
    return out, err


def _read(stream) -> tuple[bytes, str]:
    """The raw bytes AND the cp1252 decoding.

    Both, because `.decode("cp1252")` can never yield U+1F916 - no cp1252 byte maps
    above U+2122 - so asserting `ROBOT not in decoded` is unfalsifiable. Assert on the
    BYTES for what must not be there; the decoded form is for reading the text.
    """
    raw = stream.buffer.getvalue()
    return raw, raw.decode("cp1252")


def _result(outcome="already", *, title=TITLE, card_title="Wild Robot", problems=(),
            backup_path=None):
    ref = TrackRef(cid=0, tid=0, key="0.0", title=title,
                   declared_format="opus", artifact_url="https://x/a")
    # `TrackDecision` was reshaped by the declared-change-set refactor: the single
    # `status`/`reason` pair became `edits` / `blocked_reason` / `notes`.
    decision = TrackDecision(ref, notes=["already: 'opus'"])
    plan = CardPlan(card_id="1WCvI", title=card_title, decisions=[decision])
    return CardResult("1WCvI", card_title, outcome, plan, backup_path, list(problems))


def test_print_card_result_survives_a_track_title_the_console_cannot_encode(monkeypatch):
    """THE issue #31 crash. Must not raise, and must not silently print nothing.

    `card_title` carries the ROBOT too, so this one test covers BOTH title emit
    sites: `res.title` at `repair.py:740` and `d.ref.title` at `:745`. The plan's
    Task 1.3 table says `:740` folds in here; its Task 1.1 snippet left the card
    title ASCII, which would have left `:740` unexercised by any test in the file.
    """
    out, _ = _force_cp1252_streams(monkeypatch)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(card_title=f"Wild Robot {ROBOT}"))

    raw, written = _read(out)
    assert "already: 'opus'" in written         # the line was really emitted
    assert "Wild Robot" in written
    assert ROBOT_UTF8 not in raw                # not smuggled through as utf-8 bytes
    assert "\\U0001f916" in written             # escaped losslessly, not dropped to '?'


def test_the_backup_path_line_survives_a_username_the_console_cannot_encode(monkeypatch):
    """`repair.py:742` - `print(f"  backup: {res.backup_path}")`.

    The backup path is built from `get_config().data_dir`, i.e. it contains the
    Windows account name, which is outside this project's control entirely. This
    line is the one an operator needs MOST after a failed apply: it is the only
    place the rollback argument is printed.
    """
    out, _ = _force_cp1252_streams(monkeypatch)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(backup_path=Path(f"C:/Users/{ROBOT}/b.json")))

    raw, written = _read(out)
    assert "backup: " in written
    assert "b.json" in written                  # the whole path survived, not a prefix
    assert ROBOT_UTF8 not in raw
    assert "\\U0001f916" in written


def test_a_problem_string_built_by_repr_survives(monkeypatch):
    """`repair.py:762` - THE WIDEST HOLE. `res.problems` is built by `_diff_paths`
    as `f"{path}: {a!r} -> {b!r}"` over ARBITRARY card field values, so any string
    Yoto ever puts in any field reaches this print.

    The canary below is the point of the test: Python 3's `repr()` does NOT escape
    printable non-ASCII, so `!r` is no protection whatsoever. If that ever changes,
    this test says so instead of quietly stopping to exercise the hole.
    """
    assert ROBOT in repr(TITLE), "repr() now escapes non-ASCII; this row is moot"

    out, _ = _force_cp1252_streams(monkeypatch)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(problems=[f"/title: 'a' -> {TITLE!r}"]))

    raw, written = _read(out)
    assert "! /title: 'a' ->" in written
    assert ROBOT_UTF8 not in raw
    assert "\\U0001f916" in written


# --------------------------------------------------------------------------- #
# The `main`-driving rows. `main` calls `_make_console_safe()` itself, so these
# also prove the call is wired up and not merely present.
#
# `setup_logging` (`repair.py:830`) and `YotoClient` (`:831`) are monkeypatched, so
# nothing here touches the network or the real log file. `_backup_dir` (`:876`) is
# NOT patched and does not need to be: `tests/conftest.py`'s autouse `temp_config`
# fixture already points `get_config().data_dir` at a tmp_path, so the real
# %LOCALAPPDATA%\YotoMaker\repair-backups tree is unreachable from any test.
# --------------------------------------------------------------------------- #
class _FakeClient:
    """The whole surface `main` touches before it reaches a card."""

    def __init__(self, summaries=()):
        self._summaries = list(summaries)

    def is_connected(self) -> bool:
        return True

    def list_my_cards(self) -> list:
        return list(self._summaries)


def _drive_main(monkeypatch, argv, *, summaries=(), repair_card=None):
    """Run `main(argv)` against forced cp1252 streams and no real Yoto or logging.
    Returns (exit_code, raw stdout bytes, decoded stdout)."""
    out, _ = _force_cp1252_streams(monkeypatch)
    monkeypatch.setattr(repair_mod, "setup_logging", lambda *a, **k: None)
    monkeypatch.setattr(repair_mod, "YotoClient", lambda *a, **k: _FakeClient(summaries))
    if repair_card is not None:
        monkeypatch.setattr(repair_mod, "repair_card", repair_card)
    code = repair_mod.main(argv)
    raw, written = _read(out)
    return code, raw, written


def test_list_survives_a_card_title_the_console_cannot_encode(monkeypatch):
    """`repair.py:843` - `--list` prints `s.title` straight from GET /content/mine.

    `--list` is the command the CLI's own error at `:716` tells the operator to run
    ("Try --list, or pass --card-id"), so a crash here is a dead end: the recovery
    path for one failure would be the second failure.
    """
    code, raw, written = _drive_main(
        monkeypatch, ["--list"],
        summaries=[CardSummary("1WCvI", f"Wild Robot {ROBOT}", created_at="2026-07-22")])

    assert code == 0
    assert "1WCvI" in written
    assert "(created 2026-07-22)" in written     # the whole line, not a truncation
    assert ROBOT_UTF8 not in raw
    assert "\\U0001f916" in written


def test_an_ambiguous_title_reports_every_candidate_without_crashing(monkeypatch):
    """`repair.py:854` - `print(str(exc))` for a `resolve_targets` failure. The
    ambiguous-title raise at `:723` interpolates EVERY candidate's `m.title`, so one
    unencodable card in the account breaks disambiguation for all of them.

    This is a refuse-to-guess path - the CLI will never auto-pick a card to mutate -
    so the message IS the entire remedy. Crashing instead of printing it leaves the
    operator with two cards, no card ids, and no way forward.
    """
    code, raw, written = _drive_main(
        monkeypatch, ["--title", "wild robot"],
        summaries=[CardSummary("1WCvI", f"Wild Robot {ROBOT} (part 1)", track_count=5),
                   CardSummary("7FcVe", f"Wild Robot {ROBOT} (part 2)", track_count=18)])

    assert code == 2
    assert "matched 2 cards" in written
    assert "1WCvI" in written and "7FcVe" in written     # both candidates, not one
    assert ROBOT_UTF8 not in raw
    assert written.count("\\U0001f916") == 2            # escaped per candidate


def test_a_yoto_error_from_repair_card_does_not_crash_the_error_line(monkeypatch):
    """`repair.py:878` - `print(f"{card_id}: ERROR - {exc}")`. A `YotoError`'s text
    is `_friendly_http`'s prose (`client.py:587-590`, `:594-597`), which carries
    U+2019 and U+2014.

    ⚠ THE PLAN'S ROW FOR THIS SITE IS NOT SELF-SUFFICIENT, and this test is written
    to say so rather than to pass vacuously. The message it proposes - "Yoto
    wouldn't take that - too big." with U+2019 and U+2014 - CANNOT crash a cp1252
    console: both characters are in cp1252 (0x92 and 0x97), which is §1.5's own
    point about why `516cbf7` was fixing a different problem. A test raising only
    that would pass identically with the guard deleted.

    So the message carries the card title as well, and the assertions pin BOTH
    halves, which is strictly more than the row asked for:

      * the typography survives as REAL GLYPHS - evidence that `errors=` did not
        damage output that already worked, i.e. the OEM-console mojibake that
        `encoding="utf-8"` would have risked. Confirmed against the live account,
        where `Julie<U+2019>s Library` emits U+2019 as cp1252 0x92;
      * the emoji survives as an ESCAPE rather than an exception.

    Do NOT edit `client.py` to fix this. The guard makes that copy safe without
    touching it, and its ownership is item 26's open question (plan §1.9).
    """
    def _boom(*a, **k):
        raise YotoError(f"Yoto wouldn\u2019t take that \u2014 it was too big: {TITLE}")

    code, raw, written = _drive_main(monkeypatch, ["--card-id", "1WCvI"],
                                     repair_card=_boom)

    assert code == 1
    assert "1WCvI: ERROR - " in written
    assert "wouldn\u2019t take that \u2014 it was too big" in written   # glyphs, not escapes
    assert ROBOT_UTF8 not in raw
    assert "\\U0001f916" in written


def test_stderr_is_guarded_too_so_argparse_can_report_an_unencodable_argument(monkeypatch):
    """Pins the `sys.stderr` half of the guard - the half nothing else here can see.

    argparse writes `unrecognized arguments: ...` to STDERR from `parse_args` at
    `repair.py:878`, interpolating the offending argument verbatim. Before this test
    existed, changing the guard to `for stream in (sys.stdout,):` left all of the
    above green, because `_cp1252_stdout()` was only ever bound to `sys.stdout`.

    On a real process this half is a no-op - CPython forces
    `errors="backslashreplace"` on `sys.stderr` and ignores even
    `PYTHONIOENCODING=cp1252:strict`, both measured - so it is defence-in-depth for a
    stream someone else replaced. Untested defence-in-depth is how the stdout half got
    into this state in the first place, so it is pinned rather than trusted.
    """
    _, err = _force_cp1252_streams(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        repair_mod.main(["--card-id", "1WCvI", ROBOT])

    assert exc.value.code == 2
    raw = err.buffer.getvalue()
    written = raw.decode("cp1252")
    assert "unrecognized arguments" in written
    assert ROBOT_UTF8 not in raw
    assert "\\U0001f916" in written


# --------------------------------------------------------------------------- #
# Source-level pins. `tests/test_static_cache.py:114-127` is this repo's own
# precedent for pairing a behavioural encoding test with a source assertion.
# --------------------------------------------------------------------------- #
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


def test_the_guard_covers_both_streams():
    """The `sys.stderr` half is load-bearing only on a stream someone else replaced,
    so it is the half most likely to be "simplified" away by someone who measures it
    on a real process and finds it changes nothing. The behavioural pin above is the
    real guard; this one names the reason at the source level so the diff is obvious.
    """
    src = inspect.getsource(repair_mod._make_console_safe)
    assert "for stream in (sys.stdout, sys.stderr):" in src
