import * as React from 'react';
import type { ResourceState } from './use-geo-resource';

/** A resource still loading or failed, in words; null once it is ready. A failure says what is missing and offers a retry. */
export function GeoStatus({ label, state }: { readonly label: string; readonly state: ResourceState<unknown> }) {
  if (state.status === 'ready') return null;
  if (state.status === 'loading') {
    return (
      <div role="status" aria-label={`Loading ${label}`} className="space-y-2" data-testid="geo-loading">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-9 animate-pulse bg-cx-sub-2 motion-reduce:animate-none" />
        ))}
        <p className="text-label text-cx-muted">Loading {label}…</p>
      </div>
    );
  }
  return (
    <div role="alert" className="border border-cx-warn-line bg-cx-warn-bg p-3 text-xs text-cx-ink-soft">
      <p>
        The {label} could not be loaded{state.httpStatus ? ` (HTTP ${state.httpStatus})` : ''}. Nothing from it is shown.
      </p>
      <button
        type="button"
        onClick={state.reload}
        className="mt-2 cursor-pointer border border-cx-line bg-white px-2 py-1 font-semibold text-cx-ink outline-none hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-cx-accent">
        Retry
      </button>
    </div>
  );
}
