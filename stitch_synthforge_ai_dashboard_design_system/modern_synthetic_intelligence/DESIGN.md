---
name: Modern Synthetic Intelligence
colors:
  surface: '#faf8ff'
  surface-dim: '#dbd9e0'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3fa'
  surface-container: '#efedf4'
  surface-container-high: '#e9e7ee'
  surface-container-highest: '#e3e1e8'
  on-surface: '#1a1b20'
  on-surface-variant: '#484554'
  inverse-surface: '#2f3035'
  inverse-on-surface: '#f2f0f7'
  outline: '#797586'
  outline-variant: '#c9c4d7'
  surface-tint: '#5f43d4'
  primary: '#431fb8'
  on-primary: '#ffffff'
  primary-container: '#5b3fd0'
  on-primary-container: '#d6ccff'
  inverse-primary: '#c9beff'
  secondary: '#5f5c70'
  on-secondary: '#ffffff'
  secondary-container: '#e5dff7'
  on-secondary-container: '#656276'
  tertiary: '#755b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#cca73c'
  on-tertiary-container: '#503d00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e6deff'
  primary-fixed-dim: '#c9beff'
  on-primary-fixed: '#1b0063'
  on-primary-fixed-variant: '#4725bc'
  secondary-fixed: '#e5dff7'
  secondary-fixed-dim: '#c9c3da'
  on-secondary-fixed: '#1c192a'
  on-secondary-fixed-variant: '#474457'
  tertiary-fixed: '#ffdf90'
  tertiary-fixed-dim: '#e9c254'
  on-tertiary-fixed: '#241a00'
  on-tertiary-fixed-variant: '#584400'
  background: '#faf8ff'
  on-background: '#1a1b20'
  surface-variant: '#e3e1e8'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '700'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  title-card:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-default:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-ui:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
  code-schema:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

The design system projects clarity, intelligence, and approachable sophistication. Built for complex data synthesis workflows, it deliberately avoids the cold, dystopian tropes of machine learning interfaces. Instead, it balances high-utility engineering depth with a luminous, calm visual atmosphere.

The core visual language embraces:
- **Luminous Soft Bento:** Information partitioned into high-radius floating panels on pale tinted canvases, using generous whitespace to decouple mental load from data complexity.
- **Approachable SaaS Elegance:** Crisp geometric typography, pill-shaped control ergonomics, and gentle atmospheric gradient washes (soft lavender to ethereal peach/pink) that signal generative power without visual noise.
- **Confident Precision:** Dense schema displays and data matrices tempered by smooth micro-interactions, soft borders, and vivid violet anchors.

## Colors

The palette is engineered around an electric, high-chroma violet balanced against a light lavender foundation and an ultra-soft violet-tinted ground.

- **Primary Violet (`#5B3FD0`):** Anchors primary actions, selected indicators, interactive state focus, and core analytical visualizations.
- **Secondary Lavender (`#EDE7FF`):** Provides soft structural contrast for badges, selected row highlights, and icon container fills.
- **Tertiary Accent (`#FFD666`):** The signature AI engine identifier, utilized exclusively for machine-generated signals, smart suggestions, and generative status badges.
- **Surfaces & Grounds:** Base background sits on `#FAF8FF`. Primary cards rest on pure `#FFFFFF` layered over subtle `#ECE8F7` structural borders.
- **Typography Tokens:**
  - Headings / Strong: `#1B1740`
  - Body text: `#5C5878`
  - Muted / Supporting: `#9A96B5`
- **Functional Semantics:**
  - Success: `#22A06B`
  - Warning: `#F5A524`
  - Danger / Error: `#E5484D`
  - System Info: `#3B82F6`

## Typography

The type scale combines the open, friendly geometry of Plus Jakarta Sans for UI flow and editorial titles with the rigor of JetBrains Mono for data structures, regex patterns, and synthetic entity distributions.

- Headings demand tight negative tracking (`-0.02em` to `-0.03em`) to deliver modern editorial confidence.
- Body text preserves ample breathing room with a 1.45–1.5 line-height ratio to maximize scanning speed across complex data panels.
- JetBrains Mono provides unambiguous character differentiation for synthetic schema identifiers, dataset tokens, and seed variables.

## Layout & Spacing

The layout is grounded in a clean 8px baseline rhythm. Information follows a flexible bento modular structure:

