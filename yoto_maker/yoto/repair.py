"""Repair already-created MYO cards in place: fix each track's declared `format`.

Existing cards this app made declare `format: "mp3"`, but Yoto re-transcodes and
SERVES Ogg Opus. On the physical player that mismatch is the leading suspect for
an offline download that never completes. Item 17 fixed it for NEW cards; this
repairs the ones already sitting in the account.

Safe by construction: account-first (real cardId, never a local draft); update
IN PLACE (POST /content WITH cardId -> NFC link survives, no duplicate);
FORMAT-ONLY (fileSize/duration self-correct server-side, channels already right);
confirm-before-correct (set "opus" only after the served artifact is PROVEN
Opus); all-or-nothing per card; backup-then-write (the rollback path);
verify-after (only format changed); idempotent; DRY-RUN BY DEFAULT.

Shapes pinned against a real GET /card/gzP2B body (plan Task 1/Step 0):
  * GET /card/{id} returns ``{"card": {...}, "ownership": {...}}`` — client.get_card
    unwraps to the inner ``card`` object, which is what we back up / mutate / POST.
  * chapters live at ``content.chapters`` on that inner card.
  * each track's ``format`` is a direct string field.
  * each track's ``trackUrl`` is the RESOLVED, pre-signed https artifact URL
    (``https://secure-media.yotoplay.com/...?Expires=..&Signature=..``) — that is
    what we probe. (On create the app writes ``yoto:#<sha>``; the GET resolves it.)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..config import get_config
from ..logging_setup import setup_logging
from .client import YotoClient, YotoError

CORRECT_FORMAT = "opus"


# --------------------------------------------------------------------------- #
# Body shape (PINNED to the real GET /card body — plan §Ground truth, Task 1/0)
# --------------------------------------------------------------------------- #
def _find_chapters(body: dict) -> list[dict]:
    """The chapter list inside a (unwrapped) GET /card body. Confirmed path first.

    ``client.get_card`` already unwraps the ``{"card": ...}`` envelope, so the
    confirmed path is ``content.chapters``. The ``card.content.chapters`` and
    bare ``chapters`` fallbacks stay so this survives an un-unwrapped body."""
    for path in (("content", "chapters"), ("card", "content", "chapters"), ("chapters",)):
        node: object = body
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list):
            return node
    return []


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
    artifact_url: str | None


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
            ))
    return refs


# --------------------------------------------------------------------------- #
# The safety-critical corrector: deep-copy, overwrite ONLY `format`.
# --------------------------------------------------------------------------- #
def apply_format_corrections(body: dict, correct_keys: set[str], fmt: str = CORRECT_FORMAT) -> dict:
    """Return a NEW body (input untouched) with `format = fmt` set ONLY on the
    tracks named in `correct_keys` (positional 'cid.tid'). Nothing else changes —
    not title/trackUrl/duration/fileSize/channels/keys/display/order, not the
    card-level metadata or media aggregates."""
    out = copy.deepcopy(body)
    for ci, chapter in enumerate(_find_chapters(out)):
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for ti, tr in enumerate(tracks or []):
            if isinstance(tr, dict) and f"{ci}.{ti}" in correct_keys:
                tr["format"] = fmt
    return out


# --------------------------------------------------------------------------- #
# Round-trip verify: after == before + the intended format flip, and NOTHING else.
# --------------------------------------------------------------------------- #
_VOLATILE_TOP_KEYS = ("updatedAt", "updated", "etag", "version", "revision")


def _normalize_url(value: str) -> str:
    """A signed CDN URL reduced to its stable identity: scheme+host+path, with the
    volatile query signature (Expires / Signature / Key-Pair-Id) and fragment
    dropped. The resource path token encodes the artifact's sha, so a real change
    of artifact is still caught while signature rotation across the ~60-min signing
    window is ignored. (Confirmed: two consecutive GETs return the SAME signed URL;
    it rotates only across the window.)"""
    cut = len(value)
    for sep in ("?", "#"):
        i = value.find(sep)
        if i != -1:
            cut = min(cut, i)
    return value[:cut]


def _normalize_urls(obj):
    if isinstance(obj, dict):
        return {k: _normalize_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_urls(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("http"):
        return _normalize_url(obj)
    return obj


def _strip_volatile(body: dict) -> dict:
    """A deep copy reduced to what a round-trip diff should legitimately compare:
    server-managed fields that change every write (updatedAt/etag/version/...)
    removed — both at the card root AND inside `content` (the real body carries a
    `content.version` counter that Yoto may bump on any write; it is never a field
    this repair intends to change, so dropping it avoids a false verify-failure) —
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


