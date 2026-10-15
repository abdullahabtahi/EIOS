'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';

export type ResourceState<T> =
  | { status: 'loading' }
  | { status: 'error'; httpStatus: number; reload: () => void }
  | { status: 'ready'; data: T };

/** A JSON resource from the backend; an error says so (with its HTTP status), offers a retry, and the map then shows no marks from it. */
export function useGeoResource<T>(path: string): ResourceState<T> {
  const [state, setState] = React.useState<ResourceState<T>>({ status: 'loading' });
  const [attempt, setAttempt] = React.useState(0);
  const reload = React.useCallback(() => {
    setState({ status: 'loading' });
    setAttempt((n) => n + 1);
  }, []);

  React.useEffect(() => {
    let live = true;
    authFetch(path, { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!live) return;
        if (!res.ok) return setState({ status: 'error', httpStatus: res.status, reload });
        setState({ status: 'ready', data: (await res.json()) as T });
      })
      .catch(() => live && setState({ status: 'error', httpStatus: 0, reload }));
    return () => {
      live = false;
    };
  }, [path, attempt, reload]);

  return state;
}

export const dataOf = <T,>(state: ResourceState<T>): T | null => (state.status === 'ready' ? state.data : null);
