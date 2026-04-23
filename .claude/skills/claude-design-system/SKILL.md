---
name: claude-design-system
description: Apply Anthropic/Claude's visual design language to the React dashboard. Warm off-white background, serif display typography, Clay accent, minimal chrome, generous whitespace, text-forward layouts. Use whenever building or editing any `dashboard/` UI component, choosing colors, spacing, typography, or layout patterns.
---

# Claude Design System Skill

Design tokens, patterns, and do/don't rules for the React dashboard. The goal: the demo looks like an Anthropic product, not a generic SaaS dashboard or a Streamlit clone.

## Mood

Warm, paper-like, text-forward, calm. Think of a well-edited research publication, not a Silicon Valley startup landing page. Minimal color, maximum clarity.

## Color Tokens (CSS custom properties)

Define once in `dashboard/src/styles/tokens.css`:

```css
:root {
  /* Surfaces — warm, paper-like */
  --bg:               #F5F4EE;   /* primary background, warm off-white */
  --bg-elevated:      #FAF9F5;   /* cards, panels — slightly lighter */
  --bg-sunken:        #EEECE4;   /* input backgrounds, code blocks */
  --border-subtle:    #E5E3DA;   /* 1px dividers */
  --border-strong:    #CAC6B8;   /* focus rings, emphasis */

  /* Text — warm dark neutrals */
  --fg:               #1F1E1C;   /* body text, near-black with warm tint */
  --fg-muted:         #6B6862;   /* secondary / helper text */
  --fg-subtle:        #9A958B;   /* captions, timestamps */

  /* Accent — Clay (Anthropic signature terracotta-orange) */
  --accent:           #CC785C;
  --accent-hover:     #B8654B;
  --accent-soft:      #F2DDD2;   /* tinted backgrounds, highlight wells */

  /* Semantic — muted, never saturated */
  --success:          #5A7A5A;   /* matched earthy green */
  --warn:             #B88A3E;   /* warm ochre */
  --danger:           #B44A3A;   /* muted brick */
  --info:             #5F7A8C;   /* slate blue */

  /* Data viz palette (ordered, colorblind-safe) */
  --viz-1:            #CC785C;
  --viz-2:            #5F7A8C;
  --viz-3:            #7A8B5A;
  --viz-4:            #8A6B9C;
  --viz-5:            #B88A3E;
}
```

## Typography

- **Display / headings:** a warm serif. Prefer `Copernicus`, `Tiempos Headline`, or `Source Serif 4` as web fallbacks. Use sparingly — headings only.
- **Body:** a clean, humanist sans-serif. Prefer `Inter`, `Styrene B` (licensed), or system `ui-sans-serif`.
- **Mono:** warm monospace. `JetBrains Mono`, `IBM Plex Mono`, or `ui-monospace`.

Token definitions:

```css
:root {
  --font-serif:  'Source Serif 4', 'Copernicus', Georgia, serif;
  --font-sans:   Inter, 'Styrene B', ui-sans-serif, system-ui, sans-serif;
  --font-mono:   'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace;

  /* Scale — generous line-height for readability */
  --text-xs:     0.8125rem;  /* 13px */
  --text-sm:     0.875rem;   /* 14px */
  --text-base:   1rem;       /* 16px */
  --text-lg:     1.125rem;   /* 18px */
  --text-xl:     1.375rem;   /* 22px — serif preferred */
  --text-2xl:    1.75rem;    /* 28px — serif */
  --text-3xl:    2.25rem;    /* 36px — serif, hero only */

  --leading-tight:  1.2;
  --leading-normal: 1.55;
  --leading-loose:  1.75;
}
```

Heading/body pairing:

```css
h1, h2, h3 { font-family: var(--font-serif); line-height: var(--leading-tight); }
body       { font-family: var(--font-sans);  line-height: var(--leading-normal); }
pre, code  { font-family: var(--font-mono); }
```

## Spacing

