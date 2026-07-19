"""Prepare the large 'picture' used on the printed label.

Accepts any image (a YouTube thumbnail, an uploaded photo, a library icon, or an
AI image), converts odd formats (e.g. YouTube's WebP), fixes orientation, and
produces a clean square-ish PNG suitable for the label. Kept separate from the
tiny 16x16 device icon, which needs very different treatment.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

LABEL_MAX = 1024  # px on the long edge — plenty for print, small on disk


class ImageError(RuntimeError):
    """User-friendly image problem."""


def prepare_label_image(source: str | Path, out_dir: str | Path, *, name: str = "label_image") -> Path:
    """Return a normalized PNG for the label. Raises :class:`ImageError`."""
    source = Path(source)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise ImageError("That picture file could not be found.")

    try:
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)  # honor phone photo rotation
            im = im.convert("RGB")
            im.thumbnail((LABEL_MAX, LABEL_MAX), Image.LANCZOS)
            out = out_dir / f"{name}.png"
            im.save(out, format="PNG", optimize=True)
            return out
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError("We couldn't read that picture. Try a JPG or PNG image.") from exc


def save_upload(data: bytes, out_dir: str | Path, *, name: str = "uploaded") -> Path:
    """Persist raw uploaded bytes to disk, then normalize for the label."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"{name}_raw"
    raw.write_bytes(data)
    try:
        return prepare_label_image(raw, out_dir, name=name)
    finally:
        raw.unlink(missing_ok=True)


SOURCE_MAX = 1600  # keep the editable source reasonably high-res for zoom


def save_source_image(source: str | Path, out_dir: str | Path, *, name: str = "picture_source") -> Path:
    """Save a normalized, higher-res copy of the original image for re-cropping."""
    source = Path(source)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise ImageError("That picture file could not be found.")
    try:
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((SOURCE_MAX, SOURCE_MAX), Image.LANCZOS)
            out = out_dir / f"{name}.png"
            im.save(out, format="PNG")
            return out
    except Exception as exc:
        raise ImageError("We couldn't read that picture. Try a JPG or PNG image.") from exc


def crop_image(
    source: str | Path,
    box: tuple[int, int, int, int],
    out_dir: str | Path,
    *,
    name: str = "card_picture",
) -> Path:
    """Crop ``source`` to ``box`` (x, y, w, h in source pixels) and save a PNG.

    Coordinates are clamped to the image, so a slightly out-of-bounds request
    from the UI can't error.
    """
    source = Path(source)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    x, y, w, h = box
    try:
        with Image.open(source) as im:
            im = im.convert("RGB")
            iw, ih = im.size
            x = max(0, min(int(x), iw - 1))
            y = max(0, min(int(y), ih - 1))
            w = max(1, min(int(w), iw - x))
            h = max(1, min(int(h), ih - y))
            crop = im.crop((x, y, x + w, y + h))
            crop.thumbnail((LABEL_MAX, LABEL_MAX), Image.LANCZOS)
            out = out_dir / f"{name}.png"
            crop.save(out, format="PNG", optimize=True)
            return out
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError("We couldn't adjust that picture. Please try again.") from exc
