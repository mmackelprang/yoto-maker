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


def test_the_budget_covers_the_track_picture_which_sits_one_level_deeper(tmp_path):
    """The budget was measured against the audio path only.

    A track's picture is written to ``<folder>\\Track pictures\\<stem>.png`` — one
    segment and one separator further down, 15 characters — so a folder and title
    that produced a 255-character audio path produced a 270-character picture
    path. With Windows long paths disabled (the default) that write fails, the
    runner swallows it as a log warning, and the pictures vanish silently while
    the sheet says they are there.
    """
    folder = tmp_path / ("d" * 40)
    name = names.track_filename(7, 20, "T" * 400, ".mp3", folder=folder)
    picture = folder / names.TRACK_PICTURES_DIR / (Path(name).stem + ".png")

    assert len(str(folder / name)) <= names.MAX_PATH_CHARS
    assert len(str(picture)) <= names.MAX_PATH_CHARS
    # Not simply over-generous either: the title is truncated to exactly the room
    # the DEEPER of the two paths leaves, so the picture lands on the limit.
    assert len(str(picture)) == names.MAX_PATH_CHARS


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


def _sheet(files, failures=(), picture=None, split=(), version="0.1.13",
           track_pictures=False):
    return sheet_mod.SheetData(
        card_name="Bedtime Stories",
        files=list(files),
        failures=list(failures),
        advisories=rules.advise(list(files)),
        split=list(split),
        picture_png=picture,
        has_card_picture_file=picture is not None,
        has_track_pictures=track_pictures,
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


def test_the_sheet_names_the_track_pictures_folder_only_when_it_is_there():
    """overview.md §9.2: the sheet mentions them CONDITIONALLY.

    The paragraph was unconditional, while the runner skips the subfolder
    entirely when no track resolves an icon and when its mkdir fails — so the
    page told her to look for a folder that was not there.
    """
    present = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")], track_pictures=True))
    assert "The little pictures on the Yoto screen" in present
    assert "<strong>Track pictures</strong>" in present

    absent = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")]))
    assert "The little pictures on the Yoto screen" not in absent
    assert "Track pictures" not in absent
    # Step 6 is never conditional and must survive either branch.
    assert "6. Put it on a card" in absent


def test_the_plural_missing_track_notice_agrees_with_itself():
    """copy.md §6.8 gives the singular verbatim; the plural body it leaves
    unspecified. The closing clause was shared, so the plural read "…so they
    aren’t in this folder… If you want IT on the card…".
    """
    one = sheet_mod.render_sheet(_sheet([_f(1, "01 - A.mp3")], failures=["Chapter Four"]))
    assert "If you want it on the card, go back to Yoto Maker and try again." in one

    many = sheet_mod.render_sheet(
        _sheet([_f(1, "01 - A.mp3")], failures=["Chapter Four", "Chapter Five"])
    )
    assert "If you want them on the card, go back to Yoto Maker and try again." in many
    assert "If you want it on the card" not in many


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


def test_two_saves_of_one_card_name_both_succeed_and_get_their_own_folder(tmp_path, sample_mp3):
    """unique_dir() probes and then the runner creates — a gap two saves can sit
    in. The loser's mkdir() raised FileExistsError, which _os_reason maps to the
    generic "something went wrong", reporting a fault for a collision.

    Pressing save, reloading (which re-enables the button) and pressing save
    again is all it takes; two tabs do it too.
    """
    import threading

    root = tmp_path / "saved"
    results: list = []
    errors: list = []
    ready = threading.Barrier(2)

    def run(n: int) -> None:
        try:
            ready.wait(timeout=10)
            results.append(runner_mod.export_card(
                tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
                picture_path=None, root=root, scratch_dir=tmp_path / f"s{n}",
                version="0.1.13",
            ))
        except BaseException as exc:          # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(n,)) for n in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, errors
    assert len(results) == 2
    assert len({r.folder for r in results}) == 2, "one folder held both cards"
    assert all(r.folder.exists() for r in results)
    assert {r.folder.name for r in results} == {"Bedtime Stories", "Bedtime Stories (2)"}


def test_losing_the_race_for_a_folder_name_re_resolves_instead_of_failing(
    tmp_path, sample_mp3, monkeypatch
):
    """The race above, made deterministic: something else takes the resolved name
    between the probe and the create. Nothing is overwritten — the stolen folder
    is left exactly as it was found."""
    root = tmp_path / "saved"
    root.mkdir(parents=True)
    real = runner_mod.unique_dir
    stolen: list = []

    def steal(r, name):
        candidate = real(r, name)
        if not stolen:                        # only the first resolution loses
            stolen.append(candidate)
            candidate.mkdir()
            (candidate / "someone else's file.txt").write_text("x", encoding="utf-8")
        return candidate

    monkeypatch.setattr(runner_mod, "unique_dir", steal)
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
        picture_path=None, root=root, scratch_dir=tmp_path / "s", version="0.1.13",
    )
    assert stolen[0].name == "Bedtime Stories"
    assert res.folder.name == "Bedtime Stories (2)"
    assert (stolen[0] / "someone else's file.txt").exists(), "never overwrite"


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
    """192 kbps is what keeps a 50-minute track under Yoto's 100 MB cap, and this
    is the only test that names the figure.

    ``bitrate`` is a REQUIRED keyword on the spy, with no default. Given one it
    would have matched normalize_to_mp3's own ``"192k"`` default, so deleting
    ``bitrate=EXPORT_BITRATE`` from the runner left this test green — verified by
    removing that kwarg and watching this fail, then putting it back.
    """
    assert rules.EXPORT_BITRATE == "192k"
    seen = {}
    real = runner_mod.normalize_to_mp3

    def spy(src, out_dir, *, bitrate, **kw):
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
    assert seen["bitrate"] == rules.EXPORT_BITRATE == "192k"


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
    # …and the sheet says so, because it is there.
    page = (res.folder / "What to do next.html").read_text(encoding="utf-8")
    assert "Track pictures" in page


