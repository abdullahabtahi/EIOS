"use client";

import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

interface DomainInfo {
  id: string;
  name: string;
  x: number; // 0 - 100% (Feasibility)
  y: number; // 0 - 100% (Value from bottom)
  prioritized: boolean;
  valueDescription: string;
  feasibilityFactors: string;
  dataProducts: string[];
  primaryKpi: string;
}

const DOMAINS: DomainInfo[] = [
  {
    id: "risk-compl",
    name: "Risk & Compliance Sentinel",
    x: 82,
    y: 88,
    prioritized: true,
    valueDescription: "95% AML false positive drop, 1-click MFSA/LFSA SAR dossiers",
    feasibilityFactors: "Pre-existing Cashier & MT5 logs, high regulatory executive sponsorship",
    dataProducts: ["Customer 360", "Device Fingerprint Registry", "AML Transaction Lineage"],
    primaryKpi: "Triage Time: 4h → 30s",
  },
  {
    id: "client-intel",
    name: "Client Intelligence (Customer 360)",
    x: 75,
    y: 78,
    prioritized: true,
    valueDescription: "Onboarding speed, churn prediction, high-frequency trader LTV",
    feasibilityFactors: "Unified OAuth & KYC repository, high data hygiene",
    dataProducts: ["Identity Graph", "Behavioral Session Stream", "Deposit Propensity"],
    primaryKpi: "Onboard Velocity: +40%",
  },
  {
    id: "partner-intel",
    name: "Partner & Affiliate Intelligence",
    x: 70,
    y: 65,
    prioritized: true,
    valueDescription: "Opposite trading arbitrage detection, $42.5k clawbacks, IB lot volume",
    feasibilityFactors: "Affiliate portal metadata, daily rev-share payment ledger",
    dataProducts: ["Affiliate Tree", "Trade Correlation Matrix", "Commission Ledger"],
    primaryKpi: "Protected Payouts: $42.5k/mo",
  },
  {
    id: "competitive-intel",
    name: "Competitive Intelligence",
    x: 62,
    y: 60,
    prioritized: true,
    valueDescription: "Exness/XM spread tracking, partner poaching NLP extraction",
    feasibilityFactors: "Public broker APIs, Zendesk support tickets, news scrapers",
    dataProducts: ["Competitor Spread Feeds", "Partner Poaching Signal Store"],
    primaryKpi: "Churn Prevention: $1.24M ARR",
  },
  {
    id: "financial-book",
    name: "Financial & Dealer B-Book",
    x: 42,
    y: 82,
    prioritized: false,
    valueDescription: "Synthetic indices margin yield, A-Book LP hedging cost optimization",
    feasibilityFactors: "Complex liquidity provider matching engine, multi-currency accounting",
    dataProducts: ["LP Order Book Stream", "Synthetics B-Book Yield Engine"],
    primaryKpi: "Dealer Net Margin: +1.8%",
  },
  {
    id: "operational-health",
    name: "Operational Health & MT5 Latency",
    x: 48,
    y: 35,
    prioritized: false,
    valueDescription: "MT5 gateway latency (sub-15ms), WebSocket tick drops, DP2P escrow speed",
    feasibilityFactors: "Raw socket telemetries, infrastructure DevOps logging",
    dataProducts: ["Network Latency Ledger", "DP2P Dispute Monitor"],
    primaryKpi: "Avg Tick Latency: 11.4ms",
  },
];

