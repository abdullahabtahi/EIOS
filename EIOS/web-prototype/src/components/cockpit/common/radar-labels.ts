export interface LabelCandidate {
  readonly id: string;
  readonly cx: number;
  readonly cy: number;
  /** Which side of the node the label sits on. */
  readonly side: 'start' | 'end';
  /** Higher draws first and wins a collision. */
  readonly priority: number;
}

export interface Box {
  readonly x0: number;
  readonly y0: number;
  readonly x1: number;
  readonly y1: number;
}

const CHAR_WIDTH = 5.4;
const LABEL_HEIGHT = 11;
const LABEL_OFFSET = 10;
const NODE_RADIUS = 8;

const overlaps = (a: Box, b: Box): boolean => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;

function labelBox({ id, cx, cy, side }: LabelCandidate): Box {
  const width = id.length * CHAR_WIDTH;
  const x0 = side === 'end' ? cx - LABEL_OFFSET - width : cx + LABEL_OFFSET;
  return { x0, y0: cy - LABEL_HEIGHT / 2, x1: x0 + width, y1: cy + LABEL_HEIGHT / 2 };
}

const nodeBox = ({ cx, cy }: LabelCandidate): Box => ({
  x0: cx - NODE_RADIUS,
  y0: cy - NODE_RADIUS,
  x1: cx + NODE_RADIUS,
  y1: cy + NODE_RADIUS,
});

/**
 * Greedy label placement: highest priority first, a label is shown only when it does not
 * overlap an already placed label, a reserved area (axis captions) or a higher-priority node. Pinned ids (selected, hovered) always show.
 * Returns the set of ids whose label should be drawn.
 */
export function visibleLabelIds(
  candidates: readonly LabelCandidate[],
  pinned: ReadonlySet<string>,
  reserved: readonly Box[] = [],
): ReadonlySet<string> {
  const ordered = [...candidates].sort((a, b) => b.priority - a.priority);
  const placed: Box[] = [...reserved];
  const higher: Box[] = [];
  const shown = new Set<string>();

  for (const candidate of ordered) {
    const box = labelBox(candidate);
    const blockedByLabel = placed.some((other) => overlaps(box, other));
    const blockedByNode = higher.some((other) => overlaps(box, other));
    higher.push(nodeBox(candidate));
    if (pinned.has(candidate.id) || (!blockedByLabel && !blockedByNode)) {
      shown.add(candidate.id);
      placed.push(box);
    }
  }
  return shown;
}