def test_the_sheet_never_claims_a_pictures_folder_that_was_not_written(tmp_path, sample_mp3):
    """spec §2.6 requirement 1: the sheet is generated from what actually landed.

    No track resolved an icon, so the runner writes no subfolder — and the page
    must not send her looking for one.
    """
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One")], card_name="Bedtime Stories",
        picture_path=None, root=tmp_path / "saved", scratch_dir=tmp_path / "s",
        version="0.1.13",
    )
    assert not (res.folder / "Track pictures").exists()
    page = (res.folder / "What to do next.html").read_text(encoding="utf-8")
    assert "Track pictures" not in page


def test_the_instruction_sheet_is_written_last(tmp_path, sample_mp3, monkeypatch):
    """overview.md §10.5a — this write order is a CONTRACT, not an accident.

    copy.md §5.10 is the string that makes it one. When the app loses contact
    with a running save it cannot say whether the save finished, so it gives her
    a test she can actually perform instead: *"If there's a page in it called
    'What to do next', the save finished — that page lists what's actually
    there."* That is only true because the sheet is written **after** every audio
    file and every picture.

    If a refactor ever moves the sheet earlier — for a preview, say — that
    paragraph becomes a lie in the worst direction: she finds a half-written
    folder with a sheet in it and concludes the save completed. Nothing else in
    the suite would notice, which is why this test exists.

    Asserted at the moment of the write rather than on mtimes, which are too
    coarse on Windows to order two writes a few milliseconds apart.
    """
    from PIL import Image

    root = tmp_path / "saved"
    folder = root / "Bedtime Stories"
    picture = tmp_path / "cover.png"
    Image.new("RGB", (64, 64), "teal").save(picture)
    icon = tmp_path / "icon.png"
    Image.new("RGB", (16, 16), "purple").save(icon)

    at_sheet_time: list[list[str]] = []
    at_sheet_time_icons: list[list[str]] = []
    real_render = runner_mod.render_sheet

    def spy(data):
        # Called immediately BEFORE the sheet is written, so whatever is on disk
        # right now is exactly the set of things the sheet is written after.
        at_sheet_time.append(sorted(p.name for p in folder.iterdir()))
        pics = folder / runner_mod.TRACK_PICTURES_DIR
        at_sheet_time_icons.append(sorted(p.name for p in pics.iterdir()) if pics.is_dir() else [])
        return real_render(data)

    monkeypatch.setattr(runner_mod, "render_sheet", spy)
    res = runner_mod.export_card(
        tracks=[_track(sample_mp3, "Chapter One", icon=icon),
                _track(sample_mp3, "Chapter Two")],
        card_name="Bedtime Stories", picture_path=picture, root=root,
        scratch_dir=tmp_path / "scratch", version="0.1.13",
    )
    assert res.folder == folder
    assert len(at_sheet_time) == 1, "the sheet is rendered exactly once"
    landed = set(at_sheet_time[0])

    # Sanity: the spy really did observe a populated folder, so the equality
    # below is not passing on two empty sets.
    assert "01 - Chapter One.mp3" in landed
    assert "02 - Chapter Two.mp3" in landed
    assert runner_mod.CARD_PICTURE_NAME in landed
    assert runner_mod.TRACK_PICTURES_DIR in landed

    # THE ASSERTION THAT MATTERS, and it is an equality rather than a list of
    # names on purpose: what was on disk when the sheet was rendered must be
    # EVERYTHING the run produced except the sheet itself. A whitelist of known
    # names would still pass if a later refactor wrote one more file AFTER the
    # sheet — which is precisely the regression that turns copy.md §5.10
    # paragraph 2 into a lie, because she would find a folder with a
    # "What to do next" page in it that is nonetheless incomplete.
    final = {p.name for p in folder.iterdir()}
    assert landed == final - {runner_mod.SHEET_NAME}, (
        "something was written AFTER the instruction sheet: "
        f"{sorted(final - {runner_mod.SHEET_NAME} - landed)}. "
        "copy.md §5.10 paragraph 2 tells the user that the presence of that "
        "page means the save finished — overview.md §10.5a makes the write "
        "order a contract, and this breaks it."
    )
    assert runner_mod.SHEET_NAME in final

    # The track-pictures subfolder must be POPULATED before the sheet, not just
    # created — iterdir() above is not recursive, so it alone would not notice.
    assert at_sheet_time_icons[0], "track pictures were written after the sheet"


