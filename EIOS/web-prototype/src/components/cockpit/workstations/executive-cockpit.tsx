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
    return <p className="p-4 text-xs text-slate-500 bg-slate-50 border border-slate-200 font-mono">Loading executive decision board…</p>;
  }
  if (load.status === 'error') {
    return (
      <p role="alert" className="p-4 text-xs text-red-700 bg-red-50 border border-red-200 font-mono">
        The executive board could not be loaded. Nothing is shown in its place.
      </p>
    );
  }

  const { board } = load;
  return (
    <div className="space-y-4 text-slate-900 pb-12 select-none">
      {/* 1. Hero 28-Day Net Revenue Projection & Credible Interval Envelope */}
      <ForecastCard forecast={board.forecast} />

      {/* Morning Briefing: Screen-reader accessible to avoid duplicating Copilot Dossier */}
      <div role="region" id="panel-briefing" aria-label="Morning Briefing" className="sr-only">
        <BriefingCards horizons={board.horizons} />
      </div>

      {/* 2. Causal Topology Graph Fitted from Historical Observations */}
      <div role="tabpanel" id="panel-dag" aria-label="Causal DAG Canvas">
        <CausalGraph nodes={board.nodes} edges={board.edges} />
      </div>

      {/* 3. Co-Primary Execution Deck: What-If Parametric Simulation + Strategic Play Staging */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-stretch">
        <div role="tabpanel" id="panel-whatif" aria-label="What-If Parametric Waterfall" className="h-full">
          {board.shocks[0] && <WhatIfPanel shock={board.shocks[0]} />}
        </div>
        <div role="tabpanel" id="panel-tradeoffs" aria-label="Strategic Trade-offs" className="h-full">
          <OpportunitiesPanel risks={board.risks} opportunities={board.opportunities} />
        </div>
      </div>
    </div>
  );
}
