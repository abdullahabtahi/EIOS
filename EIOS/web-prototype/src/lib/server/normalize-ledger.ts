import type {
  ChainVerification,
  ComplianceLedger,
  IntentSignOffs,
  LedgerRow,
  SignOff,
  SignedCheckpoint,
} from '@/components/cockpit/state/cockpit-types';

type Raw = Record<string, unknown>;

const str = (v: unknown): string => (typeof v === 'string' ? v : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
const rows = (v: unknown): Raw[] => (Array.isArray(v) ? (v.filter((r) => r && typeof r === 'object') as Raw[]) : []);

function row(r: Raw): LedgerRow {
  return {
    ledgerSeq: num(r.ledger_seq),
    eventType: str(r.event_type),
    entityId: str(r.entity_id),
    actorId: str(r.actor_id),
    previousHash: str(r.prev_hash),
    recordHash: str(r.current_hash),
    timestamp: str(r.timestamp),
    anchored: r.is_worm_anchored === true,
  };
}

function signOff(v: unknown): SignOff | null {
  if (!v || typeof v !== 'object') return null;
  const r = v as Raw;
  return { officerId: str(r.officer_id), role: str(r.role), approvedAt: str(r.approved_at) };
}

function intent(r: Raw): IntentSignOffs {
  return {
    intentId: str(r.intent_id),
    actionType: str(r.action_type),
    targetEntityId: str(r.target_entity_id),
    severity: str(r.severity),
    status: str(r.status),
    requiresDualApproval: r.requires_dual_approval === true,
    first: signOff(r.first_approver),
    second: signOff(r.second_approver),
  };
}

function checkpoint(r: Raw): SignedCheckpoint {
  return {
    checkpointId: str(r.checkpoint_id),
    chainHeadSeq: num(r.chain_head_seq),
    rootHash: str(r.root_hash),
    retentionExpiration: str(r.retention_expiration),
  };
}

function verification(v: unknown): ChainVerification {
  const r = (v && typeof v === 'object' ? v : {}) as Raw;
  return {
    entriesVerified: num(r.total_entries_verified),
    unbroken: r.is_chain_unbroken === true,
    headHash: str(r.chain_head_hash),
    anchorsMatched: num(r.worm_anchors_matched),
  };
}

/** The backend's ledger payload in the cockpit's shape; a missing field reads as empty, never as a pass. */
export function normalizeLedger(raw: Raw): ComplianceLedger {
  return {
    entries: rows(raw.entries).map(row),
    approvals: rows(raw.approvals).map(intent),
    checkpoints: rows(raw.checkpoints).map(checkpoint),
    verification: verification(raw.verification),
    isSimulated: raw.is_simulated !== false,
  };
}
