"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "./hooks";

/** Every third frame of one generated push-in clip (see public/landing/PROVENANCE.md). */
const FRAME_COUNT = 65;
const FRAME_W = 1280;
const FRAME_H = 720;

const frameSrc = (i: number): string => `/landing/push/f_${String(i + 1).padStart(3, "0")}.webp`;
const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

function loadFrame(i: number): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`push frame ${i} failed to load`));
    img.src = frameSrc(i);
  });
}

const STAGES = [
  {
    title: "Below, four layers of governed data and models.",
    body: "Worlds, ingestion, the ontology and the assistant. Each can only be reached through the one beneath it.",
  },
  {
    title: "On top, the surface an operator works in.",
    body: "Five workstations: executive, AML investigator, partner manager, compliance and data operations.",
  },
] as const;

function Copy({ stage }: { stage: number }) {
  return (
    <div className="fde-push-copy">
      {STAGES.map((s, k) => (
        <div key={s.title} className={`fde-push-stage${k === stage ? " is-active" : ""}`} aria-hidden={k !== stage}>
          <h2 className="fde-h2">{s.title}</h2>
          <p className="fde-note">{s.body}</p>
        </div>
      ))}
    </div>
  );
}

function PinnedPush() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frames = useRef<Array<HTMLImageElement | undefined>>([]);
  const shown = useRef(-1);
  const [stage, setStage] = useState(0);

  const draw = useCallback((target: number) => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    let i = target;
    while (i >= 0 && !frames.current[i]) i -= 1;
    const img = frames.current[i];
    if (!img || shown.current === i) return;
    shown.current = i;
    ctx.drawImage(img, 0, 0, FRAME_W, FRAME_H);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const step = window.matchMedia("(max-width: 720px)").matches ? 2 : 1;
    const loadAll = async () => {
      const first = await loadFrame(0).catch(() => undefined);
      if (cancelled || !first) return;
      frames.current[0] = first;
      draw(0);
      for (let i = 1; i < FRAME_COUNT; i += step) {
        const batch = Array.from({ length: Math.min(6, Math.ceil((FRAME_COUNT - i) / step)) }, (_, b) => i + b * step);
        const done = await Promise.all(batch.map((n) => loadFrame(n).catch(() => undefined)));
        if (cancelled) return;
        done.forEach((img, b) => {
          frames.current[batch[b]] = img;
        });
        i += (batch.length - 1) * step;
      }
    };
    const section = sectionRef.current;
    if (!section) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          void loadAll();
        }
      },
      { rootMargin: "150% 0px" },
    );
    io.observe(section);
    return () => {
      cancelled = true;
      io.disconnect();
    };
  }, [draw]);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const el = sectionRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const travel = rect.height - window.innerHeight;
      const p = travel > 0 ? clamp01(-rect.top / travel) : 0;
      draw(Math.round(clamp01(p / 0.9) * (FRAME_COUNT - 1)));
      setStage(p > 0.55 ? 1 : 0);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [draw]);

  return (
    <div ref={sectionRef} className="fde-push">
      <div className="fde-push-sticky">
        <div className="fde-push-frame">
          <canvas
            ref={canvasRef}
            width={FRAME_W}
            height={FRAME_H}
            role="img"
            aria-label="The camera rises through the five-layer stack to the workstation layer on top."
          />
        </div>
        <Copy stage={stage} />
      </div>
    </div>
  );
}

function StaticPush() {
  return (
    <div className="fde-push-static">
      <div className="fde-push-frame">
        {/* eslint-disable-next-line @next/next/no-img-element -- a fixed local still; no optimiser needed */}
        <img src={frameSrc(FRAME_COUNT - 1)} alt="The workstation layer on top of the stack." width={FRAME_W} height={FRAME_H} loading="lazy" />
      </div>
      <div className="fde-push-copy">
        {STAGES.map((s) => (
          <div key={s.title} className="fde-push-stage is-active">
            <h2 className="fde-h2">{s.title}</h2>
            <p className="fde-note">{s.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PushIn() {
  const reduced = useReducedMotion();
  return (
    <section className="fde-push-section" aria-label="From the data layers to the workstation">
      {reduced ? <StaticPush /> : <PinnedPush />}
    </section>
  );
}
