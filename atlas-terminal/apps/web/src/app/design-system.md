# ATLAS Morgan Stanley Design System

## Core Palette
- `surface.canvas`: `#FAFAFA`
- `surface.raised`: `#FFFFFF`
- `surface.sunken`: `#F1F3F6`
- `brand.navy`: `#1B2A4A`
- `brand.blue`: `#2E5B9A`
- `brand.gold`: `#C4A35A`
- `fin.positive`: `#2D8B5E`
- `fin.negative`: `#C0392B`
- `fin.warning`: `#D9822B`
- `text.primary`: `#1A1A2E`
- `text.secondary`: `#4A5568`
- `text.muted`: `#6B7B8D`

## Typography
- Headings: `Source Serif 4`
- Body: `Inter`
- Numbers, tickers, dense tables: `JetBrains Mono` with tabular numerals

## Component Rules
- Page titles use serif typography and a bottom hairline.
- Cards use `surface.raised`, `border.DEFAULT`, and `shadow-card`.
- Tabs use navy active states and sunken inactive rails.
- Positive/negative metrics use `fin.positive` and `fin.negative`; warnings use gold or warning amber, not red.
- Charts should import colors from `src/app/lib/chart-theme.ts` instead of hardcoding hex values.

## Migration Notes
- Legacy `bg.*` and `accent.*` Tailwind tokens still exist as compatibility aliases.
- `/report` remains the visual source of truth for print layout; the rest of the app is converging toward that tone.
