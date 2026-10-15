import * as React from 'react';
import type { GeoFlows, GeoReference } from './geo-types';

/** Where every figure comes from, one click away; the as-of date stays visible on the closed row. */
export function GeoSources({ flows, reference }: { readonly flows: GeoFlows | null; readonly reference: GeoReference | null }) {
  if (!flows && !reference) return null;
  const asOf = flows?.as_of.slice(0, 10);
  return (
    <details className="border-t border-cx-line-soft">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-xs font-semibold text-cx-ink-soft outline-none hover:bg-cx-sub focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent">
        <span>Sources</span>
        {asOf && <span className="font-mono text-label font-normal text-cx-muted">as of {asOf}</span>}
      </summary>
      <ul className="space-y-1 px-4 pb-3 text-label text-cx-muted">
        {flows && (
          <li>
            {flows.source} · as of <span className="font-mono">{flows.as_of.slice(0, 10)}</span>
          </li>
        )}
        {reference &&
          Object.values(reference.sources).map((s) => (
            <li key={s.source}>
              {s.source}
              {s.as_of && <> · as of <span className="font-mono">{s.as_of}</span></>}
            </li>
          ))}
      </ul>
    </details>
  );
}
