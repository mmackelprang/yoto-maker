# ADR — "Repair my cards": fix declared track metadata on already-created MYO cards

**Date:** 2026-07-21
**Status:** proposed — needs Mark's approval before Planner picks it up
**Depends on:** queue **item 17** ("transcoded-metadata propagation" —
`_poll_transcode` returns `transcodedInfo`; `build_content_payload` emits it).
This feature reuses item 17's plumbing; it must not duplicate it.

**Decision in one line:** Build it as a **three-PR arc after item 17 ships**,
around a **strategy-agnostic update-in-place core** that a pluggable
`MetadataRecoverer` feeds. **Strategy B (probe the stored artifact) is the
preferred recoverer when viable; Strategy A (re-derive from source) is the
fallback.** The feature repairs cards **all-or-nothing per card**, never
duplicates, and is **honest that it cannot rescue a card that has neither a
resolvable stored artifact nor surviving source.**

---

## 1. Context

### 1.1 The bug this repairs (established; not re-investigated here)

For every track, the app declares `fileSize` / `format` / `duration` /
`channels` from the **local pre-upload MP3** — `format` hardcoded `"mp3"`,
`channels` hardcoded `"stereo"` (`client.py:134-135`, `models.py:19-21`,
`models.py:39-42`). Yoto transcodes server-side and the **true** values live in a
`transcodedInfo` object returned by the transcode-status poll. The `/content`
track should carry those, not the local ones. When they disagree, the physical
player can fail to download/play the card.

Item 17 fixes this **for newly created cards**: `_poll_transcode`
(`client.py:182`) will return `transcodedInfo` alongside the sha, and
`build_content_payload` (`models.py:24`) will emit it. This ADR fixes the
**cards already sitting in users' accounts**, which item 17 does nothing for.

### 1.2 What the app can and cannot do against an existing card (verified)

| Capability | Endpoint / fact | Status |
| --- | --- | --- |
| **Update in place, same card** | `POST /content` with `cardId` in the body updates the *same* card, preserving `cardId` → the physical MYO card's NFC linkage survives, **no duplicate** created. Reference: `bperkinspdx/yoto-mcp-server` `addTrackToCard` (GET-mutate-POST). | **Verified** |
| **List cards** | `GET /content/mine` → `cardId` + `title` (no chapters). | **Verified** |
| **Read one card** | `GET /content/{cardId}` → full chapters/tracks, each with `trackUrl` (`yoto:#<sha>`) and current *declared* metadata. | **Verified** |
| **Fetch true transcoded metadata by sha** | **No documented API.** The card stores only the wrong declared values. | **No such API** |
| **App remembers cards it made** | It does **not**. `CardResult.content_id` (`client.py:56`) is returned as an ephemeral job result at `app.py:658` and dropped. | **Verified** |

Two consequences drive the whole design:

1. Because the app never persisted a `cardId`, the repair flow is **account-first**:
   it lists the live account (`GET /content/mine`) and works from the real
   `cardId`, **not** from the local in-memory draft. There is no reliable local
   record to match against.
2. Because there is **no API to read true metadata by sha**, recovering the
   correct values for an *already-stored* track is the hard part, and there are
   exactly two possible sources for it — §1.3.

### 1.3 The two — and only two — metadata-recovery strategies

**Strategy A — re-derive from source.** Re-run the upload flow with the
**original source audio**, poll transcode, read `transcodedInfo`, then update in
place. Yoto de-dupes on the **source-file sha**: if Yoto still has it cached,
`uploadUrl` comes back null and zero bytes upload (metadata-only, same
`transcodedSha256` → **`trackUrl` unchanged**). Requires the original bytes.
Note the app normalizes + splits into ~50-min parts (`normalize.py`, the
50-minute chunker), so a "track" is a **processed chunk**, not the raw file — see
§6.3 for the reproduction problem. **Unverified caveat:** whether a dedup-hit
`uploadId` still yields `transcodedInfo` when polled. Design must handle "if not,
force a real upload."

**Strategy B — probe the stored artifact.** Resolve the track's
`yoto:#<sha>` to a downloadable URL, `HEAD`/ranged-`GET` it to read the true
`Content-Length` (`fileSize`) and probe `format`/`duration`/`channels`. **Needs
no source audio.** But resolving `yoto:#<sha>` → URL is **undocumented** (only
community web-player scraping, reportedly 404-ing for most cards now).

