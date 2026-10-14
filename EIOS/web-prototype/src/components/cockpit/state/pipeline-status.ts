/**
 * Derives the operator-facing pipeline status from real connection state.
 * Constitution Principle III / VIII: the UI must never claim "live" or "synced"
 * unless the current data actually arrived live.
 */

export type PipelineTone = 'ok' | 'warn' | 'bad' | 'neutral';

/** Whether the state in view came from governed data products or from in-process fixtures. */
export type DataOrigin = 'live' | 'engine' | 'fixture';

export interface PipelineStatus {
  readonly label: 'Live' | 'Engine' | 'Fixture' | 'Replay' | 'Syncing' | 'Offline';
  readonly tone: PipelineTone;
}

export interface PipelineStatusInput {
  readonly isLiveConnected: boolean;
  readonly isCachedFallback: boolean;
  readonly isSimulatedOutage: boolean;
  readonly isLoading: boolean;
  readonly dataOrigin: DataOrigin;
}

export function getPipelineStatus(input: PipelineStatusInput): PipelineStatus {
  if (input.isSimulatedOutage || input.isCachedFallback) return { label: 'Replay', tone: 'warn' };
  if (input.isLoading) return { label: 'Syncing', tone: 'neutral' };
  if (!input.isLiveConnected) return { label: 'Offline', tone: 'bad' };
  if (input.dataOrigin === 'fixture') return { label: 'Fixture', tone: 'warn' };
  if (input.dataOrigin === 'engine') return { label: 'Engine', tone: 'ok' };
  return { label: 'Live', tone: 'ok' };
}
