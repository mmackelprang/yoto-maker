# Plan — Settings discoverability in the connected state

**Spec:** [`docs/design-handoffs/configuration-surface/`](../../design-handoffs/configuration-surface/)
— `overview.md` §12, `copy.md` §1a, `interactions.md` §1.4, `tokens.md` §2b,
`mockups/settings-view.md` §1 and §7a. All amended in place by commit `e52908e`.

**Relationship to the handoff:** **follows.** Two resolutions of gaps in the
handoff's illustrative snippets are marked `PLANNER RESOLUTION` inline and listed
in §Deviations. Neither changes a specified decision.

**Ships in:** v0.1.10, alongside
[`2026-07-20-stale-asset-cache-after-update.md`](2026-07-20-stale-asset-cache-after-update.md)
(queue item 8, PR #14). **That PR owns the `0.1.10` version bump. This plan does
not touch `pyproject.toml` or `yoto_maker/__init__.py`.**

**Absorbs:** `BUILDER_QUEUE.md` item 5 (`#yotoPill` label fails AA). Retire that
row when this PR merges.

**7 tasks.** Two files of source (`index.html`, `styles.css`), one line of
JavaScript, one new test file, one release note.

---

## The defect

A connected user who knew the Settings feature existed, had approved its design,
and was actively looking for it could not find it. He asked for *"the option to
connect to a different account (redo auth)."*

This is a **vocabulary** failure, not a visibility failure. Nothing on the
connected screen contained the words *account*, *different* or *change*:

| Entry point | Says | Names |
| --- | --- | --- |
| `#yotoPill` | `Yoto connected` | a **state** |
| `#settingsLink` | `Settings` | a **category** |
| `#advToggle` | `⚙️ Yoto connection settings` | a **destination** — and hidden anyway |

Two compounding PR #10 errors produced it. `#advToggle` lives inside
`#connectRow`, which is `.hidden` whenever connected — so the one contextual link
vanished in exactly the state where "a different account" is coherent. And PR #10
relabelled it from v0.1.8's `⚙️ Use a different Yoto account (advanced)` to
`⚙️ Yoto connection settings`. **v0.1.8 had the words and hid them; v0.1.9 kept
the hiding and removed the words.** He went looking for the string PR #10
deleted.

### Evidence discipline — read this before changing anything not in the tasks

The field report is **contaminated**. His browser was serving a stale `app.js`
(the bug queue item 8 fixes), which killed *both* live entry points — the footer
`#settingsLink` is also an `<a href="#settings">`, and with no `hashchange`
handler registered the hash changes and no view swaps. So "the pill didn't work"
is fully explained by the cache bug and is **discarded**. What survives is his
*vocabulary* (a stale build changes what the app does, not what the user was
looking for), a markup fact Polisher stated during PR #10, and an
already-measured contrast number.

**The claim "nobody clicks the pill because it looks like a badge" is NOT
established, and nothing below is justified by it.** The pill's treatment changes
only as far as the measured contrast failure forces, plus one glyph. It does not
gain a border, a gear, or size. If a later report shows a *working* pill going
unclicked, that is new evidence and a new conversation. `overview.md` §12.1.

---

## Two hazards specific to this PR

### 1. The `⚙️` stays on the step-3 link. "No gear" applies to the **pill** only.

These are two different controls and they get opposite answers, which is easy to
misread:

- **`#advToggle` (step 3)** keeps `⚙️` on **both** copy variants. The glyph is
  the *constant* and the words are the *variable*, so a user who found the
  control while disconnected can recognise it later when the words have changed.
  `copy.md` §1a.
- **`#yotoPill` (header)** gets a trailing `›` and **explicitly not a gear**. A
  gear says *settings* — the category vocabulary that already failed — and to a
  reader who hasn't learned the convention it reads as *machinery, technical,
  don't touch*, which repels the `INSTALL-FOR-MOM.md` user. `›` claims only that
  there is somewhere to go. `overview.md` §12.6.

Do not "harmonise" these.

### 2. Contrast numbers from PR #10's UAT session are suspect

Queue item 8's plan established that PR #10's UAT produced three false readings
from cached CSS. The 2.56:1 that motivates the fill inversion comes from that
era. Designer's sweep in `tokens.md` §2b is independent, but the **Test Plan
below re-measures the shipped result rather than asserting the spec's numbers**,
and Tester must verify on both a cache-cleared page and a naturally-loaded one.
See §Test Plan §D.

---

## Constraints

- **Do not touch the `.setting` primitive.** `tokens.md` §3 is untouched.
  Designer confirms it was not read, extended or clarified for this work. Every
  change here is on the card view and the header; the settings view does not
  change at all.
- **`overview.md` §3's placement decision is untouched** — no tab strip, no fifth
  step, nothing above step 1.
- **Net cost to the everyday path is one 13px line at the bottom of step 3.**
  Anything that adds more weight than that is out of scope.
- **No version bump.** PR #14 owns it.
- `#advRow` is **never** hidden. No `show()` call, no `.hidden`. That is the
  whole point.

---

## Tasks

### Task 1 — Move `#advRow` out of `#connectRow` to the last child of step 3

`yoto_maker/server/static/index.html`. Two edits to the step-3 section
(currently lines 118–142).

**1a. Remove `#advRow` from `#connectRow`.** Replace:

```html
      <div id="connectRow" class="hidden">
        <div class="msg-box info">You'll need to connect your Yoto account first.</div>
        <button id="connectBtn" class="btn primary big" style="margin-top:12px">🔗 Connect my Yoto account</button>
        <div id="advRow" style="margin-top:10px">
          <a href="#settings" id="advToggle" class="tiny">⚙️ Yoto connection settings</a>
        </div>
      </div>
```

with:

```html
      <div id="connectRow" class="hidden">
        <div class="msg-box info">You'll need to connect your Yoto account first.</div>
        <button id="connectBtn" class="btn primary big" style="margin-top:12px">🔗 Connect my Yoto account</button>
      </div>
```

**1b. Add it back as the last child of the section**, after `#sendDone`. Replace:

```html
      <div id="sendError" class="msg-box err hidden"></div>
      <div id="sendDone" class="msg-box ok hidden"></div>
    </section>
```

with:

```html
      <div id="sendError" class="msg-box err hidden"></div>
      <div id="sendDone" class="msg-box ok hidden"></div>

      <!-- Last child, deliberately. Ahead of #sendBtn this would push the
           primary action down and take a tab stop before it — a cost paid on
           every card-making visit for a control used twice ever. Last child
           also fixes the link's position as #sendProgress / #sendError /
           #sendDone appear and disappear, and lands it directly beneath
           #sendError on a failed send. NEVER hidden and NOT inside
           #connectRow: it was inside it until v0.1.9, which meant the one
           contextual way into Settings vanished in exactly the state where
           "use a different account" is a coherent thing to want.
           .tiny is on THIS wrapper and not on the anchor — see below.
           overview.md §12.4, interactions.md §1.4. -->
      <div id="advRow" class="tiny" style="margin-top:14px">
        <a href="#settings" id="advToggle">⚙️ Yoto connection settings</a>
      </div>
    </section>
```

Three things are load-bearing in that markup:

1. **`.tiny` is on the wrapper, the anchor is bare.** On the anchor,
   `.tiny`'s `color: var(--muted)` (specificity 0-1-0) beat
   `a { color: var(--accent-dark) }` (0-0-1) — so the app's most important
   contextual link was the only link in the app that didn't look like a link:
   13px grey, reading as a caption. On the wrapper `.tiny` sets only the 13px
   size and the anchor takes accent purple from `styles.css:263`, at 7.20:1 on
   `--card`, underlined (no `text-decoration` rule exists on `a`). **This is the
   exact construction the footer's `#settingsLink` already uses** and it adds
   zero CSS.
2. **The `⚙️` stays.** See §Hazard 1.
3. **The literal string here is the not-connected variant.** Task 2 overwrites it
   on every `renderStatus()`, which runs before first paint of a meaningful
   state. Shipping the connected variant as the static default would flash "a
   different account" at a user who has none.

> **PLANNER RESOLUTION — `margin-top:14px`.** `interactions.md` §1.4's snippet is
> `<div id="advRow" class="tiny">` with no spacing. With none, the link butts
> flush against `.btn.big`'s bottom edge (`.btn.big` has padding but no bottom
> margin). 14px is chosen over the old 10px because it matches
> `.msg-box { margin-top: 14px }` — so the gap above the link is identical
> whether the preceding sibling is `#sendBtn`, `#sendError` or `#sendDone`, which
> is what "its position never shifts" requires visually and not just structurally.

