"""Generate a printable PDF label for a Yoto card.

Layout: one insert-style card centered on a Letter page with a light cut border
— a big picture up top, the card name, then a numbered track list (each track
can show its little pixel icon). Designed to be printed on plain or sticker
paper and trimmed out, to keep with the physical card.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# Insert-card size — readable, holds a full track list, cuts out easily.
CARD_W = 3.5 * inch
CARD_H = 5.0 * inch
MARGIN = 0.18 * inch
INK = (0.15, 0.13, 0.22)
MUTED = (0.42, 0.40, 0.50)
ACCENT = (0.486, 0.361, 0.839)  # #7c5cd6, matches the app


@dataclass
class LabelTrack:
    title: str
    icon_path: Path | None = None


def generate_label_pdf(
    out_path: str | Path,
    *,
    card_name: str,
    tracks: list[LabelTrack],
    image_path: str | Path | None = None,
    page_size=letter,
) -> Path:
    """Write the label PDF and return its path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    page_w, page_h = page_size
    c = canvas.Canvas(str(out_path), pagesize=page_size)
    x0 = (page_w - CARD_W) / 2
    y0 = (page_h - CARD_H) / 2

    _cut_border(c, x0, y0)

    inner_x = x0 + MARGIN
    inner_w = CARD_W - 2 * MARGIN
    cursor_y = y0 + CARD_H - MARGIN

    # --- picture (top) --------------------------------------------------
    # A 4:3-ish area rather than a full square, so the track list keeps room.
    # With a single track we can afford a taller, more prominent picture.
    pic_h = inner_w * (0.92 if len(tracks) <= 1 else 0.72)
    if image_path and Path(image_path).exists():
        _rounded_image(c, image_path, inner_x, cursor_y - pic_h, inner_w, pic_h)
    else:
        _placeholder(c, inner_x, cursor_y - pic_h, inner_w, pic_h)
    cursor_y -= pic_h + 0.16 * inch

    # --- card name (auto-fit, may wrap to 2 lines) ---------------------
    cursor_y = _draw_title(c, card_name or "My Yoto Card", inner_x, cursor_y, inner_w)
    cursor_y -= 0.1 * inch

    # --- divider --------------------------------------------------------
    c.setStrokeColorRGB(*ACCENT)
    c.setLineWidth(1.2)
    c.line(inner_x, cursor_y, inner_x + inner_w, cursor_y)
    cursor_y -= 0.16 * inch

    # --- track list -----------------------------------------------------
    _draw_tracks(c, tracks, inner_x, cursor_y, inner_w, bottom=y0 + MARGIN + 0.06 * inch)

    # --- footer ---------------------------------------------------------
    c.setFont("Helvetica-Oblique", 6.5)
    c.setFillColorRGB(*MUTED)
    c.drawCentredString(x0 + CARD_W / 2, y0 + MARGIN * 0.6, "Made with Yoto Maker")

    c.showPage()
    c.save()
    return out_path


# --------------------------------------------------------------------------- #
def _cut_border(c, x0, y0):
    c.setStrokeColorRGB(0.8, 0.8, 0.85)
    c.setLineWidth(0.6)
    c.roundRect(x0, y0, CARD_W, CARD_H, 10, stroke=1, fill=0)


def _rounded_image(c, image_path, x, y, w, h):
    try:
        img = ImageReader(str(image_path))
        c.saveState()
        path = c.beginPath()
        path.roundRect(x, y, w, h, 8)
        c.clipPath(path, stroke=0, fill=0)
        # cover-fit: fill the square, cropping overflow
        iw, ih = img.getSize()
        scale = max(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(
            img, x - (dw - w) / 2, y - (dh - h) / 2, dw, dh,
            preserveAspectRatio=False, mask="auto",
        )
        c.restoreState()
    except Exception:
        _placeholder(c, x, y, w, h)


def _placeholder(c, x, y, w, h):
    c.setFillColorRGB(0.93, 0.92, 0.97)
    c.roundRect(x, y, w, h, 8, stroke=0, fill=1)
    c.setFillColorRGB(*MUTED)
    c.setFont("Helvetica", 10)
    c.drawCentredString(x + w / 2, y + h / 2, "(no picture)")


def _draw_title(c, text, x, y, w) -> float:
    size = 22
    c.setFillColorRGB(*INK)
    while size >= 12:
        c.setFont("Helvetica-Bold", size)
        if c.stringWidth(text, "Helvetica-Bold", size) <= w:
            c.drawString(x, y - size, text)
            return y - size - 2
        size -= 1
    # too long even at min size: wrap to two lines
    c.setFont("Helvetica-Bold", 13)
    line1, line2 = _wrap_two(c, text, "Helvetica-Bold", 13, w)
    c.drawString(x, y - 13, line1)
    if line2:
        c.drawString(x, y - 27, line2)
        return y - 30
    return y - 16


def _draw_tracks(c, tracks, x, y, w, *, bottom):
    if not tracks:
        return
    line_h = 0.22 * inch
    icon = 0.16 * inch
    n = len(tracks)
    max_lines = max(1, int((y - bottom) / line_h))
    shown = tracks[:max_lines]
    for i, tr in enumerate(shown, start=1):
        ty = y - line_h * i
        # number
        c.setFillColorRGB(*ACCENT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, ty + 3, f"{i}.")
        text_x = x + 0.2 * inch
        # optional pixel icon
        if tr.icon_path and Path(tr.icon_path).exists():
            try:
                c.drawImage(
                    ImageReader(str(tr.icon_path)), text_x, ty, icon, icon,
                    preserveAspectRatio=True, mask="auto",
                )
                text_x += icon + 0.06 * inch
            except Exception:
                pass
        # title (truncate to fit)
        c.setFillColorRGB(*INK)
        c.setFont("Helvetica", 9.5)
        title = _truncate(c, tr.title, "Helvetica", 9.5, x + w - text_x)
        c.drawString(text_x, ty + 3, title)

    if n > len(shown):
        ty = y - line_h * (len(shown) + 1)
        c.setFillColorRGB(*MUTED)
        c.setFont("Helvetica-Oblique", 8.5)
        c.drawString(x, ty + 3, f"…and {n - len(shown)} more")


def _truncate(c, text, font, size, max_w) -> str:
    if c.stringWidth(text, font, size) <= max_w:
        return text
    ell = "…"
    while text and c.stringWidth(text + ell, font, size) > max_w:
        text = text[:-1]
    return text + ell


def _wrap_two(c, text, font, size, max_w) -> tuple[str, str]:
    words = text.split()
    line1 = ""
    i = 0
    while i < len(words) and c.stringWidth((line1 + " " + words[i]).strip(), font, size) <= max_w:
        line1 = (line1 + " " + words[i]).strip()
        i += 1
    line2 = " ".join(words[i:])
    return line1 or text, _truncate(c, line2, font, size, max_w) if line2 else ""
