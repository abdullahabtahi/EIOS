import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OrbitSequence } from "@/components/landing/OrbitSequence";
import { PushIn } from "@/components/landing/PushIn";

// jsdom has no createImageBitmap, which stands in for a browser that cannot play the clips.
describe("scroll-driven sequences without bitmap decoding", () => {
  it("falls back to the still and the full captions instead of an empty canvas", async () => {
    const { container } = render(<OrbitSequence />);
    await waitFor(() => expect(container.querySelector(".fde-system-static")).not.toBeNull());
    expect(container.querySelector("canvas")).toBeNull();
    expect(container.querySelector("img")?.getAttribute("src")).toMatch(/^\/landing\/orbit\/f_041\.webp\?v=/);
    expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(5);
  });

  it("falls back to the last push frame and says six workstations", async () => {
    const { container } = render(<PushIn />);
    await waitFor(() => expect(container.querySelector(".fde-push-static")).not.toBeNull());
    expect(container.querySelector("img")?.getAttribute("src")).toMatch(/^\/landing\/push\/f_065\.webp\?v=/);
    expect(screen.getByText(/^Six workstations/)).toBeInTheDocument();
  });
});
