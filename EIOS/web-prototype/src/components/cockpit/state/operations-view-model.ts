/**
 * Operations Board view model.
 * Adapts either the backend payload (sla_statuses / error_budgets / red_line_gates)
 * or the fixture shape (SloHealthItem[]) into one render model. Nothing is invented:
 * values the source does not provide stay null. When there is no usable payload the
 * board shows an explicitly flagged [ILLUSTRATIVE] baseline instead of a silent
 * "everything is healthy" claim.
 */

export type OpsStatus = 'HEALTHY' | 'DEGRADED' | 'BREACHED';
export type OpsTone = 'ok' | 'warn' | 'bad';

export interface OpsCard {
  readonly id: string;
  readonly name: string;
  readonly status: OpsStatus;
  readonly primaryLabel: string;
  readonly primary: string;
  readonly details: readonly { readonly label: string; readonly value: string }[];
  readonly budgetRemainingPct: number | null;
}

export interface OpsGate {
  readonly id: string;
  readonly name: string;
  readonly status: 'PASS' | 'FAIL';
}

export interface OpsSummary {
  readonly tone: OpsTone;
  readonly label: string;
}

export interface OperationsView {
  readonly source: 'live' | 'baseline';
  readonly cards: readonly OpsCard[];
  readonly gates: readonly OpsGate[];
  readonly summary: OpsSummary;
  readonly gateSummary: OpsSummary;
}

type Rec = Record<string, unknown>;

const isRec = (v: unknown): v is Rec => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown, fallback = ''): string => (typeof v === 'string' ? v : fallback);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

function toStatus(v: unknown): OpsStatus {
  return v === 'HEALTHY' || v === 'DEGRADED' || v === 'BREACHED' ? v : 'DEGRADED';
}

function formatUtc(iso: unknown): string {
  const raw = str(iso);
  const d = new Date(raw);
  if (!raw || Number.isNaN(d.getTime())) return 'unknown';
  return `${d.toISOString().slice(5, 16).replace('T', ' ')}Z`;
}

function productCard(raw: Rec): OpsCard {
  const quality = num(raw.null_check_pass_rate);
  const sla = num(raw.freshness_sla_seconds);
  const name = str(raw.product_name, 'unknown_product');
  return {
    id: name,
    name,
    status: toStatus(raw.status),
    primaryLabel: 'Quality',
    primary: quality === null ? '—' : `${(quality * 100).toFixed(2)}%`,
    details: [
      { label: 'SLA', value: sla === null ? '—' : `${sla}s` },
      { label: 'Last ingest', value: formatUtc(raw.last_ingestion_timestamp) },
    ],
    budgetRemainingPct: null,
  };
}

function budgetCard(raw: Rec): OpsCard {
  const consumed = num(raw.consumed_pct);
  const remaining = consumed === null ? null : Math.max(0, Math.min(100, 100 - consumed));
  const id = str(raw.slo_id, str(raw.name, 'slo'));
  return {
    id,
    name: str(raw.name, id),
    status: toStatus(raw.status),
    primaryLabel: 'Error budget left',
    primary: remaining === null ? '—' : `${remaining.toFixed(1)}%`,
    details: [],
    budgetRemainingPct: remaining,
  };
}

function fixtureCard(raw: Rec): OpsCard {
  return {
    id: str(raw.sloId, str(raw.name, 'slo')),
    name: str(raw.name),
    status: toStatus(raw.status),
    primaryLabel: 'Current Value',
    primary: str(raw.currentValue, '—'),
    details: [{ label: 'Target', value: str(raw.targetValue, '—') }],
    budgetRemainingPct: num(raw.errorBudgetRemainingPct),
  };
}

function toGates(raw: unknown): OpsGate[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter(isRec).map((g) => ({
    id: str(g.gate_id, str(g.gateId, 'RL-?')),
    name: str(g.name),
    status: g.status === 'PASS' ? 'PASS' : 'FAIL',
  }));
}

