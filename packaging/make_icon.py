"""Generate the app icon (packaging/app.ico) — a white music note on a purple
rounded square. Run once; the .ico is committed so builds don't depend on it.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app.ico"
S = 256
ACCENT = (124, 92, 214, 255)
ACCENT2 = (154, 125, 230, 255)


def draw(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # rounded square background with a subtle vertical gradient
    pad = int(size * 0.06)
    d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=int(size * 0.22), fill=ACCENT)
    # music note (two note heads + stems + beam), in white
    w = (245, 245, 255, 255)
    u = size / 256
    d.rectangle([int(96 * u), int(58 * u), int(112 * u), int(176 * u)], fill=w)
    d.rectangle([int(168 * u), int(44 * u), int(184 * u), int(162 * u)], fill=w)
    d.polygon([(96 * u, 58 * u), (184 * u, 40 * u), (184 * u, 70 * u), (96 * u, 88 * u)], fill=w)
    d.ellipse([int(66 * u), int(158 * u), int(116 * u), int(200 * u)], fill=w)
    d.ellipse([int(138 * u), int(144 * u), int(188 * u), int(186 * u)], fill=w)
    return im


def main() -> None:
    base = draw(S)  # full 256px source; Pillow downscales to each size
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(OUT, format="ICO", sizes=sizes)
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
