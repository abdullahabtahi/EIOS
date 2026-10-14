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
