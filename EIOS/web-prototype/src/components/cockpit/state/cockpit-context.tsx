'use client';

/**
 * Institutional Operator Cockpit React Context & State Reducer
 * Governs active persona, Common Operational Picture (COP) selection,
 * Two-Phase Commit Staged Actions, What-If parameters, and deterministic outage simulation.
 * Adheres to Constitution Principles I–VIII.
 */

import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from 'react';
import { authFetch } from '@/lib/auth/token';
import { useAuth } from '@/lib/auth/auth-context';
import {
  ALL_ROLES,
  PREFETCH_DELAY_MS,
  PANEL_TTL_MS,
  loadShelf,
  loadWorkstation,
  prefetchWorkstations,
  type WorkstationFreshness,
} from './workstation-fetch';
import {
  PersonaRole,
  WorkstationApiResponse,
  CaseApiResponse,
  CaseExtras,
  DataOrigin,
  TriageItem,
  CopilotDossier,
  ActionIntentCard,
  DisasterRecoveryProof,
  RedLineGateStatus,
  FlywheelDiagnosticStatus,
  OperatorIdentity,
  WhatIfShockParameters,
  normalizePersonaRole,
} from './cockpit-types';
import {
  getFallbackWorkstationData,
  simulateOutageFallbackState,
  FALLBACK_OPERATOR,
  TRIAGE_DOSSIERS_BY_ID,
  MOCK_PARTNERS,
  buildPartnerRetentionDossier,
} from './fixtures';

export interface CockpitState {
  // Session & Persona
  activeRole: PersonaRole;
  operator: OperatorIdentity;
  sessionId: string;

  // Tripartite Selection
  activeTriageItemId: string | null;
  activeEntityId: string | null;
  triageSearchQuery: string;
  triageSeverityFilter: 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

  // Workstation Content
  triageItems: TriageItem[];
  activeDossier: CopilotDossier | null;
  activeDrProofs: DisasterRecoveryProof[];
  activeRedLineGates: RedLineGateStatus[];
  activeFlywheelStatus: FlywheelDiagnosticStatus | null;
  /** Role-specific canvas payload exactly as delivered; null until the active role has loaded. */
  canvasPayload: WorkstationApiResponse['canvasPayload'] | null;

  // Governed Action Shelf (Two-Phase Commit)
  stagedActions: ActionIntentCard[];
  governedActionShelfExpanded: boolean;
  fourEyesPendingAction: ActionIntentCard | null;

  // What-If Simulation Engine
  whatIfParams: WhatIfShockParameters;

  // Which view the dossier column shows, and whether an answer arrived while it showed the dossier
  dossierView: 'dossier' | 'chat';
  chatUnread: boolean;
  chatFocusTick: number; // bumped each time the chat is opened, so its input takes focus

  // Infrastructure Telemetry & Outage State
  isLiveConnected: boolean;
  isCachedFallback: boolean;
  dataOrigin: DataOrigin;
  /** The selected AML case: its computed dossier is fetched on selection when the data is engine-backed. */
  caseStatus: 'idle' | 'loading' | 'ready' | 'error';
  caseError: string | null;
  /** What surrounds the selected engine-computed case: evidence strip, SAR panel and the stage requests that apply. */
  caseExtras: CaseExtras;
  isSimulatedOutage: boolean;
  asOfTimestamp: string;
  systemLatencyMs: number;
  isLoading: boolean;
  /** How current the workstation in view is: refreshing behind cached live data, slow, or stale after a failed refresh. */
  workstationFreshness: WorkstationFreshness;
  error: string | null;
}

