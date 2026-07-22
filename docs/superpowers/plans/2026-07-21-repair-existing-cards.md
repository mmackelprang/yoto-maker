# Repair existing cards' declared `format` (mp3 → opus) in place — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**This will be built and RUN AGAINST THREE REAL CARDS TONIGHT.** It mutates live
production cards in the maintainer's account. Every safety property below
(backup-before-write, all-or-nothing, confirm-before-correct, verify-after,
dry-run-by-default) is load-bearing, not decorative. Read §Ground truth and
§Design decisions before writing a line.

**Design basis:** [`docs/architecture/decisions/2026-07-21-repair-existing-cards.md`](../../architecture/decisions/2026-07-21-repair-existing-cards.md)
(the ADR — currently untracked; **this PR commits it**, see Task 6). This plan
**deviates deliberately from the ADR** and is much smaller than the ADR's 3-PR
arc: the read-only diagnostic the ADR was waiting on has now run, and it proved
the correction is trivial. See §How this deviates from the ADR.

**Goal:** For a set of existing cards (by cardId or title), set each track's
declared `format` to the value Yoto actually serves the device — the literal
string `"opus"` — **in place**, preserving the physical card's NFC link, its
icons, keys, titles, ordering and every other field. The correction is applied
**only** to tracks whose served artifact is probed and **proven** Opus, and
**only** if **every** track on the card can be so confirmed (all-or-nothing). The
tool is **dry-run by default**; writes require `--apply`; a timestamped backup of
the full original card is written to disk **before** any write, and doubles as
the rollback source.

**Tech stack:** Python 3.11 / dataclasses / the existing `httpx`-based
`YotoClient` (mocked in tests) / argparse / pytest. No new dependencies, no
frontend, no server route, no job system, **no version bump**.

**6 tasks, one PR.** New module `yoto_maker/yoto/repair.py` + a thin
`yoto_maker/repair.py` CLI shim + four small `client.py` additions + a new test
file + committing the preparatory architecture docs. No existing production
behaviour changes.

---

## Global Constraints

- **Branch first.** `feat/repair-existing-cards`, PR into `main`. This changes
  source, so it goes on a branch (global `CLAUDE.md`). Never commit implementation
  to `main`.
- **Prerequisites are on `main` (verified).** Item 17 (`format` on **new** cards)
  merged as **PR #18** (`0de7cf1` "advertise Yoto's true transcoded format"); item
  13 (client-ID validation + multi-upload) merged as **PR #19** (`6481aca`, v0.1.11).
  This feature depends on neither's code paths directly — item 17 is the reason the
  correct value is known to be `"opus"` and is why **new** cards no longer need
  repair — but both are listed as dependencies because this closes the same bug for
  **old** cards. The `docs/BUILDER_QUEUE.md` rows for 13/17 are **stale** (13 shows
  in flight, 17 has no row); that is Builder's reconciliation, not this plan's — do
  not let it block you.
- **The ONLY field ever written is each track's `format`.** Not `fileSize`,
  `duration`, `channels`, `title`, `trackUrl`, `key`, `display`/icons, chapter
  structure, order, or any card-level metadata. The live diagnostic proved
  `fileSize`/`duration` self-correct server-side and `channels` is already right
  (see §Ground truth). The verify step **fails** if anything but `format` changed.
- **Never rebuild via `build_content_payload`.** That function only models the
  fields this app writes for new cards; running an existing card through it would
  silently drop icons, custom keys, ordering, and anything Yoto stores that the app
  doesn't model. The corrector **deep-copies the GET'd body and overwrites only
  `format`** on confirmed tracks. This is the single most important safety rule.
- **Confirm before you correct — never guess.** A track's `format` is set to
  `"opus"` **only** after its served artifact is fetched from its pre-signed URL
  and proven Opus (Content-Type `…opus`, or the `OggS`…`OpusHead` container magic).
  A track whose artifact is not confirmed Opus, or can't be probed at all, is
  **never** touched.
- **All-or-nothing per card.** If **any** track that needs correction cannot be
  confirmed Opus, **abort that card with zero writes** and report which track(s)
  blocked it. Never POST a partially-corrected body. A card is left byte-for-byte
  as it was when it can't be fully repaired.
- **Backup before write; backup IS the rollback.** In `--apply`, before the POST,
  the full verbatim GET body is written (flushed + `fsync`ed) to
  `<data_dir>/repair-backups/<cardId>-<YYYYMMDD-HHMMSS>.json`. `--rollback <path>`
  re-POSTs a backup in place. Update-in-place preserves `cardId`, so a rollback is
  exact.
- **Idempotent.** A track already `format=="opus"` stages no correction; a card
  whose tracks are all already `"opus"` writes nothing and reports "already
  correct". Re-running the tool is always safe.
- **Dry-run by DEFAULT.** No `--apply` → discover + read + probe + compute + report
  the intended change, **no POST, no backup**. This is the settled answer to the
  brief's "dry-run OR require --apply" — we do **both**: default is dry-run *and*
  writing requires the explicit `--apply` flag. `--dry-run` is accepted explicitly
  too (and wins over `--apply` if both are passed — the safe direction).
- **No version bump, no release cut required.** This is a maintainer utility run
  from source (`python -m yoto_maker.repair …`). It ships inside the package but
  needs no `.exe` rebuild to run tonight, and it touches no static asset, so item 8's
  asset-cache hazard does not apply. Do **not** bump `__version__` or `pyproject`;
  do **not** touch the pending v0.1.11 release.
- **Tests use a mocked client — no live calls in the suite.** Every test drives a
  fake with `get_card` / `list_my_cards` / `update_card` / `probe_artifact`
  scripted. No network, no ffmpeg, runs everywhere.

---

## Ground truth (verified live — this wins over the ADR where they differ)

