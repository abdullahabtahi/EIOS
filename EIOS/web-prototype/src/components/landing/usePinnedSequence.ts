"use client";

import { useEffect, useRef, useState } from "react";
import { FrameSequence } from "./frameSequence";

export type SequenceStatus = "loading" | "ready" | "failed";

interface PinnedSequenceOptions {
  readonly count: number;
  readonly width: number;
  readonly height: number;
  readonly src: (index: number) => string;
  /** Scroll progress through the pinned section (0 to 1) to a position in the clip (0 to 1). */
  readonly frameAt: (progress: number) => number;
  /** Called on every scroll frame with the section progress; keep it cheap and let React bail out on equal state. */
  readonly onProgress: (progress: number) => void;
}

const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

/**
 * Draws a pre-rendered clip onto a canvas as its section scrolls past.
 * Frames load only near the viewport, a window of them stays decoded, and everything is released once the section is far away.
 * `failed` means the clip cannot play here: the caller shows a still instead.
 */
export function usePinnedSequence(opts: PinnedSequenceOptions) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState<SequenceStatus>("loading");
  const onProgress = useRef(opts.onProgress);

  useEffect(() => {
    onProgress.current = opts.onProgress;
  });

  const { count, width, height, src, frameAt } = opts;

  useEffect(() => {
    const section = sectionRef.current;
    const canvas = canvasRef.current;
    if (!section || !canvas || typeof createImageBitmap !== "function" || typeof IntersectionObserver === "undefined") {
      setStatus("failed");
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setStatus("failed");
      return;
    }

    const step = window.matchMedia("(max-width: 720px)").matches ? 2 : 1;
    let target = 0;
    let shown = -1;
    let raf = 0;
    let active = false;

    const paint = () => {
      const hit = seq.nearest(target);
      if (!hit || hit.index === shown) return;
      shown = hit.index;
      ctx.drawImage(hit.bitmap, 0, 0, width, height);
      setStatus("ready");
    };

    const seq = new FrameSequence({ count, step, src, onFrame: paint, onUnavailable: () => setStatus("failed") });

    const update = () => {
      raf = 0;
      const rect = section.getBoundingClientRect();
      const travel = rect.height - window.innerHeight;
      const progress = travel > 0 ? clamp01(-rect.top / travel) : 0;
      target = Math.round(clamp01(frameAt(progress)) * (count - 1));
      onProgress.current(progress);
      if (active) seq.want(target);
      paint();
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };

    const io = new IntersectionObserver(
      (entries) => {
        const on = entries[entries.length - 1]?.isIntersecting ?? false;
        if (on === active) return;
        active = on;
        if (on) {
          seq.want(target);
        } else {
          seq.release();
          shown = -1;
        }
      },
      { rootMargin: "100% 0px" },
    );
    io.observe(section);

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
      io.disconnect();
      seq.release();
    };
  }, [count, width, height, src, frameAt]);

  return { sectionRef, canvasRef, status } as const;
}
