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

import logging
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .. import config as config_mod
from ..audio.normalize import AudioInfo, probe_audio
from . import auth

log = logging.getLogger("yoto_maker.yoto")

# Uploading the audio can take minutes on a slow home connection, so the write
# must NOT use the short default timeout (that caused 60s WriteTimeouts). Connect
# and read stay bounded so a genuinely dead connection still fails cleanly.
UPLOAD_TIMEOUT = httpx.Timeout(connect=30.0, read=180.0, write=None, pool=30.0)
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


@dataclass
class CardSummary:
    """One card as listed by GET /content/mine."""
    card_id: str
    title: str
    created_at: str | None = None
    track_count: int | None = None


@dataclass
class ArtifactProbe:
    """What a served artifact actually is, read from its pre-signed URL."""
    is_opus: bool
    detail: str                       # human-readable reason, for the report
    content_type: str | None = None


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


def _track_count(card: dict) -> int | None:
    """Best-effort track count from a /content/mine list item (often absent)."""
    if not isinstance(card, dict):
        return None
    for key in ("trackCount", "noOfTracks"):
        v = card.get(key)
        if isinstance(v, int):
            return v
    tracks = card.get("tracks")
    return len(tracks) if isinstance(tracks, list) else None


def _transcoded_format(info) -> str | None:
    """Return Yoto's true transcoded ``format`` (e.g. ``"opus"``), else ``None``.

    Yoto re-transcodes every upload and reports the real artifact's format in the
    ``transcodedInfo`` block of the poll response. The card should advertise that
    (Yoto serves Ogg Opus), not the local pre-upload file's format. This is
    **best-effort**: a missing / empty / wrong-type ``transcodedInfo`` returns
    ``None`` so the caller falls back to the local probe rather than failing —
    the card is always built. ``fileSize``/``duration``/``channels`` are left to
    the local probe because Yoto already self-corrects those server-side.
    """
    if isinstance(info, dict):
        fmt = info.get("format")
        if isinstance(fmt, str) and fmt:
            return fmt
    return None


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
            sha, transcoded_info = self._poll_transcode(
                upload_id,
                on_wait=lambda secs: emit(
                    "transcode", i, total,
                    f"Preparing track {i} of {total}… (Yoto is processing — {secs}s)",
                ),
            )

            info = _safe_probe(tr.audio_path)
            # Advertise Yoto's true transcoded format (it serves Ogg Opus) when it
            # reports one; otherwise fall back to the local probe. Best-effort: a
            # missing transcodedInfo degrades, it never blocks the card.
            fmt = _transcoded_format(transcoded_info) or info.format
            icon_ref = None
            if tr.icon_path:
                icon_ref = self._upload_icon_best_effort(tr.icon_path)

            metas.append(
                TrackMeta(
                    title=tr.title,
                    transcoded_sha=sha,
                    duration_s=info.duration_s,
                    file_size=info.file_size,
                    fmt=fmt,
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
        size = audio_path.stat().st_size if audio_path.exists() else 0
        try:
            with open(audio_path, "rb") as fh:
                resp = self._client.put(
                    upload_url,
                    content=fh.read(),
                    headers={"Content-Type": content_type},
                    timeout=UPLOAD_TIMEOUT,  # don't 60s-timeout a large/slow upload
                )
            resp.raise_for_status()
        except Exception as exc:
            log.warning("Yoto audio PUT failed (%s, %d bytes): %r", audio_path.name, size, exc)
            raise YotoError(_friendly_http(exc, "uploading the audio")) from exc

    def _poll_transcode(
        self,
        upload_id: str,
        *,
        timeout_s: float = 600.0,
        interval: float = 2.0,
        on_wait=None,
    ) -> tuple[str, dict | None]:
        """Poll until Yoto finishes transcoding; return ``(sha, transcodedInfo)``.

        ``transcodedInfo`` is the block Yoto returns alongside the sha describing
        the real transcoded artifact (its ``format``/``fileSize``/etc). It is
        returned as-is (a dict, or ``None`` if Yoto didn't include one) for the
        caller to use best-effort — the sha alone is enough to build the card.

        Yoto transcodes server-side and returns 202 (with no sha) while working;
        a large track can take minutes, so we wait up to ``timeout_s`` (default
        10 min) and report elapsed time via ``on_wait``. Transient errors are
        tolerated; auth failures are fatal.
        """
        deadline = time.time() + timeout_s
        start = time.time()
        consecutive_errors = 0
        while time.time() < deadline:
            try:
                resp = self._client.get(
                    f"{self._base}/media/upload/{upload_id}/transcoded",
                    params={"loudnorm": "false"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                body = resp.json()
                sha = _dig(body, "transcodedSha256")
                if sha:
                    return sha, _dig(body, "transcodedInfo")
                consecutive_errors = 0
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (401, 403):
                    raise YotoError(_friendly_http(exc, "preparing the audio")) from exc
                consecutive_errors += 1
                if consecutive_errors >= 8:
                    raise YotoError(_friendly_http(exc, "preparing the audio")) from exc
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors >= 8:
                    raise YotoError(_friendly_http(exc, "preparing the audio")) from exc
            if on_wait:
                on_wait(int(time.time() - start))
            time.sleep(interval)
        raise YotoError(
            "Yoto is taking too long to prepare this audio. Very long tracks can time "
            "out — this app now splits long files into parts automatically, so please "
            "try again. If it keeps happening, the file may be too large for Yoto."
        )

    def _upload_icon_best_effort(self, icon_path: Path) -> str | None:
        """Upload a 16x16 icon; return 'yoto:#<mediaId>' or None on any failure.

        Yoto's display-icon endpoint wants the **raw image bytes** as the body
        (Content-Type image/png), NOT a multipart form — a multipart request is
        rejected with 400 "A binary image file is required".
        """
        try:
            with open(icon_path, "rb") as fh:
                data = fh.read()
            resp = self._client.post(
                f"{self._base}/media/displayIcons/user/me/upload",
                headers={**self._headers(), "Content-Type": "image/png"},
                content=data,
            )
            resp.raise_for_status()
            media_id = _dig(resp.json(), "mediaId", "displayIconId", "id")
            if media_id:
                return f"yoto:#{media_id}"
            log.warning("Icon upload returned no mediaId: %s", resp.text[:200])
            return None
        except Exception as exc:
            log.warning("Icon upload failed (best-effort, continuing without icon): %r", exc)
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

    # -- account read/write surface (used by yoto/repair.py) --------------
    def list_my_cards(self) -> list[CardSummary]:
        """GET /content/mine -> the account's cards (id + title + createdAt).

        The live shape is ``{"cards": [ {cardId, title, createdAt, ...}, ... ]}``
        (pinned against a real body); the parsing also tolerates a bare list or
        another common wrapper so it survives a shape change.
        """
        try:
            resp = self._client.get(f"{self._base}/content/mine", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "listing your cards")) from exc

        items = data if isinstance(data, list) else _dig(data, "cards", "content", "mine", default=[])
        cards: list[CardSummary] = []
        for it in items if isinstance(items, list) else []:
            cid = _dig(it, "cardId", "contentId", "id")
            if not cid:
                continue
            cards.append(CardSummary(
                card_id=cid,
                title=_dig(it, "title", default="(untitled)"),
                created_at=_dig(it, "createdAt", "created", default=None),
                track_count=_track_count(it),
            ))
        return cards

    def get_card(self, card_id: str) -> dict:
        """GET /card/{card_id} -> the card body, UNWRAPPED from its envelope.

        The live endpoint returns ``{"card": {...}, "ownership": {...}}`` (pinned
        against a real body — plan Task 1/Step 0). We return the inner ``card``
        object: the thing repair.py backs up, deep-copies, mutates (format only)
        and POSTs back via POST /content. It also carries each track's resolved,
        short-lived pre-signed ``trackUrl`` used to probe the served artifact. A
        response that is already unwrapped is returned as-is.
        """
        try:
            resp = self._client.get(f"{self._base}/card/{card_id}", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "reading the card")) from exc
        if isinstance(data, dict) and isinstance(data.get("card"), dict):
            return data["card"]
        return data

    def update_card(self, card_id: str, body: dict) -> dict:
        """POST /content with body['cardId'] = card_id -> update IN PLACE.

        Preserves cardId (and the physical NFC link) and creates NO duplicate.
        The body is sent verbatim except that cardId is (re)asserted, so icons,
        keys, ordering and every unmodelled field survive. This is deliberately
        NOT routed through build_content_payload.

        CAVEAT (pre-merge review HIGH #1): repair.py hands us the deep-copied GET
        body, whose track ``trackUrl`` values are RESOLVED, time-limited signed CDN
        URLs (not the ``yoto:#<sha>`` refs written at create time). We POST them back
        verbatim on the "change only format" principle, relying on Yoto re-mapping
        its own CDN URL to the internal audio reference. That round-trip is UNPROVEN
        by this tool's verify (which runs inside the signing window). The repair CLI
        prints a staged-rollout warning in --apply mode for exactly this reason.
        """
        payload = dict(body)
        payload["cardId"] = card_id
        try:
            resp = self._client.post(
                f"{self._base}/content",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "saving the repaired card")) from exc

    def probe_artifact(self, url: str) -> ArtifactProbe:
        """Fetch a track's served artifact and decide whether it is Ogg Opus.

        The URL is PRE-SIGNED (its auth is in the query string), so we send NO
        bearer header. HEAD first for Content-Type; then sniff the first bytes
        for the Ogg 'OggS' page header + the 'OpusHead' identification header —
        the confirmed signature of what Yoto serves the device. (The real
        Content-Type is ``audio/ogg`` with no ``codecs`` param, so the magic-byte
        path is the one that actually confirms Opus in the field.) Returns a soft
        result (never raises): is_opus=False on any non-Opus / unreadable case,
        with a human-readable reason for the report.
        """
        ctype = ""
        try:
            h = self._client.head(url, follow_redirects=True)
            h.raise_for_status()
            ctype = (h.headers.get("Content-Type") or "").strip()
        except Exception:
            ctype = ""  # some CDNs reject HEAD — fall through to the ranged GET
        if "opus" in ctype.lower():
            return ArtifactProbe(True, f"Content-Type {ctype}", ctype)
        try:
            g = self._client.get(url, headers={"Range": "bytes=0-255"}, follow_redirects=True)
            g.raise_for_status()
            head = g.content[:256]
        except Exception as exc:
            return ArtifactProbe(False, f"couldn't read the artifact ({exc.__class__.__name__})", ctype or None)
        if head[:4] == b"OggS" and b"OpusHead" in head:
            return ArtifactProbe(True, f"OggS/OpusHead magic (Content-Type {ctype or '?'})", ctype or None)
        return ArtifactProbe(False, f"not Opus (Content-Type {ctype or '?'}, first bytes {head[:4]!r})", ctype or None)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "YotoClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


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
    if isinstance(exc, httpx.TimeoutException):
        return (
            f"The connection to Yoto timed out while {doing}. This usually means a slow "
            "internet connection — please try again, ideally on a faster connection."
        )
    return f"Something went wrong while {doing}. Please check your internet and try again."
