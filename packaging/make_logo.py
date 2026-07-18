"""Render the Yoto Maker logo as hosted PNGs (from the same design as app.ico).

Draws the white music note on a purple rounded square at high resolution
(supersampled for smooth edges) and writes several sizes plus a transparent
variant. Output goes to ``site/`` for publishing to GitHub Pages.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "site"
ACCENT = (124, 92, 214, 255)   # #7c5cd6
NOTE = (245, 245, 255, 255)


def _draw(size: int, *, background: bool = True) -> Image.Image:
    """Draw at 4x then downscale for smooth anti-aliased edges."""
    ss = size * 4
    im = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = ss / 256

    if background:
        pad = int(ss * 0.06)
        d.rounded_rectangle([pad, pad, ss - pad, ss - pad], radius=int(ss * 0.22), fill=ACCENT)
        note = NOTE
    else:
        note = ACCENT  # purple note on transparent, for light UIs

    # music note: two stems + beam + two note heads
    d.rectangle([int(96 * u), int(58 * u), int(112 * u), int(176 * u)], fill=note)
    d.rectangle([int(168 * u), int(44 * u), int(184 * u), int(162 * u)], fill=note)
    d.polygon([(96 * u, 58 * u), (184 * u, 40 * u), (184 * u, 70 * u), (96 * u, 88 * u)], fill=note)
    d.ellipse([int(66 * u), int(158 * u), int(116 * u), int(200 * u)], fill=note)
    d.ellipse([int(138 * u), int(144 * u), int(188 * u), int(186 * u)], fill=note)

    return im.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in (1024, 512, 256, 128):
        _draw(size).save(OUT_DIR / f"yoto-maker-logo-{size}.png")
    # a transparent-background variant (purple note, no square)
    _draw(512, background=False).save(OUT_DIR / "yoto-maker-logo-transparent-512.png")
    # a convenient default name
    _draw(512).save(OUT_DIR / "yoto-maker-logo.png")
    print("wrote logos to", OUT_DIR)
    for p in sorted(OUT_DIR.glob("*.png")):
        print(" ", p.name, p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
