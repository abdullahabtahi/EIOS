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
import {
  PersonaRole,
  WorkstationApiResponse,
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

  // Modals & Omnipresent Command Bar
  copilotCommandOpen: boolean;

  // Infrastructure Telemetry & Outage State
  isLiveConnected: boolean;
  isCachedFallback: boolean;
  dataOrigin: 'live' | 'fixture';
  isSimulatedOutage: boolean;
  asOfTimestamp: string;
  systemLatencyMs: number;
  isLoading: boolean;
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
  | { type: 'STAGE_ACTION'; payload: ActionIntentCard }
  | { type: 'UNSTAGE_ACTION'; payload: string }
  | { type: 'CLEAR_STAGED_ACTIONS' }
  | { type: 'SET_SHELF_EXPANDED'; payload: boolean }
  | { type: 'OPEN_FOUR_EYES_MODAL'; payload: ActionIntentCard }
  | { type: 'CLOSE_FOUR_EYES_MODAL' }
  | { type: 'ACTION_AUTHORIZED'; payload: { actionId: string; signedReceipt: string; secondOfficerId: string; rationale?: string } }
  | { type: 'SET_WHAT_IF_PARAMS'; payload: Partial<WhatIfShockParameters> }
  | { type: 'RESET_WHAT_IF_PARAMS' }
  | { type: 'SET_COPILOT_COMMAND_OPEN'; payload: boolean }
  | { type: 'TOGGLE_SIMULATED_OUTAGE'; payload?: boolean }
  | { type: 'SELECT_ENTITY'; payload: string };

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
  copilotCommandOpen: false,
  isLiveConnected: true,
  isCachedFallback: false,
  dataOrigin: initialData.dataOrigin ?? 'fixture',
  isSimulatedOutage: false,
  asOfTimestamp: initialData.asOfTimestamp,
  systemLatencyMs: 14,
  // True until the first workstation response lands, so the UI never claims "Live" unproven.
  isLoading: true,
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
      return { ...state, isLoading: true, error: null };
    }

    case 'LOAD_WORKSTATION_SUCCESS': {
      const resp = action.payload;
      const initialActiveId = resp?.triageItems?.[0]?.id ?? null;
      return {
        ...state,
        isLoading: false,
        isLiveConnected: resp?.isLiveConnected ?? state.isLiveConnected,
        isCachedFallback: resp?.isCachedFallback ?? false,
        dataOrigin: resp?.dataOrigin ?? 'fixture',
        asOfTimestamp: resp?.asOfTimestamp ?? state.asOfTimestamp,
        triageItems: resp?.triageItems ?? state.triageItems,
        activeTriageItemId: initialActiveId ?? state.activeTriageItemId,
        activeEntityId: resp?.triageItems?.[0]?.entityId ?? state.activeEntityId,
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

    case 'ACTION_AUTHORIZED': {
      const { actionId, signedReceipt, secondOfficerId, rationale } = action.payload;
      return {
        ...state,
        fourEyesPendingAction: null,
        stagedActions: state.stagedActions.map((a) => {
          if (a.intentId === actionId) {
            return {
              ...a,
              lifecycleState: 'COMMITTED',
              fourEyesRecord: {
                initiatorOfficerId: a.fourEyesRecord?.initiatorOfficerId ?? state.operator.officerId,
                initiatorTimestamp: a.fourEyesRecord?.initiatorTimestamp ?? a.stagedTimestamp,
                secondOfficerId,
                secondOfficerTimestamp: new Date().toISOString(),
                approvalRationale: rationale ?? 'Dually verified and authorized via Cloud KMS ECDSA P-256',
                idpClaimValidation: true,
              },
              kmsSignatureBadge: {
                ...a.kmsSignatureBadge,
                signatureDigest: signedReceipt || a.kmsSignatureBadge.signatureDigest,
                verified: true,
              },
            };
          }
          return a;
        }),
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

    case 'SET_COPILOT_COMMAND_OPEN': {
      return {
        ...state,
        copilotCommandOpen: action.payload,
      };
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
  authorizeAction: (actionId: string, secondOfficerId: string, signedReceipt: string, rationale?: string) => void;
  setWhatIfParams: (params: Partial<WhatIfShockParameters>) => void;
  resetWhatIfParams: () => void;
  setCopilotCommandOpen: (open: boolean) => void;
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
    dispatch({ type: 'LOAD_WORKSTATION_START' });
    try {
      const res = await authFetch(`/api/cockpit/workstations/${role}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }

      const data: WorkstationApiResponse = await res.json();
      if (seq !== requestSeq.current) return;
      dispatch({ type: 'LOAD_WORKSTATION_SUCCESS', payload: data });
    } catch (err) {
      // A superseded request is not a failure; the newer request owns the state.
      if (seq !== requestSeq.current || (err instanceof DOMException && err.name === 'AbortError')) return;
      // Deterministic fallback under failure (Principle VIII)
      const fallback = getFallbackWorkstationData(role);
      dispatch({
        type: 'LOAD_WORKSTATION_SUCCESS',
        payload: {
          ...fallback,
          isLiveConnected: false,
          isCachedFallback: true,
        },
      });
    }
  }, []);

  useEffect(() => {
    fetchWorkstation(state.activeRole, state.isSimulatedOutage);
  }, [state.activeRole, state.isSimulatedOutage, fetchWorkstation]);

  // Global Keyboard Shortcuts (Cmd+K for Copilot Command Bar, Esc to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        dispatch({ type: 'SET_COPILOT_COMMAND_OPEN', payload: !state.copilotCommandOpen });
      } else if (e.key === 'Escape' && state.copilotCommandOpen) {
        dispatch({ type: 'SET_COPILOT_COMMAND_OPEN', payload: false });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.copilotCommandOpen]);

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

  const authorizeAction = useCallback((actionId: string, secondOfficerId: string, signedReceipt: string, rationale?: string) => {
    dispatch({
      type: 'ACTION_AUTHORIZED',
      payload: { actionId, secondOfficerId, signedReceipt, rationale },
    });
  }, []);

  const setWhatIfParams = useCallback((params: Partial<WhatIfShockParameters>) => {
    dispatch({ type: 'SET_WHAT_IF_PARAMS', payload: params });
  }, []);

  const resetWhatIfParams = useCallback(() => {
    dispatch({ type: 'RESET_WHAT_IF_PARAMS' });
  }, []);

  const setCopilotCommandOpen = useCallback((open: boolean) => {
    dispatch({ type: 'SET_COPILOT_COMMAND_OPEN', payload: open });
  }, []);

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
      authorizeAction,
      setWhatIfParams,
      resetWhatIfParams,
      setCopilotCommandOpen,
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
      authorizeAction,
      setWhatIfParams,
      resetWhatIfParams,
      setCopilotCommandOpen,
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
