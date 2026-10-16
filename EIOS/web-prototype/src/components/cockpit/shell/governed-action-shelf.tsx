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
import { Chip } from '../ui/chip';
import { authorizeIntent, GovernedActionError } from '@/lib/actions/governed-actions';

export function GovernedActionShelf() {
  const {
    state,
    setShelfExpanded,
    unstageAction,
    clearStagedActions,
    openFourEyesModal,
    applyBackendCard,
  } = useCockpit();

  const { stagedActions, governedActionShelfExpanded } = state;

  const [authorizeError, setAuthorizeError] = React.useState<{ intentId: string; message: string } | null>(null);

  // Staging from the chat happens out of sight of the shelf, so it flashes when a new action lands.
  const [flash, setFlash] = React.useState(false);
  const stagedCount = React.useRef(stagedActions.length);
  React.useEffect(() => {
    const grew = stagedActions.length > stagedCount.current;
    stagedCount.current = stagedActions.length;
    if (!grew) return;
    setFlash(true);
    const t = setTimeout(() => setFlash(false), 1600);
    return () => clearTimeout(t);
  }, [stagedActions.length]);

  // The backend records the approval and returns the card; nothing is shown as committed until it says so.
  const handleSingleAuthorize = async (action: ActionIntentCard) => {
    setAuthorizeError(null);
    try {
      const { card } = await authorizeIntent(action.intentId, state.operator.officerId);
      applyBackendCard(card);
    } catch (err) {
      const message = err instanceof GovernedActionError ? err.message : 'Authorization failed. Nothing was authorized.';
      setAuthorizeError({ intentId: action.intentId, message });
    }
  };

  const expiredCount = stagedActions.filter((a) => a.lifecycleState === 'EXPIRED').length;
  const pendingCount = stagedActions.filter((a) => a.lifecycleState === 'PENDING_SECOND_EYE').length;

  return (
    <>
      <section
        aria-label="Governed Action Shelf"
        title="Two-phase commit: nothing executes without a signed, dual-approved intent"
        data-flash={flash || undefined}
        className={`relative w-full bg-white border-t text-slate-900 z-40 shrink-0 transition-colors duration-500 ${
          flash ? 'border-cx-accent bg-cx-info-bg' : 'border-slate-300'
        }`}
      >
        {/* Slim status bar: always visible, ~36px */}
        <div className="h-9 px-4 bg-slate-50 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              type="button"
              aria-expanded={governedActionShelfExpanded}
              aria-label={governedActionShelfExpanded ? 'Collapse action shelf' : 'Expand action shelf'}
              onClick={() => setShelfExpanded(!governedActionShelfExpanded)}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-900 hover:text-cx-accent cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cx-accent"
            >
              <span className="material-symbols-sharp text-sm text-slate-500">
                {governedActionShelfExpanded ? 'expand_more' : 'expand_less'}
              </span>
              <span className="tracking-wide uppercase font-mono text-label text-slate-800">
                Governed Action Shelf
              </span>
            </button>

            <Chip tone="info">{`${stagedActions.length} staged`}</Chip>

            {expiredCount > 0 && (
              <Chip tone="warn">{`${expiredCount} expired`}</Chip>
            )}
            {pendingCount > 0 && (
              <Chip>{`${pendingCount} awaiting 2nd approver`}</Chip>
            )}
          </div>

          {stagedActions.length > 0 && (
            <button
              type="button"
              onClick={clearStagedActions}
              className="text-label text-slate-500 hover:text-red-600 font-medium transition-colors cursor-pointer"
            >
              Clear all
            </button>
          )}
        </div>

        {/* Shelf Body (Only visible when expanded) */}
        {governedActionShelfExpanded && (
          <div
            data-slot="action-drawer"
            className="absolute bottom-full inset-x-0 p-4 bg-slate-100 border-t border-slate-300 shadow-[0_-10px_24px_-12px_rgba(15,23,42,0.28)] overflow-auto max-h-[min(340px,50vh)]"
          >
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
                  const isExpired = action.lifecycleState === 'EXPIRED';
                  const isCriticalOrHigh = action.severity === 'CRITICAL' || action.severity === 'HIGH';

                  return (
                    <div
                      key={action.intentId}
                      data-testid={`action-card-${action.intentId}`}
                      className={`w-80 shrink-0 bg-white text-slate-900 border p-3 flex flex-col justify-between shadow-xs rounded-none ${
                        isCommitted ? 'border-green-500 bg-green-50/20' : 'border-slate-300'
                      }`}
                    >
                      {/* Card Header */}
                      <div>
                        <div className="flex items-center justify-between gap-1 mb-1.5">
                          <span
                            className={`px-1.5 py-0.5 text-label font-mono font-bold uppercase tracking-wider ${
                              action.severity === 'CRITICAL'
                                ? 'bg-cx-bad-bg text-cx-bad border border-cx-bad-line'
                                : action.severity === 'HIGH'
                                ? 'bg-cx-warn-bg text-cx-warn border border-cx-warn-line'
                                : 'bg-cx-sub text-cx-muted border border-cx-line'
                            }`}
                          >
                            {action.severity}
                          </span>

                          <span
                            className={`text-label font-mono font-semibold px-1 py-0.5 ${
                              isCommitted
                                ? 'bg-cx-ok-bg text-cx-ok border border-cx-ok-line'
                                : isExpired
                                ? 'bg-cx-warn-bg text-cx-warn border border-cx-warn-line'
                                : 'bg-cx-info-bg text-cx-accent border border-cx-info-line'
                            }`}
                          >
                            {action.lifecycleState}
                          </span>
                        </div>

                        <h4 className="text-xs font-bold text-cx-ink font-mono tracking-tight leading-tight">
                          {action.actionType}
                        </h4>

                        <div className="text-label text-cx-muted font-mono mt-0.5">
                          Target: <span className="font-semibold text-cx-ink">{action.targetEntityId}</span>
                        </div>

                        <p className="text-label text-cx-muted mt-2 line-clamp-2">
                          {action.estimatedImpact}
                        </p>
                      </div>

                      {/* Card Signatures & Commitment Controls */}
                      <div className="mt-3 pt-2.5 border-t border-cx-line-soft space-y-2">
                        {/* Cloud KMS Badge */}
                        <div className="flex items-center justify-between text-label font-mono text-cx-muted">
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-sharp text-xs text-cx-accent">key</span>
                            Cloud KMS P-256
                          </span>
                          <span
                            className={
                              isExpired
                                ? 'text-cx-warn font-bold'
                                : action.kmsSignatureBadge?.verified
                                ? 'text-cx-ok font-bold'
                                : 'text-cx-faint'
                            }
                          >
                            {isExpired
                              ? 'SIGNATURE EXPIRED'
                              : action.kmsSignatureBadge?.verified
                              ? 'DIGITALLY VERIFIED'
                              : 'PENDING COMMIT'}
                          </span>
                        </div>

                        {authorizeError?.intentId === action.intentId && (
                          <div
                            role="alert"
                            className="p-2 bg-cx-bad-bg border border-cx-bad-line text-cx-bad text-label font-mono"
                          >
                            {authorizeError.message}
                          </div>
                        )}

                        {/* Two-Phase Buttons */}
                        <div className="flex items-center gap-2 pt-1">
                          {isCommitted ? (
                            <div className="w-full py-1.5 bg-cx-ok-bg border border-cx-ok-line text-cx-ok text-label font-mono font-semibold flex items-center justify-center gap-1">
                              <span className="material-symbols-sharp text-xs text-cx-ok-solid">
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

                              {isExpired ? (
                                <div
                                  data-testid="action-expired-notice"
                                  className="flex-1 py-1.5 px-2 bg-cx-warn-bg border border-cx-warn-line text-cx-warn text-label font-mono font-semibold text-center"
                                >
                                  Expired · re-stage to renew
                                </div>
                              ) : action.requiresFourEyes || isCriticalOrHigh ? (
                                <button
                                  type="button"
                                  onClick={() => openFourEyesModal(action)}
                                  className="flex-1 py-1.5 bg-cx-ink hover:bg-cx-ink-hover text-white text-xs font-semibold flex items-center justify-center gap-1 cursor-pointer transition-colors shadow-xs"
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
                                  className="flex-1 py-1.5 bg-cx-accent hover:bg-cx-accent-strong text-white text-xs font-semibold flex items-center justify-center gap-1 cursor-pointer transition-colors shadow-xs"
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
