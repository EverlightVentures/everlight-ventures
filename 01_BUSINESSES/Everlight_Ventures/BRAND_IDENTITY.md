# Everlight Ventures -- Brand Identity System

**Version:** 1.0
**Date:** 2026-03-06
**Tagline:** Build Different. Build in the Light.

---

## Brand Foundation

### Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Primary Gold | Everlight Gold | #D4AF37 | Logo, accents, CTAs, icon fills |
| Secondary Gold (Light) | Champagne | #E8D48B | Hover states, gradients, light-bg text |
| Secondary Gold (Dark) | Antique Gold | #996515 | Shadows, depth, secondary accents |
| Background (Primary) | Void Black | #0A0A0A | Default canvas, dark mode |
| Background (Secondary) | Charcoal | #1A1A1A | Cards, elevated surfaces |
| Neutral Light | Platinum | #E5E5E5 | Body text on dark backgrounds |
| Neutral Mid | Smoke | #8A8A8A | Captions, metadata, muted text |
| White | Pure White | #FFFFFF | Light background canvas, reversed logo |

### Typography

| Use | Font | Fallback | Weight |
|-----|------|----------|--------|
| Logo Wordmark | Cormorant Garamond | Georgia, serif | 600 (Semi-Bold) |
| Headings | Inter | Helvetica Neue, sans-serif | 700 (Bold) |
| Body | Inter | Helvetica Neue, sans-serif | 400 (Regular) |
| Monospace/Code | JetBrains Mono | Courier New, monospace | 400 |

**Why Cormorant Garamond for the wordmark:** It carries old-money authority like a serif should, but the proportions are modern and sharp. It says "established institution" without saying "law firm from 1987." The high contrast strokes pair perfectly with metallic gold treatments.

---

## 1. Primary Logo (Wordmark + Icon Mark)

### Design Description

The primary logo has two components locked together:

**Icon (Left):**
A geometric monogram of the letters "E" and "V" fused into a single angular mark. The "E" is abstracted -- three horizontal bars stacked vertically, connected by a single vertical stroke on the left. The "V" is formed by the negative space created between the lower two bars of the E and two angled strokes that descend from the right side, converging to a point below center. The result looks like a stylized beacon or lighthouse prism -- the E's horizontal bars read as rays of light emanating from the V's apex.

The entire mark sits within an implied square boundary. Stroke weight is consistent throughout -- no hairlines, no heavy fills. Think architectural drafting, not brush strokes.

**Wordmark (Right):**
"EVERLIGHT" on top in Cormorant Garamond Semi-Bold, letterspaced at +120 (generous but not scattered). Below it, "VENTURES" in the same face at 60% the size of "EVERLIGHT," letterspaced at +200 to match the optical width of the word above. Both lines are left-aligned to the icon mark.

**Spacing:**
The gap between the icon mark and the wordmark equals the width of one "E" horizontal bar from the icon. This is the minimum clear space on all sides of the logo.

### Color Variants

| Variant | Icon | Wordmark | Background |
|---------|------|----------|------------|
| Primary (Dark) | #D4AF37 gold | #E5E5E5 platinum | #0A0A0A void black |
| Primary (Light) | #D4AF37 gold | #1A1A1A charcoal | #FFFFFF white |
| Monochrome Dark | #FFFFFF white | #FFFFFF white | #0A0A0A void black |
| Monochrome Light | #0A0A0A black | #0A0A0A black | #FFFFFF white |
| Gold Foil (Print) | Metallic gold foil | Metallic gold foil | Matte black stock |

### Sizing Rules

- **Minimum width:** 120px (digital), 1 inch (print)
- **Favicon:** Use icon mark only, filled gold on transparent
- **Below 40px:** Drop the wordmark entirely, icon mark only

---

## 2. Icon Mark (Standalone)

### Detailed Construction

The standalone icon is the E/V geometric monogram described above, centered within a square canvas with equal padding on all four sides (padding = 12.5% of canvas width).

**Construction grid (on a 64x64 unit grid):**