Established by a read-only diagnostic against the connected account + item 17's
live upload→poll capture. **Design to these; do not re-investigate.**

- **Three target cards** (cardIds known — use `--card-id` tonight):
  - "The Wild Robot" — `1WCvI` — 5 tracks
  - "Phoebe The Fashion Fairy" (the "rainbow fairy" one) — `gzP2B` — 1 track
  - "The BFG" — `7FcVe` — 18 tracks
  - All **24** tracks declare `format="mp3"`; all **24** served artifacts are
    confirmed **Ogg Opus**. So all three cards are fully repairable.
- **The correction is `format` only.** `fileSize`/`duration` already equal the
  served artifact (Yoto self-corrects them server-side); `channels` is already the
  correct string. The corrected value is the literal `"opus"` — the same string
  item 17 now writes for new cards (`transcodedInfo.format == "opus"`).
- **Endpoints (design to these):**
  - `GET /content/mine` → the account's cards (`cardId` + `title`, plus `createdAt`;
    likely no chapters). Used for `--title` resolution and `--list`.
  - `GET /card/{cardId}` → the **full** card body: each track's `trackUrl`
    (`"yoto:#<sha>"`), its declared metadata, **and Yoto-resolved pre-signed
    artifact URLs** (short-lived, ~60 min). This is the body we back up, mutate, and
    POST back. **No separate sha→URL resolution step is needed** — the resolved URL
    is already in this body (this is why Strategy B is trivial and the ADR's
    `resolve_artifact_url` is unnecessary).
  - `POST /content` with `cardId` in the body → updates the **same** card in place,
    preserving `cardId` (and the NFC link). **No duplicate.** Reference pattern:
    `bperkinspdx/yoto-mcp-server` GET-mutate-POST.
- **PIN THREE SHAPES FROM A REAL BODY BEFORE WRITING CODE (Task 1, Step 0).** The
  diagnostic already captured a real `GET /card/{cardId}` body; reuse it (or issue
  one live `GET`, read-only). From it, pin: (a) where the **chapter list** lives
  (`_find_chapters` candidates), (b) the exact **track key carrying the pre-signed
  URL** (`_ARTIFACT_URL_KEYS`), and (c) the **track `format` field path**. Commit a
  sanitized copy as `tests/fixtures/card_sample.json`. The code below ships
  defensive candidate lists so it runs even before pinning, but pinning to the real
  body removes the only genuine unknowns and is a 5-minute step.

---

## How this deviates from the ADR (surfaced, not hidden)

The ADR (`2026-07-21-repair-existing-cards.md`) designed a **3-PR arc** around a
strategy-agnostic core, a `MetadataRecoverer` chain (Strategy A re-upload +
Strategy B artifact probe), a shared `TranscodedInfo` type, two **job-backed
server routes** (`/api/repair/scan`, `/api/repair/card/{id}`), and a Designer UX
pass. **The diagnostic it was gated on has now run and collapsed the problem:**

| ADR shape | What ships here | Why |
| --- | --- | --- |
| Correct `format` + `fileSize` + `duration` + `channels` | **`format` only** | Diagnostic: the other three are already correct on served cards. |
| Strategy A (re-upload from source) as the core path | **Dropped** | The three cards have no source, and Strategy B is proven trivial. Out of scope. |
| Strategy B via undocumented `resolve_artifact_url(sha)` | **Probe the pre-signed URL already in the `GET /card` body** | No sha→URL resolution needed; the URL is handed to us. |
| Shared `TranscodedInfo` type in `models.py`; corrector in `models.py` | **Self-contained in `repair.py`** | Only `format` matters; no shared type is warranted. Keeps scope to "a module + small client additions" per the brief. |
| Two job-backed server routes + Designer UX | **A CLI utility** | It's a one-off maintainer repair, not a user-facing surface. No server/job/UX. |
| 3-PR arc | **1 PR** | The collapsed scope fits one reviewable unit safely. |

**Task 6 adds a short addendum to the ADR** recording that it shipped as this
simplified CLI utility, so the decision record stays honest. The ADR's core
principles that this plan **keeps**: account-first discovery, update-in-place with
`cardId`, all-or-nothing per card, deep-copy-and-overwrite-only, verify-after, and
"be honest per card about what couldn't be fixed".

---

## File structure

| File | Responsibility | Tasks |
| --- | --- | --- |
| `yoto_maker/yoto/client.py` | Four small additions: `CardSummary`/`ArtifactProbe` dataclasses, and `YotoClient.list_my_cards()`, `.get_card()`, `.update_card()`, `.probe_artifact()`. Reuse `_headers`/`_dig`/`_friendly_http`/`self._client`. | 1 |
| `yoto_maker/yoto/repair.py` | **New.** Pure logic (body-walk, corrector, verify/diff), orchestration (per-track decision, all-or-nothing, backup, verify, rollback, discovery), and the `main(argv)` CLI. | 2, 3, 4 |
| `yoto_maker/repair.py` | **New.** 4-line shim so `python -m yoto_maker.repair …` runs the CLI verbatim as the brief specifies. | 4 |
| `tests/test_repair.py` | **New.** The six required tests + discovery/disambiguation + rollback, all against a mocked client. | 5 |
| `tests/fixtures/card_sample.json` | **New.** A sanitized real `GET /card` body, used to pin shapes and as a realistic fixture. | 1 |
| `docs/architecture/**` | Commit the untracked ADRs + README (design basis + preparatory docs); add the ADR addendum. | 6 |
| `docs/BUILDER_QUEUE.md`, `docs/RELEASE_NOTES.md` | Queue bookkeeping (Planner already filed the row — Builder marks it done) + a release-notes line. | 6 |

