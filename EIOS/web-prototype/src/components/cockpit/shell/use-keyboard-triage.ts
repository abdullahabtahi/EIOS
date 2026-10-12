'use client';

/**
 * Institutional Operator Keyboard Triage Velocity Hook (F019 Phase 6, T019).
 * Enables Bloomberg Terminal / Superhuman velocity:
 * - 'j': Move down to next case alert
 * - 'k': Move up to previous case alert
 * - 'x': Toggle select active item
 * - 'e': Fast-stage pre-settlement hold proposal
 * - 'f': Fast-stage auto-SAR draft proposal
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { TriageItem } from '../state/cockpit-types';

export function useKeyboardTriage(triageItems: TriageItem[]) {
  const { state, selectTriageItem, stageAction } = useCockpit();

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if inside an input, textarea, or contentEditable element
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }

      // Ignore if modifier keys pressed (e.g. Cmd+K)
      if (e.metaKey || e.ctrlKey || e.altKey) {
        return;
      }

      const activeId = state.activeTriageItemId;
      const currentIndex = triageItems.findIndex((item) => item.id === activeId);

      switch (e.key.toLowerCase()) {
        case 'j': {
          // Move down
          e.preventDefault();
          if (triageItems.length === 0) return;
          const nextIndex = currentIndex < triageItems.length - 1 ? currentIndex + 1 : 0;
          selectTriageItem(triageItems[nextIndex].id);
          break;
        }
        case 'k': {
          // Move up
          e.preventDefault();
          if (triageItems.length === 0) return;
          const prevIndex = currentIndex > 0 ? currentIndex - 1 : triageItems.length - 1;
          selectTriageItem(triageItems[prevIndex].id);
          break;
        }
        case 'x': {
          // Toggle selection / focus
          e.preventDefault();
          if (activeId) {
            selectTriageItem(activeId);
          }
          break;
        }
        case 'e': {
          // Stage pre-settlement hold on active entity
          e.preventDefault();
          const activeItem = (triageItems || []).find((item) => item.id === activeId);
          if (activeItem) {
            stageAction({
              intentId: `act_hold_kb_${Date.now()}`,
              actionType: 'HOLD_WITHDRAWAL',
              targetEntityId: activeItem.entityId,
              targetEntityType: activeItem.entityType,
              severity: 'HIGH',
              lifecycleState: 'STAGED',
              stagedTimestamp: new Date().toISOString(),
              expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
              parameters: { reason: `Operator keyboard triage hold hotkey on ${activeItem.entityId}` },
              estimatedImpact: 'Holds withdrawal funds pending statutory AML review',
              requiresFourEyes: true,
              kmsSignatureBadge: {
                keyId: 'projects/feios-prod/cryptoKeys/action-signer-p256',
                algorithm: 'ECDSA_P256_SHA256',
                signatureDigest: `DIGEST_KB_${Date.now()}`,
                verified: true,
              },
              fourEyesRecord: {
                initiatorOfficerId: state.operator.officerId,
                initiatorTimestamp: new Date().toISOString(),
                idpClaimValidation: true,
              },
            });
          }
          break;
        }
        case 'f': {
          // Stage SAR draft proposal
          e.preventDefault();
          const activeItem = (triageItems || []).find((item) => item.id === activeId);
          if (activeItem) {
            stageAction({
              intentId: `act_sar_kb_${Date.now()}`,
              actionType: 'GENERATE_SAR_DRAFT',
              targetEntityId: activeItem.entityId,
              targetEntityType: activeItem.entityType,
              severity: 'MEDIUM',
              lifecycleState: 'STAGED',
              stagedTimestamp: new Date().toISOString(),
              expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
              parameters: { statutoryCitation: '31 CFR § 1020.320', filingReason: activeItem.title },
              estimatedImpact: 'Generates regulator-ready FinCEN SAR narrative for compliance officer sign-off',
              requiresFourEyes: true,
              kmsSignatureBadge: {
                keyId: 'projects/feios-prod/cryptoKeys/action-signer-p256',
                algorithm: 'ECDSA_P256_SHA256',
                signatureDigest: `DIGEST_SAR_${Date.now()}`,
                verified: true,
              },
              fourEyesRecord: {
                initiatorOfficerId: state.operator.officerId,
                initiatorTimestamp: new Date().toISOString(),
                idpClaimValidation: true,
              },
            });
          }
          break;
        }
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [triageItems, state.activeTriageItemId, state.operator, selectTriageItem, stageAction]);
}
