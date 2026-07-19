"""Self-update: notice a newer GitHub release and install it in place.

Windows can't overwrite a running ``.exe``, so updating hands off to a tiny
batch script: the app downloads the new exe next to the current one, launches
the swapper (detached), then exits. The swapper waits for the lock to release,
atomically renames the new file over the old one, and relaunches the app.

Only active in the packaged Windows build; running from source just reports that
a newer release exists (with a link).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

from . import __version__
from .config import get_config

REPO = "mmackelprang/yoto-maker"
_LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"

_DETACHED = 0x00000008  # DETACHED_PROCESS
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

_MIN_EXE_BYTES = 10 * 1024 * 1024  # a real build is ~100MB; guard against truncated downloads
_cache: dict = {"ts": 0.0, "data": None}


class UpdateError(RuntimeError):
    """User-friendly update failure."""


# --------------------------------------------------------------------------- #
# Version comparison
# --------------------------------------------------------------------------- #
def parse_version(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def can_self_update() -> bool:
    return sys.platform.startswith("win") and bool(getattr(sys, "frozen", False))


def _current_exe() -> Path | None:
    return Path(sys.executable) if getattr(sys, "frozen", False) else None


# --------------------------------------------------------------------------- #
# Checking for updates
# --------------------------------------------------------------------------- #
def check_for_update(force: bool = False) -> dict:
    """Return update info. Cached for an hour; never raises (offline → no update)."""
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"] < 3600):
        return _cache["data"]

    result = {
        "current": __version__,
        "latest": None,
        "update_available": False,
        "release_url": RELEASES_PAGE,
        "download_url": None,
        "can_self_update": can_self_update(),
    }
    try:
        # Test/override hooks so the flow can be exercised without a real release.
        forced_tag = os.environ.get("YOTO_LATEST_VERSION")
        if forced_tag:
            tag = forced_tag
            download_url = os.environ.get("YOTO_UPDATE_URL")
        else:
            resp = httpx.get(
                _LATEST_API,
                timeout=10,
                headers={"Accept": "application/vnd.github+json"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
            tag = data.get("tag_name", "") or ""
            result["release_url"] = data.get("html_url", RELEASES_PAGE)
            download_url = None
            for asset in data.get("assets", []):
                if str(asset.get("name", "")).lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break
            download_url = os.environ.get("YOTO_UPDATE_URL", download_url)

        if tag:
            result["latest"] = tag.lstrip("v")
            result["download_url"] = download_url
            result["update_available"] = is_newer(tag, __version__)
    except Exception:
        pass  # offline or API error → simply no update offered

    _cache.update(ts=now, data=result)
    return result


# --------------------------------------------------------------------------- #
# Applying an update
# --------------------------------------------------------------------------- #
def _download(url: str, dest: Path, progress=None) -> None:
    try:
        with httpx.stream("GET", url, timeout=None, follow_redirects=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0) or 0)
            done = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes(256 * 1024):
                    fh.write(chunk)
                    done += len(chunk)
                    if progress and total:
                        progress(int(done / total * 100))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise UpdateError(
            "We couldn't download the update. Please check your internet and try again, "
            "or download it from the website."
        ) from exc


def _verify(path: Path) -> None:
    if not path.exists() or path.stat().st_size < _MIN_EXE_BYTES:
        path.unlink(missing_ok=True)
        raise UpdateError("The downloaded update looked incomplete. Please try again.")


def _write_swapper(new_exe: Path, current_exe: Path) -> Path:
    """Write the batch that waits for the lock, swaps, and relaunches."""
    update_dir = get_config().data_dir / "update"
    update_dir.mkdir(parents=True, exist_ok=True)
    bat = update_dir / "swap.bat"
    # move (same-dir atomic rename) fails only while the exe is locked; retry up
    # to ~120s, then give up cleanly (old exe stays intact) and relaunch it.
    # Relaunch via PowerShell Start-Process: launching a windowed one-file exe
    # with `start` from a detached, window-less cmd gives it a broken session and
    # it hangs in early startup. Start-Process spawns it cleanly in the user
    # session instead.
    script = f"""@echo off
setlocal
set /a n=0
:retry
move /y "{new_exe}" "{current_exe}" >nul 2>&1
if not errorlevel 1 goto done
set /a n+=1
if %n% geq 120 goto giveup
timeout /t 1 /nobreak >nul
goto retry
:giveup
del "{new_exe}" >nul 2>&1
:done
powershell -NoProfile -Command "Start-Process -FilePath '{current_exe}'"
(goto) 2>nul & del "%~f0"
"""
    bat.write_text(script, encoding="ascii")
    return bat


def _clean_child_env() -> dict:
    """Environment for the relaunched app, with PyInstaller's onefile runtime
    vars stripped. A fresh onefile .exe that inherits the *parent* frozen app's
    ``_PYI_*`` / ``_MEIPASS`` vars references the parent's soon-deleted temp dir
    and hangs in its bootloader. Scrubbing them makes the child extract cleanly.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if not (k.startswith("_PYI") or k.startswith("_MEIPASS") or k == "_MEIPASS2")
    }


def _launch(bat: Path, cwd: Path) -> None:
    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        cwd=str(cwd),
        creationflags=_DETACHED | _NO_WINDOW,
        close_fds=True,
        env=_clean_child_env(),
    )


def apply_update(download_url: str, progress=None) -> dict:
    """Download the update, launch the swapper, and schedule this app to exit."""
    exe = _current_exe()
    if not exe:
        raise UpdateError("Updates only work in the installed app. Please download the new version.")
    if not download_url:
        raise UpdateError("No download was found for the latest version.")

    # Download next to the current exe so the swap is an atomic same-folder rename.
    new_exe = exe.with_name(exe.stem + ".update.exe")
    new_exe.unlink(missing_ok=True)
    _download(download_url, new_exe, progress)
    _verify(new_exe)

    bat = _write_swapper(new_exe, exe)
    _launch(bat, exe.parent)

    # Let the HTTP response reach the browser, then exit so the .exe unlocks and
    # the swapper can rename the new file into place.
    threading.Timer(2.5, lambda: os._exit(0)).start()
    return {"restarting": True}
