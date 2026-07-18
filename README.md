<div align="center">

# 🎵 Yoto Maker

**Turn audio from YouTube or a file into a card for your Yoto player — and print a matching label — from one simple screen in your web browser.**

Built to be usable by someone with **little computer knowledge**. No commands, no technical setup.

</div>

---

## 📥 Just want to use it?

1. Download **`YotoMaker.exe`** from the **[latest release](https://github.com/mmackelprang/yoto-maker/releases/latest)**.
2. Double-click it (on the first run, Windows may say *“Windows protected your PC”* → **More info → Run anyway**).
3. It opens in your browser. Follow the four steps on screen.

👉 **[Step-by-step guide with no technical words → docs/INSTALL-FOR-MOM.md](docs/INSTALL-FOR-MOM.md)**

---

## What it does

| Step | What happens |
|------|--------------|
| **1. Add audio** | Paste a **YouTube link** or choose an **audio file** (MP3/M4A/WAV…). Add as many as you like. |
| **2. Name & picture** | Name the card and pick a picture — from the audio, your own image, or a fun icon. |
| **3. Send to Yoto** | Signs into your Yoto account (once) and uploads the card for you. |
| **4. Print a label** | A ready-to-print card with the picture and track names. |

Each track also gets a little **16×16 pixel icon** on the Yoto player screen.

## One-time Yoto setup

Sending to Yoto needs a free **Client ID** from [dashboard.yoto.dev](https://dashboard.yoto.dev) (about 5 minutes, once).
See **[docs/SETUP-YOTO-CONNECTION.md](docs/SETUP-YOTO-CONNECTION.md)**. Everything else (audio, pictures, labels) works without it.

## For developers

Python + FastAPI local web app · `yt-dlp` + `ffmpeg` · `reportlab` · packaged with PyInstaller.

- **[docs/DESIGN.md](docs/DESIGN.md)** — architecture & rationale
- **[docs/DEVELOPERS.md](docs/DEVELOPERS.md)** — run from source, test, build the `.exe`

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python -m yoto_maker          # opens the app
pytest -q                     # 48 tests
```

## Status & scope

**v0.1** — Windows. Sources: YouTube + audio files (video files and audiobooks are designed-for, not yet built).
AI-generated pictures are optional and off by default.

## Honest notes

- Downloading YouTube audio is at your discretion (personal/family use).
- Audible/DRM audiobooks aren't supported — they can't be legally converted.
- The `.exe` is unsigned, so Windows SmartScreen warns once.

## License

[MIT](LICENSE) © 2026 Mark Mackelprang