**Verify after this task:** `grep -n 'advRow' index.html` returns exactly one
line, and it is after the `sendDone` line.

### Task 2 — State-dependent copy in `renderStatus()`

`yoto_maker/server/static/app.js`. `renderStatus()` is at lines 129–141. Add one
statement beside the two `show()` calls already there. Replace:

```javascript
  show($("#connectRow"), !connected);
  $("#sendBtn").disabled = !connected;
}
```

with:

```javascript
  show($("#connectRow"), !connected);
  // #advRow is NOT in #connectRow any more, so the call above no longer reaches
  // it — that is the fix, not an oversight. It is never hidden in either state.
  // "a different" is false before there is a current one: she hasn't connected
  // any account yet, and in that state the big 🔗 Connect my Yoto account button
  // directly above already owns the connect intent. Same rule copy.md §4 applies
  // to the Client ID label (Paste a Client ID / Paste a different Client ID).
  $("#advToggle").textContent = connected
    ? "⚙️ Connect a different Yoto account"
    : "⚙️ Yoto connection settings";
  $("#sendBtn").disabled = !connected;
}
```

Both strings are verbatim from `copy.md` §1a. Note the space after `⚙️` in each.

**No other JavaScript changes.** The click handler at `app.js:1119` —
`$("#advToggle").addEventListener("click", (e) => { e.preventDefault(); gotoSettings(e.currentTarget); })` —
is unchanged and already correct. Because it passes `e.currentTarget` as the
opener, `← Back to my card` returns focus to this link at the bottom of step 3.
That return path is reachable in the connected state for the first time.

