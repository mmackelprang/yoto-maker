"""FastAPI app: the local API behind the browser wizard.

Everything is loopback-only and single-user. Slow steps (YouTube download,
sending to Yoto) run as background jobs the UI polls for progress. Every error
returned to the browser is already plain-language (raised as SourceError /
YotoError / AudioError / ImageError), so the UI can show it verbatim.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .. import APP_NAME, __version__
from .. import updater
from ..audio.normalize import MAX_TRACK_SECONDS, AudioError, probe_audio, split_audio
from ..config import get_config
from ..images import crop_image, make_device_icon, prepare_label_image, save_source_image, save_upload
from ..images.ai import AIUnavailableError, ai_available, generate_image
from ..images.library import ensure_library, icon_path, list_icons
from ..images.picture import ImageError
from ..labels import LabelTrack, generate_label_pdf
from ..sources import AudioFileAdapter, SourceError, YouTubeAdapter
from ..tools import check_tools
from ..yoto import (
    NotConnectedError,
    TrackInput,
    YotoClient,
    YotoError,
    connection_status,
    finish_login,
    logout,
    start_login,
)
from .draft import get_draft
from .jobs import get_jobs

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title=APP_NAME, version=__version__)

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


@app.middleware("http")
async def _origin_guard(request, call_next):
    """Reject state-changing requests from other websites (CSRF defense).

    The server is loopback-only and unauthenticated, so a page open elsewhere in
    the same browser could otherwise POST to it. We block any non-GET request
    whose Origin isn't loopback. Same-origin UI calls (Origin = our host) and
    non-browser clients (no Origin header) are unaffected.
    """
    from urllib.parse import urlparse

    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).hostname not in _ALLOWED_HOSTS:
            return JSONResponse(status_code=403, content={"error": "Blocked a cross-site request."})
    return await call_next(request)


# --------------------------------------------------------------------------- #
# Error handling: turn our friendly exceptions into clean JSON the UI shows.
# --------------------------------------------------------------------------- #
FRIENDLY_ERRORS = (SourceError, YotoError, AudioError, ImageError, AIUnavailableError)


@app.exception_handler(SourceError)
@app.exception_handler(YotoError)
@app.exception_handler(AudioError)
@app.exception_handler(ImageError)
@app.exception_handler(AIUnavailableError)
@app.exception_handler(updater.UpdateError)
async def _friendly_handler(_request, exc):  # noqa: ANN001
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(NotConnectedError)
async def _not_connected(_request, exc):  # noqa: ANN001
    return JSONResponse(status_code=409, content={"error": "Please connect your Yoto account first.", "need_connect": True})


# --------------------------------------------------------------------------- #
# Status + draft
# --------------------------------------------------------------------------- #
@app.get("/api/status")
async def status() -> dict:
    from ..settings import get_settings

    tools = check_tools()
    return {
        "app": APP_NAME,
        "version": __version__,
        "tools": {"ffmpeg": bool(tools.ffmpeg), "yt_dlp": tools.yt_dlp, "ok": tools.ok},
        "yoto": connection_status(),
        "ai_available": ai_available(),
        "remove_sponsors": bool(get_settings().get("remove_sponsors", True)),
    }


@app.get("/api/update")
async def update_check() -> dict:
    return await run_in_threadpool(updater.check_for_update)


@app.post("/api/update/apply")
async def update_apply() -> dict:
    info = await run_in_threadpool(updater.check_for_update)
    if not info.get("can_self_update"):
        raise updater.UpdateError("This version can't update itself. Please download the new one from the website.")
    if not info.get("update_available") or not info.get("download_url"):
        raise updater.UpdateError("No update is available right now.")

    dl = info["download_url"]

    def work(update):
        update("download", 0, "Downloading the update…")
        updater.apply_update(dl, progress=lambda p: update("download", p, f"Downloading the update… {p}%"))
        return {"restarting": True}

    job_id = get_jobs().start(work)
    return {"job_id": job_id}


class RemoveSponsorsBody(BaseModel):
    enabled: bool


@app.post("/api/settings/remove-sponsors")
async def set_remove_sponsors(body: RemoveSponsorsBody) -> dict:
    from ..settings import get_settings

    get_settings().set("remove_sponsors", bool(body.enabled))
    return {"ok": True, "remove_sponsors": bool(body.enabled)}


@app.get("/api/draft")
async def get_draft_view() -> dict:
    return get_draft().view()


@app.post("/api/draft/reset")
async def reset_draft() -> dict:
    get_draft().reset()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Tracks
# --------------------------------------------------------------------------- #
def _auto_apply_picture_if_absent() -> None:
    """If no picture is chosen yet, use the one that came with the audio
    (YouTube thumbnail or embedded album art). Best-effort — never raises, and
    never overrides a picture the user already picked."""
    draft = get_draft()
    if draft.picture_path and Path(draft.picture_path).exists():
        return
    src = draft.first_suggested_image()
    if not src:
        return
    try:
        _set_picture(src, "auto")
    except Exception:
        pass  # a bad thumbnail must never block adding a track


def _add_result_as_tracks(result, source_kind: str) -> list:
    """Add a fetched source to the draft as one or more tracks.

    Audio longer than Yoto's per-track limit is split into parts (each becomes a
    track), so long audiobooks work instead of getting stuck in Yoto transcode.
    """
    draft = get_draft()
    cfg = get_config()
    parts = split_audio(result.audio_path, cfg.work_dir / "parts", max_seconds=MAX_TRACK_SECONDS)
    multi = len(parts) > 1
    added = []
    for i, part in enumerate(parts, start=1):
        try:
            duration = probe_audio(part).duration_s
        except Exception:
            duration = 0.0
        title = f"{result.suggested_title} (part {i})" if multi else result.suggested_title
        added.append(
            draft.add_track(
                title=title,
                audio_path=part,
                duration_s=duration,
                source_kind=source_kind,
                source_ref=result.source_ref,
                suggested_image_path=result.suggested_image_path,
            )
        )
    _auto_apply_picture_if_absent()
    return added


class YouTubeBody(BaseModel):
    url: str


@app.post("/api/tracks/youtube")
async def add_youtube(body: YouTubeBody) -> dict:
    """Start a background job that downloads + adds a YouTube track."""
    url = body.url.strip()
    adapter = YouTubeAdapter()
    if not adapter.can_handle(url):
        raise SourceError("That doesn't look like a YouTube link. Copy it from the address bar and try again.")

    from ..settings import get_settings

    cfg = get_config()
    draft = get_draft()
    remove_sponsors = bool(get_settings().get("remove_sponsors", True))

    def work(update):
        update("download", 5, "Getting the audio…")
        result = adapter.fetch(
            url,
            cfg.work_dir,
            on_progress=lambda p, m: update("download", max(5, p), m),
            remove_sponsors=remove_sponsors,
        )
        update("split", 95, "Getting it ready…")
        added = _add_result_as_tracks(result, "youtube")
        return {"count": len(added), "track": added[0].view() if added else None}

    job_id = get_jobs().start(work)
    return {"job_id": job_id}


@app.post("/api/tracks/file")
async def add_file(file: UploadFile) -> dict:
    cfg = get_config()
    uploads = cfg.work_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    # Never trust the client-supplied filename: strip any path components so a
    # crafted name like "..\\..\\evil.mp3" can't escape the uploads folder.
    safe_name = Path(file.filename or "audio").name or "audio"
    dest = uploads / safe_name
    dest.write_bytes(await file.read())

    adapter = AudioFileAdapter()
    if not adapter.can_handle(str(dest)):
        dest.unlink(missing_ok=True)
        raise SourceError("That file type isn't supported. Try an MP3, M4A or WAV file.")

    result = adapter.fetch(str(dest), cfg.work_dir)
    added = _add_result_as_tracks(result, "file")
    return {"count": len(added), "track": added[0].view() if added else None}


class RenameBody(BaseModel):
    title: str


@app.patch("/api/tracks/{track_id}")
async def rename_track(track_id: str, body: RenameBody) -> dict:
    track = get_draft().get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    track.title = body.title.strip() or track.title
    return {"track": track.view()}


class IconBody(BaseModel):
    icon_id: str


@app.post("/api/tracks/{track_id}/icon")
async def set_track_icon(track_id: str, body: IconBody) -> dict:
    track = get_draft().get(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    if icon_path(body.icon_id) is None:
        raise HTTPException(400, "Unknown icon")
    track.icon_id = body.icon_id
    return {"track": track.view()}


@app.delete("/api/tracks/{track_id}")
async def delete_track(track_id: str) -> dict:
    if not get_draft().remove(track_id):
        raise HTTPException(404, "Track not found")
    return {"ok": True}


class ReorderBody(BaseModel):
    order: list[str]


@app.post("/api/tracks/reorder")
async def reorder_tracks(body: ReorderBody) -> dict:
    get_draft().reorder(body.order)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Card name + picture
# --------------------------------------------------------------------------- #
class CardNameBody(BaseModel):
    name: str


@app.post("/api/card/name")
async def set_card_name(body: CardNameBody) -> dict:
    get_draft().card_name = body.name.strip()
    return {"ok": True}


def _set_picture(src_path: Path, source_kind: str) -> None:
    """Store a normalized editable source + a prepared display picture."""
    draft = get_draft()
    cfg = get_config()
    draft.picture_source_path = save_source_image(src_path, cfg.work_dir)
    draft.picture_path = prepare_label_image(draft.picture_source_path, cfg.work_dir, name="card_picture")
    draft.picture_source = source_kind


@app.post("/api/picture/auto")
async def picture_auto() -> dict:
    draft = get_draft()
    src = draft.first_suggested_image()
    if not src:
        raise ImageError("None of your audio came with a picture. Upload one or pick from the icon library.")
    _set_picture(src, "auto")
    return {"ok": True, "picture_url": "/api/picture.png"}


@app.post("/api/picture/upload")
async def picture_upload(file: UploadFile) -> dict:
    cfg = get_config()
    data = await file.read()
    raw = cfg.work_dir / "picture_upload_raw"
    raw.write_bytes(data)
    try:
        _set_picture(raw, "upload")
    finally:
        raw.unlink(missing_ok=True)
    return {"ok": True, "picture_url": "/api/picture.png"}


@app.post("/api/picture/library")
async def picture_library(body: IconBody) -> dict:
    from PIL import Image

    p = icon_path(body.icon_id)
    if not p:
        raise HTTPException(400, "Unknown icon")
    # Upscale the 16x16 icon with nearest-neighbor for crisp pixel-art on the label.
    big = get_config().work_dir / "library_src.png"
    Image.open(p).resize((640, 640), Image.NEAREST).save(big)
    _set_picture(big, "library")
    return {"ok": True, "picture_url": "/api/picture.png"}


class AIBody(BaseModel):
    prompt: str


@app.post("/api/picture/ai")
async def picture_ai(body: AIBody) -> dict:
    if not ai_available():
        raise AIUnavailableError("AI pictures aren't turned on. Use a YouTube picture, upload one, or pick an icon.")

    # generate_image() uses a synchronous, up-to-90s HTTP call. Run it off the
    # event loop so the whole server doesn't freeze while a picture is drawn.
    def _do() -> None:
        img = generate_image(body.prompt.strip(), get_config().work_dir, name="ai_src")
        _set_picture(img, "ai")

    await run_in_threadpool(_do)
    return {"ok": True, "picture_url": "/api/picture.png"}


class CropBody(BaseModel):
    x: float
    y: float
    w: float
    h: float


@app.post("/api/picture/crop")
async def picture_crop(body: CropBody) -> dict:
    draft = get_draft()
    if not draft.picture_source_path or not Path(draft.picture_source_path).exists():
        raise ImageError("There's no picture to adjust yet.")
    draft.picture_path = crop_image(
        draft.picture_source_path,
        (int(body.x), int(body.y), int(body.w), int(body.h)),
        get_config().work_dir,
        name="card_picture",
    )
    return {"ok": True, "picture_url": "/api/picture.png"}


@app.get("/api/picture.png")
async def get_picture():
    draft = get_draft()
    if not draft.picture_path or not Path(draft.picture_path).exists():
        raise HTTPException(404, "No picture yet")
    return FileResponse(draft.picture_path, media_type="image/png")


@app.get("/api/picture/source.png")
async def get_picture_source():
    draft = get_draft()
    if not draft.picture_source_path or not Path(draft.picture_source_path).exists():
        raise HTTPException(404, "No source picture")
    return FileResponse(draft.picture_source_path, media_type="image/png")


# --------------------------------------------------------------------------- #
# Icon library
# --------------------------------------------------------------------------- #
@app.get("/api/icons")
async def get_icons() -> dict:
    return {"icons": list_icons()}


@app.get("/api/icons/{icon_id}.png")
async def get_icon(icon_id: str):
    p = icon_path(icon_id)
    if not p:
        raise HTTPException(404, "Unknown icon")
    return FileResponse(p, media_type="image/png")


# --------------------------------------------------------------------------- #
# Yoto connection
# --------------------------------------------------------------------------- #
class ClientIdBody(BaseModel):
    client_id: str


@app.post("/api/yoto/client-id")
async def set_client_id(body: ClientIdBody) -> dict:
    """One-time setup: save the Yoto Client ID (registered at dashboard.yoto.dev)."""
    from ..settings import get_settings

    cid = body.client_id.strip()
    if not cid:
        raise HTTPException(400, "Please paste a Client ID.")
    get_settings().set("yoto_client_id", cid)
    return {"ok": True, "configured": True}


@app.get("/api/yoto/login")
async def yoto_login() -> dict:
    return {"url": start_login()}


@app.get("/yoto/callback", response_class=HTMLResponse)
async def yoto_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return _callback_page(False, "Sign-in was cancelled. You can close this tab and try again.")
    try:
        finish_login(code, state)
    except Exception as exc:  # noqa: BLE001
        return _callback_page(False, str(exc))
    return _callback_page(True, "Your Yoto account is connected! You can close this tab and go back to Yoto Maker.")


@app.post("/api/yoto/logout")
async def yoto_logout() -> dict:
    logout()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Send to Yoto (background job with progress)
# --------------------------------------------------------------------------- #
def _resolve_icon(track, draft) -> Path | None:
    cfg = get_config()
    if track.icon_id:
        p = icon_path(track.icon_id)
        if p:
            return p
    if draft.picture_path and Path(draft.picture_path).exists():
        return make_device_icon(draft.picture_path, cfg.work_dir, name=f"icon_{track.id}")
    if track.suggested_image_path and Path(track.suggested_image_path).exists():
        return make_device_icon(track.suggested_image_path, cfg.work_dir, name=f"icon_{track.id}")
    return icon_path("music")


@app.post("/api/send")
async def send_to_yoto() -> dict:
    draft = get_draft()
    if not draft.tracks:
        raise SourceError("Add some audio before sending to Yoto.")
    if not draft.card_name.strip():
        raise SourceError("Give your card a name before sending it.")
    # Cheap precheck (token file present) — no client created here, so nothing
    # to leak on the common "not connected yet" path.
    if not connection_status()["connected"]:
        raise NotConnectedError("Please connect your Yoto account first.")

    inputs = [
        TrackInput(audio_path=t.audio_path, title=t.title, icon_path=_resolve_icon(t, draft))
        for t in draft.tracks
    ]
    card_name = draft.card_name.strip()

    def work(update):
        def prog(stage, cur, total, msg):
            pct = int(cur / max(total, 1) * 100)
            update(stage, pct, msg)

        # One client per send, always closed — no connection-pool leak in the
        # long-lived tray process.
        with YotoClient() as client:
            result = client.create_card(card_name, inputs, progress=prog)
        return {"content_id": result.content_id, "title": result.title}

    job_id = get_jobs().start(work)
    return {"job_id": job_id}


# --------------------------------------------------------------------------- #
# Label PDF
# --------------------------------------------------------------------------- #
@app.post("/api/label")
async def make_label() -> dict:
    draft = get_draft()
    if not draft.tracks:
        raise SourceError("Add some audio before making a label.")
    cfg = get_config()
    label_tracks = [
        LabelTrack(title=t.title, icon_path=_resolve_icon(t, draft)) for t in draft.tracks
    ]
    out = cfg.work_dir / "label.pdf"
    generate_label_pdf(
        out,
        card_name=draft.card_name or "My Yoto Card",
        tracks=label_tracks,
        image_path=draft.picture_path,
    )
    return {"ok": True, "label_url": "/api/label.pdf"}


@app.get("/api/label.pdf")
async def get_label():
    out = get_config().work_dir / "label.pdf"
    if not out.exists():
        raise HTTPException(404, "No label yet")
    return FileResponse(out, media_type="application/pdf", filename="yoto-label.pdf")


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str) -> dict:
    job = get_jobs().get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.view()


# --------------------------------------------------------------------------- #
# UI + callback page
# --------------------------------------------------------------------------- #
def _callback_page(ok: bool, message: str) -> HTMLResponse:
    color = "#2e7d32" if ok else "#c62828"
    icon = "✅" if ok else "⚠️"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Yoto Maker</title>
<style>body{{font-family:system-ui,Segoe UI,Arial;background:#f5f3fb;display:flex;
min-height:100vh;align-items:center;justify-content:center;margin:0}}
.card{{background:#fff;padding:40px 48px;border-radius:18px;box-shadow:0 10px 40px rgba(80,60,140,.15);
text-align:center;max-width:420px}}h1{{color:{color};font-size:22px}}p{{color:#444;font-size:16px;line-height:1.5}}</style>
</head><body><div class="card"><div style="font-size:52px">{icon}</div>
<h1>{'Connected!' if ok else 'Not connected'}</h1><p>{message}</p></div></body></html>"""
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
async def index():
    ensure_library()  # make sure icons exist before the UI asks for them
    return FileResponse(STATIC_DIR / "index.html")


# Static assets (styles.js/css). Mounted last so API routes take precedence.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass
