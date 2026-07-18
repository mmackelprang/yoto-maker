# Yoto Maker — Design Spec

**Status:** Approved (2026-07-17)
**Author:** Mark Mackelprang (with Claude)

## 1. Purpose

A dead-simple Windows app that lets a **non-technical person** turn audio from
various sources into a **Yoto "Make Your Own" (MYO) card**, and print a matching
**physical label** (picture + card name + track list).

The primary user is "Mom" — she has little computer knowledge. Every design
decision favors *her* ease of use over developer convenience.

## 2. What the user experiences

A single friendly wizard in her web browser (served from a local app that
auto-starts). No jargon, no file management, no server to think about.

1. **Open** — Start-menu icon / auto-opens on login → browser shows "🎵 Make a Yoto Card".
2. **Add audio** — big buttons: *"Paste a YouTube link"* or *"Choose a file"*. She can add several items to one card.
3. **Name the tracks** — each item auto-fills a title (YouTube title / filename) she can edit.
4. **Name the card + pick a picture** — defaults to the auto-grabbed thumbnail; tabs for *Upload*, *Icon library*, *AI-generate (optional)*.
5. **Connect Yoto** (first time only) — one button → browser sign-in → remembered forever.
6. **Send to Yoto** — one big button, honest progress (uploading → transcoding → building playlist → done).
7. **Print the label** — opens a ready-to-print PDF (picture + card name + track list).

## 3. Architecture & stack

A small **Python** local app (chosen because yt-dlp is Python-native and the
audio/PDF/image libraries are mature):

- **Local web server** — FastAPI + uvicorn, serving a vanilla-JS browser UI on `127.0.0.1`.
- **Tray / auto-start helper** — `pystray`; starts the server on login, opens the browser, lives in the system tray.
- **Bundled tools** — `ffmpeg` + `yt-dlp` shipped with the app (nothing for her to install).
- **Packaging** — PyInstaller → one Windows installer; Start-menu + desktop shortcut.

Data flow: `Source adapter → normalized audio (ffmpeg) → picture/icon → Yoto client (upload/transcode/content) → label PDF`.

### Module layout

```
yoto_maker/
  config.py            # paths, settings, token/store locations
  tools.py             # locate/validate ffmpeg + yt-dlp
  audio/normalize.py   # ffmpeg → Yoto-friendly audio + probe metadata
  sources/
    base.py            # SourceAdapter protocol; SourceResult dataclass
    youtube.py         # yt-dlp: audio + thumbnail + title
    audiofile.py       # local mp3/m4a/wav: audio + embedded art + tags
  images/
    picture.py         # pick/normalize the label image (4 methods)
    icon.py            # 16x16 device icon (library / pixelate / AI)
  yoto/
    auth.py            # OAuth2 Authorization-Code + PKCE, token cache
    client.py          # upload URL → PUT → poll transcode → POST /content
    models.py          # typed request/response shapes
  labels/pdf.py        # reportlab label PDF
  server/app.py        # FastAPI routes + static UI
  server/static/       # index.html, app.js, styles.css, icons/
  tray.py              # system tray + browser launch
  main.py              # entry point
```

## 4. Source layer (pluggable)

`SourceAdapter` protocol so v1 ships two and later ones drop in without touching
downstream code.

- **v1:** `YouTubeAdapter` (yt-dlp → best audio + thumbnail + title), `AudioFileAdapter` (local mp3/m4a/wav → tags + embedded art).
- **Fast-follows (designed-for, not built):** `VideoFileAdapter`, `AudiobookAdapter` (M4B/MP3-folder chapter split).

Every adapter returns the same `SourceResult`:
`{ audio_path, suggested_title, suggested_image_path | None, duration_s, source_kind }`.

## 5. Picture & on-device icon

The **printed label** uses a **full-resolution image**; the Yoto screen icon is
**16×16 pixel art** — a downscaled photo looks like mush, so they are handled
separately.

- **Label picture** — full image from any of 4 methods.
- **Device 16×16 icon** — default to a **Yoto/curated pixel icon**, or auto-pixelate the chosen image.
- **Four picture methods:** (1) auto-grab from source, (2) upload own image, (3) pick from a bundled kid-friendly icon library, (4) **AI-generate (optional)**.

**AI is optional and OFF by default.** The app is 100% functional with methods
1–3 and **no keys or config**. AI-generate only appears/enables when an image
API key is present. Initial real-world use is explicitly *without* AI.

## 6. Yoto delivery

- **Auth:** OAuth2 Authorization-Code + PKCE, loopback redirect. One "Connect" click → browser sign-in → refresh token cached (silent thereafter). A public **Client ID** (registered once at dashboard.yoto.dev) ships with the app; PKCE means no secret.
  - Endpoints: `https://login.yotoplay.com/authorize`, `https://login.yotoplay.com/oauth/token`. Scopes: `user:content:manage offline_access`.
- **Upload:** `GET /media/transcode/audio/uploadUrl` → `PUT` file → poll `GET /media/upload/{id}/transcoded` until `transcodedSha256` → `POST /content` (chapters/tracks referencing `yoto:#<sha>`, per-track `display.icon16x16`).
- **Card binding caveat:** content lands in her account automatically. Binding a *brand-new blank card* the first time may need one tap in the Yoto app (guided step). Updating an already-linked card is fully automated. We attempt to minimize/eliminate the tap during implementation.

## 7. Label generator

A printable **PDF**: card-sized front label (picture + card name, large/clear) +
a small track list, laid out to print on plain or sticker paper and trimmed to
the MYO card. Generated with reportlab; opens in her browser's PDF viewer for
one-click printing.

## 8. Guardrails for a non-technical user (the whole point)

- **Plain-language errors only** — "We couldn't reach YouTube — check your internet and try again," never a stack trace.
- **Auto-retry** transient failures; **self-update yt-dlp** (YouTube changes often break old versions).
- **Hidden log file** for the developer; she never sees it.
- **Nothing to install, nothing to configure** — binaries bundled, sensible defaults everywhere.
- **Offline/degraded modes** are explained in plain words, not error codes.

## 9. Testing strategy

- **Unit tests** for each source adapter (mocked yt-dlp/network), the Yoto client (mocked HTTP), the label generator, the icon generator, the audio normalizer.
- **Real integration** where possible without secrets: run `ffmpeg` on a generated tone; generate a real label PDF; (network-permitting) a real yt-dlp metadata probe on a Creative-Commons video.
- **Yoto API** covered by mocked request/response tests against the documented shapes (no account needed); a `--check` connection self-test for when the Client ID exists.
- **UAT:** drive the browser wizard end-to-end in demo mode.

## 10. Out of scope for v1 (YAGNI)

Video files, audiobooks, Mac packaging, multiple users/accounts, cloud hosting,
editing existing cards, Audible/DRM (cannot be legally stripped).

## 11. Legal / ToS notes

- Downloading YouTube audio is against YouTube's ToS; acceptable for personal/family use at the user's discretion — surfaced honestly in docs.
- Audible/other DRM audiobooks are explicitly **not** supported.
