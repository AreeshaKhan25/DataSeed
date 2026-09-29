# Google Stitch Prompts v3 — short, one per screen

## What changed and why

v2 failed for a simple reason: the prompts were 400+ words each. Stitch treats a long prompt as a
wall to summarise, drops most of it, and stalls after a couple of screens. **These are 80–120 words
each.** Paste the theme once, then run the screens one after another.

**Design direction** — now based on `D:\arlogistics\AR_Logistics_Pakistan` (the UI you liked),
cross-checked against current work on Dribbble.

From your logistics app:
- Light blue-grey canvas `#F2F5F9` with white cards — not another dark dashboard
- Navy `#1F4E79` as the single primary
- **A dark floating macOS dock with colourful squircle app icons** — this is the signature. A light
  page with a dark dock is rare and it is what will stop this looking generated.
- Shiny CTA with a rotating gradient border, gradient stat cards that tilt on hover

From the Dribbble pass (what current data tools actually do):
- Pale blue-grey page, pure white cards, hairline borders, very soft shadows — no heavy elevation
- Big numbers with small muted labels
- Status as soft tinted pills at ~12% opacity, never solid blocks
- Tables with hairline row rules, no zebra striping, numbers right-aligned
- Charts with gradient fills under the line and rounded bar tops
- Generous whitespace; density comes from typography, not from cramming

**How to run it:** Stitch → Web project → paste Prompt 0 alone → then screens 1–10 in order, one
at a time. If a screen loses the dock or turns dark, paste this reminder above it:
`Light #F2F5F9 page, white cards, navy #1F4E79, dark floating dock at the bottom.`

---

## Prompt 0 — Theme

```
Design a web app called "DataSeed" — a synthetic data generation platform.

Light theme. Page background #F2F5F9. Cards are pure white, 16px radius,
1px #E4E9F0 border, very soft shadow. Generous whitespace.

Colors: primary navy #1F4E79, dark navy #163A5C, danger red #C0392B,
success green #15803D, teal #0E7490, orange #C2410C, violet #6D28D9.
Text #1A1C1F, muted text #646464.

Fonts: Space Grotesk bold for headings and big numbers. Plus Jakarta Sans
for all body text and labels. Space Mono for data, IDs, seeds and numbers.

Navigation is NOT a sidebar. It is a dark floating dock, horizontally
centered near the bottom of every screen: a pill with 21px radius, dark
charcoal at 78% opacity, 1px white 12% border, 10px padding, soft drop
shadow. Inside it sit colourful app icons — rounded squares with 22%
radius, each a solid color from the palette above, with a white line icon
centered. Icons magnify on hover like the macOS dock.

Buttons: primary is solid navy, 8px radius, uppercase 12px bold label with
slight letter-spacing, and a subtle animated gradient border. Secondary is
white with a #E4E9F0 border. Buttons scale down slightly when pressed.

Status pills: soft tinted background at 12% opacity with matching text.
Tables: white, hairline #EEF1F5 row lines, no zebra stripes, muted
uppercase headers, numbers right-aligned in Space Mono.
```

---

## Prompt 1 — Dashboard

```
Screen: "Projects" dashboard for DataSeed. Light #F2F5F9 page, dark floating
dock at the bottom.

Top: "Projects" heading with a search field and a navy "New project" button.

A row of four gradient stat cards with white text and a soft blurred circle
in the corner: "Projects 12", "Rows generated 2.4M", "Avg utility 91%",
"Exports 38". Use navy, teal, violet and orange gradients.

Below, a grid of white project cards, 3 per row. Each shows the project
name, small tinted pills for "Tabular", "Relational", "Documents", a line
of Space Mono metadata "4 tables · 120k rows · seed 42", four small score
bars labelled Integrity, Fidelity, Utility, Privacy, and "Updated 2h ago".
```

---

## Prompt 2 — New project / ingest

