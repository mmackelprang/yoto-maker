"""Repair already-created MYO cards in place: fix each track's declared `format`.

Existing cards this app made declare `format: "mp3"`, but Yoto re-transcodes and
SERVES Ogg Opus. On the physical player that mismatch is the leading suspect for
an offline download that never completes. Item 17 fixed it for NEW cards; this
repairs the ones already sitting in the account.

Safe by construction: account-first (real cardId, never a local draft); update
IN PLACE (POST /content WITH cardId -> NFC link survives, no duplicate);
DECLARED-CHANGE-SET correction: every write is an explicit `FieldEdit` naming its
path, its observed value and its intended value, and the round-trip verify's
expectation is derived from that SAME list - so "only what we declared changed"
holds however many intents there are. Two intents today: `format` (mp3 -> opus,
confirmed by probing the served artifact) and `overlay-label` (the missing,
schema-REQUIRED `overlayLabel`, written only where absent or empty).
fileSize/duration self-correct server-side and channels was already right, so
neither is ever written. With CANONICAL references (see below);
confirm-before-correct (set "opus" only after the served artifact is PROVEN
Opus); all-or-nothing per card; backup-then-write (the rollback path);
verify-after (only the declared change-set changed); idempotent; DRY-RUN BY
DEFAULT.

CANONICALIZE-BEFORE-POST (pre-merge review HIGH #1, hardened here). GET /card
RESOLVES each track's ``trackUrl`` to a short-lived, pre-signed https URL. Posting
that resolved URL back verbatim would freeze an EXPIRING signature into the card,
so the audio would break ~60 min later and rollback (which re-POSTs a backup that
also held an expiring URL) would share the flaw. So before every POST we rewrite
each track's ``trackUrl`` from the resolved form back to the CANONICAL ``yoto:#<sha>``
form - byte-for-byte the reference the create flow POSTs (``models.build_content_payload``
writes ``yoto:#<transcoded_sha>``). Icons get the SAME treatment: POST /content REJECTS
a resolved icon URL (confirmed live - Yoto 400: 'icon16x16 must be in format
"yoto:#{mediaId}" where mediaId is 43 characters'), so every ``display.icon16x16``
(chapter- AND track-level) is rewritten from ``https://card-content.yotoplay.com/<policy>~/<mediaId>``
back to ``yoto:#<mediaId>`` (the 43-char path segment after ``~/``). The POST body then
contains only canonical ``yoto:#...`` references (trackUrl AND icon16x16) plus the
corrected ``format``: no resolved/expiring URL of either kind, round-trip safe, rollback
clean. A track sha or an icon mediaId that can't be extracted/validated BLOCKS the whole
card (all-or-nothing) rather than being guessed.

Shapes pinned against a real GET /card/gzP2B body (plan Task 1/Step 0):
  * GET /card/{id} returns ``{"card": {...}, "ownership": {...}}`` - client.get_card
    unwraps to the inner ``card`` object, which is what we back up / mutate / POST.
  * chapters live at ``content.chapters`` on that inner card.
  * each track's ``format`` is a direct string field.
  * each track's ``trackUrl`` is the RESOLVED, pre-signed https artifact URL
    (``https://secure-media.yotoplay.com/<policy>~/<sha>?Expires=..&Signature=..#sha256=<sha>``)
    - that is what we probe, and the ``<sha>`` we canonicalize back to ``yoto:#<sha>``
    for the POST. (On create the app writes ``yoto:#<sha>``; the GET resolves it.)
  * each ``display.icon16x16`` (chapter- and track-level) is a resolved
    ``https://card-content.yotoplay.com/<policy>~/<mediaId>`` URL - we canonicalize the
    43-char ``<mediaId>`` back to ``yoto:#<mediaId>`` for the POST (Yoto requires it).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..config import get_config
from ..logging_setup import setup_logging
from .client import YotoClient, YotoError
from .models import overlay_label

CORRECT_FORMAT = "opus"


# --------------------------------------------------------------------------- #
# Body shape (PINNED to the real GET /card body - plan §Ground truth, Task 1/0)
# --------------------------------------------------------------------------- #
_CHAPTER_PATHS = (("content", "chapters"), ("card", "content", "chapters"), ("chapters",))


def _chapters_path(body: dict) -> tuple:
    """The path at which THIS body's chapter list actually lives - the same three
    candidates, in the same order, that ``_find_chapters`` has always tried. ``()``
    when there is no chapter list.

    A ``FieldEdit.path`` must be built from this, never from the confirmed
    ``("content","chapters")`` path alone: ``apply_change_set`` refuses to create a
    missing intermediate container, so a hard-coded path would RAISE on exactly the
    un-unwrapped bodies the three-candidate fallback exists to tolerate."""
    for path in _CHAPTER_PATHS:
        node: object = body
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list):
            return path
    return ()


def _find_chapters(body: dict) -> list[dict]:
    """The chapter list inside a (unwrapped) GET /card body. Confirmed path first.

    ``client.get_card`` already unwraps the ``{"card": ...}`` envelope, so the
    confirmed path is ``content.chapters``. The ``card.content.chapters`` and
    bare ``chapters`` fallbacks stay so this survives an un-unwrapped body."""
    path = _chapters_path(body)
    node: object = body
    for key in path:
        node = node[key]
    return node if isinstance(node, list) else []


def _chapter_path(body: dict, ci: int) -> tuple:
    """The FieldEdit path addressing chapter ``ci`` in THIS body's real shape."""
    return _chapters_path(body) + (ci,)


def _track_path(body: dict, ci: int, ti: int) -> tuple:
    """The FieldEdit path addressing chapter ``ci``'s track ``ti`` in THIS body."""
    return _chapters_path(body) + (ci, "tracks", ti)


def _key_of_track_path(path: tuple) -> str | None:
    """The positional 'cid.tid' key a track-level FieldEdit path addresses, or None
    for a chapter-level one. Paths are built by ``_track_path`` / ``_chapter_path``,
    so the tail is ("tracks", ti, <field>) exactly when it is track-level."""
    if len(path) >= 4 and path[-3] == "tracks" and isinstance(path[-2], int):
        return f"{path[-4]}.{path[-2]}"
    return None


# Track keys that carry the RESOLVED pre-signed artifact URL. PINNED: the real
# body carries it under ``trackUrl`` (a full https URL, not a ``yoto:#sha`` ref),
# so that key is first. The ``.startswith("http")`` guard in _artifact_url means
# an unresolved ``yoto:#sha`` value is never mistaken for a probe URL.
_ARTIFACT_URL_KEYS = ("trackUrl", "url", "audioUrl", "mediaUrl", "streamUrl", "trackUrlResolved")


def _artifact_url(track: dict) -> str | None:
    def pick(d: dict) -> str | None:
        for k in _ARTIFACT_URL_KEYS:
            v = d.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
        return None
    if not isinstance(track, dict):
        return None
    direct = pick(track)
    if direct:
        return direct
    for parent in ("audio", "media"):
        obj = track.get(parent)
        if isinstance(obj, dict):
            nested = pick(obj)
            if nested:
                return nested
    return None


# --------------------------------------------------------------------------- #
# Canonicalize a RESOLVED trackUrl back to `yoto:#<sha>` (pre-merge review HIGH #1)
# --------------------------------------------------------------------------- #
# A resolved secure-media URL looks like
#   https://secure-media.yotoplay.com/<policy>~/<sha>?Expires=..&Signature=..#sha256=<sha>
# The stable identity of the artifact is <sha>: it appears BOTH in the `#sha256=`
# fragment (most reliable) and as the `<sha>` path segment after `~/`. The
# `<policy>~` prefix and the query signature rotate every ~60 min (and per request),
# so they are NOT identity. `yoto:#<sha>` is exactly what the create flow POSTs.
_SHA_TOKEN = r"[A-Za-z0-9_-]+"
_FRAG_SHA_RE = re.compile(r"sha256=(" + _SHA_TOKEN + r")")