> **A read-only diagnostic is running right now** against three real cards to
> test whether Strategy B resolves at all. **Everything about Strategy B in this
> ADR is contingent on that result.** Design for it; ship it only if proven.

### 1.4 The honest constraint, stated up front

The maintainer's own three cards — **Wild Robot, Rainbow Fairy, BFG** — have
**no surviving source audio**. For them Strategy A is impossible. **Only Strategy
B, and only if the diagnostic proves it viable for those specific shas, can save
them.** If B is unviable, those three must be **rebuilt from re-sourced audio** —
this feature will not resurrect them. It is still worth building, because it
repairs cards for **every user who still has their source** and it is the
foundation for a "verify/repair" capability across **all future cards**. This ADR
does not pretend otherwise.

### 1.5 Conflict with an accepted decision — surfaced, not overridden

`DESIGN.md §10` lists **"editing existing cards"** as explicitly out of scope for
v1 (YAGNI). This feature *is* editing existing cards. I am **not** silently
overriding that line. The v1 exclusion was about not building a card *editor*;
this is a **targeted correctness repair** for a bug the app itself shipped, which
is a different justification. Mark should confirm he's comfortable revisiting the
§10 boundary for this narrow case before Planner starts (Open question 9.1).

---

## 2. Options considered

**Option 1 — Do nothing.** Item 17 fixes new cards; existing broken cards stay
broken; the maintainer re-creates his by hand. Cost: every user who already made
a card with the buggy version has a card that may not play, and no path back
short of rebuilding. Rejected — but note it is *survivable*, and for **sourceless
cards it may be the only real answer** if Strategy B fails (§1.4).

**Option 2 — Rebuild-and-replace.** For each broken card, re-create the whole
card from source and delete the old one. Rejected: needs source (so no better
than Strategy A for the hard cases), and **breaks NFC linkage / creates a
duplicate** unless it reuses the same `cardId` — at which point it *is* the
update-in-place path, just with more thrown away.

**Option 3 — One big "repair everything" button** that scans, recovers, and
writes in a single sweep. Rejected: it mutates live cards with the least possible
user control, makes partial-failure reporting hardest, and couples the
read-only-safe discovery to the risky write. The write surface must be
per-card and explicit.

**Option 4 (recommended) — A strategy-agnostic update-in-place core fed by a
pluggable recoverer, delivered as a 3-PR arc after item 17.** Read-only
discovery first, then the write path with Strategy A, then Strategy B as a
conditional add-on. §3.

---

## 3. Decision

### 3.1 Shape of the whole thing

```
GET /content/mine ──► discover cards (real cardId, never the local draft)
        │
        ▼
GET /content/{id} ──► parse tracks: trackUrl(sha) + declared metadata
        │
        ▼
  per track: recover TRUE metadata via a MetadataRecoverer chain
        │            (B preferred when viable → A fallback → give up)
        ▼
  compare recovered vs declared:
        equal   → track already correct, skip
        differ  → stage a correction
        │
        ▼
  ALL required tracks recovered?
        no  → abort this card, write NOTHING, report what blocked it
        yes → apply corrections onto the GET'd body (mutate copy),
              POST /content WITH cardId  ──►  re-GET, verify, report
```

The core (`diagnose → stage corrections → all-or-nothing write → verify`) is
**strategy-agnostic**. Strategy A and Strategy B are just two implementations of
one `MetadataRecoverer` interface (§3.4). This is the single most important
structural decision: it lets Strategy B land later (or never) without touching
the write path, and it makes the A-vs-B choice a per-track policy, not an
architecture fork.

### 3.2 Where the code lives

| Concern | Location | Why |
| --- | --- | --- |
| Thin API wrappers (list, get, update-with-cardId, artifact-probe) | **`yoto/client.py`**, alongside the existing `_request_upload_url` / `_poll_transcode` / `_create_content` | They are HTTP shapes; they belong with their siblings and share `_dig`, `_headers`, `_friendly_http`. |
| The corrected-payload builder | **`yoto/models.py`**, next to `build_content_payload` | Pure logic, unit-testable with no network — same reason `build_content_payload` lives there. |
| Orchestration: diagnose, recover, all-or-nothing, verify | **new `yoto/repair.py`** | It is a *service* that composes the client; keeping it out of `client.py` keeps the client a transport and lets repair be tested against a mocked client. |
| HTTP surface for the UI | **`server/app.py`** routes on the **existing job system** (`app.py:697`, `jobs.py:45`) | Strategy A does uploads/transcodes = minutes; it must be a background job like `/api/send`. |

