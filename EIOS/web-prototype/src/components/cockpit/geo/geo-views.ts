import type { LayerId } from './geo-types';

export type ViewId = 'corridors' | 'logins' | 'jurisdictions';

export interface GeoView {
  readonly id: ViewId;
  readonly label: string;
  /** The analyst's question this view answers; it is the panel's heading, so a first-time reader knows what they are looking at. */
  readonly question: string;
  /** The layers this view opens with. The analyst can still change them. */
  readonly layers: ReadonlySet<LayerId>;
}

export const VIEWS: readonly GeoView[] = [
  {
    id: 'corridors',
    label: 'Corridors',
    question: 'Where does money cross borders, and which routes touch high-risk jurisdictions?',
    layers: new Set<LayerId>(['risk', 'corridors']),
  },
  {
    id: 'logins',
    label: 'Login vs KYC',
    question: 'Which accounts log in from a different country than the one they registered in?',
    layers: new Set<LayerId>(['mismatches']),
  },
  {
    id: 'jurisdictions',
    label: 'Jurisdictions',
    question: 'Which countries do the published risk lists and scores flag, and where are offshore entities incorporated?',
    layers: new Set<LayerId>(['risk', 'offshore']),
  },
];

export const DEFAULT_VIEW: ViewId = 'corridors';

export const viewOf = (id: ViewId): GeoView => VIEWS.find((v) => v.id === id) ?? VIEWS[0];

export const LAYER_LABEL: Readonly<Record<LayerId, string>> = {
  risk: 'FATF-listed countries',
  offshore: 'Offshore entity centres',
  corridors: 'Payment corridors',
  mismatches: 'Login vs KYC country',
};
