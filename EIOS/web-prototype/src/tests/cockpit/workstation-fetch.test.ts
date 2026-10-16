import { describe, expect, it, vi } from 'vitest';
import { loadWorkstation } from '@/components/cockpit/state/workstation-fetch';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';

const live = { ...getMockWorkstationState('executive'), isLiveConnected: true, isCachedFallback: false };
const replay = { ...live, isLiveConnected: false, isCachedFallback: true };
const ok = (body: unknown) => ({ ok: true, status: 200, json: () => Promise.resolve(body) }) as Response;
const status = (code: number) => ({ ok: false, status: code, json: () => Promise.resolve({}) }) as Response;
const signal = () => new AbortController().signal;

describe('loadWorkstation', () => {
  it('returns a live answer from the first attempt with no retry', async () => {
    const fetcher = vi.fn().mockResolvedValue(ok(live));
    expect(await loadWorkstation('executive', { fetcher, signal: signal() })).toEqual({ kind: 'live', data: live });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).not.toContain('patient');
  });

  it('retries once with the longer budget when the proxy answered with a replay', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(ok(replay)).mockResolvedValueOnce(ok(live));
    const result = await loadWorkstation('executive', { fetcher, signal: signal() });
    expect(result.kind).toBe('live');
    expect(fetcher.mock.calls[1][0]).toContain('?patient=1');
  });

  it('retries after a network error, then reports unavailable, never a replay', async () => {
    const fetcher = vi.fn().mockRejectedValue(new TypeError('network'));
    expect(await loadWorkstation('executive', { fetcher, signal: signal() })).toEqual({ kind: 'unavailable' });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('treats 401 and 403 as denied without a retry', async () => {
    for (const code of [401, 403]) {
      const fetcher = vi.fn().mockResolvedValue(status(code));
      expect(await loadWorkstation('executive', { fetcher, signal: signal() })).toEqual({ kind: 'denied' });
      expect(fetcher).toHaveBeenCalledTimes(1);
    }
  });

  it('does not retry a deterministic client error', async () => {
    const fetcher = vi.fn().mockResolvedValue(status(404));
    expect(await loadWorkstation('executive', { fetcher, signal: signal() })).toEqual({ kind: 'unavailable' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('rejects on abort so a superseded request is not treated as a failure', async () => {
    const controller = new AbortController();
    const fetcher = vi.fn().mockImplementation(() => {
      controller.abort();
      return Promise.reject(new DOMException('Aborted', 'AbortError'));
    });
    await expect(loadWorkstation('executive', { fetcher, signal: controller.signal })).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('reports slow once when the first attempt is still running after the threshold', async () => {
    vi.useFakeTimers();
    try {
      const onSlow = vi.fn();
      let release: (r: Response) => void = () => {};
      const fetcher = vi.fn().mockReturnValue(new Promise<Response>((r) => (release = r)));
      const pending = loadWorkstation('executive', { fetcher, signal: signal(), onSlow });
      await vi.advanceTimersByTimeAsync(3100);
      expect(onSlow).toHaveBeenCalledTimes(1);
      release(ok(live));
      await pending;
      await vi.advanceTimersByTimeAsync(10000);
      expect(onSlow).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });
});