Use a 4px base with emphasis on **larger gaps, not smaller**. Whitespace is the aesthetic.

```css
--space-1:  0.25rem;  /* 4px  — hairlines */
--space-2:  0.5rem;   /* 8px  — tight */
--space-3:  0.75rem;  /* 12px — compact */
--space-4:  1rem;     /* 16px — default */
--space-6:  1.5rem;   /* 24px — section padding */
--space-8:  2rem;     /* 32px — between groups */
--space-12: 3rem;     /* 48px — page gutters */
--space-16: 4rem;     /* 64px — hero padding */
```

## Radius

Moderate. Never sharp corners, never pill shapes (except for chips).

```css
--radius-sm:  4px;   /* inputs */
--radius-md:  6px;   /* buttons, cards */
--radius-lg:  10px;  /* panels */
--radius-xl:  16px;  /* hero containers */
--radius-pill: 9999px; /* badges only */
```

## Borders & Shadows

- **Prefer 1px borders over shadows.** Use `var(--border-subtle)`.
- Shadows only for floating elements (modals, dropdowns), and keep them soft:
  ```css
  --shadow-sm:  0 1px 2px rgba(31, 30, 28, 0.04);
  --shadow-md:  0 4px 12px rgba(31, 30, 28, 0.06);
  ```

## Components

### Primary Button
```
bg: accent | hover: accent-hover | text: bg | radius: md | padding: 10px 18px
font: sans 14px 500 | transition: 120ms ease
```

### Card / Panel
```
bg: bg-elevated | border: 1px border-subtle | radius: lg | padding: space-6
```

### Input
```
bg: bg-sunken | border: 1px border-subtle | radius: sm
focus: border-strong + subtle accent outline
```

### Agent trace item
```
bg: bg-elevated | border-left: 2px accent | padding: space-3 space-4
font: mono 13px | color: fg-muted | role label: serif, fg, italic
```

### Field plot card
```
bg: bg-elevated | border: 1px border-subtle | radius: lg
colorbar: use matplotlib magma for T, viridis for P (matches field-visualization skill)
caption: serif italic, fg-muted, below plot
```

## Do / Don't

**Do**
- Use the serif for every heading and for short display/quote text
- Leave lots of whitespace around panels
- Use `--accent` for 1–2 focal elements per view, not for every clickable thing
- Use subtle 1px borders to separate panels
- Render matplotlib figures on `--bg-elevated`, not pure white — use `facecolor='#FAF9F5'` in matplotlib rcParams

**Don't**
- Do NOT use pure black (`#000`) or pure white (`#FFF`)
- Do NOT use harsh shadows
- Do NOT use saturated or neon colors anywhere
- Do NOT add gradients (flat only)
- Do NOT use emoji as UI elements
- Do NOT use Material, Bootstrap, or shadcn default themes unopened — override tokens first

## Matplotlib Integration

To make plots visually coherent with the dashboard, set global rc params once in `tools/visualize.py`:

```python
import matplotlib as mpl

mpl.rcParams.update({
    "figure.facecolor":  "#FAF9F5",
    "axes.facecolor":    "#FAF9F5",
    "savefig.facecolor": "#FAF9F5",
    "axes.edgecolor":    "#CAC6B8",
    "axes.labelcolor":   "#1F1E1C",
    "text.color":        "#1F1E1C",
    "xtick.color":       "#6B6862",
    "ytick.color":       "#6B6862",
    "font.family":       "serif",
    "font.serif":        ["Source Serif 4", "Georgia", "serif"],
    "axes.titlesize":    13,
    "axes.titleweight":  "normal",
})
```

## Reference

This skill codifies the visual language used on claude.ai, anthropic.com, and the Built with Opus 4.7 hackathon landing page. It is an *interpretation* based on visible public UI — exact hex codes are approximations tuned for coherence, not pixel-matches to Anthropic's brand guide. Feel free to adjust tokens slightly, but **preserve the mood**: warm, minimal, text-forward, Clay-accented.