### 3.3 API-surface additions (concrete shapes)

**One shared "true metadata" type** — the thing both strategies produce and the
corrector consumes. Item 17 introduces its emission; make it a named type both
features share rather than a loose dict:

```python
# yoto/models.py  (shared with item 17 — coordinate the exact fields with it)
@dataclass
class TranscodedInfo:
    file_size: int
    fmt: str            # the REAL container/codec Yoto produced, not "mp3"
    duration_s: float
    channels: str       # "stereo" | "mono", from the artifact, not assumed
    sample_rate: int | None = None
```

**Client wrappers** (`yoto/client.py`, new methods on `YotoClient`):

```python
def list_my_cards(self) -> list[CardSummary]:            # GET /content/mine
    # CardSummary: {card_id, title, updated_at, track_count?}

def get_card_content(self, card_id: str) -> CardContent: # GET /content/{card_id}
    # CardContent: {card_id, title, raw: dict, tracks: list[TrackView]}
    # TrackView: {chapter_key, track_key, title, sha, declared: TranscodedInfo}
    # `raw` is the verbatim GET body — the thing we mutate and POST back.

def update_content(self, card_id: str, body: dict) -> CardResult:
    # POST /content with body["cardId"] = card_id. Reuses _create_content's
    # request/error handling; add an optional card_id param to _create_content
    # rather than forking it (the endpoint is one "create-or-update").

# Strategy A — reuse the item-17 flow, stop before content creation:
def recover_metadata_via_upload(self, audio_path: Path) -> TranscodedInfo:
    # _request_upload_url → (dedup? null uploadUrl : _put_audio) →
    # _poll_transcode returns (sha, transcodedInfo). Return the info.
    # Handle the §1.3 caveat: if a dedup hit yields no pollable info, force a
    # real PUT and re-poll.

# Strategy B — CONDITIONAL on the running diagnostic:
def resolve_artifact_url(self, sha: str) -> str | None:  # undocumented; may 404
def probe_stored_artifact(self, sha: str) -> TranscodedInfo | None:
    # HEAD for Content-Length (fileSize); ranged GET → ffprobe for
    # fmt/duration/channels. Returns None if unresolvable → caller falls back.
```

