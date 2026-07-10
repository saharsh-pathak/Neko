# Design Reference — "All-in-One Crypto Companion" Landing Page

Source: reference screenshot (dark SaaS landing hero + dashboard preview, shadcn/ui-style).

---

## 1. Concept

A dark, high-contrast marketing hero for a crypto portfolio/trading product, transitioning
directly into a live product preview (dashboard cards) below the fold — "show, don't tell."
The dashboard cards double as social proof and feature explanation.

---

## 2. Color Palette

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#000000` | Page background |
| `--bg-surface` | `#0A0A0A` | Card / panel background |
| `--bg-surface-raised` | `#141414` | Nested elements, chat bubbles, inputs |
| `--border-subtle` | `#242424` | Card borders, dividers, hairlines |
| `--text-primary` | `#FAFAFA` | Headlines, primary content |
| `--text-secondary` | `#A1A1A1` | Body copy, supporting text |
| `--text-muted` | `#6B6B6B` | Captions, placeholder, disabled |
| `--accent-gradient` | `linear-gradient(180deg, #FFFFFF 0%, #6B6B6B 100%)` | Headline text fill (white → grey fade) |
| `--chip-active` | `#E5E5E5` (light chip on dark) | Selected calendar day / active state |
| `--chart-line` | `#D4D4D4` | Line chart strokes |
| `--bar-fill` | `#D4D4D4` | Bar chart fills |

Overall palette is strictly monochrome (black/white/grey) — no color accent. Contrast and
subtle elevation (via slightly lighter surfaces + hairline borders) carry all visual hierarchy.

---

## 3. Typography

| Role | Face | Weight | Notes |
|---|---|---|---|
| Display / Hero H1 | Grotesk-style sans (e.g. **Inter Tight**, **General Sans**, or **Geist**) | 700–800 | Large, tight tracking, gradient-fill (white fading to grey top→bottom) |
| Body / Subhead | Same family, regular | 400 | `--text-secondary`, relaxed line-height (~1.6) |
| UI / Card labels | Same family | 500–600 | Small size, high legibility at 13–14px |
| Numeric / Data (revenue, stats) | Same family, tabular figures | 700 | Large size for key metrics ($15,231.89, +2350, 350) |

Single type family used throughout (no serif) — utility-grade, product-grade sans. Scale is
compressed: hero ~56–64px, card titles ~14px, data figures ~28–32px, captions ~12px.

---

## 4. Layout

```
┌─────────────────────────────────────────────┐
│              (full-bleed black)              │
│         Your All-in-One Crypto Companion      │  ← centered hero, 2-line headline
│           Simplify crypto investing...        │  ← centered subhead, ~60ch max width
│                 [ Get Started ]                │  ← pill CTA button
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌────────┐┌──────┐ │
│  │ Revenue  │ │Subscript.│ │Calendar││ Goal │ │  ← 4-column bento grid
│  │ + chart  │ │ + bars   │ │        ││ +bar │ │
│  ├──────────┤ ├──────────┤ │        │├──────┤ │
│  │ Team     │ │ Chat     │ │        ││Exerc.│ │  ← second row, mixed spans
│  └──────────┘ └──────────┘ └────────┘└──────┘ │
└─────────────────────────────────────────────┘
```

- **Hero**: centered, generous vertical whitespace, max-width ~800px for headline/subhead.
- **CTA**: single pill button, black fill with soft white inner glow / gradient border,
  rounded-full, medium size.
- **Dashboard section**: bento-grid of independent cards (shadcn/ui "Card" primitives),
  4 columns on desktop, cards vary in height, rounded-xl corners (~12–16px radius),
  1px `--border-subtle` borders, no shadows (flat, border-defined depth).
- Grid gap ~16px. Section sits directly below hero with no divider — it *is* the proof.

---

## 5. Components Observed

- **Stat Card** (Total Revenue / Subscriptions): label → big number → delta caption →
  inline sparkline/bar chart footer.
- **Calendar Card**: month header with prev/next chevrons, 7-col day grid, selected day
  as filled light chip, today as bordered/outlined chip.
- **Goal Stepper Card**: circular +/- controls flanking a large numeric value, mini bar
  chart, full-width primary button ("Set Goal") in light-on-dark fill.
- **Team List Card**: avatar + name/email rows with a role `<select>`-style dropdown chip
  (Owner / Member).
- **Chat Card**: avatar header, message bubbles left (received, dark grey) and right
  (sent, lighter grey), input affordance implied at bottom.
- **Buttons**: two styles — pill CTA (hero) and rectangular rounded-md buttons (cards),
  both borderless with subtle gradient/inner-highlight for depth on dark bg.

---

## 6. Signature Element

The **hero headline's vertical gradient fade** (white at top → mid-grey at bottom) combined
with the **immediate, uncropped dashboard preview** bleeding up into the hero space — the
product *is* the hero image, rendered live rather than as a mockup screenshot.

---

## 7. Motion (implied, not visible in static reference)

- Subtle fade/slide-up on hero text and CTA on load.
- Card hover: slight border brighten (`--border-subtle` → `#3A3A3A`) or 1–2px lift.
- Chart lines/bars could animate in on scroll-into-view.
- Respect `prefers-reduced-motion`.

---

## 8. Accessibility Notes

- Verify text contrast: `--text-secondary` (#A1A1A1) on `#000000` ≈ 8.6:1 (passes AA/AAA
  for body text); `--text-muted` on card surfaces should be checked per-surface.
- All interactive chips (calendar days, role dropdowns, +/- steppers) need visible focus
  rings (e.g. 2px offset outline in `--text-primary`) since the design has no color accent
  to lean on.
- Ensure chart data (bars/line) has a non-color-only means of conveying value (labels/tooltips).
