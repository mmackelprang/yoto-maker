"""Source adapter tests (no network — URL matching, friendly errors, file path)."""
from __future__ import annotations

from pathlib import Path

import pytest

from yoto_maker.sources import AudioFileAdapter, SourceError, YouTubeAdapter
from yoto_maker.sources.youtube import _friendly_ytdlp_error


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=abc123",
    "http://youtube.com/watch?v=abc",
    "https://youtu.be/abc123",
    "https://www.youtube.com/shorts/xyz",
    "youtube.com/watch?v=abc",
])
def test_youtube_can_handle_true(url):
    assert YouTubeAdapter().can_handle(url)


@pytest.mark.parametrize("url", [
    "https://vimeo.com/12345",
    "not a url",
    "https://example.com/song.mp3",
    "",
])
def test_youtube_can_handle_false(url):
    assert not YouTubeAdapter().can_handle(url)


def test_youtube_friendly_errors():
    assert "private" in _friendly_ytdlp_error("ERROR: Private video").lower()
    assert "internet" in _friendly_ytdlp_error("urlopen error getaddrinfo failed").lower()
    assert "age" in _friendly_ytdlp_error("Sign in to confirm your age").lower()


def test_youtube_postprocessors_with_sponsorblock():
    from yoto_maker.sources.youtube import DEFAULT_SPONSOR_CATEGORIES, build_postprocessors

    pps = build_postprocessors(True, DEFAULT_SPONSOR_CATEGORIES)
    keys = [p["key"] for p in pps]
    # SponsorBlock fetches, ModifyChapters cuts, THEN we extract audio (order).
    assert keys == ["SponsorBlock", "ModifyChapters", "FFmpegExtractAudio"]
    assert pps[0]["categories"] == DEFAULT_SPONSOR_CATEGORIES
    assert pps[0]["when"] == "after_filter"
    assert pps[1]["remove_sponsor_segments"] == DEFAULT_SPONSOR_CATEGORIES


def test_youtube_postprocessors_without_sponsorblock():
    from yoto_maker.sources.youtube import build_postprocessors

    pps = build_postprocessors(False, ["sponsor"])
    assert [p["key"] for p in pps] == ["FFmpegExtractAudio"]


def test_youtube_sponsorblock_best_effort_retry(temp_config, monkeypatch, tmp_path):
    """If the download fails with SponsorBlock on, it retries without it."""
    import yt_dlp

    from yoto_maker.sources.youtube import YouTubeAdapter

    attempts = []

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download):
            has_sb = any(p.get("key") == "SponsorBlock" for p in self.opts.get("postprocessors", []))
            attempts.append(has_sb)
            if has_sb:
                # simulate the exact ffprobe failure the packaged build hit
                raise yt_dlp.utils.DownloadError(
                    "Postprocessing: Unable to determine video duration: ffprobe not found"
                )
            wd = Path(self.opts["outtmpl"]).parent
            (wd / "vid.mp3").write_bytes(b"ID3fake-audio")
            return {"id": "vid", "title": "Rainbow Magic", "duration": 123}

    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)

    result = YouTubeAdapter().fetch("https://youtu.be/vid", tmp_path / "wk", remove_sponsors=True)

    assert attempts == [True, False]        # tried WITH SponsorBlock, then WITHOUT
    assert result.suggested_title == "Rainbow Magic"
    assert result.audio_path.name == "vid.mp3"


@pytest.mark.parametrize("name,ok", [
    ("song.mp3", True), ("a.M4A", True), ("x.wav", True),
    ("clip.mp4", True), ("doc.pdf", False), ("image.png", False),
])
def test_audiofile_can_handle(name, ok):
    assert AudioFileAdapter().can_handle(name) is ok


def test_audiofile_missing_file(temp_config):
    with pytest.raises(SourceError):
        AudioFileAdapter().fetch("does_not_exist.mp3", temp_config.work_dir)


def test_audiofile_fetch_reads_title_and_copies(sample_mp3, temp_config):
    result = AudioFileAdapter().fetch(str(sample_mp3), temp_config.work_dir)
    assert result.audio_path.exists()
    assert result.source_kind == "file"
    # title comes from the embedded tag we set in the fixture
    assert result.suggested_title == "Sample Song"
    assert result.duration_s > 1.0
