"""Optional 'start automatically with Windows' support (no admin needed).

Creates/removes a shortcut in the user's Startup folder pointing at the app. Only
meaningful for the packaged .exe; in a dev checkout it's a no-op. Uses PowerShell
to author the .lnk so we don't need pywin32.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0


def _startup_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _shortcut_path() -> Path:
    return _startup_dir() / "Yoto Maker.lnk"


def _target_exe() -> Path | None:
    """The .exe to launch, only when running as a frozen build."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def _ps_quote(value) -> str:
    """Quote a value as a PowerShell single-quoted string literal, escaping any
    embedded single quotes (e.g. a user path like C:\\Users\\O'Brien\\...)."""
    return "'" + str(value).replace("'", "''") + "'"


def is_supported() -> bool:
    return sys.platform.startswith("win") and _target_exe() is not None


def is_enabled() -> bool:
    return _shortcut_path().exists()


def enable() -> bool:
    exe = _target_exe()
    if not exe:
        return False
    _startup_dir().mkdir(parents=True, exist_ok=True)
    lnk = _shortcut_path()
    ps = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({_ps_quote(lnk)});"
        f"$s.TargetPath={_ps_quote(exe)};$s.WorkingDirectory={_ps_quote(exe.parent)};"
        f"$s.Description='Yoto Maker';$s.Save()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, creationflags=_NO_WINDOW, check=True,
        )
        return lnk.exists()
    except Exception:
        return False


def disable() -> bool:
    try:
        _shortcut_path().unlink(missing_ok=True)
        return True
    except OSError:
        return False