export type CockpitAction =
  | { type: 'SET_ROLE'; payload: PersonaRole }
  | { type: 'SELECT_TRIAGE_ITEM'; payload: string }
  | { type: 'SET_TRIAGE_SEARCH'; payload: string }
  | { type: 'SET_TRIAGE_SEVERITY_FILTER'; payload: CockpitState['triageSeverityFilter'] }
  | { type: 'LOAD_WORKSTATION_START' }
  | { type: 'LOAD_WORKSTATION_SUCCESS'; payload: WorkstationApiResponse }
  | { type: 'LOAD_WORKSTATION_FAILURE'; payload: string }
  | { type: 'SHOW_CACHED_WORKSTATION'; payload: WorkstationApiResponse; revalidating: boolean }
  | { type: 'SET_SHELF'; payload: ActionIntentCard[] }
  | { type: 'WORKSTATION_FRESHNESS'; payload: WorkstationFreshness }
  | { type: 'CASE_LOADED'; payload: CaseApiResponse }
  | { type: 'CASE_FAILED'; payload: { entityId: string; message: string } }
  | { type: 'STAGE_ACTION'; payload: ActionIntentCard }
  | { type: 'UNSTAGE_ACTION'; payload: string }
  | { type: 'CLEAR_STAGED_ACTIONS' }
  | { type: 'SET_SHELF_EXPANDED'; payload: boolean }
  | { type: 'OPEN_FOUR_EYES_MODAL'; payload: ActionIntentCard }
  | { type: 'CLOSE_FOUR_EYES_MODAL' }
  | { type: 'ACTION_UPDATED'; payload: ActionIntentCard }
  | { type: 'SET_WHAT_IF_PARAMS'; payload: Partial<WhatIfShockParameters> }
  | { type: 'RESET_WHAT_IF_PARAMS' }
  | { type: 'OPEN_CHAT' }
  | { type: 'SHOW_DOSSIER' }
  | { type: 'MARK_CHAT_UNREAD' }
  | { type: 'TOGGLE_SIMULATED_OUTAGE'; payload?: boolean }
  | { type: 'SELECT_ENTITY'; payload: string };

/** The parts of a response that surround an engine-computed case; anything absent stays absent. */
function extrasOf(source: CaseExtras | undefined): CaseExtras {
  return {
    evidenceStrip: source?.evidenceStrip,
    sarDraft: source?.sarDraft,
    caseActions: source?.caseActions,
  };
}

/** Where a workstation fetches one selected entity's computed case on the engine plane (spec 031, spec 032). */
const CASE_ROUTES: Partial<Record<PersonaRole, { path: string; noun: string }>> = {
  aml_investigator: { path: '/api/cockpit/aml/cases/', noun: 'account' },
  partner_manager: { path: '/api/cockpit/partners/', noun: 'partner' },
};

/** True when the workstation shows engine-computed cases, so selections are fetched, not looked up locally. */
function isEngineCaseView(state: CockpitState): boolean {
  return state.dataOrigin === 'engine' && CASE_ROUTES[state.activeRole] !== undefined;
}

const initialWhatIfParams: WhatIfShockParameters = {
  feeShockBps: 0,
  churnRateDelta: 0,
  complianceTighteningIndex: 50,
  settlementDelayHours: 0,
};

const initialData = getFallbackWorkstationData('executive');

const initialState: CockpitState = {
  activeRole: 'executive',
  operator: FALLBACK_OPERATOR,
  sessionId: 'sess_init_2026',
  activeTriageItemId: initialData.triageItems[0]?.id ?? null,
  activeEntityId: initialData.triageItems[0]?.entityId ?? null,
  triageSearchQuery: '',
  triageSeverityFilter: 'ALL',
  triageItems: initialData.triageItems,
  activeDossier: initialData.activeDossier ?? null,
  activeDrProofs: initialData.drProofs ?? [],
  activeRedLineGates: initialData.redLineGates ?? [],
  activeFlywheelStatus: initialData.flywheelStatus ?? null,
  canvasPayload: null,
  stagedActions: initialData.stagedActionCards ?? [],
  // Collapsed by default: the shelf is a slim bar until an operator stages or opens it.
  governedActionShelfExpanded: false,
  fourEyesPendingAction: null,
  whatIfParams: initialWhatIfParams,
  dossierView: 'dossier',
  chatUnread: false,
  chatFocusTick: 0,
  isLiveConnected: true,
  isCachedFallback: false,
  dataOrigin: initialData.dataOrigin ?? 'fixture',
  caseStatus: 'idle',
  caseError: null,
  caseExtras: {},
  isSimulatedOutage: false,
  asOfTimestamp: initialData.asOfTimestamp,
  systemLatencyMs: 14,
  // True until the first workstation response lands, so the UI never claims "Live" unproven.
  isLoading: true,
  workstationFreshness: 'fresh',
  error: null,
};

