'use client';

/**
 * Four-Eyes Authorization Modal
 * Enforces Constitution Principle II (No Autonomous Write-Back).
 * Records this operator's approval through the real authorize endpoint. The backend decides who is approving from
 * the verified sign-in, so a second approver is a second person signed in as themselves, never a typed-in id. The
 * modal shows what the backend returned; it never marks anything committed on its own.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { ActionIntentCard } from '../state/cockpit-types';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { authorizeIntent, GovernedActionError } from '@/lib/actions/governed-actions';

interface FourEyesFormProps {
  action: ActionIntentCard;
  operatorId: string;
  onClose: () => void;
  onApproved: (card: ActionIntentCard) => void;
}

function FourEyesForm({ action, operatorId, onClose, onApproved }: FourEyesFormProps) {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [authError, setAuthError] = React.useState<string | null>(null);

  const handleAuthorize = async () => {
    setIsSubmitting(true);
    setAuthError(null);
    try {
      const { card } = await authorizeIntent(action.intentId, operatorId);
      onApproved(card);
    } catch (err) {
      setAuthError(err instanceof GovernedActionError ? err.message : 'Authorization failed. Nothing was authorized.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-sharp text-amber-400 text-xl">shield_person</span>
          <div>
            <DialogTitle className="text-sm font-bold tracking-tight uppercase font-mono">
              Four-Eyes Authorization
            </DialogTitle>
            <p className="text-label text-slate-400 mt-0.5">Constitution Principle II • State-change gate</p>
          </div>
        </div>
        <span className="px-2 py-0.5 bg-rose-950 border border-rose-500 text-rose-300 font-mono text-label font-bold">
          {action.severity} SEVERITY
        </span>
      </div>

      <div className="p-6 space-y-4 text-xs text-slate-800">
        <div className="p-3 bg-slate-50 border border-slate-200 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-mono font-bold text-slate-900 text-xs">
              {action.actionType} • {action.targetEntityId}
            </span>
            <span className="text-label text-slate-500 font-mono">Intent ID: {action.intentId}</span>
          </div>
          {action.estimatedImpact && <p className="text-slate-600 text-xs leading-relaxed">{action.estimatedImpact}</p>}
          <div className="pt-1 flex items-center gap-4 text-label text-slate-500 border-t border-slate-200 font-mono">
            <span>Target: {action.targetEntityType}</span>
            <span>Lifecycle: {action.lifecycleState}</span>
          </div>
        </div>

        <div className="p-3 border border-slate-200 bg-slate-50/50 space-y-1">
          <span className="text-label font-semibold text-slate-500 uppercase tracking-wider block">
            You are authorizing as
          </span>
          <div className="font-mono font-bold text-slate-900 text-xs">{operatorId}</div>
          <p className="text-label text-slate-600">
            Identity comes from your sign-in. This action needs a second, different operator to authorize it while
            signed in as themselves; it is not committed until the backend says so.
          </p>
        </div>

        <div className="p-2.5 bg-blue-50 border border-blue-200 text-blue-900 text-label flex items-start gap-2">
          <span className="material-symbols-sharp text-base text-blue-700 shrink-0">key</span>
          <div>
            <span className="font-semibold">Cloud KMS ECDSA P-256 signature:</span>
            <p className="text-label text-blue-800 mt-0.5">
              {action.kmsSignatureBadge.keyId ? (
                <>
                  Key: <span className="font-mono">{action.kmsSignatureBadge.keyId}</span>
                </>
              ) : (
                'The backend returned no key for this intent.'
              )}
            </p>
          </div>
        </div>

        {authError && (
          <div role="alert" className="p-2 bg-rose-50 border border-rose-300 text-rose-800 text-xs flex items-center gap-1.5 font-medium">
            <span className="material-symbols-sharp text-sm text-rose-600">error</span>
            {authError}
          </div>
        )}
      </div>

      <div className="bg-slate-100 border-t border-slate-200 px-6 py-3 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs rounded-none transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={isSubmitting}
          onClick={handleAuthorize}
          className="px-4 py-2 bg-slate-900 hover:bg-black text-white font-medium text-xs rounded-none transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <span aria-hidden="true" className={`material-symbols-sharp text-sm ${isSubmitting ? 'animate-spin' : ''}`}>
            {isSubmitting ? 'sync' : 'verified_user'}
          </span>
          {isSubmitting ? 'Authorizing…' : 'Authorize'}
        </button>
      </div>
    </>
  );
}

export function FourEyesApprovalModal() {
  const { state, closeFourEyesModal, applyBackendCard } = useCockpit();
  const action = state.fourEyesPendingAction;

  if (!action) return null;

  return (
    <Dialog open={!!action} onOpenChange={(open) => !open && closeFourEyesModal()}>
      <DialogContent size="sm" className="rounded-none border border-slate-300 bg-white shadow-2xl p-0">
        <FourEyesForm
          key={action.intentId}
          action={action}
          operatorId={state.operator.officerId}
          onClose={closeFourEyesModal}
          onApproved={applyBackendCard}
        />
      </DialogContent>
    </Dialog>
  );
}
