# EIOS Cockpit Design System

Source of truth for the operator cockpit in `EIOS/web-prototype/`. Tokens live in `src/app/globals.css`; `src/tests/cockpit/design-guard.test.ts` fails when a component leaves the colour budget.

## Visual world: Sovereign Light

Institutional, calm, data first. A light analytical workspace framed by dark chrome. Reference points: Palantir Foundry object pages, Blueprint density, QuantumBlack restraint.

### Surfaces
- Light analytical surfaces: canvas `cx-canvas` `#f4f6f8`, elevated `#ffffff`, hairlines `cx-line-*`.
- **Dark chrome is intentional**: the left nav rail and the first row of the top header (`cockpit-rail` `#1c2530`, `chrome-*`). It frames the workspace and gives contrast. Do not lighten it.
- Dark action buttons (Flywheel Feedback, Theater) are intentional contrast anchors. Keep them solid near-black with white text.
- The Theater/Studio canvas (`cx-studio*`) is the one deliberate dark surface inside the workspace, opened on demand.
- Radii 0–4px, sharp. One elevation device per element (border or shadow, never both).

### Colour budget
Colour means state. Everything else is neutral.

| Role | Token | Value | Use |
|---|---|---|---|
| Neutral | `slate`, `cx-ink`, `cx-muted`, `cx-faint`, `cx-line-*` | `#182026` / `#5c7080` / `#8a9ba8` | text, borders, nodes |
| Accent (one) | `cx-accent`, `cx-info`, `cx-select` | `#106ba3` | selection, focus, links, primary data series |
| Alert (one) | `cx-bad` | `#a82a2a` | critical, breach, danger only |
| Status text | `cx-ok` `#0d8050`, `cx-warn` `#a66321` | | verified / needs attention, as text or a dot. Never a filled tag |

Every Tailwind hue family aliases onto four ramps (`blue`, `red`, `green`, `amber`) in `globals.css`. Write classes as `red-*`, `green-*`, `amber-*`, `blue-*`, `slate-*` only. Category tags (tier, source, model, cohort) are neutral outline, never tinted.

### Typography
Unchanged from the shipped cockpit; it is part of the identity and is not up for refactoring without a visual review.
- **Inter** for titles, body and prose. **JetBrains Mono** (`--font-mono`) for section headers, toolbar labels, IDs, hashes and figures. Section titles and chips keep their mono-caps treatment.
- Type tokens: `text-label` 11px, `text-title` 13px.

### Structure
- Panels use the shared `PanelHeader` and `Chip` in `src/components/cockpit/ui/`.
- Three columns: triage rail, dossier, canvas; governed action shelf at the bottom. Layout rules and the persona matrix are in `EIOS/web-prototype/CLAUDE.md`.

### Motion
150–250ms ease-out, opacity and transform only. No continuous pulsing except loading; honour `prefers-reduced-motion`.

### Provenance
Provenance stays in the wire contract (`data_origin`, per-figure source and as-of) and behind each figure's popover. The UI does not show per-figure DEMO or ILLUSTRATIVE chips.

---

## Landing surface: Field Report (dark)

A second, separate world for `/` only (`EIOS/web-prototype/src/components/landing/`, tokens scoped under `.fde`). It is a Persuade surface: a forward-deployed-engineering case study set as one exploded isometric stack of the five layers. The cockpit rules above (light analytical surfaces, one dark chrome strip) do not apply to it, and nothing here may leak into cockpit components. Direction contract: `.impeccable/surfaces/eios-web-prototype-src-app-page-tsx.md`.

- **Ground and ink:** matte near-black ground (`#0e1116`), warm off-white ink (`#ecebe6`), secondary text at 68% ink, hairline rules at 16% ink. One pale steel-blue (`#9db7cf`, `--sig`) is reserved for the signal path and the active layer. One warm state colour (`--warn`, `#d6a15f`) marks only a missed or unmeasured item.
- **Type:** Schibsted Grotesk at regular weight, display `clamp(2.5rem, 4.2vw, 4.5rem)`, tracking -0.025em; uppercase tracked small labels; JetBrains Mono only for figures, ids and tags.
- **Form language:** sharp corners, hairline brackets with serif ticks, dashed leaders, no cards, no gradients, no glow, no glass. Tags (`MEASURED`, `TESTED IN CI`, `NOT MEASURED`, `BY DESIGN`) are outlined, never filled.
- **Motion:** one authored moment, the pinned scroll sequence (81 frames on a canvas, blended with `mix-blend-mode: screen`; the sticky parent carries its own ground for that), plus the hero slabs drawing in and one travelling dash on the signal arrow. Everything is off under `prefers-reduced-motion`, where the sequence becomes a static still with all five captions listed.
- **Interactive figures:** one figure frame (hairline border, control bar on top, caption with the data's origin below). Controls are outlined switches, outlined chip buttons and a segmented control whose pressed state inverts to ink. Each figure draws from a baked engine snapshot in `components/landing/data/` whose header names the endpoint and as-of; recorded agent turns are quoted verbatim.
- **Map:** deck.gl over Natural Earth outlines with no basemap; arcs coloured by corridor tier (ink low, steel-blue medium, warm high), shared exits in the warm colour, jurisdiction fills in warm steps; scroll-zoom off so the page keeps scrolling.
- **Architecture:** isometric platforms in the hero's slab grammar; chips with a steel-blue left tick mark a Google Cloud service; traced paths animate as steel-blue dashed hops.
- **Honesty:** every figure is a `[MEASURED]` result from repo docs or an engine snapshot, and lives in `content.ts` or `data/`; misses stay in the ledger; client activity is labelled synthetic while the reference layer is real public data; the client is never named; copy says "workstation".
- **Rasters:** `public/landing/orbit/*` are generated frames (Magnific, 2026-10-18); provenance in `public/landing/PROVENANCE.md` and per-file sidecars.

### Landing round 3 additions
- Charts (`MiniChart`) draw only values already printed in the row's copy: a fill, a unit strip or a one-dimensional track with dot marks. Reference values are a vertical tick, earlier or weaker values a hollow dot. No axes numbers; the labels carry the values.
- The architecture trace is scroll-linked above 1100 px (pinned, question then action). Any control takes over; scrolling back to the top hands it back. Narrow screens and reduced motion keep the manual and auto-stepping behaviour.
- `PushIn` is the second frame sequence (generated clip, graded like the hero orbit) that ends on the workstation layer before the close.