def verify_only_format_changed(before: dict, after: dict, correct_keys: set[str]) -> list[str]:
    """Return UNEXPECTED differences between `after` (the re-GET) and the intended
    result (`before` + the format corrections). [] == verified.

    Volatile fields (updatedAt, rotated pre-signed URL signatures) are ignored on
    both sides. Any residual difference — a changed title, a dropped icon, a
    reordered track, a corrected track that did NOT become 'opus', anything at all
    beyond the format flip we intended — is returned as a problem string. A
    non-empty result means the write did something we did not sanction: STOP and
    review / roll back."""
    intended = _strip_volatile(apply_format_corrections(before, correct_keys))
    got = _strip_volatile(after)
    return _diff_paths(intended, got)


# --------------------------------------------------------------------------- #
# Per-track decision + per-card plan (all-or-nothing lives here)
# --------------------------------------------------------------------------- #
@dataclass
class TrackDecision:
    ref: TrackRef
    status: str              # "already" | "correct" | "blocked"
    reason: str


@dataclass
class CardPlan:
    card_id: str
    title: str
    decisions: list[TrackDecision]

    @property
    def correct_keys(self) -> set[str]:
        return {d.ref.key for d in self.decisions if d.status == "correct"}

    @property
    def blocked(self) -> list[TrackDecision]:
        return [d for d in self.decisions if d.status == "blocked"]

    @property
    def outcome(self) -> str:
        if not self.decisions:
            return "empty"
        if self.blocked:            # all-or-nothing: ANY blocked track skips the card
            return "blocked"
        if self.correct_keys:
            return "apply"
        return "already"            # every track already 'opus' -> idempotent no-op


def plan_card(client, body: dict, card_id: str) -> CardPlan:
    """Diagnose one card: probe every track that isn't already 'opus' and decide
    correct / already / blocked. Probing is the ONLY place we decide a track is
    Opus — we never infer it from the declared value."""
    decisions: list[TrackDecision] = []
    for ref in iter_tracks(body):
        if ref.declared_format == CORRECT_FORMAT:
            decisions.append(TrackDecision(ref, "already", f"already '{CORRECT_FORMAT}'"))
            continue
        if not ref.artifact_url:
            decisions.append(TrackDecision(ref, "blocked", "no resolvable artifact URL on the card"))
            continue
        probe = client.probe_artifact(ref.artifact_url)
        if probe.is_opus:
            decisions.append(TrackDecision(
                ref, "correct", f"{ref.declared_format or '?'} -> {CORRECT_FORMAT} ({probe.detail})"))
        else:
            decisions.append(TrackDecision(ref, "blocked", f"artifact not confirmed Opus: {probe.detail}"))
    return CardPlan(card_id=card_id, title=str(_card_title(body) or card_id), decisions=decisions)


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
                now: datetime | None = None) -> CardResult:
    """Diagnose one card and, if apply and fully repairable, correct it in place.

    Order of operations in apply mode is load-bearing:
      GET -> plan(probe) -> [gate] -> BACKUP -> POST -> re-GET -> VERIFY.
    The backup is on disk before the POST; a blocked card never reaches the POST.
    """
    body = client.get_card(card_id)
    plan = plan_card(client, body, card_id)

    if plan.outcome in ("already", "empty"):
        # Pass the outcome through: "empty" (no tracks found) is reported distinctly
        # from "already" because it can mean an unexpected body shape / parse miss,
        # not a genuinely already-correct card.
        return CardResult(card_id, plan.title, plan.outcome, plan)
    if plan.outcome == "blocked":                 # all-or-nothing: write nothing
        return CardResult(card_id, plan.title, "blocked", plan)

    if not apply:                                 # dry run: report intent, no write
        return CardResult(card_id, plan.title, "dry-run", plan)

    backup_path = _write_backup(backup_dir, card_id, body, now)   # BEFORE any write
    corrected = apply_format_corrections(body, plan.correct_keys)
    # The backup is now durably on disk. If the POST or the verify re-GET raises
    # (a transient timeout is plausible on a live run), we must NOT let a bare error
    # escape as if nothing happened — the write may already have landed. Report it
    # as "write-uncertain", carrying the backup path so the operator can re-run
    # (idempotent) to confirm or roll back.
    try:
        client.update_card(card_id, corrected)
        after = client.get_card(card_id)
    except YotoError as exc:
        return CardResult(
            card_id, plan.title, "write-uncertain", plan, backup_path,
            [f"POST or verify re-GET failed AFTER the backup was written: {exc}. "
             "The write MAY already have landed — re-run (it is idempotent) to confirm, "
             f"or roll back with --rollback {backup_path}."])
    problems = verify_only_format_changed(body, after, plan.correct_keys)
    outcome = "applied" if not problems else "verify-failed"
    return CardResult(card_id, plan.title, outcome, plan, backup_path, problems)


