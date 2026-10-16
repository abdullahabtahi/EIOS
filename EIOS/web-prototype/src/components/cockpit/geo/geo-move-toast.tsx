'use client';

/** Says that the assistant moved the map and to what, with a way back. A move is never silent. */

import * as React from 'react';

export interface GeoMoveToastProps {
  readonly label: string;
  /** True when the move came with an answer; false when the reader asked for it. */
  readonly auto: boolean;
  readonly canGoBack: boolean;
  readonly onBack: () => void;
  readonly onDismiss: () => void;
}

export function GeoMoveToast({ label, auto, canGoBack, onBack, onDismiss }: GeoMoveToastProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="absolute bottom-6 left-1/2 z-20 flex max-w-[90%] -translate-x-1/2 items-center gap-3 border border-cx-line bg-white px-3 py-2 text-xs text-cx-ink shadow-md"
    >
      <span className="material-symbols-sharp text-base text-cx-accent" aria-hidden="true">
        my_location
      </span>
      <span className="min-w-0 truncate">
        {auto ? 'The assistant moved the map to' : 'Showing'} <strong>{label}</strong>
      </span>
      {canGoBack && (
        <button type="button" onClick={onBack} className="shrink-0 cursor-pointer font-semibold text-cx-accent underline hover:text-cx-ink">
          Back
        </button>
      )}
      <button type="button" onClick={onDismiss} aria-label="Dismiss" className="shrink-0 cursor-pointer text-cx-muted hover:text-cx-ink">
        ×
      </button>
    </div>
  );
}
