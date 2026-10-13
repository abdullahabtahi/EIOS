import { NextRequest } from 'next/server';
import { backendUnavailable, callBackend } from '@/lib/server/backend';

// Same-origin gateway for the browser's /api/v1/* calls, so the API itself can stay private.
// Only the /api/v1/ prefix is forwarded; the response (including SSE streams) is relayed as-is.
const FORWARDED_RESPONSE_HEADERS = ['content-type', 'cache-control'];

async function forward(req: NextRequest, context: { params: Promise<{ path: string[] }> }): Promise<Response> {
  const { path } = await context.params;
  const target = `/api/v1/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`;
  const hasBody = req.method !== 'GET' && req.method !== 'HEAD';
  const streaming = (req.headers.get('accept') ?? '').includes('text/event-stream');

  const upstream = await callBackend(
    req,
    target,
    {
      method: req.method,
      headers: {
        Accept: req.headers.get('accept') ?? 'application/json',
        ...(hasBody ? { 'Content-Type': req.headers.get('content-type') ?? 'application/json' } : {}),
      },
      body: hasBody ? await req.text() : undefined,
    },
    { timeoutMs: streaming ? null : undefined },
  );
  if (!upstream) return backendUnavailable();

  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (streaming) headers.set('X-Accel-Buffering', 'no');
  return new Response(upstream.body, { status: upstream.status, headers });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
