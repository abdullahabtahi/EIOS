import type { Layer } from "@deck.gl/core";
import type * as DeckLayers from "@deck.gl/layers";
import { CENTROIDS, CORRIDORS, GATEWAYS, type Corridor, type Gateway } from "../data/geo";
import type { RecordedTurn } from "../data/turns";

export type Lens = "corridors" | "exits" | "jurisdictions";
export type Basis = "fatf" | "eu" | "basel";
type RGBA = [number, number, number, number];

export interface CountryProps {
  readonly iso2: string;
  readonly name: string;
  readonly fatf: "increased_monitoring" | "call_for_action" | null;
  readonly eu: boolean;
  readonly basel: "lower" | "medium" | "higher" | null;
  readonly baselScore: number | null;
}

export interface CountryFeature {
  readonly type: "Feature";
  readonly properties: CountryProps;
  readonly geometry: unknown;
}

const INK: RGBA = [236, 235, 230, 255];
const SIG: RGBA = [157, 183, 207, 255];
const WARN: RGBA = [214, 161, 95, 255];
const alpha = (c: RGBA, a: number): RGBA => [c[0], c[1], c[2], a];

const TIER_COLOR: Record<Corridor[4], RGBA> = { low: alpha(INK, 90), medium: alpha(SIG, 210), high: alpha(WARN, 235) };

function basisFill(p: CountryProps, basis: Basis): RGBA {
  if (basis === "fatf") {
    if (p.fatf === "call_for_action") return alpha(WARN, 210);
    if (p.fatf === "increased_monitoring") return alpha(WARN, 105);
  } else if (basis === "eu") {
    if (p.eu) return alpha(SIG, 150);
  } else if (p.basel === "higher") return alpha(WARN, 150);
  else if (p.basel === "medium") return alpha(WARN, 55);
  else if (p.basel === "lower") return alpha(INK, 22);
  return alpha(INK, 10);
}

function focusSet(focus: RecordedTurn["focus"] | null): Set<string> {
  return new Set(focus?.ids ?? []);
}

function corridorKey(c: Corridor): string {
  return `${c[0]}>${c[1]}`;
}

export interface LayerInput {
  readonly L: typeof DeckLayers;
  readonly countries: readonly CountryFeature[];
  readonly lens: Lens;
  readonly basis: Basis;
  readonly focus: RecordedTurn["focus"] | null;
}