function cockpitReducer(state: CockpitState, action: CockpitAction): CockpitState {
  switch (action.type) {
    case 'SET_ROLE': {
      const normalized = normalizePersonaRole(action.payload) || 'executive';
      if (state.activeRole === normalized) return state;
      return {
        ...state,
        activeRole: normalized,
        canvasPayload: null,
        isLoading: true,
        error: null,
      };
    }

    case 'SELECT_TRIAGE_ITEM': {
      const selectedItem = (state.triageItems || []).find((i) => i.id === action.payload);
      if (isEngineCaseView(state)) {
        // Engine-backed cases are computed per account: never swap in a client-side stand-in while it loads.
        return {
          ...state,
          activeTriageItemId: action.payload,
          activeEntityId: selectedItem?.entityId ?? null,
          caseStatus: selectedItem ? 'loading' : state.caseStatus,
          caseError: null,
        };
      }
      let contextualDossier =
        (action.payload && TRIAGE_DOSSIERS_BY_ID[action.payload]) ||
        (selectedItem?.entityId && TRIAGE_DOSSIERS_BY_ID[selectedItem.entityId]);

      if (!contextualDossier && selectedItem) {
        if (state.activeRole === 'partner_manager' || selectedItem.entityId?.startsWith('PTR-')) {
          const partner = MOCK_PARTNERS.find((p) => p.partnerId === selectedItem.entityId);
          if (partner) {
            contextualDossier = buildPartnerRetentionDossier(partner);
          }
        }
      }

      return {
        ...state,
        activeTriageItemId: action.payload,
        activeEntityId: selectedItem?.entityId ?? null,
        activeDossier: contextualDossier || state.activeDossier,
      };
    }

    case 'SELECT_ENTITY': {
      const entityId = action.payload;
      const found = (state.triageItems || []).find(
        (i) => i.entityId === entityId || i.id === entityId
      );
      if (isEngineCaseView(state)) {
        return {
          ...state,
          activeEntityId: found?.entityId ?? entityId,
          activeTriageItemId: found ? found.id : state.activeTriageItemId,
          caseStatus: 'loading',
          caseError: null,
        };
      }
      let contextualDossier =
        (entityId && TRIAGE_DOSSIERS_BY_ID[entityId]) ||
        (found && TRIAGE_DOSSIERS_BY_ID[found.id]);

      if (!contextualDossier && entityId) {
        const isPartner =
          state.activeRole === 'partner_manager' ||
          entityId.startsWith('PTR-') ||
          entityId.startsWith('AP-');

        if (isPartner) {
          const partner = MOCK_PARTNERS.find(
            (p) => p.partnerId === entityId || `item_${p.partnerId}` === entityId
          );
          if (partner) {
            contextualDossier = buildPartnerRetentionDossier(partner);
          } else {
            contextualDossier = {
              dossierId: `dos_${entityId}`,
              entityId: entityId,
              role: 'partner_manager',
              headline: `Partner Retention Profile: ${entityId}`,
              executiveSummary: `Monitored partner account showing localized activity shifts. SCM causal concession analysis active.`,
              asOfTimestamp: new Date().toISOString(),
              isCachedSnapshot: false,
              sections: [
                {
                  sectionId: 'sec_partner_status',
                  title: 'Partner Engagement & Churn Hazard',
                  narrativeText: `Partner ${entityId} is active in monitoring queue. Causal concession guardrails applied.`,
                  citations: ['churn_hazard_probability'],
                  metrics: [],
                },
              ],
            };
          }
        } else {
          const isMule = entityId.toLowerCase().includes('mule');
          const isRing = entityId.toLowerCase().includes('ring');
          const isDevice = entityId.toLowerCase().includes('dev');
          contextualDossier = {
            dossierId: `dossier_${entityId}`,
            entityId: entityId,
            role: 'aml_investigator',
            headline: isMule
              ? `Suspect Mule Profile: ${entityId}`
              : isRing
              ? `Collusion Ring Entity: ${entityId}`
              : isDevice
              ? `Hardware Cluster Fingerprint: ${entityId}`
              : `Entity Intelligence Profile: ${entityId}`,
            executiveSummary: isMule
              ? `Identified downstream beneficiary account receiving rapid structured transfers originating from primary focal suspect CR84920.`
              : isRing
              ? `Circular layering counterpart exhibiting high-frequency round-trip velocity and 99.2% tick alignment.`
              : `Topological counterparty isolated during automated graph clustering and CGNAT proxy suppression.`,
            asOfTimestamp: new Date().toISOString(),
            isCachedSnapshot: false,
            sections: [
              {
                sectionId: 'sec_risk_telemetry',
                title: 'Topological Risk & Velocity Telemetry',
                narrativeText: `Entity ${entityId} exhibits elevated network betweenness and transaction fan-out within the active syndicate network.`,
                citations: ['[TARGET]', '[SPIKE]'],
                metrics: [
                  {
                    metricId: `M-${entityId}-RISK`,
                    name: 'Collusion Index',
                    rawValue: 0.88,
                    formattedValue: '0.88 / 1.0',
                    unit: 'score',
                    semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
                    asOfTimestamp: new Date().toISOString(),
                    originEngine: 'duckdb:semantic_layer',
                    stewardRole: 'Lead AML Officer',
                    citation: '[TARGET]',
                    isCached: false,
                  },
                ],
              },
              {
                sectionId: 'sec_sar_alignment',
                title: 'Near-Final SAR Draft Alignment',
                narrativeText: `Recommended for inclusion in FinCEN Form 111 filing as designated co-conspirator account linked to case ALT-CR84920. Pre-settlement hold action staged.`,
                citations: ['[TARGET]'],
                metrics: [],
              },
            ],
          };
        }
      }

      return {
        ...state,
        activeEntityId: entityId,
        activeTriageItemId: found ? found.id : (entityId.startsWith('PTR-') ? `item_${entityId}` : state.activeTriageItemId),
        activeDossier: contextualDossier || state.activeDossier,
      };
    }

    case 'SET_TRIAGE_SEARCH': {
      return { ...state, triageSearchQuery: action.payload };
    }

    case 'SET_TRIAGE_SEVERITY_FILTER': {
      return { ...state, triageSeverityFilter: action.payload };
    }

    case 'LOAD_WORKSTATION_START': {
      return { ...state, isLoading: true, workstationFreshness: 'fresh', error: null };
    }

    case 'LOAD_WORKSTATION_SUCCESS': {
      const resp = action.payload;
      // A refresh landing behind cached data keeps the operator's selection while that item still exists.
      const keepSelection =
        state.workstationFreshness === 'revalidating' || state.workstationFreshness === 'slow'
          ? resp?.triageItems?.find((i) => i.id === state.activeTriageItemId)
          : undefined;
      const selected = keepSelection ?? resp?.triageItems?.[0];
      const initialActiveId = selected?.id ?? null;
      return {
        ...state,
        isLoading: false,
        workstationFreshness: 'fresh',
        isLiveConnected: resp?.isLiveConnected ?? state.isLiveConnected,
        isCachedFallback: resp?.isCachedFallback ?? false,
        dataOrigin: resp?.dataOrigin ?? 'fixture',
        caseStatus: 'ready',
        caseError: null,
        caseExtras: extrasOf(resp),
        asOfTimestamp: resp?.asOfTimestamp ?? state.asOfTimestamp,
        triageItems: resp?.triageItems ?? state.triageItems,
        activeTriageItemId: initialActiveId ?? state.activeTriageItemId,
        activeEntityId: selected?.entityId ?? state.activeEntityId,
        activeDossier: resp?.activeDossier ?? state.activeDossier,
        activeDrProofs: resp?.drProofs ?? state.activeDrProofs,
        activeRedLineGates: resp?.redLineGates ?? state.activeRedLineGates,
        activeFlywheelStatus: resp?.flywheelStatus ?? state.activeFlywheelStatus,
        canvasPayload: resp?.canvasPayload ?? null,
        stagedActions: resp?.stagedActionCards && resp.stagedActionCards.length > 0 ? resp.stagedActionCards : state.stagedActions,
        systemLatencyMs: resp?.session?.systemLatencyMs ?? 18,
        error: null,
      };
    }

    case 'CASE_LOADED': {
      const loaded = action.payload;
      // A reply for an account that is no longer the selected one is stale.
      if (loaded.entityId !== state.activeEntityId) return state;
      return {
        ...state,
        activeDossier: loaded.activeDossier,
        canvasPayload: loaded.canvasPayload ?? state.canvasPayload,
        caseStatus: 'ready',
        caseError: null,
        caseExtras: extrasOf(loaded),
      };
    }

    case 'CASE_FAILED': {
      if (action.payload.entityId !== state.activeEntityId) return state;
      return { ...state, caseStatus: 'error', caseError: action.payload.message };
    }

    case 'SHOW_CACHED_WORKSTATION': {
      // Last live answer, shown while a refresh runs. The shelf is never taken from the cache: it keeps what it has until the refresh lands.
      const shown = cockpitReducer(state, {
        type: 'LOAD_WORKSTATION_SUCCESS',
        payload: { ...action.payload, stagedActionCards: [] },
      });
      return { ...shown, workstationFreshness: action.revalidating ? 'revalidating' : 'fresh' };
    }

    case 'SET_SHELF': {
      // The backend's shelf is the whole truth: what it no longer lists is gone, what it lists replaces what is shown.
      return { ...state, stagedActions: action.payload };
    }

    case 'WORKSTATION_FRESHNESS': {
      return { ...state, workstationFreshness: action.payload };
    }

    case 'LOAD_WORKSTATION_FAILURE': {
      return {
        ...state,
        isLoading: false,
        error: action.payload,
      };
    }

    case 'STAGE_ACTION': {
      // Avoid duplicate staging of the same intent card
      const exists = state.stagedActions.some((a) => a.intentId === action.payload.intentId);
      if (exists) {
        return {
          ...state,
          governedActionShelfExpanded: true,
        };
      }
      return {
        ...state,
        stagedActions: [action.payload, ...state.stagedActions],
        governedActionShelfExpanded: true,
      };
    }

    case 'UNSTAGE_ACTION': {
      return {
        ...state,
        stagedActions: state.stagedActions.filter((a) => a.intentId !== action.payload),
      };
    }

    case 'CLEAR_STAGED_ACTIONS': {
      return {
        ...state,
        stagedActions: [],
      };
    }

    case 'SET_SHELF_EXPANDED': {
      return {
        ...state,
        governedActionShelfExpanded: action.payload,
      };
    }

    case 'OPEN_FOUR_EYES_MODAL': {
      return {
        ...state,
        fourEyesPendingAction: action.payload,
      };
    }

    case 'CLOSE_FOUR_EYES_MODAL': {
      return {
        ...state,
        fourEyesPendingAction: null,
      };
    }

    case 'ACTION_UPDATED': {
      // The card is the backend's own: its lifecycle state, approvers and signature replace the staged one as given.
      return {
        ...state,
        fourEyesPendingAction: null,
        stagedActions: state.stagedActions.map((a) => (a.intentId === action.payload.intentId ? action.payload : a)),
      };
    }

    case 'SET_WHAT_IF_PARAMS': {
      return {
        ...state,
        whatIfParams: {
          ...state.whatIfParams,
          ...action.payload,
        },
      };
    }

    case 'RESET_WHAT_IF_PARAMS': {
      return {
        ...state,
        whatIfParams: initialWhatIfParams,
      };
    }

    case 'OPEN_CHAT': {
      return { ...state, dossierView: 'chat', chatUnread: false, chatFocusTick: state.chatFocusTick + 1 };
    }

    case 'SHOW_DOSSIER': {
      return { ...state, dossierView: 'dossier' };
    }

    case 'MARK_CHAT_UNREAD': {
      return state.dossierView === 'dossier' ? { ...state, chatUnread: true } : state;
    }

    case 'TOGGLE_SIMULATED_OUTAGE': {
      const nextOutage = action.payload !== undefined ? action.payload : !state.isSimulatedOutage;
      if (nextOutage) {
        const fallback = simulateOutageFallbackState(state.activeRole);
        return {
          ...state,
          isSimulatedOutage: true,
          isLiveConnected: false,
          isCachedFallback: true,
          asOfTimestamp: fallback.asOfTimestamp,
          systemLatencyMs: 0,
          triageItems: fallback.triageItems,
          activeDossier: fallback.activeDossier ?? null,
          activeDrProofs: fallback.drProofs ?? [],
          activeRedLineGates: fallback.redLineGates ?? [],
          activeFlywheelStatus: fallback.flywheelStatus ?? null,
          canvasPayload: fallback.canvasPayload,
        };
      } else {
        const liveFallback = getFallbackWorkstationData(state.activeRole);
        return {
          ...state,
          isSimulatedOutage: false,
          isLiveConnected: true,
          isCachedFallback: false,
          dataOrigin: 'fixture' as const,
          asOfTimestamp: liveFallback.asOfTimestamp,
          systemLatencyMs: 14,
          triageItems: liveFallback.triageItems,
          activeDossier: liveFallback.activeDossier ?? null,
          canvasPayload: null,
        };
      }
    }

    default:
      return state;
  }
}

