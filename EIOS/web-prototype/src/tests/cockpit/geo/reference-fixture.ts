import type { GeoReference, ReferenceCountry } from '@/components/cockpit/geo/geo-types';

const square = { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]] };
const country = (over: Partial<ReferenceCountry> & Pick<ReferenceCountry, 'iso2' | 'name'>): ReferenceCountry => ({
  boundary: square,
  position: [0.5, 0.5],
  fatf_list: null,
  entities_incorporated: null,
  entities_linked: null,
  indicators: [],
  ...over,
});

/** A tiny stand-in for the real reference payload; shapes match the backend contract. */
export const REFERENCE: GeoReference = {
  countries: [
    country({ iso2: 'BS', name: 'The Bahamas', position: [-76.5, 24.2], entities_incorporated: 209713, entities_linked: 22936,
      indicators: [{ code: 'NY.GDP.PCAP.CD', name: 'GDP per capita (current US$)', year: 2020, value: 25194 }] }),
    country({ iso2: 'PA', name: 'Panama', position: [-80.1, 8.5], entities_incorporated: 48692, entities_linked: 18345 }),
    country({ iso2: 'IR', name: 'Iran', position: [53.7, 32.4], fatf_list: 'call_for_action' }),
    country({ iso2: 'KE', name: 'Kenya', position: [37.9, 0.2], fatf_list: 'increased_monitoring', entities_incorporated: 120 }),
    country({ iso2: 'NO', name: 'Norway', position: [9, 61] }),
  ],
  sources: {
    boundaries: { source: 'Overture Maps division_area', as_of: '2026-09-23' },
    fatf: { source: 'FATF plenary statement, June 2026 (secondary summary)', as_of: '2026-06-19' },
    offshore_precedent: { source: 'ICIJ Offshore Leaks Database (entities)', as_of: '2026-09-09' },
    indicators: { source: 'World Bank WDI (latest year per country)', as_of: null },
  },
};
