import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Architecture } from "@/components/landing/architecture/Architecture";
import { Capabilities } from "@/components/landing/capabilities/Capabilities";
import { ATTRIBUTION, CAUSAL_EDGES, WHAT_IF } from "@/components/landing/data/causal";
import { CENTROIDS, CORRIDORS, GATEWAYS } from "@/components/landing/data/geo";
import { NODES, TRACES } from "@/components/landing/data/architecture";
import { GEO_TURNS } from "@/components/landing/data/turns";
import { GeoSection } from "@/components/landing/geo/GeoSection";
import { viewFor } from "@/components/landing/geo/geoLayers";
import { Problem } from "@/components/landing/Problem";

describe("baked engine snapshots", () => {
  it("keeps attribution closed at 100% and marks out-of-history shocks as correlation only", () => {
    const sum = Object.values(ATTRIBUTION).reduce((a, b) => a + b, 0);
    expect(sum).toBeCloseTo(100, 2);
    expect(WHAT_IF.find((s) => s.pct === 0)?.causal).toBe(true);
    expect(WHAT_IF.find((s) => s.pct === 50)?.causal).toBe(false);
    expect(CAUSAL_EDGES.some((e) => !e.verified)).toBe(true);
  });

  it("has a centroid for every corridor end and gateway country", () => {
    for (const c of CORRIDORS) {
      expect(CENTROIDS[c[0]]).toBeDefined();
      expect(CENTROIDS[c[1]]).toBeDefined();
    }
    for (const g of GATEWAYS) {
      expect(CENTROIDS[g.iso2]).toBeDefined();
      for (const [iso] of g.homes) expect(CENTROIDS[iso]).toBeDefined();
    }
  });

  it("only traces through nodes that exist on the diagram", () => {
    const ids = new Set(NODES.map((n) => n.id));
    for (const steps of Object.values(TRACES)) for (const s of steps) expect(ids.has(s.node)).toBe(true);
  });

  it("frames every recorded turn's focus inside the world", () => {
    for (const t of GEO_TURNS) {
      const v = viewFor(t.focus);
      expect(Math.abs(v.latitude)).toBeLessThanOrEqual(90);
      expect(v.zoom).toBeGreaterThanOrEqual(1.2);
    }
  });
});

describe("interactive sections", () => {
  it("links each finding to the capability that answers it", () => {
    render(<Problem />);
    expect(screen.getAllByRole("link", { name: /^(Network science|Causal inference|Financial geospatial|Agentic AI|Governed action)$/ })).toHaveLength(5);
  });

  it("switches capability tabs and lets the ring suppression be toggled", () => {
    render(<Capabilities />);
    const toggle = screen.getByRole("button", { name: /hub suppression/i });
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(toggle);
    expect(screen.getByText(/false merge/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /governed action/i }));
    expect(screen.getByRole("tab", { name: /governed action/i })).toHaveAttribute("aria-selected", "true");
  });

  it("refuses an approval by the proposer", () => {
    render(<Capabilities />);
    fireEvent.click(screen.getByRole("tab", { name: /governed action/i }));
    fireEvent.click(screen.getByRole("button", { name: /stage and sign/i }));
    fireEvent.click(screen.getByRole("button", { name: /approve as the proposer/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/cannot approve/i);
  });

  it("replays a recorded geo turn verbatim", () => {
    render(<GeoSection />);
    const turn = GEO_TURNS[1];
    fireEvent.click(screen.getByRole("button", { name: turn.question }));
    expect(screen.getByText(turn.answer.split("\n")[0], { exact: false })).toBeInTheDocument();
  });

  it("shows a component's Google Cloud service when selected", () => {
    render(<Architecture />);
    fireEvent.click(screen.getByRole("button", { name: /bigquery graph, runs on/i }));
    const panel = screen.getByRole("complementary");
    expect(within(panel).getByRole("heading", { name: "BigQuery Graph" })).toBeInTheDocument();
  });
});
