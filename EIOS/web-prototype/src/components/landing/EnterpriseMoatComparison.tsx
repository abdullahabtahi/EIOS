"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";

export function EnterpriseMoatComparison() {
  const moats = [
    { title: "Legacy PowerBI / Tableau", desc: "Read-only backward-looking dashboards. No write-back capabilities." },
    { title: "Standard Databricks / Snowflake", desc: "Expensive warehouse compute. Requires batch ELT processing." },
    { title: "EIOS Sovereign Intelligence Moat", desc: "Zero-ETL Lakehouse, Sub-10ms queries, Causal AI inference, and 2PC write-backs directly to the broker ledger." }
  ];

  return (
    <section id="moat-matrix" className="py-24 px-6 sm:px-12 lg:px-16 max-w-7xl mx-auto border-t border-border">
      <div className="mb-12 pb-6 border-b border-border">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
          Competitive Moat
        </div>
        <h2 className="text-3xl font-bold text-foreground">
          The Enterprise Advantage
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {moats.map((moat, i) => (
          <Card key={i} className={`bg-transparent rounded-sm ${i === 2 ? 'border-primary bg-card' : 'border-border'}`}>
            <CardContent className="pt-6">
              <h3 className="text-base font-bold text-foreground mb-4">{moat.title}</h3>
              <p className="text-sm text-muted-foreground">{moat.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
