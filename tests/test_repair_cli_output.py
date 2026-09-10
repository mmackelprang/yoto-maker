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
