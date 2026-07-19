"""Render emoji ("emoticons") to images for the label + Yoto-screen icon.

Uses the system color-emoji font (Segoe UI Emoji on Windows). Each emoji is drawn
centered on a soft rounded-square tile so it looks good on the label and when
shrunk to the 16x16 device icon.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .picture import ImageError

# A curated, kid-friendly set. Kept to widely-supported single/simple emoji.
EMOJI_SET: list[str] = [
    # faces & people
    "😀", "😃", "😄", "😁", "😊", "🥰", "😎", "🤩", "😴", "🤠", "👶", "🧑‍🚀",
    # animals
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
    "🐷", "🐸", "🐵", "🐔", "🐧", "🦄", "🐴", "🦋", "🐝", "🐙", "🐠", "🐳",
    "🦕", "🦖",
    # nature
    "🌟", "⭐", "🌈", "☀️", "🌙", "❄️", "🔥", "🌸", "🌻", "🍀", "🌳",
    # things & fun
    "🚀", "🚗", "🚂", "✈️", "⛵", "🎈", "🎁", "🎵", "🎸", "🥁", "🎨", "📚",
    "⚽", "🏀", "🎮", "🧸", "🍎", "🍓", "🍦", "🍭", "🎂",
    # hearts
    "❤️", "💜", "💙", "💚", "💛",
]

_BG = (239, 234, 251)  # soft lavender tile, matches the app


@lru_cache(maxsize=1)
def _emoji_font_path() -> str | None:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for candidate in (
        Path(windir) / "Fonts" / "seguiemj.ttf",   # Segoe UI Emoji (Windows)
        Path("/System/Library/Fonts/Apple Color Emoji.ttc"),  # macOS
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),  # Linux
    ):
        if candidate.exists():
            return str(candidate)
    return None


def emoji_supported() -> bool:
    return _emoji_font_path() is not None


def list_emojis() -> list[str]:
    return list(EMOJI_SET)


def render_emoji(emoji: str, out_dir: str | Path, *, name: str = "emoji_pic", size: int = 512) -> Path:
    """Render ``emoji`` onto a soft rounded-square tile; return the PNG path."""
    font_path = _emoji_font_path()
    if not font_path:
        raise ImageError("Emoticons aren't available on this computer.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype(font_path, int(size * 0.72))
        # Opaque background fills the whole square (no transparent corners that
        # would turn black on RGB conversion). The label/preview round it.
        im = Image.new("RGBA", (size, size), (*_BG, 255))
        d = ImageDraw.Draw(im)
        bbox = d.textbbox((0, 0), emoji, font=font, embedded_color=True)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), emoji, font=font, embedded_color=True)
        out = out_dir / f"{name}.png"
        im.convert("RGB").save(out, "PNG")
        return out
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError("We couldn't draw that emoticon. Please try another one.") from exc