**The corrector** (`yoto/models.py`) — the safety-critical function. It does
**not** rebuild via `build_content_payload` (that would discard icons, custom
chapter/track keys, ordering, and any field the app doesn't model). It
**deep-copies the GET'd body and overwrites only the metadata fields** on
matching tracks:

```python
def apply_metadata_corrections(
    card_body: dict,                       # verbatim GET /content/{id} body
    corrections: dict[str, TranscodedInfo] # keyed by track sha (or chapter/track key)
) -> dict:
    # Returns a NEW body with, per corrected track, only:
    #   format, fileSize, duration, channels   ← from TranscodedInfo
    # Everything else byte-identical: title, trackUrl/sha, keys, display.icon16x16,
    # chapter structure, order. Recompute metadata.media.{duration,fileSize} aggregates.
    # Set body["cardId"]; strip server-managed read-only fields the POST rejects
    # (createdAt/updatedAt/userId — confirm the exact set against the live round-trip).
```

**Server routes** (`server/app.py`, described for Planner — not built here):

| Route | Kind | Purpose |
| --- | --- | --- |
| `GET /api/repair/scan` | job | List cards, diagnose each (read-only; Strategy-B probe when viable, else "suspected/unknown"). Returns per-card health. |
| `POST /api/repair/card/{cardId}` | job | Recover + all-or-nothing update-in-place for one card. `?dry_run=1` returns the diff without writing. |

Both return `{"job_id": ...}` and are polled via the existing `/api/jobs/{id}`
(`app.py:697`). No new async idiom.

### 3.4 The recoverer interface and the A-vs-B policy

```python
# yoto/repair.py
class MetadataRecoverer(Protocol):
    def recover(self, track: TrackView) -> TranscodedInfo | None: ...

class ArtifactProbeRecoverer:      # Strategy B — probe_stored_artifact(sha)
class SourceReuploadRecoverer:     # Strategy A — recover_metadata_via_upload(chunk)
```

**Per-track policy (recommended):**

1. **Try Strategy B first when it is available** (diagnostic proved it viable
   *and* this sha resolves). Preferred because it needs **no source**, reads the
   **ground truth of the exact bytes the device downloads**, never re-uploads,
   and trivially preserves `trackUrl`. It is also cheap (a `HEAD` + a small
   ranged read).
2. **Else, if the user has supplied matching source** for this card, use
   **Strategy A**.
3. **Else, give up on this track** — record it as unrecoverable with the reason
   ("no way to read the stored file, and no source provided").

B's viability is **per-sha**, not global: the chain tries B, and on `None` falls
back to A, per track. The card-level outcome is then decided by §3.5.

### 3.5 Idempotency, all-or-nothing, preserve-on-failure

- **Idempotent by construction.** A track whose recovered metadata *equals* its
  declared metadata is skipped — no correction staged. Re-running repair on an
  already-fixed card stages zero corrections and **writes nothing**. This also
  means the feature needs no "was this card already repaired?" bookkeeping.
- **Never duplicates.** Every write is `POST /content` **with `cardId`** → the
  same card. There is no code path that creates a card in this feature.
- **Preserve title, icons, keys, ordering.** Guaranteed because §3.3's corrector
  mutates the GET'd body instead of rebuilding it.
- **All-or-nothing per card.** Recover **every** track that needs it *first*,
  assemble the full corrected body, and **POST once**. If any required track
  fails recovery, **abort the card with zero writes** and report which tracks
  blocked it. The original card is left **untouched** — we never POST a
  half-corrected body. (A future "repair what you can" partial mode is possible,
  but the safe default is all-or-nothing, per the brief.)
- **Verify after write.** Re-`GET` the card and confirm the corrected fields now
  match the recovered values before reporting success.

### 3.6 Trigger surface (high level — Designer owns the UX)

**Recommend both, sequenced as scan-then-fix:**

- A **"Scan my cards"** sweep is the entry point. It is **read-only** — it lists
  the account and reports per-card health. It is safe to run anytime and writes
  nothing. (With Strategy B viable it can confirm brokenness; without it, it can
  only mark cards *suspected* affected by signature — §6.1.)
- A **per-card "Repair this card"** action is the only thing that writes, and it
  is explicit per card. `dry_run` shows the exact before/after diff first.

This keeps the dangerous surface (live mutation) small, explicit, and per-card,
while the safe surface (discovery) can be broad. Detailed UX — how source is
attached for Strategy A, how title collisions are disambiguated, copy for the
"can't fix this one" state — is **deferred to Designer**.

### 3.7 The arc: three PRs after item 17

| PR | Delivers | Depends on | Ships value even if the next never lands? |
| --- | --- | --- | --- |
| **PR 1 — Discovery + diagnosis (read-only)** | `list_my_cards`, `get_card_content`, `CardContent`/`TrackView` parsing, `GET /api/repair/scan`, per-card health report. **No writes.** | item 17 (for the `TranscodedInfo` type only; can stub) | Yes — the user learns which cards look broken. |
| **PR 2 — Update-in-place core + Strategy A** | `apply_metadata_corrections`, `update_content` (POST-with-cardId), `recover_metadata_via_upload`, the `MetadataRecoverer` chain with **A only**, all-or-nothing, verify, `POST /api/repair/card/{id}`. **First PR that fixes cards** (for users with source). | item 17 (hard — reuses its upload/transcode/`transcodedInfo`), PR 1 | Yes — coherent and useful with A alone. |
| **PR 3 — Strategy B recoverer (CONDITIONAL)** | `resolve_artifact_url`, `probe_stored_artifact`, `ArtifactProbeRecoverer` plugged in front of A in the chain. **Only build if the diagnostic proves B viable.** | PR 2's core (drops in as a recoverer — no core change) | This is the **only** PR that can help **sourceless** cards. |

**Sequencing:** item 17 → PR 1 → PR 2 → PR 3 (conditional). PR 2 builds the
strategy-agnostic core so PR 3 is a pure add-on. **This is an arc, not one PR** —
the write path must not land in the same reviewable unit as discovery, and
Strategy B's viability is still unknown.

---

## 4. Consequences

### 4.1 Good

- Users who still have their source can repair broken cards **in place**, keeping
  the physical card's NFC binding — no re-tap, no duplicate.
- The repair is **idempotent** and **all-or-nothing**, so it is safe to re-run and
  never leaves a card half-fixed.
- The `list_my_cards` / `get_card_content` / `update_content` wrappers are a
  reusable **account-read/write surface** — the first time the app can see and
  edit cards it didn't just create. Future features (verify-on-open, bulk
  re-icon, rename) can build on them.
