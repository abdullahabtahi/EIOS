"use client";

import React, { useCallback, useState } from "react";
import { landingAsset } from "./assets";
import { useDataSaver, useReducedMotion } from "./hooks";
import { usePinnedSequence } from "./usePinnedSequence";

/** Every third frame of one generated push-in clip (see asset-sources/landing/PROVENANCE.md). */
const FRAME_COUNT = 65;
const FRAME_W = 1280;
const FRAME_H = 720;

const frameSrc = (i: number): string => landingAsset(`push/f_${String(i + 1).padStart(3, "0")}.webp`);
/** Scroll progress to a position in the clip: it finishes at 90% so the last frame holds. */
const frameAt = (p: number): number => p / 0.9;

const STAGES = [
  {
    title: "Below, four layers of governed data and models.",
    body: "Worlds, ingestion, the ontology and the assistant. Each can only be reached through the one beneath it.",
  },
  {
    title: "On top, the surface an operator works in.",
    body: "Six workstations: executive, AML investigator, partner manager, compliance, data operations and geospatial.",
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
  const [stage, setStage] = useState(0);
  const onProgress = useCallback((p: number) => setStage(p > 0.55 ? 1 : 0), []);
  const { sectionRef, canvasRef, status } = usePinnedSequence({
    count: FRAME_COUNT,
    width: FRAME_W,
    height: FRAME_H,
    src: frameSrc,
    frameAt,
    onProgress,
  });

  if (status === "failed") return <StaticPush />;

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
  const saver = useDataSaver();
  const still = reduced || saver;
  return (
    <section className="fde-push-section" aria-label="From the data layers to the workstation">
      {still ? <StaticPush /> : <PinnedPush />}
    </section>
  );
}
