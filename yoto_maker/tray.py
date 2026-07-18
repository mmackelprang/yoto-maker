"""System-tray icon so the app feels like a normal Windows program.

Shows a small menu: *Open Yoto Maker* and *Quit*. If a tray can't be created
(no GUI / headless), the caller falls back to running the server in the
foreground.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path

from PIL import Image


def _tray_image() -> Image.Image:
    """Use the bundled music icon, upscaled, as the tray glyph."""
    from .config import get_config

    icon = get_config().icons_dir / "music.png"
    if icon.exists():
        return Image.open(icon).resize((64, 64), Image.NEAREST).convert("RGBA")
    img = Image.new("RGBA", (64, 64), (124, 92, 214, 255))
    return img


def run_tray(url: str, on_quit) -> None:
    """Blocking: show the tray icon until the user chooses Quit.

    ``on_quit`` is called to stop the server before the process exits.
    """
    import pystray
    from pystray import MenuItem as Item

    from . import autostart

    def _open(icon, item):  # noqa: ANN001
        webbrowser.open(url)

    def _toggle_autostart(icon, item):  # noqa: ANN001
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()

    def _quit(icon, item):  # noqa: ANN001
        try:
            on_quit()
        finally:
            icon.stop()

    menu_items = [Item("Open Yoto Maker", _open, default=True)]
    if autostart.is_supported():
        menu_items.append(
            Item("Start with Windows", _toggle_autostart, checked=lambda item: autostart.is_enabled())
        )
    menu_items.append(Item("Quit", _quit))

    icon = pystray.Icon("yoto_maker", _tray_image(), "Yoto Maker", menu=pystray.Menu(*menu_items))
    icon.run()