def _sha_from_fragment(url: str) -> str | None:
    frag = url.partition("#")[2]
    if not frag:
        return None
    m = _FRAG_SHA_RE.search(frag)
    return m.group(1) if m else None


def _sha_from_path(url: str) -> str | None:
    """The `<sha>` path segment after the last `~/`, with the query+fragment removed.
    None when the URL carries no `~/<key>` segment (e.g. a differently-shaped CDN)."""
    path = url.partition("#")[0].partition("?")[0]
    if "~/" not in path:
        return None
    key = path.rsplit("~/", 1)[1].strip("/")
    return key if key and re.fullmatch(_SHA_TOKEN, key) else None


def _extract_sha(url: str) -> str | None:
    """The artifact sha from a RESOLVED trackUrl, or None if it can't be extracted
    AND validated. Prefer the `#sha256=<sha>` fragment (most reliable); when the
    `~/<sha>` path segment is ALSO present the two MUST agree - a mismatch returns
    None so the caller blocks the card rather than guess (never re-POST a wrong ref)."""
    frag = _sha_from_fragment(url)
    path = _sha_from_path(url)
    if frag and path:
        return frag if frag == path else None
    return frag or path or None


def canonical_track_url(raw: object) -> tuple[str | None, str | None]:
    """Map a track's raw ``trackUrl`` to the CANONICAL ``yoto:#<sha>`` ref for the POST.

    Returns ``(canonical, error)``:
      * ``(raw, None)``              - already a canonical ``yoto:#<sha>`` ref: leave it.
      * ``("yoto:#<sha>", None)``    - a RESOLVED https URL whose sha was extracted+validated.
      * ``(None, None)``             - no ``trackUrl`` to rewrite (nothing to do, no risk).
      * ``(None, "<reason>")``       - a resolved URL whose sha can't be extracted/validated,
                                       or an unrecognized form -> caller BLOCKS the whole card.
    """
    if not isinstance(raw, str) or not raw:
        return None, None
    if raw.startswith("yoto:#"):
        return raw, None
    if raw.startswith("http"):
        sha = _extract_sha(raw)
        if sha:
            return f"yoto:#{sha}", None
        return None, ("resolved trackUrl carries no extractable/agreeing sha - refusing "
                      "to re-POST an expiring signed URL (pre-merge review HIGH #1)")
    return None, f"unrecognized trackUrl form (not yoto:# or http): {raw[:48]!r}"


# --------------------------------------------------------------------------- #
# Canonicalize a RESOLVED icon URL back to `yoto:#<mediaId>` (live-run finding).
# --------------------------------------------------------------------------- #
# CONFIRMED LIVE: POST /content REJECTS a resolved icon URL - it requires every
# `display.icon16x16` to be `yoto:#{mediaId}` where mediaId is EXACTLY 43 chars
# (Yoto 400: 'icon16x16 must be in format "yoto:#{mediaId}" where mediaId is 43
# characters'). So icons must be canonicalized exactly like trackUrls, NOT left
# verbatim. A resolved icon URL looks like
#   https://card-content.yotoplay.com/<policy>~/<mediaId>
# with the 43-char mediaId as the path segment after `~/` (no query/fragment on the
# icon URL). The `<policy>~` prefix rotates per request; the mediaId is the identity.
_MEDIA_ID_RE = re.compile(r"[A-Za-z0-9_-]{43}")


def _extract_media_id(url: str) -> str | None:
    """The 43-char mediaId from a RESOLVED icon URL (the segment after the last `~/`,
    query/fragment stripped), or None if it isn't exactly a 43-char base64url token.
    Yoto's POST /content requires exactly 43 chars, so anything else must block rather
    than be sent (Yoto would 400 the whole POST)."""
    path = url.partition("#")[0].partition("?")[0]
    if "~/" not in path:
        return None
    seg = path.rsplit("~/", 1)[1].strip("/")
    return seg if _MEDIA_ID_RE.fullmatch(seg) else None


def canonical_icon(raw: object) -> tuple[str | None, str | None]:
    """Map a raw ``display.icon16x16`` value to the CANONICAL ``yoto:#<mediaId>`` ref.

    Returns ``(canonical, error)`` mirroring ``canonical_track_url``:
      * ``(raw, None)``                  - already a canonical ``yoto:#<mediaId>`` ref: leave it.
      * ``("yoto:#<mediaId>", None)``    - a RESOLVED card-content URL whose 43-char mediaId validated.
      * ``(None, None)``                 - no icon to rewrite (nothing to do).
      * ``(None, "<reason>")``           - a resolved URL whose mediaId can't be extracted/validated,
                                           or an unrecognized form -> caller BLOCKS the whole card.
    """
    if not isinstance(raw, str) or not raw:
        return None, None
    if raw.startswith("yoto:#"):
        return raw, None
    if raw.startswith("http"):
        media_id = _extract_media_id(raw)
        if media_id:
            return f"yoto:#{media_id}", None
        return None, ('resolved icon URL has no extractable 43-char mediaId - POST /content '
                      'requires display.icon16x16 == "yoto:#{mediaId}" (43 chars)')
    return None, f"unrecognized icon16x16 form (not yoto:# or http): {raw[:48]!r}"


def _icon_url_values(body: dict):
    """Yield ``(location, url)`` for every ``display.icon16x16`` in the card, at both
    the chapter level and the track level (mirrors how the create flow writes them)."""
    for ci, chapter in enumerate(_find_chapters(body)):
        if not isinstance(chapter, dict):
            continue
        disp = chapter.get("display")
        if isinstance(disp, dict) and isinstance(disp.get("icon16x16"), str) and disp["icon16x16"]:
            yield f"chapter {ci} display.icon16x16", disp["icon16x16"]
        for ti, tr in enumerate(chapter.get("tracks") or []):
            if not isinstance(tr, dict):
                continue
            tdisp = tr.get("display")
            if isinstance(tdisp, dict) and isinstance(tdisp.get("icon16x16"), str) and tdisp["icon16x16"]:
                yield f"track {ci}.{ti} display.icon16x16", tdisp["icon16x16"]


def icon_problems(body: dict) -> list[str]:
    """Return a problem string for each icon URL that can't be canonicalized to
    ``yoto:#<mediaId>``. Empty == every icon is already canonical or a resolved
    card-content URL with a valid 43-char mediaId (so the POST body will carry only
    canonical icon refs). A non-empty result must BLOCK the whole card (all-or-nothing)."""
    problems: list[str] = []
    for loc, url in _icon_url_values(body):
        _canon, err = canonical_icon(url)
        if err:
            problems.append(f"{loc}: {err}")
    return problems


def _canonicalize_display_icon(display: object) -> None:
    """In-place: rewrite ``display['icon16x16']`` to its canonical ``yoto:#<mediaId>``
    when it can be (a resolved card-content URL); leave already-canonical / absent /
    unrecognized values untouched. (The pre-POST gate in ``plan_card`` has already
    blocked any card carrying an un-canonicalizable icon, so in the apply path this
    only ever rewrites resolvable icons or no-ops on already-canonical ones.)"""
    if not isinstance(display, dict):
        return
    canon, err = canonical_icon(display.get("icon16x16"))
    if canon is not None and err is None:
        display["icon16x16"] = canon


def _card_title(body: dict) -> str | None:
    for path in (("title",), ("card", "title"), ("content", "title")):
        node: object = body
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, str) and node:
            return node
    return None


