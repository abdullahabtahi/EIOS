'use client';

/**
 * Stage a backend-built request from a button. The card on the shelf is the one the intent hub made, signed and
 * ledgered; a failure is shown as what it is and nothing is staged. Nothing here forges a card or a signature.
 */
import * as React from 'react';
import type { StageRequest } from '../state/cockpit-types';
import { useCockpit } from '../state/cockpit-context';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';

export interface StageRequestState {
  busy: boolean;
  /** What happened last: the staged intent, or the reason nothing was staged. */
  message: { tone: 'ok' | 'error'; text: string } | null;
  stage: (request: StageRequest) => Promise<boolean>;
}

export function useStageRequest(): StageRequestState {
  const { stageAction } = useCockpit();
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<StageRequestState['message']>(null);

  const stage = React.useCallback(
    async (request: StageRequest): Promise<boolean> => {
      setBusy(true);
      setMessage(null);
      try {
        const card = await stageProposal(request);
        stageAction(card);
        setMessage({
          tone: 'ok',
          text: `Staged ${card.actionType} (${card.lifecycleState.replaceAll('_', ' ').toLowerCase()}). A second approver is needed in the action shelf.`,
        });
        return true;
      } catch (err) {
        const text = err instanceof GovernedActionError ? err.message : 'Staging failed. Nothing was staged.';
        setMessage({ tone: 'error', text });
        return false;
      } finally {
        setBusy(false);
      }
    },
    [stageAction],
  );

  return { busy, message, stage };
}
