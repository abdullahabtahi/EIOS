"use client";

import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

export function ModernArchitectureExhibit() {
  const [activeTier, setActiveTier] = useState<number | null>(null);

  return (
    <section id="architecture-exhibit" className="py-24 px-6 sm:px-12 lg:px-16 max-w-7xl mx-auto border-t border-border">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 pb-6 border-b border-border gap-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
            Exhibit 17.2 Reimagined
          </div>
          <h2 className="text-3xl font-bold text-foreground">
            Modern Decoupled Enterprise Architecture
          </h2>
          <p className="text-base text-muted-foreground mt-4 max-w-3xl">
            Serverless, microservices-driven architecture with high-speed lakehouse storage and Pearlian causal intelligence, scaling from zero to millions of broker ticks.
          </p>
        </div>
      </div>

      <div className="bg-muted border border-border rounded-lg p-12 relative">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Tier 1 */}
          <Card 
            onMouseEnter={() => setActiveTier(1)}
            className={`transition-colors cursor-default shadow-none ${activeTier === 1 ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="text-base font-bold text-foreground">1. GATEWAY & SECURE FRONT DOOR</div>
                <div className="text-xs font-semibold text-muted-foreground px-2 py-1 bg-background border border-border rounded-sm">Edge CDN • Cloud Run</div>
              </div>
              <p className="text-sm text-muted-foreground">Controls high-throughput broker traffic, adds DDoS filtering, verifies context tokens, and terminates WebSocket connections.</p>
            </CardContent>
          </Card>

          <div className="flex justify-center text-muted-foreground">
            <span className="text-xs">▼</span>
          </div>

          {/* Tier 2 */}
          <Card 
            onMouseEnter={() => setActiveTier(2)}
            className={`transition-colors cursor-default shadow-none ${activeTier === 2 ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
          >
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="text-base font-bold text-foreground">2. STRAWBERRY GRAPHQL & CUBE CORE SEMANTIC LAYER</div>
                <div className="text-xs font-semibold text-muted-foreground px-2 py-1 bg-background border border-border rounded-sm">ISO GQL • Invariants</div>
              </div>
              <p className="text-sm text-muted-foreground">Resolves multi-hop entity relations without N+1 query overhead. Cube Core enforces single source of truth.</p>
            </CardContent>
          </Card>

          <div className="flex justify-center text-muted-foreground">
            <span className="text-xs">▼</span>
          </div>

          {/* Tier 3: Split */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card 
              onMouseEnter={() => setActiveTier(3)}
              className={`transition-colors cursor-default shadow-none ${activeTier === 3 ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
            >
              <CardContent className="pt-6">
                <div className="text-base font-bold text-foreground mb-4">3A. DECOUPLED DATA PRODUCTS</div>
                <div className="space-y-3">
                  {['Client 360', 'Dealer Book', 'Partner Integrity', 'Competitive Intelligence'].map(prod => (
                    <div key={prod} className="text-xs font-semibold text-muted-foreground p-2 bg-background border border-border rounded-sm">
                      {prod}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card 
              onMouseEnter={() => setActiveTier(4)}
              className={`transition-colors cursor-default shadow-none ${activeTier === 4 ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
            >
              <CardContent className="pt-6">
                <div className="text-base font-bold text-foreground mb-4">3B. CAUSAL & AGENT MODELS</div>
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-muted-foreground p-2 bg-background border border-border rounded-sm">DoWhy Causal DAG Engine (ATE +0.89)</div>
                  <div className="text-xs font-semibold text-muted-foreground p-2 bg-background border border-border rounded-sm">Gemini 3.8 Flash (1M Context)</div>
                  <div className="text-xs font-semibold text-muted-foreground p-2 bg-background border border-border rounded-sm">Churn Hazard Decay Model (14-Day)</div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-center text-muted-foreground">
            <span className="text-xs">▼</span>
          </div>

          {/* Tier 4 */}
          <Card 
            onMouseEnter={() => setActiveTier(5)}
            className={`transition-colors cursor-default shadow-none ${activeTier === 5 ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
          >
            <CardContent className="pt-6">
              <div className="text-base font-bold text-foreground mb-4">4. HIGH-SPEED LAKEHOUSE</div>
              <p className="text-sm text-muted-foreground">Vectorized columnar queries in sub-10 milliseconds. Cleanses and structures tick streams into audit-ready gold tables.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
