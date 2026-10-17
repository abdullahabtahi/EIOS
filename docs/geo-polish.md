# Geospatial polish: accessibility, labels, narrow widths, assistant window

Branch `feat/geo-a11y-polish`. Web only (`EIOS/web-prototype/src/components/cockpit/geo/`); no backend, wire or token change.

## What changed

| Area | Change | Test |
|---|---|---|
| Map for assistive tech | The map region's description is built from what is drawn and what is picked (`geo-map-describe.ts`), names the keyboard route (the list, the `/` key) and how the focused map pans and zooms. The region shows a focus ring when anything inside it has keyboard focus. | `geo-map-describe.test.ts` |
| Label crowding | Country names carry the volume behind them and are thinned from computed footprints at the map's zoom (`geo-labels.ts`); the ends of a picked route always keep their names; hidden names return as the map zooms in. | `geo-labels.test.ts`, `geo-layers.test.ts` |
| Tooltip | Placed by its measured height and width, flipped at the map edge and held inside it (`geo-tooltip-place.ts`). | `geo-tooltip-place.test.ts` |
| Narrow widths | Below 640px the legend is a "Key" line you open; before, the colour key was dropped and an orphaned note stayed. Open width is capped so it clears the assistant launcher and zoom control. | `geo-legend-narrow.test.tsx` |
| Assistant window | Titled "Geospatial Agent" (hairline below; the floating window leads with the grip icon that says it can be moved, the docked column with the assistant icon). Resizes from its top left corner (the window starts at the bottom right, so that is the only way to grow), with pointer, arrow keys (Shift for larger steps) and double-click to reset; the corner has no glyph at rest and shows a small bracket on hover and focus; the size is remembered in `eios.geo.chat`. | `geo-chat-dock.test.ts` |
| Contrast | Disabled layer label and the two window icons moved from `cx-faint` to `cx-muted`. | measured below |

## Measured `[MEASURED]`

- Contrast of the tokens against the surfaces they sit on: `cx-muted` 5.14:1 on white, 4.82:1 on `cx-sub`, 4.51:1 on `cx-sub-2`; `cx-faint` 2.86:1 on white (fails 4.5:1 text and 3:1 icons). A script over the rendered geo page (corridors, jurisdictions, logins, chat open) found no other text under 4.5:1 in the panel, legend or chat. The dark nav and top bar were not judged (intentional chrome).
- Real assistant answer in the floating window: "Read: ranked leads", 3.3 s on the default model, ten figures with sources.

## Tried and dropped

deck.gl `CollisionFilterExtension` for labels: in the interleaved Google Maps overlay it hid every label, so the footprints are computed in `geo-labels.ts` instead.

## Not shown on screen

A route that crosses the antimeridian: the seeded world has none (the longest, Singapore to Colombia, goes west). The wrap is covered by `geo-curves.test.ts`.

## Left

Pointer-free selection of a mark on the map (the list is the keyboard route by design); the assistant's answers name corridors by country code ("ID>MM") where the panel uses names; `[ASSUMPTION]` label footprints (7 px per character at 12 px) are estimates, not measured text widths.
