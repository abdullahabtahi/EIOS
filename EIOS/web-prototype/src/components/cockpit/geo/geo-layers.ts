import { ArcLayer, GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type {
  GeoFlows,
  GeoReference,
  GeoSelection,
  LayerId,
  LngLat,
  ReferenceCountry,
  RiskTier,
} from './geo-types';
import { corridorId, pairId, shownCorridors, shownPairs } from './geo-rank';

type Rgba = [number, number, number, number];

/** Colour carries risk only: elevated tiers are red and amber; low and unrated corridors stay a quiet grey, never green. */
export const TIER_COLOR: Readonly<Record<RiskTier, Rgba>> = {
  low: [138, 155, 168, 120],
  medium: [217, 150, 20, 210],
  high: [200, 50, 50, 220],
};
const MISMATCH_COLOR: Rgba = [16, 107, 163, 210];
const OFFSHORE_COLOR: Rgba = [16, 107, 163, 150];
const SELECTED_COLOR: Rgba = [17, 17, 17, 255];
const UNRATED_COLOR: Rgba = [138, 155, 168, 120];
const OUTLINE_COLOR: Rgba = [120, 134, 148, 90];
const NO_FILL: Rgba = [0, 0, 0, 0];

/** [ASSUMPTION] below this many incorporated entities a country is not drawn as an offshore centre (keeps the map readable). */
export const MIN_OFFSHORE_ENTITIES = 500;
const AREA_FILL_ALPHA = 70;
// Arcs lift out of the map plane; on a flat (untilted) map that is invisible, so lay the arc in the plane to read as a curve.
const ARC_TILT_DEG = 90;
const ARC_HEIGHT = 0.06;
/** An arc drawn for the current pick (a gateway and its users' homes, an account's logins), above every lens. */
export interface HighlightArc {
  readonly from: string;
  readonly to: string;
  readonly weight: number;
}

/** Where the pointer is over the map, in the map's own pixels, so a tooltip can sit beside it. */
export interface HoverPoint {
  readonly x: number;
  readonly y: number;
}

export interface LayerHandlers {
  readonly onHover?: (selection: GeoSelection, point?: HoverPoint) => void;
  readonly onSelect?: (selection: GeoSelection) => void;
}

interface ArcRow {
  readonly source: LngLat;
  readonly target: LngLat;
  readonly width: number;
  readonly color: Rgba;
  readonly ref: NonNullable<GeoSelection>;
}

const toLngLat = (p: LngLat): [number, number] => [p[0], p[1]];
const MIN_ARC_WIDTH = 1.5;
const ARC_WIDTH_RANGE = 3.5;
const SELECTED_EXTRA_WIDTH = 1.5;
/** Arc width grows with the square root of the value relative to the largest, so every dataset reads the same. */
const widthFor = (value: number, max: number): number =>
  MIN_ARC_WIDTH + ARC_WIDTH_RANGE * Math.sqrt(max > 0 ? value / max : 0);
const countryRef = (c: ReferenceCountry): NonNullable<GeoSelection> => ({ kind: 'country', id: c.iso2 });

/** FATF list to risk tier; an unlisted country is unrated (null), not low. */
export function tierOf(country: ReferenceCountry): RiskTier | null {
  if (country.fatf_list === 'call_for_action') return 'high';
  if (country.fatf_list === 'increased_monitoring') return 'medium';
  return null;
}

function positions(reference: GeoReference): ReadonlyMap<string, LngLat> {
  return new Map(reference.countries.map((c) => [c.iso2, c.position]));
}

function corridorRows(flows: GeoFlows, reference: GeoReference, selection: GeoSelection): readonly ArcRow[] {
  const at = positions(reference);
  const max = Math.max(0, ...flows.corridors.map((c) => c.volume_usd));
  const drawn = shownCorridors(flows);
  // A corridor picked from the list is drawn even when it is not among the largest, so a selection is never invisible.
  const picked = selection?.kind === 'corridor' ? flows.corridors.find((c) => corridorId(c) === selection.id) : undefined;
  const rows = picked && !drawn.includes(picked) ? [...drawn, picked] : drawn;
  return rows.flatMap((c) => {
    const source = at.get(c.origin);
    const target = at.get(c.destination);
    if (!source || !target) return [];
    const id = corridorId(c);
    const isPicked = picked === c;
    const color = isPicked ? SELECTED_COLOR : c.tier ? TIER_COLOR[c.tier] : UNRATED_COLOR;
    const width = widthFor(c.volume_usd, max) + (isPicked ? SELECTED_EXTRA_WIDTH : 0);
    return [{ source, target, width, color, ref: { kind: 'corridor', id } as const }];
  });
}

function mismatchRows(flows: GeoFlows, reference: GeoReference, selection: GeoSelection): readonly ArcRow[] {
  const at = positions(reference);
  const max = Math.max(0, ...flows.mismatch_pairs.map((p) => p.accounts));
  const drawn = shownPairs(flows);
  const picked = selection?.kind === 'mismatch' ? flows.mismatch_pairs.find((p) => pairId(p) === selection.id) : undefined;
  const rows = picked && !drawn.includes(picked) ? [...drawn, picked] : drawn;
  return rows.flatMap((p) => {
    const source = at.get(p.kyc_country);
    const target = at.get(p.ip_country);
    if (!source || !target) return [];
    const isPicked = picked === p;
    const width = widthFor(p.accounts, max) + (isPicked ? SELECTED_EXTRA_WIDTH : 0);
    return [{ source, target, width, color: isPicked ? SELECTED_COLOR : MISMATCH_COLOR, ref: { kind: 'mismatch', id: pairId(p) } as const }];
  });
}

const point = (info: { x: number; y: number }): HoverPoint => ({ x: info.x, y: info.y });

function arcLayer(id: string, rows: readonly ArcRow[], handlers: LayerHandlers): ArcLayer<ArcRow> {
  return new ArcLayer<ArcRow>({
    id,
    data: rows as ArcRow[],
    pickable: true,
    antialiasing: true,
    getSourcePosition: (d) => toLngLat(d.source),
    getTargetPosition: (d) => toLngLat(d.target),
    getSourceColor: (d) => d.color,
    getTargetColor: (d) => d.color,
    getWidth: (d) => d.width,
    getTilt: () => ARC_TILT_DEG,
    getHeight: () => ARC_HEIGHT,
    onHover: (info) => handlers.onHover?.(info.object ? (info.object as ArcRow).ref : null, point(info)),
    onClick: (info) => handlers.onSelect?.(info.object ? (info.object as ArcRow).ref : null),
  });
}

interface AreaFeature {
  readonly type: 'Feature';
  readonly geometry: ReferenceCountry['boundary'];
  readonly properties: { readonly country: ReferenceCountry };
}

// One Feature wrapper per country, built once per reference payload (the payload is a cached snapshot).
const AREAS = new WeakMap<GeoReference, readonly AreaFeature[]>();
function areaFeatures(reference: GeoReference): readonly AreaFeature[] {
  const cached = AREAS.get(reference);
  if (cached) return cached;
  const built = reference.countries.map((country) => ({ type: 'Feature' as const, geometry: country.boundary, properties: { country } }));
  AREAS.set(reference, built);
  return built;
}

function riskAreaLayer(reference: GeoReference, selection: GeoSelection, handlers: LayerHandlers): GeoJsonLayer<AreaFeature['properties']> {
  const picked = (c: ReferenceCountry) => selection?.kind === 'country' && selection.id === c.iso2;
  return new GeoJsonLayer<AreaFeature['properties']>({
    id: 'geo-risk',
    data: areaFeatures(reference) as never,
    pickable: true,
    stroked: true,
    filled: true,
    lineWidthMinPixels: 1,
    lineWidthUnits: 'pixels',
    getFillColor: (f) => {
      const tier = tierOf((f as unknown as AreaFeature).properties.country);
      if (!tier) return NO_FILL;
      const [r, g, b] = TIER_COLOR[tier];
      return [r, g, b, AREA_FILL_ALPHA];
    },
    getLineColor: (f) => (picked((f as unknown as AreaFeature).properties.country) ? SELECTED_COLOR : OUTLINE_COLOR),
    getLineWidth: (f) => (picked((f as unknown as AreaFeature).properties.country) ? 3 : 1),
    updateTriggers: { getLineColor: [selection?.kind, selection?.id], getLineWidth: [selection?.kind, selection?.id] },
    onHover: (info) => handlers.onHover?.(info.object ? countryRef((info.object as unknown as AreaFeature).properties.country) : null, point(info)),
    onClick: (info) => handlers.onSelect?.(info.object ? countryRef((info.object as unknown as AreaFeature).properties.country) : null),
  });
}

function offshoreLayer(reference: GeoReference, handlers: LayerHandlers): ScatterplotLayer<ReferenceCountry> {
  const centres = reference.countries.filter((c) => (c.entities_incorporated ?? 0) >= MIN_OFFSHORE_ENTITIES);
  return new ScatterplotLayer<ReferenceCountry>({
    id: 'geo-offshore',
    data: centres,
    pickable: true,
    stroked: true,
    radiusUnits: 'pixels',
    lineWidthMinPixels: 1,
    getPosition: (c) => toLngLat(c.position),
    getRadius: (c) => Math.max(5, Math.sqrt(c.entities_incorporated ?? 0) / 14),
    getFillColor: OFFSHORE_COLOR,
    getLineColor: [255, 255, 255, 255],
    onHover: (info) => handlers.onHover?.(info.object ? countryRef(info.object as ReferenceCountry) : null, point(info)),
    onClick: (info) => handlers.onSelect?.(info.object ? countryRef(info.object as ReferenceCountry) : null),
  });
}

/**
 * Pure: data plus view state in, deck.gl layers out. The model never writes layer specs (RL-1). Reference lenses (FATF
 * areas, offshore centres) draw only when the reference layer is present; flow lenses only when both the flows and
 * the reference layer (which places the countries) are present. Absent data draws nothing.
 */
function highlightLayer(arcs: readonly HighlightArc[], reference: GeoReference): ArcLayer<ArcRow> | null {
  const at = positions(reference);
  const max = Math.max(0, ...arcs.map((a) => a.weight));
  const rows = arcs.flatMap((a): ArcRow[] => {
    const source = at.get(a.from);
    const target = at.get(a.to);
    if (!source || !target || a.from === a.to) return [];
    return [{ source, target, width: widthFor(a.weight, max) + SELECTED_EXTRA_WIDTH, color: SELECTED_COLOR, ref: { kind: 'mismatch', id: `${a.from}>${a.to}` } }];
  });
  if (rows.length === 0) return null;
  return new ArcLayer<ArcRow>({
    id: 'geo-highlight',
    data: rows,
    pickable: false,
    getSourcePosition: (d) => toLngLat(d.source),
    getTargetPosition: (d) => toLngLat(d.target),
    getSourceColor: (d) => d.color,
    getTargetColor: (d) => d.color,
    getWidth: (d) => d.width,
    getTilt: () => ARC_TILT_DEG,
    getHeight: () => ARC_HEIGHT,
  });
}

export function buildLayers(
  flows: GeoFlows | null,
  reference: GeoReference | null,
  visible: ReadonlySet<LayerId>,
  selection: GeoSelection,
  handlers: LayerHandlers = {},
  highlight: readonly HighlightArc[] = [],
): Layer[] {
  const layers: Layer[] = [];
  if (reference && visible.has('risk')) layers.push(riskAreaLayer(reference, selection, handlers));
  if (reference && visible.has('offshore')) layers.push(offshoreLayer(reference, handlers));
  if (flows && reference && visible.has('corridors')) {
    layers.push(arcLayer('geo-corridors', corridorRows(flows, reference, selection), handlers));
  }
  if (flows && reference && visible.has('mismatches')) {
    layers.push(arcLayer('geo-mismatches', mismatchRows(flows, reference, selection), handlers));
  }
  const picked = reference ? highlightLayer(highlight, reference) : null;
  if (picked) layers.push(picked);
  return layers;
}
