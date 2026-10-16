'use client';

/**
 * High-Density Partner Portfolio Triage Grid (User Story 1, Task T003).
 * Institutional Sovereign Light Mode data table synchronized bi-directionally
 * with the 2D Cartesian Churn Radar scatter canvas.
 * Impeccable Operate craft: high density, monospace tabular numerals, sortable headers, <50ms filtering.
 */

import * as React from 'react';
import { PartnerChurnItem } from '../state/cockpit-types';

export interface PartnerTriageGridProps {
  partners: PartnerChurnItem[];
  selectedPartnerId?: string | null;
  onSelectPartner: (partner: PartnerChurnItem) => void;
  filterQuadrant?: string | null;
  className?: string;
}

type SortField = 'valueAtRiskUsd' | 'pChurn' | 'daysToChurn' | 'partnerId' | 'name' | 'driftVelocityPct';
type SortDirection = 'asc' | 'desc';

export function PartnerTriageGrid({
  partners,
  selectedPartnerId,
  onSelectPartner,
  filterQuadrant,
  className = '',
}: PartnerTriageGridProps) {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [sortField, setSortField] = React.useState<SortField>('valueAtRiskUsd');
  const [sortDirection, setSortDirection] = React.useState<SortDirection>('desc');
  const [riskBand, setRiskBand] = React.useState<'ALL' | 'CRITICAL' | 'HIGH' | 'HIGH_VAR' | 'IMMINENT'>('ALL');

  const counts = React.useMemo(() => ({
    all: partners.length,
    critical: partners.filter((p) => p.pChurn >= 0.7).length,
    high: partners.filter((p) => p.pChurn >= 0.5 && p.pChurn < 0.7).length,
    highVaR: partners.filter((p) => p.valueAtRiskUsd >= 1000000).length,
    imminent: partners.filter((p) => p.daysToChurn <= 30).length,
  }), [partners]);

  // Handle column header sort toggle
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Filtered & sorted partners
  const processedPartners = React.useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    const filtered = partners.filter((p) => {
      // Risk band preset filter
      if (riskBand === 'CRITICAL' && p.pChurn < 0.7) return false;
      if (riskBand === 'HIGH' && (p.pChurn < 0.5 || p.pChurn >= 0.7)) return false;
      if (riskBand === 'HIGH_VAR' && p.valueAtRiskUsd < 1000000) return false;
      if (riskBand === 'IMMINENT' && p.daysToChurn > 30) return false;

      // Quadrant filter if passed from parent
      if (filterQuadrant && filterQuadrant !== 'ALL') {
        const matchesQuadrant =
          (filterQuadrant === 'CRITICAL' && p.pChurn >= 0.70) ||
          (filterQuadrant === 'HIGH' && p.pChurn >= 0.50 && p.pChurn < 0.70) ||
          (filterQuadrant === 'MONITOR' && p.pChurn >= 0.30 && p.pChurn < 0.50) ||
          (filterQuadrant === 'HEALTHY' && p.pChurn < 0.30);
        if (!matchesQuadrant) return false;
      }

      if (!q) return true;
      return (
        p.partnerId.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        (p.region && p.region.toLowerCase().includes(q)) ||
        (p.cohort && p.cohort.toLowerCase().includes(q)) ||
        (p.primaryDriver && p.primaryDriver.toLowerCase().includes(q))
      );
    });

    return [...filtered].sort((a, b) => {
      let valA: number | string = 0;
      let valB: number | string = 0;

      switch (sortField) {
        case 'valueAtRiskUsd':
          valA = a.valueAtRiskUsd;
          valB = b.valueAtRiskUsd;
          break;
        case 'pChurn':
          valA = a.pChurn;
          valB = b.pChurn;
          break;
        case 'daysToChurn':
          valA = a.daysToChurn;
          valB = b.daysToChurn;
          break;
        case 'driftVelocityPct':
          valA = a.historicalDrift?.driftVelocityPct ?? 0;
          valB = b.historicalDrift?.driftVelocityPct ?? 0;
          break;
        case 'partnerId':
          valA = a.partnerId;
          valB = b.partnerId;
          break;
        case 'name':
          valA = a.name;
          valB = b.name;
          break;
      }

      if (typeof valA === 'string' && typeof valB === 'string') {
        return sortDirection === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortDirection === 'asc' ? Number(valA) - Number(valB) : Number(valB) - Number(valA);
    });
  }, [partners, searchQuery, sortField, sortDirection, filterQuadrant]);

  const totalFilteredVaR = React.useMemo(() => {
    return processedPartners.reduce((acc, p) => acc + p.valueAtRiskUsd, 0);
  }, [processedPartners]);

  return (
    <div
      className={`flex flex-col h-full bg-white border border-slate-200 rounded-sm shadow-xs overflow-hidden ${className}`}
      data-testid="partner-triage-grid"
    >
      {/* Triage Search & Filter Toolbar */}
      <div className="p-3 bg-slate-50 border-b border-slate-200 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <input
              type="text"
              role="searchbox"
              aria-label="Filter partners by ID, name, region, or driver"
              placeholder="Search partners, regions, cohorts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-300 rounded-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700 focus:border-blue-700"
            />
            <svg
              className="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 text-xs cursor-pointer"
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-3 text-label font-mono text-slate-500">
            <span>
              SHOWING <strong className="text-slate-800">{processedPartners.length}</strong> / {partners.length}
            </span>
            <span className="text-slate-300">|</span>
            <span>
              TOTAL VaR <strong className="text-slate-800">${(totalFilteredVaR / 1000).toFixed(0)}K</strong>
            </span>
          </div>
        </div>

        {/* Quick Cohort & Risk Presets */}
        <div className="flex flex-wrap items-center gap-1.5 font-mono text-label pt-0.5">
          <span className="text-slate-400 text-label uppercase font-bold mr-1">Filter Preset:</span>
          {[
            { id: 'ALL', label: `ALL (${counts.all})` },
            { id: 'CRITICAL', label: `CRITICAL ≥70% (${counts.critical})` },
            { id: 'HIGH', label: `HIGH 50-70% (${counts.high})` },
            { id: 'HIGH_VAR', label: `VaR >$1M (${counts.highVaR})` },
            { id: 'IMMINENT', label: `IMMINENT ≤30D (${counts.imminent})` },
          ].map((b) => (
            <button
              key={b.id}
              type="button"
              onClick={() => setRiskBand(b.id as any)}
              className={`px-2 py-0.5 border text-label transition-colors cursor-pointer ${
                riskBand === b.id
                  ? 'bg-slate-900 border-slate-900 text-white font-bold shadow-2xs'
                  : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
              }`}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table Body with Fixed Header */}
      <div className="flex-1 overflow-auto max-h-[520px]">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-slate-100 text-slate-600 text-label font-mono uppercase tracking-wider border-b border-slate-200 select-none">
            <tr>
              <th
                onClick={() => handleSort('partnerId')}
                className="py-2 px-3 font-semibold cursor-pointer hover:bg-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1">
                  Partner / Introducer
                  {sortField === 'partnerId' && (sortDirection === 'asc' ? ' ↑' : ' ↓')}
                </div>
              </th>
              <th className="py-2 px-3 font-semibold">Region / Cohort</th>
              <th
                onClick={() => handleSort('valueAtRiskUsd')}
                className="py-2 px-3 font-semibold text-right cursor-pointer hover:bg-slate-200 transition-colors"
              >
                <div className="flex items-center justify-end gap-1">
                  30D VaR
                  {sortField === 'valueAtRiskUsd' && (sortDirection === 'asc' ? ' ↑' : ' ↓')}
                </div>
              </th>
              <th
                onClick={() => handleSort('pChurn')}
                className="py-2 px-3 font-semibold text-center cursor-pointer hover:bg-slate-200 transition-colors"
              >
                <div className="flex items-center justify-center gap-1">
                  P(churn)
                  {sortField === 'pChurn' && (sortDirection === 'asc' ? ' ↑' : ' ↓')}
                </div>
              </th>
              <th
                onClick={() => handleSort('daysToChurn')}
                className="py-2 px-3 font-semibold text-center cursor-pointer hover:bg-slate-200 transition-colors"
              >
                <div className="flex items-center justify-center gap-1">
                  Deadline
                  {sortField === 'daysToChurn' && (sortDirection === 'asc' ? ' ↑' : ' ↓')}
                </div>
              </th>
              <th
                onClick={() => handleSort('driftVelocityPct')}
                className="py-2 px-3 font-semibold text-center cursor-pointer hover:bg-slate-200 transition-colors"
              >
                <div className="flex items-center justify-center gap-1">
                  Drift Trend
                  {sortField === 'driftVelocityPct' && (sortDirection === 'asc' ? ' ↑' : ' ↓')}
                </div>
              </th>
              <th className="py-2 px-3 font-semibold">Primary Driver</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {processedPartners.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400 italic">
                  No partners match the current search query or quadrant filter.
                </td>
              </tr>
            ) : (
              processedPartners.map((partner) => {
                const isSelected = selectedPartnerId === partner.partnerId;
                const isCritical = partner.pChurn >= 0.70;
                const isHigh = partner.pChurn >= 0.50 && partner.pChurn < 0.70;

                const statusColor = isCritical
                  ? 'text-red-700 bg-red-50 border-red-200'
                  : isHigh
                  ? 'text-amber-800 bg-amber-50 border-amber-200'
                  : 'text-green-700 bg-green-50 border-green-200';

                const tierBadgeColor =
                  partner.tier === 'TIER_1_SUPER'
                    ? 'bg-blue-50 text-blue-800 border-blue-200'
                    : partner.tier === 'TIER_2_MASTER'
                    ? 'bg-blue-50 text-blue-800 border-blue-200'
                    : 'bg-slate-100 text-slate-700 border-slate-200';

                return (
                  <tr
                    key={partner.partnerId}
                    onClick={() => onSelectPartner(partner)}
                    className={`cursor-pointer transition-colors duration-150 ${
                      isSelected
                        ? 'bg-blue-50/80 font-medium border-l-2 border-l-blue-700'
                        : 'hover:bg-slate-50/90'
                    }`}
                    data-testid={`triage-row-${partner.partnerId}`}
                  >
                    {/* Partner ID & Name */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-slate-800">
                          {partner.partnerId}
                        </span>
                        <span
                          className={`text-label font-mono px-1 py-0.2 rounded-2xs border ${tierBadgeColor}`}
                        >
                          {partner.tier === 'TIER_1_SUPER'
                            ? 'T1'
                            : partner.tier === 'TIER_2_MASTER'
                            ? 'T2'
                            : 'T3'}
                        </span>
                      </div>
                      <div className="text-label text-slate-500 truncate max-w-[170px]" title={partner.name}>
                        {partner.name}
                      </div>
                    </td>

                    {/* Region / Cohort */}
                    <td className="py-2.5 px-3">
                      <div className="text-label text-slate-700 font-medium truncate max-w-[140px]">
                        {partner.region || 'Global'}
                      </div>
                      <div className="text-label text-slate-400 truncate max-w-[140px]">
                        {partner.cohort || 'General'}
                      </div>
                    </td>

                    {/* 30D VaR */}
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-800 tabular-nums">
                      ${(partner.valueAtRiskUsd / 1000).toLocaleString('en-US', { maximumFractionDigits: 0 })}K
                    </td>

                    {/* P(churn) */}
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded-2xs text-label font-mono font-bold border ${statusColor}`}
                      >
                        {(partner.pChurn * 100).toFixed(0)}%
                      </span>
                    </td>

                    {/* Days to Churn Deadline */}
                    <td className="py-2.5 px-3 text-center font-mono text-label tabular-nums">
                      <span
                        className={
                          partner.daysToChurn <= 14
                            ? 'text-red-700 font-bold'
                            : partner.daysToChurn <= 30
                            ? 'text-amber-700 font-semibold'
                            : 'text-slate-600'
                        }
                      >
                        {partner.daysToChurn}d
                      </span>
                    </td>

                    {/* Drift Trend */}
                    <td className="py-2.5 px-3 text-center font-mono text-label tabular-nums">
                      {partner.historicalDrift?.driftVelocityPct !== undefined && partner.historicalDrift.driftVelocityPct !== 0 ? (
                        <span className={partner.historicalDrift.driftVelocityPct > 0 ? 'text-red-600 font-medium' : 'text-green-700 font-medium'}>
                          {partner.historicalDrift.driftVelocityPct > 0
                            ? `+${partner.historicalDrift.driftVelocityPct.toFixed(0)}%`
                            : `${partner.historicalDrift.driftVelocityPct.toFixed(0)}%`}
                        </span>
                      ) : (
                        <span className="text-slate-400 font-normal">—</span>
                      )}
                    </td>

                    {/* Primary Driver */}
                    <td className="py-2.5 px-3 text-label text-slate-600 truncate max-w-[180px]">
                      {partner.primaryDriver ? (
                        <span className="inline-flex items-center gap-1">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isCritical ? 'bg-red-500' : isHigh ? 'bg-amber-500' : 'bg-slate-400'
                            }`}
                          />
                          {partner.primaryDriver.replace(/_/g, ' ')}
                        </span>
                      ) : (
                        partner.primaryRootCause || 'Unclassified'
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
