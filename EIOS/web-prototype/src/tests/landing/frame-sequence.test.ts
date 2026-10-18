import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FrameSequence } from "@/components/landing/frameSequence";
import { landingAsset, landingSrcSet, LANDING_ASSET_VERSION } from "@/components/landing/assets";

interface FakeBitmap {
  readonly url: string;
  close: ReturnType<typeof vi.fn>;
}

const settle = async (): Promise<void> => {
  for (let i = 0; i < 6; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
};

describe("FrameSequence", () => {
  let bitmaps: FakeBitmap[];
  let requested: string[];
  let failing: (url: string) => boolean;

  beforeEach(() => {
    bitmaps = [];
    requested = [];
    failing = () => false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        requested.push(url);
        if (failing(url)) return { ok: false, status: 404 } as Response;
        return { ok: true, blob: async () => ({ url }) } as unknown as Response;
      }),
    );
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(async (blob: { url: string }) => {
        const bitmap: FakeBitmap = { url: blob.url, close: vi.fn() };
        bitmaps.push(bitmap);
        return bitmap;
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const make = (extra: Partial<ConstructorParameters<typeof FrameSequence>[0]> = {}) => {
    const onFrame = vi.fn();
    const onUnavailable = vi.fn();
    const seq = new FrameSequence({
      count: 81,
      step: 1,
      radius: 3,
      anchorEvery: 20,
      src: (i) => `/f/${i}`,
      onFrame,
      onUnavailable,
      ...extra,
    });
    return { seq, onFrame, onUnavailable };
  };

  it("loads the window around the target and the anchors, not the whole clip", async () => {
    const { seq } = make({ concurrency: 50 });
    seq.want(40);
    await settle();
    expect([...requested].sort()).toEqual(
      ["/f/0", "/f/20", "/f/37", "/f/38", "/f/39", "/f/40", "/f/41", "/f/42", "/f/43", "/f/60", "/f/80"].sort(),
    );
  });

  it("asks for the frame being shown first, then the anchors, then the rest of the window", async () => {
    const { seq } = make({ concurrency: 1 });
    seq.want(40);
    await settle();
    expect(requested[0]).toBe("/f/40");
    const anchorAt = requested.indexOf("/f/20");
    const edgeAt = requested.indexOf("/f/37");
    expect(anchorAt).toBeGreaterThan(-1);
    expect(anchorAt).toBeLessThan(edgeAt);
  });

  it("lets a request just outside the moved window finish but drops its frame", async () => {
    const { seq } = make({ concurrency: 50 });
    seq.want(40);
    seq.want(42); // the window is now 39 to 45; 37 is outside it but within twice the radius, so it is not aborted
    await settle();
    expect(seq.nearest(37)?.index).not.toBe(37);
    const stale = bitmaps.find((b) => b.url === "/f/37");
    expect(stale?.close).toHaveBeenCalled();
  });

  it("closes frames that fall out of the window when the target moves", async () => {
    const { seq } = make({ concurrency: 50 });
    seq.want(40);
    await settle();
    const first = bitmaps.find((b) => b.url === "/f/37");
    seq.want(60);
    expect(first?.close).toHaveBeenCalled();
    const anchor = bitmaps.find((b) => b.url === "/f/20");
    expect(anchor?.close).not.toHaveBeenCalled();
  });

  it("shows the nearest loaded frame while the exact one is still coming", async () => {
    const { seq } = make({ concurrency: 50 });
    seq.want(30);
    await settle();
    expect(seq.nearest(30)?.index).toBe(30);
    // radius 3 holds 27 to 33, so 34 is not held and the nearest held frame answers
    expect(seq.nearest(34)?.index).toBe(33);
  });

  it("loads every other frame on small screens", async () => {
    const { seq } = make({ step: 2, concurrency: 50 });
    seq.want(40);
    await settle();
    expect(requested.every((u) => Number(u.split("/").pop()) % 2 === 0)).toBe(true);
  });

  it("frees every frame and starts clean after release", async () => {
    const { seq } = make({ concurrency: 50 });
    seq.want(10);
    await settle();
    const held = [...bitmaps];
    seq.release();
    expect(held.every((b) => b.close.mock.calls.length === 1)).toBe(true);
    expect(seq.nearest(10)).toBeUndefined();
    seq.want(10);
    await settle();
    expect(seq.nearest(10)?.index).toBe(10);
  });

  it("reports unavailable when nothing loads, after one retry each", async () => {
    failing = () => true;
    vi.useFakeTimers();
    const { seq, onUnavailable } = make({ concurrency: 4 });
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    seq.want(0);
    await vi.runAllTimersAsync();
    vi.useRealTimers();
    expect(onUnavailable).toHaveBeenCalled();
    expect(requested.length).toBeGreaterThanOrEqual(8);
    error.mockRestore();
  });

  it("does not report unavailable when only some frames fail", async () => {
    failing = (u) => u === "/f/38";
    vi.useFakeTimers();
    const { seq, onUnavailable } = make({ concurrency: 50 });
    seq.want(40);
    await vi.runAllTimersAsync();
    vi.useRealTimers();
    expect(onUnavailable).not.toHaveBeenCalled();
    expect(seq.nearest(38)?.index).not.toBe(38);
  });
});

describe("landing asset urls", () => {
  it("versions every raster so the immutable cache can be busted", () => {
    expect(landingAsset("orbit/f_001.webp")).toBe(`/landing/orbit/f_001.webp?v=${LANDING_ASSET_VERSION}`);
  });

  it("builds a width-described srcset ending at the full-size file", () => {
    const set = landingSrcSet("workstation-aml", [1200, 1800], 2400);
    expect(set.split(", ")).toEqual([
      `${landingAsset("workstation-aml-1200.webp")} 1200w`,
      `${landingAsset("workstation-aml-1800.webp")} 1800w`,
      `${landingAsset("workstation-aml.webp")} 2400w`,
    ]);
  });
});
