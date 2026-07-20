# Builder queue

**Last updated:** 2026-07-20 by Planner

Work items that have an approved design and a complete implementation plan, ready
for Builder to ship one PR per row. Planner appends; Builder claims, ships and
marks done. **Priority order is the user's to set** — Planner does not reshuffle.

Status key: 📋 queued · 🚧 in flight · ⛔ blocked · ✅ shipped

---

## Queue

| # | Status | Item | Spec | Plan | Depends on | Notes |
|---|--------|------|------|------|-----------|-------|
| 1 | 🚀 | **Configuration surface** — full-page Settings view built on the reusable `.setting` primitive, plus the three backend correctness fixes it depends on | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) | [`superpowers/plans/2026-07-20-configuration-surface.md`](superpowers/plans/2026-07-20-configuration-surface.md) | — | 12 tasks. **One PR — do not split.** Backend (Tasks 1-5) before frontend (Tasks 6-10). Branch `feat/configuration-surface`. In review — awaiting Tester + Polisher gates before merge. |

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

---

## Shipped

_Nothing yet — this queue was created with item 1._
