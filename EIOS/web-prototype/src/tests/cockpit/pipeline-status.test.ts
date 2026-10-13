import { describe, it, expect } from 'vitest';
import { getPipelineStatus } from '@/components/cockpit/state/pipeline-status';

const base = { isLiveConnected: true, isCachedFallback: false, isSimulatedOutage: false, isLoading: false };

describe('getPipelineStatus (derived, never hard-coded)', () => {
  it('is Live only when connected, not cached and not in a simulated outage', () => {
    expect(getPipelineStatus(base)).toEqual({ label: 'Live', tone: 'ok' });
  });

  it('is Replay when serving a cached fallback snapshot', () => {
    expect(getPipelineStatus({ ...base, isCachedFallback: true, isLiveConnected: false })).toEqual({
      label: 'Replay',
      tone: 'warn',
    });
  });

  it('is Replay during a simulated outage even if a live flag lingers', () => {
    expect(getPipelineStatus({ ...base, isSimulatedOutage: true })).toEqual({ label: 'Replay', tone: 'warn' });
  });

  it('is Offline when not connected and not replaying a snapshot', () => {
    expect(getPipelineStatus({ ...base, isLiveConnected: false })).toEqual({ label: 'Offline', tone: 'bad' });
  });

  it('is Syncing while a workstation load is in flight (never claims Live before the first answer)', () => {
    expect(getPipelineStatus({ ...base, isLoading: true })).toEqual({ label: 'Syncing', tone: 'neutral' });
  });

  it('prefers Replay over Syncing so an outage is never masked', () => {
    expect(getPipelineStatus({ ...base, isLoading: true, isSimulatedOutage: true })).toEqual({
      label: 'Replay',
      tone: 'warn',
    });
  });
});
