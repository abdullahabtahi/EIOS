"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface FooterProps {
  onEnterCockpit?: () => void;
}

export function Footer({ onEnterCockpit }: FooterProps) {
  return (
    <footer className="bg-[var(--color-background)] border-t border-[var(--color-border)] py-[var(--spacing-lg)]">
      <div className="max-w-[1440px] mx-auto px-6 sm:px-12 lg:px-16 flex flex-col md:flex-row justify-between items-center gap-6">
        <div>
          <div className="text-label-lg font-bold text-[var(--color-brand-primary)] mb-1">FEIOS</div>
          <div className="text-body-sm text-[var(--color-brand-secondary)]">Financial Enterprise Intelligence Operating System</div>
        </div>
        <div className="flex gap-4">
          <Button variant="secondary" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            Back to Top
          </Button>
          <Button variant="default" onClick={onEnterCockpit}>
            Launch Cockpit
          </Button>
        </div>
      </div>
    </footer>
  );
}
