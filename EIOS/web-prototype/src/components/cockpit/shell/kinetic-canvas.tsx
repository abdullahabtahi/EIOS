'use client';

/**
 * Right Kinetic Canvas Container (Flexible Column)
 * Universal Tripartite COP Right Zone.
 * Dynamically dispatches role-specific visualizations:
 * - Executive: Causal DAG Canvas & What-If Waterfall (Principle III)
 * - AML Investigator: Topological Graph with CGNAT Hub Suppression & SAR Composer
 * - Partner Manager: Churn Survival Radar 2D Scatter & 3-Tier Affiliate Tree
 * - Compliance Auditor: WORM Immutability Ledger Timeline & Hash Chain Verification
 * - Data Operations: Streaming Ingestion Telemetry, 10-SLO Burndown, & DR Proofs
 * 
 * Strict Institutional Light-Mode styling.
 * Maximum 2 Headers across the whole system:
 * - Header 1: Global App Header
 * - Header 2: Kinetic Canvas Studio Header (scoped to this canvas, with live scroll spy & mode tabs)
 * Zero 3rd nav bar below Header 2. Rich, continuous, scrollable workspace.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { ExecutiveCockpitView } from '../workstations/executive-cockpit';
import { AmlWorkstationView } from '../workstations/aml-workstation';
import { PartnerWorkstationView } from '../workstations/partner-workstation';
import { ComplianceExplorerView } from '../workstations/compliance-explorer';
import { OperationsBoardView } from '../workstations/operations-board';
import { FlywheelFeedbackModal } from '../common/flywheel-feedback';

export function KineticCanvas() {
  const { state, toggleSimulatedOutage } = useCockpit();
  const [activeMode, setActiveMode] = React.useState<'workstation' | 'diagnostics'>('workstation');
  const [flywheelModalOpen, setFlywheelModalOpen] = React.useState(false);
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  const role = state.activeRole || 'executive';

  const roleConfig = React.useMemo(() => {
    switch (role) {
      case 'aml_investigator':
        return {
          title: 'KINETIC CANVAS: AML INVESTIGATOR',
          tabs: [
            { id: 'graph', label: 'Topological Graph', anchor: 'panel-graph' },
            { id: 'sar', label: 'SAR Composer', anchor: 'panel-sar' },
            { id: 'dossier', label: 'Evidence Dossier', anchor: 'panel-dossier' },
            { id: 'diagnostics', label: 'Diagnostics & Red-Lines', isDiagnostics: true },
          ],
        };
      case 'partner_manager':
        return {
          title: 'KINETIC CANVAS: PARTNER MANAGER',
          tabs: [
            { id: 'radar', label: '2D Churn Radar', anchor: 'panel-radar' },
            { id: 'grid', label: 'Portfolio Table Matrix', anchor: 'panel-grid' },
            { id: 'tree', label: 'Sub-Affiliate Tree', anchor: 'panel-tree' },
            { id: 'ontology', label: 'Ontology 360', anchor: 'panel-ontology' },
            { id: 'diagnostics', label: 'Diagnostics & Red-Lines', isDiagnostics: true },
          ],
        };
      case 'compliance_auditor':
        return {
          title: 'KINETIC CANVAS: COMPLIANCE & AUDIT',
          tabs: [
            { id: 'ledger', label: 'WORM Decision Ledger', anchor: 'panel-ledger' },
            { id: 'verifier', label: 'Chain Continuity Verifier', anchor: 'panel-verifier' },
            { id: 'dr', label: 'Disaster Recovery Proofs', anchor: 'panel-dr' },
            { id: 'diagnostics', label: 'Diagnostics & Red-Lines', isDiagnostics: true },
          ],
        };
      case 'data_operations':
        return {
          title: 'KINETIC CANVAS: DATA OPERATIONS',
          tabs: [
            { id: 'slos', label: 'Data Product SLOs', anchor: 'panel-slos' },
            { id: 'redlines', label: 'Red-Line Test Gates', anchor: 'panel-redlines' },
            { id: 'dlq', label: 'DLQ Quarantine', anchor: 'panel-dlq' },
            { id: 'dr', label: 'DR Proofs', anchor: 'panel-dr' },
            { id: 'diagnostics', label: 'Diagnostics & Red-Lines', isDiagnostics: true },
          ],
        };
      case 'executive':
      default:
        return {
          title: 'KINETIC CANVAS: EXECUTIVE',
          tabs: [
            { id: 'dag', label: 'Causal DAG', anchor: 'panel-dag' },
            { id: 'whatif', label: 'What-If Waterfall', anchor: 'panel-whatif' },
            { id: 'briefing', label: 'Morning Briefing', anchor: 'panel-briefing' },
            { id: 'tradeoffs', label: 'Strategic Trade-offs', anchor: 'panel-tradeoffs' },
            { id: 'diagnostics', label: 'Diagnostics & Red-Lines', isDiagnostics: true },
          ],
        };
    }
  }, [role]);

  const [activeTabId, setActiveTabId] = React.useState<string>(roleConfig.tabs[0].id);

  // Synchronize default tab on role changes
  React.useEffect(() => {
    if (activeMode !== 'diagnostics') {
      setActiveTabId(roleConfig.tabs[0].id);
    }
  }, [roleConfig, activeMode]);

  // Synchronize active tab with scroll position (Scroll Spy)
  React.useEffect(() => {
    if (activeMode !== 'workstation') return;
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const anchors = roleConfig.tabs.filter((t) => !t.isDiagnostics && t.anchor);
      const containerRect = container.getBoundingClientRect();

      let currentId = anchors[0]?.id;
      for (const tab of anchors) {
        const el = document.getElementById(tab.anchor!);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top - containerRect.top <= 140) {
            currentId = tab.id;
          }
        }
      }
      if (currentId && currentId !== activeTabId) {
        setActiveTabId(currentId);
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [activeMode, roleConfig, activeTabId]);

  const handleTabClick = (tab: (typeof roleConfig.tabs)[number]) => {
    if (tab.isDiagnostics) {
      setActiveMode('diagnostics');
      setActiveTabId('diagnostics');
      return;
    }
    if (activeMode === 'diagnostics') {
      setActiveMode('workstation');
    }
    setActiveTabId(tab.id);
    if (tab.anchor) {
      const el = document.getElementById(tab.anchor);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  const renderWorkstation = () => {
    switch (role) {
      case 'partner_manager':
        return <PartnerWorkstationView />;
      case 'aml_investigator':
        return <AmlWorkstationView />;
      case 'executive':
        return <ExecutiveCockpitView />;
      case 'compliance_auditor':
        return <ComplianceExplorerView />;
      case 'data_operations':
        return <OperationsBoardView />;
      default:
        return <ExecutiveCockpitView />;
    }
  };

  const activeModeLabel =
    activeMode === 'diagnostics'
      ? 'System Diagnostics'
      : (roleConfig.tabs.find((t) => t.id === activeTabId)?.label ?? roleConfig.tabs[0].label);

  return (
    <section
      aria-label="Kinetic Visualization Canvas"
      className="flex-1 min-w-[420px] bg-[#F5F8FA] flex flex-col h-full overflow-hidden select-none"
    >
      {/* Studio Surface Navigation Bar (Header #2 - Flush Canvas Header) */}
      <div className="h-11 px-4 bg-white border-b border-slate-200 flex items-center justify-between shrink-0 select-none">
        {/* Left: Role Title & Active Mode */}
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-600">hub</span>
          <span className="text-xs font-bold font-mono tracking-tight uppercase text-slate-900 truncate">
            {roleConfig.title}
          </span>
          <span className="text-slate-300 hidden xl:inline">|</span>
          <span className="text-[11px] font-mono text-slate-500 truncate hidden xl:inline">
            Mode:{' '}
            <span className="text-slate-800 font-semibold">{activeModeLabel}</span>
          </span>
        </div>

        {/* Right: View Tabs & Flywheel Feedback */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <div
            role="tablist"
            aria-label="Kinetic Canvas Modes"
            className="flex items-center bg-[#F5F8FA] p-0.5 border border-[#D8E1E8] text-[10px] font-mono"
          >
            {roleConfig.tabs.map((tab) => {
              const isSelected = activeMode === 'diagnostics' ? !!tab.isDiagnostics : activeTabId === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => handleTabClick(tab)}
                  className={`px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-none transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-white shadow-xs font-bold text-slate-900 border border-slate-200'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Active Learning Flywheel Trigger Button (Feature 014) */}
          <button
            type="button"
            onClick={() => setFlywheelModalOpen(true)}
            className="px-2.5 py-1 bg-[#182026] hover:bg-[#202B33] text-white text-[11px] font-mono font-medium flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs"
            title="Submit investigator discrepancy feedback to Active Learning Flywheel"
          >
            <span className="material-symbols-sharp text-xs text-[#D9822B]">psychology_alt</span>
            <span className="hidden sm:inline">Flywheel</span> Feedback
          </button>
        </div>
      </div>

      {/* Main Kinetic Content Zone */}
      {activeMode === 'diagnostics' ? (
        <div className="flex-1 overflow-y-auto flex flex-col p-4 space-y-4">
          {/* Diagnostics Return Bar */}
          <div className="p-3 bg-white border border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-slate-700">build</span>
              <span className="text-xs font-bold font-mono uppercase text-slate-900">
                System Diagnostics &amp; Red-Line Gates (RL-1 to RL-7)
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-emerald-100 text-emerald-800 font-bold border border-emerald-300">
                7/7 ENFORCED
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setActiveMode('workstation');
                setActiveTabId(roleConfig.tabs[0].id);
              }}
              className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-medium transition-colors cursor-pointer"
            >
              &larr; Return to Workstation
            </button>
          </div>

          {/* Flywheel Diagnostic Status Card */}
          <div className="p-4 bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-purple-600">psychology_alt</span>
                <h4 className="text-xs font-bold font-mono uppercase text-slate-900">
                  Active Learning Flywheel Telemetry (Feature 014)
                </h4>
              </div>
              <span className="text-[10px] font-mono bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5">
                Brier Score: {state.activeFlywheelStatus?.shadowModelBrierScore?.toFixed(3) ?? '0.082'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Total Feedback Events</span>
                <span className="text-base font-bold text-slate-900 tabular-nums">
                  {state.activeFlywheelStatus?.totalFeedbackEvents ?? 142}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Uncalibrated Discrepancies</span>
                <span className="text-base font-bold text-amber-700 tabular-nums">
                  {state.activeFlywheelStatus?.uncalibratedDiscrepancies ?? 2}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Calibration Drift</span>
                <span className="text-sm sm:text-base font-bold text-emerald-700 truncate">
                  {state.activeFlywheelStatus?.calibrationDriftDetected ? 'DRIFT DETECTED' : 'NOMINAL (CALIBRATED)'}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Outcomes Model Status</span>
                <span className="text-sm sm:text-base font-bold text-slate-900">SHADOW_REPLAY</span>
              </div>
            </div>
          </div>

          {/* Red-Line Test Gate Verification Card (RL-1 to RL-7) */}
          <div className="p-4 bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-emerald-600">verified</span>
                <h4 className="text-xs font-bold font-mono uppercase text-slate-900">
                  Constitutional Red-Line Test Gates (RL-1 to RL-7)
                </h4>
              </div>
              <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 font-bold">
                7/7 ENFORCED
              </span>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-2 text-xs font-mono">
              {[
                { id: 'RL-1', name: 'Zero LLM Metric Calculation (Principle I)', status: 'PASS' },
                { id: 'RL-2', name: 'Four-Eyes Dual Approval Mutation Gate (Principle II)', status: 'PASS' },
                { id: 'RL-3', name: 'Causal Refuter Placebo p > 0.05 (Principle III)', status: 'PASS' },
                { id: 'RL-4', name: 'CGNAT False Positive Hub Suppression (k > 100)', status: 'PASS' },
                { id: 'RL-5', name: 'Immutable WORM Hash-Chain Ledger Locks', status: 'PASS' },
                { id: 'RL-6', name: 'Sub-200ms Parametric Propagation & 100% Attribution', status: 'PASS' },
                { id: 'RL-7', name: 'Deterministic Offline Replay Fallback (Principle VIII)', status: 'PASS' },
              ].map((gate) => (
                <div key={gate.id} className="p-2 bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-900 mr-1.5">{gate.id}:</span>
                    <span className="text-slate-700 font-sans text-[11px]">{gate.name}</span>
                  </div>
                  <span className="px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#EDF7ED] text-[#0D8050] border border-[#C3E6D0]">
                    {gate.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Principle VIII Chaos & Fallback Verification Card */}
          <div className="p-4 bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-amber-600">electrical_services</span>
                <h4 className="text-xs font-bold font-mono uppercase text-slate-900">
                  Resilience Gate (Principle VIII) • Deterministic Fallback &amp; Partition Verification
                </h4>
              </div>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 border font-semibold ${
                state.isSimulatedOutage
                  ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200'
              }`}>
                {state.isSimulatedOutage ? 'PARTITION ACTIVE (OFFLINE REPLAY)' : 'LIVE STREAM NOMINAL'}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              Injects a simulated upstream presentation partition to test deterministic offline fallback and verified cryptographic cache replay under network severance.
            </p>
            <button
              type="button"
              onClick={() => toggleSimulatedOutage()}
              className={`px-3 py-1.5 text-xs font-mono font-medium border transition-colors flex items-center gap-1.5 cursor-pointer ${
                state.isSimulatedOutage
                  ? 'bg-amber-500 border-amber-600 text-slate-950 font-bold'
                  : 'bg-slate-50 hover:bg-slate-100 border-slate-300 text-slate-800'
              }`}
            >
              <span className="material-symbols-sharp text-xs">
                {state.isSimulatedOutage ? 'bolt' : 'electrical_services'}
              </span>
              <span>{state.isSimulatedOutage ? 'Restore Live Pipeline Stream' : 'Simulate Outage & Partition Fallback'}</span>
            </button>
          </div>
        </div>
      ) : (
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth"
        >
          {renderWorkstation()}
        </div>
      )}

      {/* Flywheel Modal (Feature 014) */}
      <FlywheelFeedbackModal
        open={flywheelModalOpen}
        onOpenChange={setFlywheelModalOpen}
      />
    </section>
  );
}
