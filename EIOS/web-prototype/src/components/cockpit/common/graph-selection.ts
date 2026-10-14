import type { DataOrigin, GraphNode } from '../state/cockpit-types';

/**
 * Whether selecting a graph node opens a case. With engine data only an account has a dossier; a device, a payment
 * method, a gateway or a collapsed ring is shown in the inspector but never requested from the backend as a case.
 * Other data origins keep the sample workstation's behaviour: every node opens.
 */
export function nodeOpensCase(node: Pick<GraphNode, 'details'>, origin: DataOrigin): boolean {
  return origin !== 'engine' || node.details?.type === 'client account';
}
