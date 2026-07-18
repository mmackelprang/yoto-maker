"""Yoto MYO upload client.

Implements the documented flow:
  1. GET  /media/transcode/audio/uploadUrl        -> upload URL + id
  2. PUT  <upload URL>  (the audio bytes)
  3. GET  /media/upload/{id}/transcoded           -> poll until transcodedSha256
  4. POST /media/displayIcons/user/me/upload      -> (optional) per-track icon
  5. POST /content                                -> create the playlist

Network shapes are parsed defensively (keys can be nested) and every failure is
turned into a plain-language :class:`YotoError`. The per-track icon step is
best-effort: if it fails, the card is still created without that icon.

NOTE: these endpoints are exercised by mocked tests here; live verification
against a real Yoto account requires a registered Client ID (see
docs/SETUP-YOTO-CONNECTION.md).
"""
from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .. import config as config_mod
from ..audio.normalize import AudioInfo, probe_audio
from . import auth
from .models import TrackMeta, build_content_payload

ProgressCb = Callable[[str, int, int, str], None]


class YotoError(RuntimeError):
    """User-friendly Yoto upload failure."""


@dataclass
class TrackInput:
    audio_path: Path
    title: str
    icon_path: Path | None = None


@dataclass
class CardResult:
    content_id: str
    title: str
    raw: dict


def _dig(data: dict, *keys: str, default=None):
    """Return the first present key, searching top level then one nesting deep."""
    for k in keys:
        if isinstance(data, dict) and k in data and data[k] not in (None, ""):
            return data[k]
    for v in data.values() if isinstance(data, dict) else []:
        if isinstance(v, dict):
            for k in keys:
                if k in v and v[k] not in (None, ""):
                    return v[k]
    return default


class YotoClient:
    def __init__(self, *, timeout: float = 60.0, client: httpx.Client | None = None):
        self._timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._base = config_mod.YOTO_API_BASE

    # -- auth ------------------------------------------------------------
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {auth.get_access_token()}"}

    def is_connected(self) -> bool:
        try:
            auth.get_access_token()
            return True
        except auth.NotConnectedError:
            return False

    # -- public: the whole card in one call ------------------------------
    def create_card(
        self,
        card_title: str,
        tracks: list[TrackInput],
        *,
        progress: ProgressCb | None = None,
    ) -> CardResult:
        if not tracks:
            raise YotoError("There are no tracks to send yet. Add some audio first.")

        def emit(stage: str, cur: int, total: int, msg: str) -> None:
            if progress:
                progress(stage, cur, total, msg)

        total = len(tracks)
        metas: list[TrackMeta] = []
        for i, tr in enumerate(tracks, start=1):
            emit("upload", i, total, f"Sending track {i} of {total}…")
            upload_url, upload_id = self._request_upload_url()
            self._put_audio(upload_url, tr.audio_path)

            emit("transcode", i, total, f"Preparing track {i} of {total}…")
            sha = self._poll_transcode(upload_id)

            info = _safe_probe(tr.audio_path)
            icon_ref = None
            if tr.icon_path:
                icon_ref = self._upload_icon_best_effort(tr.icon_path)

            metas.append(
                TrackMeta(
                    title=tr.title,
                    transcoded_sha=sha,
                    duration_s=info.duration_s,
                    file_size=info.file_size,
                    fmt=info.format,
                    channels="stereo" if info.channels >= 2 else "mono",
                    icon_ref=icon_ref,
                )
            )

        emit("content", total, total, "Building your card…")
        result = self._create_content(card_title, metas)
        emit("done", total, total, "Done! Your card is ready in your Yoto account.")
        return result

    # -- steps -----------------------------------------------------------
    def _request_upload_url(self) -> tuple[str, str]:
        try:
            resp = self._client.get(
                f"{self._base}/media/transcode/audio/uploadUrl",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "getting ready to upload")) from exc

        upload_url = _dig(data, "uploadUrl")
        upload_id = _dig(data, "uploadId")
        if not upload_url or not upload_id:
            raise YotoError("Yoto didn't give us a place to upload to. Please try again.")
        return upload_url, upload_id

    def _put_audio(self, upload_url: str, audio_path: Path) -> None:
        audio_path = Path(audio_path)
        content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
        try:
            with open(audio_path, "rb") as fh:
                resp = self._client.put(
                    upload_url,
                    content=fh.read(),
                    headers={"Content-Type": content_type},
                )
            resp.raise_for_status()
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "uploading the audio")) from exc

    def _poll_transcode(self, upload_id: str, *, attempts: int = 60, interval: float = 1.0) -> str:
        last = None
        for _ in range(attempts):
            try:
                resp = self._client.get(
                    f"{self._base}/media/upload/{upload_id}/transcoded",
                    params={"loudnorm": "false"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                last = resp.json()
            except Exception as exc:
                raise YotoError(_friendly_http(exc, "preparing the audio")) from exc

            sha = _dig(last, "transcodedSha256")
            if sha:
                return sha
            time.sleep(interval)
        raise YotoError(
            "Preparing the audio is taking longer than expected. Please try again in a moment."
        )

    def _upload_icon_best_effort(self, icon_path: Path) -> str | None:
        """Upload a 16x16 icon; return 'yoto:#<id>' or None on any failure."""
        try:
            with open(icon_path, "rb") as fh:
                resp = self._client.post(
                    f"{self._base}/media/displayIcons/user/me/upload",
                    headers=self._headers(),
                    files={"file": (Path(icon_path).name, fh.read(), "image/png")},
                )
            resp.raise_for_status()
            media_id = _dig(resp.json(), "mediaId", "displayIconId", "id")
            return f"yoto:#{media_id}" if media_id else None
        except Exception:
            return None  # icons are a nice-to-have, never fail the card over one

    def _create_content(self, card_title: str, metas: list[TrackMeta]) -> CardResult:
        payload = build_content_payload(card_title, metas)
        try:
            resp = self._client.post(
                f"{self._base}/content",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "creating the card")) from exc

        content_id = _dig(data, "cardId", "contentId", "id") or ""
        return CardResult(content_id=content_id, title=card_title, raw=data)

    def close(self) -> None:
        self._client.close()


def _safe_probe(path: Path) -> AudioInfo:
    try:
        return probe_audio(path)
    except Exception:
        size = Path(path).stat().st_size if Path(path).exists() else 0
        return AudioInfo(duration_s=0.0, channels=2, format="mp3", file_size=size)


def _friendly_http(exc: Exception, doing: str) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return "Your Yoto sign-in has expired. Please connect your Yoto account again."
        if code == 413:
            return "That audio file is too big for Yoto (max 5 hours per card)."
        if 500 <= code < 600:
            return f"Yoto had a problem while {doing}. Please try again shortly."
    return f"Something went wrong while {doing}. Please check your internet and try again."
