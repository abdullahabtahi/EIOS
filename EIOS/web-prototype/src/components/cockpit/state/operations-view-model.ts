/**
 * Operations Board view model.
 * Adapts either the backend payload (sla_statuses / error_budgets / red_line_gates)
 * or the fixture shape (SloHealthItem[]) into one render model. Nothing is invented:
 * values the source does not provide stay null. When there is no usable payload the
 * view is `unavailable`: the board says so and shows nothing in its place.
 */

export type OpsStatus = 'HEALTHY' | 'DEGRADED' | 'BREACHED' | 'NO_DATA';
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
  readonly status: 'PASS' | 'FAIL' | 'NOT_MEASURED';
  readonly basis: string;
}

export interface OpsSummary {
  readonly tone: OpsTone;
  readonly label: string;
}

export interface OperationsView {
  readonly source: 'live' | 'unavailable';
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
  return v === 'HEALTHY' || v === 'DEGRADED' || v === 'BREACHED' || v === 'NO_DATA' ? v : 'DEGRADED';
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
      ...productExtras(raw),
    ],
    budgetRemainingPct: null,
  };
}

function age(seconds: number): string {
  if (seconds < 120) return `${Math.round(seconds)} s`;
  if (seconds < 7200) return `${Math.round(seconds / 60)} min`;
  return seconds < 172800 ? `${(seconds / 3600).toFixed(1)} h` : `${Math.round(seconds / 86400)} days`;
}

/** What the engine-plane profile adds: whether freshness was judged, contract breaches and quarantine. */
function productExtras(raw: Rec): { label: string; value: string }[] {
  const out: { label: string; value: string }[] = [];
  const newest = num(raw.newest_event_age_seconds);
  if (raw.freshness_judged === false) {
    out.push({ label: 'Freshness', value: newest === null ? 'not judged' : `not judged (newest event ${age(newest)} old)` });
  }
  const breach = num(raw.contract_breach_rate);
  if (breach !== null) out.push({ label: 'Contract breaches', value: `${(breach * 100).toFixed(2)}%` });
  const held = num(raw.quarantined_records);
  if (held) out.push({ label: 'Quarantined', value: String(held) });
  return out;
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
    primary: remaining === null ? 'no data' : `${remaining.toFixed(1)}%`,
    details: observed(raw),
    budgetRemainingPct: remaining,
  };
}

function observed(raw: Rec): { label: string; value: string }[] {
  const events = num(raw.total_events);
  return events === null ? [] : [{ label: 'Observed events', value: events === 0 ? 'none' : events.toLocaleString('en-US') }];
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
    status: g.status === 'PASS' ? 'PASS' : g.status === 'NOT_MEASURED' ? 'NOT_MEASURED' : 'FAIL',
    basis: str(g.basis),
  }));
}

function summarizeCards(cards: readonly OpsCard[]): OpsSummary {
  const total = cards.length;
  const unobserved = cards.filter((c) => c.status === 'NO_DATA').length;
  const breached = cards.filter((c) => c.status === 'BREACHED').length;
  const degraded = cards.filter((c) => c.status === 'DEGRADED').length;
  if (breached > 0) return { tone: 'bad', label: `${breached} OF ${total} BREACHED` };
  if (degraded > 0) return { tone: 'warn', label: `${degraded} OF ${total} DEGRADED` };
  if (unobserved > 0) return { tone: 'warn', label: `${total - unobserved} OF ${total} OBSERVED` };
  return { tone: 'ok', label: `ALL ${total} HEALTHY` };
}

function summarizeGates(gates: readonly OpsGate[]): OpsSummary {
  const pass = gates.filter((g) => g.status === 'PASS').length;
  const failed = gates.filter((g) => g.status === 'FAIL').length;
  const unmeasured = gates.length - pass - failed;
  const label = `${pass}/${gates.length} PASSING${unmeasured > 0 ? `, ${unmeasured} NOT MEASURED` : ''}`;
  return { tone: failed > 0 ? 'bad' : unmeasured > 0 ? 'warn' : 'ok', label };
}

function unavailableView(): OperationsView {
  return {
    source: 'unavailable',
    cards: [],
    gates: [],
    summary: { tone: 'warn', label: 'NO DATA' },
    gateSummary: { tone: 'warn', label: 'NO DATA' },
  };
}

export function buildOperationsView(canvasPayload: unknown): OperationsView {
  if (!isRec(canvasPayload) || canvasPayload.type !== 'OPERATIONS_SLO') return unavailableView();
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

  if (cards.length === 0) return unavailableView();
  const finalGates = gates;

  return {
    source: 'live',
    cards,
    gates: finalGates,
    summary: summarizeCards(cards),
    gateSummary: summarizeGates(finalGates),
  };
}
