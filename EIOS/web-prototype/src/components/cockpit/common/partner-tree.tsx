'use client';

/**
 * 3-Tier Sub-Affiliate Tree Visualizer & Mirror Trading Ring Detection
 * Enforces Feature 009 (Sub-affiliate hierarchy tree & mirror trading rings).
 * Detects collusion loops where sub-affiliates extract unearned commissions via
 * tick-level execution alignment (>= 85%).
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { PartnerHierarchyNode } from '../state/cockpit-types';

const MOCK_TREE: PartnerHierarchyNode = {
  partnerId: 'PTR-882',
  name: 'Alpha FX LatAm Master (Tier 1 Super)',
  tierLevel: 1,
  monthlyCommissionUsd: 142390,
  subAffiliatesCount: 14,
  children: [
    {
      partnerId: 'PTR-882-SUB1',
      name: 'Bogota Retail Affiliates (Tier 2)',
      tierLevel: 2,
      monthlyCommissionUsd: 64200,
      subAffiliatesCount: 8,
      children: [
        {
          partnerId: 'PTR-882-C1',
          name: 'Signal Channel A (Tier 3)',
          tierLevel: 3,
          monthlyCommissionUsd: 28100,
          subAffiliatesCount: 0,
        },
        {
          partnerId: 'PTR-882-C2',
          name: 'Signal Channel B (Tier 3)',
          tierLevel: 3,
          monthlyCommissionUsd: 18400,
          subAffiliatesCount: 0,
        },
      ],
    },
    {
      partnerId: 'PTR-882-SUB2',
      name: 'Medellin Algo Trading Desk (Tier 2)',
      tierLevel: 2,
      monthlyCommissionUsd: 48900,
      subAffiliatesCount: 4,
    },
  ],
};

export function PartnerTree() {
  const { stageAction, state, selectEntity } = useCockpit();
  const [collapsedNodes, setCollapsedNodes] = React.useState<Set<string>>(new Set());
  const [toastMessage, setToastMessage] = React.useState<string | null>(null);

  const toggleCollapse = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  const handleStageClawback = () => {
    stageAction({
      intentId: `act_clawback_${Date.now()}`,
      actionType: 'CLAWBACK_COMMISSION',
      targetEntityId: 'PTR-882',
      targetEntityType: 'PARTNER',
      severity: 'HIGH',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      parameters: { partnerId: 'PTR-882', clawbackAmountUsd: 142390, reason: '88% mirror trading collusion correlation' },
      estimatedImpact: 'Clawback $142,390 USD in extracted rebates from master affiliate #882',
      requiresFourEyes: true,
      kmsSignatureBadge: {
        keyId: 'projects/feios-prod/locations/global/keyRings/eios-cockpit/cryptoKeys/action-signer-p256',
        algorithm: 'ECDSA_P256_SHA256',
        signatureDigest: `DIGEST_SIM_${Date.now()}`,
        verified: true,
      },
      fourEyesRecord: {
        initiatorOfficerId: state.operator.officerId,
        initiatorTimestamp: new Date().toISOString(),
        idpClaimValidation: true,
      },
    });

    setToastMessage('Commission Clawback intent staged for PTR-882 (KMS P-256 signed, $142,390 USD)');
    setTimeout(() => setToastMessage(null), 4000);
  };

  return (
    <div className="bg-white border border-slate-200 p-4 shadow-sm space-y-4 relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-3 right-3 z-30 text-xs font-mono px-3 py-1.5 shadow-md flex items-center gap-2 bg-emerald-50 border border-emerald-500 text-emerald-800 animate-in fade-in slide-in-from-top-1">
          <span className="material-symbols-sharp text-sm text-emerald-600">verified</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-blue-600">account_tree</span>
            <h3 className="text-xs font-bold font-mono uppercase tracking-wide text-slate-900">
              3-Tier Sub-Affiliate Hierarchy & Mirror Trading Detection
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Network tracing of multi-level rebate dispersion and collusion rings.
          </p>
        </div>

        <span className="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-300 font-mono text-[10px] font-bold">
          COLLUSION CORRELATION: 0.88 (&ge; 0.85 ALERT)
        </span>
      </div>

      {/* Mirror Trading Ring Alert Callout */}
      <div className="p-3 bg-rose-50/80 border border-rose-300 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="space-y-1.5 max-w-xl">
          <div className="flex items-center gap-1.5 text-rose-800 font-bold">
            <span className="material-symbols-sharp text-base text-rose-600">warning</span>
            <span>Mirror Trading Ring Detected: 88.0% Timing Co-occurrence</span>
          </div>
          <p className="text-[11px] text-rose-900 font-sans leading-relaxed">
            Sub-affiliates <strong>PTR-882-C1</strong> and <strong>PTR-882-C2</strong> executed identical offset orders within 40ms of master client orders, extracting $142,390 USD in rebates.
          </p>
          {/* Timing Co-occurrence Progress Bar */}
          <div className="flex items-center gap-2 pt-0.5 text-[10px]">
            <span className="text-slate-600 font-mono">Co-occurrence:</span>
            <div className="w-48 h-2 bg-rose-200 rounded-none overflow-hidden relative">
              <div className="h-full bg-rose-600" style={{ width: '88%' }} />
              {/* 85% Threshold Line */}
              <div className="absolute top-0 bottom-0 left-[85%] w-0.5 bg-rose-950" title="Alert Threshold (85%)" />
            </div>
            <span className="text-rose-700 font-bold">88.0%</span>
            <span className="text-slate-400 text-[9px] font-sans">(Threshold: 85.0%)</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleStageClawback}
          className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-none transition-colors cursor-pointer flex items-center gap-1.5 border border-rose-700 shadow-xs"
        >
          <span className="material-symbols-sharp text-sm">money_off</span>
          <span>Stage Commission Clawback ($142.3K)</span>
        </button>
      </div>

      {/* 3-Tier Tree Visualizer */}
      <div className="p-3 bg-[#F8FAFC] border border-slate-200 space-y-2 text-xs font-mono">
        {/* Tier 1 Node */}
        <div
          onClick={() => selectEntity(MOCK_TREE.partnerId)}
          className="p-2.5 bg-white border border-slate-200 hover:border-blue-400 transition-colors shadow-2xs flex items-center justify-between cursor-pointer group"
        >
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={(e) => toggleCollapse(MOCK_TREE.partnerId, e)}
              className="p-0.5 hover:bg-slate-100 cursor-pointer text-slate-500"
            >
              <span className="material-symbols-sharp text-sm">
                {collapsedNodes.has(MOCK_TREE.partnerId) ? 'chevron_right' : 'expand_more'}
              </span>
            </button>
            <span className="size-2 rounded-full bg-blue-600 inline-block" />
            <span className="font-bold text-slate-900 group-hover:text-blue-600">{MOCK_TREE.name}</span>
            <span className="text-[10px] bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.2 font-bold">
              TIER 1 SUPER
            </span>
            <span className="text-[10px] text-slate-400 font-mono">[{MOCK_TREE.partnerId}]</span>
          </div>
          <div className="text-right">
            <span className="font-bold text-slate-900">${MOCK_TREE.monthlyCommissionUsd.toLocaleString()}/mo</span>
            <span className="text-slate-400 text-[10px] block">{MOCK_TREE.subAffiliatesCount} Sub-affiliates</span>
          </div>
        </div>

        {/* Tier 2 & Tier 3 Children */}
        {!collapsedNodes.has(MOCK_TREE.partnerId) && (
          <div className="pl-6 space-y-2 border-l-2 border-slate-300 ml-3">
            {MOCK_TREE.children?.map((child) => (
              <div key={child.partnerId} className="space-y-1.5">
                <div
                  onClick={() => selectEntity(child.partnerId)}
                  className="p-2 bg-white border border-slate-200 hover:border-slate-400 transition-colors flex items-center justify-between cursor-pointer group shadow-2xs"
                >
                  <div className="flex items-center gap-2">
                    {child.children && child.children.length > 0 ? (
                      <button
                        type="button"
                        onClick={(e) => toggleCollapse(child.partnerId, e)}
                        className="p-0.5 hover:bg-slate-100 cursor-pointer text-slate-500"
                      >
                        <span className="material-symbols-sharp text-sm">
                          {collapsedNodes.has(child.partnerId) ? 'chevron_right' : 'expand_more'}
                        </span>
                      </button>
                    ) : (
                      <span className="w-4 inline-block" />
                    )}
                    <span className="size-2 rounded-full bg-slate-600 inline-block" />
                    <span className="font-medium text-slate-900 group-hover:text-blue-600">{child.name}</span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-1 py-0.2 border border-slate-200">
                      TIER 2
                    </span>
                    <span className="text-[10px] text-slate-400">[{child.partnerId}]</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-slate-800">${child.monthlyCommissionUsd.toLocaleString()}/mo</span>
                    {child.subAffiliatesCount ? (
                      <span className="text-slate-400 text-[9px] block">{child.subAffiliatesCount} downlines</span>
                    ) : null}
                  </div>
                </div>

                {/* Tier 3 Sub-children */}
                {child.children && !collapsedNodes.has(child.partnerId) && (
                  <div className="pl-6 space-y-1.5 border-l-2 border-amber-400 ml-3">
                    {child.children.map((subChild) => (
                      <div
                        key={subChild.partnerId}
                        onClick={() => selectEntity(subChild.partnerId)}
                        className="p-2 bg-amber-50/70 border border-amber-300/80 hover:border-amber-500 transition-colors flex items-center justify-between cursor-pointer group shadow-2xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="size-1.5 rounded-full bg-amber-600 inline-block" />
                          <span className="text-[11px] font-semibold text-slate-900 group-hover:text-amber-700">
                            {subChild.name}
                          </span>
                          <span className="text-[9px] bg-amber-200 text-amber-900 border border-amber-300 px-1.5 py-0.2 font-bold tracking-wider">
                            RING SUSPECT
                          </span>
                          <span className="text-[10px] text-slate-400">[{subChild.partnerId}]</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[11px] font-bold text-amber-900 block">
                            ${subChild.monthlyCommissionUsd.toLocaleString()}/mo
                          </span>
                          <span className="text-[9px] text-rose-600 font-bold block">40ms sync execution</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