export function DomainPrioritizationMatrix() {
  const [selectedDomain, setSelectedDomain] = useState<DomainInfo>(DOMAINS[0]);

  return (
    <section id="domains-matrix" className="py-[var(--spacing-lg)] px-6 sm:px-12 lg:px-16 max-w-[1440px] mx-auto border-t border-[var(--color-border)]">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-[var(--spacing-md)] pb-6 border-b border-[var(--color-border)] gap-6">
        <div>
          <div className="text-overline text-[var(--color-brand-secondary)] mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--color-brand-secondary)]" />
            Exhibit 2.2 Reimagined
          </div>
          <h2 className="text-headline-md text-[var(--color-brand-primary)]">
            Domains Prioritized on Value & Feasibility
          </h2>
          <p className="text-body-md text-[var(--color-brand-secondary)] mt-4 max-w-2xl">
            Following institutional strategic roadmapping, capital market domains are mapped across executive feasibility and enterprise financial yield.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-[var(--spacing-md)] items-start">
        {/* Interactive 2x2 Scatter Plot (7 cols) */}
        <div className="lg:col-span-7 bg-[var(--color-surface-base)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-[var(--spacing-sm)] relative">
          <div className="flex items-center justify-between text-label-sm text-[var(--color-brand-secondary)] mb-4">
            <span className="text-[var(--color-brand-primary)]">▲ HIGH ENTERPRISE VALUE</span>
            <span>EXHIBIT 2.2 MATRIX</span>
          </div>

          <div className="relative w-full h-[400px] bg-[var(--color-background)] border border-[var(--color-border)] rounded-[var(--radius-md)] p-4 overflow-hidden">
            {/* Coordinate Lines */}
            <div className="absolute left-0 top-1/2 w-full h-[1px] border-t border-dashed border-[var(--color-border)] opacity-50" />
            <div className="absolute top-0 left-1/2 h-full w-[1px] border-l border-dashed border-[var(--color-border)] opacity-50" />

            {/* Render Domain Nodes */}
            {DOMAINS.map((domain) => {
              const isSelected = selectedDomain.id === domain.id;
              return (
                <button
                  key={domain.id}
                  onClick={() => setSelectedDomain(domain)}
                  style={{ left: `${domain.x}%`, bottom: `${domain.y}%` }}
                  className="absolute -translate-x-1/2 translate-y-1/2 z-20 flex flex-col items-center group focus:outline-none"
                >
                  <div
                    className={`w-4 h-4 rounded-full flex items-center justify-center transition-colors ${
                      isSelected
                        ? "bg-[var(--color-brand-primary)] scale-125"
                        : domain.prioritized
                        ? "bg-[var(--color-brand-secondary)] hover:bg-[var(--color-brand-primary)]"
                        : "bg-transparent border border-[var(--color-brand-secondary)] hover:border-[var(--color-brand-primary)]"
                    }`}
                  />
                  <span
                    className={`text-[10px] mt-2 whitespace-nowrap px-1.5 py-0.5 ${
                      isSelected
                        ? "text-[var(--color-brand-neutral)] bg-[var(--color-brand-primary)]"
                        : "text-[var(--color-brand-secondary)] bg-[var(--color-background)] opacity-0 group-hover:opacity-100"
                    }`}
                  >
                    {domain.name.split(" ")[0]}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-label-sm text-[var(--color-brand-secondary)] mt-4 border-t border-[var(--color-border)] pt-4">
            <span>LOW FEASIBILITY</span>
            <span className="text-[var(--color-brand-primary)]">HIGH FEASIBILITY ▶</span>
          </div>
        </div>

        {/* Selected Domain Deep Dive Card (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <Card className="h-full bg-[var(--color-surface-base)]">
            <CardContent className="flex flex-col h-full pt-6">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4 mb-6">
                <div className="text-label-sm text-[var(--color-brand-secondary)] uppercase tracking-wider">Domain Architecture Profile</div>
              </div>

              <h3 className="text-headline-sm text-[var(--color-brand-primary)] mb-2">
                {selectedDomain.name}
              </h3>
              <p className="text-body-sm text-[var(--color-brand-secondary)] mb-6">
                {selectedDomain.valueDescription}
              </p>

              <div className="bg-[var(--color-background)] p-4 border border-[var(--color-border)] rounded-[var(--radius-md)] mb-6">
                <div className="text-label-sm text-[var(--color-brand-secondary)] uppercase mb-2">Feasibility Assessment</div>
                <div className="text-body-sm text-[var(--color-brand-primary)] mb-4">{selectedDomain.feasibilityFactors}</div>
                <div className="pt-4 border-t border-[var(--color-border)] flex items-center justify-between text-label-sm">
                  <span className="text-[var(--color-brand-secondary)]">Target Value Lever:</span>
                  <span className="text-[var(--color-brand-primary)]">{selectedDomain.primaryKpi}</span>
                </div>
              </div>

              <div>
                <div className="text-label-sm text-[var(--color-brand-secondary)] mb-3">Decoupled Data Products</div>
                <div className="flex flex-wrap gap-2">
                  {selectedDomain.dataProducts.map((product, i) => (
                    <div
                      key={i}
                      className="bg-[var(--color-background)] px-3 py-1.5 border border-[var(--color-border)] rounded-[var(--radius-sm)] text-label-md text-[var(--color-brand-primary)]"
                    >
                      {product}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
