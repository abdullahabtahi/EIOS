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
import { WORKSTATION_ROLES } from './workstation-roles';
import { useCockpit } from '../state/cockpit-context';
import { ExecutiveCockpitView } from '../workstations/executive-cockpit';
import { AmlWorkstationView } from '../workstations/aml-workstation';
import { PartnerWorkstationView } from '../workstations/partner-workstation';
import { ComplianceExplorerView } from '../workstations/compliance-explorer';
import { OperationsBoardView } from '../workstations/operations-board';
import { FlywheelFeedbackModal } from '../common/flywheel-feedback';

export function KineticCanvas({ onCollapse }: { onCollapse?: () => void } = {}) {
  const { state } = useCockpit();
  const [flywheelModalOpen, setFlywheelModalOpen] = React.useState(false);
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  const role = state.activeRole || 'executive';

  const roleConfig = React.useMemo(() => {
    switch (role) {
      case 'aml_investigator':
        return {
          tabs: [
            { id: 'graph', label: 'Graph', title: 'Topological Graph', anchor: 'panel-graph' },
            { id: 'sar', label: 'SAR Composer', title: 'SAR Composer', anchor: 'panel-sar' },
            { id: 'dossier', label: 'Evidence', title: 'Evidence Dossier', anchor: 'panel-dossier' },
          ],
        };
      case 'partner_manager':
        return {
          tabs: [
            { id: 'radar', label: 'Radar', title: '2D Churn Radar', anchor: 'panel-radar' },
            { id: 'grid', label: 'Portfolio', title: 'Portfolio Table Matrix', anchor: 'panel-grid' },
            { id: 'tree', label: 'Affiliates', title: 'Sub-Affiliate Tree', anchor: 'panel-tree' },
            { id: 'ontology', label: 'Ontology', title: 'Ontology 360', anchor: 'panel-ontology' },
          ],
        };
      case 'compliance_auditor':
        return {
          tabs: [
            { id: 'ledger', label: 'Ledger', title: 'WORM Decision Ledger', anchor: 'panel-ledger' },
            { id: 'verifier', label: 'Verifier', title: 'Chain Continuity Verifier', anchor: 'panel-verifier' },
            { id: 'dr', label: 'DR Proofs', title: 'Disaster Recovery Proofs', anchor: 'panel-dr' },
          ],
        };
      case 'data_operations':
        return {
          tabs: [
            { id: 'slos', label: 'SLOs', title: 'Data Product SLOs', anchor: 'panel-slos' },
            { id: 'redlines', label: 'Red-Lines', title: 'Red-Line Test Gates', anchor: 'panel-redlines' },
            { id: 'dlq', label: 'DLQ', title: 'DLQ Quarantine', anchor: 'panel-dlq' },
            { id: 'dr', label: 'DR Proofs', title: 'Disaster Recovery Proofs', anchor: 'panel-dr' },
          ],
        };
      case 'executive':
      default:
        return {
          tabs: [
            { id: 'dag', label: 'Causal DAG', title: 'Causal DAG', anchor: 'panel-dag' },
            { id: 'whatif', label: 'What-If', title: 'What-If Waterfall', anchor: 'panel-whatif' },
            { id: 'briefing', label: 'Briefing', title: 'Morning Briefing', anchor: 'panel-briefing' },
            { id: 'tradeoffs', label: 'Trade-offs', title: 'Strategic Trade-offs', anchor: 'panel-tradeoffs' },
          ],
        };
    }
  }, [role]);

  // Selected tab is remembered per workstation and derived (never synced in an effect).
  const [selectedTabs, setSelectedTabs] = React.useState<Partial<Record<string, string>>>({});
  const activeTabId = selectedTabs[role] ?? roleConfig.tabs[0].id;
  const setActiveTabId = React.useCallback(
    (id: string) => setSelectedTabs((prev) => (prev[role] === id ? prev : { ...prev, [role]: id })),
    [role],
  );

  // Synchronize active tab with scroll position (Scroll Spy)
  React.useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const anchors = roleConfig.tabs.filter((t) => t.anchor);
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
  }, [roleConfig, activeTabId, setActiveTabId]);

  const allTabs = roleConfig.tabs;
  const roleLabel = WORKSTATION_ROLES.find((r) => r.id === role)?.label ?? 'Executive';

  const handleTabClick = (tab: (typeof allTabs)[number]) => {
    setActiveTabId(tab.id);
    if (tab.anchor) {
      const el = document.getElementById(tab.anchor);
      if (el) {
        el.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  // Roving-tabindex keyboard model (WAI-ARIA tabs): arrows wrap, Home/End jump.
  const handleTabKeyDown = (e: React.KeyboardEvent, index: number) => {
    const count = allTabs.length;
    let next: number;
    if (e.key === 'ArrowRight') next = (index + 1) % count;
    else if (e.key === 'ArrowLeft') next = (index - 1 + count) % count;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = count - 1;
    else return;
    e.preventDefault();
    const tab = allTabs[next];
    handleTabClick(tab);
    document.getElementById(`canvas-tab-${tab.id}`)?.focus();
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

  return (
    <section
      aria-label="Kinetic Visualization Canvas"
      className="flex-1 min-w-[420px] bg-cx-sub flex flex-col h-full overflow-hidden"
    >
      {/* Studio Surface Navigation Bar (Header #2).
          Title left; segmented tabs + Feedback grouped right. A container query lets the
          title shed words (role, then label) before anything clips, so no dead middle gap. */}
      <div data-testid="canvas-bar" className="@container shrink-0 bg-white border-b border-slate-200 select-none">
        <div className="h-11 px-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 min-w-0">
            {onCollapse && (
              <button
                type="button"
                onClick={onCollapse}
                title="Collapse Right Canvas (press ])"
                aria-label="Collapse Right Canvas"
                className="size-6 shrink-0 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-100 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cx-accent"
              >
                <span className="material-symbols-sharp text-base">chevron_right</span>
              </button>
            )}
          <div
            data-testid="canvas-title"
            role="heading"
            aria-level={2}
            aria-label={`Kinetic Canvas: ${roleLabel}`}
            className="flex items-center gap-2 min-w-0 font-mono text-xs font-bold uppercase tracking-tight text-slate-900"
          >
            <span aria-hidden="true" className="material-symbols-sharp text-base text-cx-accent shrink-0">hub</span>
            <span aria-hidden="true" className="hidden @[620px]:inline whitespace-nowrap truncate">
              Kinetic Canvas
              <span className="hidden @[900px]:inline">{`: ${roleLabel}`}</span>
            </span>
          </div>
          </div>

          <div data-testid="canvas-actions" className="flex items-center gap-2 min-w-0">
            <div
              role="tablist"
              aria-label="Canvas sections"
              className="flex items-center min-w-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden bg-cx-sub p-0.5 border border-cx-line font-mono text-label"
            >
              {allTabs.map((tab, index) => {
                const isSelected = activeTabId === tab.id;
                const isTabStop = isSelected;
                return (
                  <button
                    key={tab.id}
                    id={`canvas-tab-${tab.id}`}
                    type="button"
                    role="tab"
                    aria-selected={isSelected}
                    tabIndex={isTabStop ? 0 : -1}
                    title={tab.title}
                    onClick={() => handleTabClick(tab)}
                    onKeyDown={(e) => handleTabKeyDown(e, index)}
                    className={`shrink-0 whitespace-nowrap px-2 @[760px]:px-3 py-1 border transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cx-accent ${
                      isSelected
                        ? 'bg-white border-slate-200 shadow-xs font-bold text-slate-900'
                        : 'border-transparent text-slate-600 hover:text-slate-900'
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
              aria-label="Flywheel Feedback"
              onClick={() => setFlywheelModalOpen(true)}
              className="h-7 shrink-0 px-2 bg-cx-ink hover:bg-cx-ink-hover text-white text-label font-mono font-medium flex items-center gap-1.5 cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-cx-accent focus-visible:ring-offset-1"
              title="Submit investigator discrepancy feedback to the Active Learning Flywheel"
            >
              <span className="material-symbols-sharp text-sm text-blue-400">psychology_alt</span>
              <span className="hidden @[700px]:inline">Flywheel Feedback</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Kinetic Content Zone */}
      <div
        ref={scrollContainerRef}
        id="workstation-panel"
        role="tabpanel"
        aria-labelledby={`tab-${role}`}
        tabIndex={-1}
        className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth outline-none"
      >
        {renderWorkstation()}
      </div>

      {/* Flywheel Modal (Feature 014) */}
      <FlywheelFeedbackModal
        open={flywheelModalOpen}
        onOpenChange={setFlywheelModalOpen}
      />
    </section>
  );
}
