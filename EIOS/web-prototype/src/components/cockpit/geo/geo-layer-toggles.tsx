import * as React from 'react';
import { LAYER_LABEL } from './geo-views';
import type { LayerId } from './geo-types';

const ORDER: readonly LayerId[] = ['risk', 'offshore', 'corridors', 'mismatches'];

/** For the analyst who wants a different mix than the open view: collapsed, so a first visit never meets it. */
export function GeoLayerToggles({ visible, disabled, onToggle }: { readonly visible: ReadonlySet<LayerId>; readonly disabled: ReadonlySet<LayerId>; readonly onToggle: (id: LayerId) => void }) {
  const on = ORDER.filter((id) => visible.has(id) && !disabled.has(id)).length;
  return (
    <details className="group border-t border-cx-line-soft">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-xs font-semibold text-cx-ink-soft outline-none hover:bg-cx-sub focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent">
        <span>Layers</span>
        <span className="font-mono text-label font-normal text-cx-muted">{on} of {ORDER.length} on</span>
      </summary>
      <div className="space-y-1.5 px-4 pb-3">
        {ORDER.map((id) => {
          const off = disabled.has(id);
          return (
            <label key={id} className={`flex items-center gap-2 text-xs ${off ? 'text-cx-faint' : 'cursor-pointer text-cx-ink'}`}>
              <input type="checkbox" className="accent-cx-accent" disabled={off} checked={visible.has(id) && !off} onChange={() => onToggle(id)} />
              {LAYER_LABEL[id]}
            </label>
          );
        })}
      </div>
    </details>
  );
}
