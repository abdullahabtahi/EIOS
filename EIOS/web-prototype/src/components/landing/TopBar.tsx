"use client";

import React, { useState, useEffect } from "react";
import { Icon } from "@/components/ui/icon";

export function TopBar() {
  const [latency, setLatency] = useState(11.4);
  const [volume, setVolume] = useState(2418920400);

  useEffect(() => {
    const interval = setInterval(() => {
      setLatency(() => +(11.0 + Math.random() * 0.8).toFixed(1));
      setVolume((prev) => prev + Math.floor(Math.random() * 5000));
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-[#04070c] border-b border-[var(--stroke-primary)] text-[11px] py-1.5 px-4 sm:px-8 flex flex-wrap items-center justify-between text-[var(--text-secondary)] font-mono tracking-wide z-50">
      <div className="flex items-center gap-4 sm:gap-6 overflow-x-auto py-0.5">
        <div className="flex items-center gap-1.5 text-[var(--text-success)] font-semibold">
          <span className="w-2 h-2 rounded-full bg-[var(--fill-success)] animate-pulse"></span>
          <span>SYSTEM ACTIVE</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Icon icon="dns" size="sm" className="text-[var(--color-brand-accents-mckinsey-cyan)]" />
          <span>MT5 CORE:</span>
          <span className="text-[var(--text-primary)]">{latency}ms</span>
        </div>
        <div className="hidden md:flex items-center gap-1.5">
          <Icon icon="monitoring" size="sm" className="text-[var(--color-brand-accents-electric-blue)]" />
          <span>24H CERTIFIED VOLUME:</span>
          <span className="text-[var(--text-primary)] font-semibold">
            ${volume.toLocaleString()}
          </span>
        </div>
        <div className="hidden lg:flex items-center gap-1.5">
          <Icon icon="bolt" size="sm" className="text-[var(--text-warning)]" />
          <span>CAUSAL FP REDUCTION:</span>
          <span className="text-[var(--text-success)] font-semibold">95.2%</span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-[10px] text-[var(--text-tertiary)]">
        <span className="flex items-center gap-1">
          <Icon icon="verified_user" size="sm" className="text-[var(--color-brand-accents-mckinsey-cyan)]" />
          REGULATORY COMPLIANT: MFSA • LFSA • FSC
        </span>
        <span className="hidden sm:inline text-[var(--stroke-primary)]">|</span>
        <span className="hidden sm:inline text-[var(--text-tertiary)]">MCKINSEY REWIRED 2ND ED. COMPLIANT</span>
      </div>
    </div>
  );
}
