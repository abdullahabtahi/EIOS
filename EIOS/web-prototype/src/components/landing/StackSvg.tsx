import React from "react";

/**
 * Exploded isometric stack of the five EIOS layers, bottom to top.
 * Every slab is a 2:1 rhombus; layer art is drawn in a [-1, 1] plane space and mapped onto it,
 * so strokes keep one weight (vector-effect) however the SVG is scaled.
 */

export const VIEW_W = 760;
export const VIEW_H = 840;
export const SLAB_CY = [700, 565, 430, 295, 160] as const;
export const SLAB_HALF_W = 230;
export const SLAB_HALF_H = 115;
const CX = VIEW_W / 2;

/** Plane (u, v) in [-1, 1] to screen. */
function plane(cy: number, u: number, v: number): [number, number] {
  return [CX + ((u - v) * SLAB_HALF_W) / 2, cy + ((u + v) * SLAB_HALF_H) / 2];
}

function planeTransform(cy: number): string {
  return `matrix(${SLAB_HALF_W / 2} ${SLAB_HALF_H / 2} ${-SLAB_HALF_W / 2} ${SLAB_HALF_H / 2} ${CX} ${cy})`;
}

function slabOutline(cy: number): string {
  return `M${CX} ${cy - SLAB_HALF_H} L${CX + SLAB_HALF_W} ${cy} L${CX} ${cy + SLAB_HALF_H} L${CX - SLAB_HALF_W} ${cy} Z`;
}

const SLAB_EDGE = 9;

/** Visible side faces of the slab: gives each layer thickness, as in the generated orbit frames. */
function slabEdge(cy: number): string {
  const t = SLAB_EDGE;
  return `M${CX - SLAB_HALF_W} ${cy}L${CX - SLAB_HALF_W} ${cy + t}L${CX} ${cy + SLAB_HALF_H + t}L${CX + SLAB_HALF_W} ${cy + t}L${CX + SLAB_HALF_W} ${cy}M${CX} ${cy + SLAB_HALF_H}L${CX} ${cy + SLAB_HALF_H + t}`;
}

/** Hairline from the slab's right vertex toward its legend numeral (the legend sits at LEADER_END). */
export const LEADER_END = VIEW_W * 0.86;

function cubePath(x: number, y: number, s: number): string {
  const k = 0.866 * s;
  return `M${x} ${y - s}L${x + k} ${y - s / 2}L${x + k} ${y + s / 2}L${x} ${y + s}L${x - k} ${y + s / 2}L${x - k} ${y - s / 2}ZM${x - k} ${y - s / 2}L${x} ${y}L${x + k} ${y - s / 2}M${x} ${y}L${x} ${y + s}`;
}

function cylinderPath(x: number, y: number, s: number): string {
  const rx = 0.78 * s;
  const ry = 0.38 * s;
  const h = 1.5 * s;
  return `M${x - rx} ${y - h}A${rx} ${ry} 0 1 0 ${x + rx} ${y - h}A${rx} ${ry} 0 1 0 ${x - rx} ${y - h}ZM${x - rx} ${y - h}L${x - rx} ${y}A${rx} ${ry} 0 0 0 ${x + rx} ${y}L${x + rx} ${y - h}`;
}

const WORLD_POINTS: ReadonlyArray<[number, number]> = [
  [-0.62, -0.5], [-0.2, -0.62], [0.28, -0.56], [0.66, -0.3],
  [-0.66, -0.06], [-0.22, -0.1], [0.24, -0.02], [0.62, 0.22],
  [-0.5, 0.42], [-0.06, 0.34], [0.38, 0.5], [0.0, 0.66],
];

function Worlds({ cy }: { cy: number }) {
  const objects = [...WORLD_POINTS]
    .map(([u, v], i) => ({ i, p: plane(cy, u, v) }))
    .sort((a, b) => a.p[1] - b.p[1]);
  return (
    <g className="fde-art">
      {objects.map(({ i, p: [x, y] }) =>
        i % 3 === 1 ? (
          <path key={i} d={cylinderPath(x, y + 4, 11)} className="fde-solid" />
        ) : (
          <path key={i} d={cubePath(x, y - 10, i % 3 === 0 ? 13 : 10)} className="fde-solid" />
        ),
      )}
    </g>
  );
}

function gridLines(count: number): string {
  const step = 2 / count;
  let d = "";
  for (let i = 0; i <= count; i += 1) {
    const t = -1 + i * step;
    d += `M${t} -1L${t} 1M-1 ${t}L1 ${t}`;
  }
  return d;
}