**Not modified, on purpose:** `models.py` (`build_content_payload` is deliberately
**not** used), `normalize.py`, `server/app.py`, `server/jobs.py`, `__init__.py`
(`__version__`), `pyproject.toml`. If a reviewer expects a `models.py` diff, the
"never rebuild via `build_content_payload`" rule is why there isn't one.

---

# Task 1: Account read/write surface + artifact probe on `YotoClient`

**Files:**
- Modify: `yoto_maker/yoto/client.py` — add two dataclasses after `CardResult`
  (after line 59) and four methods on `YotoClient` (after `_create_content`, before
  `close`, ~line 271), plus a `_track_count` module helper near `_dig`.
- Add: `tests/fixtures/card_sample.json` — a sanitized real `GET /card` body.
- Modify: `tests/test_yoto_client.py` — a couple of unit tests for the probe
  classifier and `update_card`'s cardId injection.

**Interfaces produced:**
- `list_my_cards() -> list[CardSummary]` — GET `/content/mine`.
- `get_card(card_id) -> dict` — GET `/card/{card_id}`, verbatim body.
- `update_card(card_id, body) -> dict` — POST `/content` with `body["cardId"]=card_id`.
- `probe_artifact(url) -> ArtifactProbe` — HEAD + ranged-GET sniff; **no auth header**
  (the URL is pre-signed).

