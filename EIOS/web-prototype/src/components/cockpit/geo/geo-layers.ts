import { GeoJsonLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers';
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
import { areaTier, DEFAULT_BASIS, type BasisId } from './geo-basis';
import { rgba, type Rgba } from './geo-colors';
import { curvePath, fadeAlong, wrapCopies } from './geo-curves';
import { type CorridorPair, hubsOf, pairUp } from './geo-pairs';
import { corridorId, pairId, shownCorridors, shownPairs } from './geo-rank';

/** Colour carries risk only: elevated tiers are red and amber; low and unrated corridors stay a quiet grey, never green. */
export const TIER_COLOR: Readonly<Record<RiskTier, Rgba>> = {
  low: rgba('cx-faint', 120),
  medium: rgba('cx-warn', 210),
  high: rgba('cx-bad', 220),
};
/** Selection is the accent, as everywhere in the cockpit; the data's own colours stay state and ink. */
const SELECTED_COLOR: Rgba = rgba('cx-accent', 255);
const MISMATCH_COLOR: Rgba = rgba('cx-ink', 190);
const OFFSHORE_COLOR: Rgba = rgba('cx-muted', 150);
const UNRATED_COLOR: Rgba = rgba('cx-faint', 120);
const OUTLINE_COLOR: Rgba = rgba('cx-muted', 70);
const NO_FILL: Rgba = [0, 0, 0, 0];

/** [ASSUMPTION] below this many incorporated entities a country is not drawn as an offshore centre (keeps the map readable). */
export const MIN_OFFSHORE_ENTITIES = 500;
const AREA_FILL_ALPHA = 70;
/** [ASSUMPTION] a country that this many drawn routes meet is drawn as a hub node. */
export const HUB_MIN_SPOKES = 4;
/** Share of a route's opacity kept when a pick puts something else in focus. */
const DIM = 0.28;
const HUB_BASE_RADIUS = 9;
const HUB_RADIUS_PER_SPOKE = 2.5;
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

/** One route on the map: a curved path with a colour per vertex (faint at the origin, full at the destination). */
interface PathRow {
  readonly path: readonly [number, number][];
  readonly colors: readonly Rgba[];
  readonly width: number;
  readonly ref: NonNullable<GeoSelection>;
}

interface HubRow {
  readonly iso2: string;
  readonly position: LngLat;
  readonly spokes: number;
  readonly tier: RiskTier | null;
}

/** A route as the path rows that draw it: the curve, and its copy one world over when it crosses the map's edge. */
function routeRows(source: LngLat, target: LngLat, color: Rgba, width: number, ref: NonNullable<GeoSelection>): readonly PathRow[] {
  const path = curvePath(source, target);
  return wrapCopies(path).map((p) => ({ path: p as [number, number][], colors: fadeAlong(color, p.length), width, ref }));
}

const dimmed = (color: Rgba): Rgba => [color[0], color[1], color[2], Math.round(color[3] * DIM)];

const toLngLat = (p: LngLat): [number, number] => [p[0], p[1]];
const MIN_ARC_WIDTH = 1.5;
const ARC_WIDTH_RANGE = 3.5;
const SELECTED_EXTRA_WIDTH = 1.5;
/** Arc width grows with the square root of the value relative to the largest, so every dataset reads the same. */
const widthFor = (value: number, max: number): number =>
  MIN_ARC_WIDTH + ARC_WIDTH_RANGE * Math.sqrt(max > 0 ? value / max : 0);
const countryRef = (c: ReferenceCountry): NonNullable<GeoSelection> => ({ kind: 'country', id: c.iso2 });

function positions(reference: GeoReference): ReadonlyMap<string, LngLat> {
  return new Map(reference.countries.map((c) => [c.iso2, c.position]));
}

/** Which routes the pick puts in focus: a country keeps the routes that touch it, a corridor keeps its own pair; any other pick keeps all. */
function inFocus(pair: CorridorPair, selection: GeoSelection): boolean {
  if (selection?.kind === 'country') {
    return [pair.lead.origin, pair.lead.destination].includes(selection.id);
  }
  if (selection?.kind === 'corridor') {
    return [pair.lead, pair.back].some((c) => c !== null && corridorId(c) === selection.id);
  }
  return true;
}

const isPickedPair = (pair: CorridorPair, selection: GeoSelection): boolean =>
  selection?.kind === 'corridor' && [pair.lead, pair.back].some((c) => c !== null && corridorId(c) === selection.id);

/** The drawn corridors folded into routes: the two directions of a pair are one line, and a corridor picked from the list is always among them. */
function corridorPairs(flows: GeoFlows, selection: GeoSelection): readonly CorridorPair[] {
  const drawn = shownCorridors(flows);
  const picked = selection?.kind === 'corridor' ? flows.corridors.find((c) => corridorId(c) === selection.id) : undefined;
  const rows = picked && !drawn.includes(picked) ? [...drawn, picked] : drawn;
  return pairUp(rows, flows.corridors);
}

function corridorRows(flows: GeoFlows, reference: GeoReference, selection: GeoSelection): readonly PathRow[] {
  const at = positions(reference);
  const pairs = corridorPairs(flows, selection);
  const max = Math.max(0, ...pairs.map((p) => p.gross));
  return pairs.flatMap((pair) => {
    const source = at.get(pair.lead.origin);
    const target = at.get(pair.lead.destination);
    if (!source || !target) return [];
    const picked = isPickedPair(pair, selection);
    const base = picked ? SELECTED_COLOR : pair.tier ? TIER_COLOR[pair.tier] : UNRATED_COLOR;
    const color = inFocus(pair, selection) ? base : dimmed(base);
    const width = widthFor(pair.gross, max) + (picked ? SELECTED_EXTRA_WIDTH : 0);
    return routeRows(source, target, color, width, { kind: 'corridor', id: corridorId(pair.lead) });
  });
}

/** Where drawn routes converge: one ring for the country, sized by how many routes meet there. */
function hubRows(flows: GeoFlows, reference: GeoReference, selection: GeoSelection): readonly HubRow[] {
  const at = positions(reference);
  const placed = corridorPairs(flows, selection).filter((p) => at.has(p.lead.origin) && at.has(p.lead.destination));
  return hubsOf(placed, HUB_MIN_SPOKES).flatMap((h) => {
    const position = at.get(h.iso2);
    return position ? [{ ...h, position }] : [];
  });
}

function mismatchRows(flows: GeoFlows, reference: GeoReference, selection: GeoSelection): readonly PathRow[] {
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
    return routeRows(source, target, isPicked ? SELECTED_COLOR : MISMATCH_COLOR, width, { kind: 'mismatch', id: pairId(p) });
  });
}

