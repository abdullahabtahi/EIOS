'use client';

/**
 * Forensic URL State Synchronization Hook (F019 Phase 6, T020).
 * Bi-directionally binds active case ID, persona role, entity ID, What-If shock params,
 * and CGNAT proxy suppression into URL query parameters for forensic deep-linking.
 */

import * as React from 'react';
import { useCockpit } from './cockpit-context';
import { PersonaRole, normalizePersonaRole } from './cockpit-types';

export function useForensicUrlSync() {
  const { state, setRole, selectTriageItem, selectEntity, setWhatIfParams } = useCockpit();
  const isInitialized = React.useRef(false);
  // The workstation's first load selects its own first case; an entity asked for in the URL is applied after that load.
  const requestedEntity = React.useRef<string | null>(null);

  // 1. Initial Deserialization from URL Search Params
  React.useEffect(() => {
    if (typeof window === 'undefined' || isInitialized.current) return;
    isInitialized.current = true;

    const params = new URLSearchParams(window.location.search);
    const urlRole = params.get('role');
    const urlCase = params.get('caseId') || params.get('triageId');
    const urlEntity = params.get('entityId');
    const urlFeeShock = params.get('feeShockBps');

    const normalizedRole = normalizePersonaRole(urlRole);
    if (normalizedRole) {
      setRole(normalizedRole);
    }

    if (urlCase) {
      selectTriageItem(urlCase);
    }

    if (urlEntity) {
      requestedEntity.current = urlEntity;
      selectEntity(urlEntity);
    }

    if (urlFeeShock) {
      const parsedShock = parseFloat(urlFeeShock);
      if (!isNaN(parsedShock)) {
        setWhatIfParams({ feeShockBps: parsedShock });
      }
    }
  }, [setRole, selectTriageItem, selectEntity, setWhatIfParams]);

  // 1b. Re-apply the URL's entity once the workstation has loaded, so a deep link opens that account's case
  React.useEffect(() => {
    const wanted = requestedEntity.current;
    if (!wanted || state.isLoading || state.caseStatus !== 'ready') return;
    requestedEntity.current = null;
    if (state.activeEntityId !== wanted) selectEntity(wanted);
  }, [state.isLoading, state.caseStatus, state.activeEntityId, selectEntity]);

  // 2. Serializing Active Cockpit State back to URL
  React.useEffect(() => {
    if (typeof window === 'undefined' || !isInitialized.current) return;

    const currentUrl = new URL(window.location.href);
    const params = currentUrl.searchParams;

    // Set role
    params.set('role', state.activeRole.toLowerCase());

    // Set active triage case
    if (state.activeTriageItemId) {
      params.set('caseId', state.activeTriageItemId);
    } else {
      params.delete('caseId');
    }

    // Set active entity
    if (state.activeEntityId) {
      params.set('entityId', state.activeEntityId);
    } else {
      params.delete('entityId');
    }

    // Set What-If shock if non-zero
    if (state.whatIfParams.feeShockBps !== 0) {
      params.set('feeShockBps', String(state.whatIfParams.feeShockBps));
    } else {
      params.delete('feeShockBps');
    }

    const newSearch = params.toString();
    const newRelativePathQuery = `${window.location.pathname}${newSearch ? `?${newSearch}` : ''}`;
    window.history.replaceState(null, '', newRelativePathQuery);
  }, [
    state.activeRole,
    state.activeTriageItemId,
    state.activeEntityId,
    state.whatIfParams.feeShockBps,
  ]);
}
