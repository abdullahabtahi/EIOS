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
    void fetchExecutiveBoard()
      .then((board) => {
        if (active) setLoad(board ? { status: 'ready', board } : { status: 'error' });
      })
      .catch(() => {
        if (active) setLoad({ status: 'error' });
      });
    return () => {
      active = false;
    };
  }, []);

  if (load.status === 'loading') {
    return (
      <div className="space-y-4 text-slate-900 pb-12 select-none animate-pulse">
        {/* Skeleton ForecastCard */}
        <div className="bg-white border border-slate-200 p-6 min-h-[280px] space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="h-4 w-52 bg-slate-200 rounded-xs" />
            <div className="h-4 w-32 bg-slate-100 rounded-xs" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center pt-2">
            <div className="md:col-span-5 space-y-3">
              <div className="h-3 w-40 bg-slate-200 rounded-xs" />
              <div className="h-8 w-48 bg-slate-300 rounded-xs" />
              <div className="h-3 w-64 bg-slate-100 rounded-xs" />
            </div>
            <div className="md:col-span-7 h-28 bg-slate-50 border border-slate-200 rounded-xs" />
          </div>
        </div>

        {/* Skeleton CausalGraph */}
        <div className="bg-white border border-slate-200 p-4 min-h-[240px] space-y-3 shadow-xs">
          <div className="h-4 w-60 bg-slate-200 rounded-xs" />
          <div className="h-44 bg-slate-50 border border-slate-200 rounded-xs" />
        </div>
      </div>
    );
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
      <div className="@container">
        <div className="grid grid-cols-1 @[880px]:grid-cols-2 gap-4 items-stretch">
          <div role="tabpanel" id="panel-whatif" aria-label="What-If Parametric Waterfall" className="h-full">
            {board.shocks[0] && <WhatIfPanel shock={board.shocks[0]} />}
          </div>
          <div role="tabpanel" id="panel-tradeoffs" aria-label="Strategic Trade-offs" className="h-full">
            <OpportunitiesPanel risks={board.risks} opportunities={board.opportunities} />
          </div>
        </div>
      </div>
    </div>
  );
}
