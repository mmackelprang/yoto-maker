"""Audio probing + normalization via ffmpeg/ffprobe.

Yoto transcodes uploads on its own servers, so our job here is modest:
- **probe** a file for the metadata the Yoto ``/content`` call needs
  (duration, channels, format, file size), and
- **normalize** arbitrary input (a video, a weird codec) into a clean MP3 the
  upload step can hand to Yoto.

All ffmpeg invocations are wrapped so failures become friendly errors.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..tools import require_ffmpeg, require_ffprobe

# Hide the console window ffmpeg would otherwise flash on Windows.
_NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0


@dataclass
class AudioInfo:
    duration_s: float
    channels: int
    format: str  # e.g. "mp3", "aac"
    file_size: int
    sample_rate: int = 44100

    def as_track_media(self) -> dict:
        """Shape the Yoto /content call expects under track.media."""
        return {
            "duration": round(self.duration_s),
            "fileSize": self.file_size,
            "channels": "stereo" if self.channels >= 2 else "mono",
            "format": self.format,
        }


class AudioError(RuntimeError):
    """User-friendly audio processing failure."""


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=_NO_WINDOW,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise AudioError("The audio converter could not be started.") from exc


def probe_audio(path: str | Path) -> AudioInfo:
    """Return duration/channels/format/size for an audio (or A/V) file."""
    path = Path(path)
    if not path.exists():
        raise AudioError(f"That file could not be found: {path.name}")

    ffprobe = require_ffprobe()
    # ffprobe gives clean JSON; if only ffmpeg is present, require_ffprobe
    # returned ffmpeg, which does NOT speak -show_format, so guard for that.
    if Path(ffprobe).stem.lower().startswith("ffprobe"):
        cmd = [
            ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ]
        proc = _run(cmd)
        if proc.returncode == 0 and proc.stdout.strip():
            return _parse_ffprobe(proc.stdout, path)

    # Fallback: parse ffmpeg -i stderr for a duration; assume stereo mp3.
    return _probe_with_ffmpeg(path)


def _parse_ffprobe(stdout: str, path: Path) -> AudioInfo:
    data = json.loads(stdout)
    fmt = data.get("format", {})
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    stream = audio_streams[0] if audio_streams else {}

    duration = float(fmt.get("duration") or stream.get("duration") or 0.0)
    channels = int(stream.get("channels") or 2)
    sample_rate = int(stream.get("sample_rate") or 44100)
    codec = (stream.get("codec_name") or "").lower()
    fmt_name = _friendly_format(codec, path)
    size = int(fmt.get("size") or path.stat().st_size)
    return AudioInfo(duration, channels, fmt_name, size, sample_rate)


def _probe_with_ffmpeg(path: Path) -> AudioInfo:
    ffmpeg = require_ffmpeg()
    proc = _run([ffmpeg, "-i", str(path)])
    duration = 0.0
    for line in proc.stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            ts = line.split("Duration:")[1].split(",")[0].strip()
            duration = _hhmmss_to_seconds(ts)
            break
    return AudioInfo(
        duration_s=duration,
        channels=2,
        format=_friendly_format("", path),
        file_size=path.stat().st_size,
    )


def _friendly_format(codec: str, path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    mapping = {"mp4a": "aac", "mpeg": "mp3", "": ext or "mp3"}
    return mapping.get(codec, codec or ext or "mp3")


def _hhmmss_to_seconds(ts: str) -> float:
    try:
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0


def normalize_to_mp3(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    bitrate: str = "192k",
    loudness: bool = False,
) -> tuple[Path, AudioInfo]:
    """Transcode any audio/video input into a clean stereo MP3.

    Returns the output path and its probed :class:`AudioInfo`. Set
    ``loudness=True`` to apply EBU R128 loudness normalization (quieter/louder
    sources evened out) — off by default because Yoto also normalizes.
    """
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{input_path.stem}.mp3"

    ffmpeg = require_ffmpeg()
    cmd = [ffmpeg, "-y", "-i", str(input_path), "-vn", "-ac", "2", "-ar", "44100"]
    if loudness:
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ["-codec:a", "libmp3lame", "-b:a", bitrate, str(out_path)]

    proc = _run(cmd)
    if proc.returncode != 0 or not out_path.exists():
        tail = "\n".join(proc.stderr.splitlines()[-3:])
        raise AudioError(
            "We couldn't convert that audio. It may be an unusual or damaged "
            f"file.\n\nTechnical detail: {tail}"
        )
    return out_path, probe_audio(out_path)
