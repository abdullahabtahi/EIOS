'use client';

import * as React from 'react';
import { AppNavRail } from '../shell/app-nav-rail';
import { ChromeBrand, ChromeOperator } from '../shell/chrome-bar';
import { GeoWorkspace } from './geo-workspace';

/**
 * Geospatial section shell: the global rail, the same dark chrome row as the workstations (brand and operator;
 * the telemetry and Ask controls need workstation state and are not shown here), and the workspace. One header only.
 */
export function GeoShell() {
  return (
    <div data-cockpit-shell className="relative flex h-screen w-screen flex-row overflow-hidden bg-cx-canvas font-sans text-slate-900 antialiased">
      <AppNavRail currentId="geospatial" />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="z-30 flex h-11 shrink-0 select-none items-center justify-between bg-cockpit-rail px-4 text-slate-100">
          <ChromeBrand section="Geospatial" heading />
          <ChromeOperator />
        </header>
        <main id="workspace" className="min-h-0 flex-1">
          <GeoWorkspace />
        </main>
      </div>
    </div>
  );
}
