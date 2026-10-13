import * as workerThreads from 'node:worker_threads';
if (typeof (workerThreads as any).markAsUncloneable !== 'function') {
  (workerThreads as any).markAsUncloneable = () => {};
}

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, vi } from 'vitest';

beforeAll(() => {
  vi.spyOn(console, 'info').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
});

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  (globalThis as unknown as Record<string, unknown>).ResizeObserver =
    MockResizeObserver;
}

if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

if (typeof globalThis.PointerEvent === 'undefined') {
  type EventCtor = new (...args: never[]) => Event;
  const Base: EventCtor =
    typeof globalThis.MouseEvent !== 'undefined'
      ? (MouseEvent as unknown as EventCtor)
      : Event;

  (globalThis as unknown as Record<string, unknown>).PointerEvent =
    class PointerEvent extends Base {};
}
