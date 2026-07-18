# 🎵 Yoto Maker

Turn audio from **YouTube** or a **file on your computer** into a card for your
**Yoto player**, and print a matching **label** (picture + track names) — all
from one simple screen in your web browser.

Built to be usable by someone with **little computer knowledge**. No typing
commands, no technical setup.

> 📖 **Just want to install and use it?** Jump to
> **[docs/INSTALL-FOR-MOM.md](docs/INSTALL-FOR-MOM.md)** — a step-by-step guide
> with no technical words.

---

## What it does

1. **Add audio** — paste a YouTube link, or choose an audio file.
2. **Give it a name and a picture** — used on the printed label and the Yoto screen.
3. **Send it to your Yoto** — signs into your Yoto account and uploads it for you.
4. **Print the label** — a ready-to-print page with the picture and track names.

## Status

🚧 Version 0.1 (first release). See [docs/DESIGN.md](docs/DESIGN.md) for the full design.

## For developers

- Stack: Python + FastAPI (local web app), `yt-dlp` + `ffmpeg`, `reportlab`, `pystray`.
- See [docs/DEVELOPERS.md](docs/DEVELOPERS.md) for running from source, testing, and packaging.
- See [docs/SETUP-YOTO-CONNECTION.md](docs/SETUP-YOTO-CONNECTION.md) for the one-time Yoto Client ID registration.

## License

MIT — see [LICENSE](LICENSE).
