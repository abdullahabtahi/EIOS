'use client';

/**
 * Governed Action Shelf (Two-Phase Commit)
 * Enforces Constitution Principle II (No Autonomous Write-Back).
 * Provides institutional operators with a staging area for all pending state-altering actions,
 * Cloud KMS ECDSA P-256 digital signature validation, and Four-Eyes dual approval invocation.
 * Strict Sovereign Light Mode styling.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { ActionIntentCard } from '../state/cockpit-types';
import { FourEyesApprovalModal } from '../common/four-eyes-modal';

export function GovernedActionShelf() {
  const {
    state,
    setShelfExpanded,
    unstageAction,
    clearStagedActions,
    openFourEyesModal,
    authorizeAction,
  } = useCockpit();

  const { stagedActions, governedActionShelfExpanded } = state;

  const handleSingleAuthorize = (action: ActionIntentCard) => {
    const signedReceipt = `RECEIPT_SINGLE_${action.intentId.slice(0, 8)}_${Date.now()}`;
    authorizeAction(
      action.intentId,
      state.operator.officerId,
      signedReceipt,
      'Authorized via Level 3 Executive Single Officer Signature'
    );
  };

  return (
    <>
      <section
        aria-label="Governed Action Shelf"
        className="w-full bg-white border-t border-slate-300 text-slate-900 shadow-md transition-all duration-200 z-40 shrink-0"
      >
        {/* Shelf Collapsible Header Strip */}
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShelfExpanded(!governedActionShelfExpanded)}
              className="flex items-center gap-2 text-xs font-semibold text-slate-900 hover:text-slate-700 cursor-pointer focus:outline-none"
              title={governedActionShelfExpanded ? 'Collapse shelf' : 'Expand shelf'}
            >
              <span className="material-symbols-sharp text-sm text-slate-500">
                {governedActionShelfExpanded ? 'expand_more' : 'expand_less'}
              </span>
              <span className="tracking-wide uppercase font-mono text-[11px] text-slate-800">
                Governed Action Shelf
              </span>
            </button>

            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 border border-blue-200 text-[#106BA3] font-mono text-[11px] font-bold">
              <span>{stagedActions.length}</span>
              <span className="text-[10px] uppercase font-sans">Staged</span>
            </span>

            <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] text-amber-900 font-mono bg-amber-50 px-2 py-0.5 border border-amber-200">
              <span className="material-symbols-sharp text-[13px] text-amber-600">gavel</span>
              Principle II: Two-Phase Commit Required for All Mutations
            </span>
          </div>

          <div className="flex items-center gap-3">
            {stagedActions.length > 0 && (
              <button
                type="button"
                onClick={clearStagedActions}
                className="text-[11px] text-slate-500 hover:text-rose-600 font-medium transition-colors cursor-pointer"
              >
                Clear All
              </button>
            )}

            <button
              type="button"
              onClick={() => setShelfExpanded(!governedActionShelfExpanded)}
              className="text-xs text-slate-600 hover:text-slate-900 font-medium transition-colors cursor-pointer"
            >
              {governedActionShelfExpanded ? 'Collapse' : 'Expand'}
            </button>
          </div>
        </div>

        {/* Shelf Body (Only visible when expanded) */}
        {governedActionShelfExpanded && (
          <div className="p-4 bg-slate-100/70 border-b border-slate-200 overflow-x-auto scrollbar-thin max-h-72">
            {stagedActions.length === 0 ? (
              <div className="py-6 text-center text-slate-500 text-xs">
                <span className="material-symbols-sharp text-2xl text-slate-400 block mb-1">
                  fact_check
                </span>
                No actions currently staged. Propose or stage actions from dossiers, Morning Briefing, or Copilot.
              </div>
            ) : (
              <div className="flex items-stretch gap-4 pb-1">
                {stagedActions.map((action) => {
                  const isCommitted = action.lifecycleState === 'COMMITTED';
                  const isCriticalOrHigh = action.severity === 'CRITICAL' || action.severity === 'HIGH';

                  return (
                    <div
                      key={action.intentId}
                      className={`w-80 shrink-0 bg-white text-slate-900 border p-3 flex flex-col justify-between shadow-xs rounded-none ${
                        isCommitted ? 'border-emerald-500 bg-emerald-50/20' : 'border-slate-300'
                      }`}
                    >
                      {/* Card Header */}
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1.5">
                          <span
                            className={`px-1.5 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${
                              action.severity === 'CRITICAL'
                                ? 'bg-[#FAF0F0] text-[#A82A2A] border border-[#E8C5C5]'
                                : action.severity === 'HIGH'
                                ? 'bg-[#FAF5EC] text-[#A66321] border border-[#EAD8B5]'
                                : 'bg-[#F5F8FA] text-[#5C7080] border border-[#D8E1E8]'
                            }`}
                          >
                            {action.severity}
                          </span>

                          <span
                            className={`text-[10px] font-mono font-semibold px-1 py-0.5 ${
                              isCommitted
                                ? 'bg-[#EDF7ED] text-[#0D8050] border border-[#C3E6D0]'
                                : 'bg-[#EDF5FA] text-[#106BA3] border border-[#BFD3E6]'
                            }`}
                          >
                            {action.lifecycleState}
                          </span>
                        </div>

                        <h4 className="text-xs font-bold text-[#182026] font-mono tracking-tight leading-tight">
                          {action.actionType}
                        </h4>

                        <div className="text-[11px] text-[#5C7080] font-mono mt-0.5">
                          Target: <span className="font-semibold text-[#182026]">{action.targetEntityId}</span>
                        </div>

                        <p className="text-[11px] text-[#5C7080] mt-2 line-clamp-2">
                          {action.estimatedImpact}
                        </p>
                      </div>

                      {/* Card Signatures & Commitment Controls */}
                      <div className="mt-3 pt-2.5 border-t border-[#E1E8ED] space-y-2">
                        {/* Cloud KMS Badge */}
                        <div className="flex items-center justify-between text-[10px] font-mono text-[#5C7080]">
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-sharp text-xs text-[#106BA3]">key</span>
                            Cloud KMS P-256
                          </span>
                          <span
                            className={
                              action.kmsSignatureBadge.verified ? 'text-[#0D8050] font-bold' : 'text-[#8A9BA8]'
                            }
                          >
                            {action.kmsSignatureBadge.verified ? 'DIGITALLY VERIFIED' : 'PENDING COMMIT'}
                          </span>
                        </div>

                        {/* Two-Phase Buttons */}
                        <div className="flex items-center gap-2 pt-1">
                          {isCommitted ? (
                            <div className="w-full py-1.5 bg-[#EDF7ED] border border-[#C3E6D0] text-[#0D8050] text-[11px] font-mono font-semibold flex items-center justify-center gap-1">
                              <span className="material-symbols-sharp text-xs text-[#0F9960]">
                                verified_user
                              </span>
                              COMMITTED TO WORM LEDGER
                            </div>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => unstageAction(action.intentId)}
                                className="px-2 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium cursor-pointer transition-colors"
                                title="Dismiss staged action"
                              >
                                Discard
                              </button>

                              {action.requiresFourEyes || isCriticalOrHigh ? (
                                <button
                                  type="button"
                                  onClick={() => openFourEyesModal(action)}
                                  className="flex-1 py-1.5 bg-[#182026] hover:bg-[#202B33] text-white text-xs font-semibold flex items-center justify-center gap-1 cursor-pointer transition-colors shadow-xs"
                                >
                                  <span className="material-symbols-sharp text-xs text-amber-400">
                                    shield_person
                                  </span>
                                  Authorize (Four-Eyes)
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleSingleAuthorize(action)}
                                  className="flex-1 py-1.5 bg-[#106BA3] hover:bg-[#0E5C8A] text-white text-xs font-semibold flex items-center justify-center gap-1 cursor-pointer transition-colors shadow-xs"
                                >
                                  <span className="material-symbols-sharp text-xs">edit_square</span>
                                  Execute Action
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Four Eyes Modal Portal */}
      <FourEyesApprovalModal />
    </>
  );
}