def test_the_progress_phases_put_the_sheet_after_the_pictures(tmp_path, sample_mp3):
    """The same contract from the other side: the phase order the user watches.

    The write order above is what makes copy.md §5.10 true; this pins that the
    reported order agrees with it, so a reordering cannot pass by moving the
    write and the phase together.
    """
    stages: list[str] = []
    runner_mod.export_card(
        tracks=[_track(sample_mp3, "A")], card_name="Bedtime Stories",
        picture_path=None, root=tmp_path / "saved", scratch_dir=tmp_path / "s",
        version="0.1.13",
        update=lambda stage, percent, message: stages.append(stage),
    )
    assert stages.index("sheet") > stages.index("pictures")
    assert stages.index("pictures") > stages.index("save")
    assert stages[-1] == "done"


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


# --------------------------------------------------------------------------- #
# Task 6 — opening the folder
# --------------------------------------------------------------------------- #
import os
import sys

from yoto_maker.export import reveal as reveal_mod


def test_reveal_support_matches_the_platform():
    assert reveal_mod.reveal_supported() is hasattr(os, "startfile")
    if not sys.platform.startswith("win"):
        assert reveal_mod.reveal_supported() is False


def test_reveal_refuses_rather_than_raising_something_technical(tmp_path, monkeypatch):
    monkeypatch.setattr(reveal_mod, "reveal_supported", lambda: False)
    with pytest.raises(ExportError):
        reveal_mod.reveal_folder(tmp_path)


# --------------------------------------------------------------------------- #
# Task 7 — the three routes, and the shared card construction
# --------------------------------------------------------------------------- #
import time

from fastapi.testclient import TestClient

from yoto_maker.server.app import app as fastapi_app


@pytest.fixture
def client(temp_config):
    with TestClient(fastapi_app) as c:
        yield c


def _drain(client, job_id):
    """Poll to completion. The sleep is not decoration: the job runs on another
    thread, and a tight loop starves it on a single-core runner."""
    for _ in range(400):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.01)
    raise AssertionError("job never finished")


def test_refusals_are_the_parallel_wording_and_come_before_anything_is_written(client):
    client.post("/api/draft/reset")
    r = client.post("/api/export")
    assert r.status_code == 400
    assert r.json()["error"] == "Add some audio before saving it."


