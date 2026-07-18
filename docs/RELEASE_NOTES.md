# Yoto Maker v0.1.0

The first release — turn audio into a Yoto card and print a matching label, from
one simple screen. Built to be usable by someone with little computer knowledge.

## 📥 Install (Windows)

1. Download **`YotoMaker.exe`** below.
2. Double-click it. If Windows shows *“Windows protected your PC”*, click
   **More info → Run anyway** (the app is new and unsigned).
3. It opens in your web browser automatically.

👉 Full picture-by-picture guide:
**[INSTALL-FOR-MOM.md](https://github.com/mmackelprang/yoto-maker/blob/main/docs/INSTALL-FOR-MOM.md)**

## ✨ What it does

- **Add audio** from a **YouTube link** or an **audio file** (MP3/M4A/WAV…).
- **Name the card** and give it a **picture** — from the audio, your own upload,
  or a built-in icon library.
- **Send it to your Yoto** account over Yoto's official API (one-time sign-in).
- **Print a label** with the picture and track names.
- Each track gets a little **pixel icon** on the Yoto screen.

## ⚙️ One-time setup for the Yoto connection

Sending to Yoto needs a free **Client ID** from
[dashboard.yoto.dev](https://dashboard.yoto.dev). It takes ~5 minutes and only
the person setting up needs to do it — see
**[SETUP-YOTO-CONNECTION.md](https://github.com/mmackelprang/yoto-maker/blob/main/docs/SETUP-YOTO-CONNECTION.md)**.
Adding audio, pictures, and printing labels all work without it.

## 📝 Notes

- Windows 10/11 only for now.
- Downloading YouTube audio is at your discretion (personal/family use).
- Audible/DRM audiobooks are not supported (they can't be legally converted).
- ffmpeg + yt-dlp are bundled — nothing else to install.

## 🔒 What's verified

- Real YouTube download + thumbnail, audio-file import (with tags/art), icon
  library, per-track icons, and label PDF are all verified end-to-end.
- The Yoto upload flow is implemented against Yoto's documented API and covered
  by tests with mocked responses; live upload needs your Client ID (above).
