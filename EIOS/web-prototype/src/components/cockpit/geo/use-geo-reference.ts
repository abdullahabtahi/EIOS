'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import type { GeoReference } from './geo-types';

export type ReferenceState =
  | { status: 'loading' }
  | { status: 'error'; httpStatus: number }
  | { status: 'ready'; reference: GeoReference };

/** The public reference layers from the backend; an error says so, and the map then shows no reference marks. */
export function useGeoReference(): ReferenceState {
  const [state, setState] = React.useState<ReferenceState>({ status: 'loading' });

  React.useEffect(() => {
    let live = true;
    authFetch('/api/cockpit/geo/reference', { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!live) return;
        if (!res.ok) return setState({ status: 'error', httpStatus: res.status });
        setState({ status: 'ready', reference: (await res.json()) as GeoReference });
      })
      .catch(() => live && setState({ status: 'error', httpStatus: 0 }));
    return () => {
      live = false;
    };
  }, []);

  return state;
}