def _card_id_of(body: dict) -> str | None:
    if not isinstance(body, dict):
        return None
    for k in ("cardId", "contentId", "id"):
        v = body.get(k)
        if isinstance(v, str) and v:
            return v
    inner = body.get("card")            # tolerate a still-wrapped backup
    if isinstance(inner, dict):
        return _card_id_of(inner)
    return None


@dataclass
class TrackRef:
    cid: int                 # chapter index
    tid: int                 # track index within the chapter
    key: str                 # positional identity "cid.tid" (stable regardless of the card's own keys)
    title: str
    declared_format: str | None
    artifact_url: str | None      # the URL we PROBE (top-level trackUrl or a nested audio/media url)
    track_url_raw: object = None  # the raw top-level `trackUrl` field we CANONICALIZE + rewrite


def iter_tracks(body: dict) -> list[TrackRef]:
    """Positional walk of every track. Identity is POSITIONAL ('cid.tid'), not the
    card's own key strings, so it is robust to whatever keys an existing card uses."""
    refs: list[TrackRef] = []
    for ci, chapter in enumerate(_find_chapters(body)):
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if not isinstance(tr, dict):
                continue
            fmt = tr.get("format")
            refs.append(TrackRef(
                cid=ci, tid=ti, key=f"{ci}.{ti}",
                title=str(tr.get("title") or (chapter.get("title") if isinstance(chapter, dict) else "") or f"track {ci + 1}.{ti + 1}"),
                declared_format=fmt if isinstance(fmt, str) else None,
                artifact_url=_artifact_url(tr),
                track_url_raw=tr.get("trackUrl"),
            ))
    return refs


# --------------------------------------------------------------------------- #
# The declared change-set: the safety invariant, expressed as data.
#
# "after == before + the declared change-set, and NOTHING else."
#
# Before 2026-09-10 the invariant was "only `format` changed", and it was strong
# because it was narrow - narrow because the intent was hard-coded into the shape of
# the corrector. Generalising the intent into DATA keeps the narrowness while allowing
# more than one intent: the POST body and the round-trip verify's expectation are both
# derived from the SAME list, so an intent cannot be added to one and forgotten in the
# other. ADR 2026-09-10 §3.1.
# --------------------------------------------------------------------------- #
class _Absent:
    """Sentinel for 'this key was not present in the GET body'. A real `None` is a
    value Yoto could legitimately have sent, so it cannot stand in for absence."""

    def __repr__(self) -> str:
        return "<absent>"


_ABSENT = _Absent()


@dataclass(frozen=True)
class FieldEdit:
    """One declared field write.

    `old` is carried for the CLI report and is DELIBERATELY NOT CHECKED by
    `apply_change_set`: `plan_card` and `repair_card` read the body once and plan
    from that same object, so `old` cannot have gone stale between planning and
    applying. It is documentation of why the edit was declared, not a guard - do not
    add a caller that assumes it is one.
    """

    path: tuple            # ("content","chapters",0,"tracks",0,"overlayLabel")
    old: object            # value observed in the GET body; _ABSENT if the key was missing
    new: object            # the value to write
    intent: str            # "format" | "overlay-label" - groups the report
    reason: str            # printed per-track in the CLI report


ChangeSet = list          # list[FieldEdit]; ordered, at most one edit per path (asserted)


def _assert_one_edit_per_path(edits: ChangeSet) -> None:
    """Two edits for one path would make the POST body depend on list order while the
    verify's expectation depended on it identically - so it would pass while writing
    something nobody declared twice over. Refuse instead."""
    seen: set = set()
    for e in edits:
        if e.path in seen:
            raise ValueError(f"change-set declares two edits for the same path: {e.path}")
        seen.add(e.path)


def _descend(node: object, step, so_far: tuple) -> object:
    """One step along a FieldEdit path. RAISES rather than creating a container."""
    if isinstance(node, dict):
        if not isinstance(step, str) or step not in node:
            raise ValueError(
                f"FieldEdit path {so_far} does not exist in the body; apply_change_set "
                "never creates an intermediate container (guessing a container shape is "
                "how a corrector silently writes the wrong thing into a live card)")
        return node[step]
    if isinstance(node, list):
        if not isinstance(step, int) or not 0 <= step < len(node):
            raise ValueError(f"FieldEdit path {so_far} is out of range for a list of {len(node)}")
        return node[step]
    raise ValueError(f"FieldEdit path {so_far} descends into a {type(node).__name__}")


def apply_change_set(body: dict, edits: ChangeSet) -> dict:
    """Return a NEW body (input untouched) with EXACTLY the declared paths set.

    Nothing else changes - not title/trackUrl/duration/fileSize/channels/keys/
    display/order, not the card-level metadata or media aggregates.

    A missing LEAF key is CREATED: that is the point, since `overlayLabel` is absent
    on every card this app has ever made (verified against all ten real GET bodies in
    %LOCALAPPDATA%\\YotoMaker\\repair-backups\\). A missing INTERMEDIATE container
    RAISES - see `_descend`.

    This is the single source of truth `verify_only_declared_changed` derives its
    expectation from, which is what closes the silent half of the old design: a
    declared write that Yoto DROPS shows up as `unexpectedly REMOVED` instead of
    passing as `applied`."""
    _assert_one_edit_per_path(edits)
    out = copy.deepcopy(body)
    for e in edits:
        if not e.path:
            raise ValueError("FieldEdit with an empty path")
        node: object = out
        for i, step in enumerate(e.path[:-1]):
            node = _descend(node, step, e.path[: i + 1])
        leaf = e.path[-1]
        if isinstance(node, dict):
            if not isinstance(leaf, str):
                raise ValueError(f"dict at {e.path[:-1]} addressed with non-str key {leaf!r}")
            node[leaf] = e.new
        elif isinstance(node, list):
            if not isinstance(leaf, int) or not 0 <= leaf < len(node):
                raise ValueError(f"list at {e.path[:-1]} has no index {leaf!r}")
            node[leaf] = e.new
        else:
            raise ValueError(f"cannot set {leaf!r} on a {type(node).__name__} at {e.path[:-1]}")
    return out


# --------------------------------------------------------------------------- #
# The safety-critical correctors: deep-copy, overwrite ONLY the intended fields.
# --------------------------------------------------------------------------- #
def format_edits(body: dict, correct_keys: set[str], fmt: str = CORRECT_FORMAT) -> ChangeSet:
    """The `format` intent as declared edits, for the tracks named in `correct_keys`
    (positional 'cid.tid', exactly as before)."""
    edits: ChangeSet = []
    for ci, chapter in enumerate(_find_chapters(body)):
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if isinstance(tr, dict) and f"{ci}.{ti}" in correct_keys:
                edits.append(FieldEdit(
                    path=_track_path(body, ci, ti) + ("format",),
                    old=tr.get("format", _ABSENT),
                    new=fmt,
                    intent="format",
                    reason=f"{tr.get('format') or '?'} -> {fmt}",
                ))
    return edits


def apply_format_corrections(body: dict, correct_keys: set[str], fmt: str = CORRECT_FORMAT) -> dict:
    """BACK-COMPAT WRAPPER, kept on purpose. `format` is now one intent on the
    declared change-set (ADR 2026-09-10 §3.1); this is the one-intent special case,
    and it stays so the format-only safety tests keep a target and commit 2 can be
    PROVED behaviour-neutral rather than argued to be.

    Return a NEW body (input untouched) with `format = fmt` set ONLY on the tracks
    named in `correct_keys` (positional 'cid.tid'). Nothing else changes - not
    title/trackUrl/duration/fileSize/channels/keys/display/order, not the card-level
    metadata or media aggregates."""
    return apply_change_set(body, format_edits(body, correct_keys, fmt))


