"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { LAYERS, type Layer } from "./content";
import { useReducedMotion } from "./hooks";

/** Frames come from one generated orbit clip, cropped and sampled at every third frame (see public/landing/PROVENANCE.md). */
const FRAME_COUNT = 81;
const FRAME_W = 800;
const FRAME_H = 864;
const STILL_FRAME = 40;

const frameSrc = (i: number): string => `/landing/orbit/f_${String(i + 1).padStart(3, "0")}.webp`;
const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

function loadFrame(i: number): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`frame ${i} failed to load`));
    img.src = frameSrc(i);
  });
}

function Caption({ layer, active }: { layer: Layer; active: boolean }) {
  return (
    <article className={`fde-caption${active ? " is-active" : ""}`} aria-hidden={!active}>
      <h3 className="fde-caption-name">{layer.name}</h3>
      <p className="fde-caption-body">{layer.summary}</p>
      <p className="fde-caption-fact">
        {layer.fact.text} <span className="fde-tag">{layer.fact.tag}</span>
      </p>
    </article>
  );
}

function StaticSystem() {
  return (
    <div className="fde-system-static">
      <div className="fde-frame">
        {/* eslint-disable-next-line @next/next/no-img-element -- a fixed local still; no optimiser needed */}
        <img src={frameSrc(STILL_FRAME)} alt="" width={FRAME_W} height={FRAME_H} />
      </div>
      <div className="fde-system-list">
        {LAYERS.map((layer) => (
          <Caption key={layer.n} layer={layer} active />
        ))}
      </div>
    </div>
  );
}

function PinnedSystem() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frames = useRef<Array<HTMLImageElement | undefined>>([]);
  const shown = useRef(-1);
  const [layerIdx, setLayerIdx] = useState(0);

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
      { rootMargin: "120% 0px" },
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
      draw(Math.round(clamp01((p - 0.03) / 0.94) * (FRAME_COUNT - 1)));
      setLayerIdx(Math.min(LAYERS.length - 1, Math.floor(p * LAYERS.length)));
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
    <div ref={sectionRef} className="fde-pin" style={{ "--stops": LAYERS.length } as React.CSSProperties}>
      <div className="fde-pin-sticky">
        <ol className="fde-rail" aria-hidden="true">
          {LAYERS.map((layer, k) => (
            <li key={layer.n} className={k <= layerIdx ? "is-lit" : undefined}>
              {String(layer.n).padStart(2, "0")}
            </li>
          ))}
        </ol>
        <div className="fde-captions">
          {LAYERS.map((layer, k) => (
            <Caption key={layer.n} layer={layer} active={k === layerIdx} />
          ))}
        </div>
        <div className="fde-frame">
          <canvas
            ref={canvasRef}
            width={FRAME_W}
            height={FRAME_H}
            role="img"
            aria-label="The five-layer stack turning slowly in space as you scroll."
          />
        </div>
      </div>
    </div>
  );
}

export function OrbitSequence() {
  const reduced = useReducedMotion();
  return (
    <section id="system" className="fde-system" aria-labelledby="fde-system-title">
      <h2 id="fde-system-title" className="fde-h2 fde-system-title">
        Five layers. Each one can only be reached through the one below.
      </h2>
      {reduced ? <StaticSystem /> : <PinnedSystem />}
    </section>
  );
}
