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


# --------------------------------------------------------------------------- #
# Task 4 — "What to do next.html"
# --------------------------------------------------------------------------- #
from yoto_maker.export import sheet as sheet_mod


def _sheet(files, failures=(), picture=None, split=(), version="0.1.13"):
    return sheet_mod.SheetData(
        card_name="Bedtime Stories",
        files=list(files),
        failures=list(failures),
        advisories=rules.advise(list(files)),
        split=list(split),
        picture_png=picture,
        has_card_picture_file=picture is not None,
        version=version,
        date_label="5 September 2026",
    )


def test_the_sheet_lists_her_actual_files_in_order():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3"), _f(2, "02 - B.mp3")]))
    assert html_out.index("01 - A.mp3") < html_out.index("02 - B.mp3")
    assert "Bedtime Stories" in html_out


def test_the_sheet_is_self_contained():
    """No external request, ever. DESIGN.md §8 — the app makes none anywhere."""
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")], picture=b"\x89PNG-fake"))
    assert "<script" not in html_out.lower()
    assert "<link" not in html_out.lower()
    assert "data:image/png;base64," in html_out
    # The ONLY absolute URL on the page is the one she is meant to click.
    # Asserted as "no plain http:// at all, and every https:// is that one",
    # not as a count comparison across both schemes: "http://" is not a
    # substring of "https://", so the plan's loop compared 0 against 1.
    assert "http://" not in html_out
    assert html_out.count("https://") == html_out.count("https://my.yotoplay.com") == 1


def test_step_6_is_always_present():
    """Omitting it leaves a correct upload and a card that does nothing."""
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "6. Put it on a card" in html_out
    assert "tap a blank" in html_out


def test_the_picture_step_is_omitted_entirely_when_there_is_no_picture():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "Card picture.png" not in html_out
    assert "4. Add the picture" not in html_out


def test_a_partial_run_names_the_missing_track_and_counts_only_what_landed():
    files = [_f(1, "01 - A.mp3"), _f(2, "02 - B.mp3")]
    html_out = sheet_mod.render_sheet(_sheet(files, failures=["Chapter Four"]))
    assert "isn’t here" in html_out
    assert "Chapter Four" in html_out
    assert "2 tracks" in html_out
    # "above the card name" (copy.md §6.8) means above the visible <h2>, not
    # above the <title> — that is document metadata and is always first.
    assert html_out.index("isn’t here") < html_out.index("<h2>Bedtime Stories</h2>")


def test_titles_are_escaped():
    files = [rules.SavedFile(index=1, name="01 - x.mp3", title="<b>x</b>",
                             size_bytes=1, duration_s=1, converted=False)]
    data = _sheet(files)
    data.card_name = "<script>alert(1)</script>"
    html_out = sheet_mod.render_sheet(data)
    assert "<script>alert(1)" not in html_out
    assert "&lt;script&gt;" in html_out


def test_the_size_bullet_is_always_shown_even_for_a_small_card():
    html_out = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "100 MB and an hour" in html_out
    assert "500 MB, five hours and 100 tracks" in html_out


def test_the_sheet_split_line_has_a_singular_and_a_plural(tmp_path):
    """copy.md §6.4, amended 2026-09-05. The plan emitted only the singular.

    Neither variant names a title or a count: every part is printed with its own
    number in the file list immediately below.
    """
    one = sheet_mod.render_sheet(
        _sheet([_f(1, "01 - A.mp3")], split=[rules.SplitGroup(title="Ch One", parts=2)])
    )
    assert "One of your tracks was too long for a Yoto card, so it’s in more" in one
    assert "Some of your tracks" not in one

    many = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")], split=[
        rules.SplitGroup(title="Ch One", parts=2),
        rules.SplitGroup(title="Ch Two", parts=3),
    ]))
    assert "Some of your tracks were too long for a Yoto card, so they’re each" in many
    assert "One of your tracks was too long" not in many
    # No titles, no counts, in either variant.
    for out in (one, many):
        assert "Ch One" not in out
        assert "Ch Two" not in out


# --------------------------------------------------------------------------- #
# Task 5 — the orchestration
# --------------------------------------------------------------------------- #
from yoto_maker.export import runner as runner_mod
from yoto_maker.export.errors import ExportError


def _track(path, title, dur=2.0, icon=None):
    return runner_mod.ExportTrack(title=title, audio_path=Path(path),
                                  icon_path=icon, duration_s=dur)


def test_a_saved_folder_holds_exactly_the_deliverables(tmp_path, sample_mp3):
    root = tmp_path / "saved"
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One"), _track(sample_mp3, "Chapter Two")],
        card_name="Bedtime Stories", picture_path=None, root=root,
        scratch_dir=tmp_path / "scratch", version="0.1.13",
    )
    names_on_disk = sorted(p.name for p in res.folder.iterdir())
    assert names_on_disk == ["01 - Chapter One.mp3", "02 - Chapter Two.mp3",
                            "What to do next.html"]
    assert res.folder == root / "Bedtime Stories"


def test_pressing_save_twice_never_overwrites(tmp_path, sample_mp3):
    root = tmp_path / "saved"
    kwargs = dict(tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
                  picture_path=None, root=root, scratch_dir=tmp_path / "s",
                  version="0.1.13")
    first = runner_mod.export_card(**kwargs)
    second = runner_mod.export_card(**kwargs)
    assert first.folder.name == "Bedtime Stories"
    assert second.folder.name == "Bedtime Stories (2)"
    assert first.folder.exists()


