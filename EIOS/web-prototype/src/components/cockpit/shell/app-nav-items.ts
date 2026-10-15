/**
 * Top-level sections of the EIOS global navigation rail.
 * `workstations` is the live tripartite cockpit (its personas are switched from
 * the header strip, so the rail lists it once). `geospatial` is its own route. The rest
 * are planned modules whose pages are not built yet and render as disabled entries flagged SOON.
 */

export type AppNavId = 'workstations' | 'geospatial' | 'openbb';

export interface AppNavItem {
  readonly id: AppNavId;
  readonly label: string;
  readonly icon: string;
  readonly description: string;
  readonly available: boolean;
  /** Route of the section's page; absent for planned sections. */
  readonly href?: string;
}

export const APP_NAV_ITEMS: readonly AppNavItem[] = [
  {
    id: 'workstations',
    label: 'Workstations',
    icon: 'dashboard',
    description: 'Role-based analytics',
    available: true,
    href: '/cockpit',
  },
  {
    id: 'geospatial',
    label: 'Geospatial',
    icon: 'map',
    description: 'Maps & AI analytics',
    available: true,
    href: '/cockpit/geospatial',
  },
  {
    id: 'openbb',
    label: 'OpenBB',
    icon: 'candlestick_chart',
    description: 'Market data feeds',
    available: false,
  },
];

/** The section rendered when a shell does not name one (the workstations cockpit). */
export const DEFAULT_APP_NAV_ID: AppNavId = 'workstations';
