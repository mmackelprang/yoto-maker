"""Frozen-app entry point used by PyInstaller.

Kept tiny so PyInstaller's analysis starts from a clean module. Two important
things happen before the real app starts:

1. In a **windowed** build, ``sys.stdout``/``sys.stderr`` are ``None``. Some
   libraries (notably yt-dlp) write to stderr during setup and crash on ``None``.
   We replace null streams with a harmless sink.
2. ``multiprocessing.freeze_support()`` guards against any dependency that spawns
   a child process re-running the bootloader.
"""
import io
import multiprocessing
import os
import sys


def _ensure_streams() -> None:
    devnull = open(os.devnull, "w", encoding="utf-8", errors="ignore")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None or not hasattr(stream, "write"):
            setattr(sys, name, devnull)
    if getattr(sys, "stdin", None) is None:
        sys.stdin = io.StringIO("")


_ensure_streams()

from yoto_maker.main import main  # noqa: E402

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
