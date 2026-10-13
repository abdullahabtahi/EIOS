'use client';

/**
 * Partner Manager Kinetic Canvas Workstation View
 * Institutional Analytical Grade.
 * 
 * Provides 4 clean, non-overlapping analytical surfaces:
 * 1. 2D Cartesian Churn Hazard Radar (P(churn) × VaR) with drift trajectories
 * 2. High-Density Portfolio Matrix (Full-screen tabular triage with multi-sort)
 * 3. 3-Tier Sub-Affiliate Tree & Mirror Trading Collusion Detection
 * 4. Sovereign Kinetic Ontology 360 Entity Inspector
 * 
 * Strict Single Responsibility: Zero duplicate triages, zero duplicate sliders.
 * Strict Sovereign Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { MOCK_PARTNERS } from '../state/fixtures';
import { ChurnRadarScatter } from '../common/churn-radar-scatter';
import { PartnerTree } from '../common/partner-tree';
import { PartnerTriageGrid } from '../common/partner-triage-grid';
import { PartnerOntologyInspector } from './partner-ontology-inspector';

export function PartnerWorkstationView() {
  const { state, selectEntity } = useCockpit();

  return (
    <div className="space-y-6 text-slate-900 pb-10">
      {/* Surface 1: 2D Churn Hazard Radar (Anchor: panel-radar) */}
      <div
        role="tabpanel"
        id="panel-radar"
        aria-label="2D Churn Hazard Radar"
        className="block"
      >
        <ChurnRadarScatter />
      </div>

      {/* Surface 2: High-Density Portfolio Matrix (Anchor: panel-grid) */}
      <div
        role="tabpanel"
        id="panel-grid"
        aria-label="Portfolio Table Matrix"
        className="block"
      >
        <div className="bg-white border border-slate-200 p-4 shadow-xs">
          <PartnerTriageGrid
            partners={MOCK_PARTNERS}
            selectedPartnerId={state.activeEntityId || 'PTR-882'}
            onSelectPartner={(p) => selectEntity(p.partnerId)}
          />
        </div>
      </div>

      {/* Surface 3: 3-Tier Sub-Affiliate Tree & Mirror Trading Collusion Detection (Anchor: panel-tree) */}
      <div
        role="tabpanel"
        id="panel-tree"
        aria-label="Sub-Affiliate Tree and Collusion Detection"
        className="block"
      >
        <PartnerTree />
      </div>

      {/* Surface 4: Sovereign Kinetic Ontology 360 Inspector (Anchor: panel-ontology) */}
      <div
        role="tabpanel"
        id="panel-ontology"
        aria-label="Sovereign Kinetic Ontology 360"
        className="block"
      >
        <PartnerOntologyInspector />
      </div>
    </div>
  );
}