1. Vertical stroke on the left edge: x=12, from y=8 to y=56. Stroke width = 4 units.
2. Top horizontal bar: from x=12 to x=40, at y=8. Stroke width = 4 units.
3. Middle horizontal bar: from x=12 to x=36, at y=32. Stroke width = 4 units.
4. Bottom horizontal bar: from x=12 to x=32, at y=56. Stroke width = 4 units.
5. Upper diagonal of V: from (x=40, y=8) descending to (x=52, y=44). Stroke width = 4 units.
6. Lower diagonal of V: from (x=32, y=56) ascending to (x=52, y=44). Stroke width = 4 units.

The V's apex at (52, 44) is the focal point -- the "light source." Three bars of the E decrease in length as they descend, creating the visual of light rays narrowing toward a vanishing point (or radiating outward from the apex, depending on read direction).

**Key properties:**
- No rounded corners -- all joints are sharp miters
- No fills -- this is a line-mark, not a glyph
- Optical center is slightly above geometric center (the middle bar at y=32)

### Platform-Specific Adaptations

| Platform | Size | Treatment |
|----------|------|-----------|
| GitHub | 460x460 | Gold mark on #0A0A0A, PNG with no rounding |
| Slack | 512x512 | Same as GitHub |
| Instagram | 320x320 | Gold mark on #0A0A0A, exported at 2x for retina |
| Facebook | 180x180 | Gold mark on #0A0A0A |
| X (Twitter) | 400x400 | Gold mark on #0A0A0A, circular crop-safe |
| Favicon | 32x32 | Simplified -- thicker strokes (6 unit width), gold on transparent |
| App Icon | 1024x1024 | Full detail, subtle radial gradient on gold (#D4AF37 center to #996515 edges) |
| Business Card | Vector | Gold foil stamp on matte black 19pt cardstock |

### Circular Crop Safety

For platforms that apply circular masks (Instagram, X, Facebook), the icon must sit within the inscribed circle of the square canvas. Current padding of 12.5% per side ensures this. The icon's extremities (top of E, apex of V) all fall within the safe circle.

---

## 3. AI Image Generation Prompts

### Prompt 1 -- Full Logo (Wordmark + Icon)

**For Midjourney:**

```
Luxury venture capital firm logo, geometric monogram combining letters E and V into an angular beacon shape, three horizontal light-ray bars emanating from a V-shaped apex, paired with the text "EVERLIGHT VENTURES" in elegant serif typography with generous letter spacing, gold metallic color #D4AF37 on matte black background #0A0A0A, minimalist, architectural, sharp edges, no curves, no gradients, ultra clean vector style, inspired by Berkshire Hathaway and Apple branding, professional corporate identity, 4K --ar 3:1 --s 750 --q 2 --style raw --no rounded corners, 3D, shadows, texture, organic shapes
```

**For DALL-E 3:**

```
A premium corporate logo for "EVERLIGHT VENTURES" on a pure matte black background. The logo consists of a geometric icon on the left -- an abstract monogram of the letters E and V formed by three horizontal bars (decreasing in length from top to bottom) connected by a vertical line on the left, with two diagonal strokes forming a V shape that converge at a point to the right. The icon is rendered in metallic gold (#D4AF37). To the right of the icon, the text "EVERLIGHT" appears in a refined serif font with wide letter spacing, with "VENTURES" below it in smaller text. All text is in light platinum gray. The style is ultra-minimal, sharp, geometric, and luxurious. No rounded corners. No 3D effects. Flat vector aesthetic.
```

### Prompt 2 -- Icon Mark Only (Square Avatar)

**For Midjourney:**

```
Minimalist geometric logo mark, abstract letters E and V fused into single angular symbol, three horizontal bars of decreasing length connected vertically on the left side forming stylized E, two diagonal lines converging to a point on the right forming V shape, sharp mitered corners, no curves, metallic gold #D4AF37 on solid black #0A0A0A background, centered in square frame with generous padding, vector style, luxury brand identity, suitable for app icon and favicon, ultra clean --ar 1:1 --s 750 --q 2 --style raw --no text, rounded corners, 3D, gradients, organic shapes
```

**For DALL-E 3:**

```
A square logo icon on a solid black (#0A0A0A) background. The mark is a geometric monogram of letters E and V: three horizontal gold bars stacked vertically and connected by a vertical stroke on the left (forming the E), with two diagonal strokes descending from the ends of the top and bottom bars to meet at a point on the right (forming the V). The bars decrease in length from top to bottom. All strokes are the same weight. Gold color is #D4AF37. Sharp angular joints, no curves, no rounded corners. Centered with equal padding. Minimalist vector style. Luxury corporate identity aesthetic.
```

### Prompt 3 -- Social Media Avatar (Lifestyle/Brand Context)

**For Midjourney:**

```
Luxury brand social media profile image, the gold geometric EV monogram logo embossed on a black leather texture surface, subtle spotlight from above creating soft highlight on the gold, dark moody atmosphere, shot from directly above, product photography style, matte black and metallic gold color scheme, premium feel like Rolex or Montblanc branding, cinematic lighting, shallow depth of field on edges --ar 1:1 --s 750 --q 2 --style raw --no text, bright colors, cartoon, illustration
```

**For DALL-E 3:**

```
A premium social media avatar: the geometric EV monogram (three horizontal bars forming an E connected to two diagonal strokes forming a V) appears as a gold foil stamp pressed into a matte black textured surface. Subtle overhead lighting catches the metallic gold, creating a soft gleam. The background is dark and moody with very subtle texture -- like high-end packaging or a leather portfolio. The overall feel is luxury, exclusivity, and quiet confidence. No text. Square format. Photorealistic material rendering.
```

---

## 4. SVG Concept (Hand-Codeable)

### Technical Description

The SVG uses a single `<path>` element for the icon mark and two `<text>` elements for the wordmark. Viewbox is `0 0 400 100` for the full logo, `0 0 64 64` for the icon alone.

### Icon-Only SVG (64x64 viewbox)

```
viewBox="0 0 64 64"
background: rect fill="#0A0A0A" covering full viewBox

Single path, stroke="#D4AF37", stroke-width="4", fill="none",
stroke-linejoin="miter", stroke-linecap="butt":

Move to (12, 8)          -- top-left of E
Line to (40, 8)          -- top bar of E, rightward
Move to (40, 8)          -- start upper V diagonal
Line to (52, 44)         -- descend to V apex
Line to (32, 56)         -- ascend to bottom-right of E
Move to (32, 56)         -- bottom bar start
Line to (12, 56)         -- bottom bar of E, leftward
Line to (12, 8)          -- vertical stroke of E, upward (closes left side)
Move to (12, 32)         -- middle bar start
Line to (36, 32)         -- middle bar of E, rightward
```

This produces the complete mark in a single path with 8 line segments and 3 moves. Total SVG file size under 500 bytes.

### Full Logo SVG (400x100 viewbox)

```
viewBox="0 0 400 100"
background: rect fill="#0A0A0A" covering full viewBox

Icon path (same geometry as above, scaled and positioned):
  Translated to x=10, y=18, scaled to fit a 64x64 space within the 100-tall viewBox

Text element 1:
  x="95" y="48"
  font-family="Cormorant Garamond, Georgia, serif"
  font-weight="600"
  font-size="32"
  letter-spacing="4"
  fill="#E5E5E5"
  Content: "EVERLIGHT"

Text element 2:
  x="95" y="72"
  font-family="Cormorant Garamond, Georgia, serif"
  font-weight="600"
  font-size="18"
  letter-spacing="6"
  fill="#E5E5E5"
  Content: "VENTURES"
```

### SVG Code (Icon Only -- Copy-Pasteable)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="512" height="512">
  <rect width="64" height="64" fill="#0A0A0A"/>
  <path d="M12,8 L40,8 M40,8 L52,44 L32,56 M32,56 L12,56 L12,8 M12,32 L36,32"
        stroke="#D4AF37" stroke-width="4" fill="none"
        stroke-linejoin="miter" stroke-linecap="butt"/>
</svg>
```

### SVG Code (Full Logo -- Copy-Pasteable)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100" width="800" height="200">
  <rect width="400" height="100" fill="#0A0A0A"/>
  <g transform="translate(10,18)">
    <path d="M12,8 L40,8 M40,8 L52,44 L32,56 M32,56 L12,56 L12,8 M12,32 L36,32"
          stroke="#D4AF37" stroke-width="4" fill="none"
          stroke-linejoin="miter" stroke-linecap="butt"/>
  </g>
  <text x="95" y="48" font-family="Cormorant Garamond, Georgia, serif"
        font-weight="600" font-size="32" letter-spacing="4" fill="#E5E5E5">
    EVERLIGHT
  </text>
  <text x="95" y="72" font-family="Cormorant Garamond, Georgia, serif"
        font-weight="600" font-size="18" letter-spacing="6" fill="#E5E5E5">
    VENTURES
  </text>
</svg>
```

---

## 5. Brand Application Guide

### Do

- Always use the gold icon on dark backgrounds as the default
- Maintain minimum clear space (1x icon bar width) on all sides
- Use the monochrome white variant on busy or photographic backgrounds
- Let the mark breathe -- generous whitespace is part of the brand

### Do Not

- Never stretch, rotate, or skew the logo
- Never apply drop shadows, outer glows, or bevel effects
- Never place the gold variant on a gold or yellow background
- Never rearrange the icon/wordmark relationship (icon is always left or top)
- Never add a tagline to the logo lockup -- taglines go below, separated by clear space
- Never use the icon at widths below 24px -- at that size, use a simple gold square as a placeholder

### Sub-Brand Logo System

Each Everlight sub-brand uses the EV icon mark as a unifying element:

| Sub-Brand | Treatment |
|-----------|-----------|
| HIM Loadout | EV icon at 50% opacity as watermark, sub-brand logo takes primary position |
| Everlight Logistics | EV icon + "LOGISTICS" replacing "VENTURES" in wordmark |
| Everlight Publishing | EV icon + "PUBLISHING" replacing "VENTURES" in wordmark |
| Alley Kingz | Standalone brand -- EV icon appears only in footer/"a venture of" lockup |
| Onyx POS | Standalone brand -- EV icon in footer/"a venture of" lockup |
| Hive Mind | Standalone brand -- EV icon in footer/"a venture of" lockup |

### "A Venture Of" Lockup

For standalone sub-brands, use this footer treatment:

```
[thin horizontal rule, gold, 40px wide]
a venture of
EVERLIGHT VENTURES
[EV icon mark at 16px]
```

All text in Inter Regular, 10px, #8A8A8A (Smoke), letterspaced +150.

---

## 6. File Naming Convention

When exporting assets, use this naming structure:

```
ev-logo-primary-dark.svg        -- Full logo, gold on black
ev-logo-primary-light.svg       -- Full logo, gold+charcoal on white
ev-logo-mono-dark.svg           -- Full logo, white on black
ev-logo-mono-light.svg          -- Full logo, black on white
ev-icon-gold-dark.svg           -- Icon only, gold on black
ev-icon-gold-dark-512.png       -- Icon only, 512px PNG
ev-icon-gold-dark-180.png       -- Icon only, 180px (Facebook)
ev-icon-gold-dark-32.png        -- Icon only, 32px (favicon)
ev-icon-gold-transparent.svg    -- Icon only, gold on transparent
ev-avatar-embossed-512.png      -- Lifestyle avatar version
ev-favicon.ico                  -- Multi-size favicon (16, 32, 48)
```

---

## 7. Quick Reference Card

```
Brand:        Everlight Ventures
Tagline:      Build Different. Build in the Light.
Primary Gold: #D4AF37
Dark Base:    #0A0A0A
Surface:      #1A1A1A
Body Text:    #E5E5E5
Muted Text:   #8A8A8A
Logo Font:    Cormorant Garamond 600
UI Font:      Inter 400/700
Icon Shape:   Geometric E/V monogram -- beacon/prism motif
Minimum Size: 24px icon, 120px full logo
```

---

*This document is the single source of truth for Everlight Ventures visual identity. All sub-brands, contractors, and AI agents should reference this file before producing any branded asset.*
