# Builder queue

**Last updated:** 2026-07-21 by Builder — **item 18 in flight: the card-format
repair CLI** (`python -m yoto_maker.repair`) that fixes existing cards' declared
`format` (mp3 → opus) **in place**, on branch `feat/repair-existing-cards`. The
read-only Step-0 diagnostic ran and **pinned the real `GET /card/{id}` shape**:
the body is wrapped as `{"card": {...}, "ownership": {...}}` (client unwraps it),
and each track's pre-signed artifact URL is on **`trackUrl`** itself (a
`https://secure-media.yotoplay.com/…?Signature=…` URL, not the `yoto:#sha` the
plan assumed) — so the plan's literal code was adapted at exactly the step it
told Builder to pin. `gzP2B`'s single artifact was probed read-only and
confirmed **Ogg Opus** (`OggS`/`OpusHead`; served `Content-Type: audio/ogg`, no
`codecs` param). Dry-run by default, backup-before-write, all-or-nothing,
verify-after; **no version bump**. Suite **244 passed**. **This PR does NOT run
`--apply`** — the live 3-card repair is the coordinator's separate post-merge
step. **Bookkeeping reconciled in this same edit:** items 13 (PR #19) and 17
(PR #18) are both on `main` and now sit in the Shipped table (13's stale
in-flight Queue row is retired); item 18 has a Queue row + briefing below.

Previously: 2026-07-21 by Builder — **item 17 shipped: Yoto's true
transcoded `format` now flows into the card payload**
([PR #18](https://github.com/mmackelprang/yoto-maker/pull/18)). The card
previously advertised `format: "mp3"` for every track while Yoto actually serves
**Ogg Opus**. **The scope was narrowed from the original plan after a live
capture:** a real upload→transcode-poll confirmed `transcodedInfo.format ==
"opus"` (a child of `transcode`), and a read-only diagnostic on the three real
cards showed declared `fileSize`/`duration` **already match** the served values —
Yoto self-corrects those server-side. So the fix is **format-only, best-effort**:
a missing/misshapen `transcodedInfo` degrades to the local probe and still builds
the card (it can NEVER block card creation), and `channels` stays the existing
`"stereo"`/`"mono"` string. The wider fail-loud / fileSize-propagation / int-
channels design was tried and reverted. Backend-only, **no version bump** — rides
the next release cut. Item 17 landed independently of **item 13 (PR #19), which
merged to `main` just before it**; both edit this queue file but no code files
overlap. Suite **142 passed**; pre-merge review clean. On-device confirmation that
`format: "opus"` cures the physical player's stuck offline download is the
post-merge maintainer step.

Previously: 2026-07-21 by Builder — **item 13 claimed and in flight.**
Branch `feat/client-id-validation-and-multi-upload`; shipping as v0.1.11 in the
four commit stacks (0 → A → B → C) the plan mandates. **Protocol override for
this item: it will be taken to green and left awaiting maintainer sign-off, NOT
auto-merged** — Item A is auth-adjacent (it rewrites the Client ID / sign-in
flow) and falls under the "pause before merge on anything sensitive" rule.

Previously: 2026-07-21 by Planner — **two queue edits, no new feature spec.**
(1) The latent **HTTPException-copy-loss bug is now folded into item 13** as a new
Stack 0 task (**Task 1b**): `api()` gains a string-guarded `data.detail` fallback so
every `HTTPException` message becomes visible, with a copy audit of all eleven
raises and the one developer-ish string (`Unknown icon`) softened. Item 13 is now
**20 tasks**; its row, briefing, and the plan's §Commit stacks / §Deviations /
§For the queue / Test Plan §L are all updated. (2) **The job-system arc from the
file-upload ADR is now tracked as three dependency-ordered rows — items 14 (PR A),
15 (PR B), 16 (PR C)** — deliberately not collapsed, because PR A is independently
shippable. All three are **⛔ blocked on item 13 shipping first and on ADR
approval** (the ADR is still `proposed`); PR C additionally needs a maintainer
**go/no-go** before it is planned. See the arc briefing.

Previously: 2026-07-21 by Planner — **item 13 filed and planned: Client ID
validation + multi-file audio upload, one PR in three commit stacks, shipping as
v0.1.11.** It answers a real incident — the maintainer's daughter typed her email
address into the Client ID field, the app saved it and called `logout()`,
destroying her working session behind an opaque Auth0 error. Item A (stacks 0+A)
prevents that class of failure; Item B (stack B) is the unrelated multi-file
upload that ships alongside. **Read the row's briefing notes before starting —
the commit-stack ordering is a hard shipping constraint, and three findings in
the plan are exactly the things that get lost between spec and build.** The plan
also builds the three job-system-ADR seams (S1/S2/S3) into Item B; **that arc
itself is out of scope for this PR.**

Previously: 2026-07-20 by Builder — **v0.1.10 is released. Items 8 and 9
are both `🚢 released`.** PR #16 merged as `be93ee1` after both gates cleared;
tag `v0.1.10` → `715bd1c` on the remote; `YotoMaker.exe` (127,040,616 bytes)
uploaded. Suite **137 passed**. Release:
<https://github.com/mmackelprang/yoto-maker/releases/tag/v0.1.10>

**The update path was verified end-to-end, not assumed** — the same check
v0.1.9's release cut introduced. A client spoofed to `0.1.9`, with **no
`YOTO_LATEST_VERSION` override** (it short-circuits the API call at
`updater.py:80` and would test the override instead of the release), hits the
real releases API and gets `update_available: true`, `latest: "0.1.10"`, and a
`download_url` answering **200 at 127,040,616 bytes** — byte-identical to the
uploaded asset. A v0.1.10 client correctly gets no banner. **The user's live
v0.1.9 install on port 8777 should now offer them this update**, which is the
end-to-end proof that v0.1.9's release-path work holds.

**Both PR #16 gates cleared, and the MEDIUM was this PR marking its own
homework.** Polisher: 0 HIGH, 1 MEDIUM, 2 LOW. Tester: 12 flows passed, 0
failed, 0 HIGH, 0 MEDIUM, 3 LOW. The MEDIUM was that `styles.css` asserted
Designer's **derived** figures (4.97 / 5.81) as measured — line 73 literally
said the pair *"measures 4.97:1"* — in the very PR that took the real
measurement. Fixed in `292550f`, along with the missing supersession pointer in
`tokens.md`. Polisher's two LOWs are queued as items **11** and **12**; Tester's
methodology LOW is recorded with the methodology in `tokens.md` §2b.

**The regression test nobody specced is now in the tree.** Tester drove a live
connected↔disconnected transition with no reload; since PR #16 made the copy
state-dependent inside `renderStatus()`, that is this change's primary
regression guard and static markup assertions structurally cannot cover it.
`tests/test_settings_link_transition_e2e.py` is the repo's **first e2e spec** —
it drives the flip through the app's own `refreshStatus()` rather than writing
`textContent` itself, and **five mutations were verified failing**, including
the one-way-flip case every static assertion passes. It skips cleanly when
playwright or its browser is absent, so it does not become a second instance of
item 3; playwright is now declared in dev extras rather than left ambient.

**One thing shipped unverified again, deliberately:** the screen-reader
announcement on `#yotoPill`'s new accessible name. NVDA is still not installed
and Narrator's speech still cannot be captured as text, so **nobody has heard
it** — the accessibility tree is consistent with the expected utterance, but
that is an argument from construction. Recorded under **Not verified in
v0.1.10** in `docs/RELEASE_NOTES.md` and in the GitHub release body, exactly as
v0.1.9's reveal toggle was. Anyone with a screen reader can close both in about
a minute.

Previously: 2026-07-20 by Builder — **item 9 shipped as
[PR #16](https://github.com/mmackelprang/yoto-maker/pull/16), open and
deliberately not merged: Tester and Polisher gate this one.** All 7 tasks done,
suite **133 passed**. **Item 5 is retired** — absorbed and delivered by Tasks
3–5, as its Designer pass specified.

**The contrast numbers were re-measured live from rendered pixels, not asserted
from the spec** — the whole point, given PR #10's UAT produced three false
readings from cached CSS. Sampled from element screenshots with PIL: label at
rest **5.03:1** (spec predicted 4.97), hover **5.87:1** (5.81), green dot
**3.93:1** (3.88), amber dot **3.53:1** (3.48). Every figure lands slightly
*better* than Designer's independent sweep, on both a hard-reloaded and a
naturally-loaded page. Alpha `0.28` stands; the `0.32` escape hatch in
`tokens.md` §2b was not needed.

**Which set supersedes which is now stated in the tree, not just here.**
`tokens.md` §2b opens with a provenance box marking every figure in that section
as *derived*, tabling it against both independent measured sets, and saying the
measured set wins; §4's certification table carries the measured values with the
derived ones noted alongside. `styles.css` marks its three derived figures as
derived and cites the measured value beside each, guarded by a test. Tester's
independent run read **5.09 / 5.95**, agreeing with PR #16's 5.03 / 5.87 to
within a rounding step and, like it, landing better than derived.

**A sampling hazard is recorded with the methodology** (`tokens.md` §2b): naive
whole-element sampling of `.pill` returns a spurious **3.30:1** from
rounded-corner antialiasing, where the fill fades into bare gradient. Those
pixels have no label drawn over them, so the pair they describe never renders.
Sample the fill's interior, inset past the corner radius. Written down so a
future pass does not re-derive a false failure and "fix" a control that passes.

**The defect was reproduced live on the pre-PR build before being fixed.** The
still-running **v0.1.9** `.exe` on port 8777 served as a control: in the
connected state it reports `#advRow` inside `#connectRow`, `#connectRow` hidden,
and `advRowVisible: false` — the one contextual way into Settings literally
unrenderable, exactly as the field report described. **One new finding, filed
below as item 10** (pre-existing 320px header wrap, proven not ours).

*(That control was first written up as "the still-running v0.1.10 `.exe`", which
is self-contradictory — v0.1.10 is the release this PR is part of. It is v0.1.9,
which is the correct pre-PR baseline, so the control was valid and every
conclusion drawn from it stands. Corrected here and in PR #16's body.)*

Previously: 2026-07-20 by Builder — **item 8 is merged** as
[PR #15](https://github.com/mmackelprang/yoto-maker/pull/15), merge commit
`77d499c`. **No release cut yet, deliberately:** item 9 ships in the same
v0.1.10, so the tag, the `.exe` and the GitHub release all wait for it. Item 8
is therefore `✅ merged` and not `🚢 released` — the distinction this queue
introduced after v0.1.9 sat merged-but-unreleased for a day. **Item 9 is next
and is now in flight.**

Previously: 2026-07-20 by Builder — item 8 shipped as PR #15. All 7 tasks done, suite
**120 passed**, verified from the frozen `.exe` as well as from source. The
poisoned-cache repair was measured for real — cache never cleared, F5 not
Ctrl+Shift+R — and the pre-fix document was confirmed serving from cache with
**zero network requests**, which is the plan's linchpin claim measured rather
than assumed. Review found the plan's "complete surface" claim was wrong:
`logo.png` was a third unstamped asset, now fixed and guarded by a sweep rather
than a filename list. **Item 9 rebases onto the `0.1.10` bump this PR owns.**

Previously: 2026-07-20 by Planner — **item 9 filed and planned: a
connected user cannot find the way into Settings.** Reported from the field by
the user, who knew the feature existed, had approved its design, was actively
looking, and still could not find it. It is a **vocabulary** failure, not a
visibility one, and the plan is deliberately built on only the uncontaminated
half of the evidence — read its briefing notes before starting. **It absorbs
item 5**, which is now planned rather than blocked-pending-Designer.

**Items 8 and 9 both ship in v0.1.10 and are two PRs, not one.** Item 8 owns the
version bump; item 9 must not also bump. Prefer shipping 8 first — its version
stamp is what lets an already-poisoned browser receive item 9's fix at all.

Previously: 2026-07-20 by Planner — **item 8 filed and planned: the stale
asset bug.** It is the highest-priority row on this list. It has plausibly
degraded every release since v0.1.5, it fails silently and partially against the
user least able to work around it, and **we filed it twice as a testing hazard
rather than the shipping bug it is** — see its briefing notes. Ships in v0.1.10.

Previously: 2026-07-20 by Builder — item 7 shipped, and **v0.1.9 is now
genuinely released**: tag `v0.1.9` pushed to origin, `YotoMaker.exe` built and
uploaded, and the update path verified end-to-end (a spoofed v0.1.8 client is
offered v0.1.9 by the real releases API). Items 1 and 7 are the first rows to use
the `🚢 released` state the same PR introduced. Items 2–6 re-checked against the
code and all still accurate.

Previously: item 1 merged as PR #10 but sat merged-but-unreleased for a day —
the gap that motivated the vocabulary split below. Items 4, 5 and 6 were filed
from that PR's Tester and Polisher gates; like items 2 and 3, all are
pre-existing and were deliberately left out of its scope.

Work items that have an approved design and a complete implementation plan, ready
for Builder to ship one PR per row. Planner appends; Builder claims, ships and
marks done. **Priority order is the user's to set** — Planner does not reshuffle.

Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ merged · 🚢 released

**`✅ merged` is not `🚢 released`.** Merged means the PR is on `main`. Released
means a tag is pushed, an `.exe` is built and a GitHub release carries it — which
is the only thing `updater.py` can see, and therefore the only thing a user can
receive. A row moves to 🚢 only when `gh release view v<version>` returns a
release with an uploaded `.exe` asset. **Paste that command's output into the
row's PR or the commit that marks it.** v0.1.9 sat merged-but-unreleased for a
day because these two states shared one word.

---

## Queue

| # | Status | Item | Spec | Plan | Depends on | Notes |
|---|--------|------|------|------|-----------|-------|
| 2 | 📋 | **`--port` flag doesn't move the OAuth redirect URI** — the flag changes the listening port but not `cfg.port`, so Yoto sign-in always redirects to 8777 | _needs Planner pass_ | _needs Planner pass_ | — | Pre-existing in v0.1.8 and documented in `--help`. Small fix, but it touches the OAuth redirect — wants a plan before someone changes it blind. |
| 3 | 📋 | **`test_youtube_sponsorblock_best_effort_retry` does a bare `import yt_dlp` and hard-fails when it is absent** (`tests/test_sources.py:60`) — wants a `pytest.importorskip` guard | _needs Planner pass_ | _needs Planner pass_ | — | One-line test fix. **Re-checked 2026-07-20 and the row's original framing was wrong:** `yt-dlp` is a **core** dependency in `pyproject.toml`, not an optional one, so a correctly-installed environment always has it and the suite is green (137 passed). The failure mode is a partial or editable dev install. Still worth the guard — a test should skip on a missing dep rather than report a red that costs every future Builder a moment of "is this me?" — but it is **latent, not active**, which lowers its priority. Planner should decide whether it is worth a row at all. |
| 4 | 📋 | **The crop editor modal has no focus trap** — Tab escapes the modal into the page behind it | _needs Planner pass_ | _needs Planner pass_ | — | MEDIUM. Pre-existing from the v0.1.7 crop editor; **not** a PR #10 regression. Observed Tab order below. |
| 5 | ✅ | ~~**`#yotoPill` white label fails WCAG AA at rest**~~ — **ABSORBED into item 9 and DELIVERED by it** ([PR #16](https://github.com/mmackelprang/yoto-maker/pull/16), Tasks 3–5) | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12.5–12.6 + `tokens.md` §2b | [item 9's plan](superpowers/plans/2026-07-20-settings-discoverability.md), Tasks 3–5 | — | **Retired 2026-07-20 — do not schedule.** The fill inversion shipped in PR #16 and the result was **measured live from rendered pixels, not asserted**: the white label goes **2.56:1 → 5.03:1** at rest and 5.87:1 on hover, clearing the 4.5:1 bar. The `aria-label` deletion (WCAG 2.5.3) shipped with it. Nothing is left in this row. Historical record follows. The Designer pass it was waiting for is done, and concluded the contrast defect and the connected-state discoverability defect are **one defect measured two ways**: the fix for both is a single fill inversion (`rgba(255,255,255,0.18)` → `rgba(36,29,56,0.28)`, 2.56:1 → 4.97:1). Shipping contrast separately would leave the discoverability fix's primary entry point illegible, and shipping discoverability separately would contradict this row. **Retire this row when item 9 merges** — there is nothing left in it that item 9's plan does not carry. |
| 6 | 📋 | **`favicon.ico` 404 on the callback page** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic. Logged so it isn't rediscovered; safe to leave sitting. |
| 10 | 📋 | **The header pill's label wraps to two lines at 320px** — the header grows to 110px and the pill to 48px | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic, **pre-existing and proven so** — measured identically (pill 48px, header 110px, `scrollWidth` 305) on the pre-PR `.exe` control at the same width, and removing the new chevron does not change it by a pixel. **No overflow, no horizontal scroll, no overlap with the brand** — the header just gets taller. Item 9's Test Plan §E.5 expected "no wrap" and prescribed dropping the chevron's leading gap if tight; that escalation is **inapplicable**, since even the shortest label wraps with the chevron removed entirely. The real cause is `.brand` + pill exceeding 320px, which is a header-layout question item 9 was explicitly forbidden from touching. |
| 11 | 📋 | **`⚙️` is unhidden text inside `#advToggle`'s accessible name** — the step-3 link announces as *"gear Connect a different Yoto account"* | _needs Designer pass_ | _needs Designer pass_ | — | LOW, **pre-existing since v0.1.9**, from PR #16's Polisher gate. **Needs Designer, not Builder** — see briefing notes; it is specced-in, not an oversight, and the obvious fix collides with two other rules. |
| 12 | 📋 | **`#advToggle`'s touch target is ~20px against WCAG 2.2 AA's 24×24** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, **pattern-level and pre-existing**. It matches the canonical footer link `#settingsLink` exactly, so this is a question about the app's link pattern, not about one control. Enlarging *this* link alone is the prominence increase `overview.md` §12.7 forbids. Fix the pattern or accept it — do not special-case one link. |
| 13 | ✅ | **Client ID validation + multi-file audio upload** — **MERGED to `main` as [PR #19](https://github.com/mmackelprang/yoto-maker/pull/19) (`6481aca`, v0.1.11); also recorded in the Shipped table. Row kept because items 14–16's arc briefing references it.** Item A blocks a malformed Client ID before it can destroy a working sign-in or fire a doomed authorize request; Item B adds sequential multi-file upload with grouped partial-failure reporting, retry and cancel | [`specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md) | [`plans/2026-07-21-client-id-validation-and-multi-file-upload.md`](superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md) | — | **Ships as v0.1.11. HIGH — Item A closes a live account-lockout footgun a real user hit.** One PR, **three commit stacks in order 0 → A → B → C** (see briefing notes); Item A must revert independently. 20 tasks — Stack 0 also folds in the latent HTTPException-message-visibility fix (Task 1b). **The plan owns the version bump — it must, the version string is the asset cache key.** Extends the `configuration-surface/` handoff (§13, `copy.md` §4b–d/§7, `interactions.md` §3.6); Item B's surface has no handoff by decision. |
| 14 | ⛔ | **Move `POST /api/tracks/file` onto the background job system (ADR PR A)** — the endpoint returns `{job_id}` and runs on a job thread, matching `/api/tracks/youtube`. Removes a redundant ~260 MB double-write and stops long transcodes from blocking uvicorn's event loop (today a long split hangs `/api/status` and every route) | [ADR §3.1](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs Planner pass_ | **13 ships first; ADR approved** | **Independently shippable and valuable — do NOT collapse the arc into one PR.** Ships without cancel or new progress. Lands on item 13's three seams (S1/S2/S3): ~15–20% client touch, near-zero deleted. **The regression the seams guard:** a job endpoint reports failure through `pollJob` with **no `.status`**, and `jobs.py` has **zero test coverage**, so item 13's reason-precedence test (classifier reads `err.data.reason`+`retryable` before `.status`) is what stops job failures misclassifying as transient (success criterion 12). Add `tests/test_jobs.py`. **Never persist jobs** (ADR §5.4) — a job surviving restart would `add_track` into a fresh empty draft. See arc briefing. |
| 15 | ⛔ | **Exact server-side cancel + real long-file progress (ADR PR B)** — the ffmpeg `Popen` rewrite in `normalize.py::_run`, a server-side `cancelled` terminal state **distinct from `error`**, `POST /api/jobs/{id}/cancel`, job eviction, partial-segment cleanup | [ADR §3.2](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs Planner pass_ | **14 (PR A); 13; ADR approved** | This is the PR that **deletes the client's *"may still finish"* hedge sentence**. `cancelled` MUST be distinct from `error` or a cancel is reclassified transient and offered `Try again` (ADR §5.2.6). `_run` is shared by `probe_audio` / `normalize_to_mp3` / `split_audio` — default the new kwargs to `None` for byte-identical behavior when unset. See arc briefing. |
| 16 | ⛔ | **Client-only XHR upload-progress for short files (ADR PR C)** — replace `fetch` with `XMLHttpRequest` in `uploadOneFile` (seam S1) for `upload.onprogress`, fed through `setAddProgress` (seam S3) | [ADR §3.3](architecture/decisions/2026-07-21-file-upload-on-job-system.md) | _needs go/no-go, then plan_ | **14 (PR A); 13; maintainer go/no-go** | **DEFERRABLE cut-line — needs an explicit maintainer go/no-go before it is planned** (ADR open question 1). Open product question: for **under-50-min files the whole wait is the upload leg**, which **only the browser can measure**, so A+B alone leave short files with a differently-fake bar (ADR §1.4, §7.4–7.5). The arc is coherent with A + B alone. See arc briefing. |
| 18 | 🚧 | **Repair existing cards' declared `format` (mp3 → opus) IN PLACE** — a CLI utility (`python -m yoto_maker.repair --card-id … [--apply]`) that reads a card via `GET /card/{id}`, probes each track's served artifact for Ogg Opus, and rewrites **only** each track's `format` via `POST /content` with `cardId` — preserving the physical NFC link, icons, keys, order and every other field. Dry-run by default; backup-before-write; all-or-nothing per card; verify-after; idempotent | [ADR](architecture/decisions/2026-07-21-repair-existing-cards.md) (design basis; committed by this PR) | [plan](superpowers/plans/2026-07-21-repair-existing-cards.md) | 17 (PR #18) + 13 (PR #19) — both on main | **In flight on `feat/repair-existing-cards`.** New `yoto/repair.py` (pure corrector + orchestration + CLI) + 4 small `client.py` methods + a `yoto_maker/repair.py` shim + `tests/test_repair.py` + `tests/fixtures/card_sample.json`. **`format` is the only field ever written.** **Step-0 pinning found the real body is wrapped `{"card":…,"ownership":…}` and the artifact URL is `trackUrl` itself** (adapted from the plan's assumptions). **No version bump.** The live 3-card `--apply` run is the coordinator's post-merge step — this PR does not write. 6 tasks. |

### Item 18 — briefing notes

- **It mutates LIVE production cards. Every safety property is load-bearing.** The
  apply-mode order is fixed: GET → plan (probe) → all-or-nothing gate → **BACKUP**
  → POST → re-GET → **verify**. A blocked card never reaches the POST; the backup
  is durable on disk (flush + `fsync`) before the POST; the verify fails loudly on
  any change beyond the intended `format` flip. **This PR does not run `--apply`;
  the live 3-card run is the coordinator's separate post-merge step.**
- **Step-0 pinning (read-only `GET /card/gzP2B`) corrected the plan's assumptions
  — this is what the plan told Builder to pin, and it mattered.** The real body is
  **wrapped**: `{"card": {…}, "ownership": {…}}`; `client.get_card` unwraps to the
  inner `card` object (which carries `content.chapters`, `cardId`, `title`,
  `metadata`) — that inner object is what we back up, mutate and POST. The
  pre-signed artifact URL is **`trackUrl` itself** (a full
  `https://secure-media.yotoplay.com/…?Expires=…&Signature=…#sha256=…` URL, stable
  within the ~60-min signing window), **not** the `yoto:#sha` the plan assumed — so
  `_ARTIFACT_URL_KEYS` leads with `trackUrl` and the verify **normalizes** signed
  URLs to their sha-bearing path (ignores signature rotation, still catches a real
  resource remap). `gzP2B`'s artifact was probed read-only and confirmed **Ogg
  Opus** (`OggS`/`OpusHead`; served `Content-Type: audio/ogg`, no `codecs` param, so
  the magic-byte sniff is the path that actually confirms it). `/content/mine`
  returns `{"cards":[…]}`; all three cardIds present (`1WCvI`'s real title is
  **"Wild Robot"**, not "The Wild Robot" — a second reason to use `--card-id`).
- **`format` is the ONLY field ever written.** `fileSize`/`duration` self-correct
  server-side and `channels` is already right, so the whole correction is one string
  per track. **Never rebuild via `build_content_payload`** — it only models new-card
  fields and would drop icons/keys/order. Deep-copy the (unwrapped) GET body and
  overwrite only `format`.
- **Confirm before correcting — never guess.** A track is set to `"opus"` only after
  its served artifact is PROVEN Opus. Unprobeable or non-Opus → that track blocks the
  **whole** card (all-or-nothing); the card is left byte-for-byte untouched.
- **Dry-run is the DEFAULT; `--apply` is opt-in** (and `--dry-run` wins if both are
  passed). Backups are written only in apply mode, only before the POST.
- **Use `--card-id` for the live run, not `--title`.** Discovery **refuses to
  auto-pick** an ambiguous title by design. All three cardIds are known: `1WCvI`,
  `gzP2B`, `7FcVe`.
- **The architecture docs are committed by this PR** (plan Task 6): the repair ADR
  (design basis + an addendum recording the 1-PR simplification), the job-system ADR,
  and `docs/architecture/README.md`. **No version bump; no release cut.**

### Item 13 — briefing notes

- **Commit-stack order is a hard constraint, not a suggestion.** One PR, but
  **Stack 0 (shared groundwork, 2 commits: the `.msg-box` helper + the `api()`
  HTTPException `detail` fallback, Tasks 1 and 1b) → Stack A (Item A, tasks
  2–10) → Stack B (Item B, tasks 11–18) → Stack C (version bump + notes, task
  19)**. Item A's commits must be contiguous and revertable without breaking
  Item B — which is why the shared paragraph helper is its own Stack 0 at the
  base rather than living inside Item A. Do not interleave; finish and commit a
  stack before the next. Plan §Commit stacks explains why the maintainer's
  literal "two stacks" reading needed a third.
- **The hard gate is a DENY-LIST, never the 32-character rule.** This is the
  single most important thing not to "simplify". The 32-char alphanumeric shape
  is *advice* that produces the `unusual` verdict; as a hard gate it would lock
  every user out the day Yoto issues a differently-shaped ID, with recovery
  requiring a code change and a release. It is also why `conftest.py`'s
  `test_client_id` (14 chars, an underscore) still passes under uniform blocking.
  Task 2's tests guard both the shipped default scoring `ok` and `test_client_id`
  not being blocked — **a red suite anywhere in Stack A most likely means the
  deny-list was built as an allow-list.**
- **The refusal must run BEFORE the write and BEFORE `logout()`.** The whole
  point is that a user with a working session never loses it to a typo, and the
  reassurance copy (*"…and you're still signed in to Yoto."*) is true *only*
  because of that ordering. `test_the_refusal_runs_BEFORE_the_write_and_BEFORE_logout`
  asserts neither side effect fired — **do not relax it**; if the ordering
  changes on purpose, the copy must change with it.
- **Blocking is uniform across all three tiers; only the recovery copy varies.**
  `env` and `builtin` get a recovery *sentence*, not a button (the button would
  promise something the app can't do). Two stale sentences in the handoff
  (`interactions.md` §3.6.2's diagram and §3.6.7's role note) still describe an
  earlier draft that exempted `env`; **the plan flags them in §Deviations and
  they need a post-merge amendment.** `env` blocks.
- **Three findings the plan carries because they get lost between spec and
  build**, each with its own task or test: `api()` must re-throw `AbortError`
  distinctly (Task 11 — without it a user's own cancel is reported as a network
  error *and* offered a retry); the reorder sorts **groups not tracks** and all
  counts are **files not tracks** (one file can split into many, Task 16); and a
  cancelled batch must **never** fire the reorder (Task 16/17).
- **Verified during planning, so nobody re-litigates it:** a cancelled in-flight
  file almost always still lands (the request body is buffered before the handler
  runs, and there are no await points after it). The copy says so honestly and
  must keep saying *"may"*. The synchronous transcode also blocks the server's
  event loop, which is why cancel is purely client-side. Plan §Verified during
  planning has the repro output.
- **The plan builds three job-system-ADR seams into Item B (S1/S2/S3).** They are
  good factoring on their own terms and cost ~30 min. **The job-system arc itself
  is out of scope for this PR — do not plan it, do not absorb it.** S2 in
  particular is guarded by a test because without it a future job failure would
  misclassify and break success criterion 12.
- **The plan owns the v0.1.11 bump (Task 19).** The version string is the asset
  cache key (`index.html`'s `?v=__ASSET_V__`), and this PR is almost all
  `app.js` — without the bump, existing browsers keep serving the old script
  against the new markup, which is queue item 8's bug with a new payload.
- **Two things surfaced for the queue, plus one now folded in** (plan §For the
  queue): the `HTTPException`-messages-never-reach-the-user copy-loss class
  (`api()` read `data.error`, FastAPI sends `{detail}`) is **no longer deferred —
  it is fixed in Stack 0, Task 1b**, with a copy audit of all eleven raises and
  the one developer-ish string it surfaces (`Unknown icon`) softened; item 2
  (`--port` doesn't move the redirect URI) becomes *visible* for the first time
  because setting 3 now displays that value; and the event-loop-blocking transcode
  is now measured, strengthening the job-system case.

### Items 14–16 — the file-upload-on-job-system arc (briefing)

Source of truth:
[`docs/architecture/decisions/2026-07-21-file-upload-on-job-system.md`](architecture/decisions/2026-07-21-file-upload-on-job-system.md).
**The ADR is `proposed` and needs Mark's approval before Planner picks up any of
the three.** All three also depend on **item 13 shipping first** — PR A rewrites
the `POST /api/tracks/file` contract that PR B builds against.

- **Do NOT collapse these into one PR.** The ADR is explicit (Option 5 over
  Option 2): **PR A is independently shippable and valuable on its own.** It
  removes a redundant ~260 MB double-write and — the bigger win — stops a long
  transcode from blocking uvicorn's event loop; today a multi-minute split hangs
  `/api/status` and *every* other route (ADR §1.1, §5.1, measured in item 13's
  plan §Verified during planning). PR A ships without cancel and without new
  progress.
- **PR A is an edit, not a rewrite, because item 13 built the seams.** It lands on
  S1 (one `uploadOneFile` call site), S2 (classifier reads `err.data.reason` +
  `retryable` before `.status`) and S3 (one `setAddProgress` writer): ~15–20% of
  the client touched, near-zero deleted (ADR §4). **The one load-bearing risk:** a
  job endpoint reports failure through `pollJob` with **no `.status`**, and
  `jobs.py` has **zero test coverage** (ADR §4.3, §6). Item 13's reason-precedence
  branch (S2) is the *only* thing stopping a real, permanent job failure from
  misclassifying as transient and offering a `Try again` that reliably fails
  (success criterion 12). **PR A must add `tests/test_jobs.py`** covering
  `reason` / `retryable` / cancelled propagation.
- **PR A must never let a job outlive the draft — do NOT add persistence**
  (ADR §5.4). `_draft` is a module-level global that dies with the process; a job
  surviving a restart would `add_track` into a *fresh, empty* draft, which is
  strictly worse than losing the job. PR A should also map a `/api/jobs/{id}` 404
  to a *"Yoto Maker restarted"* message rather than the generic transient branch
  (ADR §5.2.3) — that is also the owner of the copy for item 13's flagged
  `"Job not found"` string (item 13 plan Task 1b, copy audit).
- **PR B is one surgery that buys two things** — exact cancel and real long-file
  progress both need the same `Popen` rewrite of `normalize.py::_run` (ADR §3.2).
  It adds a server-side **`cancelled` terminal state that MUST be distinct from
  `error`**: a cancel arriving as `status: "error"` is reclassified transient and
  offered `Try again` for the thing she just stopped (ADR §5.2.6). PR B is the one
  that **deletes the client's *"may still finish"* hedge sentence.** `_run` is
  shared by `probe_audio` / `normalize_to_mp3` / `split_audio`; default the new
  kwargs to `None` so unset behavior is byte-identical.
- **PR C is the deferrable cut-line — get an explicit maintainer go/no-go before
  planning it** (ADR open question 1, §3.3, §7.5). It is client-only
  (`fetch` → `XMLHttpRequest` for `upload.onprogress`). The open product question:
  for a file **under 50 minutes** — the common case — essentially the entire wait
  is the *upload leg*, which **only the browser can measure** (ADR §1.4). So
  **A + B alone leave short files with a differently-fake bar** (near-zero, then a
  jump), which may read *worse* than today's fake 40% (ADR §7.4). The arc is
  coherent with A + B alone; C is the only PR whose value is not self-evident.

### Item 9 — briefing notes

- **It is a vocabulary fix, not a visibility fix.** The user knew the feature
  existed, had approved its design, was actively looking, and asked for *"the
  option to connect to a different account."* Nothing on the connected screen
  contained *account*, *different* or *change* — the pill names a **state**, the
  footer a **category**, the step-3 link a **destination**. Unhiding the link
  without restoring the vocabulary leaves him matching against the wrong string
  again. `overview.md` §12.2.
- **The evidence is partially contaminated and the plan is built only on the
  clean half.** His browser was serving a stale `app.js` (item 8), which killed
  *both* live entry points — the footer link is also an `<a href="#settings">`
  with no handler registered on v0.1.8's script. All click-behavior evidence is
  discarded. **Do not add prominence changes justified by "the pill looks like a
  badge"** — that claim is explicitly not established. The pill's treatment
  changes only as far as a separately-measured contrast failure forces, plus one
  glyph. No border, no size increase, no gear.
- **Two controls, opposite answers on the gear glyph, and it is easy to
  misread.** `#advToggle` (step 3) **keeps** `⚙️` on both copy variants — the
  glyph is the constant so the control stays recognisable when the words change.
  `#yotoPill` (header) gets `›` and **explicitly not** a gear: a gear says
  *settings*, the category vocabulary that already failed, and reads as
  "machinery, don't touch" to the `INSTALL-FOR-MOM.md` user. Do not harmonise
  these. Plan §Hazard 1.
- **Measurement provenance — re-measure, don't assert.** Item 8's plan found that
  PR #10's UAT produced three false readings from cached CSS, so contrast numbers
  from that session are suspect, including the pill's 2.56:1. Designer's sweep is
  independent, but Test Plan §D requires the shipped result be measured live, on
  a hard-reloaded page **and** a naturally-loaded one, with both runs agreeing.
- **Order.** Not a hard dependency, but **prefer shipping item 8 first**: its
  version stamp is what lets an already-poisoned browser receive this fix at all.
  Task 2 is a `renderStatus()` change, exactly the kind a stale `app.js`
  swallows while the new markup renders. Both PRs edit `index.html` in disjoint
  regions (item 8: lines 7 and 309; item 9: 16–18 and 118–142), so a conflict is
  unlikely; whichever merges second rebases, and `docs/RELEASE_NOTES.md` is the
  only file needing real attention (plan Task 7 is written for both orders).
- **Do not touch the `.setting` primitive.** Designer confirms it was not read,
  extended or clarified for this work, and nothing here changes the settings view
  at all. `overview.md` §3's placement decision is likewise untouched.
- **Two things the design brief did not list and the plan adds**, both flagged in
  its §Deviations: a `margin-top` on the relocated `#advRow` (the handoff snippet
  omits spacing, which would butt the link against `.btn.big`), and a rewrite of
  the now-false `outline-offset` hazard comment at `styles.css:64–73`, which
  duplicates the 2.57:1 claim `tokens.md` §2a retired. **Keep the offset itself.**

### Item 11 — briefing notes

- **The contradiction, stated plainly.** The same design amendment mandates
  `aria-hidden="true"` on the pill's `›` *because* an affordance glyph should not
  be part of an accessible name — and simultaneously requires `⚙️` on **both**
  `#advToggle` copy variants (`copy.md` §1a), where it is bare text and therefore
  *is* part of the name. Both rules are defensible; together they are inconsistent.
- **Why Builder must not just fix it.** The gear on `#advToggle` is load-bearing
  by design: it is the constant that keeps the control recognisable when the words
  change between states (`overview.md` §12.6, and it is the deliberate opposite of
  the pill's answer). Silently wrapping or dropping it is a design change.
- **It is also structurally awkward as specced.** `renderStatus()` sets
  `$("#advToggle").textContent` wholesale on every status render, which would
  destroy a nested `<span aria-hidden>` on the first transition. Any fix has to
  change *how* the copy is applied, not just what it says — likely `replaceChildren()`
  with a rebuilt span, or moving the glyph into CSS `::before`. Note the CSS route
  has its own trade-off: generated content is still exposed to some screen readers.
- **Not urgent.** Pre-existing since v0.1.9, LOW severity, and the announcement is
  clumsy rather than wrong — a user hears an extra word, not a false one.

### Item 8 — briefing notes

- **Read the plan before starting.** The approach is a deliberate combination of
  two mechanisms plus a document-level header, and each part covers a specific
  blind spot in the others. Dropping any one of the three leaves a fix that looks
  correct and does nothing in the field.
- **We misfiled this twice.** Builder and Tester both hit this symptom during PR
  #10 and PR #11 UAT and it was written up as a *testing hazard* — "clear your
  cache before UAT" — in `docs/DEVELOPERS.md` and both v0.1.9-era plan files.
  One of the three "false failures" recorded there (**the pill triggering sign-in
  instead of routing to Settings**) is verbatim the bug the user later reported
  from the field. Tasks 5 and 7 correct that framing.
- **The single most important UAT instruction: do not clear the browser cache.**
  The whole claim is that an already-broken browser is repaired with no user
  action. Clearing the cache first destroys the test and would have hidden this
  bug for a sixth release.
- **Highest-risk implementation detail:** `read_text()` must be passed
  `encoding="utf-8"` explicitly. Without it the frozen `.exe` reads `index.html`
  as cp1252, raises `UnicodeDecodeError` at byte 1201, and 500s the entire UI —
  while passing every test on a UTF-8 machine. Test plan §C.3 is the gate.
- **Version-bump ownership.** This PR bumps `pyproject.toml` and
  `yoto_maker/__init__.py` to `0.1.10`. Coordinate with the Designer-specced
  Settings-discoverability item landing in the same release; whichever merges
  second rebases.
- **Adjacent but out of scope:** item 2 (`--port` doesn't update `cfg.port`) sits
  at `main.py:59`, one file over from this work. Leave it alone — it changes OAuth
  redirect behavior and has its own row.

### Item 2 — briefing notes

- **The defect.** `yoto_maker/main.py:59` computes `port = args.port or cfg.port`
  and passes it to `start_server()`, but never assigns it back to `cfg.port`.
  `_redirect_uri()` reads `cfg.port`, so it keeps returning 8777 no matter what
  the flag says. The server listens on the requested port; only the OAuth
  redirect is wrong.
- **How it surfaced.** Found while running PR #10's UAT on a non-default port,
  and it blocked one Tester sub-check. Everything not involving Yoto sign-in
  works fine under `--port`, which is why it has survived since v0.1.8.
- **Why it isn't in PR #10.** Pre-existing, unrelated to the configuration
  surface, and it changes OAuth redirect behavior — not something to slip into a
  UI PR's review-gate fixes.
- **Worth a Planner pass despite being small:** the redirect URI has to match
  what's registered on Yoto's side, so "just set `cfg.port`" may be necessary but
  not sufficient. The right answer may be to reject `--port` for sign-in flows
  with a clear message rather than silently produce a redirect that Yoto rejects.

### Item 3 — briefing notes

- `tests/test_sources.py::test_youtube_sponsorblock_best_effort_retry` does a
  bare `import yt_dlp` and fails with `ModuleNotFoundError` wherever that
  optional dependency isn't installed — which includes this machine.
- Wants `pytest.importorskip("yt_dlp")` so the suite is green when the dep is
  absent and still exercises the retry path when it's present.
- The suite reports **109 passed, 1 failed** without the dep, and that one
  failure is environmental. It should be a skip.
- **Confirmed environmental during the v0.1.9 release cut.** `yt-dlp` had to be
  installed to build the `.exe` (the spec's `collect_all("yt_dlp")` needs it),
  and with it present the suite runs **110 passed, 0 failed** — the test itself
  is fine, it just states a dependency it should be skipping on. Note the count
  is 109/110 rather than the 100 recorded earlier; PR #10 and #11 added tests.

### Item 4 — briefing notes

- **The defect.** The crop editor modal never traps focus. Observed Tab order,
  starting inside the modal: `cropZoom` → `cropCancel` → `cropApply` → **escapes
  to `body`** → `yotoPill` → `ytUrl` → `skipSponsors`. A keyboard user tabs
  straight out of the modal and into the page behind it, with no way back except
  Shift-Tab counting.
- **Wants:** a focus trap (cycle within the modal), plus the usual modal
  companions — focus moved into the dialog on open, restored to the invoking
  control on close.
- **Pre-existing**, introduced with the crop editor in v0.1.7. Found while
  running PR #10's keyboard/focus gate (§C), which is why it surfaced now.
  Explicitly **not** a PR #10 regression and deliberately out of that PR's scope.
- PR #10 *did* ship a registry-driven Escape handler; check whether the crop
  modal should register with it rather than growing its own key handling.

### Item 5 — briefing notes

- **The defect.** `#yotoPill`'s white label measures **2.56:1** against the light
  end of the pill's gradient. WCAG AA wants 4.5:1 for body-size text. It fails
  **at rest** — the focus and hover treatments PR #10 added are fine (that PR's
  focus ring measured 3.26:1 worst case against a 3:1 non-text requirement).
- **Why it's queued rather than fixed in PR #10.** Pre-existing and independent
  of the configuration surface. But PR #10 promotes the pill from decorative
  status indicator to the **primary entry point for Settings**, which raises the
  stakes on a control that already failed — worth fixing soon rather than never.
- **Needs a Designer pass.** The fix is a call about the gradient's fill or the
  label's treatment (darken the light stop, add a scrim, restyle the label, or
  drop white entirely). That is a visual-language decision with knock-on effects
  for the pill's connected/not-connected states — not a Builder picking a darker
  hex in isolation. Route to Designer before Planner writes the plan.

**Designer pass complete, 2026-07-20 — and it took the row with it.**

- **Outcome: absorbed, not scheduled.** Specified in
  `design-handoffs/configuration-surface/overview.md` §12.5–12.6 and
  `tokens.md` §2b, as part of the connected-state Settings-discoverability fix.
- **Why absorbed rather than left as its own row.** A label at 2.56:1 is not only
  an accessibility finding — it is *literally harder to see*, and a control whose
  label is hard to see does not get scanned. The discoverability spec had to
  respecify this same control anyway; leaving a row reading *needs Designer pass*
  against a control that now has one would put the queue in contradiction with a
  shipped spec.
- **The chosen fix, for the record.** Not the gradient stop (constrained by
  `tokens.md` §2a's focus-ring invariant, and it is the app's visual signature)
  and not the label (abandons `header { color: #fff }`). **Invert the fill**:
  `rgba(255,255,255,0.18)` → `rgba(36,29,56,0.28)`. The pill was failing because
  its fill was *white over an already-light gradient* — it lightened the
  background behind white text. Worst-case label contrast **2.56:1 → 4.97:1**;
  hover **3.28:1 → 5.81:1**; both status dots improve; full 1%-interval sweep and
  the rejected alphas are in `tokens.md` §2b.
- **Two knock-ons Planner should carry into the plan.** (1) The long
  `.pill:hover` derivation comment at `styles.css:87-104` should be **deleted**,
  not preserved — it derives a two-layer grey composite that exists only because
  the rest state was white, and hover becomes the same ink at a higher alpha.
  (2) `tokens.md` §2a's `outline-offset: 0` hazard note is now superseded (the
  2.57:1 figure becomes 4.97:1); it has been amended in place. **Keep the
  offset** regardless — it is still visually correct.
- **One further defect found on the same control and folded in:** the pill's
  `aria-label` overrides its visible text as the accessible name, so the name
  does not contain the label — WCAG 2.1 AA **2.5.3 Label in Name**. Introduced by
  PR #10, not pre-existing. Fix is a deletion; `title` alone is correct.

---

## Shipped

| # | Item | Spec | Plan | PR | Merged | Released |
|---|------|------|------|----|--------|----------|
| 1 | **Configuration surface** — full-page Settings view built on the reusable `.setting` primitive, plus the three backend correctness fixes it depends on | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) | [`superpowers/plans/2026-07-20-configuration-surface.md`](superpowers/plans/2026-07-20-configuration-surface.md) | [#10](https://github.com/mmackelprang/yoto-maker/pull/10) | ✅ 2026-07-20 | 🚢 v0.1.9 |
| 7 | **Client ID reveal control + the v0.1.9 release cut** — show the value in effect (full mask, monospace, `Show the whole thing` disclosure) for `saved`/`env`; then actually tag, build and publish v0.1.9 | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) (amended in `884fa6a`) | [`superpowers/plans/2026-07-20-client-id-reveal-and-v0.1.9-release.md`](superpowers/plans/2026-07-20-client-id-reveal-and-v0.1.9-release.md) | [#11](https://github.com/mmackelprang/yoto-maker/pull/11) (Part A), [#12](https://github.com/mmackelprang/yoto-maker/pull/12) (corrections) | ✅ 2026-07-20 | 🚢 v0.1.9 |
| 8 | **Browsers serve a stale `app.js`/`styles.css` after auto-update** — new HTML runs against old JavaScript, which is what made Settings unreachable on v0.1.9 | brief in plan §The defect | [`superpowers/plans/2026-07-20-stale-asset-cache-after-update.md`](superpowers/plans/2026-07-20-stale-asset-cache-after-update.md) | [#15](https://github.com/mmackelprang/yoto-maker/pull/15) (`77d499c`) | ✅ 2026-07-20 | 🚢 v0.1.10 |
| 9 | **A connected user cannot find the way into Settings** — `#advRow` leaves `#connectRow` for the end of step 3 and its copy names the *account*; pill fill inverted for legibility; pill `aria-label` deleted | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12, amended in `e52908e` | [`superpowers/plans/2026-07-20-settings-discoverability.md`](superpowers/plans/2026-07-20-settings-discoverability.md) | [#16](https://github.com/mmackelprang/yoto-maker/pull/16) (`be93ee1`) | ✅ 2026-07-20 | 🚢 v0.1.10 |
| 13 | **Client ID validation + multi-file audio upload** — Item A blocks a malformed Client ID from destroying a working sign-in before the write/`logout()`; Item B adds sequential multi-file upload with grouped partial-failure reporting, retry and cancel | [`specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md) | [`superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md`](superpowers/plans/2026-07-21-client-id-validation-and-multi-file-upload.md) | [#19](https://github.com/mmackelprang/yoto-maker/pull/19) (`6481aca`) | ✅ 2026-07-21 | ⏳ next cut (v0.1.11) |
| 17 | **Transcoded `format` propagation** — the card advertises Yoto's true transcoded format (Ogg Opus) instead of a hardcoded `"mp3"`; best-effort, degrades to the local probe if `transcodedInfo` is absent. Live-verified shape; `fileSize`/`duration`/`channels` deliberately left as-is (Yoto self-corrects them) | brief in plan §The defect | [`superpowers/plans/2026-07-21-transcoded-metadata-propagation.md`](superpowers/plans/2026-07-21-transcoded-metadata-propagation.md) | [#18](https://github.com/mmackelprang/yoto-maker/pull/18) | ✅ 2026-07-21 | ⏳ next cut |

Item 1 shipped all 12 tasks as one PR, as planned. Its Builder briefing notes
were consumed and removed; the spec and plan above remain the durable record.
Three findings surfaced during its review gates and were filed as items 4, 5
and 6 rather than fixed in scope.

Item 7 shipped Part A (tasks 1–7 + 11) as PR #11 and Part B (tasks 8–10, the
release cut) directly on `main`. PR #12 folded in two corrections found during
UAT before the tag: Test Plan §H.3 expected the reveal toggle to wrap beneath the
value at 400px when it actually stays beside it (a wrong expectation, not a
defect), and the stale-build hazard gained its second cause — a stale *server*,
where the single-instance guard makes a new dev server exit 0 while UAT silently
measures the old build.

**Items 8 and 9 — v0.1.10 Released cells, evidenced per the rule above:**

```
$ gh release view v0.1.10 --json tagName,assets -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
v0.1.10 -> YotoMaker.exe

$ gh release view v0.1.10 --json assets -q '.assets[] | "\(.name)  \(.size) bytes  state=\(.state)"'
YotoMaker.exe  127040616 bytes  state=uploaded

$ git ls-remote --tags origin v0.1.10
715bd1c55b96bb63c2eb25a2f284b5f53c21b499        refs/tags/v0.1.10
```

Tag `v0.1.10` → `715bd1c`, confirmed on the remote. **The update path was
verified end-to-end rather than assumed:** with `__version__` spoofed to
`0.1.9` and **no `YOTO_LATEST_VERSION` override** in play (the override
short-circuits the API call at `updater.py:80`, so setting it would test the
override instead of the release), `updater.check_for_update()` hits the real
releases API and returns `update_available: True`, `latest: "0.1.10"`, with a
`download_url` that answers `200` at the expected 127,040,616 bytes. A v0.1.10
client correctly gets no banner.

**The frozen `.exe` was verified serving both fixes, not just built.** Item 8's
cp1252 hazard (`read_text()` without `encoding="utf-8"` 500s the whole UI from a
frozen build while passing every test on a UTF-8 machine) is the gate, and it
passes: `/` returns 200, `/api/status` returns 200, and the served document
carries `?v=0.1.10` stamps on its assets. Item 9's markup was checked in the
served HTML rather than the source — `#advToggle` is outside `#connectRow`,
`#advRow` follows `#sendDone`, the chevron carries `aria-hidden="true"`, the
pill has no `aria-label`, and the served stylesheet carries the inverted fill.

**One item shipped unverified again, deliberately not marked green:** the
screen-reader announcement of `#yotoPill`'s new accessible name (Test Plan
§E.3). Same reason as v0.1.9's reveal toggle — NVDA is not installed and
Narrator's speech cannot be captured as text. Recorded in PR #16's body, under
**Not verified in v0.1.10** in `docs/RELEASE_NOTES.md`, and in the GitHub
release body.

---

**Items 1 and 7 — v0.1.9 Released cells are evidenced**, per the rule above:

```
$ gh release view v0.1.9 --json tagName,assets -q '.tagName + " -> " + (.assets[0].name // "NO ASSET")'
v0.1.9 -> YotoMaker.exe

$ gh release view v0.1.9 --json assets -q '.assets[] | "\(.name)  \(.size) bytes  state=\(.state)"'
YotoMaker.exe  127039674 bytes  state=uploaded
```

Tag `v0.1.9` → `aa3c085`, confirmed on the remote (`git ls-remote --tags origin
v0.1.9`) — the step that was missed last time. **The update path was verified
end-to-end rather than assumed:** with `__version__` spoofed to `0.1.8` and no
`YOTO_LATEST_VERSION` override in play, `updater.check_for_update()` hits the
real releases API and returns `update_available: True`, `latest: "0.1.9"`, with a
`download_url` that answers `200` at the expected 127,039,674 bytes. A v0.1.9
client correctly gets no banner.

**One item shipped unverified, deliberately not marked green:** the screen-reader
announcements on the reveal toggle (Test Plan §F.1–F.3). NVDA is not installed
and Narrator's speech cannot be captured as text, so nobody has heard the
control. The accessibility tree is consistent with the expected utterances and
double-announcement is ruled out structurally, but that is an argument from
construction, not an observation. Recorded in PR #11's body and under
**Not verified in v0.1.9** in `docs/RELEASE_NOTES.md`. Anyone with a screen
reader can close it in about thirty seconds.
