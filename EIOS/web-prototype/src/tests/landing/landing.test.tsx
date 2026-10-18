import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Close } from "@/components/landing/Close";
import { FIELD_NOTES, LAYERS, RED_LINES, RESULTS } from "@/components/landing/content";
import { FieldNotes } from "@/components/landing/FieldNotes";
import { RedLines } from "@/components/landing/RedLines";
import { ResultsLedger } from "@/components/landing/ResultsLedger";
import { SiteNav } from "@/components/landing/SiteNav";
import { StackHero } from "@/components/landing/StackHero";

describe("landing content", () => {
  it("keeps the five layers in data order with at most four legend lines each", () => {
    expect(LAYERS.map((l) => l.n)).toEqual([1, 2, 3, 4, 5]);
    for (const layer of LAYERS) expect(layer.legend.length).toBeLessThanOrEqual(4);
  });

  it("states the two red lines that are not measured live instead of hiding them", () => {
    const open = RED_LINES.filter((r) => r.status !== "MEASURED").map((r) => r.id);
    expect(open).toEqual(["RL-2", "RL-7"]);
    expect(RED_LINES).toHaveLength(7);
  });

  it("keeps at least one missed result in the ledger", () => {
    expect(RESULTS.some((r) => r.kind === "miss")).toBe(true);
    expect(FIELD_NOTES.length).toBeGreaterThan(0);
  });
});

describe("landing sections", () => {
  it("opens the app on its first section (geospatial) from the nav and the close", () => {
    render(
      <>
        <SiteNav />
        <Close />
      </>,
    );
    const links = screen.getAllByRole("link", { name: /open the workstation/i });
    expect(links).toHaveLength(2);
    for (const link of links) expect(link).toHaveAttribute("href", "/cockpit/geospatial");
  });

  it("renders the hero with one legend band per layer and an accessible diagram", () => {
    render(<StackHero />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    const legend = screen.getByRole("list", { name: /five layers/i });
    expect(within(legend).getAllByText(/^(Worlds|Ingestion|Ontology|Assistant|Workstations)$/)).toHaveLength(5);
    expect(screen.getByRole("img", { name: /exploded isometric diagram/i })).toBeInTheDocument();
  });

  it("tags every ledger row as measured and labels how each one held", () => {
    render(<ResultsLedger />);
    expect(screen.getAllByText("MEASURED")).toHaveLength(RESULTS.length);
    expect(screen.getByText("Missed")).toBeInTheDocument();
  });

  it("lists all seven red lines and every field note", () => {
    render(
      <>
        <RedLines />
        <FieldNotes />
      </>,
    );
    expect(screen.getAllByText(/^RL-\d$/)).toHaveLength(7);
    expect(screen.getAllByText(/^Before$/)).toHaveLength(FIELD_NOTES.length);
  });
});