def _is_set(value: object) -> bool:
    """An `overlayLabel` we must leave alone: a non-empty string. Absent, None, "" and
    "   " all mean the field needs writing."""
    return isinstance(value, str) and value.strip() != ""


def overlay_label_edits(body: dict) -> tuple[ChangeSet, dict[str, list[str]]]:
    """The `overlay-label` intent: declare the missing `overlayLabel` at chapter AND
    track level, keyed on POSITION.

    Returns `(edits, notes)` where `notes` maps a positional key - "c{ci}" for a
    chapter, "{ci}.{ti}" for a track - to this intent's per-object notes.

    IDEMPOTENT BY CONSTRUCTION, with no "was this card labelled?" bookkeeping:

      1. The expected value is a pure function of POSITION, through the one shared
         helper `models.overlay_label`. Run 2 computes the same value, finds it
         equal, declares zero edits, and `outcome` is "already" - so no POST.
      2. ⚠ The value is NEVER derived from the card's own `key` field. `key` is "01"
         and the label is "1"; a path that read `key` and a path that computed from
         the index would disagree, and two runs could flip-flop forever.
      3. An existing NON-EMPTY `overlayLabel` is never overwritten - reported
         `already` and left alone. That is not only idempotency: it stops this tool
         flip-flopping against ANOTHER editor. A user who sets "Chapter 1" in the
         Yoto app would otherwise have it reset to "1" on every run, forever. It
         also means our edit is always absent-or-empty -> value, never a clobber,
         which is what keeps both the verify and the rollback story simple.

    MULTI-TRACK CHAPTERS ARE DECLINED, NOT GUESSED - and BOTH levels are declined.
    All three live cards are 1 chapter : 1 track (5x1, 18x1, 1x1 - read from the real
    bodies) and `build_content_payload` emits one track per chapter by construction,
    so this never fires on a card this app made. For a hand-assembled card we have
    ZERO evidence for the within-chapter numbering convention, and this path mutates
    live data. Declining the CHAPTER label too (not just the tracks) is deliberate:
    writing it alone would leave the schema-REQUIRED track field missing while making
    a later run's idempotency check see a labelled chapter and skip - a partial job
    that permanently hides itself. The `format` intent proceeds unaffected, which is
    the entire reason `declined` is not `blocked`: an unprobeable artifact is a
    correctness hazard and must stop the card; a label we cannot confidently number
    is not, and must never cost a card the PROVEN format fix."""
    edits: ChangeSet = []
    notes: dict[str, list[str]] = {}
    for ci, chapter in enumerate(_find_chapters(body)):
        if not isinstance(chapter, dict):
            continue
        # ⚠ RAW indices, carried alongside each track. `iter_tracks` (:351-368) and
        # `format_edits` walk the UNFILTERED list and `continue` past a non-dict entry,
        # so a raw index is what `TrackDecision.ref.key` and every other positional key
        # in this module mean. Filtering first and re-enumerating would renumber the
        # survivors: on `tracks=[None, {...}]` it would address `tracks[0]` - the None -
        # for what is really `tracks[1]`, `plan_card` would decode the key as "ci.0",
        # fail to find it in `by_key` (which holds "ci.1"), and silently DROP the edit.
        # The schema-required label would then go unwritten with nothing in the report
        # to say so. Found by pre-merge review.
        tracks = [(ti, t) for ti, t in enumerate(chapter.get("tracks") or [])
                  if isinstance(t, dict)]
        if not tracks:
            # ⚠ Declined, NOT labelled. A chapter with no tracks has nothing that can
            # carry the schema-REQUIRED track-level `overlayLabel`, so writing the
            # chapter label alone is exactly the partial-job-that-hides-itself the
            # multi-track case is declined for. It also keeps `CardPlan.outcome`'s
            # `empty` branch honest: `empty` is checked BEFORE `change_set`, so a card
            # whose every chapter is track-less would otherwise carry pending
            # chapter-level writes and still report "no tracks found - nothing to do",
            # losing them silently. That is blocker 1's shape all over again. Found by
            # pre-merge review.
            notes.setdefault(f"c{ci}", []).append(
                "declined: chapter has no tracks; nothing can carry the required "
                "track-level overlayLabel - skipped")
            continue
        if len(tracks) > 1:
            note = (f"chapter has {len(tracks)} tracks; overlayLabel numbering "
                    "convention unknown - skipped")
            notes.setdefault(f"c{ci}", []).append(f"declined: {note}")
            for ti, _tr in tracks:
                notes.setdefault(f"{ci}.{ti}", []).append(f"declined: {note}")
            continue

        expected = overlay_label(ci + 1)
        if _is_set(chapter.get("overlayLabel")):
            notes.setdefault(f"c{ci}", []).append(
                f"already: chapter overlayLabel {chapter['overlayLabel']!r} - left alone")
        else:
            edits.append(FieldEdit(
                path=_chapter_path(body, ci) + ("overlayLabel",),
                old=chapter.get("overlayLabel", _ABSENT),
                new=expected,
                intent="overlay-label",
                reason=f"chapter overlayLabel absent -> {expected!r}"))
            notes.setdefault(f"c{ci}", []).append(f"planned: chapter overlayLabel -> {expected!r}")

        for ti, tr in tracks:          # ti is the RAW index - see the note above
            if _is_set(tr.get("overlayLabel")):
                notes.setdefault(f"{ci}.{ti}", []).append(
                    f"already: overlayLabel {tr['overlayLabel']!r} - left alone")
                continue
            edits.append(FieldEdit(
                path=_track_path(body, ci, ti) + ("overlayLabel",),
                old=tr.get("overlayLabel", _ABSENT),
                new=expected,
                intent="overlay-label",
                reason=f"overlayLabel absent -> {expected!r}"))
            notes.setdefault(f"{ci}.{ti}", []).append(f"planned: overlayLabel -> {expected!r}")
    return edits, notes


def build_repair_payload(body: dict, edits: ChangeSet, canonical_urls: dict[str, str]) -> dict:
    """The NEW body to POST (input untouched): the declared change-set applied, PLUS
    the media-reference canonicalization - every `trackUrl` rewritten to its canonical
    `yoto:#<sha>` and every `display.icon16x16` (chapter- AND track-level) to its
    `yoto:#<mediaId>`, because POST /content rejects a resolved form of either.

    THE CANONICALIZATION IS DELIBERATELY NOT IN THE CHANGE-SET, and folding it in
    would break the verify (ADR 2026-09-10 §3.1's stated boundary). The verify
    neutralises media refs on BOTH sides via `_normalize_url`, because the re-GET
    returns a freshly RESOLVED URL and not the canonical ref we posted. Declaring
    canonicalization as edits would make `intended` canonical while `after` is
    resolved, and the existing normalize-then-compare would have to be undone."""
    out = apply_change_set(body, edits)
    for ci, chapter in enumerate(_find_chapters(out)):
        if isinstance(chapter, dict):
            _canonicalize_display_icon(chapter.get("display"))       # chapter-level icon
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if not isinstance(tr, dict):
                continue
            _canonicalize_display_icon(tr.get("display"))            # track-level icon
            canon = canonical_urls.get(f"{ci}.{ti}")
            if canon is not None:
                tr["trackUrl"] = canon
    return out


