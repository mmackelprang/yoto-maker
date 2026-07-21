# New tokens & utilities — Configuration surface

Three additions to `styles.css`. Everything else in this spec uses the existing
token set (`--accent`, `--accent-dark`, `--accent-soft`, `--ink`, `--muted`,
`--bg`, `--card`, `--ok`, `--warn`, `--err`, `--radius`, `--shadow`).

---

## 1. `--warn-soft: #fdf1e3` — NEW TOKEN

**Why it's needed.** The confirmation step before "Sign in to Yoto again" and
"Go back to the built-in one" is neither an error nor a success nor neutral
info. The existing `.msg-box` variants are:

| Variant | Background | Meaning |
| ------- | ---------- | ------- |
| `.err`  | `#fdeaea`  | Something failed |
| `.ok`   | `#e8f6ee`  | Something succeeded |
| `.info` | `#eef1fb`  | Neutral instruction |

A confirmation is "stop and read this before you continue" — using `.err` would
tell the user something is already broken (it isn't), and `.info` is too quiet
to slow anyone down. `--warn` (`#c9701a`) already exists as the foreground for
exactly this register but has **no matching soft background**, which is why the
palette has an `--accent-soft` but no `--warn-soft`.

`#fdf1e3` is derived the same way `--accent-soft` (`#efeafb`) relates to
`--accent` (`#7c5cd6`): the hue at very low saturation against the `--card`
white.

**Contrast — measured, and it constrains how the token may be used.**

| Foreground on `--warn-soft` | Ratio | Verdict |
| --- | --- | --- |
| `--warn` `#c9701a` | **3.24:1** | ❌ fails AA for body text |
| `--ink` `#241d38` | 14.43:1 | ✅ |
| `--muted` `#6b6480` | 5.02:1 | ✅ |

So **`--warn` must not be used as a text color on `--warn-soft`.** The
confirmation box sets its body copy in `--ink`; `--warn` appears only as a 4px
left border, where it's a non-text indicator and the 3.61:1 it scores against
the card white clears the 3:1 requirement for UI components.

This is the better design regardless of the numbers — a confirmation the user
must actually *read before disconnecting her account* should be set in the same
high-contrast ink as the rest of the app, not in a warm brown at 15px. The
color's job here is to flag the box, not to carry the sentence.

**Deliberately not adding a `.msg-box.warn` variant.** The obvious
`background: var(--warn-soft); color: var(--warn)` pairing is exactly the
combination that fails above, and a variant that can only be used incorrectly is
a trap for whoever adds setting #5. `.setting-confirm` covers the one real need.

```css
:root {
  --warn-soft: #fdf1e3;
}
```

**Used by:** `.setting-confirm` only.

---

## 2. Global `:focus-visible` — NEW UTILITY (fixes an existing gap)

**This is a pre-existing accessibility bug, not something this feature
introduces.** `styles.css` today defines focus styling for exactly one thing:

```css
input:focus, textarea:focus { outline: none; border-color: var(--accent); background: #fff; }
```

Every `<button>` in the app — `.btn`, `.tab`, `.iconbtn`, `.emojibtn`, `.pill` —
has **no visible focus indicator at all**. A keyboard user cannot see where they
are anywhere in Yoto Maker today.

The configuration surface is the first screen in this app that a keyboard-only
or screen-reader user is likely to reach *while something is already wrong*
(their connection broke). Shipping it on top of an invisible focus ring is not
acceptable, and the fix is four lines that improve every existing screen too.

```css
:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}
/* Inputs already show focus via border-color; keep the ring off them
   so the two treatments don't stack into a doubled outline. */
input:focus-visible, textarea:focus-visible { outline: none; }
```

`:focus-visible` (not `:focus`) means mouse users never see the ring — no visual
change to the everyday path.

**Scope note for Planner:** this rule lands globally and affects screens outside
this PR's surface. That is intentional and desirable, but it means the visual
diff will touch step 1–4 too. Do not let a reviewer flag that as scope creep.

---

## 2a. `--focus-ring` — SURFACE-SCOPED OVERRIDE (amendment, 2026-07-20)

**Amends §2 and §4. Raised by Polisher against PR #10; the defect traces to a
gap in this file, so the fix is specified here rather than left to Builder.**

### The defect

A single flat ring color cannot serve every surface, and §2 shipped as if it
could. `#yotoPill` is the one focusable control that does not sit on `--card` or
`--bg` — it sits inside `header`, whose background is
`linear-gradient(120deg, var(--accent), #9a7de6)`. The ring is therefore drawn
**on the gradient, in the gradient's own start color**:

| Ring `--accent` vs | Ratio | |
| --- | --- | --- |
| gradient start `#7c5cd6` | **1.00:1** | invisible — the ring *is* the background |
| gradient end `#9a7de6` | **1.48:1** | ❌ fails 3:1 |

This is the app's primary entry point to the settings surface
([`overview.md` §5.1](overview.md)) and `overview.md` §10.5 requires a visible
focus indicator on the whole surface. It is the one control this PR promotes,
and its ring does not render.

### The fix: one level of token indirection

The ring color becomes a variable that surfaces declare. Custom-property
inheritance does the rest — **any** control placed inside `header`, now or
later, picks up the correct ring with no new rule.

```css
:root {
  /* Focus-ring color. Surfaces that are neither --card nor --bg MUST redeclare
     this if --accent does not clear 3:1 against them. See §4 for the certified
     surface list and the invariant that governs the header gradient. */
  --focus-ring: var(--accent);
}

header { --focus-ring: #ffffff; }

:focus-visible {
  outline: 3px solid var(--focus-ring);   /* was: var(--accent) */
  outline-offset: 2px;                    /* load-bearing — see below */
  border-radius: 4px;
}
input:focus-visible, textarea:focus-visible { outline: none; }
```

That is the entire change: one new custom property, one scoped override, one
edited declaration. No new rule targets `#yotoPill` or `.pill` — **patching the
pill specifically was rejected**, because the next control added to the header
would silently reintroduce the same defect.

### Measured — both ends of the gradient, and every point between

The pill's position relative to the gradient shifts with viewport width, so a
ratio at one stop is not sufficient. Swept at 1% intervals across the full
`#7c5cd6` → `#9a7de6` interpolation:

| Ring `#ffffff` vs | Ratio | Target | |
| --- | --- | --- | --- |
| gradient start `#7c5cd6` | 4.82:1 | 3.0 | ✅ |
| gradient end `#9a7de6` | 3.26:1 | 3.0 | ✅ |
| **worst point across the sweep** | **3.26:1** | 3.0 | ✅ |

The minimum sits at the light end, so `#9a7de6` is the binding constraint and
the pill's actual horizontal position never produces a worse number.

### The 2px offset is load-bearing — do not remove it

The ring passes **because of** `outline-offset: 2px`, not incidentally. The
offset leaves a 2px band of bare gradient between the pill and the ring, so the
ring is adjacent to the gradient on *both* faces. Measured against the pill's own
fill (`rgba(255,255,255,0.18)` composited over the gradient):

| White ring vs pill fill | Ratio | |
| --- | --- | --- |
| over `#7c5cd6` → `#9479dd` | 3.48:1 | ✅ |
| over `#9a7de6` → `#ac94ea` | **2.57:1** | ❌ fails 3:1 |

Setting `outline-offset: 0` on the header would make the ring adjacent to that
fill and **reintroduce the failure**. Flagged because a reviewer measuring
ring-against-pill rather than ring-against-gradient will read 2.57 and think this
fix is wrong; it is correct only so long as the offset survives.

> **Amended 2026-07-20 (§2b) — the 2.57:1 figure above is superseded.** The
> pill's fill changes from `rgba(255,255,255,0.18)` to `rgba(36,29,56,0.28)`,
> and white against the new fill measures **4.97:1**, clearing 3:1 with room to
> spare. The `outline-offset: 0` hazard this paragraph describes **no longer
> exists**.
>
> **Keep the offset anyway** — it is visually correct and removing it buys
> nothing. But the numbers above are left corrected rather than standing,
> because a reviewer who trusts them would conclude the offset is carrying a
> load it stopped carrying. The two paragraphs above remain accurate as the
> record of *why the offset was introduced*; they are no longer accurate as a
> description of what would happen if it were removed.

### Why white, and why not a dual ring

White is not a compromise — it is the header's established foreground
(`header { color: #fff }`, `.pill { color: #fff }`), so the ring speaks the
surface's own vocabulary rather than importing a second one.

Alternatives measured and rejected:

| Candidate | Worst ratio across gradient | Verdict |
| --- | --- | --- |
| `#ffffff` | 3.26:1 | ✅ **chosen** — matches header foreground |
| `--ink` `#241d38` | 3.33:1 | ❌ no meaningful ratio gain; reads as a dark blob, off-register for a pastel header |
| `#000000` | 4.36:1 | ❌ best ratio, but pure black appears nowhere in this palette |
| Dual ring (white inner + dark outer halo) | self-contrasting at 14:1 | ❌ rejected — see below |

A dual ring (`outline: 3px solid #fff` + `box-shadow: 0 0 0 8px var(--ink)`)
would be visible independent of any background, and it is the standard answer
where a single color genuinely cannot win. It is rejected here because it buys
margin the measurements say is not needed, it grows the pill's visual box by
16px inside a header with only 22px of padding, and — decisively — it cannot be
expressed as a single inherited custom property, so it would not generalise to
future header controls the way `--focus-ring` does. The recurrence guard for
this class of defect is the token indirection plus the enumerated surface table
in §4, not additional pixels.

### Invariant this creates

> **Any color used as a `header` gradient stop must maintain ≥3:1 against
> `#ffffff` — i.e. relative luminance ≤ 0.30.**
> `#9a7de6` measures 0.2725, leaving real but finite headroom. Lightening the
> header gradient past that threshold breaks the focus ring and requires
> revisiting `--focus-ring` on this surface.

### Note, no change requested

`border-radius: 4px` inside the `:focus-visible` block is inert in practice —
every focusable class (`.pill`, `.tab`, `.btn`, `.iconbtn`, `.emojibtn`,
`.back-link`) declares its own radius at equal specificity and later in source
order, so all of them win. It affects only bare elements. Left alone; recorded
so a future reader does not mistake it for the thing shaping the ring.

---

---

## 2b. `#yotoPill` — fill inversion and affordance mark (amendment, 2026-07-20)

**Amends §4's contrast table and the `.pill` rules in `styles.css`. Absorbs
`BUILDER_QUEUE.md` item 5, which was filed *needs Designer pass*; this is that
pass.** Required by [`overview.md` §12.5–12.6](overview.md). Two declarations
change and one glyph is added. Nothing else on this surface moves.

> ### ⚠️ Provenance — every ratio in §2b is **derived**, and the shipped build has been **measured**
>
> The figures throughout §2b (4.97, 5.81, 3.48, 3.88, and the full sweep below)
> come from Designer's arithmetic over the gradient, computed *before* the fix
> shipped. They are predictions, and they are good ones — but they are not
> observations.
>
> **[PR #16](https://github.com/mmackelprang/yoto-maker/pull/16) measured the
> live rendered pixels** (element screenshots sampled with PIL, on a
> hard-reloaded page and a naturally-loaded page, both agreeing). Tester then
> re-measured independently. **Where the two disagree, the measured set wins** —
> it is the shipped surface, and this section is not.
>
> | Pair | Derived (§2b) | Measured (PR #16) | Measured (Tester) | Bar |
> | --- | --- | --- | --- | --- |
> | White label at rest | 4.97:1 | **5.03:1** | 5.09:1 | 4.5 |
> | White label on hover | 5.81:1 | **5.87:1** | 5.95:1 | 4.5 |
> | Green dot | 3.88:1 | **3.93:1** | — | 3.0 |
> | Amber dot | 3.48:1 | **3.53:1** | — | 3.0 |
>
> **Every measured value lands better than derived**, so no conclusion in §2b
> changes: alpha `0.28` stands and the `0.32` escape hatch was not needed. The
> derived figures are kept in place rather than overwritten because the
> *reasoning* below (why 0.28 and not 0.22 or 0.40) is built on the sweep, and a
> sweep with four rows silently swapped for measurements would no longer be an
> internally consistent derivation. Read §2b for *why*; read the table above for
> *what the build actually does*.
>
> Full record: `BUILDER_QUEUE.md` item 9.

### Methodology note — sampling a rounded, translucent fill

Recorded because a future pass will otherwise re-derive a false failure.

**Naive whole-element sampling of `.pill` yields a spurious ~3.30:1.** The pill
has `border-radius: 999px`, so its bounding box includes corner pixels where the
antialiased fill fades out into bare header gradient. Those pixels are the
lightest in the box and a min-luminance sweep finds them first — but **no part of
the label is drawn over them**, so the ratio they produce describes a pair that
never renders.

Sample the region actually behind the glyphs: the fill's interior, inset past the
corner radius. That is where 5.03:1 and 5.87:1 above come from, and it is the
pair AA is asking about.

### The defect, and why it is a discoverability defect

The pill's label measures **2.56:1** against the light end of the header
gradient. AA wants 4.5:1 for 14px text. It fails **at rest** — the focus ring
(§2a, 3.26:1 against a 3:1 bar) and the hover treatment are both fine.

It fails for a structural reason worth naming, because it dictates the fix: the
fill is `rgba(255,255,255,0.18)` — **white over an already-light gradient**. It
*lightens* the background behind white text. The pill is fighting its own label.

This is filed as an accessibility item, but a label at 2.56:1 is also *literally
harder to see*, and a control whose label is hard to see is a control that does
not get scanned. `overview.md` §12 fixes a discoverability failure on this same
control; the two defects are the same defect measured two ways, which is why
they ship together.

### Directions considered

| Direction | Verdict |
| --- | --- |
| Darken the header gradient's light stop | ❌ Blast radius. `#9a7de6` is constrained by §2a's focus-ring invariant (luminance ≤ 0.30) and is the app's whole visual signature. Changing it to fix one control is the tail wagging the dog. |
| Restyle the label dark on the existing fill | ❌ Abandons `header { color: #fff }`. The pill stops speaking the header's vocabulary and reads as a foreign object pasted onto the gradient. |
| **Darken the fill** | ✅ **Chosen.** One declaration, local to `.pill`, changes nothing else on the surface. |

### The sweep — `--ink` at alpha over the full gradient

White label, swept at 1% intervals across `#7c5cd6` → `#9a7de6`. The worst point
is at the light end in every row, matching §2a's finding that `#9a7de6` is the
binding constraint for anything drawn on this header.

| Fill | Worst | Best | Composite (dark end → light end) | |
| --- | --- | --- | --- | --- |
| `rgba(255,255,255,0.18)` *(shipped)* | **2.56:1** | 3.36:1 | `#9479dd` → `#ac94ea` | ❌ the defect |
| `rgba(36,29,56,0.22)` | 4.51:1 | 6.28:1 | `#694eb3` → `#8068c0` | ❌ clears 4.5 by 0.01 — no headroom at all |
| `rgba(36,29,56,0.25)` | 4.74:1 | 6.54:1 | `#664cae` → `#7c65ba` | ◻ passes, thin |
| **`rgba(36,29,56,0.28)`** | **4.97:1** | 6.80:1 | `#634aaa` → `#7962b5` | ✅ **chosen** — shipped and measured at **5.03:1**, composite `rgb(120,97,181)` |
| `rgba(36,29,56,0.32)` | 5.31:1 | 7.11:1 | `#6048a3` → `#745eae` | ✅ available if UAT wants darker |
| `rgba(36,29,56,0.40)` | 6.01:1 | 7.85:1 | `#594397` → `#6b57a0` | ✅ but reads as a dark chip on a pastel header |

**Why 0.28 and not lower or higher.** 0.22 is the arithmetic floor and clears the
bar by 0.01, which is not a margin — a future gradient tweak inside §2a's stated
headroom would silently reintroduce the failure. 0.28 buys ~10% margin while
keeping the composite unambiguously in the purple family (`#7962b5`), so the pill
still reads as part of the header rather than as a black chip stuck to it. Past
0.32 the pill starts competing with the `h1` for attention, which §12.7 forbids —
this surface is visited twice ever and must not gain prominence.

```css
.pill { background: rgba(36,29,56,0.28); }   /* was rgba(255,255,255,0.18) */
```

### Hover — re-derived, and much simpler than what it replaces

The shipped hover is `rgba(144,144,144,0.28)`, and `styles.css:87-104` carries a
long comment deriving it: a two-layer composite (18% white + 12% black over the
gradient) pre-flattened into one translucent grey so that the transition would
interpolate rather than snap, with the alpha rounded to make 144 rather than 145
reproduce the composite.

**That entire derivation exists only because the rest state was white.** With an
ink rest state, hover is the same colour at more alpha:

```css
.pill:hover { background-color: rgba(36,29,56,0.38); }   /* 5.81:1 worst case */
```

It interpolates natively under the existing `transition: background-color .12s`,
because it always was a plain `background-color` and now both ends are the same
hue. **Builder should delete the comment, not preserve it** — it documents a
problem that no longer exists, and leaving it would send the next reader hunting
for a two-layer composite that isn't there.

`.pill:active { transform: translateY(1px); }` is unchanged.

### Everything else on the pill improves or holds

"After" is derived; the measured column is what the shipped build does.

| Pair | Shipped | After (derived) | **Measured** | Bar | |
| --- | --- | --- | --- | --- | --- |
| White label vs fill | 2.56:1 | **4.97:1** | **5.03:1** | 4.5 | ✅ fixed |
| White label vs fill, hover | 3.28:1 | 5.81:1 | **5.87:1** | 4.5 | ✅ now passes on hover too |
| Amber dot `#ffd35c` vs fill | — | 3.48:1 | **3.53:1** | 3.0 | ✅ |
| Green dot `#7CFCB0` vs fill | — | 3.88:1 | **3.93:1** | 3.0 | ✅ |
| White focus ring vs fill | 2.57:1 | **4.97:1** | **5.03:1** | 3.0 | ✅ — same white on the same fill as the label, so it takes the label's figure |

### This retires §2a's `outline-offset` hazard note (but not the offset)

§2a warns that setting `outline-offset: 0` on the header would put the white ring
adjacent to the pill's own fill, where it came out at **2.57:1** and failed.
**That number is now 4.97:1 derived / 5.03:1 measured** — the same figure as the
label, because it is the same white on the same fill. The hazard is gone.

**Do not remove the offset.** It is still visually correct and removing it buys
nothing. But §2a's warning has been amended in place rather than left standing: a
file that tells a future reviewer "measuring ring-against-pill gives 2.57 and that
is why the offset is load-bearing" would be stating something false about the
shipped CSS, and the next person to trust it would draw a wrong conclusion.

### The affordance mark: a trailing `›`

```html
<button id="yotoPill" class="pill" title="Yoto connection settings">
  <span class="dot"></span>
  <span id="yotoPillText">Checking…</span>
  <span class="pill-chev" aria-hidden="true">›</span>
</button>
```

```css
.pill-chev { font-weight: 700; line-height: 1; }
```

No new colour (inherits the pill's `#fff`), no new size (inherits 14px), no new
spacing (the pill's existing `gap: 8px`). The rejection of a gear, of `→`, and of
a border is argued in [`overview.md` §12.6](overview.md); the copy consequence —
that an icon is a string, and `⚙️` would say *settings*, the category vocabulary
that already failed — is in [`copy.md` §1a](copy.md).

**`aria-hidden="true"` is required, not optional.** Unlike `.dot` (an empty span
that announces nothing), `›` is text content and would otherwise be read out.

**`aria-label` is removed from the pill** in the same edit. It overrode the
visible text as the accessible name, producing a WCAG 2.1 AA **2.5.3 Label in
Name** failure. `title` alone gives the correct name/description split. See
`copy.md` §1a.

### Narrow widths — the one thing to check in UAT

`interactions.md` §5.1 recorded that this spec "adds no new header controls", so
header crowding was unchanged. The chevron adds roughly 8px of glyph plus the
pill's 8px gap — about 16px, inside an existing control rather than beside it.
At 320px the header holds `🎵 Yoto Maker` and `● Yoto not connected ›`, which is
the longest combination. **Confirm no wrap or overflow at 320px.** If it is
tight, the escalation is dropping the chevron's leading gap, never adding a
second header row.

### Contrast table (§4) — amended rows

The `header` row of §4's focus-ring table is unchanged: the ring is drawn on bare
gradient because of `outline-offset: 2px`, and the fill change does not affect it
(it only improves the offset-0 fallback, above).

Two rows are added to §4's main table for the pill, which the original
certification omitted entirely — **that omission is what let a 2.56:1 label ship
and is the same class of gap §2a found in the focus-ring table.** The rule is now
uniform across both tables: every rendered pair gets a row.

| Pair | Ratio | Target | |
| --- | --- | --- | --- |
| `#ffffff` label on `.pill` fill over `header` gradient | 4.97:1 derived / **5.03:1 measured** | 4.5 | ✅ worst point, light end |
| `.pill` status dots on that fill | 3.48:1 / 3.88:1 derived · **3.53:1 / 3.93:1 measured** | 3.0 | ✅ amber / green |

---

## 3. `.setting*` component block — NEW COMPONENT

The reusable config-section primitive. Full anatomy and markup contract in
[`overview.md`](overview.md#the-setting-primitive); the CSS contract is
reproduced here for the token/CSS review.

```css
/* --- Settings view -------------------------------------------------- */
.settings-head { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.settings-head h2 { font-size: 22px; margin: 0; }
.settings-head h2:focus { outline: none; }   /* programmatic focus target */

.back-link {
  background: none; border: none; cursor: pointer; font-family: inherit;
  font-size: 16px; font-weight: 600; color: var(--accent-dark);
  padding: 8px 12px 8px 6px; border-radius: 10px;
  display: inline-flex; align-items: center; gap: 6px;
}
.back-link:hover { background: var(--accent-soft); }

/* --- The config-section primitive ----------------------------------- */
.setting {
  background: var(--card);
  border-radius: var(--radius);
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.setting h3 { font-size: 18px; margin: 0 0 6px; }
.setting-desc { color: var(--muted); font-size: 15px; margin: 0 0 16px; }

.setting-status {
  display: flex; align-items: flex-start; gap: 9px;
  font-size: 15px; font-weight: 600; margin-bottom: 16px;
}
.setting-status .dot {
  width: 10px; height: 10px; border-radius: 50%; flex: none;
  margin-top: 7px; background: var(--muted);
}
.setting-status.is-ok      .dot { background: var(--ok); }
.setting-status.is-warn    .dot { background: var(--warn); }
.setting-status.is-err     .dot { background: var(--err); }
.setting-status.is-unknown .dot { background: var(--muted); }
.setting-status .sub { display: block; font-weight: 400; color: var(--muted); font-size: 14px; }

.setting-body { margin-bottom: 16px; }
.setting-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

.setting-confirm {
  background: var(--warn-soft);
  border-left: 4px solid var(--warn);   /* the only use of --warn as color here */
  border-radius: 12px;
  padding: 16px; margin-top: 14px;
  color: var(--ink);                     /* NOT --warn — see §1 contrast table */
}
.setting-confirm p { margin: 0 0 14px; font-size: 15px; }
.setting-confirm p:first-child { font-weight: 600; }
.setting-confirm .setting-actions { justify-content: flex-end; }

@media (max-width: 420px) {
  .setting-actions { flex-direction: column; align-items: stretch; }
  .setting-actions .btn { justify-content: center; }
}
```

---

## 3a. `.mono-value` — NEW UTILITY (amendment, 2026-07-20)

Required by [`overview.md` §11](overview.md). A machine-generated value displayed
for a human to **compare against another screen**, character by character.

**Why this is not optional, and why it matters more than the reveal control it
ships alongside.** The built-in Client ID is:

```
a8OGO6EfbWit5tDUUrOz0g49s49NQoU1
```

Four capital `O`, two `0`, one lowercase `o`. In the app's UI face
(`"Segoe UI", system-ui, …`, `styles.css:28`) `O` and `0` are near-identical at
14px, and `l` / `I` / `1` collapse entirely. The one task this value exists to
support is comparing it against dashboard.yoto.dev — and a proportional face
makes that comparison fail *silently and confidently*, which is the worst
available failure mode. A monospace face disambiguates the glyph pairs and gives
the eye fixed columns to hold its place in a 32-character string.

```css
.mono-value {
  font-family: Consolas, "Cascadia Mono", "SF Mono", Menlo, monospace;
  font-size: 14px;
  letter-spacing: 0.02em;
  color: var(--ink);
  word-break: break-all;   /* 32 chars must wrap inside the column, never overflow */
  align-self: center;      /* inert outside a flex row; see note */
}
```

**Font stack.** Windows-first, matching the app's v1 target (`config.py:17-19`):
Consolas ships on every supported Windows, Cascadia Mono on 11. macOS and the
generic keyword follow for dev machines. No web font — the app has no external
requests and must not gain one for this.

**`word-break: break-all`, not chunking.** The obvious alternative is
`a8OG O6Ef bWit …` in groups of four, the license-key convention, and it does
help the eye. It is rejected because **the spaces would be copied.** A user
selecting the value to paste it somewhere would silently get a string with seven
spaces in it, and the resulting failure ("I copied it exactly and it didn't
work") is far more expensive than the scanning help is worth. `word-break`
inserts nothing; a selection yields the exact 32 characters.

For the same reason: **do not add `user-select: none`**, and do not add a copy
button — full-plus-copy-button was considered and rejected, and a copy button
would need its own transient "Copied!" state and clipboard-failure path for a
value the user can select with a mouse.

**`align-self: center`.** The value span sits in a `.row` (`display: flex`,
`styles.css:171`) with no `align-items`, so it defaults to `stretch` and its
text would top-align against the vertically-centred text of the `.btn.small`
beside it. `align-self` has no effect on a non-flex-item, so the rule is safe
if this utility is ever reused outside a row.

**Named `-value`, not `.mono`, deliberately.** A bare `.mono` reads as a pure
font utility, and the next person to reach for it would inherit `align-self`
and `break-all` by surprise. The name states the scope: a machine value
displayed for reading, inside a row.

**Contrast:** `--ink` on `--card` = 14.6:1 ✅ — already row 1 of §4. No new row
needed.

---

## 4. Verified contrast for everything this surface renders

Measured, not assumed. Text targets 4.5:1 (AA), non-text UI targets 3:1.

For flat opaque pairs, computing the ratio from the two hex values *is* the
measurement — there is nothing to composite. The four `.pill` rows are different:
a translucent fill over a gradient has to be composited first, so a derived
figure is a prediction. **Those four carry live measurements** from PR #16, with
§2b's derived values noted alongside. See §2b's provenance box for both sets and
for the sampling hazard that produces a false 3.30:1.

| Pair | Ratio | Target | |
| --- | --- | --- | --- |
| `--ink` on `--card` | 14.6:1 | 4.5 | ✅ titles, status headlines |
| `--muted` on `--card` | 5.59:1 | 4.5 | ✅ `.setting-desc`, `.sub`, `.tiny` |
| `--ink` on `--warn-soft` | 14.43:1 | 4.5 | ✅ confirmation body |
| `--muted` on `--warn-soft` | 5.02:1 | 4.5 | ✅ |
| `--warn` on `--warn-soft` | 3.24:1 | 4.5 | ❌ **banned as text** — border only |
| `--ok` dot on `--card` | 4.25:1 | 3.0 | ✅ |
| `--warn` dot on `--card` | 3.61:1 | 3.0 | ✅ |
| `--err` dot on `--card` | 5.62:1 | 3.0 | ✅ |
| `#ffffff` label on `.pill` fill over `header` gradient | **5.03:1** | 4.5 | ✅ **added 2026-07-20 (§2b)** — was 2.56:1 ❌. Measured live in PR #16; §2b derived 4.97:1 |
| `#ffffff` label on `.pill` fill, hover | **5.87:1** | 4.5 | ✅ **added 2026-07-20 (§2b)** — was 3.28:1 ❌. Measured; §2b derived 5.81:1 |
| `.pill` amber dot `#ffd35c` on that fill | **3.53:1** | 3.0 | ✅ **added 2026-07-20 (§2b)**. Measured; §2b derived 3.48:1 |
| `.pill` green dot `#7CFCB0` on that fill | **3.93:1** | 3.0 | ✅ **added 2026-07-20 (§2b)**. Measured; §2b derived 3.88:1 |

**The last four rows were absent from the original certification, and that
omission is what let a 2.56:1 label ship** (`BUILDER_QUEUE.md` item 5). It is the
same class of gap §2a found in the focus-ring table below: a surface that renders
text was never measured because nobody wrote its row. The rule is now uniform
across both tables — **every rendered pair gets a row, including on gradients,
including inside translucent fills.**

### Focus ring — certified against every surface that renders one

**This table previously listed two surfaces while the implementation had five.
That gap is what produced the `#yotoPill` defect (§2a).** The rule is now: a
focusable control may only be placed on a surface listed here, and adding a
surface means adding a row — including surfaces introduced by future PRs.

The ring color is `var(--focus-ring)`, which resolves to `--accent` everywhere
except `header`.

| Surface | Background | Ring resolves to | Ratio | |
| --- | --- | --- | --- | --- |
| `--card` `#ffffff` | flat | `--accent` | 4.82:1 | ✅ `.btn`, `.tab`, `.iconbtn`, `.emojibtn`, `.back-link`, `.modal` |
| `--bg` `#f6f4fb` | flat | `--accent` | 4.42:1 | ✅ controls sitting directly on `main` |
| `--warn-soft` `#fdf1e3` | flat | `--accent` | 4.33:1 | ✅ `.setting-confirm` action buttons |
| `.update-banner` | gradient `#efeafb` → `#e6ddfa` | `--accent` | 4.09:1 / **3.69:1** | ✅ worst point is the `#e6ddfa` end |
| `header` | gradient `--accent` → `#9a7de6` | **`#ffffff`** | 4.82:1 / **3.26:1** | ✅ **only** via the §2a override; `--accent` here measures 1.00:1–1.48:1 ❌ |

Gradient surfaces are quoted at both stops and were swept at 1% intervals; the
bolded figure is the worst point across the sweep, not an endpoint reading.

Two surfaces in that list are gradients, and both were absent from the original
certification. **Any future control placed in `header` inherits the correct
white ring automatically** through `--focus-ring`; any future control placed on a
*new* non-`--card`, non-`--bg` surface does **not** — it inherits `--accent` and
must be measured before it ships. If the surface fails, the fix is to redeclare
`--focus-ring` on that surface, never to add a rule targeting the control.

**Amendment 2026-07-20 — the `Show the whole thing` toggle, checked against this
table.** The control introduced by [`overview.md` §11](overview.md) is a
`.btn.small` inside `.setting-body`, whose background is `.setting`'s
`var(--card)`. That is **row 1** of the table above: ring resolves to `--accent`,
4.82:1, and `.btn` is already enumerated there. **No new row, no extension of
the table, no `--focus-ring` override.**

Verified it cannot land anywhere else: the toggle lives in slot 4 (Body) and
never inside `.setting-confirm`, so it never renders on `--warn-soft`; and it is
not a header control, so the `header` override is not in play. The one thing
that would invalidate this is moving the control into the confirmation box —
which §4.3.3 as amended explicitly does not do (the toggle stays put and stays
enabled while a confirmation is open, rather than being relocated into it).

The status dot is **never the only carrier of state** — every dot is paired with
a text headline saying the same thing (`copy.md` §3, §4), so the surface is fully
legible to a user who can't distinguish the colors at all.

---

## 5. Reuse notes

**Deliberately reused rather than redefined:** `.msg-box` (+ `.err` / `.ok` /
`.info`), `.btn` (+ `.primary` / `.ghost` / `.small`), `.row.wrap`, `.grow`,
`.tiny`, `.hidden`, `.progress`. The primitive adds structure, not new visual
vocabulary.

**Amendment 2026-07-20.** The value-display row (`overview.md` §11.5) is built
entirely from that list — `.row.wrap`, `.grow`, `.tiny`, `.hidden`, and
`.btn.small` for the toggle — plus `.mono-value` (§3a), the single new rule in
the amendment. `.btn.small` (`styles.css:122`) is used here for the first time
on this surface; it is the correct weight for a control that sits beside a value
rather than beneath a paragraph, and it inherits `.btn`'s certified focus ring,
`:disabled`, and hover treatment with nothing added.

The toggle is deliberately **not** styled as a bare text link. `.back-link` is
the nearest existing link-like control and is sized for a page-level action
(16px, 8px 12px padding); reusing it would put page-navigation weight on an
in-section disclosure. A `.btn.small` reads as what it is — a small control
attached to the row it modifies.

**Deliberately NOT reused:** `.step`. `.setting` is visually near-identical to
`.step` (same card, radius, shadow, padding) — that similarity is the point,
it's the same app. But it is a separate class with a separate name because
`.step` carries the numbered-badge `h2` treatment and the "do this in order"
semantics, and settings must never inherit those. See the placement rationale
in `overview.md`.
