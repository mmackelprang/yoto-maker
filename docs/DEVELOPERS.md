# Developer guide

## Overview

Yoto Maker is a local FastAPI web app with a vanilla-JS browser UI, packaged into
a single Windows `.exe` with PyInstaller. It turns YouTube links / audio files
into a Yoto Make-Your-Own card and a printable label.

See [DESIGN.md](DESIGN.md) for the full architecture and rationale.

```
yoto_maker/
  config.py          paths, Client-ID resolution
  settings.py        JSON prefs store
  tools.py           locate ffmpeg / yt-dlp
  logging_setup.py   rotating file log
  autostart.py       optional Windows Startup shortcut
  audio/normalize.py ffmpeg probe + transcode
  sources/           SourceAdapter + youtube + audiofile
  images/            label picture, 16x16 icon, icon library, optional AI
  yoto/              OAuth2 PKCE auth, upload client, content models
  labels/pdf.py      reportlab label
  server/            FastAPI app, draft state, job runner, static UI
  tray.py, main.py   tray + entry point
packaging/           PyInstaller spec, launcher, icon, ffmpeg vendor
tests/               pytest suite
```

## Run from source

Requires Python 3.11+ and `ffmpeg` on PATH.

```bash
python -m venv .venv
.venv/Scripts/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# optional: your Yoto client id (see docs/SETUP-YOTO-CONNECTION.md)
export YOTO_CLIENT_ID=...         # PowerShell: $env:YOTO_CLIENT_ID="..."

python -m yoto_maker              # opens the browser + tray
python -m yoto_maker --no-tray --no-browser   # headless dev server on :8777
python -m yoto_maker --check      # tool + connection self-check
```

### Testing UI changes in a browser — clear the cache first

The static assets under `yoto_maker/server/static/` are served **without cache-busting**, so a browser will reuse a
stale `app.js` / `style.css` straight across a rebuild. This reliably produces *false* UI failures: a CSS custom
property that reads empty, a control that behaves like its previous version, a focus ring that looks like the UA
default.

Before measuring anything in the browser, clear the cache and keep it disabled — `Network.clearBrowserCache` plus
`Network.setCacheDisabled {cacheDisabled: true}` over CDP, or DevTools open with "Disable cache" ticked.

**The tell is a size mismatch:** compare the byte count of the served asset against the file on disk. If they
disagree, you are testing a build that no longer exists — clear the cache and re-run the check.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

The suite mocks all Yoto network calls, so no account is needed. Tests
that need ffmpeg self-skip if it's missing.

## Optional AI pictures

Off by default. Set a key to enable the AI tab:

```bash
export YOTO_MAKER_AI_KEY=sk-...   # or OPENAI_API_KEY
```

Everything else works with no key.

## Building the Windows .exe

```bash
pip install pyinstaller
python packaging/make_icon.py                    # regenerate app.ico (committed)
# stage ffmpeg.exe AND ffprobe.exe for bundling (any recent static build):
#   copy ffmpeg.exe  -> packaging/vendor/ffmpeg.exe
#   copy ffprobe.exe -> packaging/vendor/ffprobe.exe   (needed by SponsorBlock)
pyinstaller packaging/YotoMaker.spec --distpath packaging/dist --workpath packaging/build --noconfirm
```

Output: `packaging/dist/YotoMaker.exe` — a one-file, windowed build that bundles
the UI, the pixel-icon library, `ffmpeg.exe` + `ffprobe.exe`, and all of `yt_dlp`.

### Publishing a release

There is no CI. A release is these five steps in order, and **the version bump is
not one of them** — bumping `pyproject.toml` and `yoto_maker/__init__.py` happens
in the feature PR, and on its own ships nothing.

1. **Verify** — on `main`, clean, `pytest -q` green, `docs/RELEASE_NOTES.md`
   opens with the version being cut and its section covers everything in it.
2. **Tag the merge commit** and push it:
   ```bash
   git tag v0.1.9 <merge-sha> && git push origin v0.1.9
   ```
3. **Build** (see above). Stage `packaging/vendor/ffmpeg.exe` **and**
   `ffprobe.exe` first — they are gitignored and absent in a fresh checkout.
4. **Publish:**
   ```bash
   gh release create v0.1.9 packaging/dist/YotoMaker.exe \
     --title "Yoto Maker v0.1.9" --notes-file docs/RELEASE_NOTES.md
   ```
5. **Verify the release exists**, because steps 2–4 can each half-succeed:
   ```bash
   gh release view v0.1.9 --json tagName,assets \
     -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
   ```
   Expected: `v0.1.9 -> YotoMaker.exe`. Anything else — including a release with
   no asset — means users get no update.

**`updater.py` reads GitHub releases, not tags and not `pyproject.toml`.** A
bumped version with no release is invisible to every installed copy: the app
correctly reports "no update available" because there is nothing to download.
This is what happened to v0.1.9, and the symptom is indistinguishable from the
app being up to date. If a user says "I'm not getting the update", run step 5
first.

The end-user install guide ([INSTALL-FOR-MOM.md](INSTALL-FOR-MOM.md)) points at
`releases/latest`, so an un-created release also leaves that link on the previous
version.

## Notes

- **Fixed port 8777** keeps the OAuth redirect URL stable; the app is
  single-instance (a second launch just opens the browser to the first).
- **yt-dlp updates often** as YouTube changes; bump it in `requirements.txt` and
  rebuild when downloads start failing.
- Runtime data (tokens, logs, work files) live in `%LOCALAPPDATA%\YotoMaker` and
  are never committed.
- The unsigned `.exe` triggers Windows SmartScreen once ("More info → Run
  anyway"). Code signing would remove this but needs a certificate.
