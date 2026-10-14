/**
 * The two browser calls that change governed state: stage a proposal, authorize a staged intent.
 *
 * Both go to the real endpoints through the same-origin proxies and return the card the backend made. Neither
 * fabricates a card, a receipt or a lifecycle state: on any failure they throw `GovernedActionError` with a reason an
 * operator can read, and the caller shows it. The assistant only ever proposes; a person calls these.
 */
import type { ActionIntentCard, StageRequest } from '@/components/cockpit/state/cockpit-types';
import { authFetch } from '@/lib/auth/token';
import { normalizeActionCard } from '@/lib/server/normalize';

const STAGE_PATH = '/api/cockpit/actions/stage';
const AUTHORIZE_PATH = '/api/cockpit/actions/authorize';

export class GovernedActionError extends Error {
  constructor(
    readonly status: number | null,
    message: string,
  ) {
    super(message);
  }
}

export type AuthorizeStatus = 'COMMITTED' | 'APPROVED' | 'PENDING_SECOND_EYE';

export interface AuthorizeResult {
  status: AuthorizeStatus | string;
  card: ActionIntentCard;
}

function describeFailure(verb: string, status: number | null, detail: string): string {
  if (status === null) return `The EIOS backend could not be reached. Nothing was ${verb}.`;
  if (status === 401) return `Your session is not authorized (HTTP 401). Sign in again. Nothing was ${verb}.`;
  if (status === 403) return `Your role is not permitted to do this (HTTP 403). Nothing was ${verb}.`;
  if (status === 503) return `The EIOS backend is offline. Nothing was ${verb}.`;
  return detail ? `${detail} (HTTP ${status}). Nothing was ${verb}.` : `The request failed (HTTP ${status}). Nothing was ${verb}.`;
}

async function post(path: string, body: unknown, verb: string): Promise<Record<string, unknown>> {
  let res: Response;
  try {
    res = await authFetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  } catch {
    throw new GovernedActionError(null, describeFailure(verb, null, ''));
  }
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : '';
    throw new GovernedActionError(res.status, describeFailure(verb, res.status, detail));
  }
  return data;
}

function cardOf(data: Record<string, unknown>, verb: string): ActionIntentCard {
  const raw = data.card;
  const card = raw && typeof raw === 'object' ? normalizeActionCard(raw as Record<string, unknown>) : null;
  if (!card?.intentId) throw new GovernedActionError(502, `The backend returned no action card. Nothing was ${verb}.`);
  return card;
}

/** Stage a proposal's backend-built request. Returns the signed, ledgered card; it still needs a second approver. */
export async function stageProposal(request: StageRequest): Promise<ActionIntentCard> {
  return cardOf(await post(STAGE_PATH, request, 'staged'), 'staged');
}

/** Record this operator's approval. The backend decides who the approver is from the verified token. */
export async function authorizeIntent(intentId: string, authorizerId: string): Promise<AuthorizeResult> {
  const data = await post(AUTHORIZE_PATH, { intent_id: intentId, authorizer_id: authorizerId }, 'authorized');
  return { status: typeof data.status === 'string' ? data.status : 'UNKNOWN', card: cardOf(data, 'authorized') };
}
