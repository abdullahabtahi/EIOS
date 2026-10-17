'use client';

/**
 * Partner churn hazard radar (spec 032): 30-day hazard against 30-day referred volume for every scored partner,
 * with the hazard path at t-30 and t-14, the cohort the cohort test found, and an inspector over computed fields.
 * Deals and the cohort playbook stage through the intent hub; nothing on this chart is filled in client-side.
 */

import { spreadEdgeTies, visibleLabelIds } from './radar-labels';
import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { PartnerChurnItem, WhatIfCausalResponse } from '../state/cockpit-types';
import { PartnerTriageGrid } from './partner-triage-grid';
import { fetchChurnRadar, simulatePartnerWhatIf } from '../state/api-bridge';
import { MOCK_PARTNERS } from '../state/fixtures';
import { type CohortSignal, fetchCohorts, partnersFromCanvas, toPartnerItem } from '../state/partner-radar';
import { PartnerRadarInspector } from './partner-radar-inspector';
import { useStageRequest } from './use-stage-request';

const MAX_RADAR_LABELS = 12;
const AXIS_FRACTIONS = [0, 0.25, 0.5, 0.75, 1] as const;
/** Value-axis gridlines in the sqrt scale's own units (value = max * t^2). */
const Y_TICKS = [0.25, 0.5, 0.75, 1] as const;

function xTickLabel(axis: string, f: number): string {
  if (axis === 'VELOCITY') return `${f === 0 ? 0 : -Math.round(f * 100)}%`;
  if (axis === 'DAYS_TO_CHURN') return `${Math.round(180 * (1 - f))}d`;
  return f.toFixed(2);
}
export { MOCK_PARTNERS };

type FilterMode = 'ALL' | 'CRITICAL' | 'STABLE';
type AxisDimension = 'P_CHURN' | 'VELOCITY' | 'DAYS_TO_CHURN';
type ViewMode = 'INDIVIDUAL' | 'COHORT';