### Task 3 — Pill markup: delete `aria-label`, add the chevron

`yoto_maker/server/static/index.html` lines 16–18. Replace:

```html
    <button id="yotoPill" class="pill" title="Yoto connection settings" aria-label="Yoto connection settings">
      <span class="dot"></span><span id="yotoPillText">Checking…</span>
    </button>
```

with:

```html
    <!-- No aria-label. It overrode the visible text as the accessible name, so
         the name ("Yoto connection settings") did not contain the label ("Yoto
         connected") — WCAG 2.1 AA 2.5.3 Label in Name, and a speech-input user
         saying "click Yoto connected" did not activate it. Introduced by PR #10,
         not pre-existing. With text content present and title kept, a screen
         reader announces "Yoto connected, button, Yoto connection settings" —
         state, role, destination — with one attribute fewer. copy.md §1a. -->
    <button id="yotoPill" class="pill" title="Yoto connection settings">
      <span class="dot"></span><span id="yotoPillText">Checking…</span><span class="pill-chev" aria-hidden="true">›</span>
    </button>
```

`aria-hidden="true"` on the chevron is **required, not optional**. Unlike `.dot`
(an empty span that announces nothing), `›` is text content and would otherwise
be read out. Do not give it an `aria-label` — anything it could say would
duplicate either the pill's text or its `title`.

**Not a gear, and not `→`.** `→` reads as *leave / external*, and this app
already spends `↗` on genuinely external links (`index.html:240`, `:303`). `›` is
the deeper-into-this-app convention and is visually lighter, which matters
because this surface must not gain prominence. The app already uses `←` for back
(`index.html:181`); a trailing `›` completes that vocabulary rather than importing
one. `overview.md` §12.6.

### Task 4 — Pill CSS: invert the fill, re-derive hover, delete the stale comment

`yoto_maker/server/static/styles.css` lines 80–108. Replace the whole block —
the `.pill` rule, the 18-line derivation comment at 87–104, and `.pill:hover`:

