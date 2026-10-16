import type { ViewCommand } from '../state/cockpit-types';
import type { BasisId } from './geo-basis';
import type { GeoSelection } from './geo-types';
import type { ViewId } from './geo-views';

/** What the map shows: the state a move changes and Back restores. */
export interface MapState {
  readonly view: ViewId;
  readonly selected: GeoSelection;
  readonly basis: BasisId;
}

/** The view that shows a kind of object: an exit, a login pair or an account on Login vs KYC, a country on Jurisdictions. */
export function viewForKind(kind: ViewCommand['kind']): ViewId {
  if (kind === 'country') return 'jurisdictions';
  if (kind === 'corridor') return 'corridors';
  return 'logins';
}

/** The map state after the assistant's move: its view, its object selected, the colouring basis unchanged. */
export function stateAfterMove(current: MapState, move: ViewCommand): MapState {
  return { view: viewForKind(move.kind), selected: { kind: move.kind, id: move.id }, basis: current.basis };
}

/** The map context a question carries: what is in view and what is selected, in the backend's closed vocabulary. */
export interface MapContextPayload {
  readonly view: ViewId;
  readonly selection?: { readonly kind: NonNullable<GeoSelection>['kind']; readonly id: string };
  readonly basis?: BasisId;
}

export function mapContextOf(state: MapState): MapContextPayload {
  return {
    view: state.view,
    ...(state.selected ? { selection: { kind: state.selected.kind, id: state.selected.id } } : {}),
    ...(state.view === 'jurisdictions' ? { basis: state.basis } : {}),
  };
}

const KIND_WORD: Readonly<Record<ViewCommand['kind'], string>> = {
  country: 'country',
  corridor: 'corridor',
  mismatch: 'login-country pair',
  gateway: 'gateway',
  account: 'account',
};

/** A plain label for a move or a selection, used where no richer title is at hand. */
export function moveLabel(move: { readonly kind: ViewCommand['kind']; readonly id: string }): string {
  return `${KIND_WORD[move.kind]} ${move.id.replace('>', ' → ')}`;
}

/** The questions offered before the first turn: fixed templates, each answered by a tool the geospatial assistant has. */
export function geoSuggestions(selected: GeoSelection): string[] {
  const about =
    selected?.kind === 'gateway'
      ? ['Why is this exit suspicious, and who else is in its ring?']
      : selected?.kind === 'account'
        ? [`What does ${selected.id}'s geography show?`]
        : selected?.kind === 'corridor'
          ? ['How much money moves on this corridor, and through whom?']
          : selected?.kind === 'country'
            ? ['What is our exposure to this country, and where does it stand on the lists?']
            : ['Where should I look first?'];
  return [
    ...about,
    'What did the June FATF plenary change for our book?',
    'Since the EU took Nigeria off its high-risk list, what activity there continues?',
  ];
}