- The strategy-agnostic core means **Strategy B is a drop-in**, and its absence
  costs nothing structurally.
- Diagnosis (PR 1) delivers value with **zero write risk**.

### 4.2 Bad — the parts that are the reason this file exists

1. **It mutates live production cards.** Every successful repair rewrites a real
   card in the user's account. A logic bug in `apply_metadata_corrections`
   damages real data. Mitigations: `dry_run` diff, all-or-nothing, verify-after,
   and **golden-body round-trip tests** (GET body in → assert only the four
   fields changed → out). This corrector needs the most test coverage in the arc.
2. **Sourceless cards may be unfixable.** §1.4. If Strategy B fails the
   diagnostic, the maintainer's three cards — and any user in the same
   position — **cannot** be repaired by this feature and must be rebuilt. The
   feature must **say so per card**, not silently skip.
3. **Title-based association is a wrong-card hazard for Strategy A.** The feature
   identifies cards by real `cardId` (safe), but attaching a user-provided source
   file to *the right card* relies on title + `createdAt` + track count, which can
   collide. A mis-association would upload the wrong audio's metadata. Mitigation:
   never auto-associate silently — surface `createdAt`, track count, and track
   titles and require explicit selection (Designer owns the UX; the risk is
   real).
4. **Strategy A can change the sha.** If reproduced chunk bytes aren't
   byte-identical to the original (non-deterministic normalize/split — §6.3),
   Yoto won't dedup, a **new** `transcodedSha256` is minted, and the repaired
   track points at a fresh (correct) artifact instead of the original. Functionally
   a valid repair, but it is **not** the pure metadata-only fix it appears to be,
   and it means Strategy A is not guaranteed to preserve `trackUrl`. State this to
   the user rather than implying "we only touched the numbers."
5. **The dedup/`transcodedInfo` caveat is unverified.** §1.3: a dedup-hit
   `uploadId` may not yield pollable `transcodedInfo`. PR 2 must handle the
   "force a real upload" branch, which turns a claimed metadata-only operation
   into a full re-upload (minutes, bandwidth).
6. **Strategy B is undocumented and may rot.** Even if the diagnostic passes
   today, sha→URL resolution is community-observed, not contract. It can 404
   tomorrow. PR 3's recoverer must fail soft (return `None` → fall back / report),
   never hard.

### 4.3 Neutral, worth stating

- The **local draft is irrelevant** to this feature — it operates on the account,
  not `get_draft()`. No change to `draft.py`.
- The job system's known gaps (no cancel, no eviction — see the file-upload ADR)
  apply here too. A Strategy-A repair of a 10-part audiobook is ten uploads and
  can't be cancelled today. Not this ADR's problem to solve, but worth flagging
  that it inherits that limitation.

---

## 5. Related

- **Depends on:** queue **item 17** — transcoded-metadata propagation. This ADR
  reuses item 17's `_poll_transcode`→`transcodedInfo` path and shares the
  `TranscodedInfo` type. Coordinate the exact field set with item 17 so there is
  one shape, not two.
- **Prior ADR / job-system reality:**
  [`2026-07-21-file-upload-on-job-system.md`](2026-07-21-file-upload-on-job-system.md)
  — the job system's missing cancel/eviction (its §1.2) is inherited here.
- **Code this designs against:** `yoto/client.py` (`create_card` :93,
  `_request_upload_url` :146, `_put_audio` :165, `_poll_transcode` :182,
  `_create_content` :256, `CardResult` :56), `yoto/models.py`
  (`build_content_payload` :24, `TrackMeta` :11), `server/app.py`
  (`/api/send` :631, `/api/jobs/{id}` :697), `server/jobs.py`
  (`JobManager.start` :45), `config.py` (`YOTO_API_BASE` :181).