```css
.pill {
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.18); color: #fff;
  padding: 8px 14px; border-radius: 999px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: none;
  transition: background-color .12s, transform .06s;
}
```

with:

```css
.pill {
  display: inline-flex; align-items: center; gap: 8px;
  /* --ink at 28% over the header gradient, NOT white. The shipped
     rgba(255,255,255,0.18) was white over an already-light gradient — it
     LIGHTENED the background behind white text, and the label measured 2.56:1
     against a 4.5:1 bar. Inverting takes the worst case (the #9a7de6 light end)
     to 4.97:1. 0.22 is the arithmetic floor and clears the bar by 0.01, which is
     no margin at all; 0.28 buys ~10% while keeping the composite (#7962b5) in
     the purple family, so the pill still reads as part of the header rather than
     as a dark chip stuck to it. Past 0.32 it starts competing with the h1.
     Full 1%-interval sweep and rejected alphas: tokens.md §2b. */
  background: rgba(36,29,56,0.28); color: #fff;
  padding: 8px 14px; border-radius: 999px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: none;
  transition: background-color .12s, transform .06s;
}
/* Hover is the same ink at more alpha (5.81:1 worst case), and interpolates
   natively under the transition above because both ends are now the same hue.
   The long two-layer-grey derivation that used to live here has been deleted
   with the white rest state that forced it. */
.pill:hover { background-color: rgba(36,29,56,0.38); }
```

**Delete the comment at 87–104 outright; do not preserve it.** It derives
`rgba(144,144,144,0.28)` as a pre-flattened composite of 18% white + 12% black,
including the detail that rounding the alpha makes 144 rather than 145 reproduce
it. That entire derivation exists *only* because the rest state was white.
Leaving it would send the next reader hunting for a two-layer composite that
isn't there. `tokens.md` §2b.

`.pill:active`, `.pill .dot` and `.pill.connected .dot` (lines 106–108) are
**unchanged**. The dots improve for free: amber `#ffd35c` to 3.48:1 and green
`#7CFCB0` to 3.88:1 against the new fill, both clearing the 3:1 non-text bar.

Then add the chevron rule immediately after `.pill.connected .dot`:

```css
/* Affordance mark only. No new colour (inherits the pill's #fff), no new size
   (inherits 14px), no new spacing (uses the pill's existing gap: 8px). */
.pill-chev { font-weight: 700; line-height: 1; }
```

### Task 5 — Correct the now-false `outline-offset` hazard comment

`yoto_maker/server/static/styles.css`, the `header` rule, lines 64–73. **This is
not in the design brief's task list; it is a consequence of Task 4 that would
otherwise leave the shipped CSS documenting a hazard that no longer exists.**
`tokens.md` §2a was amended in place for exactly this reason — the 2.57:1 figure
becomes 4.97:1 under the new fill — and the same sentence is duplicated here in
the source. A file telling a future reviewer "ring-against-pill measures 2.57 and
that is why the offset is load-bearing" would be stating something false about
the shipped CSS.

Replace:

```css
  /* --accent measures 1.00:1–1.48:1 against this gradient — a ring in the
     gradient's own start color is literally invisible. White is the header's
     established foreground and clears 3:1 across the whole gradient (worst
     point 3.26:1 at the #9a7de6 end). Scoped to the surface, not to .pill, so
     any future header control inherits the correct ring for free.
     The `outline-offset: 2px` above is LOAD-BEARING: it leaves a band of bare
     gradient between control and ring. Against the pill's own fill
     (rgba(255,255,255,0.18) over the gradient -> #ac94ea) white is only
     2.57:1 and FAILS. Setting the offset to 0 here reintroduces the defect.
     See tokens.md §2a. */
```

with:

```css
  /* --accent measures 1.00:1–1.48:1 against this gradient — a ring in the
     gradient's own start color is literally invisible. White is the header's
     established foreground and clears 3:1 across the whole gradient (worst
     point 3.26:1 at the #9a7de6 end). Scoped to the surface, not to .pill, so
     any future header control inherits the correct ring for free.
     `outline-offset: 2px` puts the ring on bare gradient, which is where the
     3.26:1 above is measured. It used to be load-bearing for a second reason
     too — against the pill's old white fill, a ring at offset 0 was white on
     near-white and failed. The 2026-07-20 fill inversion retired that hazard
     (the same pair now measures the same 4.97:1 as the label), so the offset is
     kept because it is visually correct, not because removing it would break
     contrast. Superseded figures are in tokens.md §2a; the new sweep is §2b. */
```

