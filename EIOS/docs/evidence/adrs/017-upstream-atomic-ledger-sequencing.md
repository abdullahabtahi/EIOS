# ADR-017: Upstream Atomic Sequencer for Append-Only Decision Ledger

## Status

Accepted

## Date

2026-10-05

## Context

Principle II and Section 6.2 mandate an append-only, tamper-evident Decision Ledger tracking every action proposal, human approval, and simulated execution.
The ledger design relies on a cryptographic hash chain where row $N$ contains `prev_hash` equal to the SHA-256 digest of row $N-1$.
However, BigQuery streaming inserts (`tabledata.insertAll` or BigQuery Storage Write API) operate over distributed partition buffers. Distributed streaming writes do not guarantee global serialization order or immediate cross-worker read-after-write consistency. If two approvers commit actions concurrently, race conditions would cause conflicting sequence numbers (`ledger_seq`) or branching hash chains, corrupting tamper-evidence verification.

## Options considered

- **In-BigQuery Sequential Stamping via Stored Procedures**: BigQuery does not support interactive serializable transactions or auto-incrementing identity columns across concurrent streaming inserts.
- **Single-Threaded Kafka / Cloud Pub/Sub Sequencer Worker**: Dedicated single-partition subscriber assigning sequence numbers before batch loading to BigQuery. Cons: Introduces queue lag, single-point-of-failure subscriber, latency overhead.
- **Upstream Transactional Sequence Counter in Firestore / Spanner (Chosen)**: During action execution commit, the Approval Service runs an atomic transaction on an upstream sequence document in Firestore (or Cloud Spanner). The transaction:
  1. Reads the current `global_seq` and `current_tail_hash`.
  2. Increments `global_seq` to produce `ledger_seq = global_seq + 1`.
  3. Computes `new_hash = SHA256(ledger_seq || action_payload || current_tail_hash)`.
  4. Atomically updates the sequence document.
  5. Streams the finalized, strictly ordered record (`ledger_seq`, `prev_hash`, `new_hash`, `payload`) to BigQuery and GCS WORM storage.

## Decision

Adopt the **Upstream Transactional Sequence Counter** pattern implemented in Firestore. All ledger sequence numbers and cryptographic hash links are stamped upstream within an ACID transaction before streaming into BigQuery and GCS.

## Consequences

- Positive: Total elimination of concurrency race conditions and hash-chain branching.
- Positive: Guaranteed strict monotonic sequence numbers ($1, 2, 3, \dots, N$) and unbroken cryptographic hash chains.
- Positive: BigQuery streaming latency has zero effect on sequence integrity.
- Negative: Adds a low-latency atomic transaction hop (~15ms in Firestore) to action execution finalization.

## Evidence

Spike S-06 architectural analysis; Google Cloud architecture patterns for streaming tamper-evident ledgers.

## Revisit when

Write throughput exceeds Firestore single-document transactional limits (>10,000 writes/sec), at which point range-partitioned sequence trees or Cloud Spanner true-time sequences would be utilized.
