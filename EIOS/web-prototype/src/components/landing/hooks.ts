"use client";

import { useEffect, useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void): () => void {
  const mql = window.matchMedia(QUERY);
  mql.addEventListener("change", onChange);
  return () => mql.removeEventListener("change", onChange);
}

/** True when the visitor asked for reduced motion. Server render assumes motion is fine. */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false,
  );
}

interface ConnectionLike {
  readonly saveData?: boolean;
  readonly effectiveType?: string;
  addEventListener(type: "change", listener: () => void): void;
  removeEventListener(type: "change", listener: () => void): void;
}

const connection = (): ConnectionLike | undefined => (navigator as Navigator & { connection?: ConnectionLike }).connection;

/** True when the visitor asked to save data or is on a 2g link, so heavy image sequences should give way to stills. */
export function useDataSaver(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const c = connection();
      c?.addEventListener("change", onChange);
      return () => c?.removeEventListener("change", onChange);
    },
    () => {
      const c = connection();
      return c?.saveData === true || c?.effectiveType === "slow-2g" || c?.effectiveType === "2g";
    },
    () => false,
  );
}

/** Live result of a media query. Server render assumes it does not match. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/**
 * Marks `[data-reveal]` children visible as they enter the viewport.
 * Content is visible by default: the hidden state only exists once this hook has armed the root.
 */
export function useReveal(root: React.RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const el = root.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia(QUERY).matches) return;
    el.classList.add("fde-armed");
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            io.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
    el.querySelectorAll("[data-reveal]").forEach((n) => io.observe(n));
    return () => {
      io.disconnect();
      el.classList.remove("fde-armed");
    };
  }, [root]);
}