- **Accepted decision this revisits:** `DESIGN.md §10` ("editing existing cards"
  out of scope) — §1.5 above. Surfaced for Mark, not overridden.
- **Reference client:** `github.com/bperkinspdx/yoto-mcp-server` `addTrackToCard`
  (the GET-mutate-POST update-in-place pattern).
- **Live evidence pending:** the read-only Strategy-B diagnostic against three
  real cards. **Its result gates PR 3 and gates §1.4's verdict for sourceless
  cards.**

---

## 6. Deeper notes the implementer will need

### 6.1 Detecting "broken" without recovery (for the read-only scan)

The authoritative test is *recover → compare*. But PR 1's scan may run before any
recoverer exists, or on a sourceless card with B unavailable, and still wants to
say something. The **signature of the bug** is `format == "mp3"` **and**
`channels == "stereo"` on every track (the hardcoded values). If Yoto's transcode
produces a non-`mp3` container (item 17's research will confirm what
`transcodedInfo.format` actually is), then `format == "mp3"` is a strong
*suspected-affected* marker. **Label it suspected, never confirmed**, until a
recoverer proves the mismatch.

### 6.2 The POST round-trip shape (verify against the live API)

`GET /content/{id}` returns server-managed fields (`createdAt`, `updatedAt`,
possibly `userId`, `contentId` vs `cardId`) that the update `POST` may reject or
ignore. The corrector must send `cardId` and the mutated `content`/`metadata`/
`title`, and strip whatever the API refuses. **The running read-only diagnostic
can capture an exact GET body** — use it to pin the precise round-trip shape
before PR 2, rather than guessing.

### 6.3 Strategy A's chunk-reproduction problem

A "track" is a ~50-min **processed chunk**, not the raw source. To recover chunk
*N*'s metadata via Strategy A, the app must re-run `normalize → split` on the
original source and take part *N*, matching chunks to tracks **by ordinal**
(track 1 = part 1). This holds for the common one-source-audiobook-per-card case.
It breaks for cards assembled from **multiple** sources or hand-reordered tracks —
those need explicit per-track source mapping (Designer + a later PR). If
normalize/split is non-deterministic, the reproduced chunk won't dedup (§4.2.4).
PR 2 should first confirm whether the pipeline is byte-deterministic; if it is,
Strategy A is a clean metadata-only fix, and if not, it is a re-upload.

---

## 7. Verdicts asked for in the brief

- **Recommended flow:** account-first discovery (`/content/mine` →
  `/content/{id}`) → per-track recover via a `MetadataRecoverer` chain → compare
  vs declared → **all-or-nothing** `apply_metadata_corrections` →
  `POST /content` **with `cardId`** → re-GET verify → per-card/per-track report.
- **A vs B:** **B preferred when viable** (no source, ground truth, no re-upload,
  preserves `trackUrl`); **A is the fallback** when B doesn't resolve *and* the
  user has source; **give up per-track** otherwise. Chosen per track, degrading
  gracefully, with full per-track reporting.
- **API surface:** `list_my_cards`, `get_card_content`, `update_content`
  (POST-with-`cardId` via an optional param on `_create_content`),
  `recover_metadata_via_upload` (Strategy A, reuses item 17), and
  `resolve_artifact_url` + `probe_stored_artifact` (Strategy B, conditional) — all
  in `client.py`; `apply_metadata_corrections` + `TranscodedInfo` in `models.py`;
  the orchestrator + recoverers in a new `yoto/repair.py`; two job-backed routes
  in `app.py`.
- **Sourceless cards:** **Honestly, no — unless Strategy B proves viable.**
  Wild Robot / Rainbow Fairy / BFG have no source, so only B can save them, and B
  is unproven. If B fails, they must be rebuilt. The feature is still worth
  building for users who have source and for all future cards.
- **PR shape:** a **three-PR arc after item 17** — read-only discovery, then the
  update-in-place core + Strategy A, then Strategy B as a conditional drop-in
  recoverer. **Hard dependency on item 17** for the transcode/`transcodedInfo`
  plumbing and the shared `TranscodedInfo` type.

---

## 8. Consequences the UX pass must resolve (flagged, not specified)

Designer owns these; naming them so they aren't discovered mid-build:

1. How the user **attaches source** for Strategy A, and how a source file is
   mapped to the right card/tracks when titles collide.