function Ingestion({ cy }: { cy: number }) {
  const cell = 2 / 14;
  return (
    <g transform={planeTransform(cy)} className="fde-art">
      <path d={gridLines(14)} className="fde-line fde-fine" />
      {[[3, 5], [4, 5], [4, 6], [5, 7], [6, 7], [6, 8], [7, 9], [8, 9]].map(([i, j]) => (
        <rect key={`${i}-${j}`} x={-1 + i * cell} y={-1 + j * cell} width={cell} height={cell} className="fde-fill-signal" />
      ))}
      <rect x={-1 + 10 * cell} y={-1 + 3 * cell} width={cell} height={cell} className="fde-line fde-dash" />
      <path d="M-1 0.12L1 0.12" className="fde-line fde-dash" />
    </g>
  );
}

const NODES: ReadonlyArray<[number, number]> = [
  [-0.7, -0.35], [-0.35, -0.7], [-0.4, 0.1], [0.05, -0.3], [0.1, 0.45],
  [0.5, -0.1], [0.62, 0.55], [-0.15, 0.7], [0.55, -0.62],
];
const EDGES: ReadonlyArray<[number, number]> = [
  [0, 1], [0, 2], [1, 3], [2, 3], [3, 4], [3, 5], [4, 6], [5, 6], [2, 7], [4, 7], [5, 8], [1, 8],
];

function Ontology({ cy }: { cy: number }) {
  return (
    <g transform={planeTransform(cy)} className="fde-art">
      {EDGES.map(([a, b]) => (
        <path
          key={`${a}-${b}`}
          d={`M${NODES[a][0]} ${NODES[a][1]}L${NODES[b][0]} ${NODES[b][1]}`}
          className="fde-line"
        />
      ))}
      {NODES.map(([u, v], i) => (
        <circle key={i} cx={u} cy={v} r={i === 3 ? 0.13 : 0.07} className={i === 3 ? "fde-hub" : "fde-node"} />
      ))}
    </g>
  );
}

function Assistant({ cy }: { cy: number }) {
  const rows = Array.from({ length: 9 }, (_, i) => -0.8 + i * 0.2);
  return (
    <g transform={planeTransform(cy)} className="fde-art">
      {rows.map((v, i) => (
        <g key={v}>
          <rect x={-0.85} y={v} width={0.5} height={0.1} className={i === 4 ? "fde-fill-signal" : "fde-line"} />
          <rect x={-0.28} y={v} width={0.4 + ((i * 7) % 5) * 0.08} height={0.1} className="fde-line" />
          <rect x={0.62} y={v} width={0.22} height={0.1} className={i === 4 ? "fde-fill-ink" : "fde-line"} />
        </g>
      ))}
    </g>
  );
}

function Workstations({ cy }: { cy: number }) {
  return (
    <g transform={planeTransform(cy)} className="fde-art">
      <rect x={-0.88} y={-0.82} width={0.5} height={1.64} className="fde-line" />
      <rect x={-0.3} y={-0.82} width={1.18} height={0.84} className="fde-line" />
      <rect x={-0.3} y={0.1} width={0.56} height={0.72} className="fde-line" />
      <rect x={0.34} y={0.1} width={0.54} height={0.72} className="fde-line" />
      <path d="M-0.22 -0.2L-0.05 -0.5L0.18 -0.28L0.4 -0.62L0.62 -0.4L0.8 -0.7" className="fde-line fde-signal" />
      {[-0.66, -0.46, -0.26, -0.06].map((v) => (
        <path key={v} d={`M-0.8 ${v}L-0.46 ${v}`} className="fde-line fde-fine" />
      ))}
    </g>
  );
}

const ART = [Worlds, Ingestion, Ontology, Assistant, Workstations] as const;

export interface StackSvgProps {
  readonly active: number | null;
}

export function StackSvg({ active }: StackSvgProps) {
  return (
    <svg
      className="fde-stack-svg"
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      role="img"
      aria-label="Exploded isometric diagram of the five EIOS layers, from synthetic worlds at the bottom to the operator workstations at the top, with a signal rising through them."
      data-active={active ?? undefined}
    >
      {SLAB_CY.map((cy, k) => {
        const Art = ART[k];
        return (
          <g
            key={cy}
            className={`fde-layer${active === k ? " is-active" : ""}`}
            style={{ "--i": k } as React.CSSProperties}
          >
            <path d={slabEdge(cy)} className="fde-edge" />
            <path d={slabOutline(cy)} className="fde-slab" pathLength={1} />
            <path
              d={`M${CX + SLAB_HALF_W + 8} ${cy}L${LEADER_END} ${cy}`}
              className="fde-leader"
              aria-hidden="true"
            />
            <Art cy={cy} />
          </g>
        );
      })}
      <g className="fde-arrow" aria-hidden="true">
        <path d="M118 705C14 600 14 280 118 172" className="fde-arrow-line" pathLength={1} />
        <path d="M118 172L103 177.6M118 172L114.2 187.6" className="fde-arrow-head" />
        <path d="M118 705C14 600 14 280 118 172" className="fde-arrow-run" pathLength={1} />
      </g>
    </svg>
  );
}
