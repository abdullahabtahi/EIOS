'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import type { GeoListChange, ListId } from './geo-types';
import type { ResourceState } from './use-geo-resource';

interface Settled {
  readonly key: string;
  readonly state: ResourceState<GeoListChange>;
}

/**
 * What a list's latest change does to the book, fetched only while a comparison is open (null when none is). Until
 * the answer for the current list arrives it reads as loading; an error says so with its HTTP status and offers a
 * retry, and the map then draws no change outlines.
 */
export function useListChange(listId: ListId | null): ResourceState<GeoListChange> | null {
  const [settled, setSettled] = React.useState<Settled | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const reload = React.useCallback(() => setAttempt((n) => n + 1), []);
  const key = listId ? `${listId}:${attempt}` : null;

  React.useEffect(() => {
    if (!key || !listId) return;
    let live = true;
    const settle = (state: ResourceState<GeoListChange>) => live && setSettled({ key, state });
    authFetch(`/api/cockpit/geo/list-changes?list_id=${listId}`, { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!res.ok) return settle({ status: 'error', httpStatus: res.status, reload });
        settle({ status: 'ready', data: (await res.json()) as GeoListChange });
      })
      .catch(() => settle({ status: 'error', httpStatus: 0, reload }));
    return () => {
      live = false;
    };
  }, [key, listId, reload]);

  if (!key) return null;
  return settled?.key === key ? settled.state : { status: 'loading' };
}
