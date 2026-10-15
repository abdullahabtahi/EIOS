'use client';

import * as React from 'react';
import { GEO_FIXTURE } from './geo-fixture';
import { buildLayers } from './geo-layers';
import { GeoMap } from './geo-map';
import { GeoWidgets } from './geo-widgets';
import { GeoCopilotPanel } from './geo-copilot-panel';
import { GeoLegend } from './geo-legend';
import { useGeoReference } from './use-geo-reference';
import type { GeoEvidence, GeoSelection, LayerId } from './geo-types';

const ALL_LAYERS: ReadonlySet<LayerId> = new Set(['risk', 'offshore', 'corridors', 'mismatches']);

/** Map-first workspace: Google basemap with deck.gl evidence, copilot placeholder on the left, widgets on the right. */
export function GeoWorkspace({ evidence = GEO_FIXTURE }: { readonly evidence?: GeoEvidence }) {
  const reference = useGeoReference();
  const [visible, setVisible] = React.useState<ReadonlySet<LayerId>>(ALL_LAYERS);
  const [hovered, setHovered] = React.useState<GeoSelection>(null);
  const [selected, setSelected] = React.useState<GeoSelection>(null);

  const toggle = React.useCallback((id: LayerId) => {
    setVisible((prev) => (prev.has(id) ? new Set([...prev].filter((x) => x !== id)) : new Set([...prev, id])));
  }, []);

  const layers = React.useMemo(
    () =>
      buildLayers(evidence, reference.status === 'ready' ? reference.reference : null, visible, selected, {
        onHover: setHovered,
        onSelect: setSelected,
      }),
    [evidence, reference, visible, selected],
  );

  return (
    <div className="flex h-full min-h-0">
      <div className="relative min-w-0 flex-1">
        <GeoMap layers={layers} />
        <div className="pointer-events-none absolute left-3 top-3 z-10">
          <div className="pointer-events-auto">
            <GeoCopilotPanel />
          </div>
        </div>
        <div className="pointer-events-none absolute bottom-6 left-3 z-10">
          <GeoLegend />
        </div>
      </div>
      <div className="w-80 shrink-0 border-l border-cx-line bg-white">
        <GeoWidgets evidence={evidence} reference={reference} visible={visible} onToggle={toggle} hovered={hovered} selected={selected} />
      </div>
    </div>
  );
}