### Task 6 — Regression tests

New file `tests/test_card_view_markup.py`. The `temp_config` fixture is autouse
from `conftest.py` and points `bundle_root` at the repo root, so `STATIC_DIR`
resolves normally.

These read the static files directly rather than going through the `/` route, so
they are **independent of whether PR #14 has landed** and of how that PR
rewrites the route.

```python
"""The way into Settings must exist, be worded for the user, and be legible.

Regression cover for the v0.1.9 field report: a connected user who knew the
Settings feature existed could not find it. #advToggle lived inside #connectRow,
which is hidden whenever connected, and its label had been changed from words
naming the *account* to words naming the *destination*. See
docs/design-handoffs/configuration-surface/overview.md §12.

These are markup and stylesheet assertions, deliberately. The defect was
structural — a control nested inside a container that gets hidden — and that is
exactly the class of defect a cheap static assertion catches and a browser test
only catches if someone remembers to check the healthy state.
"""
from __future__ import annotations

import pytest

from yoto_maker.server.app import STATIC_DIR


@pytest.fixture(scope="module")
def index_html() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATIC_DIR / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def styles_css() -> str:
    return (STATIC_DIR / "styles.css").read_text(encoding="utf-8")


def test_adv_row_is_not_inside_connect_row(index_html):
    """The v0.1.9 defect itself.

    #connectRow's contents run from its own id to the #sendBtn that follows the
    div, so anything inside it lies in that span. #advToggle must not.
    """
    start = index_html.index('id="connectRow"')
    end = index_html.index('id="sendBtn"')
    assert start < end, "markup order changed; this test needs rewriting"
    assert 'id="advToggle"' not in index_html[start:end]


def test_adv_row_is_the_last_child_of_step_3(index_html):
    """Not before #sendBtn: that pushes the primary action down and takes a tab
    stop ahead of it. Last child also fixes the link's position as the transient
    boxes come and go, and lands it directly beneath #sendError on a failure.
    """
    order = [
        index_html.index(f'id="{el}"')
        for el in ("connectRow", "sendBtn", "sendProgress", "sendError", "sendDone", "advRow")
    ]
    assert order == sorted(order)


def test_adv_row_is_never_hidden(index_html):
    """No .hidden class in the markup and no show() call in the script.

    Asserted on the exact opening tag rather than a slice around it: the
    explanatory comment above the div contains the word "hidden", so a window
    around the id would match the prose and prove nothing.
    """
    assert '<div id="advRow" class="tiny"' in index_html
    assert 'id="advRow" class="tiny hidden"' not in index_html
    assert 'id="advRow" class="hidden' not in index_html


def test_adv_row_is_not_hidden_by_script(app_js):
    assert 'show($("#advRow")' not in app_js


def test_tiny_is_on_the_wrapper_not_the_anchor(index_html):
    """On the anchor, .tiny's color (0-1-0) beat `a { color: --accent-dark }`
    (0-0-1) and the app's most important contextual link rendered grey, reading
    as a caption rather than a link. Same construction as the footer's
    #settingsLink. interactions.md §1.4.
    """
    assert '<div id="advRow" class="tiny"' in index_html
    assert 'id="advToggle" class="tiny"' not in index_html
    assert 'class="tiny" id="advToggle"' not in index_html


def test_both_link_strings_are_rendered(app_js):
    """Verbatim from copy.md §1a. The connected variant is the whole fix: it
    contains the words the user was scanning with — account, different — which
    no string on the connected screen previously did.
    """
    assert '"⚙️ Connect a different Yoto account"' in app_js
    assert '"⚙️ Yoto connection settings"' in app_js


def test_the_gear_stays_on_the_step_3_link(index_html, app_js):
    """The glyph is the constant and the words are the variable, so a user who
    found this control in one state can recognise it in the other. This is the
    opposite of the pill's answer and that is deliberate — copy.md §1a.
    """
    assert "⚙️" in index_html
    assert app_js.count("⚙️") == 2


def test_pill_has_no_aria_label(index_html):
    """WCAG 2.1 AA 2.5.3 Label in Name. It overrode the visible text as the
    accessible name, so a speech-input user saying "click Yoto connected" did
    not activate it. title alone gives the right name/description split.
    """
    pill = index_html[index_html.index('id="yotoPill"') : index_html.index("yotoPillText")]
    assert "aria-label" not in pill
    assert 'title="Yoto connection settings"' in pill


def test_pill_chevron_is_present_and_silent(index_html):
    """Unlike .dot (an empty span), the chevron is text content and would be
    read out. It is an affordance mark, not a label.
    """
    assert '<span class="pill-chev" aria-hidden="true">›</span>' in index_html


def test_pill_is_not_given_a_gear(index_html):
    """Decided, not defaulted. A gear says "settings" — the category vocabulary
    that already failed to match — and reads as "machinery, don't touch" to the
    INSTALL-FOR-MOM user. overview.md §12.6.
    """
    pill = index_html[index_html.index('id="yotoPill"') : index_html.index("</button>", index_html.index('id="yotoPill"'))]
    assert "⚙" not in pill
    assert "→" not in pill


def test_pill_fill_is_ink_not_white(styles_css):
    """White at 18% over an already-light gradient lightened the background
    behind white text: 2.56:1 against a 4.5:1 bar. tokens.md §2b.
    """
    assert "rgba(36,29,56,0.28)" in styles_css
    assert "rgba(255,255,255,0.18)" not in styles_css


def test_stale_hover_derivation_is_gone(styles_css):
    """The two-layer grey composite existed only because the rest state was
    white. Leaving the derivation comment would send the next reader hunting for
    a composite that isn't there.
    """
    assert "rgba(144,144,144" not in styles_css
    assert "145,145,145" not in styles_css
    assert "rgba(36,29,56,0.38)" in styles_css


def test_no_stylesheet_comment_still_claims_the_retired_hazard(styles_css):
    """tokens.md §2a's outline-offset hazard is superseded by the fill inversion
    (2.57:1 -> 4.97:1) and was amended in place. The duplicate of that claim in
    styles.css must not survive to mislead a reviewer. The offset itself stays.
    """
    assert "2.57:1" not in styles_css
    assert "outline-offset: 2px" in styles_css
```

