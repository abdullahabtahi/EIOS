"use client";

import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

export function DomainReimaginationSteps() {
  const [activeStep, setActiveStep] = useState(1);

  const steps = [
    { num: 1, title: "Identify Value Levers", desc: "Map broker operations to measurable P&L levers." },
    { num: 2, title: "Design the Future State", desc: "Storyboard the 'to-be' processes with Causal AI." },
    { num: 3, title: "Data Product Architecture", desc: "Define bounded data domains (e.g. Client 360)." },
    { num: 4, title: "Deploy AI & Engine Models", desc: "Integrate DoWhy Causal DAGs and LLMs." },
    { num: 5, title: "Operational Write-backs", desc: "Enable 2PC automated ledger writes." }
  ];

  return (
    <section id="reimagination-steps" className="py-24 px-6 sm:px-12 lg:px-16 max-w-7xl mx-auto border-t border-border">
      <div className="mb-12 pb-6 border-b border-border">
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
          Exhibit 3.1 Reimagined
        </div>
        <h2 className="text-3xl font-bold text-foreground">
          5-Step Domain Reimagination
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        {steps.map(step => (
          <Card 
            key={step.num} 
            onMouseEnter={() => setActiveStep(step.num)}
            className={`cursor-default transition-colors ${activeStep === step.num ? 'bg-background border-primary' : 'bg-transparent border-border'}`}
          >
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-muted-foreground mb-4">0{step.num}</div>
              <h3 className="text-base font-bold text-foreground mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