def test_saving_needs_no_sign_in(client, sample_mp3, monkeypatch):
    """The headline property. If this test ever needs a connection, the feature
    has been deleted."""
    import yoto_maker.server.app as app_mod

    monkeypatch.setattr(app_mod, "connection_status",
                        lambda: {"connected": False, "client_id_verdict": "ok"})
    # The draft is a module-level global that survives across tests in a file,
    # so every route test that adds tracks starts from a known-empty one.
    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    assert job["status"] == "done", job
    assert job["result"]["saved_count"] == 1


def test_the_status_route_reports_where_saved_files_go(client):
    cfg = client.get("/api/status").json()["config"]
    assert cfg["saved_dir"].endswith("Yoto Maker")
    assert cfg["saved_dir"] != cfg["data_dir"]


def test_the_sheet_route_serves_what_is_in_the_folder(client, sample_mp3):
    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    folder = Path(job["result"]["folder_path"])
    served = client.get(job["result"]["sheet_url"])
    assert served.status_code == 200
    assert served.text == (folder / "What to do next.html").read_text(encoding="utf-8")


def test_the_open_route_accepts_an_opaque_id_and_never_a_path(client, sample_mp3):
    """The safety property, overview.md §7.3.

    The route now takes one field so the button can open the folder its OWN panel
    is about rather than whichever job finished last — but that field is an
    opaque id this server minted, never a filesystem path. The distinction is
    what this test pins: the model has exactly one field named ``id``, and a
    real, existing path offered as an id is simply an id nobody minted, so it
    takes the same "folder is gone" failure a deleted folder does.
    """
    import inspect

    from yoto_maker.export.errors import REASON_FOLDER_GONE
    from yoto_maker.server.app import OpenSavedBody, open_saved_folder

    client.post("/api/draft/reset")
    assert list(inspect.signature(open_saved_folder).parameters) == ["body"]
    assert list(OpenSavedBody.model_fields) == ["id"]
    assert client.post("/api/export/open").status_code == 400   # nothing saved yet

    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    assert job["status"] == "done", job

    # The folder EXISTS and is the one the server just wrote — and offering its
    # path as the id still gets nowhere, because ids are looked up, never joined.
    refused = client.post("/api/export/open", json={"id": job["result"]["folder_path"]})
    assert refused.status_code == 400
    assert refused.json()["error"] == REASON_FOLDER_GONE
    assert "path" not in refused.json()


def test_a_failed_open_carries_the_path_so_the_message_is_not_a_dead_end(
    client, sample_mp3, monkeypatch
):
    """copy.md §5.5a's two cases, distinguished by the route.

    (a) nothing recorded -> the {error} envelope, no path.
    (b) the folder is there and the OS refused -> the same envelope PLUS the
        path, which app.js renders beneath the sentence in .mono-value.
    """
    import yoto_maker.server.app as app_mod
    from yoto_maker.export.errors import REASON_CANNOT_OPEN, REASON_FOLDER_GONE

    client.post("/api/draft/reset")
    gone = client.post("/api/export/open")
    assert gone.status_code == 400
    assert gone.json()["error"] == REASON_FOLDER_GONE
    assert "path" not in gone.json()

    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    job = _drain(client, client.post("/api/export").json()["job_id"])
    assert job["status"] == "done", job

    def boom(_folder):
        raise ExportError(REASON_CANNOT_OPEN)

    monkeypatch.setattr(app_mod, "reveal_folder", boom)
    refused = client.post("/api/export/open")
    assert refused.status_code == 400
    assert refused.json()["error"] == REASON_CANNOT_OPEN
    assert refused.json()["path"] == job["result"]["folder_path"]


def test_every_save_gets_its_own_scratch_root_and_removes_it_afterwards(
    client, sample_mp3, monkeypatch
):
    """Two concurrent saves once shared ``work/export`` — and the runner keys each
    track's staging directory on the track index alone, while normalize_to_mp3
    names its output after the input's stem. Two jobs converting their own track
    1 therefore wrote to the same path, and a card was written holding another
    card's audio and reported as a complete success.
    """
    import yoto_maker.server.app as app_mod

    seen: list[Path] = []
    real = app_mod.export_card

    def spy(**kwargs):
        seen.append(Path(kwargs["scratch_dir"]))
        return real(**kwargs)

    monkeypatch.setattr(app_mod, "export_card", spy)
    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})

    for _ in range(2):
        job = _drain(client, client.post("/api/export").json()["job_id"])
        assert job["status"] == "done", job

    assert len(seen) == 2
    assert len(set(seen)) == 2, f"two jobs shared one scratch root: {seen}"
    assert not [p for p in seen if p.exists()], "each run must remove its own"