- [ ] **Step 0: Pin the real shapes.** Obtain one real `GET /card/{cardId}` body
  (reuse the diagnostic's capture, or issue one read-only GET). Confirm the chapter
  path, the pre-signed-URL track key, and the `format` field path. Save a sanitized
  copy (redact the pre-signed URL query signatures) to `tests/fixtures/card_sample.json`.
  Update `_find_chapters` / `_ARTIFACT_URL_KEYS` in Task 2 to put the **confirmed**
  key first.

- [ ] **Step 1: Add the dataclasses and helper.**

In `yoto_maker/yoto/client.py`, after `CardResult` (line 59) add:

```python
@dataclass
class CardSummary:
    """One card as listed by GET /content/mine."""
    card_id: str
    title: str
    created_at: str | None = None
    track_count: int | None = None


@dataclass
class ArtifactProbe:
    """What a served artifact actually is, read from its pre-signed URL."""
    is_opus: bool
    detail: str                       # human-readable reason, for the report
    content_type: str | None = None
```

After `_dig` (after line 72) add:

```python
def _track_count(card: dict) -> int | None:
    """Best-effort track count from a /content/mine list item (often absent)."""
    if not isinstance(card, dict):
        return None
    for key in ("trackCount", "noOfTracks"):
        v = card.get(key)
        if isinstance(v, int):
            return v
    tracks = card.get("tracks")
    return len(tracks) if isinstance(tracks, list) else None
```

- [ ] **Step 2: Add the four methods.** In `YotoClient`, after `_create_content`
  (after line 270) and before `close` (line 272), insert:

```python
    # -- account read/write surface (used by yoto/repair.py) --------------
    def list_my_cards(self) -> list[CardSummary]:
        """GET /content/mine -> the account's cards (id + title + createdAt)."""
        try:
            resp = self._client.get(f"{self._base}/content/mine", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "listing your cards")) from exc

        # The list may be bare or wrapped; confirm the wrapper against a live body.
        items = data if isinstance(data, list) else _dig(data, "cards", "content", "mine", default=[])
        cards: list[CardSummary] = []
        for it in items if isinstance(items, list) else []:
            cid = _dig(it, "cardId", "contentId", "id")
            if not cid:
                continue
            cards.append(CardSummary(
                card_id=cid,
                title=_dig(it, "title", default="(untitled)"),
                created_at=_dig(it, "createdAt", "created", default=None),
                track_count=_track_count(it),
            ))
        return cards

    def get_card(self, card_id: str) -> dict:
        """GET /card/{card_id} -> the FULL verbatim card body.

        Returned as-is (nothing dropped) — it is the thing repair.py backs up,
        deep-copies, mutates (format only) and POSTs back. It also carries the
        short-lived pre-signed artifact URLs used to probe each track.
        """
        try:
            resp = self._client.get(f"{self._base}/card/{card_id}", headers=self._headers())
            resp.raise_for_status()
            return resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "reading the card")) from exc

    def update_card(self, card_id: str, body: dict) -> dict:
        """POST /content with body['cardId'] = card_id -> update IN PLACE.

        Preserves cardId (and the physical NFC link) and creates NO duplicate.
        The body is sent verbatim except that cardId is (re)asserted, so icons,
        keys, ordering and every unmodelled field survive. This is deliberately
        NOT routed through build_content_payload.
        """
        payload = dict(body)
        payload["cardId"] = card_id
        try:
            resp = self._client.post(
                f"{self._base}/content",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except auth.NotConnectedError:
            raise
        except Exception as exc:
            raise YotoError(_friendly_http(exc, "saving the repaired card")) from exc

    def probe_artifact(self, url: str) -> ArtifactProbe:
        """Fetch a track's served artifact and decide whether it is Ogg Opus.

        The URL is PRE-SIGNED (its auth is in the query string), so we send NO
        bearer header. HEAD first for Content-Type; then sniff the first bytes
        for the Ogg 'OggS' page header + the 'OpusHead' identification header —
        the confirmed signature of what Yoto serves the device. Returns a soft
        result (never raises): is_opus=False on any non-Opus / unreadable case,
        with a human-readable reason for the report.
        """
        ctype = ""
        try:
            h = self._client.head(url, follow_redirects=True)
            h.raise_for_status()
            ctype = (h.headers.get("Content-Type") or "").strip()
        except Exception:
            ctype = ""  # some CDNs reject HEAD — fall through to the ranged GET
        if "opus" in ctype.lower():
            return ArtifactProbe(True, f"Content-Type {ctype}", ctype)
        try:
            g = self._client.get(url, headers={"Range": "bytes=0-255"}, follow_redirects=True)
            g.raise_for_status()
            head = g.content[:256]
        except Exception as exc:
            return ArtifactProbe(False, f"couldn't read the artifact ({exc.__class__.__name__})", ctype or None)
        if head[:4] == b"OggS" and b"OpusHead" in head:
            return ArtifactProbe(True, f"OggS/OpusHead magic (Content-Type {ctype or '?'})", ctype or None)
        return ArtifactProbe(False, f"not Opus (Content-Type {ctype or '?'}, first bytes {head[:4]!r})", ctype or None)
```

- [ ] **Step 3: Unit tests for the probe classifier + `update_card`.** Put these in
  the new `tests/test_repair.py` (self-contained — a tiny local httpx fake, so no
  churn to `test_yoto_client.py`'s `FakeResponse`/`FakeClient`). The classifier must
  have at least one direct test for each of the three paths (Content-Type opus,
  `OggS`/`OpusHead` magic, non-Opus); the behavioural probe coverage lives elsewhere
  in `test_repair.py` via a fake that returns `ArtifactProbe` directly.

```python
def test_probe_reads_opus_content_type():
    from yoto_maker.yoto.client import YotoClient

    class Resp:
        def __init__(self, headers=None, content=b""):
            self.headers = headers or {}
            self.content = content
        def raise_for_status(self): pass
    class HttpFake:
        def head(self, url, **k): return Resp({"Content-Type": "audio/ogg; codecs=opus"})
        def get(self, url, **k): return Resp(content=b"OggS...OpusHead...")
    yc = YotoClient(client=HttpFake())
    assert yc.probe_artifact("https://x/a").is_opus


def test_probe_sniffs_ogg_opus_magic_when_content_type_is_generic():
    from yoto_maker.yoto.client import YotoClient

    class Resp:
        def __init__(self, headers=None, content=b""):
            self.headers = headers or {}
            self.content = content
        def raise_for_status(self): pass
    class HttpFake:
        def head(self, url, **k): return Resp({"Content-Type": "application/octet-stream"})
        def get(self, url, **k):
            return Resp({"Content-Type": "application/octet-stream"},
                        b"OggS\x00\x02" + b"\x00" * 20 + b"OpusHead" + b"\x00" * 20)
    assert YotoClient(client=HttpFake()).probe_artifact("https://x/a").is_opus


def test_probe_rejects_non_opus():
    from yoto_maker.yoto.client import YotoClient

    class Resp:
        def __init__(self, headers=None, content=b""):
            self.headers = headers or {}
            self.content = content
        def raise_for_status(self): pass
    class HttpFake:
        def head(self, url, **k): return Resp({"Content-Type": "audio/mpeg"})
        def get(self, url, **k): return Resp({"Content-Type": "audio/mpeg"}, b"ID3\x03mp3data")
    p = YotoClient(client=HttpFake()).probe_artifact("https://x/a")
    assert p.is_opus is False and "not Opus" in p.detail


def test_update_card_injects_cardid_and_posts_content():
    from yoto_maker.yoto.client import YotoClient
    posts = []
    class HttpFake:
        def post(self, url, json=None, headers=None, **k):
            posts.append((url, json))
            class R:
                def raise_for_status(self): pass
                def json(self): return {"cardId": "C1"}
            return R()
    YotoClient(client=HttpFake()).update_card("C1", {"title": "T", "content": {}})
    assert posts[0][0].endswith("/content")
    assert posts[0][1]["cardId"] == "C1"
```

- [ ] **Step 4: Run.** `python -m pytest tests/test_repair.py tests/test_yoto_client.py -q`
  Expected: the four new tests here PASS; existing client tests unaffected.

- [ ] **Step 5: Commit.**

```bash
git add yoto_maker/yoto/client.py tests/test_repair.py tests/fixtures/card_sample.json
git commit -m "feat(yoto): account read/write surface + artifact probe on YotoClient

Adds list_my_cards (GET /content/mine), get_card (GET /card/{id}, verbatim
body), update_card (POST /content WITH cardId -> update in place, no duplicate,
NOT via build_content_payload) and probe_artifact (pre-signed URL -> is it Ogg
Opus, by Content-Type then OggS/OpusHead magic; no bearer header). The first
account read/write surface the app has for cards it did not just create; the
repair CLI composes it."
```

---

# Task 2: Pure logic — body walk, format-only corrector, round-trip verify

**Files:**
- Add: `yoto_maker/yoto/repair.py` — the pure, network-free half (walk, corrector,
  verify/diff, volatile-strip). No I/O, no client.

**Interfaces produced:**
- `iter_tracks(body) -> list[TrackRef]`
- `apply_format_corrections(body, correct_keys, fmt="opus") -> dict` — deep-copy,
  overwrite `format` only.
- `verify_only_format_changed(before, after, correct_keys) -> list[str]` — [] == verified.

- [ ] **Step 1: Write the module header + pure logic.** Create
  `yoto_maker/yoto/repair.py`:

```python
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
# Body shape (PIN to a real GET /card body — see plan §Ground truth, Task 1/0)
# --------------------------------------------------------------------------- #
def _find_chapters(body: dict) -> list[dict]:
    """The chapter list inside a GET /card body. Put the CONFIRMED path first."""
    for path in (("content", "chapters"), ("card", "content", "chapters"), ("chapters",)):
        node: object = body
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list):
            return node
    return []


# Track keys that carry the RESOLVED pre-signed artifact URL. Put the confirmed
# key first. These regenerate every GET, so they are also stripped before diffing.
_ARTIFACT_URL_KEYS = ("url", "audioUrl", "mediaUrl", "streamUrl", "trackUrlResolved")


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
    for k in ("cardId", "contentId", "id"):
        v = body.get(k) if isinstance(body, dict) else None
        if isinstance(v, str) and v:
            return v
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


def _strip_volatile(body: dict) -> dict:
    """A deep copy with fields that legitimately change every GET removed, so a
    round-trip diff sees only meaningful changes: top-level updatedAt/etag/etc,
    and each track's regenerated pre-signed artifact URL(s)."""
    out = copy.deepcopy(body)
    if isinstance(out, dict):
        for k in _VOLATILE_TOP_KEYS:
            out.pop(k, None)
    for chapter in _find_chapters(out):
        tracks = chapter.get("tracks") if isinstance(chapter, dict) else None
        for tr in tracks or []:
            if not isinstance(tr, dict):
                continue
            for k in _ARTIFACT_URL_KEYS:
                tr.pop(k, None)
            for parent in ("audio", "media"):
                if isinstance(tr.get(parent), dict):
                    for k in _ARTIFACT_URL_KEYS:
                        tr[parent].pop(k, None)
    return out


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

    Volatile fields (updatedAt, regenerated pre-signed URLs) are ignored on both
    sides. Any residual difference — a changed title, a dropped icon, a reordered
    track, a corrected track that did NOT become 'opus', anything at all beyond the
    format flip we intended — is returned as a problem string. A non-empty result
    means the write did something we did not sanction: STOP and review/roll back."""
    intended = _strip_volatile(apply_format_corrections(before, correct_keys))
    got = _strip_volatile(after)
    return _diff_paths(intended, got)
```

- [ ] **Step 2: Run** the pure-logic tests once Task 5 exists, or eyeball now.
  This task adds no tests of its own; Task 5 covers it. Commit with Task 3 (they are
  one module) — or commit the pure half now:

```bash
git add yoto_maker/yoto/repair.py
git commit -m "feat(repair): pure body-walk, format-only corrector, round-trip verify

apply_format_corrections deep-copies the GET'd body and overwrites ONLY each
confirmed track's format; verify_only_format_changed re-diffs after vs
(before + the intended flip), ignoring volatile fields (updatedAt, regenerated
pre-signed URLs), and returns any residual change so an unsanctioned write is
caught. Identity is positional (cid.tid), robust to a card's own key strings."
```

---

# Task 3: Orchestration — decide, back up, write, verify, roll back, discover

**Files:**
- Modify: `yoto_maker/yoto/repair.py` — append the decision/orchestration layer.

**Interfaces produced:**
- `plan_card(client, body, card_id) -> CardPlan`
- `repair_card(client, card_id, *, apply, backup_dir, now=None) -> CardResult`
- `rollback_from_backup(client, backup_path) -> CardResult`
- `resolve_targets(client, *, card_ids, titles) -> list[tuple[str, str]]`

- [ ] **Step 1: Append the orchestration.** Add to `yoto_maker/yoto/repair.py`:

```python
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
    outcome: str             # "already" | "dry-run" | "applied" | "blocked" | "verify-failed" | "restored"
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
        return CardResult(card_id, plan.title, "already", plan)
    if plan.outcome == "blocked":                 # all-or-nothing: write nothing
        return CardResult(card_id, plan.title, "blocked", plan)

    if not apply:                                 # dry run: report intent, no write
        return CardResult(card_id, plan.title, "dry-run", plan)

    backup_path = _write_backup(backup_dir, card_id, body, now)   # BEFORE any write
    corrected = apply_format_corrections(body, plan.correct_keys)
    client.update_card(card_id, corrected)
    after = client.get_card(card_id)
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
    'rainbow fairy' is titled 'Phoebe The Fashion Fairy' — so prefer --card-id.)"""
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
```

- [ ] **Step 2: Commit** (with Task 2's half if not already committed):

```bash
git add yoto_maker/yoto/repair.py
git commit -m "feat(repair): decision/backup/verify/rollback/discovery orchestration

plan_card probes each non-opus track and decides correct/already/blocked;
CardPlan.outcome enforces all-or-nothing (any blocked track skips the whole
card). repair_card runs GET -> plan -> gate -> BACKUP -> POST -> re-GET -> verify
in that order; rollback_from_backup re-POSTs a backup in place; resolve_targets
maps --card-id/--title to real cardIds and refuses to auto-pick an ambiguous
title."
```

---

# Task 4: CLI + `python -m yoto_maker.repair` shim

**Files:**
- Modify: `yoto_maker/yoto/repair.py` — add `main(argv)`, `_print_card_result`,
  `_backup_dir`, and the `__main__` guard.
- Add: `yoto_maker/repair.py` — the shim so `python -m yoto_maker.repair` runs it.

**Interface produced:**
- `python -m yoto_maker.repair --card-id 1WCvI,gzP2B,7FcVe [--apply]` (and
  equivalently `python -m yoto_maker.yoto.repair …`).

- [ ] **Step 1: Append the CLI to `yoto_maker/yoto/repair.py`:**

```python
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

    exit_code = 0
    for card_id, _label in targets:
        try:
            res = repair_card(client, card_id, apply=apply, backup_dir=_backup_dir())
        except YotoError as exc:
            print(f"{card_id}: ERROR — {exc}\n")
            exit_code = 1
            continue
        _print_card_result(res)
        if res.outcome in ("blocked", "verify-failed"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add the shim `yoto_maker/repair.py`:**

```python
"""Convenience entry point so `python -m yoto_maker.repair` runs the repair CLI.

The implementation lives in yoto_maker/yoto/repair.py (next to the Yoto client).
This thin shim exists so the command the maintainer runs is exactly:

    python -m yoto_maker.repair --card-id 1WCvI,gzP2B,7FcVe --apply
"""
import sys

from .yoto.repair import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke-test the CLI wiring (no network).**
  `python -m yoto_maker.repair --help` must print usage and exit 0.
  `python -m yoto_maker.repair` with no args must `parser.error` (exit 2).
  (Both run before any client call except `is_connected()`; on a dev box with no
  token the tool prints the "not connected" line and exits 2 — that is correct.)

- [ ] **Step 4: Commit.**

```bash
git add yoto_maker/yoto/repair.py yoto_maker/repair.py
git commit -m "feat(repair): CLI (dry-run by default) + python -m yoto_maker.repair shim

--card-id / --title / --apply / --dry-run / --rollback / --list. Dry run is the
default and wins over --apply if both are passed; writing is opt-in. Per-card
output shows the backup path, each track's decision, the result, and any verify
problems. The shim makes the maintainer's literal command work verbatim."
```

---

# Task 5: Tests — the six required + discovery/disambiguation + rollback

**Files:**
- Modify: `tests/test_repair.py` (created in Task 1) — add the orchestration tests.

**Interfaces consumed:** everything from Tasks 2–4, via a mocked client. No
network, no ffmpeg.

- [ ] **Step 1: Add the fixtures + fake at the top of `tests/test_repair.py`
  (below the Task-1 probe tests):**

```python
import copy
import pytest

from yoto_maker.yoto.client import ArtifactProbe, CardSummary
from yoto_maker.yoto.repair import (
    apply_format_corrections,
    repair_card,
    resolve_targets,
    verify_only_format_changed,
)
from yoto_maker.yoto.client import YotoError


def _card(card_id="C1", formats=("mp3", "mp3"), with_urls=True, title="Test Card"):
    """A GET /card body in the create-shape: one track per chapter, with icons,
    keys, durations, sizes, channels — everything the verify must preserve."""
    chapters = []
    for i, fmt in enumerate(formats, start=1):
        key = f"{i:02d}"
        track = {
            "key": key, "title": f"Track {i}", "type": "audio",
            "trackUrl": f"yoto:#SHA{i}", "format": fmt,
            "duration": 100 + i, "fileSize": 1000 + i, "channels": "stereo",
            "display": {"icon16x16": f"yoto:#ICON{i}"},
        }
        if with_urls:
            track["url"] = f"https://cdn.example/{card_id}/{i}.opus?sig=EPHEMERAL{i}"
        chapters.append({"key": key, "title": f"Track {i}", "tracks": [track]})
    return {"cardId": card_id, "title": title,
            "content": {"chapters": chapters},
            "updatedAt": "2026-07-21T00:00:00Z"}


class FakeClient:
    """Scripts get_card/list_my_cards/update_card/probe_artifact. get_card returns
    the original until a POST happens, then the posted body (or an `after`
    override, to simulate the server changing something unexpectedly)."""

    def __init__(self, body, *, probe=None, after=None, summaries=None):
        self._body = copy.deepcopy(body)
        self._after = after
        self._probe = probe or (lambda url: ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
        self._summaries = summaries
        self.posts = []

    def is_connected(self):
        return True

    def list_my_cards(self):
        if self._summaries is not None:
            return self._summaries
        return [CardSummary(self._body.get("cardId", "C1"), self._body.get("title", "Test Card"), "2026-07-21", 2)]

    def probe_artifact(self, url):
        return self._probe(url)

    def get_card(self, card_id):
        if self.posts:
            return copy.deepcopy(self._after if self._after is not None else self.posts[-1])
        return copy.deepcopy(self._body)

    def update_card(self, card_id, body):
        self.posts.append(copy.deepcopy(body))
        return {"cardId": card_id}
```

- [ ] **Step 2: The six required tests + extras:**

```python
def test_corrector_sets_only_format_everything_else_byte_identical():
    """apply_format_corrections computes format='opus' and leaves every other
    field byte-identical (deep structural equality), and does not mutate its input."""
    before = _card("C1", ("mp3", "mp3"))
    expected = copy.deepcopy(before)
    for ch in expected["content"]["chapters"]:
        ch["tracks"][0]["format"] = "opus"

    out = apply_format_corrections(before, {"0.0", "1.0"})

    assert out == expected                                   # ONLY format changed, everywhere
    assert before["content"]["chapters"][0]["tracks"][0]["format"] == "mp3"  # input untouched


def test_unprobeable_or_non_opus_track_skips_whole_card_no_post(tmp_path):
    """A single non-Opus/unprobeable track blocks the ENTIRE card (all-or-nothing):
    no POST is issued and the card is reported skipped."""
    def probe(url):
        # track 2's artifact is (say) still MP3 / unreadable
        return (ArtifactProbe(False, "Content-Type audio/mpeg — not Opus", "audio/mpeg")
                if url.endswith("2.opus?sig=EPHEMERAL2") else ArtifactProbe(True, "OggS/OpusHead", "audio/ogg"))
    fake = FakeClient(_card("C1", ("mp3", "mp3")), probe=probe)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "blocked"
    assert fake.posts == []                                  # NEVER wrote a partial card
    assert len(res.plan.blocked) == 1


def test_dry_run_issues_no_post(tmp_path):
    fake = FakeClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=False, backup_dir=tmp_path / "b")
    assert res.outcome == "dry-run"
    assert res.plan.correct_keys == {"0.0", "1.0"}
    assert fake.posts == []


def test_idempotent_already_opus_no_post(tmp_path):
    fake = FakeClient(_card("C1", ("opus", "opus")))
    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")
    assert res.outcome == "already"
    assert fake.posts == []


def test_backup_written_before_any_post(tmp_path):
    """The backup file must be durably on disk BEFORE the POST fires."""
    backup_dir = tmp_path / "b"
    existed_at_post = {"value": None}

    class OrderingClient(FakeClient):
        def update_card(self, card_id, body):
            existed_at_post["value"] = any(backup_dir.glob(f"{card_id}-*.json"))
            return super().update_card(card_id, body)

    fake = OrderingClient(_card("C1", ("mp3", "mp3")))
    res = repair_card(fake, "C1", apply=True, backup_dir=backup_dir)

    assert existed_at_post["value"] is True                 # backup existed when POST ran
    assert res.backup_path and res.backup_path.exists()
    # and the backup is the verbatim ORIGINAL (still mp3), not the corrected body
    saved = __import__("json").loads(res.backup_path.read_text(encoding="utf-8"))
    assert saved["content"]["chapters"][0]["tracks"][0]["format"] == "mp3"


def test_verify_catches_an_unexpected_extra_field_change(tmp_path):
    """If the re-GET shows a change beyond the intended format flip, verify fails."""
    after = _card("C1", ("opus", "opus"))
    after["title"] = "Changed By Server"                    # an unsanctioned change
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "verify-failed"
    assert any("title" in p.lower() for p in res.problems)


def test_verify_passes_when_only_format_changed(tmp_path):
    """The happy path: re-GET differs only in format (+ regenerated URLs/updatedAt)."""
    after = _card("C1", ("opus", "opus"))
    after["updatedAt"] = "2026-07-21T23:59:59Z"             # volatile, must be ignored
    for ch in after["content"]["chapters"]:                 # fresh pre-signed URLs, ignored
        ch["tracks"][0]["url"] = "https://cdn.example/rotated?sig=NEW"
    fake = FakeClient(_card("C1", ("mp3", "mp3")), after=after)

    res = repair_card(fake, "C1", apply=True, backup_dir=tmp_path / "b")

    assert res.outcome == "applied"
    assert res.problems == []
    assert len(fake.posts) == 1


# --- discovery -------------------------------------------------------------

def test_resolve_targets_passes_card_ids_through(tmp_path):
    fake = FakeClient(_card())
    assert resolve_targets(fake, card_ids=["1WCvI", "gzP2B", "7FcVe"], titles=[]) == [
        ("1WCvI", "1WCvI"), ("gzP2B", "gzP2B"), ("7FcVe", "7FcVe")]


def test_resolve_targets_refuses_ambiguous_title():
    summaries = [CardSummary("A", "The Wild Robot", "d1", 5),
                 CardSummary("B", "The Wild Robot 2", "d2", 3)]
    fake = FakeClient(_card(), summaries=summaries)
    with pytest.raises(YotoError) as exc:
        resolve_targets(fake, card_ids=[], titles=["wild"])   # substring-matches both
    assert "disambiguate" in str(exc.value).lower()


def test_resolve_targets_matches_exact_title():
    summaries = [CardSummary("A", "The BFG", "d1", 18),
                 CardSummary("B", "The BFG Read-Along", "d2", 18)]
    fake = FakeClient(_card(), summaries=summaries)
    assert resolve_targets(fake, card_ids=[], titles=["The BFG"]) == [("A", "The BFG")]
```

- [ ] **Step 3: Run.** `python -m pytest tests/test_repair.py -q` — all PASS.
  Then the whole suite: `python -m pytest tests/ -q` — the existing count plus the
  new tests, all green.

- [ ] **Step 4: Commit.**

```bash
git add tests/test_repair.py
git commit -m "test(repair): the six safety guarantees + discovery + verify

Corrector changes ONLY format (deep structural equality, input untouched); a
non-Opus/unprobeable track skips the WHOLE card with no POST; dry-run writes
nothing; an already-opus card is a no-op; the backup exists on disk BEFORE the
POST and holds the ORIGINAL body; the round-trip verify catches an unsanctioned
extra-field change and passes when only format (+ volatile fields) changed.
Plus card-id pass-through and title disambiguation."
```

---

# Task 6: Commit the preparatory architecture docs + bookkeeping

This feature's design basis and the sibling job-system ADR are currently
**untracked**. Commit them as part of this PR (they are preparatory docs, not
source), add the ADR addendum recording the simplification, and finish the queue
row Planner filed.

**Files:**
- Add (commit as-is): `docs/architecture/README.md`,
  `docs/architecture/decisions/2026-07-21-repair-existing-cards.md`,
  `docs/architecture/decisions/2026-07-21-file-upload-on-job-system.md`.
- Modify: `docs/architecture/decisions/2026-07-21-repair-existing-cards.md` — append
  the addendum below.
- Modify: `docs/BUILDER_QUEUE.md` — move item 18 to the appropriate state and record
  the PR (Planner already added the row + briefing).
- Modify: `docs/RELEASE_NOTES.md` — one line under an "Unreleased / tooling" note (no
  version bump).

- [ ] **Step 1: Append this addendum** to
  `docs/architecture/decisions/2026-07-21-repair-existing-cards.md`:

```markdown
---

## Addendum — 2026-07-21: shipped as a simplified CLI utility

The read-only diagnostic this ADR was gated on (Open questions 2 and 3) has run.
It collapsed the problem, and the feature shipped **much smaller** than the 3-PR
arc above:

- **`format` is the only field that needed correcting.** `fileSize`/`duration`
  self-correct server-side and `channels` was already right (all 24 tracks on the
  three cards). So `apply_metadata_corrections` became a `format`-only overwrite.
- **Strategy B is trivial and is the whole story.** `GET /card/{cardId}` already
  returns resolved pre-signed artifact URLs, so no `resolve_artifact_url(sha)` was
  needed — probe the URL directly for Ogg Opus. **Strategy A (re-upload) was
  dropped** (out of scope; the three cards have no source anyway).
- **No shared `TranscodedInfo` type, no `models.py` change, no job-backed server
  routes, no Designer UX.** It ships as a **CLI utility** (`python -m
  yoto_maker.repair`), not a user-facing surface — appropriate for a one-off
  maintainer repair.
- **The ADR's core principles were kept:** account-first discovery, update-in-place
  with `cardId`, all-or-nothing per card, deep-copy-and-overwrite-only, verify-after,
  dry-run-by-default, honest per-card reporting.

Implementation: `yoto_maker/yoto/repair.py` (+ small `yoto_maker/yoto/client.py`
additions + a `yoto_maker/repair.py` CLI shim). Plan:
`docs/superpowers/plans/2026-07-21-repair-existing-cards.md`. Queue item 18.
```

- [ ] **Step 2: Commit the docs.**

```bash
git add docs/architecture/ docs/superpowers/plans/2026-07-21-repair-existing-cards.md docs/BUILDER_QUEUE.md docs/RELEASE_NOTES.md
git commit -m "docs(architecture): commit the repair + job-system ADRs and the arch README

These preparatory docs were untracked. The repair ADR is this feature's design
basis; its addendum records that it shipped as a simplified format-only CLI
utility. Also lands the plan, the queue row (item 18) and a tooling note."
```

> **Note on a fourth untracked file.** `git status` also shows
> `docs/superpowers/plans/2026-07-21-transcoded-metadata-propagation.md` untracked —
> that is **item 17's** plan, not this feature's. Leave it for item 17's bookkeeping,
> or fold it into this docs commit if the maintainer prefers one clean docs sweep;
> either is fine, it is a doc-only file.

---

## Test Plan (stands on its own — no live device, no network)

The consolidated view the merge gate reviews against. Everything is exercised by
the mocked-client tests above.

| # | Assertion | Where |
| --- | --- | --- |
| T1 | Corrector sets `format="opus"` on confirmed tracks and leaves **every** other field byte-identical (deep structural equality); input not mutated. | `test_corrector_sets_only_format_everything_else_byte_identical` |
| T2 | A non-Opus / unprobeable track skips the **whole** card (all-or-nothing) and issues **no POST**. | `test_unprobeable_or_non_opus_track_skips_whole_card_no_post` |
| T3 | Dry run issues **no POST**. | `test_dry_run_issues_no_post` |
| T4 | Idempotency: a card already all-`"opus"` writes nothing, reports "already correct". | `test_idempotent_already_opus_no_post` |
| T5 | The backup file is on disk **before** the POST, and holds the **original** body. | `test_backup_written_before_any_post` |
| T6 | Round-trip verify **fails** on an unexpected extra-field change; **passes** when only `format` (+ volatile fields) changed. | `test_verify_catches_an_unexpected_extra_field_change`, `test_verify_passes_when_only_format_changed` |
| T7 | Probe classifies Opus by Content-Type **and** by `OggS`/`OpusHead` magic; rejects non-Opus; `update_card` injects `cardId` and POSTs `/content`. | `test_probe_*`, `test_update_card_injects_cardid_and_posts_content` |
| T8 | Discovery: cardIds pass through; an ambiguous title raises with candidates; an exact title resolves. | `test_resolve_targets_*` |

**Live run (maintainer, TONIGHT — this is the acceptance test):**

1. **Dry run first, always:**
   `python -m yoto_maker.repair --card-id 1WCvI,gzP2B,7FcVe`
   Expect: each card lists its tracks `mp3 -> opus (…OpusHead…)`, RESULT "WOULD
   correct N track(s)", **no** backup line, **no** write.
2. **Apply:** add `--apply`. Expect: a `backup:` path per card, all tracks corrected,
   "POST ok; verify ok". If any card reports **blocked** or **verify-failed**, it was
   left untouched (blocked) or is flagged for rollback (verify-failed).
3. **Confirm on the physical player:** the offline download that never completed now
   completes. (This is the real-world proof; the suite can't cover it.)
4. **Rollback if needed:** `python -m yoto_maker.repair --rollback <backup path>`.
5. **Idempotency check:** re-run step 1 — every card should now report "already
   correct".

---

## Deviations / notes for the reviewer

- **`models.py` / `build_content_payload` are intentionally untouched and unused.**
  Update-in-place POSTs the deep-copied GET body with only `format` changed;
  rebuilding via `build_content_payload` would drop icons/keys/order. This is the
  central safety decision, not an oversight.
- **The verify is deliberately strict.** It reports *any* residual change beyond the
  intended `format` flip (after ignoring `updatedAt` and the regenerated pre-signed
  URLs). If Yoto legitimately normalises some field server-side on write, the verify
  will surface it as a `verify-failed` for human review rather than accept it
  silently — the safe direction for a live-mutation tool, and the backup is right
  there to roll back from.
- **Three shapes are pinned from a real body (Task 1, Step 0), not guessed.** The
  code ships defensive candidate lists (`_find_chapters`, `_ARTIFACT_URL_KEYS`, the
  `format` path) so it runs before pinning, but the real captured `GET /card` body
  removes the only genuine unknowns. Do this first.
- **`--title` is a convenience with a known trap.** A card's colloquial name may not
  be its real title ("rainbow fairy" is titled "Phoebe The Fashion Fairy"), so title
  matching can miss or collide. Discovery **refuses to auto-pick** an ambiguous
  title. For tonight, use `--card-id` (all three IDs are known).
- **No version bump, no release cut.** Utility run from source; ships in the package
  but needs no `.exe` to run tonight and touches no static asset. Do not touch the
  pending v0.1.11 release.
- **Pre-signed URL expiry (~60 min) is not a concern for one run.** `get_card`
  returns fresh URLs and probing happens seconds later in the same call. If a probe
  ever 403s on an expired URL, just re-run the command (a fresh GET issues fresh
  URLs; the tool is idempotent, so re-running is safe).
```