"""Shapes for the Yoto ``/content`` payload, isolated so they're easy to test.

Building the JSON body is pure logic (no network), so it lives here and is unit
tested directly. Field names follow Yoto's documented MYO content model.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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


def build_content_payload(card_title: str, tracks: list[TrackMeta]) -> dict:
    """Return the JSON body for ``POST /content``.

    Each track becomes its own chapter (the common MYO layout: one screen entry
    per track), with the per-track pixel icon on the chapter's display.
    """
    chapters = []
    for i, t in enumerate(tracks, start=1):
        key = f"{i:02d}"
        display = {"icon16x16": t.icon_ref} if t.icon_ref else {}
        track = {
            "key": key,
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
