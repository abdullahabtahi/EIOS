import type { PersonaRole, WorkstationApiResponse } from './cockpit-types';

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
): Promise<WorkstationResult> {
  const res = await fetcher(`/api/cockpit/workstations/${role}${patient ? '?patient=1' : ''}`, {
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
