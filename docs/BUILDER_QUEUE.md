# Builder queue

**Last updated:** 2026-07-20 by Builder — **item 9 shipped as
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
| 3 | 📋 | **`test_youtube_sponsorblock_best_effort_retry` fails without the optional `yt_dlp` dep** — wants a `pytest.importorskip` guard | _needs Planner pass_ | _needs Planner pass_ | — | One-line test fix. The only red in an otherwise green suite, so it costs every future Builder a moment of "is this me?". |
| 4 | 📋 | **The crop editor modal has no focus trap** — Tab escapes the modal into the page behind it | _needs Planner pass_ | _needs Planner pass_ | — | MEDIUM. Pre-existing from the v0.1.7 crop editor; **not** a PR #10 regression. Observed Tab order below. |
| 5 | ✅ | ~~**`#yotoPill` white label fails WCAG AA at rest**~~ — **ABSORBED into item 9 and DELIVERED by it** ([PR #16](https://github.com/mmackelprang/yoto-maker/pull/16), Tasks 3–5) | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12.5–12.6 + `tokens.md` §2b | [item 9's plan](superpowers/plans/2026-07-20-settings-discoverability.md), Tasks 3–5 | — | **Retired 2026-07-20 — do not schedule.** The fill inversion shipped in PR #16 and the result was **measured live from rendered pixels, not asserted**: the white label goes **2.56:1 → 5.03:1** at rest and 5.87:1 on hover, clearing the 4.5:1 bar. The `aria-label` deletion (WCAG 2.5.3) shipped with it. Nothing is left in this row. Historical record follows. The Designer pass it was waiting for is done, and concluded the contrast defect and the connected-state discoverability defect are **one defect measured two ways**: the fix for both is a single fill inversion (`rgba(255,255,255,0.18)` → `rgba(36,29,56,0.28)`, 2.56:1 → 4.97:1). Shipping contrast separately would leave the discoverability fix's primary entry point illegible, and shipping discoverability separately would contradict this row. **Retire this row when item 9 merges** — there is nothing left in it that item 9's plan does not carry. |
| 6 | 📋 | **`favicon.ico` 404 on the callback page** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic. Logged so it isn't rediscovered; safe to leave sitting. |
| 8 | ✅ | **Browsers serve a stale `app.js`/`styles.css` after auto-update** — new HTML runs against old JavaScript, which is what made Settings unreachable on v0.1.9 | brief in plan §The defect | [`superpowers/plans/2026-07-20-stale-asset-cache-after-update.md`](superpowers/plans/2026-07-20-stale-asset-cache-after-update.md) | — | **HIGH — merged 2026-07-20 as [PR #15](https://github.com/mmackelprang/yoto-maker/pull/15) (`77d499c`). Ships in v0.1.10 — `✅ merged`, NOT yet `🚢 released`; the tag waits on item 9.** Shipping bug, silent and partial, plausibly degrading every release since v0.1.5. 7 tasks, all shipped. **This PR owns the `0.1.10` version bump** — item 9 must not also bump, and rebases onto it. |
| 11 | 📋 | **`⚙️` is unhidden text inside `#advToggle`'s accessible name** — the step-3 link announces as *"gear Connect a different Yoto account"* | _needs Designer pass_ | _needs Designer pass_ | — | LOW, **pre-existing since v0.1.9**, from PR #16's Polisher gate. **Needs Designer, not Builder** — see briefing notes; it is specced-in, not an oversight, and the obvious fix collides with two other rules. |
| 12 | 📋 | **`#advToggle`'s touch target is ~20px against WCAG 2.2 AA's 24×24** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, **pattern-level and pre-existing**. It matches the canonical footer link `#settingsLink` exactly, so this is a question about the app's link pattern, not about one control. Enlarging *this* link alone is the prominence increase `overview.md` §12.7 forbids. Fix the pattern or accept it — do not special-case one link. |
| 10 | 📋 | **The header pill's label wraps to two lines at 320px** — the header grows to 110px and the pill to 48px | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic, **pre-existing and proven so** — measured identically (pill 48px, header 110px, `scrollWidth` 305) on the pre-PR `.exe` control at the same width, and removing the new chevron does not change it by a pixel. **No overflow, no horizontal scroll, no overlap with the brand** — the header just gets taller. Item 9's Test Plan §E.5 expected "no wrap" and prescribed dropping the chevron's leading gap if tight; that escalation is **inapplicable**, since even the shortest label wraps with the chevron removed entirely. The real cause is `.brand` + pill exceeding 320px, which is a header-layout question item 9 was explicitly forbidden from touching. |
| 9 | 🚧 | **A connected user cannot find the way into Settings** — `#advRow` moves out of `#connectRow` to the end of step 3 and its copy names the *account*; pill fill inverted for legibility; pill `aria-label` deleted | [`design-handoffs/configuration-surface/`](design-handoffs/configuration-surface/) §12 (+ `copy.md` §1a, `interactions.md` §1.4, `tokens.md` §2b, `mockups` §1/§7a), amended in `e52908e` | [`superpowers/plans/2026-07-20-settings-discoverability.md`](superpowers/plans/2026-07-20-settings-discoverability.md) | — (item 8 shipped first, as preferred) | **HIGH — ships in v0.1.10. [PR #16](https://github.com/mmackelprang/yoto-maker/pull/16) open, awaiting Tester + Polisher — not merged.** 7 tasks, all shipped; suite 133 passed; reviewer found no HIGH or MEDIUM. **Absorbs item 5, now retired.** Version correctly NOT bumped — `pyproject.toml` and `__init__.py` untouched, both already `0.1.10` from item 8. Contrast re-measured live (5.03:1 at rest); connected **and** disconnected states both verified, the healthy one being the state nobody had exercised. |

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

**Both rows' Released cells are evidenced**, per the rule above:

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
