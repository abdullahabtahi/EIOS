/**
 * Top-level sections of the EIOS global navigation rail.
 * `workstations` is the live tripartite cockpit (its personas are switched from
 * the header strip, so the rail lists it once). The others are planned modules
 * whose pages are not built yet and render as disabled entries flagged SOON.
 */

export type AppNavId = 'workstations' | 'geospatial' | 'openbb';

export interface AppNavItem {
  readonly id: AppNavId;
  readonly label: string;
  readonly icon: string;
  readonly description: string;
  readonly available: boolean;
}

export const APP_NAV_ITEMS: readonly AppNavItem[] = [
  {
    id: 'workstations',
    label: 'Workstations',
    icon: 'dashboard',
    description: 'Role-based analytics',
    available: true,
  },
  {
    id: 'geospatial',
    label: 'Geospatial',
    icon: 'map',
    description: 'Maps & AI analytics',
    available: false,
  },
  {
    id: 'openbb',
    label: 'OpenBB',
    icon: 'candlestick_chart',
    description: 'Market data feeds',
    available: false,
  },
];

/** The section whose view the shell currently renders. */
export const CURRENT_APP_NAV_ID: AppNavId = 'workstations';