- **App Shell:** A dedicated 240px static or collapsible navigation sidebar paired with a 64px persistent utility header.
- **Bento Grid:** Content spans a 12-column adaptive grid using 24px (`1.5rem`) gutters on desktop screens, compressing to 16px on tablets and a single column on mobile screens.
- **Card Breathing Room:** Bento modules require 24px internal padding (`space-lg`) for standard cards and 32px (`space-xl`) for featured generation canvases or hero panels.
- **Vertical Hierarchy:** Section groups maintain 32px to 48px vertical margins to enforce visual chunking without requiring aggressive dividing lines.

## Elevation & Depth

Visual hierarchy relies on diffuse, tinted ambient shadowing rather than opaque dark drops, creating an uplifting, luminous feel.

- **Level 0 (Canvas Base):** Flat `#FAF8FF`. Ambient gradients (`linear-gradient(135deg, #E9DFFF 0%, #F8D9F0 50%, #FFF3DF 100%)`) exist exclusively as background blurs with low opacity (40-60%) behind hero surfaces.
- **Level 1 (Bento Surfaces):** White `#FFFFFF` backed by a 1px border of `#ECE8F7` and a soft ambient shadow: `0 4px 20px -2px rgba(91, 63, 208, 0.04), 0 2px 6px -1px rgba(27, 23, 64, 0.02)`.
- **Level 2 (Interactive Floating / Active Cards):** `0 12px 32px -4px rgba(91, 63, 208, 0.08), 0 4px 12px -2px rgba(27, 23, 64, 0.03)`.
- **Level 3 (Overlays, Menus & Modals):** `0 24px 48px -8px rgba(27, 23, 64, 0.12), 0 8px 16px -4px rgba(91, 63, 208, 0.06)` with backdrop blur filter (`backdrop-filter: blur(12px)`).

## Shapes

The design system applies curved geometries to soften dense technical interfaces:

- **Interactive Pills (`9999px` / `rounded-full`):** All call-to-action buttons, segmented tabs, filter tags, and status chips use full pill geometry.
- **Bento Containers (`20px` to `24px`):** Content cards, table enclosures, and workflow nodes use a 20px curvature to produce tactile panels.
- **Controls & Form Fields (`12px`):** Inputs, select triggers, and code blocks adopt a balanced 12px radius, avoiding awkward nested pill clashes while keeping the friendly aesthetic.

## Components

### Buttons
- **Primary:** Full pill (`border-radius: 9999px`), solid `#5B3FD0`, text `#FFFFFF`. Hover: `#4A30B8`. Focus: 3px outer ring `#EDE7FF`.
- **Secondary:** Full pill, transparent background, 1.5px border `#5B3FD0`, text `#5B3FD0`. Hover: background `#EDE7FF`.
- **Ghost/Tertiary:** Full pill, transparent background, text `#5C5878`. Hover: background `#EDE7FF`, text `#1B1740`.

### Pills, Chips & AI Badges
- **Status Chips:** Full pill, height 24px, 10px horizontal padding, text size 12px semibold. Built with subtle tint backgrounds and solid semantic dots (e.g., `#22A06B` for active pipelines).
- **AI Feature Badge:** Pill indicator with `#FFD666` background, `#1B1740` text and sparkle glyph (`✦ AI`), letter-spacing 0.02em, font size 11px uppercase weight 700.

### Segmented Controls & Navigation
- **Pill Tab Switchers:** Enclosed container `#FAF8FF` with 1px border `#ECE8F7`. Active segment transitions into an elevated white pill with `#5B3FD0` text and subtle micro-shadow.
- **Sidebar Items:** Pill highlight on active item with `#EDE7FF` background and `#5B3FD0` font weight 600. Default state remains neutral text `#5C5878`.

### Input Fields & Controls
- **Inputs:** 12px border radius, 44px height, background `#FFFFFF`, border 1px solid `#ECE8F7`, placeholder `#9A96B5`. Focus shifts border to `#5B3FD0` with `0 0 0 3px #EDE7FF`.
- **Checkboxes & Radios:** 6px radius for checkboxes, full circle for radios. Selected state fills with `#5B3FD0` and crisp white check/dot glyphs.

### Cards & Bento Panels
- White `#FFFFFF` base, 20px corner radius, 1px border `#ECE8F7`.
- Header areas feature a 40px rounded-square lavender icon container (`#EDE7FF`) with a `#5B3FD0` line icon alongside an 18px semibold card title.
- Tables nested in cards use borderless rows on `#FFFFFF` with `#FAF8FF` zebra or hover states, separated by hairline `#ECE8F7` rules.