const point = (info: { x: number; y: number }): HoverPoint => ({ x: info.x, y: info.y });

function pathLayer(id: string, rows: readonly PathRow[], handlers: LayerHandlers): PathLayer<PathRow> {
  return new PathLayer<PathRow>({
    id,
    data: rows as PathRow[],
    pickable: true,
    getPath: (d) => d.path as [number, number][],
    getColor: (d) => d.colors as Rgba[],
    getWidth: (d) => d.width,
    widthUnits: 'pixels',
    capRounded: true,
    jointRounded: true,
    autoHighlight: false,
    onHover: (info) => handlers.onHover?.(info.object ? (info.object as PathRow).ref : null, point(info)),
    onClick: (info) => handlers.onSelect?.(info.object ? (info.object as PathRow).ref : null),
  });
}

function hubLayer(hubs: readonly HubRow[], handlers: LayerHandlers): ScatterplotLayer<HubRow> {
  return new ScatterplotLayer<HubRow>({
    id: 'geo-hubs',
    data: hubs as HubRow[],
    pickable: true,
    stroked: true,
    filled: false,
    radiusUnits: 'pixels',
    lineWidthUnits: 'pixels',
    getPosition: (h) => toLngLat(h.position),
    getRadius: (h) => HUB_BASE_RADIUS + HUB_RADIUS_PER_SPOKE * h.spokes,
    getLineWidth: 2,
    getLineColor: (h) => (h.tier === 'high' ? TIER_COLOR.high : h.tier === 'medium' ? TIER_COLOR.medium : rgba('cx-muted', 200)),
    onHover: (info) => handlers.onHover?.(info.object ? { kind: 'country', id: (info.object as HubRow).iso2 } : null, point(info)),
    onClick: (info) => handlers.onSelect?.(info.object ? { kind: 'country', id: (info.object as HubRow).iso2 } : null),
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

function riskAreaLayer(
  reference: GeoReference,
  selection: GeoSelection,
  handlers: LayerHandlers,
  basis: BasisId,
  override: ReadonlyMap<string, RiskTier | null> | null,
): GeoJsonLayer<AreaFeature['properties']> {
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
      const country = (f as unknown as AreaFeature).properties.country;
      const tier = override?.has(country.iso2) ? (override.get(country.iso2) ?? null) : areaTier(country, basis);
      if (!tier) return NO_FILL;
      const [r, g, b] = TIER_COLOR[tier];
      return [r, g, b, AREA_FILL_ALPHA];
    },
    getLineColor: (f) => (picked((f as unknown as AreaFeature).properties.country) ? SELECTED_COLOR : OUTLINE_COLOR),
    getLineWidth: (f) => (picked((f as unknown as AreaFeature).properties.country) ? 3 : 1),
    updateTriggers: { getFillColor: [basis, override], getLineColor: [selection?.kind, selection?.id], getLineWidth: [selection?.kind, selection?.id] },
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
function highlightLayer(arcs: readonly HighlightArc[], reference: GeoReference): PathLayer<PathRow> | null {
  const at = positions(reference);
  const max = Math.max(0, ...arcs.map((a) => a.weight));
  const rows = arcs.flatMap((a): readonly PathRow[] => {
    const source = at.get(a.from);
    const target = at.get(a.to);
    if (!source || !target || a.from === a.to) return [];
    return routeRows(source, target, SELECTED_COLOR, widthFor(a.weight, max) + SELECTED_EXTRA_WIDTH, { kind: 'mismatch', id: `${a.from}>${a.to}` });
  });
  if (rows.length === 0) return null;
  return new PathLayer<PathRow>({
    id: 'geo-highlight',
    data: rows,
    pickable: false,
    getPath: (d) => d.path as [number, number][],
    getColor: (d) => d.colors as Rgba[],
    getWidth: (d) => d.width,
    widthUnits: 'pixels',
    capRounded: true,
    jointRounded: true,
  });
}

/** Countries a list change names: added ones outlined red, removed ones outlined blue (the activity there continues). */
export interface ListChangeMarks {
  readonly added: ReadonlySet<string>;
  readonly removed: ReadonlySet<string>;
}
const ADDED_COLOR: Rgba = rgba('cx-bad', 255);
const REMOVED_COLOR: Rgba = rgba('cx-accent', 255);

function listChangeLayer(reference: GeoReference, marks: ListChangeMarks): GeoJsonLayer<AreaFeature['properties']> | null {
  const changed = areaFeatures(reference).filter(
    (f) => marks.added.has(f.properties.country.iso2) || marks.removed.has(f.properties.country.iso2),
  );
  if (changed.length === 0) return null;
  const isAdded = (f: unknown) => marks.added.has((f as AreaFeature).properties.country.iso2);
  return new GeoJsonLayer<AreaFeature['properties']>({
    id: 'geo-list-change',
    data: changed as never,
    pickable: false,
    stroked: true,
    filled: false,
    lineWidthUnits: 'pixels',
    getLineColor: (f) => (isAdded(f) ? ADDED_COLOR : REMOVED_COLOR),
    getLineWidth: (f) => (isAdded(f) ? 3 : 2.5),
  });
}

export function buildLayers(
  flows: GeoFlows | null,
  reference: GeoReference | null,
  visible: ReadonlySet<LayerId>,
  selection: GeoSelection,
  handlers: LayerHandlers = {},
  highlight: readonly HighlightArc[] = [],
  basis: BasisId = DEFAULT_BASIS,
  listChange: ListChangeMarks | null = null,
  /** Tiers that replace the list's own for named countries: the earlier edition, while a comparison shows "Before". */
  tierOverride: ReadonlyMap<string, RiskTier | null> | null = null,
): Layer[] {
  const layers: Layer[] = [];
  const outlined = reference && listChange ? listChangeLayer(reference, listChange) : null;
  if (reference && visible.has('risk')) layers.push(riskAreaLayer(reference, selection, handlers, basis, tierOverride));
  if (reference && visible.has('offshore')) layers.push(offshoreLayer(reference, handlers));
  if (flows && reference && visible.has('corridors')) {
    layers.push(pathLayer('geo-corridors', corridorRows(flows, reference, selection), handlers));
    const hubs = hubRows(flows, reference, selection);
    if (hubs.length > 0) layers.push(hubLayer(hubs, handlers));
  }
  if (flows && reference && visible.has('mismatches')) {
    layers.push(pathLayer('geo-mismatches', mismatchRows(flows, reference, selection), handlers));
  }
  if (outlined) layers.push(outlined);
  const picked = reference ? highlightLayer(highlight, reference) : null;
  if (picked) layers.push(picked);
  return layers;
}