```
Screen: "New project" for DataSeed. Light page, centered 720px column, dark
dock at the bottom.

Heading "Bring your schema" with the subtitle "We learn the shape of your
data and never store a real record."

A large white drop zone with a dashed #E4E9F0 border and a navy upload
icon: "Drop a CSV, SQL schema, or JSON sample".

Below it three white option rows, each with a colored squircle icon, a
title and a description: "Connect a database", "Paste a schema",
"Start from a template".

At the bottom a horizontal stepper: Ingest, Schema, Relationships,
Generate, Validate, Export — with Ingest active in navy.
```

---

## Prompt 3 — Schema studio

```
Screen: "Schema" for DataSeed. Light page, dark dock at the bottom.

Heading "Schema" with "3 tables · 19 columns" beneath it.

A white banner tinted violet: "AI inferred 7 semantic types and flagged 2
columns as direct PII", with "Review" and a navy "Accept all" button.

Left, a narrow white card listing tables with row counts in Space Mono:
customers 1,200, orders 4,860, order_items 14,203. "customers" is selected.

Right, a wide white card with a column table. Headers: Column, Type,
Semantic, PII, Privacy, Nulls, Sample. Rows for customer_id, name, email,
signup_date, balance, segment, notes. Column names and samples in Space
Mono. PII shows red "Direct" and amber "Quasi" tinted pills. AI-inferred
rows have a small violet sparkle icon.
```

---

## Prompt 4 — Relationships

```
Screen: "Relationships" for DataSeed — an entity-relationship canvas. Light
page with a faint dot grid, dark dock at the bottom.

Four white node cards connected by curved navy lines: customers, orders,
order_items, products. Each card has a navy header bar with the table name
in Space Mono and field rows beneath, with small key icons on primary keys
and teal link icons on foreign keys.

Small pills on each connector show "1:N" or "N:1".

Top-left, a floating white toolbar with zoom in, zoom out, fit and
auto-layout icons.

Right, a white panel "Relationship" showing the selected edge, a
cardinality selector for 1:1 / 1:N / N:N, a small bar chart of children
per parent, and a toggle "Compute parent totals from children", switched on.
```

---

## Prompt 5 — Workspace

```
Screen: "Workspace" for DataSeed — live data generation. Light page, dark dock
at the bottom. This is the main screen.

Heading "Workspace" with "northwind_retail · seed 42" in Space Mono, and a
green "Engine ready" pill on the right.

Tabs: Tabular, Relational, Documents — Relational active.
Below, table pills: customers, orders, order_items — orders selected.

A wide white card holding a data table. Headers in muted uppercase:
order_id, customer_id, order_date, status, items, total. About 12 rows in
Space Mono, hairline row lines, no zebra. Status uses tinted pills: green
shipped, amber pending, red refunded. The total column is right-aligned
and bold navy.

At the card's base: "6,240 of 10,000 rows" with a navy progress bar.

Right, a 340px column of separate white cards: "Output" with Rows and Seed
inputs, "Quality" with null rate and outlier rate sliders, "Privacy" with
three selectable pills, "Edge cases" with four checkboxes. Then a navy
"Generate" button and a white "Export" button.
```

---

## Prompt 6 — Trust report

```
Screen: "Trust report" for DataSeed. Light page, dark dock at the bottom.
Make this the most polished screen.

Four white cards in a row, each with a circular progress ring, a big number
in Space Grotesk and a short caption:
Integrity 100 green "0 orphan keys", Fidelity 96 navy "Distributions match",
Utility 75 navy "Trained on synthetic, tested on real", Privacy 99 green
"No record traces to a real person".

A green tinted banner: "All gates passed — cleared for export" with an
"Export" button.

Left white card "Utility": a grouped bar chart comparing "Trained on real"
in grey and "Trained on synthetic" in navy, then three Space Mono lines —
TRTR 0.936, TSTR 0.827, ratio 0.884.

Right white card "Privacy": three rows with meter bars — exact matches 0,
distance to closest record 0.34, membership inference 0.51. Below,
"Detection AUC 0.54" as a big number with the caption "0.50 means
indistinguishable from real".

Full-width white card at the bottom: "Fidelity by column" — a table of
column, distance, match percentage, and a small overlaid sparkline.
```

---

## Prompt 7 — Documents

