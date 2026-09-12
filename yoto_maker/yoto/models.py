"""Shapes for the Yoto ``/content`` payload, isolated so they're easy to test.

Building the JSON body is pure logic (no network), so it lives here and is unit
tested directly. Field names follow Yoto's documented MYO content model.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrackMeta:
    """One finished track, ready to be placed in the content payload."""

    title: str
    transcoded_sha: str
    duration_s: float
    file_size: int
    fmt: str = "mp3"
    channels: str = "stereo"
    icon_ref: str | None = None  # "yoto:#<mediaId>" if an icon was uploaded


def overlay_label(ordinal: int) -> str:
    """The label Yoto shows when browsing a card's chapters and tracks.

    1-based and UNPADDED - deliberately NOT the zero-padded `key`. Three reasons,
    heaviest first:

      1. Yoto's own sample app writes `overlayLabel: "1"` in the SAME object
         literal as `key: "01"` (yotoplay/examples, vanilla-js-html/src/upload.js,
         fetched 2026-09-10). The padded identifier and the unpadded label coexist
         deliberately.
      2. The field is display text, not an identifier - Yoto describes it as "used
         in the app for track numbering". Rendering `01 02 ... 18` where
         `1 2 ... 18` belongs would be a visible regression on an 18-chapter card.
      3. Zero-padding is a property of OUR `key` scheme (`key = f"{i:02d}"` below),
         not Yoto's. Copying it into a user-visible string exports an internal
         convention.

    THIS IS THE ONLY PLACE THE VALUE IS COMPUTED. The create path below and the
    repair path's `overlay-label` intent (`yoto/repair.py`) both call it, so the two
    cannot drift - and `tests/test_repair.py`'s round-trip agreement test proves it
    for N > 9, where a padding difference would show.

    The ordinal is the chapter's 1-based position; a single track inherits its
    chapter's label. NEVER derive it from the card's own `key` field - `key` is
    "01" and the label is "1", so a path that read `key` and a path that computed
    from the index would disagree and the two could flip-flop forever.

    Reversing the decision is one line (ADR 2026-09-10 open question 4).
    """
    return str(ordinal)


def build_content_payload(card_title: str, tracks: list[TrackMeta]) -> dict:
    """Return the JSON body for ``POST /content``.

    Each track becomes its own chapter (the common MYO layout: one screen entry
    per track), with the per-track pixel icon on the chapter's display, and
    ``overlayLabel`` at both levels - the label Yoto shows when the player's knob
    browses chapters (see ``overlay_label``).
    """
    chapters = []
    for i, t in enumerate(tracks, start=1):
        key = f"{i:02d}"
        label = overlay_label(i)        # UNPADDED "1" beside the PADDED key "01"
        display = {"icon16x16": t.icon_ref} if t.icon_ref else {}
        track = {
            "key": key,
            "overlayLabel": label,      # REQUIRED by Yoto's track schema (issue #31)
            "title": t.title,
            "trackUrl": f"yoto:#{t.transcoded_sha}",
            "type": "audio",
            "format": t.fmt,
            "duration": round(t.duration_s),
            "fileSize": t.file_size,
            "channels": t.channels,
        }
        if display:
            track["display"] = dict(display)
        chapters.append(
            {
                "key": key,
                "overlayLabel": label,  # optional at chapter level; Yoto's sample sets it
                "title": t.title,
                "tracks": [track],
                **({"display": display} if display else {}),
            }
        )

    return {
        "title": card_title,
        "content": {"chapters": chapters},
        "metadata": {
            "media": {
                "duration": round(sum(t.duration_s for t in tracks)),
                "fileSize": sum(t.file_size for t in tracks),
            }
        },
    }