2. Copy for the **"we couldn't fix this card"** state, distinguishing
   *no-source-and-B-unavailable* from *B-resolved-but-probe-failed*.
3. Whether the scan presents **suspected** vs **confirmed** brokenness (§6.1) and
   how that uncertainty is worded.
4. The **`dry_run` before/after diff** presentation — what "we're about to change
   these four numbers on these tracks" looks like.
5. Whether Strategy A's possible **sha change** (§4.2.4) needs to be surfaced to
   the user ("this re-uploads the audio") or can stay silent.

---

## 9. Open questions

1. **Does Mark accept revisiting `DESIGN.md §10`** ("editing existing cards" out
   of scope) for this narrow repair case? (§1.5.) **Mark decides** before Planner
   starts.
2. **Is Strategy B viable?** The running diagnostic decides. Its result gates
   whether PR 3 is built at all and whether the sourceless cards have any path.
   **Diagnostic decides; Mark confirms scope of PR 3.**
3. **Exact `POST /content` update round-trip shape** — which server-managed fields
   to strip (§6.2). **Resolved from the diagnostic's captured GET body; confirmed
   by Planner against the live API.**
4. **Is the normalize/split pipeline byte-deterministic** enough for Strategy A to
   dedup and stay metadata-only (§6.3)? **Planner/Builder verifies in PR 2.**
5. **Does a dedup-hit `uploadId` yield pollable `transcodedInfo`** (§1.3 caveat)?
   **Builder verifies in PR 2; the "force real upload" branch ships regardless.**
6. **Partial-repair mode** (fix the tracks we can, leave the rest) — deferred; the
   safe default is all-or-nothing. Revisit only if users ask. **Future.**

---

## Addendum — 2026-07-21: shipped as a simplified CLI utility

The read-only diagnostic this ADR was gated on (Open questions 2 and 3) has run.
It collapsed the problem, and the feature shipped **much smaller** than the 3-PR
arc above:

- **`format` is the only field that needed correcting.** `fileSize`/`duration`
  self-correct server-side and `channels` was already right (all 24 tracks on the
  three cards). So `apply_metadata_corrections` became a `format`-only overwrite
  (`apply_format_corrections`).
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

### What the build's Step-0 pinning changed vs this ADR (Open question 3, resolved)

The plan told Builder to pin the exact `GET /card/{id}` shapes against a real body
before writing code. It did (read-only `GET /card/gzP2B`), and reality differed
from the plan's literal assumptions in two load-bearing ways — captured here so the
decision record stays honest:

- **The GET body is wrapped**: `{"card": {…}, "ownership": {…}}`. `client.get_card`
  unwraps to the inner `card` object; that inner object (fields: `content`,
  `metadata`, `title`, `cardId`, `userId`, `createdAt`, `updatedAt`) is what is
  backed up, deep-copied, mutated (format only) and POSTed back to `/content`. The
  inner shape is a superset of what `build_content_payload` produces, so the
  GET-mutate-POST round-trip is well-formed.
- **The pre-signed artifact URL is `trackUrl` itself** — a full
  `https://secure-media.yotoplay.com/…?Expires=…&Signature=…#sha256=<sha>` URL, not
  the `yoto:#<sha>` reference the plan assumed. Yoto resolves `yoto:#` refs to signed
  CDN URLs on GET (icons too). Two consecutive GETs returned the **same** signed URL
  (stable within the ~60-min signing window; the `#sha256=` fragment and the path
  token both carry the artifact sha). So `_ARTIFACT_URL_KEYS` leads with `trackUrl`,
  and the round-trip **verify normalizes signed URLs to their sha-bearing path**
  before diffing — ignoring signature rotation but still catching a real artifact
  remap. The served `Content-Type` is a bare `audio/ogg` (no `codecs` param), so the
  `OggS`/`OpusHead` magic-byte sniff — not the Content-Type check — is what confirms
  Opus in the field.

Implementation: `yoto_maker/yoto/repair.py` (+ `yoto_maker/yoto/client.py`
additions: `list_my_cards` / `get_card` / `update_card` / `probe_artifact` + a
`yoto_maker/repair.py` CLI shim). Plan:
`docs/superpowers/plans/2026-07-21-repair-existing-cards.md`. Queue item 18.