def canonicalize_body_media_refs(body: dict) -> dict:
    """Return a NEW body with every `trackUrl` AND every `display.icon16x16` rewritten
    to its canonical `yoto:#<...>` ref where it can be, left verbatim where it can't
    (best-effort). Used by rollback so a restore never re-POSTs a resolved trackUrl OR
    a resolved icon URL either (POST /content rejects both). Unlike the repair path
    this never blocks - a restore is a recovery action - but it makes the restored card
    as canonical as the refs allow."""
    out = copy.deepcopy(body)
    for chapter in _find_chapters(out):
        if isinstance(chapter, dict):
            _canonicalize_display_icon(chapter.get("display"))
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for tr in tracks or []:
            if not isinstance(tr, dict):
                continue
            _canonicalize_display_icon(tr.get("display"))
            canon, err = canonical_track_url(tr.get("trackUrl"))
            if canon is not None and err is None:
                tr["trackUrl"] = canon
    return out


# --------------------------------------------------------------------------- #
# Round-trip verify: after == before + the intended format flip, and NOTHING else.
# --------------------------------------------------------------------------- #
_VOLATILE_TOP_KEYS = ("updatedAt", "updated", "etag", "version", "revision")


def _normalize_url(value: str) -> str:
    """A media reference reduced to its STABLE artifact identity, so a round-trip diff
    ignores everything that legitimately rotates but still catches a real change of
    artifact. All of these map to the SAME identity when they name the same artifact:
      * a canonical ``yoto:#<sha>`` ref (what we POST);
      * a resolved URL's ``#sha256=<sha>`` fragment (most reliable on a re-GET);
      * the ``<sha>`` after ``~/`` in a resolved URL's path (icons / fragment-less URLs);
    failing all three, scheme+host+path (query and fragment dropped).

    This must NOT be a naive string compare: the re-GET after a write re-resolves each
    ``trackUrl`` to a FRESH pre-signed URL - a new query signature AND (shared across
    every media URL in one response) a new ``<policy>~`` path prefix - both of which
    rotate ~hourly / per request and are not identity. Unifying the canonical and
    resolved forms means the verify asserts the ARTIFACT is unchanged: our posted
    ``yoto:#<sha>`` and the re-GET's re-resolved ``...#sha256=<sha>`` compare EQUAL when
    (and only when) Yoto re-resolved to the same sha - which also confirms the
    canonicalized round-trip worked. The sha extraction here reuses `_extract_sha`, so
    it enforces the SAME fragment/path agreement the pre-POST gate does: a re-GET whose
    fragment and path disagree yields no unified sha and so is flagged by the diff
    rather than silently trusted."""
    if value.startswith("yoto:#"):
        return f"sha256:{value[len('yoto:#'):]}"
    sha = _extract_sha(value)          # agreement-enforced (fragment must match ~/<key>)
    if sha:
        return f"sha256:{sha}"
    return value.partition("#")[0].partition("?")[0]   # e.g. a fragment-less, ~/-less URL


def _normalize_urls(obj):
    if isinstance(obj, dict):
        return {k: _normalize_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_urls(v) for v in obj]
    if isinstance(obj, str) and (obj.startswith("http") or obj.startswith("yoto:#")):
        return _normalize_url(obj)
    return obj


def _strip_volatile(body: dict) -> dict:
    """A deep copy reduced to what a round-trip diff should legitimately compare:
    server-managed fields that change every write (updatedAt/etag/version/...)
    removed - both at the card root AND inside `content` (the real body carries a
    `content.version` counter that Yoto may bump on any write; it is never a field
    this repair intends to change, so dropping it avoids a false verify-failure) -
    and every signed CDN URL normalized to its stable path (dropping the rotating
    signature). So the diff sees only meaningful changes."""
    out = copy.deepcopy(body)
    if isinstance(out, dict):
        for k in _VOLATILE_TOP_KEYS:
            out.pop(k, None)
        content = out.get("content")
        if isinstance(content, dict):
            for k in _VOLATILE_TOP_KEYS:
                content.pop(k, None)
    return _normalize_urls(out)


