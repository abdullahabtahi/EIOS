'use client';

/**
 * Persisted pane width (localStorage, with an in-memory fallback when storage is
 * unavailable, e.g. private windows). Uses useSyncExternalStore so server and first
 * client render both show the default and hydration never mismatches.
 */

import * as React from 'react';

const CHANGE_EVENT = 'eios:pane-width-change';
const memory = new Map<string, string>();

function readRaw(key: string): string | null {
  try {
    return window.localStorage.getItem(key) ?? memory.get(key) ?? null;
  } catch {
    return memory.get(key) ?? null;
  }
}

function writeRaw(key: string, value: string): void {
  memory.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // storage unavailable: the in-memory copy still keeps this session consistent
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener('storage', onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener('storage', onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

export const clampWidth = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, Math.round(value)));

export function usePersistedWidth(
  key: string,
  fallback: number,
  min: number,
  max: number,
): readonly [number, (next: number) => void] {
  const raw = React.useSyncExternalStore(
    subscribe,
    () => readRaw(key),
    () => null,
  );
  const parsed = raw === null ? NaN : Number.parseInt(raw, 10);
  const value = Number.isFinite(parsed) ? clampWidth(parsed, min, max) : fallback;

  const setValue = React.useCallback(
    (next: number) => writeRaw(key, String(clampWidth(next, min, max))),
    [key, min, max],
  );
  return [value, setValue] as const;
}