```
Screen: "Documents" for DataSeed. Light page, dark dock at the bottom.

Heading "Documents" with a green "Totals reconciled" pill.

Left, a white card listing templates with small paper thumbnails: Invoice
EU (VAT) selected, Invoice US, Invoice IN (GST), Bank statement,
Purchase order.

Center, a realistic invoice on a white page with a soft shadow: header
"INVOICE" with "#INV-10432" in Space Mono, billed-to and from blocks, a
line items table with Item, Qty, Price, Amount, and a totals block showing
Subtotal 1,240.00, VAT 20% 248.00 and TOTAL 1,488.00 in bold navy. Beneath
it a small pager reading "Document 3 of 50".

Right, white cards: "Settings" with count, region, currency and date
format; "Tax rule" showing VAT 20%; a range slider "1 to 8 line items"; a
locked toggle "Totals computed from line items"; format pills PDF, HTML,
JSON, CSV; and a navy "Generate 50 documents" button.
```

---

## Prompt 8 — Export

```
Screen: "Export" modal for DataSeed, centered over a dimmed light page, 640px
wide, white, 16px radius.

Title "Export dataset" with "northwind_retail · 3 tables · 19,263 rows ·
seed 42" in Space Mono beneath it.

A green tinted strip with a check icon: "All integrity gates passed".

A 2x3 grid of selectable format cards, each with an icon, a name and a
Space Mono size: CSV 4.2 MB, JSON 6.8 MB, Parquet 1.9 MB, SQL dump 5.1 MB,
Postgres, PDF documents 12.4 MB. SQL dump is selected with a navy border.

Three toggles: include schema, include trust report, include generation
config. All on.

A collapsed "Reproduce via API" section showing a dark code block with a
copy icon.

Footer: a white "Cancel" button and a navy "Download" button.
```

---

## Prompt 9 — Generating

```
Screen: generation in progress for DataSeed. Light page, dark dock at the
bottom, content centered in a 560px column.

Heading "Generating 19,263 rows" with "northwind_retail · seed 42" in
Space Mono.

A vertical list of seven steps, each a row with a status icon, a label and
a right-aligned Space Mono value:
Reading schema — done, green check, 0.1s
Fitting distributions — done, green check, 0.8s
Generating customers — done, green check, 1,200 rows
Generating orders — in progress, navy spinner, with a navy progress bar
beneath and "2,914 / 4,860 rows"
Generating order_items — pending, muted
Reconciling totals — pending, muted
Validating integrity — pending, muted

Completed steps are joined by a green vertical line, pending ones by a grey
line. At the bottom, a white "Cancel" button and the muted note
"Deterministic — seed 42 always produces identical output".
```

---

## Prompt 10 — Settings

```
Screen: "Settings" for DataSeed. Light page, dark dock at the bottom, content
in a 780px column.

Heading "Settings".

White cards stacked with 16px gaps, each with a title and rows:
"Generation" — default row count, default seed, engine selector
(Copula / CTGAN), locale and currency dropdowns.
"AI" — a masked API key field with a green "Connected" pill, a model
dropdown, and a toggle "Cache AI responses" switched on.
"Privacy defaults" — three toggles: block exact matches, hash direct PII,
add differential noise.
"Export" — default format pills and a toggle "Require passing trust report
before export", switched on and locked.

Each card has its own small navy "Save" button in the corner.
```

---

## Porting notes

Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
```

You already have the two hardest components written in `D:\arlogistics\AR_Logistics_Pakistan`:
`components/ui/mac-os-dock.tsx` and `components/ui/shiny-button.tsx`, plus the dock and shiny-CTA
CSS in `app/globals.css`. **Copy those across rather than rebuilding them** — the dock is the single
most distinctive element here and it is already working code. `dashboard-stat-card.tsx` gives you
the tilting gradient stat cards for Prompt 1 for free.

Dock icon colours, reused as category accents throughout: navy `#1F4E79` (dashboard),
teal `#0E7490` (data), orange `#C2410C` (generate), violet `#6D28D9` (AI/schema),
grey `#374151` (settings), red `#C0392B` (danger).

One thing to watch: on a light page the muted `#646464` is fine for labels, but keep all table
values at `#1A1C1F`. Judges will be reading this off a projector.
