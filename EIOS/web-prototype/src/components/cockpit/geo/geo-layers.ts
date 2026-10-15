import { ArcLayer, GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type {
  Corridor,
  GeoEvidence,
  GeoReference,
  GeoSelection,
  LayerId,
  LngLat,
  Mismatch,
  ReferenceCountry,
  RiskTier,
} from './geo-types';

type Rgba = [number, number, number, number];

export const TIER_COLOR: Readonly<Record<RiskTier, Rgba>> = {
  low: [34, 139, 94, 200],
  medium: [217, 150, 20, 210],
  high: [200, 50, 50, 220],
};
const MISMATCH_COLOR: Rgba = [57, 75, 89, 230];
const OFFSHORE_COLOR: Rgba = [16, 107, 163, 170];
const SELECTED_COLOR: Rgba = [17, 17, 17, 255];
const OUTLINE_COLOR: Rgba = [120, 134, 148, 90];
const NO_FILL: Rgba = [0, 0, 0, 0];

/** [ASSUMPTION] below this many incorporated entities a country is not drawn as an offshore centre (keeps the map readable). */
export const MIN_OFFSHORE_ENTITIES = 500;
const AREA_FILL_ALPHA = 70;
// Arcs lift out of the map plane; on a flat (untilted) map that is invisible, so lay the arc in the plane to read as a curve.
const ARC_TILT_DEG = 90;
const ARC_HEIGHT = 0.2;

export interface LayerHandlers {
  readonly onHover?: (selection: GeoSelection) => void;
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
const widthFor = (volumeUsd: number, scale: number): number => Math.max(1.5, Math.sqrt(volumeUsd) / scale);
const countryRef = (c: ReferenceCountry): NonNullable<GeoSelection> => ({ kind: 'country', id: c.iso2 });

/** FATF list to risk tier; an unlisted country is unrated (null), not low. */
export function tierOf(country: ReferenceCountry): RiskTier | null {
  if (country.fatf_list === 'call_for_action') return 'high';
  if (country.fatf_list === 'increased_monitoring') return 'medium';
  return null;
}

function positions(evidence: GeoEvidence): ReadonlyMap<string, LngLat> {
  return new Map(evidence.jurisdictions.map((j) => [j.code, j.position]));
}

function corridorRows(evidence: GeoEvidence, selection: GeoSelection): readonly ArcRow[] {
  const at = positions(evidence);
  return evidence.corridors.flatMap((c: Corridor) => {
    const source = at.get(c.origin);
    const target = at.get(c.destination);
    if (!source || !target) return [];
    const picked = selection?.kind === 'corridor' && selection.id === c.id;
    return [{ source, target, width: widthFor(c.volumeUsd, 220), color: picked ? SELECTED_COLOR : TIER_COLOR[c.riskTier], ref: { kind: 'corridor', id: c.id } as const }];
  });
}

function mismatchRows(evidence: GeoEvidence, selection: GeoSelection): readonly ArcRow[] {
  const at = positions(evidence);
  return evidence.mismatches.flatMap((m: Mismatch) => {
    const source = at.get(m.kycCountry);
    const target = at.get(m.ipCountry);
    if (!source || !target) return [];
    const picked = selection?.kind === 'mismatch' && selection.id === m.accountId;
    return [{ source, target, width: widthFor(m.volumeUsd, 160), color: picked ? SELECTED_COLOR : MISMATCH_COLOR, ref: { kind: 'mismatch', id: m.accountId } as const }];
  });
}

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
    onHover: (info) => handlers.onHover?.(info.object ? (info.object as ArcRow).ref : null),
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
    onHover: (info) => handlers.onHover?.(info.object ? countryRef((info.object as unknown as AreaFeature).properties.country) : null),
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
    onHover: (info) => handlers.onHover?.(info.object ? countryRef(info.object as ReferenceCountry) : null),
    onClick: (info) => handlers.onSelect?.(info.object ? countryRef(info.object as ReferenceCountry) : null),
  });
}

/**
 * Pure: evidence plus view state in, deck.gl layers out. The model never writes layer specs (RL-1). The reference
 * lenses (FATF areas, offshore centres) draw only when the reference layer is present; without it they are absent.
 */
export function buildLayers(
  evidence: GeoEvidence,
  reference: GeoReference | null,
  visible: ReadonlySet<LayerId>,
  selection: GeoSelection,
  handlers: LayerHandlers = {},
): Layer[] {
  const layers: Layer[] = [];
  if (reference && visible.has('risk')) layers.push(riskAreaLayer(reference, selection, handlers));
  if (reference && visible.has('offshore')) layers.push(offshoreLayer(reference, handlers));
  if (visible.has('corridors')) layers.push(arcLayer('geo-corridors', corridorRows(evidence, selection), handlers));
  if (visible.has('mismatches')) layers.push(arcLayer('geo-mismatches', mismatchRows(evidence, selection), handlers));
  return layers;
}
