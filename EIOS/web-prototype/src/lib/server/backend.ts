import { NextRequest, NextResponse } from 'next/server';
import { getServiceIdToken } from './iam';

export const BACKEND_URL = process.env.EIOS_BACKEND_URL || 'http://127.0.0.1:8000';
const DEFAULT_TIMEOUT_MS = 8000;

interface CallOptions {
  /** Abort after this many ms; null for no limit (streaming). */
  timeoutMs?: number | null;
}

/**
 * Call the EIOS API on behalf of the operator. Forwards the operator's Authorization header and,
 * when the API is IAM-protected, adds the service identity. Returns null only when the backend is
 * unreachable or the service identity cannot be obtained.
 */
export async function callBackend(
  req: NextRequest | Request,
  path: string,
  init: RequestInit = {},
  options: CallOptions = {},
): Promise<Response | null> {
  const headers = new Headers(init.headers);
  const authorization = req.headers.get('authorization');
  if (authorization) headers.set('Authorization', authorization);
  const timeoutMs = options.timeoutMs === undefined ? DEFAULT_TIMEOUT_MS : options.timeoutMs;
  try {
    const serviceToken = await getServiceIdToken();
    if (serviceToken) headers.set('X-Serverless-Authorization', `Bearer ${serviceToken}`);
    return await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers,
      cache: 'no-store',
      ...(timeoutMs === null ? {} : { signal: AbortSignal.timeout(timeoutMs) }),
    });
  } catch {
    return null;
  }
}

/** The backend is unreachable: say so. Never fabricate a successful governed action. */
export function backendUnavailable(): NextResponse {
  return NextResponse.json({ detail: 'EIOS backend is unavailable', offline: true }, { status: 503 });
}

/** Pass a non-OK backend answer through unchanged, so 401/403/422 reach the operator as what they are. */
export async function relayError(res: Response): Promise<NextResponse> {
  const body = await res.json().catch(() => ({ detail: res.statusText || 'Request failed' }));
  return NextResponse.json(body, { status: res.status });
}

/** Relay the backend's answer as-is: success body, or its real error status. */
export async function relay(res: Response | null): Promise<NextResponse> {
  if (!res) return backendUnavailable();
  return res.ok ? NextResponse.json(await res.json()) : relayError(res);
}
