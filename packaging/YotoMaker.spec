# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a one-file, windowed Yoto Maker.exe.

Bundles: the static UI, the pixel-icon library, ffmpeg.exe (under vendor/), and
the whole yt_dlp package (many lazily-imported extractors). No console window.
"""
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(os.path.dirname(SPECPATH)))

# yt-dlp pulls in hundreds of extractor modules lazily — collect everything.
ytd_datas, ytd_binaries, ytd_hidden = collect_all("yt_dlp")

datas = [
    (os.path.join(ROOT, "yoto_maker", "server", "static"), os.path.join("yoto_maker", "server", "static")),
    (os.path.join(ROOT, "packaging", "vendor", "ffmpeg.exe"), "vendor"),
    # ffprobe is required by yt-dlp's SponsorBlock/ModifyChapters step to read
    # media duration for some audio formats — bundle it too, not just ffmpeg.
    (os.path.join(ROOT, "packaging", "vendor", "ffprobe.exe"), "vendor"),
]
datas += ytd_datas
datas += collect_data_files("certifi")

hiddenimports = list(ytd_hidden)
hiddenimports += collect_submodules("uvicorn")
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "pystray._win32",
    "PIL._tkinter_finder",
]

a = Analysis(
    [os.path.join(ROOT, "packaging", "yoto_maker_launch.py")],
    pathex=[ROOT],
    binaries=ytd_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "PyInstaller"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YotoMaker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,           # no console window
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, "packaging", "app.ico"),
)