export function buildLayers({ L, countries, lens, basis, focus }: LayerInput): Layer[] {
  const f = focusSet(focus);
  const hasFocus = f.size > 0;
  const focusCountries = focus && (focus.kind === "country" || focus.kind === "countries") ? f : new Set<string>();
  const showCorridors = lens === "corridors" || focus?.kind === "corridor";
  const showExits = lens === "exits" || focus?.kind === "exit" || focus?.kind === "gateways";
  const maxVol = Math.max(...CORRIDORS.map((c) => c[2]));

  const layers: Layer[] = [
    new L.GeoJsonLayer<CountryProps>({
      id: "countries",
      data: countries as unknown as DeckLayers.GeoJsonLayerProps<CountryProps>["data"],
      stroked: true,
      filled: true,
      getFillColor: (d) => {
        const p = (d as unknown as CountryFeature).properties;
        if (focusCountries.has(p.iso2)) return alpha(SIG, 170);
        return lens === "jurisdictions" ? basisFill(p, basis) : alpha(INK, 10);
      },
      getLineColor: alpha(INK, 46),
      lineWidthMinPixels: 0.6,
      pickable: true,
      updateTriggers: { getFillColor: [lens, basis, [...focusCountries].join()] },
    }),
  ];

  if (showCorridors) {
    layers.push(
      new L.ArcLayer<Corridor>({
        id: "corridors",
        data: CORRIDORS as Corridor[],
        getSourcePosition: (c) => [...CENTROIDS[c[0]]] as [number, number],
        getTargetPosition: (c) => [...CENTROIDS[c[1]]] as [number, number],
        getSourceColor: (c) => (hasFocus && focus?.kind === "corridor" && !f.has(corridorKey(c)) ? alpha(INK, 18) : TIER_COLOR[c[4]]),
        getTargetColor: (c) => (hasFocus && focus?.kind === "corridor" && !f.has(corridorKey(c)) ? alpha(INK, 18) : TIER_COLOR[c[4]]),
        getWidth: (c) => 1 + Math.sqrt(c[2] / maxVol) * 6,
        getHeight: 0.35,
        widthUnits: "pixels",
        pickable: true,
        updateTriggers: { getSourceColor: [focus?.ids.join()], getTargetColor: [focus?.ids.join()] },
      }),
    );
  }

  if (showExits) {
    const homes = GATEWAYS.flatMap((g) => g.homes.map(([iso, n]) => ({ g, iso, n })));
    const lit = (g: Gateway) => !hasFocus || focus?.kind === "gateways" || f.has(g.id);
    layers.push(
      new L.ArcLayer<(typeof homes)[number]>({
        id: "exit-homes",
        data: homes,
        getSourcePosition: (h) => [...CENTROIDS[h.iso]] as [number, number],
        getTargetPosition: (h) => [...CENTROIDS[h.g.iso2]] as [number, number],
        getSourceColor: (h) => alpha(SIG, lit(h.g) ? 70 : 12),
        getTargetColor: (h) => alpha(SIG, lit(h.g) ? 230 : 20),
        getWidth: (h) => 0.8 + h.n * 0.5,
        getHeight: 0.5,
        widthUnits: "pixels",
        updateTriggers: { getSourceColor: [focus?.ids.join()], getTargetColor: [focus?.ids.join()] },
      }),
      new L.ScatterplotLayer<Gateway>({
        id: "exits",
        data: GATEWAYS as Gateway[],
        getPosition: (g) => [...CENTROIDS[g.iso2]] as [number, number],
        getRadius: (g) => 4 + g.accounts * 0.45,
        radiusUnits: "pixels",
        stroked: true,
        filled: true,
        getFillColor: (g) => alpha(WARN, lit(g) ? 220 : 40),
        getLineColor: alpha(INK, 200),
        lineWidthMinPixels: 1,
        pickable: true,
        updateTriggers: { getFillColor: [focus?.ids.join()] },
      }),
      new L.TextLayer<Gateway>({
        id: "exit-labels",
        data: (GATEWAYS as Gateway[]).filter(lit),
        getPosition: (g) => [...CENTROIDS[g.iso2]] as [number, number],
        getText: (g) => g.id,
        getSize: 11,
        getColor: alpha(INK, 230),
        getPixelOffset: [0, -18],
        fontFamily: "ui-monospace, monospace",
        characterSet: "auto",
        fontSettings: { sdf: true },
        outlineWidth: 4,
        outlineColor: [14, 17, 22, 255],
      }),
    );
  }

  if (focusCountries.size) {
    layers.push(
      new L.TextLayer<string>({
        id: "country-labels",
        data: [...focusCountries].filter((iso) => CENTROIDS[iso]),
        getPosition: (iso) => [...CENTROIDS[iso]] as [number, number],
        getText: (iso) => countries.find((c) => c.properties.iso2 === iso)?.properties.name ?? iso,
        getSize: 12,
        getColor: alpha(INK, 240),
        fontFamily: "system-ui, sans-serif",
        characterSet: "auto",
        fontSettings: { sdf: true },
        outlineWidth: 4,
        outlineColor: [14, 17, 22, 255],
      }),
    );
  }

  return layers;
}

/** Centre and zoom that frame the objects a recorded turn returned. */
export function viewFor(focus: RecordedTurn["focus"] | null): { longitude: number; latitude: number; zoom: number } {
  const home = { longitude: 24, latitude: 10, zoom: 1.3 };
  if (!focus || focus.kind === "none" || focus.ids.length === 0) return home;
  const points: Array<readonly [number, number]> = [];
  for (const id of focus.ids) {
    if (focus.kind === "corridor") {
      const [a, b] = id.split(">");
      points.push(CENTROIDS[a], CENTROIDS[b]);
    } else if (focus.kind === "exit" || focus.kind === "gateways") {
      const g = GATEWAYS.find((x) => x.id === id);
      if (g) {
        points.push(CENTROIDS[g.iso2]);
        if (focus.kind === "exit") g.homes.forEach(([iso]) => points.push(CENTROIDS[iso]));
      }
    } else if (CENTROIDS[id]) points.push(CENTROIDS[id]);
  }
  const xs = points.filter(Boolean).map((p) => p[0]);
  const ys = points.filter(Boolean).map((p) => p[1]);
  if (!xs.length) return home;
  const span = Math.max(Math.max(...xs) - Math.min(...xs), (Math.max(...ys) - Math.min(...ys)) * 1.6, 8);
  const zoom = Math.max(1.4, Math.min(4.2, Math.log2(360 / span) - 0.4));
  return { longitude: (Math.max(...xs) + Math.min(...xs)) / 2, latitude: (Math.max(...ys) + Math.min(...ys)) / 2, zoom };
}
