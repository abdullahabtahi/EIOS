import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RESULTS } from "@/components/landing/content";
import { RESULT_CHARTS } from "@/components/landing/data/charts";
import { MiniChart } from "@/components/landing/MiniChart";
import { ResultsLedger } from "@/components/landing/ResultsLedger";

describe("landing charts", () => {
  it("only charts rows that exist", () => {
    const whats = new Set(RESULTS.map((r) => r.what));
    for (const key of Object.keys(RESULT_CHARTS)) expect(whats.has(key)).toBe(true);
  });

  it("keeps every plotted value inside its own scale", () => {
    const all = Object.values(RESULT_CHARTS).flat();
    for (const c of all) {
      if (c.kind === "track") for (const m of c.marks) expect(m.at >= c.min && m.at <= c.max).toBe(true);
      if (c.kind === "fill") expect(c.value <= c.of).toBe(true);
      if (c.kind === "units") expect(c.filled <= c.total).toBe(true);
    }
  });

  it("states each plotted number in the row's own copy", () => {
    const row = (what: string) => RESULTS.find((r) => r.what === what)!;
    expect(row("Revenue forecast").result).toMatch(/0\.74/);
    expect(row("Revenue forecast").result).toMatch(/87%/);
    expect(row("Churn hazard calibration").result).toMatch(/0\.43/);
    expect(row("Churn hazard calibration").result).toMatch(/0\.21/);
    expect(row("Ring-exit detection on the map").against).toMatch(/0\.86/);
    expect(row("Causal fit against the planted chain").result).toMatch(/1\.5%/);
  });

  it("draws a fill, a unit chart and a track", () => {
    const { container } = render(
      <>
        <MiniChart chart={{ kind: "fill", value: 50, of: 100, label: "x", unit: "%" }} />
        <MiniChart chart={{ kind: "units", filled: 3, total: 5, label: "ok" }} />
        <MiniChart
          chart={{ kind: "track", min: 0, max: 10, unit: "u", ticks: [0, 10], marks: [{ at: 5, label: "mid", tone: "main" }] }}
        />
      </>,
    );
    expect(container.querySelectorAll(".fde-mc-cells .is-on")).toHaveLength(3);
    expect(screen.getByText("mid")).toBeInTheDocument();
    expect(screen.getByText(/3 of 5 ok/)).toBeInTheDocument();
  });

  it("keeps one ledger row per result", () => {
    const { container } = render(<ResultsLedger />);
    expect(container.querySelectorAll(".fde-ledger > li")).toHaveLength(RESULTS.length);
  });
});
