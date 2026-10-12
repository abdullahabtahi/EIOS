"use client";

import React from "react";
import { Header } from "@/components/landing/Header";
import { HeroSection } from "@/components/landing/HeroSection";
import { InteractiveSandbox } from "@/components/landing/InteractiveSandbox";
import { DomainReimaginationSteps } from "@/components/landing/DomainReimaginationSteps";
import { ModernArchitectureExhibit } from "@/components/landing/ModernArchitectureExhibit";
import { EnterpriseMoatComparison } from "@/components/landing/EnterpriseMoatComparison";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground font-sans">
      <Header onEnterCockpit={() => router.push("/cockpit")} />
      <main className="flex-1">
        <HeroSection />
        <InteractiveSandbox />
        <DomainReimaginationSteps />
        <ModernArchitectureExhibit />
        <EnterpriseMoatComparison />
      </main>
      <footer className="py-6 border-t border-border bg-muted flex items-center justify-between px-6 sm:px-12 lg:px-16 text-sm text-muted-foreground">
        <div className="font-bold text-foreground">FEIOS</div>
        <div>Financial Enterprise Intelligence Operating System</div>
        <div>
          <button
            type="button"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="hover:text-foreground mr-4 cursor-pointer"
          >
            Back to Top
          </button>
          <Link
            href="/cockpit"
            className="font-bold text-foreground hover:underline inline-flex items-center gap-1"
          >
            Launch Cockpit →
          </Link>
        </div>
      </footer>
    </div>
  );
}
