import type { GeoSelection } from './geo-types';
import { DEFAULT_BASIS, isBasis, type BasisId } from './geo-basis';
import { VIEWS, type ViewId } from './geo-views';

/** What the address bar holds, so a view and a pick can be shared, bookmarked, cited in a SAR or opened by the copilot. */
export interface GeoUrlState {
  readonly view: ViewId | null;
  readonly selection: GeoSelection;
  /** Which list colours the Jurisdictions map; null when the address does not say. */
  readonly basis: BasisId | null;
}

const KINDS = new Set(['country', 'corridor', 'mismatch', 'gateway', 'account']);
// A selection id is a country code, an `A>B` pair, a gateway id or an account id; nothing else is accepted from a URL.
const ID = /^[A-Za-z0-9>_-]{1,64}$/;

export function parseGeoUrl(search: string): GeoUrlState {
  const params = new URLSearchParams(search);
  const rawView = params.get('view');
  const view = VIEWS.some((v) => v.id === rawView) ? (rawView as ViewId) : null;
  const raw = params.get('sel');
  const rawBasis = params.get('basis');
  const basis = isBasis(rawBasis) ? rawBasis : null;
  if (!raw) return { view, selection: null, basis };
  const cut = raw.indexOf(':');
  const kind = raw.slice(0, cut);
  const id = raw.slice(cut + 1);
  if (cut < 1 || !KINDS.has(kind) || !ID.test(id)) return { view, selection: null, basis };
  return { view, selection: { kind, id } as NonNullable<GeoSelection>, basis };
}

/** The query string for a state; other parameters already in the URL are kept. */
export function formatGeoUrl(current: string, view: ViewId, selection: GeoSelection, basis: BasisId = DEFAULT_BASIS): string {
  const params = new URLSearchParams(current);
  params.set('view', view);
  if (selection) params.set('sel', `${selection.kind}:${selection.id}`);
  else params.delete('sel');
  // The basis only means something on the Jurisdictions map, and the default is not worth a parameter.
  if (view === 'jurisdictions' && basis !== DEFAULT_BASIS) params.set('basis', basis);
  else params.delete('basis');
  const out = params.toString();
  return out ? `?${out}` : '';
}