export function ChurnRadarScatter() {
  const { state, selectEntity } = useCockpit();

  // The radar the workstation payload carries (engine plane), refreshed from the radar endpoint. Sample partners
  // are only for the fixture plane; an engine-backed screen never shows them.
  const [partners, setPartners] = React.useState<PartnerChurnItem[]>(
    () => partnersFromCanvas(state.canvasPayload) ?? (state.dataOrigin === 'engine' ? [] : MOCK_PARTNERS),
  );
  const [cohorts, setCohorts] = React.useState<CohortSignal[]>([]);
  const cohort = cohorts[0] ?? null;
  const cohortStaging = useStageRequest();
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [filterMode, setFilterMode] = React.useState<FilterMode>('ALL');
  const [axisDimension, setAxisDimension] = React.useState<AxisDimension>('P_CHURN');
  const [viewMode, setViewMode] = React.useState<ViewMode>('INDIVIDUAL');
  const [hoveredPartner, setHoveredPartner] = React.useState<PartnerChurnItem | null>(null);
  const [showAllTrails, setShowAllTrails] = React.useState<boolean>(false);
  const [toastMessage, setToastMessage] = React.useState<string | null>(null);

  // Counterfactual What-If Simulator state (0 to 100% concession intensity)
  const [concessionSlider, setConcessionSlider] = React.useState<number>(0);
  const [isSimulatingCausal, setIsSimulatingCausal] = React.useState<boolean>(false);
  const [whatIfResponse, setWhatIfResponse] = React.useState<WhatIfCausalResponse | null>(null);

  // Hydrate live partners via API bridge & subscribe to SSE stream
  React.useEffect(() => {
    let isMounted = true;

    async function loadRadar() {
      const liveData = await fetchChurnRadar();
      if (isMounted && Array.isArray(liveData?.partners) && liveData.partners.length) {
        setPartners(liveData.partners.map(toPartnerItem));
      }
      const found = await fetchCohorts();
      if (isMounted) setCohorts(found);
    }

    void loadRadar();

    return () => {
      isMounted = false;
    };
  }, []);

  // Synchronize active selection with Cockpit context
  const matchedPartner = React.useMemo(() => {
    const activeId = state.activeEntityId;
    if (activeId) {
      const found = partners.find(
        (p) => p.partnerId === activeId || p.partnerId.includes(activeId) || activeId.includes(p.partnerId)
      );
      if (found) return found;
    }
    return partners[0];
  }, [state.activeEntityId, partners]);

  const [localSelectedPartner, setLocalSelectedPartner] = React.useState<PartnerChurnItem | null>(null);
  const selectedPartner = state.activeEntityId ? matchedPartner : (localSelectedPartner ?? matchedPartner);

  // Debounced live counterfactual evaluation query (250ms)
  React.useEffect(() => {
    if (concessionSlider === 0 || !selectedPartner) {
      setWhatIfResponse(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSimulatingCausal(true);
      try {
        const prompt = `Simulate VIP Concession Deal (intensity: ${concessionSlider}%) for partner ${selectedPartner.partnerId}`;
        setWhatIfResponse(await simulatePartnerWhatIf(selectedPartner.partnerId, prompt));
      } finally {
        setIsSimulatingCausal(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [concessionSlider, selectedPartner?.partnerId]); // eslint-disable-line react-hooks/exhaustive-deps

  const displayedPartners = React.useMemo(() => {
    return partners.filter((p) => {
      if (filterMode === 'CRITICAL') return p.pChurn >= 0.5;
      if (filterMode === 'STABLE') return p.pChurn < 0.5;
      return true;
    });
  }, [partners, filterMode]);

  const activeFocusPartner = hoveredPartner || selectedPartner;

  // Keyboard shortcut listener: ESC exits studio, F toggles studio
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false);
      if (e.key.toLowerCase() === 'f' && !['input', 'textarea'].includes((e.target as HTMLElement)?.tagName?.toLowerCase())) {
        setIsFullscreen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  // The cohort playbook the backend priced for the cohort the cohort test found, staged through the intent hub.
  const handleStageCohortBatch = () => {
    if (cohort?.stageRequest) void cohortStaging.stage(cohort.stageRequest);
  };

  // Value axis: square-root scale up to the largest volume on the chart; the divider is the backend's high-value
  // line (the top quarter of 30-day volume), so a dot's quadrant here is the quadrant the backend assigned.
  const valueScale = React.useMemo(() => {
    const values = partners.flatMap((p) => [
      p.valueAtRiskUsd,
      p.historicalDrift?.tMinus30d.valueAtRiskUsd ?? 0,
      p.historicalDrift?.tMinus14d.valueAtRiskUsd ?? 0,
    ]);
    const sorted = partners.map((p) => p.valueAtRiskUsd).sort((a, b) => a - b);
    const line = sorted.length ? sorted[Math.floor(sorted.length * 0.75)] : 0;
    return { max: Math.max(1, ...values), line };
  }, [partners]);
  const normValue = (v: number) => Math.min(1, Math.max(0, Math.sqrt(Math.max(v, 0) / valueScale.max)));
  const compactUsd = (v: number) => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : `$${Math.round(v / 1e3)}K`);

  // Helper to calculate SVG coordinates for partners
  const getCoordinates = (p: PartnerChurnItem, width: number, height: number) => {
    const leftPad = 55;
    const rightPad = width - 35;
    const topPad = 25;
    const bottomPad = height - 52;
    const plotWidth = rightPad - leftPad;
    const plotHeight = bottomPad - topPad;

    let normX = p.pChurn;
    if (axisDimension === 'VELOCITY') {
      normX = Math.min(1, Math.max(0, Math.abs(Math.min(p.loginDecayPct ?? 0, 0)) / 100));
    } else if (axisDimension === 'DAYS_TO_CHURN') {
      normX = Math.max(0, Math.min(1, 1 - p.daysToChurn / 180));
    }

    const normY = normValue(p.valueAtRiskUsd);
    const cx = leftPad + spreadEdgeTies(normX, p.partnerId) * plotWidth;
    const cy = bottomPad - normY * plotHeight;
    return { cx, cy, normX, normY, leftPad, rightPad, topPad, bottomPad, plotWidth, plotHeight };
  };

  // Simulated coordinate when What-If concession slider is applied
  const getSimulatedCoordinates = (p: PartnerChurnItem, width: number, height: number) => {
    const base = getCoordinates(p, width, height);
    const liftPct = (whatIfResponse?.projected_retention_lift_pct ?? p.projectedLiftPct ?? 18.5) / 100;
    const reduction = liftPct * (concessionSlider / 100);
    const simPChurn = Math.max(0, p.pChurn * (1 - reduction));
    const simNormX = axisDimension === 'P_CHURN' ? simPChurn : Math.max(0, base.normX * (1 - reduction));
    const simCx = base.leftPad + simNormX * base.plotWidth;

    return { ...base, simCx, simPChurn };
  };

  // SVG Canvas Dimension Config
  const svgWidth = isFullscreen ? 880 : 760;
  const svgHeight = isFullscreen ? 400 : 420;

  // Render Core SVG Radar Canvas
  const renderSvgCanvas = () => {
    const { leftPad, rightPad, topPad, bottomPad, plotWidth, plotHeight } = getCoordinates(
      selectedPartner,
      svgWidth,
      svgHeight
    );
    const midX = leftPad + plotWidth * 0.5;
    const valueY = bottomPad - normValue(valueScale.line) * plotHeight;
    const midY = valueY;

    // The cohort the backend's cohort test found
    const latAmNodes = displayedPartners.filter((p) => cohort?.partnerIds.includes(p.partnerId));
    const latAmCoords = latAmNodes.map((p) => getCoordinates(p, svgWidth, svgHeight));

    // Label only what fits: the selected and hovered node always, then by value at risk.
    // Overlapping labels stay hidden until the node is hovered.
    const labelIds = visibleLabelIds(
      displayedPartners.map((p) => {
        const { cx, cy } = getCoordinates(p, svgWidth, svgHeight);
        return { id: p.partnerId, cx, cy, side: p.pChurn > 0.8 ? 'end' : 'start', priority: p.valueAtRiskUsd } as const;
      }),
      new Set([selectedPartner.partnerId, ...(hoveredPartner ? [hoveredPartner.partnerId] : [])]),
      [],
      MAX_RADAR_LABELS,
    );

    return (
      <svg className="w-full h-full" viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
        <defs>
          <pattern id="radarGridLight" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(100, 116, 139, 0.08)" strokeWidth="1" />
          </pattern>
          <linearGradient id="trajectoryGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#94A3B8" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#106ba3" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {/* Canvas Background */}
        <rect width={svgWidth} height={svgHeight} fill="none" />
        <g stroke="rgba(100, 116, 139, 0.12)" strokeWidth="1">
          {AXIS_FRACTIONS.map((f) => (
            <line key={`gx-${f}`} x1={leftPad + f * plotWidth} y1={topPad} x2={leftPad + f * plotWidth} y2={bottomPad} />
          ))}
          {Y_TICKS.map((t) => (
            <line key={`gy-${t}`} x1={leftPad} y1={bottomPad - t * plotHeight} x2={rightPad} y2={bottomPad - t * plotHeight} />
          ))}
        </g>

        {/* Quadrant Shaded Zones */}
        <rect x={midX} y={topPad} width={rightPad - midX} height={midY - topPad} fill="rgba(168, 42, 42, 0.04)" />
        <rect x={leftPad} y={topPad} width={midX - leftPad} height={midY - topPad} fill="rgba(100, 116, 139, 0.02)" />
        <rect x={midX} y={midY} width={rightPad - midX} height={bottomPad - midY} fill="rgba(100, 116, 139, 0.02)" />
        <rect x={leftPad} y={midY} width={midX - leftPad} height={bottomPad - midY} fill="rgba(100, 116, 139, 0.02)" />

        {/* Quadrant Divider Axis Lines */}
        <line x1={midX} y1={topPad - 5} x2={midX} y2={bottomPad + 5} stroke="#CBD5E1" strokeWidth="1.5" strokeDasharray="4,4" />
        <line x1={leftPad - 10} y1={midY} x2={rightPad + 10} y2={midY} stroke="#CBD5E1" strokeWidth="1.5" strokeDasharray="4,4" />

        {/* Quadrant Semantic Labels */}
        <text x={midX + 10} y={topPad - 9} fill="#8f2323" fontSize="10" fontFamily="monospace" fontWeight="bold">
          HIGH VALUE / HIGH DISENGAGEMENT RISK
        </text>
        <text x={leftPad + 10} y={topPad - 9} fill="#64748B" fontSize="10" fontFamily="monospace" fontWeight="bold">
          HIGH VALUE / STABLE GIANTS
        </text>
        <text x={midX + 10} y={bottomPad + 29} fill="#64748B" fontSize="10" fontFamily="monospace" fontWeight="bold">
          LOW VALUE / HIGH RISK
        </text>
        <text x={leftPad + 10} y={bottomPad + 29} fill="#64748B" fontSize="10" fontFamily="monospace" fontWeight="bold">
          LOW VALUE / STABLE
        </text>

        {/* Coordinate Axis Reference Ticks */}
        <g fontSize="10" fontFamily="monospace" fill="#64748B">
          {AXIS_FRACTIONS.map((f) => (
            <text key={`tx-${f}`} x={leftPad + f * plotWidth} y={bottomPad + 14} textAnchor="middle">
              {xTickLabel(axisDimension, f)}
            </text>
          ))}
          {Y_TICKS.filter((t) => Math.abs(bottomPad - t * plotHeight - valueY) > 11 && t < 1).map((t) => (
            <text key={`ty-${t}`} x={leftPad - 6} y={bottomPad - t * plotHeight + 3} textAnchor="end">
              {compactUsd(valueScale.max * t * t)}
            </text>
          ))}
          <text x={leftPad - 6} y={topPad + 4} textAnchor="end">{compactUsd(valueScale.max)}</text>
          <text x={leftPad - 6} y={valueY + 3} textAnchor="end">{compactUsd(valueScale.line)}</text>
          <text x={leftPad - 6} y={bottomPad + 2} textAnchor="end">$0</text>
        </g>

        {/* COHORT CLUSTER OVERLAY */}
        {viewMode === 'COHORT' && latAmCoords.length >= 2 && (() => {
          const xs = latAmCoords.map((c) => c.cx);
          const ys = latAmCoords.map((c) => c.cy);
          const minX = Math.min(...xs) - 25;
          const maxX = Math.max(...xs) + 25;
          const minY = Math.min(...ys) - 20;
          const maxY = Math.max(...ys) + 20;
          const cx = (minX + maxX) / 2;
          const cy = (minY + maxY) / 2;
          const rx = (maxX - minX) / 2;
          const ry = (maxY - minY) / 2;

          return (
            <g pointerEvents="none" className="animate-in fade-in duration-300">
              <ellipse
                cx={cx}
                cy={cy}
                rx={Math.max(rx, 50)}
                ry={Math.max(ry, 35)}
                fill="rgba(225, 29, 72, 0.05)"
                stroke="#a82a2a"
                strokeWidth="1.5"
                strokeDasharray="4,4"
              />
              <rect x={cx - 110} y={Math.max(topPad + 14, minY + 6)} width="220" height="15" fill="#faf3f3" stroke="#ebc9c9" strokeWidth="0.8" rx="1" />
              <text x={cx} y={Math.max(topPad + 14, minY + 6) + 11} fill="#761f1f" fontSize="10" fontFamily="monospace" fontWeight="bold" textAnchor="middle">
                {cohort ? `${cohort.region} cohort: ${cohort.partnerCount} partners, ${compactUsd(cohort.valueAtRiskUsd)} volume` : ''}
              </text>
            </g>
          );
        })()}

        {/* HISTORICAL DRIFT TRAJECTORIES (Task T006) */}

        {/* Active Focus Partner Crosshair Guide Lines */}
        {activeFocusPartner && (() => {
          const { cx, cy } = getCoordinates(activeFocusPartner, svgWidth, svgHeight);
          return (
            <g pointerEvents="none">
              <line x1={cx} y1={topPad} x2={cx} y2={bottomPad + 5} stroke="#106ba3" strokeWidth="1" strokeDasharray="2,2" opacity="0.6" />
              <line x1={leftPad - 10} y1={cy} x2={rightPad} y2={cy} stroke="#106ba3" strokeWidth="1" strokeDasharray="2,2" opacity="0.6" />
              {/* Coordinate indicator pills */}
              <rect x={cx - 32} y={bottomPad + 5} width="64" height="13" fill="#0F172A" rx="1" />
              <text x={cx} y={bottomPad + 14} fill="#FFFFFF" fontSize="10" fontFamily="monospace" textAnchor="middle">
                {axisDimension === 'P_CHURN'
                  ? `Risk ${activeFocusPartner.pChurn.toFixed(2)}`
                  : axisDimension === 'VELOCITY'
                  ? `Decay: ${activeFocusPartner.loginDecayPct}%`
                  : `Urgency: ${activeFocusPartner.daysToChurn}d`}
              </text>
              <rect x={leftPad - 50} y={cy - 6} width="44" height="12" fill="#0F172A" rx="1" />
              <text x={leftPad - 28} y={cy + 3} fill="#FFFFFF" fontSize="10" fontFamily="monospace" textAnchor="middle">
                ${(activeFocusPartner.valueAtRiskUsd / 1000).toFixed(0)}K
              </text>
            </g>
          );
        })()}

        {/* Counterfactual What-If Trajectory Arrow (Live Simulator) */}
        {concessionSlider > 0 && activeFocusPartner && (() => {
          const base = getCoordinates(activeFocusPartner, svgWidth, svgHeight);
          const sim = getSimulatedCoordinates(activeFocusPartner, svgWidth, svgHeight);
          return (
            <g pointerEvents="none" className="animate-in fade-in duration-200">
              <line
                x1={base.cx}
                y1={base.cy}
                x2={sim.simCx}
                y2={base.cy}
                stroke="url(#trajectoryGrad)"
                strokeWidth="2.5"
                strokeDasharray="3,3"
              />
              <circle cx={sim.simCx} cy={base.cy} r={10} fill="rgba(14, 92, 138, 0.15)" stroke="#0e5c8a" strokeWidth="1.8" />
              <circle cx={sim.simCx} cy={base.cy} r={4} fill="#0e5c8a" />
              <rect x={sim.simCx - 57} y={base.cy - 20} width="114" height="14" fill="#0e5c8a" rx="2" />
              <text x={sim.simCx} y={base.cy - 10} fill="#FFFFFF" fontSize="10" fontFamily="monospace" fontWeight="bold" textAnchor="middle">
                Risk (sim) = {sim.simPChurn.toFixed(2)}
              </text>
            </g>
          );
        })()}

        {/* Plotted Partner Nodes */}
        {displayedPartners.map((p) => {
          const { cx, cy } = getCoordinates(p, svgWidth, svgHeight);
          const isSelected = selectedPartner.partnerId === p.partnerId;
          const isHovered = hoveredPartner?.partnerId === p.partnerId;
          const isCritical = p.pChurn >= 0.5;

          return (
            <g
              key={p.partnerId}
              className="cursor-pointer group"
              onMouseEnter={() => setHoveredPartner(p)}
              onMouseLeave={() => setHoveredPartner(null)}
              onClick={() => {
                setLocalSelectedPartner(p);
                selectEntity(p.partnerId);
              }}
              data-testid={`radar-node-${p.partnerId}`}
            >
              <title>{`${p.name} (${p.partnerId}) · risk ${p.pChurn.toFixed(2)} · value at risk $${Math.round(p.valueAtRiskUsd / 1000)}K`}</title>
              {/* PELT Decay Pulse Halo */}
              {p.changePointDetected && (isSelected || isHovered) && (
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected ? 16 : 11}
                  fill="none"
                  stroke={isCritical ? '#a82a2a' : '#64748B'}
                  strokeWidth="1.2"
                  strokeDasharray="3,3"
                  opacity="0.75"
                  className="animate-pulse"
                />
              )}

              {/* Marker: a small translucent dot so overlaps read as density; the full ring marks only the selected or hovered node */}
              {isSelected || isHovered ? (
                <>
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSelected ? 8.5 : 7}
                    fill="#FFFFFF"
                    stroke={isSelected ? '#106ba3' : isCritical ? '#a82a2a' : '#64748B'}
                    strokeWidth={isSelected ? 2.5 : 1.8}
                  />
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSelected ? 4.5 : 3.5}
                    fill={isSelected ? '#106ba3' : isCritical ? '#a82a2a' : '#64748B'}
                  />
                </>
              ) : (
                <circle
                  cx={cx}
                  cy={cy}
                  r={3.6}
                  fill={isCritical ? '#a82a2a' : '#64748B'}
                  fillOpacity={0.7}
                  stroke="#FFFFFF"
                  strokeWidth={0.8}
                />
              )}

            </g>
          );
        })}

        {/* Trajectory: drawn above the nodes so the path and its T-30d / T-14d markers stay legible in a dense cluster */}
        {displayedPartners.map((p) => {
          const isSelected = selectedPartner.partnerId === p.partnerId;
          const isHovered = hoveredPartner?.partnerId === p.partnerId;
          const shouldRenderTrail = (isSelected || isHovered || (showAllTrails && p.pChurn >= 0.5)) && p.historicalDrift;

          if (!shouldRenderTrail || !p.historicalDrift) return null;

          const currentCoord = getCoordinates(p, svgWidth, svgHeight);
          const coord30 = {
            cx: leftPad + p.historicalDrift.tMinus30d.pChurn * plotWidth,
            cy: bottomPad - normValue(p.historicalDrift.tMinus30d.valueAtRiskUsd) * plotHeight,
          };
          const coord14 = {
            cx: leftPad + p.historicalDrift.tMinus14d.pChurn * plotWidth,
            cy: bottomPad - normValue(p.historicalDrift.tMinus14d.valueAtRiskUsd) * plotHeight,
          };

          return (
            <g key={`drift-${p.partnerId}`} pointerEvents="none" className="animate-in fade-in duration-200">
              {/* Dotted Trail Path: T-30d -> T-14d -> T-0d */}
              <polyline
                points={`${coord30.cx},${coord30.cy} ${coord14.cx},${coord14.cy} ${currentCoord.cx},${currentCoord.cy}`}
                fill="none"
                stroke={isSelected ? '#106ba3' : '#94A3B8'}
                strokeWidth={isSelected ? '2' : '1.2'}
                strokeDasharray="3,3"
              />

              {/* T-30d Origin Breadcrumb */}
              <circle cx={coord30.cx} cy={coord30.cy} r="3.5" fill="#64748B" stroke="#FFFFFF" strokeWidth="1.2" />
              <text x={coord30.cx} y={coord30.cy - 8} fill="#475569" fontSize="10" fontFamily="monospace" fontWeight="bold" textAnchor="middle" stroke="#FFFFFF" strokeWidth="3" paintOrder="stroke fill">
                T-30d
              </text>

              {/* T-14d Mid-Point Breadcrumb */}
              <circle cx={coord14.cx} cy={coord14.cy} r="4" fill="#475569" stroke="#FFFFFF" strokeWidth="1.2" />
              <text x={coord14.cx} y={coord14.cy - 8} fill="#475569" fontSize="10" fontFamily="monospace" fontWeight="bold" textAnchor="middle" stroke="#FFFFFF" strokeWidth="3" paintOrder="stroke fill">
                T-14d
              </text>

              {/* Directional Velocity Vector Chevron */}
              <circle cx={currentCoord.cx} cy={currentCoord.cy} r="12" fill="none" stroke="#a82a2a" strokeWidth="0.8" opacity="0.4" />
            </g>
          );
        })}

        {/* Node labels: drawn above every node so a neighbouring marker never covers one */}
        {displayedPartners
          .filter((p) => labelIds.has(p.partnerId))
          .map((p) => {
            const { cx, cy } = getCoordinates(p, svgWidth, svgHeight);
            const isSelected = selectedPartner.partnerId === p.partnerId;
            const isHovered = hoveredPartner?.partnerId === p.partnerId;
            return (
              <g key={`label-${p.partnerId}`} pointerEvents="none">
                <text
                    x={cx + (p.pChurn > 0.8 ? -10 : 10)}
                    y={cy + 3.5}
                    fill={isSelected ? '#0e5c8a' : '#0F172A'}
                    fontSize={isSelected || isHovered ? '9.5' : '8.5'}
                    fontFamily="monospace"
                    fontWeight={isSelected || isHovered ? 'bold' : '600'}
                    textAnchor={p.pChurn > 0.8 ? 'end' : 'start'}
                    stroke="#F8FAFC"
                    strokeWidth="3"
                    paintOrder="stroke fill"
                  >
                    {p.partnerId}
                  </text>
              </g>
            );
          })}

        {/* Dynamic Axis Description */}
        <text x={svgWidth / 2} y={svgHeight - 10} fill="#475569" fontSize="10" fontFamily="monospace" fontWeight="600" textAnchor="middle">
          {axisDimension === 'P_CHURN'
            ? 'Disengagement risk score → (0.00 to 1.00)'
            : axisDimension === 'VELOCITY'
            ? 'Engagement Decay Rate (60d baseline) → (-100% to 0%)'
            : 'Intervention Urgency (180d down to 0d) →'}
        </text>
        <text x="14" y={svgHeight / 2} fill="#475569" fontSize="10" fontFamily="monospace" fontWeight="600" transform={`rotate(-90 14 ${svgHeight / 2})`} textAnchor="middle">
          Value at Risk (VaR) →
        </text>
      </svg>
    );
  };

  // Diagnostic inspector over the selected partner's computed fields
  const renderDiagnosticInspector = () => (
    <PartnerRadarInspector
      partner={selectedPartner}
      concession={concessionSlider}
      onConcession={setConcessionSlider}
      simulating={isSimulatingCausal}
      whatIf={whatIfResponse}
    />
  );

  if (!selectedPartner) {
    return (
      <p className="p-4 text-xs text-cx-muted bg-white border border-cx-line">
        No partners are scored yet. The radar fills when the partner engine has run.
      </p>
    );
  }

  // FULLSCREEN STUDIO VIEW (Institutional Analytical Studio)
  if (isFullscreen) {
    return (
      <div
        id="churn-radar-fullscreen-theater"
        className="fixed inset-0 z-50 bg-cx-wash flex flex-col overflow-hidden animate-in fade-in duration-200 select-none text-slate-900"
      >
        {/* Studio Top Control Ribbon */}
        <div className="px-4 py-2.5 bg-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 shadow-xs shrink-0">
          <div className="flex items-center gap-3">
            <span className="material-symbols-sharp text-lg text-blue-700">track_changes</span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-900">
                  Partner Disengagement Radar Studio
                </h2>
                <span className="px-1.5 py-0.2 bg-slate-100 border border-slate-300 text-slate-700 text-label font-mono font-bold">
                  INSTITUTIONAL STUDIO GRADE
                </span>
                <span className="px-1.5 py-0.2 bg-green-50 border border-green-200 text-green-800 text-label font-mono font-bold">
                  TLP:AMBER • KMS P-256
                </span>
              </div>
              <span className="text-label font-mono text-slate-500">
                Synchronized 2D Cartesian Risk Space ({partners.length} Monitored Partners · ${(partners.reduce((acc, p) => acc + p.valueAtRiskUsd, 0) / 1000000).toFixed(2)}M Portfolio VaR)
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* View Mode Toggle */}
            <div className="flex items-center border border-slate-200 bg-slate-50 p-0.5 text-label font-mono">
              <button
                type="button"
                onClick={() => setViewMode('INDIVIDUAL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  viewMode === 'INDIVIDUAL' ? 'bg-white shadow-2xs text-slate-900' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                NODES ({partners.length})
              </button>
              <button
                type="button"
                onClick={() => setViewMode('COHORT')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  viewMode === 'COHORT' ? 'bg-red-50 text-red-800 border border-red-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                COHORTS
              </button>
            </div>

            {/* Filter Mode */}
            <div className="flex items-center border border-slate-200 bg-slate-50 p-0.5 text-label font-mono">
              <button
                type="button"
                onClick={() => setFilterMode('ALL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'ALL' ? 'bg-white shadow-2xs text-slate-900' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                ALL ({partners.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('CRITICAL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'CRITICAL' ? 'bg-red-50 text-red-700 border border-red-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                CRITICAL ({partners.filter((p) => p.pChurn >= 0.5).length})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('STABLE')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'STABLE' ? 'bg-green-50 text-green-700 border border-green-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                STABLE ({partners.filter((p) => p.pChurn < 0.5).length})
              </button>
            </div>

            {/* Critical Trails */}
            <label className="flex items-center gap-1.5 text-xs font-mono text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={showAllTrails}
                onChange={(e) => setShowAllTrails(e.target.checked)}
                className="rounded-2xs accent-blue-700"
              />
              <span>Critical Trails</span>
            </label>

            {/* Exit Studio Button */}
            <button
              type="button"
              onClick={() => setIsFullscreen(false)}
              className="px-3 py-1 bg-slate-900 hover:bg-black text-white text-xs font-mono font-bold cursor-pointer flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <span className="material-symbols-sharp text-sm">fullscreen_exit</span>
              <span>Exit (Esc)</span>
            </button>
          </div>
        </div>

        {/* Studio Body: Expansive Canvas + Contextual Diagnostic Inspector Panel (Always Visible) */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* 100% Canvas Area */}
          <div className="flex-1 h-full p-4 flex flex-col justify-between overflow-hidden bg-cx-wash">
            <div className="flex-1 w-full relative min-h-[480px] bg-white border border-slate-200 shadow-2xs overflow-hidden">
              {renderSvgCanvas()}
            </div>
            <div className="mt-2 flex items-center justify-between text-label font-mono text-slate-500 px-1">
              <span>Interactive Nodes: Click node to focus crosshairs and update diagnostic inspector · Hover for rapid telemetry preview</span>
              <span>Press Esc or click Exit Studio to return to Cockpit</span>
            </div>
          </div>

          {/* Diagnostic Inspector Panel (Always Visible in Studio View) */}
          <div className="w-[420px] xl:w-[460px] bg-cx-wash-2 border-l border-slate-200 overflow-y-auto p-4 space-y-3 shrink-0 shadow-xl z-20">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-sm text-cx-accent">tune</span>
                <span className="text-xs font-bold font-mono uppercase text-slate-900">
                  Diagnostic Inspector · {selectedPartner.partnerId}
                </span>
              </div>
            </div>
            {renderDiagnosticInspector()}
          </div>
        </div>
      </div>
    );
  }

  // EMBEDDED VIEW (Standard Workstation Card with Co-Primary Side-by-Side Split)
  return (
    <div className="bg-white border border-slate-200 p-4 shadow-xs space-y-4 relative select-none">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-3 right-3 z-30 text-xs font-mono px-3 py-1.5 shadow-md flex items-center gap-2 bg-green-50 border border-green-500 text-green-800 animate-in fade-in slide-in-from-top-1">
          <span className="material-symbols-sharp text-sm text-green-600">verified</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header & Telemetry Ribbon */}
      <div className="space-y-2.5 border-b border-slate-200 pb-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-blue-700">track_changes</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                Partner Disengagement Radar: risk score × Value at Risk (VaR)
              </h3>
            </div>
            <p className="text-label text-slate-500 mt-0.5">
              Synchronized 2D Cartesian Disengagement Radar with High-Density Portfolio Triage.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Controls: Nodes -> Critical Nodes & Trails (Start Left) */}
          <div className="flex flex-wrap items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center border border-slate-200 bg-slate-50 p-0.5 text-label font-mono">
              <button
                type="button"
                onClick={() => setViewMode('INDIVIDUAL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  viewMode === 'INDIVIDUAL' ? 'bg-white shadow-2xs text-slate-900' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                NODES ({partners.length})
              </button>
              <button
                type="button"
                onClick={() => setViewMode('COHORT')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  viewMode === 'COHORT' ? 'bg-red-50 text-red-800 border border-red-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                COHORTS
              </button>
            </div>

            {/* Segmented Filter */}
            <div className="flex items-center border border-slate-200 bg-slate-50 p-0.5 text-label font-mono">
              <button
                type="button"
                onClick={() => setFilterMode('ALL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'ALL' ? 'bg-white shadow-2xs text-slate-900' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                ALL ({partners.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('CRITICAL')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'CRITICAL' ? 'bg-red-50 text-red-700 border border-red-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                CRITICAL ({partners.filter((p) => p.pChurn >= 0.5).length})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('STABLE')}
                className={`px-2 py-0.5 font-bold cursor-pointer transition-colors ${
                  filterMode === 'STABLE' ? 'bg-green-50 text-green-700 border border-green-200' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                STABLE ({partners.filter((p) => p.pChurn < 0.5).length})
              </button>
            </div>

            {/* Show All Trails Toggle */}
            <label className="hidden sm:flex items-center gap-1 text-label font-mono text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showAllTrails}
                onChange={(e) => setShowAllTrails(e.target.checked)}
                className="rounded-2xs accent-blue-700"
              />
              <span>Critical Trails</span>
            </label>
          </div>

          {/* Fullscreen Studio Trigger (Most Right) */}
          <button
            type="button"
            id="churn-radar-fullscreen-toggle"
            onClick={() => setIsFullscreen(true)}
            className="px-2.5 py-1 text-label font-mono font-bold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300 cursor-pointer flex items-center gap-1 transition-colors ml-auto"
            title="Expand to Fullscreen Studio (Keyboard shortcut: F)"
          >
            <span className="material-symbols-sharp text-sm">fullscreen</span>
            <span>Studio</span>
          </button>
        </div>
      </div>

      {/* Cohort Systemic Risk Banner with 1-Click Batch Remediation (Task T011) */}
      {viewMode === 'COHORT' && (
        <div className="p-3 bg-amber-50 border border-amber-300 text-amber-900 text-xs font-mono flex flex-wrap items-center justify-between gap-3">
          {cohort ? (
            <>
              <div className="flex items-start gap-2">
                <span className="material-symbols-sharp text-base text-amber-600 shrink-0 mt-0.5">warning</span>
                <div>
                  <strong className="block">
                    {cohort.region}: {cohort.partnerCount} partners at high risk together (binomial test p = {cohort.pValue.toFixed(4)})
                  </strong>
                  <span className="text-label text-amber-800">
                    {compactUsd(cohort.valueAtRiskUsd)} of 30-day volume. {cohort.primaryDriver}.
                  </span>
                  {cohortStaging.message && (
                    <span role={cohortStaging.message.tone === 'error' ? 'alert' : 'status'} className="block text-label mt-1">
                      {cohortStaging.message.text}
                    </span>
                  )}
                </div>
              </div>
              {cohort.stageRequest && (
                <button
                  type="button"
                  disabled={cohortStaging.busy}
                  onClick={handleStageCohortBatch}
                  className="px-3 py-1.5 bg-red-700 hover:bg-red-800 text-white font-mono font-bold text-xs rounded-xs cursor-pointer transition-colors shadow-xs shrink-0"
                >
                  Stage a retention playbook for the {cohort.region} cohort
                </button>
              )}
            </>
          ) : (
            <span>No regional cohort is significant at this as-of.</span>
          )}
        </div>
      )}

      {/* 2D Cartesian Churn Radar Canvas (Full Width) */}
      <div className="relative w-full h-[460px] bg-cx-wash border border-slate-200 overflow-hidden select-none">
        {renderSvgCanvas()}
      </div>

      {/* Quick Portfolio Telemetry Bar */}
      <div className="p-3 bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-slate-500 text-label uppercase block">Monitored Portfolio</span>
            <span className="font-bold text-slate-900">{partners.length} Partners</span>
          </div>
          <div>
            <span className="text-slate-500 text-label uppercase block">Critical At-Risk</span>
            <span className="font-bold text-red-700">{partners.filter((p) => p.pChurn >= 0.5).length} Partners</span>
          </div>
          <div>
            <span className="text-slate-500 text-label uppercase block">Total Portfolio VaR</span>
            <span className="font-bold text-slate-900">${(partners.reduce((acc, p) => acc + p.valueAtRiskUsd, 0) / 1000000).toFixed(2)}M USD</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-label">Selected:</span>
          <span className="px-2 py-0.5 bg-white border border-slate-300 font-bold text-slate-900">
            {selectedPartner.name} ({selectedPartner.partnerId})
          </span>
          <span className={`px-1.5 py-0.5 text-label font-bold border ${selectedPartner.pChurn >= 0.5 ? 'bg-red-50 text-red-800 border-red-200' : 'bg-green-50 text-green-800 border-green-200'}`}>
            Risk {selectedPartner.pChurn.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Diagnostic Inspector (Shown by default) */}
      <div id="radar-embedded-inspector" className="block pt-2">
        <div className="bg-cx-wash border border-slate-200 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-sm text-cx-accent">tune</span>
              <span className="text-xs font-bold font-mono uppercase text-slate-800">
                Diagnostic Deep-Dive &amp; What-If Counterfactuals ({selectedPartner.partnerId})
              </span>
            </div>
          </div>
          {renderDiagnosticInspector()}
        </div>
      </div>
    </div>
  );
}