def test_a_mixed_card_copies_mp3_and_m4a_and_converts_flac(tmp_path, sample_mp3):
    """Acceptance criterion 11. The .m4a staying put is the specific thing to check."""
    from yoto_maker.tools import find_ffmpeg
    import subprocess

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        pytest.skip("ffmpeg not available")
    incoming = tmp_path / "in"
    incoming.mkdir()
    m4a = incoming / "sea.m4a"
    flac = incoming / "rain.flac"
    for out in (m4a, flac):
        subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=1", str(out)],
                       capture_output=True, check=True)

    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Song"), _track(m4a, "The Sea"), _track(flac, "Rain")],
        card_name="Mixed", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    written = [f.name for f in res.files]
    assert written == ["01 - Song.mp3", "02 - The Sea.m4a", "03 - Rain.mp3"]
    assert [f.converted for f in res.files] == [False, False, True]


def test_conversion_uses_192k(tmp_path, sample_mp3, monkeypatch):
    seen = {}
    real = runner_mod.normalize_to_mp3

    def spy(src, out_dir, *, bitrate="192k", **kw):
        seen["bitrate"] = bitrate
        return real(src, out_dir, bitrate=bitrate, **kw)

    monkeypatch.setattr(runner_mod, "normalize_to_mp3", spy)
    wav = tmp_path / "in.wav"
    wav.write_bytes(sample_mp3.read_bytes())      # extension drives the decision
    try:
        runner_mod.export_card(
            tracks=[_track(wav, "A")], card_name="C", picture_path=None,
            root=tmp_path / "saved", scratch_dir=tmp_path / "s", version="0.1.13",
        )
    except ExportError:
        pass                                       # ffmpeg may reject the fake wav
    assert seen["bitrate"] == "192k"


def test_a_partial_run_keeps_the_rest_and_the_sheet_tells_the_truth(tmp_path, sample_mp3):
    """Acceptance criterion 5."""
    missing = tmp_path / "in" / "gone.mp3"
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One"), _track(missing, "Chapter Four")],
        card_name="Bedtime Stories", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    assert [f.name for f in res.files] == ["01 - Chapter One.mp3"]
    assert [f.title for f in res.failures] == ["Chapter Four"]
    page = (res.folder / "What to do next.html").read_text(encoding="utf-8")
    assert "Chapter Four" in page              # named in the notice
    assert "02 - Chapter Four" not in page     # NOT in the file list
    assert "1 track" in page


def test_a_total_failure_leaves_no_folder_behind(tmp_path):
    """Acceptance criterion 9, and the reason copy.md §5.7's last line is true."""
    root = tmp_path / "saved"
    with pytest.raises(ExportError):
        runner_mod.export_card(
            tracks=[_track(tmp_path / "nope.mp3", "A")], card_name="Bedtime Stories",
            picture_path=None, root=root, scratch_dir=tmp_path / "s", version="0.1.13",
        )
    assert not (root / "Bedtime Stories").exists()


def test_every_track_failing_names_them_all_rather_than_guessing_one_cause(tmp_path):
    """copy.md §5.7's fourth {reason} row, added 2026-09-05.

    The plan raised ExportError(failures[0].reason), which reports one cause as
    if it were the only one. §5.7 reuses §5.6's numbered list instead.
    """
    root = tmp_path / "saved"
    with pytest.raises(ExportError) as exc:
        runner_mod.export_card(
            tracks=[_track(tmp_path / "gone-a.mp3", "Chapter One"),
                    _track(tmp_path / "gone-b.mp3", "Chapter Two")],
            card_name="Bedtime Stories", picture_path=None, root=root,
            scratch_dir=tmp_path / "s", version="0.1.13",
        )
    lines = str(exc.value).split("\n")
    assert lines[0] == "None of your 2 tracks could be saved:"
    assert lines[1].startswith("1. “Chapter One” — ")
    assert lines[2].startswith("2. “Chapter Two” — ")
    assert not (root / "Bedtime Stories").exists()


def test_track_pictures_go_in_a_subfolder_named_to_match(tmp_path, sample_mp3):
    icon = tmp_path / "icon.png"
    from PIL import Image
    Image.new("RGB", (16, 16), "purple").save(icon)
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One", icon=icon)],
        card_name="Bedtime Stories", picture_path=None, root=tmp_path / "saved",
        scratch_dir=tmp_path / "s", version="0.1.13",
    )
    assert (res.folder / "Track pictures" / "01 - Chapter One.png").exists()
    # The subfolder is the whole point: no loose 16x16 PNG beside the audio.
    assert not list(res.folder.glob("*.png"))


def test_the_result_view_carries_everything_the_panel_needs(tmp_path, sample_mp3):
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
        picture_path=None, root=tmp_path / "saved", scratch_dir=tmp_path / "s",
        version="0.1.13",
    )
    v = res.view()
    for key in ("folder_name", "folder_path", "saved_count", "total_count", "files",
                "failures", "split_groups", "converted", "oversize_tracks", "card_mb",
                "card_duration_words", "card_tracks", "over_card_bytes",
                "over_card_seconds", "over_card_tracks"):
        assert key in v
