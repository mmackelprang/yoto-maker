"""The 'card being made' — a single in-memory draft.

This is a *local, single-user* app, so one global draft is all we need. It holds
the tracks the user has added, the card name, and the chosen label picture. The
draft is the single source of truth the UI reads and writes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Track:
    id: str
    title: str
    audio_path: Path
    duration_s: float = 0.0
    source_kind: str = "file"
    source_ref: str = ""
    suggested_image_path: Path | None = None
    icon_id: str | None = None  # chosen library icon for the device screen

    def view(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "duration": round(self.duration_s),
            "duration_label": _fmt_duration(self.duration_s),
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "icon_id": self.icon_id,
        }


@dataclass
class DraftCard:
    card_name: str = ""
    picture_path: Path | None = None
    picture_source: str = ""  # "auto" | "upload" | "library" | "ai"
    tracks: list[Track] = field(default_factory=list)

    # -- mutation --------------------------------------------------------
    def add_track(
        self,
        title: str,
        audio_path: Path,
        *,
        duration_s: float = 0.0,
        source_kind: str = "file",
        source_ref: str = "",
        suggested_image_path: Path | None = None,
    ) -> Track:
        track = Track(
            id=uuid.uuid4().hex[:12],
            title=title.strip() or "Untitled",
            audio_path=Path(audio_path),
            duration_s=duration_s,
            source_kind=source_kind,
            source_ref=source_ref,
            suggested_image_path=suggested_image_path,
        )
        self.tracks.append(track)
        return track

    def get(self, track_id: str) -> Track | None:
        return next((t for t in self.tracks if t.id == track_id), None)

    def remove(self, track_id: str) -> bool:
        before = len(self.tracks)
        self.tracks = [t for t in self.tracks if t.id != track_id]
        return len(self.tracks) != before

    def reorder(self, order: list[str]) -> None:
        index = {tid: i for i, tid in enumerate(order)}
        self.tracks.sort(key=lambda t: index.get(t.id, len(order)))

    def first_suggested_image(self) -> Path | None:
        for t in self.tracks:
            if t.suggested_image_path and Path(t.suggested_image_path).exists():
                return t.suggested_image_path
        return None

    def reset(self) -> None:
        self.card_name = ""
        self.picture_path = None
        self.picture_source = ""
        self.tracks = []

    # -- view ------------------------------------------------------------
    def view(self) -> dict:
        return {
            "card_name": self.card_name,
            "has_picture": self.picture_path is not None and Path(self.picture_path).exists(),
            "picture_source": self.picture_source,
            "picture_url": "/api/picture.png" if self.picture_path else None,
            "tracks": [t.view() for t in self.tracks],
            "total_duration_label": _fmt_duration(sum(t.duration_s for t in self.tracks)),
        }


def _fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds <= 0:
        return ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# Single global draft for this local session.
_draft = DraftCard()


def get_draft() -> DraftCard:
    return _draft