Run `python -m pytest tests/ -q`. Expect the pre-existing
`test_youtube_sponsorblock_best_effort_retry` failure if `yt_dlp` is absent
(queue item 3) — that is environmental and out of scope. Everything else green.

### Task 7 — Release note

`docs/RELEASE_NOTES.md`. **Order-dependent — read both cases before editing.**

PR #14 (queue item 8) also writes a v0.1.10 section.

**If PR #14 has already merged**, a `# Yoto Maker v0.1.10` heading and a
`### Fixed in v0.1.10` section already exist. Add these two bullets to the top of
that existing `### Fixed in v0.1.10` list and change nothing else.

**If this PR merges first**, replace the `# Yoto Maker v0.1.9` heading at line 1
with `# Yoto Maker v0.1.10`, keep the three-line description beneath it, and
insert a new `### Fixed in v0.1.10` section above the existing
`### 🆕 New in v0.1.9`. Demote nothing else — the v0.1.9 sections keep their
headings, as `### 🆕 New in v0.1.8` did before them.

The bullets, either way:

```markdown
- **The way to use a different Yoto account is back where you can see it.** The
  link at the bottom of step 3 now says **⚙️ Connect a different Yoto account**
  once you're signed in, and it no longer disappears when everything is working.
  Previously it only showed up while you were *dis*connected — which is the one
  time you don't need it.
- **The Yoto button in the corner is easier to read.** Its label was too faint
  against the purple header. It's now a filled shape with a small `›` to show it
  takes you somewhere.
```

