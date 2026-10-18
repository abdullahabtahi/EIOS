"use client";

import React, { useCallback, useState } from "react";
import { landingAsset } from "./assets";
import { LAYERS, type Layer } from "./content";
import { useDataSaver, useReducedMotion } from "./hooks";
import { usePinnedSequence } from "./usePinnedSequence";

/** Frames come from one generated orbit clip, cropped and sampled at every third frame (see asset-sources/landing/PROVENANCE.md). */
const FRAME_COUNT = 81;
const FRAME_W = 800;
const FRAME_H = 864;
const STILL_FRAME = 40;

const frameSrc = (i: number): string => landingAsset(`orbit/f_${String(i + 1).padStart(3, "0")}.webp`);
/** Scroll progress to a position in the clip: a short hold at each end. */
const frameAt = (p: number): number => (p - 0.03) / 0.94;

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
        <img src={frameSrc(STILL_FRAME)} alt="" width={FRAME_W} height={FRAME_H} loading="lazy" decoding="async" />
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
  const [layerIdx, setLayerIdx] = useState(0);
  const onProgress = useCallback((p: number) => setLayerIdx(Math.min(LAYERS.length - 1, Math.floor(p * LAYERS.length))), []);
  const { sectionRef, canvasRef, status } = usePinnedSequence({
    count: FRAME_COUNT,
    width: FRAME_W,
    height: FRAME_H,
    src: frameSrc,
    frameAt,
    onProgress,
  });

  if (status === "failed") return <StaticSystem />;

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
  const saver = useDataSaver();
  const still = reduced || saver;
  return (
    <section id="system" className="fde-system" aria-labelledby="fde-system-title">
      <h2 id="fde-system-title" className="fde-h2 fde-system-title">
        Five layers. Each one can only be reached through the one below.
      </h2>
      {still ? <StaticSystem /> : <PinnedSystem />}
    </section>
  );
}
