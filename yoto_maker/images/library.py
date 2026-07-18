"""A small, offline, kid-friendly icon library.

We generate the icons programmatically with Pillow (no external asset files to
ship or license). Each icon is drawn at high resolution then reduced to a crisp
16x16 PNG that doubles as the Yoto device icon. The set is intentionally small
for v1; more can be added later (or wired to Yoto's public icon library).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from ..config import get_config

_SUP = 8  # supersample factor: draw at 16*8 then shrink for smooth edges
_S = 16 * _SUP


@dataclass(frozen=True)
class LibraryIcon:
    id: str
    label: str
    path: Path

    def as_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "url": f"/api/icons/{self.id}.png"}


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (_S, _S), (255, 255, 255, 0))
    return im, ImageDraw.Draw(im)


def _star(d, c=(255, 200, 40)):
    import math

    cx = cy = _S / 2
    r_out, r_in = _S * 0.46, _S * 0.19
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=c)


def _heart(d, c=(233, 69, 96)):
    q = _S / 4
    d.ellipse([q * 0.6, q * 0.7, q * 2.0, q * 2.1], fill=c)
    d.ellipse([q * 2.0, q * 0.7, q * 3.4, q * 2.1], fill=c)
    d.polygon([(q * 0.7, q * 1.7), (q * 3.3, q * 1.7), (_S / 2, _S * 0.88)], fill=c)


def _music(d, c=(124, 92, 214)):
    d.rectangle([_S * 0.42, _S * 0.18, _S * 0.5, _S * 0.72], fill=c)
    d.rectangle([_S * 0.66, _S * 0.12, _S * 0.74, _S * 0.66], fill=c)
    d.polygon([(_S * 0.42, _S * 0.18), (_S * 0.74, _S * 0.10),
               (_S * 0.74, _S * 0.24), (_S * 0.42, _S * 0.32)], fill=c)
    d.ellipse([_S * 0.26, _S * 0.62, _S * 0.5, _S * 0.84], fill=c)
    d.ellipse([_S * 0.5, _S * 0.56, _S * 0.74, _S * 0.78], fill=c)


def _sun(d, c=(255, 176, 32)):
    import math

    cx = cy = _S / 2
    for i in range(8):
        a = i * math.pi / 4
        x, y = cx + _S * 0.46 * math.cos(a), cy + _S * 0.46 * math.sin(a)
        d.line([cx, cy, x, y], fill=c, width=int(_S * 0.06))
    d.ellipse([_S * 0.3, _S * 0.3, _S * 0.7, _S * 0.7], fill=c)


def _moon(d, c=(120, 150, 230)):
    d.ellipse([_S * 0.24, _S * 0.16, _S * 0.84, _S * 0.86], fill=c)
    d.ellipse([_S * 0.42, _S * 0.10, _S * 0.98, _S * 0.80], fill=(255, 255, 255, 0))


def _cloud(d, c=(120, 190, 235)):
    d.ellipse([_S * 0.14, _S * 0.42, _S * 0.5, _S * 0.72], fill=c)
    d.ellipse([_S * 0.36, _S * 0.32, _S * 0.72, _S * 0.7], fill=c)
    d.ellipse([_S * 0.54, _S * 0.42, _S * 0.86, _S * 0.72], fill=c)
    d.rectangle([_S * 0.24, _S * 0.56, _S * 0.76, _S * 0.72], fill=c)


def _flower(d, c=(236, 110, 173), center=(255, 210, 60)):
    import math

    cx = cy = _S / 2
    for i in range(6):
        a = i * math.pi / 3
        x, y = cx + _S * 0.24 * math.cos(a), cy + _S * 0.24 * math.sin(a)
        d.ellipse([x - _S * 0.16, y - _S * 0.16, x + _S * 0.16, y + _S * 0.16], fill=c)
    d.ellipse([cx - _S * 0.13, cy - _S * 0.13, cx + _S * 0.13, cy + _S * 0.13], fill=center)


def _smiley(d, c=(255, 205, 60), ink=(60, 50, 30)):
    d.ellipse([_S * 0.12, _S * 0.12, _S * 0.88, _S * 0.88], fill=c)
    d.ellipse([_S * 0.34, _S * 0.36, _S * 0.44, _S * 0.5], fill=ink)
    d.ellipse([_S * 0.56, _S * 0.36, _S * 0.66, _S * 0.5], fill=ink)
    d.arc([_S * 0.3, _S * 0.4, _S * 0.7, _S * 0.78], start=20, end=160, fill=ink, width=int(_S * 0.05))


def _book(d, c=(90, 170, 120), page=(245, 245, 240)):
    d.rectangle([_S * 0.18, _S * 0.24, _S * 0.82, _S * 0.76], fill=c)
    d.rectangle([_S * 0.24, _S * 0.3, _S * 0.5, _S * 0.7], fill=page)
    d.rectangle([_S * 0.5, _S * 0.3, _S * 0.76, _S * 0.7], fill=page)
    d.line([_S * 0.5, _S * 0.3, _S * 0.5, _S * 0.7], fill=c, width=int(_S * 0.03))


def _rocket(d, c=(224, 90, 90), fin=(120, 150, 230)):
    d.polygon([(_S * 0.5, _S * 0.12), (_S * 0.64, _S * 0.5),
               (_S * 0.36, _S * 0.5)], fill=c)
    d.rectangle([_S * 0.36, _S * 0.5, _S * 0.64, _S * 0.78], fill=c)
    d.polygon([(_S * 0.36, _S * 0.58), (_S * 0.24, _S * 0.78), (_S * 0.36, _S * 0.78)], fill=fin)
    d.polygon([(_S * 0.64, _S * 0.58), (_S * 0.76, _S * 0.78), (_S * 0.64, _S * 0.78)], fill=fin)
    d.ellipse([_S * 0.44, _S * 0.5, _S * 0.56, _S * 0.62], fill=(245, 245, 240))


_ICONS: dict[str, tuple[str, callable]] = {
    "star": ("Star", _star),
    "heart": ("Heart", _heart),
    "music": ("Music note", _music),
    "sun": ("Sun", _sun),
    "moon": ("Moon", _moon),
    "cloud": ("Cloud", _cloud),
    "flower": ("Flower", _flower),
    "smiley": ("Smiley face", _smiley),
    "book": ("Book", _book),
    "rocket": ("Rocket", _rocket),
}


def ensure_library() -> list[LibraryIcon]:
    """Generate any missing icons into the icons dir; return the full list."""
    icons_dir = get_config().icons_dir
    icons_dir.mkdir(parents=True, exist_ok=True)
    out: list[LibraryIcon] = []
    for icon_id, (label, fn) in _ICONS.items():
        path = icons_dir / f"{icon_id}.png"
        if not path.exists():
            im, draw = _canvas()
            fn(draw)
            im = im.resize((16, 16), Image.BOX)
            im.save(path, format="PNG")
        out.append(LibraryIcon(icon_id, label, path))
    return out


def list_icons() -> list[dict]:
    return [i.as_dict() for i in ensure_library()]


def icon_path(icon_id: str) -> Path | None:
    for icon in ensure_library():
        if icon.id == icon_id:
            return icon.path
    return None
