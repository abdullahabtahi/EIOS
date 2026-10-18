import React from "react";
import "./landing.css";
import "./landing-sections.css";
import "./landing-capabilities.css";
import "./landing-geo-arch.css";
import "./landing-charts.css";
import "./landing-push.css";
import "./landing-ring.css";
import { Architecture } from "./architecture/Architecture";
import { Capabilities } from "./capabilities/Capabilities";
import { Close } from "./Close";
import { FieldNotes } from "./FieldNotes";
import { landingSans } from "./fonts";
import { GeoSection } from "./geo/GeoSection";
import { OrbitSequence } from "./OrbitSequence";
import { PushIn } from "./PushIn";
import { RevealRoot } from "./RevealRoot";
import { Problem } from "./Problem";
import { Showcase } from "./Showcase";
import { RedLines } from "./RedLines";
import { ResultsLedger } from "./ResultsLedger";
import { SiteNav } from "./SiteNav";
import { StackHero } from "./StackHero";

export function LandingPage() {
  return (
    <RevealRoot className={`fde ${landingSans.variable}`}>
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
    </RevealRoot>
  );
}
