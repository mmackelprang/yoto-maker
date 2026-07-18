"""YouTube source adapter, backed by yt-dlp (used as a library).

Extracts the best audio, the video thumbnail (as the suggested picture) and the
title. Errors are translated into plain language for a non-technical user.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from ..tools import find_ffmpeg
from .base import SourceError, SourceResult

# Called during download with a 0-100 percent and a short message.
ProgressHook = Callable[[int, str], None]

_YT_RE = re.compile(
    r"^(https?://)?(www\.)?(m\.)?(youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/)",
    re.IGNORECASE,
)


def _friendly_ytdlp_error(message: str) -> str:
    low = message.lower()
    if "video unavailable" in low or "private video" in low:
        return "That video isn't available — it may be private or removed."
    if "sign in" in low or "age" in low:
        return "That video is age-restricted or needs a sign-in, so it can't be downloaded."
    if "urlopen error" in low or "getaddrinfo" in low or "network" in low:
        return "We couldn't reach YouTube. Please check your internet connection and try again."
    if "unsupported url" in low or "is not a valid url" in low:
        return "That doesn't look like a YouTube link. Please copy the link from the address bar."
    return "We couldn't get that video. Please double-check the link and try again."


class YouTubeAdapter:
    kind = "youtube"

    def can_handle(self, user_input: str) -> bool:
        return bool(_YT_RE.match(user_input.strip()))

    def fetch(
        self,
        user_input: str,
        work_dir: Path,
        *,
        on_progress: ProgressHook | None = None,
    ) -> SourceResult:
        import yt_dlp

        url = user_input.strip()
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        out_tmpl = str(work_dir / "%(id)s.%(ext)s")

        def _hook(d: dict) -> None:
            if not on_progress:
                return
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                pct = int(done / total * 90) if total else 0
                on_progress(pct, "Getting the audio…")
            elif d.get("status") == "finished":
                on_progress(92, "Converting the audio…")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "writethumbnail": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "progress_hooks": [_hook],
            # Convert whatever we get into mp3 so the pipeline is uniform.
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            ],
        }
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg).parent)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:  # type: ignore[attr-defined]
            raise SourceError(_friendly_ytdlp_error(str(exc))) from exc
        except Exception as exc:  # pragma: no cover - unexpected
            raise SourceError(_friendly_ytdlp_error(str(exc))) from exc

        video_id = info.get("id", "audio")
        title = (info.get("title") or "Untitled").strip()
        duration = float(info.get("duration") or 0.0)

        audio_path = self._locate(work_dir, video_id, (".mp3",))
        if audio_path is None:
            raise SourceError("The audio was downloaded but couldn't be found afterwards.")

        image_path = self._locate(
            work_dir, video_id, (".jpg", ".png", ".webp", ".jpeg")
        )

        return SourceResult(
            audio_path=audio_path,
            suggested_title=title,
            source_kind=self.kind,
            duration_s=duration,
            suggested_image_path=image_path,
            source_ref=url,
        )

    @staticmethod
    def _locate(work_dir: Path, stem: str, exts: tuple[str, ...]) -> Path | None:
        for ext in exts:
            candidate = work_dir / f"{stem}{ext}"
            if candidate.exists():
                return candidate
        # Fall back to any file with a matching extension (thumbnail naming
        # can vary by extractor).
        for ext in exts:
            matches = sorted(work_dir.glob(f"{stem}*{ext}"))
            if matches:
                return matches[0]
        return None
