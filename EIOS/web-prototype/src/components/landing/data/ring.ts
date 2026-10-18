/**
 * AML case CR84920 from the engine over the seeded world (`GET /api/cockpit/aml/cases/CR84920`,
 * kinetic canvas payload, as of 2026-10-14T08:00Z). Account ids are synthetic.
 */

export const RING_SUSPECT = "CR84920";

/** The ring the engine reports: the suspect plus 22 linked accounts that share one device and one payment method. */
export const RING_SIZE = 23;

export const RING_SAMPLE: readonly string[] = [
  "CR11568",
  "CR22286",
  "CR23211",
  "CR29257",
  "CR29662",
  "CR29709",
  "CR30645",
  "CR33758",
];

export const SHARED_DEVICE = "Device ff23c8";
export const SHARED_PAYMENT = "Payment method 84b570";

/** A public payment gateway the suspect transacts through. Left in, it would join its other 141 users to the ring. */
export const HUB = { id: "PA-HUB-007", degree: 142, collapsed: 141 } as const;

/** Suspect's 30-day deposits: $8,000 against a declared $500 a month; 96% of deposits withdrawn. */
export const CASE_FACTS = { deposits30d: 8000, declaredMonthly: 500, multiple: 16, withdrawnPct: 96 } as const;
