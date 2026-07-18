"""Make the tiny 16x16 pixel-art icon shown on the Yoto player screen.

A downscaled photo looks like mush at 16x16, so we do a deliberate pixel-art
reduction: crop to square, shrink with a box filter, and (optionally) boost
saturation/contrast so the shape still reads on the little screen.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ICON_SIZE = 16


def make_device_icon(source: str | Path, out_dir: str | Path, *, name: str = "icon16") -> Path:
    """Produce a 16x16 PNG suitable for Yoto's ``display.icon16x16``.

    Works from any image — a thumbnail, an uploaded photo, or a library icon
    (which is already 16x16 and passes through crisply).
    """
    source = Path(source)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        # Center-crop to square so nothing important is squashed.
        im = ImageOps.fit(im, (ICON_SIZE * 8, ICON_SIZE * 8), Image.LANCZOS)
        # Punch up color/contrast a touch so it reads at tiny size.
        im = ImageEnhance.Color(im).enhance(1.25)
        im = ImageEnhance.Contrast(im).enhance(1.1)
        # Reduce to 16x16 with a box filter for clean pixels.
        im = im.resize((ICON_SIZE, ICON_SIZE), Image.BOX)
        out = out_dir / f"{name}.png"
        im.save(out, format="PNG")
        return out
