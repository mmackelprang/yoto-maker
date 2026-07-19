"""Integration-ish tests for audio probe/normalize, images, and label PDF."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from yoto_maker.audio.normalize import normalize_to_mp3, probe_audio
from yoto_maker.images import make_device_icon, prepare_label_image, save_upload
from yoto_maker.images.library import ensure_library, icon_path, list_icons
from yoto_maker.labels import LabelTrack, generate_label_pdf


# ---- audio ----------------------------------------------------------------
def test_probe_audio(sample_mp3):
    info = probe_audio(sample_mp3)
    assert info.duration_s > 1.0
    assert info.file_size > 0
    assert info.channels >= 1
    media = info.as_track_media()
    assert media["duration"] == round(info.duration_s)
    assert media["channels"] in ("mono", "stereo")


def test_normalize_to_mp3(sample_mp3, temp_config):
    out, info = normalize_to_mp3(sample_mp3, temp_config.work_dir / "norm")
    assert out.exists() and out.suffix == ".mp3"
    assert info.duration_s > 1.0


def test_split_audio_short_file_passthrough(sample_mp3, temp_config):
    from yoto_maker.audio.normalize import split_audio

    parts = split_audio(sample_mp3, temp_config.work_dir / "parts", max_seconds=3600)
    assert parts == [sample_mp3]  # short file → single track, unchanged


def test_split_audio_long_file_splits(temp_config, has_ffmpeg):
    import subprocess

    from yoto_maker.audio.normalize import probe_audio, split_audio
    from yoto_maker.tools import require_ffmpeg

    src = temp_config.work_dir / "long.mp3"
    subprocess.run(
        [require_ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=9",
         "-b:a", "64k", str(src)],
        capture_output=True, check=True,
    )
    parts = split_audio(src, temp_config.work_dir / "parts", max_seconds=3)
    assert len(parts) >= 3                      # ~9s at 3s each → ~3 parts
    for p in parts:
        assert p.exists()
        assert probe_audio(p).duration_s <= 4   # each part under the limit (+tolerance)


def test_friendly_format_maps_to_yoto_enum():
    from pathlib import Path

    from yoto_maker.audio.normalize import _YOTO_FORMATS, _friendly_format

    # ffprobe codec names that are NOT valid Yoto formats must be mapped.
    assert _friendly_format("vorbis", Path("x.ogg")) == "ogg"
    assert _friendly_format("pcm_s24le", Path("x.wav")) == "wav"
    assert _friendly_format("mp4a", Path("x.m4a")) == "aac"
    assert _friendly_format("mp3", Path("x.mp3")) == "mp3"
    # unknown codec falls back via extension, else mp3 — always a valid enum
    assert _friendly_format("weirdcodec", Path("x.m4a")) == "x-m4a"
    assert _friendly_format("weirdcodec", Path("x.xyz")) == "mp3"
    for codec in ("vorbis", "pcm_s24le", "pcm_f32le", "opus", "flac", "mp4a", ""):
        assert _friendly_format(codec, Path("a.bin")) in _YOTO_FORMATS


# ---- images ---------------------------------------------------------------
def test_library_generates_ten_icons():
    icons = list_icons()
    assert len(icons) == 10
    assert {"star", "music", "rocket"} <= {i["id"] for i in icons}
    for i in icons:
        p = icon_path(i["id"])
        assert p and p.exists()
        assert Image.open(p).size == (16, 16)


def test_make_device_icon_is_16x16(temp_config):
    star = icon_path("star")
    out = make_device_icon(star, temp_config.work_dir, name="dev")
    assert Image.open(out).size == (16, 16)


def test_prepare_label_image(temp_config):
    # a big red square
    src = temp_config.work_dir / "big.png"
    Image.new("RGB", (2000, 1500), (200, 30, 30)).save(src)
    out = prepare_label_image(src, temp_config.work_dir, name="lbl")
    w, h = Image.open(out).size
    assert max(w, h) <= 1024  # downscaled
    assert out.suffix == ".png"


def test_save_upload(temp_config):
    import io
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), (10, 120, 200)).save(buf, format="JPEG")
    out = save_upload(buf.getvalue(), temp_config.work_dir, name="up")
    assert out.exists()
    assert Image.open(out).mode == "RGB"


# ---- labels ---------------------------------------------------------------
def test_generate_label_pdf(temp_config):
    ensure_library()
    tracks = [LabelTrack(f"Track {i}", icon_path("star")) for i in range(1, 5)]
    out = generate_label_pdf(
        temp_config.work_dir / "label.pdf",
        card_name="Test Card",
        tracks=tracks,
        image_path=icon_path("star"),
    )
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_generate_label_pdf_no_picture(temp_config):
    out = generate_label_pdf(
        temp_config.work_dir / "label2.pdf",
        card_name="No Pic",
        tracks=[LabelTrack("Only track")],
        image_path=None,
    )
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"
