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
from yoto_maker.yoto.client import CardSummary, YotoError
from yoto_maker.yoto.repair import CardPlan, CardResult, TrackDecision, TrackRef

ROBOT = "\U0001f916"          # U+1F916; encodable in NO single-byte Windows codepage
TITLE = f"The Wild Robot {ROBOT} By Peter Brown (part 1)"


def _cp1252_stdout() -> io.TextIOWrapper:
    """A real text stream whose codec cannot encode U+1F916, with the strict-ish
    error handler a fresh interpreter gives a redirected stdout. Forced rather
    than inherited so this test fails on a UTF-8 machine and on Linux CI too."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                            write_through=True)


def _result(outcome="already", *, title=TITLE, card_title="Wild Robot", problems=(),
            backup_path=None):
    ref = TrackRef(cid=0, tid=0, key="0.0", title=title,
                   declared_format="opus", artifact_url="https://x/a")
    decision = TrackDecision(ref, "already", "already 'opus'")
    plan = CardPlan(card_id="1WCvI", title=card_title, decisions=[decision])
    return CardResult("1WCvI", card_title, outcome, plan, backup_path, list(problems))


def test_print_card_result_survives_a_track_title_the_console_cannot_encode(monkeypatch):
    """THE issue #31 crash. Must not raise, and must not silently print nothing.

    `card_title` carries the ROBOT too, so this one test covers BOTH title emit
    sites: `res.title` at `repair.py:740` and `d.ref.title` at `:745`. The plan's
    Task 1.3 table says `:740` folds in here; its Task 1.1 snippet left the card
    title ASCII, which would have left `:740` unexercised by any test in the file.
    """
    stream = _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(card_title=f"Wild Robot {ROBOT}"))

    written = stream.buffer.getvalue().decode("cp1252")
    assert "already 'opus'" in written          # the line was really emitted
    assert "Wild Robot" in written
    assert ROBOT not in written                 # it could not be; it was escaped
    assert "\\U0001f916" in written             # losslessly, not dropped to '?'


def test_the_backup_path_line_survives_a_username_the_console_cannot_encode(monkeypatch):
    """`repair.py:742` - `print(f"  backup: {res.backup_path}")`.

    The backup path is built from `get_config().data_dir`, i.e. it contains the
    Windows account name, which is outside this project's control entirely. This
    line is the one an operator needs MOST after a failed apply: it is the only
    place the rollback argument is printed.
    """
    stream = _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(backup_path=Path(f"C:/Users/{ROBOT}/b.json")))

    written = stream.buffer.getvalue().decode("cp1252")
    assert "backup: " in written
    assert "b.json" in written                  # the whole path survived, not a prefix
    assert ROBOT not in written
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

    stream = _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    repair_mod._make_console_safe()
    repair_mod._print_card_result(_result(problems=[f"/title: 'a' -> {TITLE!r}"]))

    written = stream.buffer.getvalue().decode("cp1252")
    assert "! /title: 'a' ->" in written
    assert ROBOT not in written
    assert "\\U0001f916" in written


# --------------------------------------------------------------------------- #
# The `main`-driving rows. `main` calls `_make_console_safe()` itself, so these
# also prove the call is wired up and not merely present.
#
# `setup_logging` (:780), `YotoClient` (:781) and `_backup_dir` (:826, which calls
# `get_config`) are all monkeypatched, so no test here touches the network, the
# real log file, or the real %LOCALAPPDATA%\YotoMaker\repair-backups tree.
# --------------------------------------------------------------------------- #
class _FakeClient:
    """The whole surface `main` touches before it reaches a card."""

    def __init__(self, summaries=()):
        self._summaries = list(summaries)

    def is_connected(self) -> bool:
        return True

    def list_my_cards(self) -> list:
        return list(self._summaries)


def _drive_main(monkeypatch, argv, *, summaries=(), backup_dir=None, repair_card=None):
    """Run `main(argv)` against a forced cp1252 stdout and no real Yoto, logging or
    backup directory. Returns (exit_code, what was written, decoded)."""
    stream = _cp1252_stdout()
    monkeypatch.setattr("sys.stdout", stream)
    monkeypatch.setattr(repair_mod, "setup_logging", lambda *a, **k: None)
    monkeypatch.setattr(repair_mod, "YotoClient", lambda *a, **k: _FakeClient(summaries))
    monkeypatch.setattr(repair_mod, "_backup_dir", lambda: backup_dir)
    if repair_card is not None:
        monkeypatch.setattr(repair_mod, "repair_card", repair_card)
    code = repair_mod.main(argv)
    return code, stream.buffer.getvalue().decode("cp1252")


def test_list_survives_a_card_title_the_console_cannot_encode(monkeypatch):
    """`repair.py:793` - `--list` prints `s.title` straight from GET /content/mine.

    `--list` is the command the CLI's own error at :716 tells the operator to run
    ("Try --list, or pass --card-id"), so a crash here is a dead end: the recovery
    path for one failure would be the second failure.
    """
    code, written = _drive_main(
        monkeypatch, ["--list"],
        summaries=[CardSummary("1WCvI", f"Wild Robot {ROBOT}", created_at="2026-07-22")])

    assert code == 0
    assert "1WCvI" in written
    assert "(created 2026-07-22)" in written     # the whole line, not a truncation
    assert ROBOT not in written
    assert "\\U0001f916" in written


def test_an_ambiguous_title_reports_every_candidate_without_crashing(monkeypatch):
    """`repair.py:804` - `print(str(exc))` for a `resolve_targets` failure. The
    ambiguous-title raise at `:723` interpolates EVERY candidate's `m.title`, so one
    unencodable card in the account breaks disambiguation for all of them.

    This is a refuse-to-guess path - the CLI will never auto-pick a card to mutate -
    so the message IS the entire remedy. Crashing instead of printing it leaves the
    operator with two cards, no card ids, and no way forward.
    """
    code, written = _drive_main(
        monkeypatch, ["--title", "wild robot"],
        summaries=[CardSummary("1WCvI", f"Wild Robot {ROBOT} (part 1)", track_count=5),
                   CardSummary("7FcVe", f"Wild Robot {ROBOT} (part 2)", track_count=18)])

    assert code == 2
    assert "matched 2 cards" in written
    assert "1WCvI" in written and "7FcVe" in written     # both candidates, not one
    assert ROBOT not in written
    assert written.count("\\U0001f916") == 2            # escaped per candidate


def test_a_yoto_error_from_repair_card_does_not_crash_the_error_line(monkeypatch, tmp_path):
    """`repair.py:828` - `print(f"{card_id}: ERROR - {exc}")`. A `YotoError`'s text
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
        `encoding="utf-8"` would have risked;
      * the emoji survives as an ESCAPE rather than an exception.

    Do NOT edit `client.py` to fix this. The guard makes that copy safe without
    touching it, and its ownership is item 26's open question (plan §1.9).
    """
    def _boom(*a, **k):
        raise YotoError(f"Yoto wouldn\u2019t take that \u2014 it was too big: {TITLE}")

    code, written = _drive_main(monkeypatch, ["--card-id", "1WCvI"],
                                backup_dir=tmp_path, repair_card=_boom)

    assert code == 1
    assert "1WCvI: ERROR - " in written
    assert "wouldn\u2019t take that \u2014 it was too big" in written   # glyphs, not escapes
    assert ROBOT not in written
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
