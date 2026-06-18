# HA Custom Panel Design

Size, type, spacing, and colour for **Home Assistant custom panels** (Lit/TS web components
served by an integration). Make the panel look native to HA and follow Material 3 — not
hand-eyeballed pixel values.

Use this whenever touching a panel's CSS/markup: section headers, disclosure arrows, buttons,
thumbnails, list density, colours. Re-invoke after `/compact`.

**Fetch before deciding sizes/tokens — don't guess from memory:**
- Material 3 type scale: https://m3.material.io/styles/typography/type-scale-tokens
- Material 3 states/touch targets: https://m3.material.io/foundations/interaction/states/overview
- HA frontend theming (CSS custom properties): https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/#styling
- HA theme variables list: https://github.com/home-assistant/frontend/blob/dev/src/resources/theme/material-3-tokens.ts

---

## The core rule: tokens over literals

Never hardcode a colour and never invent a `font-size` per element. Pull from HA's theme
custom properties (so the panel follows the user's theme + dark/light), and size from the
Material 3 type scale. A panel full of `color:#49454f; font-size:13px` is the smell this skill
exists to kill.

### HA theme custom properties to use (with sane fallbacks)

```css
color: var(--primary-text-color, #1c1b1f);
color: var(--secondary-text-color, #49454f);      /* captions, hints, inactive */
background: var(--card-background-color, #fff);
background: var(--primary-background-color);
border-color: var(--divider-color);
accent:  var(--primary-color);                     /* HA accent */
border-radius: var(--ha-card-border-radius, 12px);
```

Define a small `:host` token block mapping panel-local names (`--pu-primary`, `--pu-outline`)
to HA vars once, then reference those — one place to retune.

---

## Material 3 type scale (use these, pick by role)

| Role | size / line / weight | Panel use |
|---|---|---|
| Headline small | 24 / 32 / 400 | Page/screen title |
| **Title large** | **22 / 28 / 400** | **Section headers** (the big collapsible groups) |
| Title medium | 16 / 24 / 500 | Sub-section / card title |
| Body large | 16 / 24 / 400 | Primary text, inputs |
| Body medium | 14 / 20 / 400 | Secondary text |
| Label large | 14 / 20 / 500 | Buttons |
| Label medium | 12 / 16 / 500 | Badges, chips |
| Label small | 11 / 16 / 500 | Dense captions only |

**Section headers are title-large (22), not 13-16px.** A collapsible group header is a primary
landmark — it should clearly outrank body text. If everything is 13-16px the hierarchy is flat
and it reads as a wall.

HA renders denser than stock M3; it's fine to tighten line-height a touch, but keep the *ratio*
(header ≥ 1.4× body) so hierarchy survives.

---

## Disclosure arrows / expand indicators

- Use a **24px icon**, not a 12px text glyph (`▸`). In HA, prefer `<ha-icon icon="mdi:chevron-right">`
  (it inherits `--mdc-icon-size`, default 24px) or an inline 24px SVG. A text caret can't hit
  24px crisply and ignores theme icon sizing.
- Rotate 90° on expand with a `transform .15s` transition; colour `--secondary-text-color`.
- The whole header row is the click target (not just the arrow).

```css
.chev { --mdc-icon-size: 24px; color: var(--secondary-text-color); transition: transform .15s; }
.chev.open { transform: rotate(90deg); }
```

---

## Touch targets & icon buttons

- Minimum interactive target **48×48** (M3). Visual icon can be smaller (24), but padding makes
  the hit area 48. Icon buttons: 40 visual / 48 hit min.
- Thumbnails for pixel art: scale up with `image-rendering: pixelated` — an 8×8 icon at 64×64 is
  a clean 8× and stays crisp. Match related thumbnail heights so a grid aligns.

---

## Lists & sorting

A list the user scans needs a **predictable order** — sort by an intrinsic property (size, type,
name), never backend insertion order. Group by kind first if kinds exist, then by a numeric
dimension, then name. State the sort in a hint if non-obvious.

---

## Review checklist

1. Any literal hex colour or `font-size` that should be a token / scale step?
2. Section headers ≥ title-large (22) and clearly outranking body?
3. Disclosure arrows a 24px icon, not a tiny glyph?
4. Every interactive element ≥ 48px hit area?
5. Lists sorted by an intrinsic key, not insertion order?
6. Dark + light both legible (because colours came from theme vars)?
7. Spacing on a consistent step (4/8/12/16/20/24), not arbitrary?

---

## This repo (Pimoroni Unicorn panel)

- Single Lit file `frontend/src/panel.ts` → built to committed `custom_components/pimoroni_unicorn/panel/editor.js`
  (`cd frontend && npm run build`; CI diffs the committed bundle). The `.js` is display-only.
- Existing classes: `.stitle` (section title), `.chev` (arrow), `.thumb` (100×64 widget), `.iconthumb`
  (loaded icon). Retune these against the scale above, not by nudging single px.
- Keep render logic in the Python backend; panel stays presentation.