def rollback_from_backup(client, backup_path: Path) -> CardResult:
    """Restore a card in place from a backup JSON (re-POST it with its cardId)."""
    body = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    card_id = _card_id_of(body)
    if not card_id:
        raise YotoError(f"Backup {backup_path} has no cardId to restore to.")
    client.update_card(card_id, body)
    after = client.get_card(card_id)
    problems = _diff_paths(_strip_volatile(body), _strip_volatile(after))
    title = str(_card_title(body) or card_id)
    return CardResult(card_id, title, "restored" if not problems else "verify-failed",
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
    0 or >1 cards RAISES with the candidates listed — we never auto-pick a card to
    mutate. (Note: a card's colloquial name may not match its real title — e.g.
    'rainbow fairy' is titled 'Phoebe The Fashion Fairy', and 'The Wild Robot' is
    titled 'Wild Robot' — so prefer --card-id.)"""
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
                raise YotoError(f'"{q}" matched {len(matches)} cards — disambiguate with --card-id:\n{lines}')
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
    print(f"{res.title} ({res.card_id}) — {n} track{'s' if n != 1 else ''}")
    if res.backup_path:
        print(f"  backup: {res.backup_path}")
    for d in res.plan.decisions:
        mark = {"already": "=", "correct": ">", "blocked": "x"}.get(d.status, " ")
        print(f'  [{mark}] track {d.ref.key} "{d.ref.title}": {d.reason}')
    summary = {
        "already": f"already correct (all {n} track(s) '{CORRECT_FORMAT}') — nothing to do",
        "empty": "no tracks found on this card — nothing to do",
        "dry-run": f"WOULD correct {len(res.plan.correct_keys)} track(s) — re-run with --apply to write",
        "applied": f"corrected {len(res.plan.correct_keys)} track(s); POST ok; verify ok",
        "blocked": (f"SKIPPED — {len(res.plan.blocked)} track(s) could not be confirmed Opus; "
                    "card left untouched (all-or-nothing)"),
        "verify-failed": ("WROTE but VERIFY FAILED — review the diffs below and roll back with "
                          f"--rollback {res.backup_path}"),
        "write-uncertain": ("the POST or verify re-GET errored AFTER the backup was written — the "
                            "write MAY have landed; re-run (idempotent) to confirm or roll back"),
        "restored": "restored from backup; verify ok",
    }.get(res.outcome, res.outcome)
    print(f"  RESULT: {summary}")
    for p in res.problems:
        print(f"    ! {p}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m yoto_maker.repair",
        description="Repair the declared audio format on existing Yoto cards (mp3 -> opus), in place.",
    )
    parser.add_argument("--card-id", default="", help="Comma-separated cardIds, e.g. 1WCvI,gzP2B,7FcVe")
    parser.add_argument("--title", action="append", default=[],
                        help="Card title to match (repeatable). Prefer --card-id; a colloquial name may not match the real title.")
    parser.add_argument("--apply", action="store_true", help="Actually write the fix. WITHOUT this flag it is a DRY RUN.")
    parser.add_argument("--dry-run", action="store_true", help="Force a dry run (the default; wins over --apply if both are given).")
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
        return 0 if not res.problems else 1

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
              else "DRY RUN — no changes will be written (pass --apply to write)")
    print(f"=== Repair existing cards — {banner} ===\n")
    if apply:
        # The one property this tool CANNOT self-verify (pre-merge review, HIGH #1):
        # it re-POSTs each card's resolved, signed `trackUrl` back to Yoto. The verify
        # runs inside the ~60-min signing window, so it cannot prove Yoto re-maps its
        # own CDN URL back to the internal audio reference rather than freezing an
        # expiring URL. Fail mode would be a card that plays for ~an hour then stops.
        print("!! trackUrl round-trip is UNPROVEN — do a STAGED rollout:\n"
              "   1) apply to ONE card first (gzP2B is smallest),\n"
              "   2) confirm playback on the physical player (ideally also re-GET after\n"
              "      ~60 min and check the signature rotated),\n"
              "   3) only then apply the rest. Backups are written before every POST.\n")

    exit_code = 0
    for card_id, _label in targets:
        try:
            res = repair_card(client, card_id, apply=apply, backup_dir=_backup_dir())
        except YotoError as exc:
            print(f"{card_id}: ERROR — {exc}\n")
            exit_code = 1
            continue
        _print_card_result(res)
        if res.outcome in ("blocked", "verify-failed", "write-uncertain", "empty"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
