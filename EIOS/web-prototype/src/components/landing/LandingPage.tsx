"use client";

import React, { useRef } from "react";
import "./landing.css";
import "./landing-sections.css";
import "./landing-capabilities.css";
import "./landing-geo-arch.css";
import "./landing-charts.css";
import "./landing-push.css";
import { Architecture } from "./architecture/Architecture";
import { Capabilities } from "./capabilities/Capabilities";
import { Close } from "./Close";
import { FieldNotes } from "./FieldNotes";
import { landingSans } from "./fonts";
import { GeoSection } from "./geo/GeoSection";
import { useReveal } from "./hooks";
import { OrbitSequence } from "./OrbitSequence";
import { PushIn } from "./PushIn";
import { Problem } from "./Problem";
import { Showcase } from "./Showcase";
import { RedLines } from "./RedLines";
import { ResultsLedger } from "./ResultsLedger";
import { SiteNav } from "./SiteNav";
import { StackHero } from "./StackHero";

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null);
  useReveal(root);

  return (
    <div ref={root} id="top" className={`fde ${landingSans.variable}`}>
      <SiteNav />
      <main>
        <StackHero />
        <Problem />
        <OrbitSequence />
        <Capabilities />
        <GeoSection />
        <Showcase />
        <Architecture />
        <ResultsLedger />
        <RedLines />
        <FieldNotes />
      </main>
      <PushIn />
      <Close />
    </div>
  );
}
