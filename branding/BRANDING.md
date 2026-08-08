# Yoto Maker — brand guide

**Proposed display name:** Yoto Maker
**Tagline:** *From link to card in four steps.*

## Why this name

Keep it. The audience is explicitly non-technical (*"INSTALL-FOR-MOM"*), and for that audience
the name must say exactly what the tool does: it makes Yoto cards. Cleverness would cost clarity.
Branding effort goes into warmth instead.

**Alternates considered:** *Cardsmith* (charming, loses the Yoto anchor), *StoryPress* (lovely,
vague), keeping as-is won.

## The mark

A Yoto-style card carrying a music note, with a sparkle at the corner — the moment the card
becomes *yours*. Rounded everything, high warmth, reads at kid-height.

## Palette

| Color | Hex | Role |
|---|---|---|
| Coral | `#FF6B57` | Background / primary brand color |
| Lagoon Teal | `#2EC4B6` | The note, buttons, links |
| Sunshine | `#FFC93C` | Sparkle, highlights |
| Cream | `#FFF6EC` | Card, panels, text on dark |

## Voice

Four-step voice: short sentences, no jargon, every instruction starts with a verb. If a word
wouldn't appear in INSTALL-FOR-MOM.md, it doesn't appear in the UI.

*(Note: "Yoto" is Yoto Ltd's trademark — fine for a free companion tool described as such, but
keep "unofficial companion" wording on any public page, and don't reuse Yoto's own logo.)*

## Files in this directory

| File | Use |
|---|---|
| `logo.svg` | Full lockup (mark + wordmark + tagline) for README headers and docs |
| `favicon.svg` | Square app mark, scales from 16px to full size |
| `favicon.ico` | Legacy multi-size favicon (16/32/48) for browsers that want `.ico` |
| `favicon-32.png` | 32px PNG favicon |
| `apple-touch-icon.png` | 180px iOS home-screen icon |
| `icon-512.png` | Large raster for app manifests, social cards, stores |

### Wiring the favicon into a web page

```html
<link rel="icon" href="/branding/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/branding/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="/branding/apple-touch-icon.png">
```

### README header

```markdown
<p align="center"><img src="branding/logo.svg" alt="Yoto Maker" width="520"></p>
```

## Typography

Wordmark: **Montserrat Bold** (falls back to Segoe UI / system sans). Body text: the platform
default sans. For code-adjacent surfaces, any monospace at hand — the brand doesn't pin one.

The logo's wordmark is live SVG text, so it renders with whatever sans is installed; if you want
it pixel-identical everywhere, convert the text to outlines in any SVG editor and re-save.

## Dark and light backgrounds

The tile carries its own background, so both `logo.svg` and `favicon.svg` work unchanged on
light or dark pages. The wordmark in `logo.svg` is dark ink — on a dark page, either rely on the
tile alone (use `favicon.svg`) or restyle the two `<text>` fills to `#F0F2F5`.

---
*Generated as a proposal — names, colors, and marks are suggestions to accept, tweak, or reject.*