Both are written for the `INSTALL-FOR-MOM.md` reader: no "WCAG", no "contrast
ratio", no element ids.

---

## Deviations and resolutions

| # | Handoff says | Plan does | Why |
| --- | --- | --- | --- |
| 1 | `interactions.md` §1.4 snippet: `<div id="advRow" class="tiny">`, no spacing | adds `style="margin-top:14px"` | The snippet is illustrative and elides the surrounding transient boxes too. With no margin the link butts flush against `.btn.big`. 14px matches `.msg-box { margin-top: 14px }` so the gap is identical whichever sibling precedes it. |
| 2 | Brief's task list does not mention `styles.css:64–73` | Task 5 rewrites that comment | `tokens.md` §2a was amended in place for the retired 2.57:1 hazard; the same claim is duplicated verbatim in the stylesheet. Leaving it would leave the shipped CSS asserting something false. Consistent with §2b's own instruction to delete the hover derivation for the same reason. |

Nothing else deviates. No specified decision is changed.

---

## Test Plan

**Standing UAT hazards — both have produced false readings on this project:**

1. **Browser cache.** `docs/DEVELOPERS.md` §Hazards. Every measurement below is
   worthless against a stale `styles.css`. See §D for the specific protocol.
2. **A stale server.** The app is single-instance. If an installed
   `YotoMaker.exe` or an earlier `python -m yoto_maker` already owns port 8777,
   a new dev server **prints one line and exits 0** — and UAT then silently
   measures the old build. The tell is
   `Yoto Maker is already running at http://127.0.0.1:8777` in the launch output.
   **Read the launch log before testing anything.**

### A. Connected state — the criterion that failed