def test_each_save_gets_an_id_that_resolves_to_its_own_folder(client, sample_mp3):
    """interactions.md §9.3. A single "last folder" global served whichever job
    finished LAST to every panel: save card A in one tab, card B in another, and
    tab A's "📄 What to do next" showed card B's instructions.
    """
    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})

    first = _drain(client, client.post("/api/export").json()["job_id"])["result"]
    second = _drain(client, client.post("/api/export").json()["job_id"])["result"]

    assert first["save_id"] and second["save_id"]
    assert first["save_id"] != second["save_id"]
    assert first["folder_path"] != second["folder_path"]
    # The id travels INSIDE the URL the panel is handed — it reconstructs nothing.
    assert first["sheet_url"].endswith(first["save_id"])

    for r in (first, second):
        served = client.get(r["sheet_url"])
        assert served.status_code == 200
        assert served.text == (
            Path(r["folder_path"]) / "What to do next.html"
        ).read_text(encoding="utf-8")

    # The proof that the ids are doing the work: the two pages are different.
    assert client.get(first["sheet_url"]).text != client.get(second["sheet_url"]).text


def test_starting_a_new_card_forgets_the_folder(client, sample_mp3):
    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})
    _drain(client, client.post("/api/export").json()["job_id"])
    assert client.get("/api/export/sheet.html").status_code == 200
    client.post("/api/draft/reset")
    assert client.get("/api/export/sheet.html").status_code == 404


def test_both_paths_build_the_same_card(client, sample_mp3, monkeypatch):
    """Acceptance criterion 8, at the seam where the two could drift.

    Calling _build_card_inputs twice and comparing proves DETERMINISM, not
    SHARING — it would still pass if the send path went back to its own inline
    comprehension, which is the exact drift criterion 8 forbids. So the sharing
    itself is pinned below: both route bodies must name the function, and both
    must be observed calling it when actually driven.
    """
    import inspect
    from types import SimpleNamespace

    import yoto_maker.server.app as app_mod

    client.post("/api/draft/reset")
    with sample_mp3.open("rb") as fh:
        client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "Bedtime Stories"})

    # 1. Determinism, and that _resolve_icon is called rather than reimplemented.
    draft = app_mod.get_draft()
    a, name_a = app_mod._build_card_inputs(draft)
    b, name_b = app_mod._build_card_inputs(draft)
    assert name_a == name_b == "Bedtime Stories"
    assert [(x.title, x.audio_path, x.icon_path) for x in a] == \
           [(x.title, x.audio_path, x.icon_path) for x in b]
    assert all(x.icon_path is not None for x in a), "_resolve_icon must have run"

    # 2. Both routes name the shared function in their own source.
    for route in (app_mod.send_to_yoto, app_mod.export_to_folder):
        assert "_build_card_inputs(" in inspect.getsource(route), route.__name__

    # 3. And both actually call it when driven end to end.
    calls: list = []
    real = app_mod._build_card_inputs

    def spy(d):
        calls.append(d)
        return real(d)

    class _FakeYotoClient:
        """No network. The send path's only job here is to reach the shared call."""

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def create_card(self, name, inputs, progress=None):
            return SimpleNamespace(content_id="fake", title=name)

    monkeypatch.setattr(app_mod, "_build_card_inputs", spy)
    monkeypatch.setattr(app_mod, "connection_status",
                        lambda: {"connected": True, "client_id_verdict": "ok"})
    monkeypatch.setattr(app_mod, "YotoClient", _FakeYotoClient)

    sent = _drain(client, client.post("/api/send").json()["job_id"])
    assert sent["status"] == "done", sent
    assert len(calls) == 1, "the send path must go through _build_card_inputs"

    saved = _drain(client, client.post("/api/export").json()["job_id"])
    assert saved["status"] == "done", saved
    assert len(calls) == 2, "the save path must go through _build_card_inputs"
