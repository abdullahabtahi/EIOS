"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface HeroSectionProps {
  onEnterCockpit?: () => void;
}

export function HeroSection({ onEnterCockpit }: HeroSectionProps) {
  return (
    <section className="relative w-full overflow-hidden bg-background border-b border-border pt-32 pb-24">
      <div className="max-w-7xl mx-auto px-6 sm:px-12 lg:px-16 flex flex-col items-center text-center">

        {/* Overline */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-8">
          <span className="w-1.5 h-1.5 bg-primary rounded-full" />
          Sovereign Institutional Decision Operating System
        </div>

        {/* Massive Headline */}
        <h1 className="text-5xl md:text-6xl font-extrabold text-foreground mb-6 max-w-5xl tracking-tight">
          The Sovereign Intelligence <span className="text-primary">Operating System</span> for Capital Markets
        </h1>

        {/* Subtext */}
        <p className="text-lg md:text-xl text-muted-foreground max-w-3xl mb-12">
          Unifying high-frequency broker telemetries, ISO GQL property graphs, and Pearlian Causal AI (DoWhy). Eliminates 95% of AML false positives, neutralizes opposite-trading arbitrage rings, and prevents partner churn before flight.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-24">
          <Button variant="default" size="lg" onClick={onEnterCockpit}>
            Launch Interactive Cockpit →
          </Button>
          <Button variant="outline" size="lg" onClick={() => {
            document.getElementById("hero-sandbox")?.scrollIntoView({ behavior: "smooth" });
          }}>
            Explore the Architecture
          </Button>
        </div>

        {/* Data Points */}
        <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 border-t border-border">
          <div className="text-left">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">24H Certified Volume</span>
              <span className="text-[10px] font-mono text-primary-foreground bg-primary px-1.5 py-0.5 rounded-sm">CUBE CORE</span>
            </div>
            <div className="text-3xl font-bold text-foreground font-mono">$2,418,920,400</div>
            <div className="text-xs text-muted-foreground mt-2">
              Zero metric hallucination guarantee
            </div>
          </div>

          <div className="text-left border-t md:border-t-0 md:border-l border-border md:pl-6 pt-4 md:pt-0">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">AML FP Drop</span>
              <span className="text-[10px] font-mono text-primary-foreground bg-primary px-1.5 py-0.5 rounded-sm">DOWHY DAG</span>
            </div>
            <div className="text-3xl font-bold text-foreground font-mono">95.2%</div>
            <div className="text-xs text-muted-foreground mt-2 font-mono">
              ATE: <span className="text-green-600">+0.89</span> Backdoor adjustment applied
            </div>
          </div>

          <div className="text-left border-t md:border-t-0 md:border-l border-border md:pl-6 pt-4 md:pt-0">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Protected Annualized ARR</span>
              <span className="text-[10px] font-mono text-primary-foreground bg-destructive px-1.5 py-0.5 rounded-sm">ROOM 1000</span>
            </div>
            <div className="text-3xl font-bold text-foreground font-mono">$1,240,000</div>
            <div className="text-xs text-muted-foreground mt-2">
              14-Day Competitor poaching NLP
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