def _diff_paths(a: object, b: object, path: str = "") -> list[str]:
    problems: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                problems.append(f"{path}/{k}: unexpectedly ADDED ({b[k]!r})")
            elif k not in b:
                problems.append(f"{path}/{k}: unexpectedly REMOVED (was {a[k]!r})")
            else:
                problems += _diff_paths(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            problems.append(f"{path}: length {len(a)} -> {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                problems += _diff_paths(x, y, f"{path}[{i}]")
    elif a != b:
        problems.append(f"{path}: {a!r} -> {b!r}")
    return problems


def verify_only_declared_changed(before: dict, after: dict, edits: ChangeSet) -> list[str]:
    """Return UNEXPECTED differences between `after` (the re-GET) and the intended
    result (`before` + the DECLARED change-set). [] == verified.

    Renamed from `verify_only_format_changed`: the guarantee is no longer
    format-shaped, and leaving the old name on a function that tolerates a second
    intent would be the most misleading identifier in the file.

    Unchanged: the re-GET RE-RESOLVES every `trackUrl` to a fresh pre-signed URL (new
    signature, new `<policy>~` prefix), so media refs are compared by their extracted
    sha / mediaId and never by the raw string - a naive compare would always differ.
    Volatile server fields (`updatedAt`, `content.version`) are ignored on both sides;
    everything else - title, duration, fileSize, channels, icons, keys, order - must be
    identical. Any residual difference is returned as a problem string, and a non-empty
    result means the write did something we did not sanction: STOP and review / roll back.

    What the change-set buys, and it is a net SAFETY GAIN over format-only:

      * A DECLARED addition is already in `intended`, so `_diff_paths`' `k not in a`
        branch does not fire on it - no `_VOLATILE_TOP_KEYS` widening, which would
        have blinded the verify to the very field it exists to control.
      * An UNDECLARED addition still fires. The guarantee stays field-level.
      * ⚠ A declared write that Yoto SILENTLY DROPS now fires `unexpectedly REMOVED`
        -> `verify-failed`. Under format-only that case reported `applied` and the fix
        had not landed. Given that POST /content demonstrably enriches and derives (it
        adds 16 keys we never send - ADR §1.4), this is the branch most likely to fire
        in the field."""
    intended = _strip_volatile(apply_change_set(before, edits))
    got = _strip_volatile(after)
    return _diff_paths(intended, got)


# --------------------------------------------------------------------------- #
# Per-track decision + per-card plan (all-or-nothing lives here)
# --------------------------------------------------------------------------- #
@dataclass
class TrackDecision:
    ref: TrackRef
    edits: ChangeSet = field(default_factory=list)   # 0, 1 or 2 declared writes for THIS track
    blocked_reason: str | None = None                # card-fatal (all-or-nothing) when set
    notes: list[str] = field(default_factory=list)   # one per intent: already / planned / declined


@dataclass
class CardPlan:
    card_id: str
    title: str
    decisions: list[TrackDecision]
    canonical_urls: dict[str, str] = field(default_factory=dict)  # key -> "yoto:#<sha>" for the POST body
    card_edits: ChangeSet = field(default_factory=list)           # chapter-level writes
    card_problems: list[str] = field(default_factory=list)        # card-level blockers (e.g. signed icons)
    card_notes: list[str] = field(default_factory=list)

    @property
    def change_set(self) -> ChangeSet:
        """The ONE list from which both the POST body and the verify's expectation are
        derived. `CardPlan.correct_keys` is RETIRED (ADR §3.2): a card can now need a
        write with no format corrections at all, so any surviving `correct_keys`
        caller would be a latent 'writes nothing' bug - which is exactly blocker 1."""
        return [e for d in self.decisions for e in d.edits] + self.card_edits

    @property
    def blocked(self) -> list[TrackDecision]:
        return [d for d in self.decisions if d.blocked_reason]

    @property
    def tracks_changed(self) -> int:
        return sum(1 for d in self.decisions if d.edits)

    @property
    def outcome(self) -> str:
        # Blocked is checked FIRST so a card-level blocker (e.g. an unresolvable
        # chapter-level icon) is reported even on a card the walker found no tracks on
        # - otherwise it would silently read as "empty" and its reason go unprinted.
        if self.blocked or self.card_problems:   # all-or-nothing: ANY blocker skips the card
            return "blocked"
        if not self.decisions:
            return "empty"
        if self.change_set:                      # <-- the SECOND DECISION AXIS lives here
            return "apply"
        # ⚠ `already` now means EVERY DECLARED INTENT is satisfied, not "every track is
        # already 'opus'". Before the second axis existed, a card that was already
        # `opus` but unlabelled returned here and wrote NOTHING - a silent no-op on
        # every card that needed the label (blocker 1, ADR §1.3).
        return "already"


def plan_card(client, body: dict, card_id: str, *, overlay_labels: bool = True) -> CardPlan:
    """Diagnose one card against every declared intent and decide what to write.

    Canonicalization runs FIRST and blocks the whole card (all-or-nothing) if ANY
    track's resolved trackUrl can't be reduced to a validated `yoto:#<sha>` ref - we
    must never re-POST an expiring signed URL, and we never guess a sha. Probing
    remains the ONLY place we decide a track is Opus; we never infer it from the
    declared value.

    TWO INTENTS, and only ONE of them can block (ADR 2026-09-10 §3.2):
      * `format`        - already / planned / BLOCKED. An unprobeable or non-Opus
                          artifact is a correctness hazard and must stop the card.
      * `overlay-label` - already / planned / DECLINED, and it NEVER blocks. A label
                          we cannot confidently number is not a correctness hazard,
                          and it must never cost a card the PROVEN format fix. That
                          inversion is the whole reason `declined` exists.
    """
    decisions: list[TrackDecision] = []
    canonical: dict[str, str] = {}
    for ref in iter_tracks(body):
        # 1) Canonicalize the trackUrl we'd POST back. A failure blocks the card.
        canon, err = canonical_track_url(ref.track_url_raw)
        if err:
            decisions.append(TrackDecision(ref, blocked_reason=err))
            continue
        if canon is None and ref.artifact_url and ref.artifact_url.startswith("http"):
            # A resolved (expiring) artifact URL exists but is not on the rewritable
            # top-level `trackUrl` field - refuse rather than re-POST it verbatim.
            decisions.append(TrackDecision(
                ref, blocked_reason="resolved artifact URL is not on the top-level "
                                    "trackUrl field; cannot canonicalize it safely"))
            continue
        if canon is not None:
            canonical[ref.key] = canon

        # 2) The `format` intent. Decision logic byte-for-byte as before; only the
        #    recording shape changed.
        if ref.declared_format == CORRECT_FORMAT:
            decisions.append(TrackDecision(ref, notes=[f"already: '{CORRECT_FORMAT}'"]))
            continue
        if not ref.artifact_url:
            decisions.append(TrackDecision(
                ref, blocked_reason="no resolvable artifact URL on the card"))
            continue
        probe = client.probe_artifact(ref.artifact_url)
        if not probe.is_opus:
            decisions.append(TrackDecision(
                ref, blocked_reason=f"artifact not confirmed Opus: {probe.detail}"))
            continue
        decisions.append(TrackDecision(ref, edits=[FieldEdit(
            path=_track_path(body, ref.cid, ref.tid) + ("format",),
            old=ref.declared_format if ref.declared_format is not None else _ABSENT,
            new=CORRECT_FORMAT,
            intent="format",
            reason=f"{ref.declared_format or '?'} -> {CORRECT_FORMAT} ({probe.detail})",
        )], notes=[f"planned: {ref.declared_format or '?'} -> {CORRECT_FORMAT} "
                   f"({probe.detail}); trackUrl -> {canon}"]))

    # 3) The `overlay-label` intent, off the SAME positional walk. Never blocks.
    card_edits: ChangeSet = []
    card_notes: list[str] = []
    if overlay_labels:
        label_edits, label_notes = overlay_label_edits(body)
        by_key = {d.ref.key: d for d in decisions}
        # Track-level label edits attach to their own TrackDecision so the CLI report
        # groups by track; chapter-level ones are card_edits.
        for e in label_edits:
            key = _key_of_track_path(e.path)       # None for a chapter-level path
            if key is None:
                card_edits.append(e)
            elif key in by_key and not by_key[key].blocked_reason:
                by_key[key].edits.append(e)
            # else: a BLOCKED (or unwalked) track - drop the edit. The card will not
            # be written at all (all-or-nothing), and carrying it would both
            # misreport the intent and smuggle a track write into card_edits.
        for key, notes in label_notes.items():
            if key in by_key:
                by_key[key].notes.extend(notes)
            else:
                card_notes.extend(f"chapter {key[1:]}: {n}" for n in notes)

    # 4) Card-level guard: POST /content requires canonical yoto:#<mediaId> icons. Any
    #    icon whose 43-char mediaId can't be extracted/validated blocks the whole card
    #    (all-or-nothing) - the normal case is canonicalized in build.
    card_problems = icon_problems(body)
    return CardPlan(card_id=card_id, title=str(_card_title(body) or card_id),
                    decisions=decisions, canonical_urls=canonical,
                    card_edits=card_edits, card_problems=card_problems,
                    card_notes=card_notes)


# --------------------------------------------------------------------------- #
# Apply (with backup + verify) / rollback
# --------------------------------------------------------------------------- #
@dataclass
class CardResult:
    card_id: str
    title: str
    outcome: str             # already|empty|dry-run|applied|blocked|verify-failed|write-uncertain|restored
    plan: CardPlan
    backup_path: Path | None = None
    problems: list[str] = field(default_factory=list)


def _write_backup(backup_dir: Path, card_id: str, body: dict, now: datetime | None = None) -> Path:
    """Write the verbatim original body to disk, DURABLY (flush + fsync), BEFORE
    any POST. This file is the rollback source."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    path = backup_dir / f"{card_id}-{ts}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    return path


def repair_card(client, card_id: str, *, apply: bool, backup_dir: Path,
                now: datetime | None = None, overlay_labels: bool = True) -> CardResult:
    """Diagnose one card and, if apply and fully repairable, correct it in place.

    Order of operations in apply mode is load-bearing:
      GET -> plan(probe) -> [gate] -> BACKUP -> POST -> re-GET -> VERIFY.
    The backup is on disk before the POST; a blocked card never reaches the POST.
    """
    body = client.get_card(card_id)
    plan = plan_card(client, body, card_id, overlay_labels=overlay_labels)

    if plan.outcome in ("already", "empty"):
        # Pass the outcome through: "empty" (no tracks found) is reported distinctly
        # from "already" because it can mean an unexpected body shape / parse miss,
        # not a genuinely already-correct card.
        return CardResult(card_id, plan.title, plan.outcome, plan)
    if plan.outcome == "blocked":                 # all-or-nothing: write nothing
        return CardResult(card_id, plan.title, "blocked", plan, problems=list(plan.card_problems))

    if not apply:                                 # dry run: report intent, no write
        return CardResult(card_id, plan.title, "dry-run", plan)

    backup_path = _write_backup(backup_dir, card_id, body, now)   # BEFORE any write
    # ONE change-set list, computed once, handed to BOTH the payload build and the
    # verify below. That shared value IS the invariant: deriving it twice would
    # reintroduce exactly the hand-kept agreement between two functions that made
    # blocker 2 possible (ADR 2026-09-10 §3.1). This is the line where it lands.
    edits = plan.change_set
    # Build the POST body: the declared change-set AND every trackUrl canonicalized
    # to `yoto:#<sha>`, so no resolved/expiring signed URL is written back
    # (pre-merge review HIGH #1). The backup above holds the verbatim original.
    corrected = build_repair_payload(body, edits, plan.canonical_urls)
    # The backup is now durably on disk. If the POST or the verify re-GET raises
    # (a transient timeout is plausible on a live run), we must NOT let a bare error
    # escape as if nothing happened - the write may already have landed. Report it
    # as "write-uncertain", carrying the backup path so the operator can re-run
    # (idempotent) to confirm or roll back.
    try:
        client.update_card(card_id, corrected)
        after = client.get_card(card_id)
    except YotoError as exc:
        return CardResult(
            card_id, plan.title, "write-uncertain", plan, backup_path,
            [f"POST or verify re-GET failed AFTER the backup was written: {exc}. "
             "The write MAY already have landed - re-run (it is idempotent) to confirm, "
             f"or roll back with --rollback {backup_path}."])
    problems = verify_only_declared_changed(body, after, edits)    # the SAME list
    outcome = "applied" if not problems else "verify-failed"
    return CardResult(card_id, plan.title, outcome, plan, backup_path, problems)


_OVERLAY_RESIDUE = (
    "the card still carries overlayLabel; Yoto's POST /content does not delete keys "
    "omitted from the body. Everything else is restored.")


def _tolerate_overlay_residue(problems: list[str]) -> tuple[list[str], bool]:
    """Re-report a RESIDUAL `overlayLabel` after a restore as explanation, not failure.

    ⚠ THIS IS NOT THE `_VOLATILE_TOP_KEYS` TRAP, and the difference is structural:
    it lives ONLY in the rollback path and never in `verify_only_declared_changed`;
    it is scoped to ONE field; it tolerates only residual PRESENCE and never a
    changed VALUE; and it changes a REPORT LINE, not the diff the repair path acts
    on. `_VOLATILE_TOP_KEYS` would have blinded the verify to the field in BOTH
    bodies, including a value Yoto changed on its own. Do not cite this as a
    precedent for widening that tuple (ADR §1.3, §4.2.1).

    The cost, stated: a restore can no longer distinguish OUR residual label from a
    label Yoto wrote itself. Accepted, because `canonicalize_body_media_refs`
    already establishes that a restore never blocks - a restore is a recovery action,
    and a rollback that cries wolf is worse than one that under-reports a field the
    operator is deliberately abandoning.

    DO NOT "fix" this by posting `overlayLabel: null` to clear it. Track-level
    `overlayLabel` is `z.string()`, not `.nullable()` - a null would fail validation
    and take the whole restore down with it. `overlayLabelOverride` is the nullable
    one, and we never write it.
    """
    kept, tolerated = [], False
    for p in problems:
        if "/overlayLabel:" in p and "unexpectedly ADDED" in p:
            tolerated = True
            kept.append(f"{p.split(':')[0]}: {_OVERLAY_RESIDUE}")
        else:
            kept.append(p)
    return kept, tolerated


def rollback_from_backup(client, backup_path: Path) -> CardResult:
    """Restore a card in place from a backup JSON (re-POST it with its cardId).

    The backup holds the verbatim GET body, whose trackUrls AND icon URLs are the
    RESOLVED forms POST /content rejects. Re-POSTing those verbatim would fail (or
    re-introduce HIGH #1), so the restore POST canonicalizes every trackUrl back to
    `yoto:#<sha>` and every icon back to `yoto:#<mediaId>` first (best-effort - a
    restore never blocks). The verify compares by sha/mediaId, so a restore to the
    same artifacts passes."""
    body = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    card_id = _card_id_of(body)
    if not card_id:
        raise YotoError(f"Backup {backup_path} has no cardId to restore to.")
    client.update_card(card_id, canonicalize_body_media_refs(body))
    after = client.get_card(card_id)
    problems = _diff_paths(_strip_volatile(body), _strip_volatile(after))
    # A backup predates `overlayLabel`, so restoring one POSTs a body without it -
    # correct and deliberate (ADR §3.5). But if POST /content MERGES rather than
    # REPLACES, `after` still carries the label the backup lacks, and the restore
    # would report `verify-failed` on a card that is in fact fine - a false alarm at
    # the worst possible moment. Residual PRESENCE is re-reported as explanation; a
    # changed VALUE still fails.
    problems, _tolerated = _tolerate_overlay_residue(problems)
    real = [p for p in problems if _OVERLAY_RESIDUE not in p]
    title = str(_card_title(body) or card_id)
    return CardResult(card_id, title, "restored" if not real else "verify-failed",
                      CardPlan(card_id, title, []), Path(backup_path), problems)


# --------------------------------------------------------------------------- #
# Discovery: resolve --card-id / --title to real cardIds
# --------------------------------------------------------------------------- #
def _match_title(query: str, summaries: list) -> list:
    q = query.strip().lower()
    exact = [s for s in summaries if s.title.lower() == q]
    if exact:
        return exact
    sub = [s for s in summaries if q in s.title.lower()]
    if sub:
        return sub
    toks = [t for t in q.split() if t]
    return [s for s in summaries if toks and all(t in s.title.lower() for t in toks)]


def resolve_targets(client, *, card_ids: list[str], titles: list[str]) -> list[tuple[str, str]]:
    """Resolve requested cards to (card_id, label) pairs. cardIds pass straight
    through; titles are fuzzy-matched against GET /content/mine. A title matching
    0 or >1 cards RAISES with the candidates listed - we never auto-pick a card to
    mutate. (Note: a card's colloquial name may not match its real title - e.g.
    'rainbow fairy' is titled 'Phoebe The Fashion Fairy', and 'The Wild Robot' is
    titled 'Wild Robot' - so prefer --card-id.)"""
    targets: list[tuple[str, str]] = []
    seen: set[str] = set()
    for cid in card_ids:
        cid = cid.strip()
        if cid and cid not in seen:
            seen.add(cid)
            targets.append((cid, cid))
    if titles:
        summaries = client.list_my_cards()
        for q in titles:
            matches = _match_title(q, summaries)
            if not matches:
                raise YotoError(f'No card title matched "{q}". Try --list, or pass --card-id.')
            if len(matches) > 1:
                lines = "\n".join(
                    f"    {m.card_id}  {m.title}  (created {m.created_at or '?'}, "
                    f"{m.track_count if m.track_count is not None else '?'} tracks)"
                    for m in matches
                )
                raise YotoError(f'"{q}" matched {len(matches)} cards - disambiguate with --card-id:\n{lines}')
            m = matches[0]
            if m.card_id not in seen:
                seen.add(m.card_id)
                targets.append((m.card_id, m.title))
    return targets


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _backup_dir() -> Path:
    return get_config().data_dir / "repair-backups"


def _print_card_result(res: CardResult) -> None:
    n = len(res.plan.decisions)
    print(f"{res.title} ({res.card_id}) - {n} track{'s' if n != 1 else ''}")
    if res.backup_path:
        print(f"  backup: {res.backup_path}")
    for d in res.plan.decisions:
        mark = "x" if d.blocked_reason else (">" if d.edits else "=")
        detail = d.blocked_reason or "; ".join(d.notes) or "nothing to change"
        print(f'  [{mark}] track {d.ref.key} "{d.ref.title}": {detail}')
    for note in res.plan.card_notes:
        print(f"  [-] {note}")
    summary = {
        # `already` now means EVERY DECLARED INTENT is satisfied, not "every track is
        # 'opus'". The old string would have printed "already correct (all 18 tracks
        # 'opus')" AND THEN WRITTEN on a card that was opus but unlabelled.
        "already": f"already correct ({n} track(s), nothing to change) - nothing to do",
        "empty": "no tracks found on this card - nothing to do",
        "dry-run": (f"WOULD make {len(res.plan.change_set)} change(s) across "
                    f"{res.plan.tracks_changed} track(s) - re-run with --apply to write"),
        "applied": f"made {len(res.plan.change_set)} change(s); POST ok; verify ok",
        "blocked": (f"SKIPPED - {len(res.plan.blocked)} track(s) blocked"
                    + (f" + {len(res.plan.card_problems)} card-level issue(s)" if res.plan.card_problems else "")
                    + "; card left untouched (all-or-nothing) - see below"),
        "verify-failed": ("WROTE but VERIFY FAILED - review the diffs below and roll back with "
                          f"--rollback {res.backup_path}"),
        "write-uncertain": ("the POST or verify re-GET errored AFTER the backup was written - the "
                            "write MAY have landed; re-run (idempotent) to confirm or roll back"),
        "restored": "restored from backup; verify ok",
    }.get(res.outcome, res.outcome)
    print(f"  RESULT: {summary}")
    for p in res.problems:
        print(f"    ! {p}")
    print()


def _make_console_safe() -> None:
    """Never let a card's own text crash the CLI. Call this FIRST in `main`.

    Card and track titles come straight out of Yoto's JSON (`iter_tracks` at :363,
    `_card_title` via :924 and :1068), and `_diff_paths` (:731-749) `repr()`s
    arbitrary card field values into the problem strings - and Python 3's `repr()`
    does NOT escape printable non-ASCII, so `{a!r}` is no protection. When stdout is
    a pipe, a file, or a legacy Windows console, its codec is the locale's (cp1252
    on the maintainer's box) and the write raises UnicodeEncodeError.

    THIS IS NOT COSMETIC. `main` prints each card's result at :1288, AFTER
    `repair_card` has already POSTed at :994. A crash here means the write landed
    and the operator cannot tell whether it verified, whether a backup was written,
    or which card to roll back. Wild Robot (1WCvI) carries U+1F916 in all five
    track titles (issue #31).

    WHY `errors=` AND NOT `encoding=`. Setting only the error handler cannot make
    any currently-working output worse: where the stream is already UTF-8 the
    handler never fires, and where it is not, an unencodable character becomes
    `\\U0001f916` instead of an exception. Forcing `encoding="utf-8"` would also fix
    the crash but can turn a real OEM console's correct output into mojibake, so it
    is rejected. `backslashreplace` over `replace` because `?` destroys information
    an operator may be using to identify which track is which.

    WHY NOT THE 2026-07-22 APPROACH. `516cbf7` ("ASCII-safe CLI output") replaced
    em-dashes with hyphens in THIS FILE'S OWN LITERALS - 26 lines, one file. Every
    character it removed is encodable in cp1252; it was fixing OEM-console mojibake.
    A literal sweep cannot reach text that arrives over the wire, so it never
    covered this and a second sweep would not either. `0240cbb`'s pre-merge review
    then cleared "Unicode track titles are safe" on the strength of
    `logging_setup.py:22`'s `encoding="utf-8"` - true of the LOG FILE, and the
    console `print()` path was never in its scope.

    WHY NOT `$env:PYTHONUTF8=1`. It works, and it is the only reason this tool has
    ever completed a run - but it lives in two prose lines (`SESSION_STATE.md:245`
    and the 2026-09-10 ADR's own command at :77) and in no code. The original
    runbook omits it, which is exactly how issue #31 was filed. A fix that depends
    on the operator remembering an env var is not a fix.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:          # already-replaced stream, or a frozen build
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):    # a stream that refuses reconfiguration
            pass


def main(argv: list[str] | None = None) -> int:
    _make_console_safe()          # BEFORE any print, including argparse's own
    parser = argparse.ArgumentParser(
        prog="python -m yoto_maker.repair",
        description="Repair the declared audio format on existing Yoto cards (mp3 -> opus), in place.",
    )
    parser.add_argument("--card-id", default="", help="Comma-separated cardIds, e.g. 1WCvI,gzP2B,7FcVe")
    parser.add_argument("--title", action="append", default=[],
                        help="Card title to match (repeatable). Prefer --card-id; a colloquial name may not match the real title.")
    parser.add_argument("--apply", action="store_true", help="Actually write the fix. WITHOUT this flag it is a DRY RUN.")
    parser.add_argument("--dry-run", action="store_true", help="Force a dry run (the default; wins over --apply if both are given).")
    parser.add_argument("--no-overlay-labels", action="store_true",
                        help="Do not write the missing overlayLabel; correct only the "
                             "declared format. The label fix is the unproven half "
                             "(issue #31) - this is how it backs out without a revert.")
    parser.add_argument("--rollback", default="", help="Path to a backup JSON to restore in place, then exit.")
    parser.add_argument("--list", action="store_true", help="List the account's cards and exit.")
    args = parser.parse_args(argv)

    setup_logging()
    client = YotoClient()
    if not client.is_connected():
        print("Not connected to Yoto. Open the app once and connect your account, then retry.")
        return 2

    if args.rollback:
        res = rollback_from_backup(client, Path(args.rollback))
        _print_card_result(res)
        # Keyed on the OUTCOME, not on `problems`: a tolerated residual overlayLabel
        # leaves an explanatory problem LINE on a restore that genuinely succeeded,
        # and keying on `problems` here would turn that explanation back into a
        # failure exit code - undoing `_tolerate_overlay_residue` at the last step.
        return 0 if res.outcome == "restored" else 1

    if args.list:
        for s in client.list_my_cards():
            print(f"  {s.card_id}  {s.title}  (created {s.created_at or '?'})")
        return 0

    card_ids = [c for c in args.card_id.split(",") if c.strip()]
    if not card_ids and not args.title:
        parser.error("give --card-id and/or --title (or --list)")

    apply = args.apply and not args.dry_run     # dry-run wins; writing is opt-in
    try:
        targets = resolve_targets(client, card_ids=card_ids, titles=args.title)
    except YotoError as exc:
        print(str(exc))
        return 2

    banner = ("APPLYING CHANGES (writing to live cards)" if apply
              else "DRY RUN - no changes will be written (pass --apply to write)")
    print(f"=== Repair existing cards - {banner} ===\n")
    if apply:
        # HIGH #1 is addressed: every trackUrl is canonicalized to `yoto:#<sha>` before
        # the POST, so no resolved/expiring signed URL is ever written back - the body
        # posted is the same reference form the card was created with, and the verify
        # confirms the re-GET re-resolves to the SAME sha. A staged rollout is still the
        # prudent way to prove real playback end-to-end on the physical player.
        print("A staged rollout is still recommended:\n"
              "   1) apply to ONE card first (gzP2B is smallest),\n"
              "   2) confirm playback on the physical player (ideally also re-GET after\n"
              "      ~60 min - the trackUrl signature should have rotated, same sha),\n"
              "   3) only then apply the rest. Backups are written before every POST,\n"
              "      and both apply and rollback POST canonical yoto:#<sha> refs.\n")

    exit_code = 0
    for card_id, _label in targets:
        try:
            res = repair_card(client, card_id, apply=apply, backup_dir=_backup_dir(),
                              overlay_labels=not args.no_overlay_labels)
        except YotoError as exc:
            print(f"{card_id}: ERROR - {exc}\n")
            exit_code = 1
            continue
        _print_card_result(res)
        if res.outcome in ("blocked", "verify-failed", "write-uncertain", "empty"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
