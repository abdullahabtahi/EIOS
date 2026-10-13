/* eslint-disable @typescript-eslint/no-explicit-any */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createSseParser } from '@/lib/sse';
import { getServiceIdToken, resetServiceIdTokenCache } from '@/lib/server/iam';
import { GET, POST } from '@/app/api/v1/[...path]/route';

const jwt = (expSeconds: number) =>
  `h.${Buffer.from(JSON.stringify({ exp: expSeconds })).toString('base64url')}.s`;

describe('createSseParser', () => {
  const collect = () => {
    const events: Array<[string, string]> = [];
    return { events, feed: createSseParser((n, d) => events.push([n, d])) };
  };

  it('dispatches named events with JSON data', () => {
    const { events, feed } = collect();
    feed('event: churn_update\ndata: {"a":1}\n\n');
    expect(events).toEqual([['churn_update', '{"a":1}']]);
  });

  it('reassembles events split across arbitrary chunk boundaries', () => {
    const { events, feed } = collect();
    for (const piece of ['event: churn_', 'update\nda', 'ta: {"a"', ':2}\n', '\n']) feed(piece);
    expect(events).toEqual([['churn_update', '{"a":2}']]);
  });

  it('handles CRLF, comments, multi-line data and default event name', () => {
    const { events, feed } = collect();
    feed(': keep-alive\r\n\r\ndata: one\r\ndata: two\r\n\r\n');
    expect(events).toEqual([['message', 'one\ntwo']]);
  });

  it('ignores a trailing partial event until it completes', () => {
    const { events, feed } = collect();
    feed('event: x\ndata: partial');
    expect(events).toEqual([]);
  });
});

describe('getServiceIdToken', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    resetServiceIdTokenCache();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it('is null when no audience is configured (local development)', async () => {
    expect(await getServiceIdToken(undefined)).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('asks the metadata server for the audience and caches the token until near expiry', async () => {
    const token = jwt(Math.floor(Date.now() / 1000) + 3600);
    fetchMock.mockResolvedValue(new Response(token));
    expect(await getServiceIdToken('https://api.example')).toBe(token);
    expect(await getServiceIdToken('https://api.example')).toBe(token);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('audience=https%3A%2F%2Fapi.example');
    expect(init.headers['Metadata-Flavor']).toBe('Google');
  });

  it('refreshes a token that is about to expire', async () => {
    fetchMock.mockImplementation(async () => new Response(jwt(Math.floor(Date.now() / 1000) + 30)));
    await getServiceIdToken('https://api.example');
    await getServiceIdToken('https://api.example');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('fails loudly when the metadata server refuses', async () => {
    fetchMock.mockResolvedValue(new Response('no', { status: 403 }));
    await expect(getServiceIdToken('https://api.example')).rejects.toThrow('403');
  });
});

describe('/api/v1 gateway', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    resetServiceIdTokenCache();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    delete process.env.EIOS_BACKEND_IAM_AUDIENCE;
  });
  afterEach(() => vi.unstubAllGlobals());

  const ctx = (...path: string[]) => ({ params: Promise.resolve({ path }) });
  const req = (url: string, init: RequestInit = {}) => {
    const r: any = new Request(url, init);
    r.nextUrl = new URL(url);
    return r;
  };

  it('forwards path, query, method, body and the operator token', async () => {
    fetchMock.mockResolvedValue(new Response('{"ok":true}', { headers: { 'content-type': 'application/json' } }));
    const res = await POST(
      req('http://web/api/v1/synthesis/what-if?x=1', {
        method: 'POST',
        headers: { Authorization: 'Bearer firebase-token', 'Content-Type': 'application/json' },
        body: '{"shock":5}',
      }),
      ctx('synthesis', 'what-if'),
    );
    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe('http://127.0.0.1:8000/api/v1/synthesis/what-if?x=1');
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"shock":5}');
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer firebase-token');
  });

  it('adds the service identity in X-Serverless-Authorization without touching the operator header', async () => {
    process.env.EIOS_BACKEND_IAM_AUDIENCE = 'https://api.example';
    fetchMock
      .mockResolvedValueOnce(new Response(jwt(Math.floor(Date.now() / 1000) + 3600)))
      .mockResolvedValueOnce(new Response('{}'));
    await GET(req('http://web/api/v1/churn/radar', { headers: { Authorization: 'Bearer firebase-token' } }), ctx('churn', 'radar'));
    const headers = fetchMock.mock.calls[1][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer firebase-token');
    expect(headers.get('X-Serverless-Authorization')).toMatch(/^Bearer h\./);
  });

  it('relays backend errors with their own status', async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"Authentication required"}', { status: 401 }));
    expect((await GET(req('http://web/api/v1/churn/radar'), ctx('churn', 'radar'))).status).toBe(401);
  });

  it('reports an unreachable backend as 503 offline', async () => {
    fetchMock.mockRejectedValue(new Error('down'));
    const res = await GET(req('http://web/api/v1/churn/radar'), ctx('churn', 'radar'));
    expect(res.status).toBe(503);
    expect((await res.json()).offline).toBe(true);
  });

  it('reports an unobtainable service identity as 503, not as an unauthenticated call', async () => {
    process.env.EIOS_BACKEND_IAM_AUDIENCE = 'https://api.example';
    fetchMock.mockResolvedValue(new Response('no', { status: 403 }));
    expect((await GET(req('http://web/api/v1/churn/radar'), ctx('churn', 'radar'))).status).toBe(503);
    expect(fetchMock).toHaveBeenCalledTimes(1); // only the metadata call; the API was never contacted
  });

  it('streams SSE responses through unchanged', async () => {
    fetchMock.mockResolvedValue(new Response('event: a\ndata: {}\n\n', { headers: { 'content-type': 'text/event-stream' } }));
    const res = await GET(req('http://web/api/v1/churn/stream', { headers: { accept: 'text/event-stream' } }), ctx('churn', 'stream'));
    expect(res.headers.get('content-type')).toBe('text/event-stream');
    expect(await res.text()).toContain('event: a');
    expect(fetchMock.mock.calls[0][1].signal).toBeUndefined();
  });
});
