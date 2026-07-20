# Builder queue

**Last updated:** 2026-07-20 by Planner — **item 8 filed and planned: the stale
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
| 5 | 📋 | **`#yotoPill` white label fails WCAG AA at rest** — 2.56:1 against the gradient's light end, needs 4.5:1 | _needs Designer pass_ | _needs Planner pass_ | — | Pre-existing and independent of PR #10, but PR #10 promotes this control to primary entry point. **Needs a Designer pass, not a Builder hex pick.** |
| 6 | 📋 | **`favicon.ico` 404 on the callback page** | _needs Planner pass_ | _needs Planner pass_ | — | LOW, cosmetic. Logged so it isn't rediscovered; safe to leave sitting. |
| 8 | 📋 | **Browsers serve a stale `app.js`/`styles.css` after auto-update** — new HTML runs against old JavaScript, which is what made Settings unreachable on v0.1.9 | brief in plan §The defect | [`superpowers/plans/2026-07-20-stale-asset-cache-after-update.md`](superpowers/plans/2026-07-20-stale-asset-cache-after-update.md) | — | **HIGH — ships in v0.1.10.** Shipping bug, silent and partial, plausibly degrading every release since v0.1.5. 7 tasks. **This PR owns the `0.1.10` version bump** — Designer's Settings-discoverability PR must not also bump. |

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