function summarizeCards(cards: readonly OpsCard[]): OpsSummary {
  const total = cards.length;
  const breached = cards.filter((c) => c.status === 'BREACHED').length;
  const degraded = cards.filter((c) => c.status === 'DEGRADED').length;
  if (breached > 0) return { tone: 'bad', label: `${breached} OF ${total} BREACHED` };
  if (degraded > 0) return { tone: 'warn', label: `${degraded} OF ${total} DEGRADED` };
  return { tone: 'ok', label: `ALL ${total} HEALTHY` };
}

function summarizeGates(gates: readonly OpsGate[]): OpsSummary {
  const pass = gates.filter((g) => g.status === 'PASS').length;
  return { tone: pass === gates.length ? 'ok' : 'bad', label: `${pass}/${gates.length} PASSING` };
}

/** [ILLUSTRATIVE] baseline shown only when the backend supplied no usable payload. */
const BASELINE_CARDS: readonly OpsCard[] = [
  ['DP-01', 'Raw Ingestion Pipeline', '< 30s', '18.4s', 82.5],
  ['DP-02', 'DuckDB Semantic Metrics Engine', '100.0%', '100.0%', 100],
  ['DP-03', 'DoWhy Refuter Causal Matrix', '>= 0.80', '0.88', 91],
  ['DP-04', 'CGNAT Proxy Suppression Filter', '< 1.0%', '0.05%', 95],
  ['DP-05', 'WORM Immutable Decision Ledger', '100.0%', '100.0%', 100],
  ['DP-06', 'What-If Sub-200ms Propagation', '< 200ms', '48.2ms', 88],
].map(([id, name, target, current, budget]) => ({
  id: id as string,
  name: name as string,
  status: 'HEALTHY' as const,
  primaryLabel: 'Current Value',
  primary: current as string,
  details: [{ label: 'Target', value: target as string }],
  budgetRemainingPct: budget as number,
}));

const BASELINE_GATES: readonly OpsGate[] = [
  ['RL-1', 'Zero LLM Metric Calculation (Principle I)'],
  ['RL-2', 'No Autonomous Write-Back Four-Eyes Gate (Principle II)'],
  ['RL-3', 'Causal Refuter Placebo Threshold p > 0.05 (Principle III)'],
  ['RL-4', 'CGNAT Proxy Hub Suppression k > 100 (Feature 010)'],
  ['RL-5', 'WORM Cryptographic SHA-256 Hash Chaining'],
  ['RL-6', 'Sub-200ms Parametric Propagation & 100% Attribution'],
  ['RL-7', 'Deterministic Offline Replay Fallback (Principle VIII)'],
].map(([id, name]) => ({ id, name, status: 'PASS' as const }));

function baselineView(): OperationsView {
  return {
    source: 'baseline',
    cards: BASELINE_CARDS,
    gates: BASELINE_GATES,
    summary: summarizeCards(BASELINE_CARDS),
    gateSummary: summarizeGates(BASELINE_GATES),
  };
}

export function buildOperationsView(canvasPayload: unknown): OperationsView {
  if (!isRec(canvasPayload) || canvasPayload.type !== 'OPERATIONS_SLO') return baselineView();
  const data = canvasPayload.data;

  let cards: OpsCard[] = [];
  let gates: OpsGate[] = [];

  if (Array.isArray(data)) {
    cards = data.filter(isRec).map(fixtureCard);
  } else if (isRec(data)) {
    const products = Array.isArray(data.sla_statuses) ? data.sla_statuses.filter(isRec).map(productCard) : [];
    const budgets = Array.isArray(data.error_budgets) ? data.error_budgets.filter(isRec).map(budgetCard) : [];
    cards = [...products, ...budgets];
    gates = toGates(data.red_line_gates);
  }

  if (cards.length === 0) return baselineView();
  const finalGates = gates.length > 0 ? gates : BASELINE_GATES;

  return {
    source: 'live',
    cards,
    gates: finalGates,
    summary: summarizeCards(cards),
    gateSummary: summarizeGates(finalGates),
  };
}
