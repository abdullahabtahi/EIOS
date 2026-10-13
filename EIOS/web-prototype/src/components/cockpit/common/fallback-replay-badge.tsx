'use client';

/**
 * Fallback Replay Badge & Banner
 * Enforces Constitution Principle VIII (Deterministic Fallback Under Outage).
 * Explicitly alerts institutional operators when cached verified snapshots are being served
 * during presentation engine partitions or outage simulations.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { formatUtcTimestamp } from '@/lib/utils';

interface FallbackReplayBadgeProps {
  timestamp?: string;
  reason?: string;
  size?: 'sm' | 'default';
  className?: string;
}

export function FallbackReplayBadge({
  timestamp,
  reason,
  size = 'default',
  className = '',
}: FallbackReplayBadgeProps) {
  const formattedTime = React.useMemo(() => {
    return timestamp ? formatUtcTimestamp(timestamp) : 'PRE-COMPILED SNAPSHOT';
  }, [timestamp]);

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-medium border border-amber-400 bg-amber-50 text-amber-900 rounded-none shadow-xs ${
        size === 'sm' ? 'px-1.5 py-0.5 text-label' : 'px-2 py-1 text-xs'
      } ${className}`}
      title={reason ?? `Deterministic Fallback: Serving verified snapshot cached as of ${formattedTime}`}
    >
      <span className="material-symbols-sharp text-amber-600 text-[13px] animate-pulse">
        history
      </span>
      <span className="font-bold tracking-tight">[REPLAY]</span>
      <span className="text-amber-800 tabular-nums hidden sm:inline">{formattedTime}</span>
    </span>
  );
}

interface FallbackReplayBannerProps {
  className?: string;
}

export function FallbackReplayBanner({ className = '' }: FallbackReplayBannerProps) {
  const { state, toggleSimulatedOutage, refreshWorkstation } = useCockpit();
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  if (!state.isCachedFallback && !state.isSimulatedOutage) {
    return null;
  }

  const handleReconnect = async () => {
    setIsRefreshing(true);
    try {
      if (state.isSimulatedOutage) {
        toggleSimulatedOutage(false);
      }
      await refreshWorkstation();
    } finally {
      setIsRefreshing(false);
    }
  };

  const formattedTime = formatUtcTimestamp(state.asOfTimestamp);

  return (
    <aside
      aria-label="Deterministic Fallback Replay Alert"
      className={`w-full bg-amber-50 border-b border-amber-300 text-amber-950 px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs z-30 transition-all ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <div className="flex items-center justify-center size-6 bg-amber-200/80 border border-amber-400 text-amber-900">
          <span className="material-symbols-sharp text-base">warning</span>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold tracking-tight text-amber-900 bg-amber-200/70 px-1 py-0.2 border border-amber-300">
              [REPLAY] PRINCIPLE VIII ACTIVE
            </span>
            <span className="font-semibold text-amber-900">
              {state.isSimulatedOutage
                ? 'Simulated Outage Mode Active'
                : 'Upstream Presentation Partition: Deterministic Fallback'}
            </span>
          </div>
          <p className="text-label text-amber-800 mt-0.5">
            Serving cryptographically verified offline snapshot cached at{' '}
            <span className="font-mono font-semibold tabular-nums text-amber-950">{formattedTime}</span>.
            Mutations will require two-phase commit queueing upon reconnect.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {state.isSimulatedOutage && (
          <button
            type="button"
            onClick={() => toggleSimulatedOutage(false)}
            className="px-2.5 py-1 bg-amber-100 hover:bg-amber-200 border border-amber-400 text-amber-900 font-medium rounded-none text-xs transition-colors flex items-center gap-1 cursor-pointer"
          >
            <span className="material-symbols-sharp text-sm">toggle_off</span>
            Exit Outage Simulation
          </button>
        )}

        <button
          type="button"
          disabled={isRefreshing}
          onClick={handleReconnect}
          className="px-2.5 py-1 bg-amber-900 hover:bg-amber-950 text-white font-medium rounded-none text-xs transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
        >
          <span className={`material-symbols-sharp text-sm ${isRefreshing ? 'animate-spin' : ''}`}>
            sync
          </span>
          {isRefreshing ? 'Reconnecting...' : 'Attempt Live Reconnect'}
        </button>
      </div>
    </aside>
  );
}
