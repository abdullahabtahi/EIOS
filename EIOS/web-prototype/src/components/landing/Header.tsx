"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Cpu, Activity, ShieldCheck } from "lucide-react";

interface HeaderProps {
  onEnterCockpit?: () => void;
}

export function Header({ onEnterCockpit }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/90 backdrop-blur-md">
      {/* Top tier: System Status */}
      <div className="h-7 w-full border-b border-border bg-background px-4 flex items-center justify-between text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-1.5 text-green-600">
            <span className="w-1.5 h-1.5 bg-green-600 rounded-full" />
            System Active
          </span>
          <span className="hidden sm:inline-flex items-center gap-1">
            <Activity className="w-3 h-3" />
            MTS Core: <strong className="text-foreground font-normal ml-0.5">11.5ms</strong>
          </span>
          <span className="hidden md:inline-flex">
            24H Certified Volume: <strong className="text-foreground font-normal ml-0.5">$2,418,921,122</strong>
          </span>
          <span className="hidden lg:inline-flex text-amber-600">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            Causal FP Reduction: 95.2%
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden md:flex items-center gap-1 text-primary">
            <ShieldCheck className="w-3 h-3" />
            Regulatory Compliant: MFSA • LFSA • FSC
          </span>
          <span className="text-muted-foreground">|</span>
          <span>McKinsey Rewired 2nd Ed. Compliant</span>
        </div>
      </div>

      {/* Main Nav */}
      <div className="flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-secondary border border-border rounded-sm text-primary">
            <Cpu className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-foreground">FEIOS</span>
              <span className="text-[9px] font-mono bg-primary text-primary-foreground px-1 py-0.5 rounded-sm leading-none">v2.6.4</span>
            </div>
            <span className="text-[10px] text-muted-foreground hidden sm:block font-semibold uppercase tracking-widest">Financial Enterprise Intelligence OS</span>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-6">
          <a href="#sandbox" className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5 font-medium">
            <span className="w-1 h-1 rounded-full bg-primary"></span>
            Causal Simulator
          </a>
          <a href="#domains" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">The 6 Domains</a>
          <a href="#architecture-exhibit" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">Lakehouse Architecture</a>
          <a href="#reimagination-steps" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">5-Step Blueprint</a>
          <a href="#moat-matrix" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">Enterprise Moats</a>
        </nav>

        <div className="flex items-center gap-3">
          <Button onClick={onEnterCockpit} variant="default" size="sm" className="hidden sm:inline-flex">
            Enter Secure Cockpit →
          </Button>
        </div>
      </div>
    </header>
  );
}
