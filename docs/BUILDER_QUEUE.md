# Builder queue

**Last updated:** 2026-07-20 by Builder — added items 2 and 3, both found by the
PR #10 review gates and deliberately left out of that PR's scope.

Work items that have an approved design and a complete implementation plan, ready
for Builder to ship one PR per row. Planner appends; Builder claims, ships and
marks done. **Priority order is the user's to set** — Planner does not reshuffle.

Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ shipped

---

## Queue

| # | Status | Item | Spec | Plan | Depends on | Notes |
|---|--------|------|------|------|-----------|-------|
| 1 | 🚀 | **Configuration surface** — full-page Settings view built on the reusable `.setting` primitive, plus the three backend correctness fixes it depends on | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) | [`superpowers/plans/2026-07-20-configuration-surface.md`](superpowers/plans/2026-07-20-configuration-surface.md) | — | 12 tasks. **One PR — do not split.** Backend (Tasks 1-5) before frontend (Tasks 6-10). Branch `feat/configuration-surface`. In review — awaiting Tester + Polisher gates before merge. |
| 2 | 📋 | **`--port` flag doesn't move the OAuth redirect URI** — the flag changes the listening port but not `cfg.port`, so Yoto sign-in always redirects to 8777 | _needs Planner pass_ | _needs Planner pass_ | — | Pre-existing in v0.1.8 and documented in `--help`. Small fix, but it touches the OAuth redirect — wants a plan before someone changes it blind. |
| 3 | 📋 | **`test_youtube_sponsorblock_best_effort_retry` fails without the optional `yt_dlp` dep** — wants a `pytest.importorskip` guard | _needs Planner pass_ | _needs Planner pass_ | — | One-line test fix. The only red in an otherwise green suite, so it costs every future Builder a moment of "is this me?". |

### Item 1 — briefing notes for Builder

- **Ships together on purpose.** The UI and the three correctness fixes are one
  PR because the settings screen is dishonest without them: it would report
  "connected" in exactly the broken state it exists to repair.
- **Sequence matters.** Tasks 1-5 are backend and must land first; the frontend
  is planned against endpoints that only exist after Task 5. Tasks 7 and 8 leave
  the tree briefly broken between commits — they are adjacent for that reason and
  must not be reordered.
- **The plan documents eight places where the design and the code disagree**
  (§ "Where the design and the code still disagree"). The designer caught three;
  reading the code found five more, one of which — `AuthError` collapsing network
  failure and rejection into one class — makes the specified `unknown` state
  unimplementable until Task 3 lands. Read that section before starting.
- **Two `copy.md` strings have no reachable trigger** in this PR and are
  deliberately not wired. Do not invent triggers for them.
- **Global `:focus-visible` intentionally changes steps 1-4.** The user approved
  this explicitly. Not scope creep; do not revert on review.
- **Test Plan is written to be executed**, not skimmed. The `broken` and
  `unknown` account states must be reproduced (sections E and F), not assumed —
  they are the whole reason the check endpoint exists.

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
- Currently the suite reports **100 passed, 1 failed**, and that one failure is
  environmental. It should be a skip.

---

## Shipped

_Nothing yet — this queue was created with item 1._
