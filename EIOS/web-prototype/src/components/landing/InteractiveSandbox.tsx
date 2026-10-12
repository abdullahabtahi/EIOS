"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface InteractiveSandboxProps {
  onEnterCockpit?: () => void;
}

export function InteractiveSandbox({ onEnterCockpit }: InteractiveSandboxProps) {
  const [activeTab, setActiveTab] = useState<"client" | "partner" | "churn">("client");
  const [useCausalEngine, setUseCausalEngine] = useState(true);

  return (
    <section id="hero-sandbox" className="py-24 px-6 sm:px-12 lg:px-16 max-w-7xl mx-auto border-t border-border">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 pb-6 border-b border-border gap-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
            Interactive Capability Showcase
          </div>
          <h2 className="text-3xl font-bold text-foreground">
            The Multi-Vector Operational Simulator
          </h2>
          <p className="text-lg text-muted-foreground mt-4 max-w-2xl">
            Experience how FEIOS unmasks financial crime syndicates, cancels arbitrage leakage, and stops partner churn in real time.
          </p>
        </div>

        {/* Minimalist Tabs */}
        <div className="flex gap-2">
          <Button
            variant={activeTab === "client" ? "default" : "secondary"}
            onClick={() => setActiveTab("client")}
          >
            Client Sentinel
          </Button>
          <Button
            variant={activeTab === "partner" ? "default" : "secondary"}
            onClick={() => setActiveTab("partner")}
          >
            Partner Fraud
          </Button>
          <Button
            variant={activeTab === "churn" ? "default" : "secondary"}
            onClick={() => setActiveTab("churn")}
          >
            Churn Radar
          </Button>
        </div>
      </div>

      {/* Simulator Workspace */}
      <div className="border border-border rounded-lg overflow-hidden bg-card">
        {/* Top Console Bar */}
        <div className="bg-background px-6 py-4 border-b border-border flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-sm font-medium text-muted-foreground">
            <span className="flex items-center gap-2">
              TARGET: <strong className="text-foreground uppercase">
                {activeTab === "client" && "Account #CR84920"}
                {activeTab === "partner" && "Partner #MP-007"}
                {activeTab === "churn" && "Partner #AP-1029"}
              </strong>
            </span>
            <span>|</span>
            <span>
              NODES: {activeTab === "client" ? "23 Accounts" : activeTab === "partner" ? "46 Accounts" : "18 Referrals"}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {activeTab === "client" && (
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Inference Engine:</span>
                <Button
                  size="sm"
                  variant={useCausalEngine ? "default" : "secondary"}
                  onClick={() => setUseCausalEngine(!useCausalEngine)}
                >
                  {useCausalEngine ? "DoWhy Causal DAG" : "Standard Heuristics"}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[500px]">

          {/* Main Visual Canvas (8 cols) */}
          <div className="lg:col-span-8 p-8 border-b lg:border-b-0 lg:border-r border-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-semibold uppercase tracking-widest text-foreground">
                  {activeTab === "client" && "TOPOLOGICAL SYNDICATE MESH"}
                  {activeTab === "partner" && "OPPOSITE TRADING CORRELATION"}
                  {activeTab === "churn" && "SILENT DISENGAGEMENT RADAR"}
                </span>
              </div>

              {/* Distilled Schematic View */}
              <div className="relative h-[300px] w-full bg-background border border-border rounded-md flex items-center justify-center p-6">

                {/* Minimalist SVG Schematic depending on tab */}
                {activeTab === "client" && (
                  <svg viewBox="0 0 400 200" className="w-full h-full text-muted-foreground" stroke="currentColor" fill="none">
                    <circle cx="200" cy="100" r="30" stroke="var(--color-foreground)" strokeWidth="1" />
                    <text x="200" y="104" textAnchor="middle" fill="var(--color-foreground)" fontSize="10" className="font-mono">CR84920</text>
                    <circle cx="100" cy="50" r="15" strokeDasharray="2 2" />
                    <circle cx="300" cy="150" r="15" strokeDasharray="2 2" />
                    <circle cx="300" cy="50" r="15" stroke="var(--color-destructive)" />
                    <line x1="115" y1="60" x2="175" y2="85" strokeWidth="0.5" />
                    <line x1="285" y1="140" x2="225" y2="115" strokeWidth="0.5" />
                    <line x1="285" y1="60" x2="225" y2="85" strokeWidth="0.5" stroke="var(--color-destructive)" />
                  </svg>
                )}
                {activeTab === "partner" && (
                  <svg viewBox="0 0 400 200" className="w-full h-full text-muted-foreground" stroke="currentColor" fill="none">
                    <path d="M 50 100 Q 125 50, 200 100 T 350 100" strokeWidth="1" />
                    <path d="M 50 100 Q 125 150, 200 100 T 350 100" strokeWidth="1" strokeDasharray="4 4" />
                    <rect x="190" y="80" width="20" height="40" fill="var(--color-background)" stroke="var(--color-foreground)" />
                    <text x="200" y="140" textAnchor="middle" fill="var(--color-foreground)" fontSize="10" className="font-mono">89.2% Inverse Correlation</text>
                  </svg>
                )}
                {activeTab === "churn" && (
                  <svg viewBox="0 0 400 200" className="w-full h-full text-muted-foreground" stroke="currentColor" fill="none">
                    <polyline points="50,50 150,80 250,150 350,180" strokeWidth="1.5" stroke="var(--color-destructive)" />
                    <circle cx="250" cy="150" r="4" fill="var(--color-destructive)" />
                    <text x="250" y="170" textAnchor="middle" fill="var(--color-destructive)" fontSize="10" className="font-mono">Threshold Crossed</text>
                  </svg>
                )}
              </div>
            </div>

            {/* Forensic Output */}
            <div className="mt-8 bg-secondary border border-border rounded-sm p-4">
              <p className="text-sm text-foreground font-mono">
                System Output: {activeTab === "client" ? "Synthetic arbitrage detected across 6 sub-nodes with identical order entry within 42ms." : activeTab === "partner" ? "Master Partner #MP-007 controls 7 sub-affiliates. Both sides harvest spread bonuses while net market risk is zeroed." : "Rebate settlement delays on MT5. Competitor NLP extraction confirms poaching risk."}
              </p>
            </div>
          </div>

          {/* Right Action Shelf (4 cols) */}
          <div className="lg:col-span-4 p-8 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-foreground mb-6 pb-4 border-b border-border">
                ACTION STAGING
              </div>

              <div className="space-y-4">
                <Card className="bg-background border-border shadow-none rounded-sm">
                  <CardContent className="pt-4 pb-4 px-4">
                    <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Target Entity</div>
                    <div className="text-base font-mono font-bold text-foreground mt-1">
                      {activeTab === "client" ? "Account #CR84920" : activeTab === "partner" ? "Partner #MP-007" : "Partner #AP-1029"}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-background border-border shadow-none rounded-sm">
                  <CardContent className="pt-4 pb-4 px-4">
                    <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                      {activeTab === "churn" ? "Protected Value" : "Estimated Exposure"}
                    </div>
                    <div className="text-2xl font-mono text-foreground mt-1 font-bold">
                      {activeTab === "client" ? "$247,000" : activeTab === "partner" ? "$42,500" : "$140,000"}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="pt-8">
              <Button variant="default" onClick={onEnterCockpit} className="w-full justify-center">
                Execute Protocol
              </Button>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