interface CockpitContextValue {
  state: CockpitState;
  dispatch: React.Dispatch<CockpitAction>;
  filteredTriageItems: TriageItem[];
  setRole: (role: PersonaRole) => void;
  selectTriageItem: (id: string) => void;
  selectEntity: (entityId: string) => void;
  setSearchQuery: (query: string) => void;
  setSeverityFilter: (filter: CockpitState['triageSeverityFilter']) => void;
  stageAction: (action: ActionIntentCard) => void;
  unstageAction: (intentId: string) => void;
  clearStagedActions: () => void;
  openFourEyesModal: (action: ActionIntentCard) => void;
  closeFourEyesModal: () => void;
  /** Replace a staged card with the one the backend returned after an approval. */
  applyBackendCard: (card: ActionIntentCard) => void;
  setWhatIfParams: (params: Partial<WhatIfShockParameters>) => void;
  resetWhatIfParams: () => void;
  openChat: () => void;
  showDossier: () => void;
  markChatUnread: () => void;
  toggleSimulatedOutage: (enabled?: boolean) => void;
  setShelfExpanded: (expanded: boolean) => void;
  refreshWorkstation: () => Promise<void>;
}

const CockpitContext = createContext<CockpitContextValue | null>(null);

export function CockpitProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(cockpitReducer, initialState);

  // Latest-request-wins: every new load (role change, outage toggle) aborts the previous
  // one and invalidates its response, so a slow stale reply can never overwrite the
  // workstation the operator is actually looking at.
  const requestSeq = useRef(0);
  const inFlight = useRef<AbortController | null>(null);
  // The last live answer per workstation: never a replay, never persisted, gone on reload.
  const displayedRole = useRef<PersonaRole | null>(null);
  const lastLive = useRef(new Map<PersonaRole, { data: WorkstationApiResponse; at: number }>());
  // One operator's data is never shown to the next: drop the cache whenever the signed-in operator changes.
  const { operator } = useAuth();
  const operatorUid = operator?.uid ?? null;
  useEffect(() => {
    lastLive.current.clear();
  }, [operatorUid]);

  // Fetch workstation data whenever activeRole changes (unless simulated outage is active)
  const fetchWorkstation = useCallback(async (role: PersonaRole, isOutage: boolean) => {
    const seq = ++requestSeq.current;
    inFlight.current?.abort();
    inFlight.current = null;

    if (isOutage) {
      const fallback = simulateOutageFallbackState(role);
      dispatch({ type: 'LOAD_WORKSTATION_SUCCESS', payload: fallback });
      return;
    }

    const controller = new AbortController();
    inFlight.current = controller;
    // Stale-while-revalidate: show the last live answer for this workstation at once and refresh behind it.
    // Only on a switch: a refresh of the workstation already in view must not reset the operator's selection.
    const entry = lastLive.current.get(role);
    const lastKnown = entry?.data;
    const onSwitch = role !== displayedRole.current;
    const cached = onSwitch ? lastKnown : undefined;
    // Panels younger than the TTL are not refetched; the shelf is, every time (it is what an approver acts on).
    const panelsFresh = onSwitch && entry !== undefined && Date.now() - entry.at < PANEL_TTL_MS;
    displayedRole.current = role;
    if (cached) dispatch({ type: 'SHOW_CACHED_WORKSTATION', payload: cached, revalidating: !panelsFresh });
    else dispatch({ type: 'LOAD_WORKSTATION_START' });
    try {
      if (panelsFresh) {
        const shelf = await loadShelf(authFetch, controller.signal);
        if (seq !== requestSeq.current) return;
        if (shelf.kind === 'live') dispatch({ type: 'SET_SHELF', payload: shelf.cards });
        else if (shelf.kind === 'denied') {
          lastLive.current.clear();
          dispatch({ type: 'LOAD_WORKSTATION_FAILURE', payload: 'Not authorised to view this workstation. Sign in again.' });
        } else dispatch({ type: 'WORKSTATION_FRESHNESS', payload: 'stale' });
        return;
      }
      const result = await loadWorkstation(role, {
        fetcher: authFetch,
        signal: controller.signal,
        onSlow: () => {
          if (seq === requestSeq.current) dispatch({ type: 'WORKSTATION_FRESHNESS', payload: 'slow' });
        },
      });
      if (seq !== requestSeq.current) return;
      if (result.kind === 'live') {
        lastLive.current.set(role, { data: result.data, at: Date.now() });
        dispatch({ type: 'LOAD_WORKSTATION_SUCCESS', payload: result.data });
        return;
      }
      // A refused token is shown as what it is: never masked by cached data or a replay.
      if (result.kind === 'denied') {
        lastLive.current.clear();
        dispatch({ type: 'LOAD_WORKSTATION_FAILURE', payload: 'Not authorised to view this workstation. Sign in again.' });
        return;
      }
      // Both attempts failed. Keep showing the last live data (on screen already), labelled stale.
      if (lastKnown) {
        dispatch({ type: 'WORKSTATION_FRESHNESS', payload: 'stale' });
        return;
      }
      dispatch({ type: 'LOAD_WORKSTATION_SUCCESS', payload: { ...getFallbackWorkstationData(role), isLiveConnected: false, isCachedFallback: true } });
    } catch (err) {
      // A superseded request is not a failure; the newer request owns the state.
      if (seq !== requestSeq.current || (err instanceof DOMException && err.name === 'AbortError')) return;
      dispatch({ type: 'LOAD_WORKSTATION_SUCCESS', payload: { ...getFallbackWorkstationData(role), isLiveConnected: false, isCachedFallback: true } });
    }
  }, []);

  // Once the workstation in view is live, warm the others behind it so most switches start from cached data.
  const settledLive =
    !state.isLoading &&
    state.workstationFreshness === 'fresh' &&
    state.isLiveConnected &&
    !state.isCachedFallback &&
    !state.isSimulatedOutage;
  useEffect(() => {
    if (!settledLive) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const others = ALL_ROLES.filter((r) => r !== displayedRole.current && !lastLive.current.has(r));
      void prefetchWorkstations(others, {
        fetcher: authFetch,
        signal: controller.signal,
        // Never over a newer answer the operator's own load already stored.
        onLive: (role, data) => {
          if (!lastLive.current.has(role)) lastLive.current.set(role, { data, at: Date.now() });
        },
      });
    }, PREFETCH_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [settledLive, operatorUid]);

  useEffect(() => {
    fetchWorkstation(state.activeRole, state.isSimulatedOutage);
  }, [state.activeRole, state.isSimulatedOutage, fetchWorkstation]);

  // Engine-backed workstations: opening a case fetches that entity's computed dossier and canvas (latest wins).
  const caseSeq = useRef(0);
  useEffect(() => {
    const entityId = state.activeEntityId;
    const route = CASE_ROUTES[state.activeRole];
    if (state.dataOrigin !== 'engine' || !route || !entityId) return;
    if (state.caseStatus !== 'loading') return;
    const seq = ++caseSeq.current;
    const controller = new AbortController();
    (async () => {
      try {
        const res = await authFetch(`${route.path}${encodeURIComponent(entityId)}`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        if (seq !== caseSeq.current) return;
        if (!res.ok) {
          const message = res.status === 404 ? `No ${route.noun} record for ${entityId}` : `The case could not be loaded (${res.status})`;
          dispatch({ type: 'CASE_FAILED', payload: { entityId, message } });
          return;
        }
        dispatch({ type: 'CASE_LOADED', payload: (await res.json()) as CaseApiResponse });
      } catch (err) {
        if (seq !== caseSeq.current || (err instanceof DOMException && err.name === 'AbortError')) return;
        dispatch({ type: 'CASE_FAILED', payload: { entityId, message: 'The case could not be loaded' } });
      }
    })();
    return () => controller.abort();
  }, [state.activeEntityId, state.caseStatus, state.dataOrigin, state.activeRole]);

  // Global shortcut: Cmd/Ctrl+K opens the chat in the dossier column and focuses its input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        dispatch({ type: 'OPEN_CHAT' });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filtered triage items memoization
  const filteredTriageItems = useMemo(() => {
    return state.triageItems.filter((item) => {
      // Severity filter
      if (state.triageSeverityFilter !== 'ALL' && item.severity !== state.triageSeverityFilter) {
        return false;
      }
      // Text query search
      if (state.triageSearchQuery.trim() !== '') {
        const query = state.triageSearchQuery.toLowerCase();
        const matchesTitle = item.title.toLowerCase().includes(query);
        const matchesSub = item.subtitle.toLowerCase().includes(query);
        const matchesEntity = item.entityId.toLowerCase().includes(query);
        const matchesTags = item.tags.some((t) => t.toLowerCase().includes(query));
        return matchesTitle || matchesSub || matchesEntity || matchesTags;
      }
      return true;
    });
  }, [state.triageItems, state.triageSeverityFilter, state.triageSearchQuery]);

  // Convenience Action Helpers
  const setRole = useCallback((role: PersonaRole) => {
    const valid = normalizePersonaRole(role) || 'executive';
    dispatch({ type: 'SET_ROLE', payload: valid });
  }, []);

  const selectTriageItem = useCallback((id: string) => {
    dispatch({ type: 'SELECT_TRIAGE_ITEM', payload: id });
  }, []);

  const selectEntity = useCallback((entityId: string) => {
    dispatch({ type: 'SELECT_ENTITY', payload: entityId });
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    dispatch({ type: 'SET_TRIAGE_SEARCH', payload: query });
  }, []);

  const setSeverityFilter = useCallback((filter: CockpitState['triageSeverityFilter']) => {
    dispatch({ type: 'SET_TRIAGE_SEVERITY_FILTER', payload: filter });
  }, []);

  const stageAction = useCallback((action: ActionIntentCard) => {
    dispatch({ type: 'STAGE_ACTION', payload: action });
  }, []);

  const unstageAction = useCallback((intentId: string) => {
    dispatch({ type: 'UNSTAGE_ACTION', payload: intentId });
  }, []);

  const clearStagedActions = useCallback(() => {
    dispatch({ type: 'CLEAR_STAGED_ACTIONS' });
  }, []);

  const openFourEyesModal = useCallback((action: ActionIntentCard) => {
    dispatch({ type: 'OPEN_FOUR_EYES_MODAL', payload: action });
  }, []);

  const closeFourEyesModal = useCallback(() => {
    dispatch({ type: 'CLOSE_FOUR_EYES_MODAL' });
  }, []);

  const applyBackendCard = useCallback((card: ActionIntentCard) => {
    dispatch({ type: 'ACTION_UPDATED', payload: card });
  }, []);

  const setWhatIfParams = useCallback((params: Partial<WhatIfShockParameters>) => {
    dispatch({ type: 'SET_WHAT_IF_PARAMS', payload: params });
  }, []);

  const resetWhatIfParams = useCallback(() => {
    dispatch({ type: 'RESET_WHAT_IF_PARAMS' });
  }, []);

  const openChat = useCallback(() => dispatch({ type: 'OPEN_CHAT' }), []);
  const showDossier = useCallback(() => dispatch({ type: 'SHOW_DOSSIER' }), []);
  const markChatUnread = useCallback(() => dispatch({ type: 'MARK_CHAT_UNREAD' }), []);

  const toggleSimulatedOutage = useCallback((enabled?: boolean) => {
    dispatch({ type: 'TOGGLE_SIMULATED_OUTAGE', payload: enabled });
  }, []);

  const setShelfExpanded = useCallback((expanded: boolean) => {
    dispatch({ type: 'SET_SHELF_EXPANDED', payload: expanded });
  }, []);

  const refreshWorkstation = useCallback(async () => {
    await fetchWorkstation(state.activeRole, state.isSimulatedOutage);
  }, [fetchWorkstation, state.activeRole, state.isSimulatedOutage]);

  const value = useMemo<CockpitContextValue>(
    () => ({
      state,
      dispatch,
      filteredTriageItems,
      setRole,
      selectTriageItem,
      selectEntity,
      setSearchQuery,
      setSeverityFilter,
      stageAction,
      unstageAction,
      clearStagedActions,
      openFourEyesModal,
      closeFourEyesModal,
      applyBackendCard,
      setWhatIfParams,
      resetWhatIfParams,
      openChat,
      showDossier,
      markChatUnread,
      toggleSimulatedOutage,
      setShelfExpanded,
      refreshWorkstation,
    }),
    [
      state,
      filteredTriageItems,
      setRole,
      selectTriageItem,
      selectEntity,
      setSearchQuery,
      setSeverityFilter,
      stageAction,
      unstageAction,
      clearStagedActions,
      openFourEyesModal,
      closeFourEyesModal,
      applyBackendCard,
      setWhatIfParams,
      resetWhatIfParams,
      openChat,
      showDossier,
      markChatUnread,
      toggleSimulatedOutage,
      setShelfExpanded,
      refreshWorkstation,
    ]
  );

  return <CockpitContext.Provider value={value}>{children}</CockpitContext.Provider>;
}

export function useCockpit(): CockpitContextValue {
  const context = useContext(CockpitContext);
  if (!context) {
    throw new Error('useCockpit must be used within a CockpitProvider');
  }
  return context;
}
