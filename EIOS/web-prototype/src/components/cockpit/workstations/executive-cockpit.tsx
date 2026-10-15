'use client';

/**
 * Executive Decision Cockpit. Everything on this screen is read from the backend's executive board: the briefing,
 * the projection with its measured interval, the fitted causal graph, and the what-if. A failed read says so; no
 * figure is filled in.
 */

import * as React from 'react';
import { fetchExecutiveBoard, type ExecutiveBoard } from '../executive/board';
import { BriefingCards, ForecastCard } from '../executive/forecast-and-briefing';
import { CausalGraph } from '../executive/causal-graph';
import { WhatIfPanel } from '../executive/what-if-panel';
import { OpportunitiesPanel } from '../executive/opportunities-panel';

type Load = { status: 'loading' } | { status: 'error' } | { status: 'ready'; board: ExecutiveBoard };

export function ExecutiveCockpitView() {
  const [load, setLoad] = React.useState<Load>({ status: 'loading' });

  React.useEffect(() => {
    let active = true;
    fetchExecutiveBoard().then((board) => {
      if (active) setLoad(board ? { status: 'ready', board } : { status: 'error' });
    });
    return () => {
      active = false;
    };
  }, []);

  if (load.status === 'loading') {
    return <p className="p-4 text-xs text-cx-muted bg-cx-sub border border-cx-line">Loading the executive board…</p>;
  }
  if (load.status === 'error') {
    return (
      <p role="alert" className="p-4 text-xs text-cx-bad bg-white border border-cx-line">
        The executive board could not be loaded. Nothing is shown in its place.
      </p>
    );
  }

  const { board } = load;
  return (
    <div className="space-y-6 text-cx-ink pb-10">
      <div className="flex justify-end text-label font-mono text-cx-muted">
        as of {board.asOf.slice(0, 16).replace('T', ' ')} UTC · {board.dataOrigin}
      </div>
      <ForecastCard forecast={board.forecast} />
      <BriefingCards horizons={board.horizons} />
      <div role="tabpanel" id="panel-dag" aria-label="Causal DAG Canvas">
        <CausalGraph nodes={board.nodes} edges={board.edges} />
      </div>
      <div role="tabpanel" id="panel-whatif" aria-label="What-If Parametric Waterfall">
        {board.shocks[0] && <WhatIfPanel shock={board.shocks[0]} />}
      </div>
      <div role="tabpanel" id="panel-tradeoffs" aria-label="Strategic Trade-offs">
        <OpportunitiesPanel risks={board.risks} opportunities={board.opportunities} />
      </div>
    </div>
  );
}
