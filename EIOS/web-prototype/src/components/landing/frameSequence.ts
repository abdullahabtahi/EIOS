/**
 * Scroll-driven frame sequences keep only a window of decoded frames in memory.
 * Decoded RGBA is about 3 MB a frame, so holding a whole clip (81 and 65 frames) costs hundreds of MB.
 * The window follows the scroll position, sparse anchor frames stay for fast scrolls, and `release` frees it all.
 */

export interface FrameSequenceOptions {
  readonly count: number;
  /** 1 loads every frame, 2 every other frame (small screens). */
  readonly step: number;
  readonly src: (index: number) => string;
  /** Frames kept on either side of the frame being shown. */
  readonly radius?: number;
  /** One anchor frame in this many stays loaded while the sequence is active. */
  readonly anchorEvery?: number;
  readonly concurrency?: number;
  /** A frame arrived, so the owner can redraw. */
  readonly onFrame: () => void;
  /** Nothing could be loaded at all: the owner should show a still instead. */
  readonly onUnavailable: () => void;
}

export interface LoadedFrame {
  readonly index: number;
  readonly bitmap: ImageBitmap;
}

/** Frames this close to the shown one are fetched before anything else. */
const NEAR = 2;
const ATTEMPTS = 2;
const RETRY_DELAY_MS = 400;

const wait = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchBitmap(url: string, signal: AbortSignal): Promise<ImageBitmap> {
  let lastError: unknown;
  for (let attempt = 0; attempt < ATTEMPTS; attempt += 1) {
    try {
      const res = await fetch(url, { signal });
      if (!res.ok) throw new Error(`${url} answered ${res.status}`);
      return await createImageBitmap(await res.blob());
    } catch (err) {
      if (signal.aborted) throw err;
      lastError = err;
      await wait(RETRY_DELAY_MS * (attempt + 1));
    }
  }
  throw lastError;
}

export class FrameSequence {
  private readonly opts: Required<Omit<FrameSequenceOptions, "onFrame" | "onUnavailable">> &
    Pick<FrameSequenceOptions, "onFrame" | "onUnavailable">;
  private readonly bitmaps = new Map<number, ImageBitmap>();
  private readonly inflight = new Map<number, AbortController>();
  private readonly failed = new Set<number>();
  private desired: readonly number[] = [];
  private center = -1;
  private active = false;

  constructor(opts: FrameSequenceOptions) {
    this.opts = { radius: 10, anchorEvery: 8, concurrency: 4, ...opts };
  }

  /** True for the indices this sequence actually loads. */
  private isStop(i: number): boolean {
    return i >= 0 && i < this.opts.count && (i % this.opts.step === 0 || i === this.opts.count - 1);
  }

  /**
   * Frames to hold for a centre. The few frames at the centre come first, then the anchors, then the rest of the
   * window: under fast scrolling the window keeps moving, so anchors must not wait behind frames that get dropped.
   */
  private plan(center: number): readonly number[] {
    const { count, radius, anchorEvery } = this.opts;
    const byDistance = (a: number, b: number): number => Math.abs(a - center) - Math.abs(b - center);
    const window: number[] = [];
    for (let i = center - radius; i <= center + radius; i += 1) if (this.isStop(i)) window.push(i);
    const anchors: number[] = [];
    for (let i = 0; i < count; i += 1) {
      if (this.isStop(i) && (i % anchorEvery === 0 || i === count - 1) && !window.includes(i)) anchors.push(i);
    }
    const sorted = window.sort(byDistance);
    const near = sorted.filter((i) => Math.abs(i - center) <= NEAR);
    return [...near, ...anchors.sort(byDistance), ...sorted.filter((i) => Math.abs(i - center) > NEAR)];
  }

  /** The loaded frame closest to `target`, or undefined while nothing has arrived. */
  nearest(target: number): LoadedFrame | undefined {
    for (let d = 0; d < this.opts.count; d += 1) {
      for (const i of d === 0 ? [target] : [target - d, target + d]) {
        const bitmap = this.bitmaps.get(i);
        if (bitmap) return { index: i, bitmap };
      }
    }
    return undefined;
  }

  /** Move the window to `center` and fetch whatever it is missing. A no-op while inactive or unmoved. */
  want(center: number): void {
    this.active = true;
    if (center === this.center) return;
    this.center = center;
    this.desired = this.plan(center);
    const keep = new Set(this.desired);
    for (const [i, bitmap] of this.bitmaps) {
      if (!keep.has(i)) {
        bitmap.close();
        this.bitmaps.delete(i);
      }
    }
    // A request just outside the window is left to finish (it is dropped on arrival) so a moving window cannot starve every fetch.
    for (const [i, controller] of this.inflight) {
      if (!keep.has(i) && Math.abs(i - center) > this.opts.radius * 2) {
        controller.abort();
        this.inflight.delete(i);
      }
    }
    this.pump();
  }

  /** Free every frame and stop every request. `want` starts it again. */
  release(): void {
    this.active = false;
    this.center = -1;
    this.desired = [];
    for (const controller of this.inflight.values()) controller.abort();
    this.inflight.clear();
    for (const bitmap of this.bitmaps.values()) bitmap.close();
    this.bitmaps.clear();
    this.failed.clear();
  }

  private pump(): void {
    for (const i of this.desired) {
      if (this.inflight.size >= this.opts.concurrency) return;
      if (this.bitmaps.has(i) || this.inflight.has(i) || this.failed.has(i)) continue;
      void this.load(i);
    }
  }

  private async load(i: number): Promise<void> {
    const controller = new AbortController();
    this.inflight.set(i, controller);
    try {
      const bitmap = await fetchBitmap(this.opts.src(i), controller.signal);
      if (controller.signal.aborted || !this.active || !this.desired.includes(i)) {
        bitmap.close();
        return;
      }
      this.bitmaps.set(i, bitmap);
      this.opts.onFrame();
    } catch (err) {
      if (controller.signal.aborted) return;
      this.failed.add(i);
      if (this.bitmaps.size === 0 && this.failed.size >= this.opts.concurrency) {
        console.error("landing frame sequence unavailable", err);
        this.opts.onUnavailable();
      }
    } finally {
      if (this.inflight.get(i) === controller) this.inflight.delete(i);
      if (this.active) this.pump();
    }
  }
}