1. Load `/` with a working Yoto connection (green dot, `Yoto connected`).
2. **A6 (`overview.md` §12.8's new success criterion): scanning, not exploring.**
   Without clicking anything, read the rendered card view and find a string that
   names the *account*. Expect `⚙️ Connect a different Yoto account` at the
   bottom of step 3.
3. The link renders in accent purple (`--accent-dark`), 13px, underlined — **not
   grey**. This is the `.tiny` specificity fix; a grey link is a fail.
4. Click it. The settings view swaps in and `#settingsTitle` takes focus.
5. Click `← Back to my card`. Focus returns to `#advToggle` at the bottom of
   step 3, not to the top of the page.

### B. Disconnected state

1. Sign out (or start from a machine with no saved token).
2. Step 3 shows `#connectRow` (`You'll need to connect your Yoto account first.`
   + `🔗 Connect my Yoto account`), then a disabled `🚀 Send to Yoto`, then the
   link reading **`⚙️ Yoto connection settings`** — *not* "a different".
3. Confirm the link is still present and still last. It must not have moved back
   inside `#connectRow`.

### C. Position stability and adjacency

1. **Transient boxes.** With a card ready, press `🚀 Send to Yoto`. As
   `#sendProgress` appears and then `#sendDone` replaces it, the link stays the
   last thing in the card. Its distance from the bottom edge of the step must not
   change; only the content above it moves.
2. **Failure adjacency.** Force a send failure (disconnect the network mid-send,
   or revoke the token). `#sendError` appears and the link sits **directly
   beneath it** — this is the follow-the-symptom adjacency the pill never had.
   Screenshot this; it is the single most important frame in this PR.
3. **Tab order.** From step 2's field, Tab forward. Expect
   `#sendBtn` → `#advToggle` when connected, and
   `#connectBtn` → `#sendBtn` (disabled, skipped) → `#advToggle` when not.
   `#advToggle` must be **last** in step 3 and must not precede `#sendBtn`.
4. `#advToggle` shows the standard `--accent` focus ring (row 1 of `tokens.md`
   §4, already certified — no override, no new row).

### D. Pill contrast — measured live, not asserted from the spec

**Do this twice: once on a hard-reloaded page, and once on a page loaded
naturally in a browser that has visited the app before.** PR #10's UAT produced
three false readings from cached CSS, and the 2.56:1 that motivates this change
dates from that session. Both runs must agree; if they disagree, you are
measuring a stale stylesheet and nothing else in this section is valid.

1. Confirm the computed `background-color` of `#yotoPill` is
   `rgba(36, 29, 56, 0.28)`. If it is `rgba(255, 255, 255, 0.18)`, stop — stale
   CSS.
2. Measure the white label against the composited fill **at the light end of the
   gradient** (the pill's right edge, nearest `#9a7de6`) — that is the worst
   point. Expect ≈**4.97:1**, and in any case **≥ 4.5:1**. Record the number you
   actually measured; do not copy the spec's.
3. Hover and re-measure. Expect ≈5.81:1, ≥ 4.5:1.
4. Measure both status dots against the fill: amber ≈3.48:1, green ≈3.88:1, both
   ≥ 3.0:1.
5. If the measured worst case lands between 4.5 and 4.7, `tokens.md` §2b keeps
   `rgba(36,29,56,0.32)` (5.31:1) available. Do not go past 0.32 — the pill
   starts competing with the `h1`, which §12.7 forbids.

### E. Pill — focus, chevron, accessibility

1. Tab to the pill. The focus ring is **white** (`header` sets
   `--focus-ring: #ffffff`), drawn on bare gradient with `outline-offset: 2px`,
   and clearly visible. A purple ring means the `--focus-ring` override was lost.
2. The chevron `›` renders trailing the label, in the pill's own white at 14px,
   with the existing 8px gap. No new colour, size or spacing.
3. **Screen reader.** With NVDA or Narrator, focus the pill. Expect
   *"Yoto connected, button, Yoto connection settings"* — state, role,
   destination. If it announces *"Yoto connection settings, button"* the
   `aria-label` is still present.
4. The chevron is **not** announced.
5. **320px width.** Resize to 320px. The header holds `🎵 Yoto Maker` and
   `● Yoto not connected ›` — the longest combination. **Confirm no wrap and no
   overflow.** If tight, the escalation is dropping the chevron's leading gap,
   never adding a second header row.

### F. No regression to the four-step flow

1. Run one full card end to end: add audio (step 1), set a picture (step 2),
   send (step 3), make a label (step 4). All four steps behave as before.
2. Step 3 is one 13px line taller than v0.1.9 and nothing else about it changed.
3. The settings view is **byte-identical in behaviour** — `.setting` was not
   touched. Open Settings, exercise the account section and the Client ID
   section, and confirm nothing moved.
4. The footer `Settings` link still works and is deliberately unchanged.

### G. Unit suite

`python -m pytest tests/ -q`. New file green. Pre-existing `yt_dlp` failure is
environmental (queue item 3) and out of scope.

---

## Cross-PR coordination

**Both this PR and PR #14 edit `index.html`, but in disjoint regions** — PR #14
touches only line 7 (`<link>`) and line 309 (`<script>`); this PR touches lines
16–18 (the header pill) and 118–142 (step 3). A textual conflict is unlikely and
a semantic one is impossible. Whichever merges second rebases; the only file
needing attention on rebase is `docs/RELEASE_NOTES.md` (Task 7) and, if PR #14
went first, nothing else.

**This PR does not bump the version.** `pyproject.toml:7` and
`yoto_maker/__init__.py` stay at `0.1.9` in this branch and reach `0.1.10` via
PR #14.

**Recommended order: PR #14 first.** Its version stamp is what lets a user with a
poisoned cache actually receive this fix. Shipping the discoverability change to
a browser that will keep serving v0.1.9's `app.js` reproduces the original
incident with a new payload — Task 2's `renderStatus()` line is exactly the kind
of script-side change a stale `app.js` swallows while the new markup renders.

## Docs Impact

- `docs/RELEASE_NOTES.md` — Task 7.
- `docs/BUILDER_QUEUE.md` — retire item 5 (absorbed; the row is already marked
  ⛔ and annotated) and mark this row merged.
- No change to `docs/DESIGN.md`, `docs/DEVELOPERS.md`,
  `docs/INSTALL-FOR-MOM.md` or `docs/SETUP-YOTO-CONNECTION.md`. The user-facing
  path is unchanged in structure; one link changed its words and location.
- The design handoff is already amended (`e52908e`) and needs no further edit.
