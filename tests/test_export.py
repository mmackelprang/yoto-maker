"""Save-to-a-folder mode.

Design: docs/design-handoffs/export-only-mode/. Strings: that package's copy.md.
Every test here runs against tmp_path — conftest points Config.documents_dir at
a temp directory precisely so the suite never writes to a real Documents folder.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from yoto_maker.config import get_config, resolve_documents_dir


def test_saved_dir_hangs_off_documents_and_is_not_precreated(temp_config):
    cfg = get_config()
    assert cfg.saved_dir == cfg.documents_dir / "Yoto Maker"
    assert not cfg.saved_dir.exists(), "ensure_dirs() must not create it"


def test_documents_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("YOTO_DOCUMENTS_DIR", str(tmp_path / "Docs"))
    assert resolve_documents_dir() == tmp_path / "Docs"


def test_documents_resolution_never_raises(monkeypatch):
    monkeypatch.delenv("YOTO_DOCUMENTS_DIR", raising=False)
    assert isinstance(resolve_documents_dir(), Path)


# --------------------------------------------------------------------------- #
# Task 2 — the reason strings and the naming rules
# --------------------------------------------------------------------------- #
from datetime import date

from yoto_maker.export.errors import NameTooLongError
from yoto_maker.export import names


def test_sanitize_strips_windows_illegals_and_never_returns_empty():
    assert names.sanitize_component(r'a/b\c:d*e?f"g<h>i|j', fallback="X") == "abcdefghij"
    assert names.sanitize_component("   ", fallback="X") == "X"
    assert names.sanitize_component("Bedtime...", fallback="X") == "Bedtime"
    assert names.sanitize_component("CON", fallback="X") == "CON_"


def test_numbering_is_two_digits_and_widens_past_99():
    assert names.number_width(5) == 2
    assert names.number_width(99) == 2
    assert names.number_width(100) == 3
    assert names.number_width(101) == 3


def test_filename_sort_equals_play_order_including_split_parts(tmp_path):
    titles = ["Chapter One", "Chapter Eighteen (part 1)", "Chapter Eighteen (part 2)", "Zebra"]
    made = [
        names.track_filename(i, len(titles), t, ".mp3", folder=tmp_path)
        for i, t in enumerate(titles, start=1)
    ]
    assert sorted(made) == made


def test_a_long_title_is_truncated_never_dropped_and_the_number_survives(tmp_path):
    name = names.track_filename(7, 20, "T" * 400, ".mp3", folder=tmp_path)
    assert name.startswith("07 - ")
    assert name.endswith(".mp3")
    assert len(str(tmp_path / name)) <= names.MAX_PATH_CHARS


def test_two_titles_that_truncate_identically_still_differ(tmp_path):
    a = names.track_filename(1, 2, "T" * 400, ".mp3", folder=tmp_path)
    b = names.track_filename(2, 2, "T" * 400, ".mp3", folder=tmp_path)
    assert a != b


def test_an_impossible_path_raises_rather_than_writing_something_wrong(tmp_path):
    deep = tmp_path / ("d" * 240)
    with pytest.raises(NameTooLongError):
        names.track_filename(1, 1, "Chapter One", ".mp3", folder=deep)


def test_collisions_get_the_windows_convention_and_never_overwrite(tmp_path):
    (tmp_path / "Bedtime Stories").mkdir()
    assert names.unique_dir(tmp_path, "Bedtime Stories").name == "Bedtime Stories (2)"
    (tmp_path / "Bedtime Stories (2)").mkdir()
    assert names.unique_dir(tmp_path, "Bedtime Stories").name == "Bedtime Stories (3)"


def test_spoken_formats():
    assert names.duration_words(43 * 60) == "43 minutes"
    assert names.duration_words(3600) == "1 hour"
    assert names.duration_words(8 * 3600 + 40 * 60) == "8 hours 40 minutes"
    assert names.duration_words(0) == "0 minutes"
    assert names.megabytes(118_000_000) == 118
    assert names.date_words(date(2026, 9, 5)) == "5 September 2026"


# --------------------------------------------------------------------------- #
# Task 3 — what Yoto takes, and what the app does about it
# --------------------------------------------------------------------------- #
from yoto_maker.export import rules


def test_the_copy_as_is_set_is_exactly_the_three_documented_types():
    assert rules.COPY_AS_IS == {".mp3", ".m4a", ".aac"}


def test_bitrate_keeps_a_50_minute_track_under_the_100_mb_cap():
    """Acceptance criterion 12. 192 kbps * 3000 s = ~72 MB; ~265 kbps breaks it."""
    kbps = int(rules.EXPORT_BITRATE.rstrip("k"))
    assert kbps * 1000 / 8 * 3000 < rules.MAX_TRACK_BYTES


@pytest.mark.parametrize("ext", [".mp3", ".m4a", ".aac", ".MP3", ".M4A"])
def test_the_copy_as_is_set_is_never_converted(ext):
    assert rules.needs_conversion(Path(f"x{ext}")) is False
    assert rules.output_suffix(Path(f"x{ext}")) == ext.lower()


@pytest.mark.parametrize("ext", [".wav", ".flac", ".ogg", ".opus", ".mp4"])
def test_everything_else_becomes_an_mp3(ext):
    assert rules.needs_conversion(Path(f"x{ext}")) is True
    assert rules.output_suffix(Path(f"x{ext}")) == ".mp3"


def test_an_oversized_mp3_is_still_never_converted():
    """overview.md §8.6's asymmetry, stated as a test so nobody 'fixes' it.

    The app acts on format and advises on size. A 320 kbps 50-minute MP3 is
    ~120 MB and is copied untouched.
    """
    assert rules.needs_conversion(Path("huge.mp3")) is False


def _f(i, name, size=1, dur=1.0, conv=False, title=None):
    return rules.SavedFile(index=i, name=name, title=title or name, size_bytes=size,
                           duration_s=dur, converted=conv)


def test_advisories_measure_the_written_files_and_never_block():
    """oversize is SELECTIVE, the card ceiling is measured over all of them, and
    neither one blocks anything.

    The sizes matter: only the first file is over the 100 MB per-track cap, and
    the four under it are what carry the card past 500 MB. A single 400 MB
    companion would be over the per-track cap itself and would prove nothing
    about the selection.
    """
    files = [_f(1, "01 - A.mp3", size=118_000_000)]
    files += [_f(i, f"{i:02d} - B.mp3", size=99_000_000) for i in range(2, 6)]
    a = rules.advise(files)
    assert [f.name for f in a.oversize] == ["01 - A.mp3"]
    assert a.card_bytes == 514_000_000
    assert a.over_card_bytes is True
    assert a.over_card_tracks is False


def test_split_groups_report_only_real_multi_part_tracks():
    files = [
        _f(1, "01 - Ch One.mp3", title="Ch One"),
        _f(2, "02 - Ch Two (part 1).mp3", title="Ch Two (part 1)"),
        _f(3, "03 - Ch Two (part 2).mp3", title="Ch Two (part 2)"),
    ]
    groups = rules.split_groups(files)
    assert [(g.title, g.parts) for g in groups] == [("Ch Two", 2)]
