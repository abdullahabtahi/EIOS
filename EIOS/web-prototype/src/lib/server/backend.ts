import { NextRequest, NextResponse } from 'next/server';

export const BACKEND_URL = process.env.EIOS_BACKEND_URL || 'http://127.0.0.1:8000';
const TIMEOUT_MS = 8000;

/** Call the EIOS API with the caller's Authorization header. Returns null only when the backend is unreachable. */
export async function callBackend(req: NextRequest, path: string, init: RequestInit = {}): Promise<Response | null> {
  const headers = new Headers(init.headers);
  const authorization = req.headers.get('authorization');
  if (authorization) headers.set('Authorization', authorization);
  try {
    return await fetch(`${BACKEND_URL}${path}`, { ...init, headers, cache: 'no-store', signal: AbortSignal.timeout(TIMEOUT_MS) });
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
