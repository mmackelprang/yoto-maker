"""Entry point for Yoto Maker.

Normal use (installed app): start the local server, open the browser, and sit in
the system tray until the user quits. Includes single-instance behavior: if the
app is already running, just open the browser to it and exit.

Flags (mostly for development/testing):
  --no-browser   don't auto-open the browser
  --no-tray      run the server in the foreground (Ctrl+C to stop)
  --check        print a tool/connection self-check and exit
"""
from __future__ import annotations

import argparse
import sys
import time
import webbrowser

from . import APP_NAME, __version__
from .config import get_config
from .images.library import ensure_library
from .logging_setup import setup_logging
from .server.runner import AlreadyRunningError, start_server


def _self_check() -> int:
    from .tools import check_tools
    from .yoto import connection_status

    cfg = get_config()
    tools = check_tools()
    yoto = connection_status()
    print(f"{APP_NAME} v{__version__} self-check")
    print(f"  data dir : {cfg.data_dir}")
    print(f"  ffmpeg   : {'OK ' + str(tools.ffmpeg) if tools.ffmpeg else 'MISSING'}")
    print(f"  yt-dlp   : {'OK' if tools.yt_dlp else 'MISSING'}")
    print(f"  Yoto ID  : {'configured' if yoto['configured'] else 'NOT configured (set YOTO_CLIENT_ID)'}")
    print(f"  Yoto auth: {'connected' if yoto['connected'] else 'not connected'}")
    return 0 if tools.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yoto-maker", description=f"{APP_NAME} — {__version__}")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-tray", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--port", type=int, default=None,
                        help="Run on a non-default port (dev/testing; Yoto sign-in needs the default 8777).")
    args = parser.parse_args(argv)

    cfg = get_config()
    cfg.ensure_dirs()
    setup_logging()
    ensure_library()

    if args.check:
        return _self_check()

    port = args.port or cfg.port

    try:
        handle = start_server(wait=True, port=port)
    except AlreadyRunningError as running:
        # Another copy is already up — just open it.
        if not args.no_browser:
            webbrowser.open(str(running))
        print(f"{APP_NAME} is already running at {running}")
        return 0

    if not args.no_browser:
        webbrowser.open(handle.url)

    if args.no_tray:
        print(f"{APP_NAME} running at {handle.url} — press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            handle.stop()
            return 0

    # Normal mode: tray icon keeps the app alive.
    try:
        from .tray import run_tray

        run_tray(handle.url, handle.stop)
    except Exception:
        # No tray available (headless) — fall back to foreground.
        print(f"{APP_NAME} running at {handle.url} — press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            handle.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
