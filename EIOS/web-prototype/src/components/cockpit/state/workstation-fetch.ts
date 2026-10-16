import type { ActionIntentCard, PersonaRole, WorkstationApiResponse } from './cockpit-types';

/** How fresh the workstation in view is. `fresh` is the last answer; the rest are in-between states. */
export type WorkstationFreshness = 'fresh' | 'revalidating' | 'slow' | 'stale';

/** Past this, a request still in flight is reported as "taking longer" rather than silently spinning. */
export const SLOW_AFTER_MS = 3000;

export type WorkstationResult =
  /** The backend answered live. */
  | { kind: 'live'; data: WorkstationApiResponse }
  /** The operator's token was refused: never masked by cached data or a replay. */
  | { kind: 'denied' }
  /** The backend did not answer in time, twice. The caller decides between stale data and a labelled replay. */
  | { kind: 'unavailable'; retryable?: boolean };

/** Every workstation, in the order a prefetch warms them. */
export const ALL_ROLES: readonly PersonaRole[] = [
  'executive',
  'aml_investigator',
  'partner_manager',
  'compliance_auditor',
  'data_operations',
];

/** A cached workstation younger than this is shown without refetching its panels; the shelf is always refetched. */
export const PANEL_TTL_MS = 30_000;

/** Wait this long after the visible workstation is live before warming the others, so it never competes with it. */
export const PREFETCH_DELAY_MS = 1000;

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface LoadOptions {
  fetcher: Fetcher;
  signal: AbortSignal;
  /** Called once if the first attempt is still running after SLOW_AFTER_MS. */
  onSlow?: () => void;
}

async function attempt(
  fetcher: Fetcher,
  role: PersonaRole,
  signal: AbortSignal,
  patient: boolean,
  withShelf = true,
): Promise<WorkstationResult> {
  const query = new URLSearchParams({ ...(patient ? { patient: '1' } : {}), ...(withShelf ? {} : { shelf: '0' }) }).toString();
  const res = await fetcher(`/api/cockpit/workstations/${role}${query ? `?${query}` : ''}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  });
  if (res.status === 401 || res.status === 403) return { kind: 'denied' };
  // Another 4xx is the same on a second try: report it without the long retry.
  if (res.status >= 400 && res.status < 500) return { kind: 'unavailable', retryable: false };
  if (!res.ok) return { kind: 'unavailable' };
  const data: WorkstationApiResponse = await res.json();
  // The proxy answers 200 with a labelled replay when the backend timed out; that is not a live answer.
  return data.isLiveConnected && !data.isCachedFallback ? { kind: 'live', data } : { kind: 'unavailable' };
}

/**
 * Warm the cache for the workstations the operator is not looking at: one at a time, one attempt each, no retry,
 * and silent on failure (the real load runs when they switch). Stops when the signal aborts.
 */
export async function prefetchWorkstations(
  roles: readonly PersonaRole[],
  options: { fetcher: Fetcher; signal: AbortSignal; onLive: (role: PersonaRole, data: WorkstationApiResponse) => void },
): Promise<void> {
  for (const role of roles) {
    if (options.signal.aborted) return;
    try {
      const result = await attempt(options.fetcher, role, options.signal, false, false);
      if (result.kind === 'denied') return;
      if (result.kind === 'live' && !options.signal.aborted) options.onLive(role, result.data);
    } catch {
      // A failed prefetch costs nothing: the switch fetches normally.
    }
  }
}

/**
 * Load one workstation: a normal attempt, then one retry with the proxy's longer budget.
 * An abort rejects (the caller treats it as superseded); everything else resolves to a result.
 */
export async function loadWorkstation(role: PersonaRole, options: LoadOptions): Promise<WorkstationResult> {
  const { fetcher, signal, onSlow } = options;
  const slowTimer = onSlow ? setTimeout(onSlow, SLOW_AFTER_MS) : undefined;
  try {
    for (const patient of [false, true]) {
      try {
        const result = await attempt(fetcher, role, signal, patient);
        if (result.kind !== 'unavailable') return result;
        if (result.retryable === false) return { kind: 'unavailable' };
      } catch (err) {
        if (signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) throw err;
      }
    }
    return { kind: 'unavailable' };
  } finally {
    clearTimeout(slowTimer);
  }
}

export type ShelfResult =
  | { kind: 'live'; cards: ActionIntentCard[] }
  | { kind: 'denied' }
  | { kind: 'unavailable' };

/** The action shelf on its own (never cached). One attempt: the panels in view stay; a failure labels them stale. */
export async function loadShelf(fetcher: Fetcher, signal: AbortSignal): Promise<ShelfResult> {
  try {
    const res = await fetcher('/api/cockpit/shelf', { method: 'GET', headers: { Accept: 'application/json' }, signal });
    if (res.status === 401 || res.status === 403) return { kind: 'denied' };
    if (!res.ok) return { kind: 'unavailable' };
    const body: { stagedActionCards?: ActionIntentCard[] } = await res.json();
    return Array.isArray(body.stagedActionCards) ? { kind: 'live', cards: body.stagedActionCards } : { kind: 'unavailable' };
  } catch (err) {
    if (signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) throw err;
    return { kind: 'unavailable' };
  }
}
