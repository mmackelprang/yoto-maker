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

## 4. Verified contrast for everything this surface renders

Measured, not assumed. Text targets 4.5:1 (AA), non-text UI targets 3:1.

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
| `--accent` focus ring on `--card` | 4.82:1 | 3.0 | ✅ |
| `--accent` focus ring on `--bg` | 4.42:1 | 3.0 | ✅ |

The status dot is **never the only carrier of state** — every dot is paired with
a text headline saying the same thing (`copy.md` §3, §4), so the surface is fully
legible to a user who can't distinguish the colors at all.

---

## 5. Reuse notes

**Deliberately reused rather than redefined:** `.msg-box` (+ `.err` / `.ok` /
`.info`), `.btn` (+ `.primary` / `.ghost` / `.small`), `.row.wrap`, `.grow`,
`.tiny`, `.hidden`, `.progress`. The primitive adds structure, not new visual
vocabulary.

**Deliberately NOT reused:** `.step`. `.setting` is visually near-identical to
`.step` (same card, radius, shadow, padding) — that similarity is the point,
it's the same app. But it is a separate class with a separate name because
`.step` carries the numbered-badge `h2` treatment and the "do this in order"
semantics, and settings must never inherit those. See the placement rationale
in `overview.md`.
