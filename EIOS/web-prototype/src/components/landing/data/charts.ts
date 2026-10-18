/**
 * Chart specs for the results ledger and the field notes. Every value is copied from the row it sits beside in
 * content.ts (which cites the harness report); nothing here is derived or rounded differently.
 */

export interface Mark {
  readonly at: number;
  readonly label: string;
  /** "ref" is a bar or budget the result is held to; "hollow" is the weaker or earlier value. */
  readonly tone: "main" | "ref" | "hollow";
}

export type Chart =
  | { readonly kind: "fill"; readonly value: number; readonly of: number; readonly label: string; readonly unit: string }
  | { readonly kind: "units"; readonly filled: number; readonly total: number; readonly label: string }
  | {
      readonly kind: "track";
      readonly min: number;
      readonly max: number;
      readonly unit: string;
      readonly marks: readonly Mark[];
      /** Draw a band between two marks (by index). */
      readonly span?: readonly [number, number];
      readonly ticks: readonly number[];
    };

/** Keyed by the `what` of a RESULTS row. A row may carry two charts (a second, labelled track). */
export const RESULT_CHARTS: Readonly<Record<string, readonly Chart[]>> = {
  "Live agent evaluation, development and validation splits": [
    { kind: "fill", value: 96.8, of: 100, label: "figures supported", unit: "%" },
  ],
  "Sealed split, run once, three repeats": [
    { kind: "fill", value: 97.8, of: 100, label: "figures supported", unit: "%" },
  ],
  "Data contracts under planted breaches": [{ kind: "units", filled: 11, total: 11, label: "planted breaches quarantined" }],
  "Causal fit against the planted chain": [
    {
      kind: "track",
      min: 0,
      max: 5,
      unit: "largest coefficient error, 0 to 5%",
      ticks: [0, 1, 2, 3, 4, 5],
      marks: [
        { at: 1.5, label: "default world 1.5%", tone: "main" },
        { at: 4, label: "forty seeds, within 4%", tone: "ref" },
      ],
      span: [0, 1],
    },
  ],
  "Revenue forecast": [
    {
      kind: "track",
      min: 0,
      max: 1.2,
      unit: "error against carrying today forward, lower is better",
      ticks: [0, 0.4, 0.8, 1.2],
      marks: [
        { at: 0.74, label: "model 0.74", tone: "main" },
        { at: 1, label: "carry today forward 1.00", tone: "ref" },
      ],
    },
    {
      kind: "track",
      min: 80,
      max: 100,
      unit: "90% interval: share of outcomes inside, 80 to 100%",
      ticks: [80, 85, 90, 95, 100],
      marks: [
        { at: 87, label: "held 87%", tone: "main" },
        { at: 90, label: "promised 90%", tone: "ref" },
      ],
    },
  ],
  "What-if shock propagation": [
    {
      kind: "track",
      min: 0,
      max: 200,
      unit: "propagation time, 0 to 200 ms",
      ticks: [0, 50, 100, 150, 200],
      marks: [
        { at: 1, label: "under 1 ms", tone: "main" },
        { at: 200, label: "200 ms budget", tone: "ref" },
      ],
    },
  ],
  "Ring-exit detection on the map": [
    {
      kind: "track",
      min: 0.8,
      max: 1,
      unit: "precision, 0.80 to 1.00",
      ticks: [0.8, 0.85, 0.9, 0.95, 1],
      marks: [
        { at: 0.86, label: "without hub suppression 0.86", tone: "hollow" },
        { at: 1, label: "with it 1.00", tone: "main" },
      ],
      span: [0, 1],
    },
  ],
  "Churn hazard calibration": [
    {
      kind: "track",
      min: 0,
      max: 0.6,
      unit: "hazard, 0 to 0.6",
      ticks: [0, 0.2, 0.4, 0.6],
      marks: [
        { at: 0.21, label: "observed 0.21", tone: "main" },
        { at: 0.43, label: "model mean 0.43", tone: "hollow" },
      ],
      span: [0, 1],
    },
  ],
  "Financial red-team probes": [{ kind: "units", filled: 15, total: 15, label: "probes passed" }],
};
