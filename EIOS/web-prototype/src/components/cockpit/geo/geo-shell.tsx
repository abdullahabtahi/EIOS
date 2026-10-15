'use client';

import * as React from 'react';
import { AppNavRail } from '../shell/app-nav-rail';
import { GeoWorkspace } from './geo-workspace';

/** Geospatial section shell: global rail plus one slim title row (no persona strip; one header only) and the workspace. */
export function GeoShell() {
  return (
    <div data-cockpit-shell className="relative flex h-screen w-screen flex-row overflow-hidden bg-cx-canvas font-sans text-slate-900 antialiased">
      <AppNavRail currentId="geospatial" />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-11 shrink-0 items-center gap-3 border-b border-cx-line bg-white px-4">
          <h1 className="text-title font-sans font-semibold text-cx-ink">Geospatial</h1>
          <span className="text-xs text-cx-muted">Financial geography as an evidence lens</span>
        </header>
        <main id="workspace" className="min-h-0 flex-1">
          <GeoWorkspace />
        </main>
      </div>
    </div>
  );
}
