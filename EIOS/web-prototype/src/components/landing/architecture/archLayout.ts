import { GROUPS, NODES, type ArchNode, type GroupId } from "../data/architecture";

export const VIEW = { w: 1240, h: 940 } as const;
export const CHIP = { w: 170, h: 32, gapX: 10, gapY: 8 } as const;

export interface Slab {
  readonly id: GroupId;
  readonly cx: number;
  readonly cy: number;
  readonly hw: number;
  readonly hh: number;
}

const COLS = [220, 620, 1020] as const;

/** Platform rhombi: three on top, the ontology across the middle, three below, as in a layered systems drawing. */
export const SLABS: Readonly<Record<GroupId, Slab>> = {
  workstations: { id: "workstations", cx: COLS[0], cy: 214, hw: 196, hh: 54 },
  agents: { id: "agents", cx: COLS[1], cy: 214, hw: 196, hh: 54 },
  apis: { id: "apis", cx: COLS[2], cy: 214, hw: 196, hh: 54 },
  ontology: { id: "ontology", cx: 620, cy: 486, hw: 580, hh: 118 },
  data: { id: "data", cx: COLS[0], cy: 836, hw: 196, hh: 54 },
  logic: { id: "logic", cx: COLS[1], cy: 836, hw: 196, hh: 54 },
  action: { id: "action", cx: COLS[2], cy: 836, hw: 196, hh: 54 },
};

export const SLAB_EDGE = 10;

export function slabTop(s: Slab): string {
  return `M${s.cx} ${s.cy - s.hh}L${s.cx + s.hw} ${s.cy}L${s.cx} ${s.cy + s.hh}L${s.cx - s.hw} ${s.cy}Z`;
}

export function slabSide(s: Slab): string {
  const t = SLAB_EDGE;
  return `M${s.cx - s.hw} ${s.cy}L${s.cx - s.hw} ${s.cy + t}L${s.cx} ${s.cy + s.hh + t}L${s.cx + s.hw} ${s.cy + t}L${s.cx + s.hw} ${s.cy}M${s.cx} ${s.cy + s.hh}L${s.cx} ${s.cy + s.hh + t}`;
}

/** y of the slab's upper (sign -1) or lower (+1) boundary at x. */
export function edgeY(s: Slab, x: number, sign: -1 | 1): number {
  const k = Math.max(0, 1 - Math.abs(x - s.cx) / s.hw);
  return s.cy + sign * s.hh * k;
}

export interface Placed {
  readonly node: ArchNode;
  readonly x: number;
  readonly y: number;
}

/** Chips stand on their platform in a two-column grid; the ontology lays its five in one row across its face. */
function place(): Readonly<Record<string, Placed>> {
  const out: Record<string, Placed> = {};
  for (const g of GROUPS) {
    const s = SLABS[g.id];
    const nodes = NODES.filter((n) => n.group === g.id);
    if (g.tier === "mid") {
      const step = 194;
      nodes.forEach((node, i) => {
        out[node.id] = { node, x: s.cx + (i - (nodes.length - 1) / 2) * step, y: s.cy };
      });
      continue;
    }
    const rows = Math.ceil(nodes.length / 2);
    const gridH = rows * CHIP.h + (rows - 1) * CHIP.gapY;
    const baseY = s.cy - 14 - gridH;
    nodes.forEach((node, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = s.cx + (col === 0 ? -1 : 1) * (CHIP.w / 2 + CHIP.gapX / 2);
      const y = baseY + row * (CHIP.h + CHIP.gapY) + CHIP.h / 2;
      out[node.id] = { node, x, y };
    });
  }
  return out;
}

export const PLACED = place();

export interface Wire {
  readonly id: string;
  readonly group: GroupId;
  readonly d: string;
}

/** Fan of wires between each outer platform and the ontology's facing edge. */
function wires(): readonly Wire[] {
  const mid = SLABS.ontology;
  const out: Wire[] = [];
  for (const g of GROUPS) {
    if (g.tier === "mid") continue;
    const s = SLABS[g.id];
    const n = 7;
    for (let i = 0; i < n; i += 1) {
      const t = i / (n - 1) - 0.5;
      const ox = s.cx + t * 150;
      if (g.tier === "top") {
        const y0 = s.cy + s.hh * (1 - Math.abs(t) * 0.6) + SLAB_EDGE;
        const y1 = edgeY(mid, ox, -1);
        out.push({ id: `${g.id}-${i}`, group: g.id, d: `M${s.cx + t * 90} ${y0}C${s.cx + t * 90} ${(y0 + y1) / 2} ${ox} ${(y0 + y1) / 2} ${ox} ${y1}` });
      } else {
        const gridTop = Math.min(...NODES.filter((nd) => nd.group === g.id).map((nd) => PLACED[nd.id].y)) - CHIP.h / 2;
        const y1 = edgeY(mid, ox, 1) + SLAB_EDGE;
        out.push({ id: `${g.id}-${i}`, group: g.id, d: `M${s.cx + t * 120} ${gridTop - 4}C${s.cx + t * 120} ${(gridTop + y1) / 2} ${ox} ${(gridTop + y1) / 2} ${ox} ${y1}` });
      }
    }
  }
  return out;
}

export const WIRES = wires();

/** Where a hop leaves or enters a chip: the edge facing the other chip, so the path never crosses a label. */
function port(p: Placed, toward: Placed): [number, number] {
  const dx = toward.x - p.x;
  const dy = toward.y - p.y;
  if (Math.abs(dy) > CHIP.h * 1.5) return [p.x, p.y + Math.sign(dy) * (CHIP.h / 2 + 2)];
  return [p.x + Math.sign(dx || 1) * (CHIP.w / 2 + 2), p.y];
}

/** A curve between two chips for a traced path, edge to edge, bowing away from the straight line. */
export function hop(a: Placed, b: Placed): string {
  const [ax, ay] = port(a, b);
  const [bx, by] = port(b, a);
  const vertical = Math.abs(by - ay) > Math.abs(bx - ax);
  const c1 = vertical ? `${ax} ${(ay + by) / 2}` : `${(ax + bx) / 2} ${ay}`;
  const c2 = vertical ? `${bx} ${(ay + by) / 2}` : `${(ax + bx) / 2} ${by}`;
  return `M${ax} ${ay}C${c1} ${c2} ${bx} ${by}`;
}
