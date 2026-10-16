# Why the cockpit fell back to Replay, and the fix

**Symptom.** The cockpit showed "Pipeline: Replay" and the cached snapshot although the backend was up and `/health` answered in milliseconds.

**Cause `[MEASURED]`.** `GET /api/cockpit/workstations/<role>` took about 11 s per call against the dev setup (Firestore for approvals, Cloud KMS signing, from a laptop). The Next route gives the backend 8 s (`DEFAULT_TIMEOUT_MS` in `web-prototype/src/lib/server/backend.ts`), then serves the labelled replay. A profile showed 44 sequential Firestore reads: the server listed the 22 staged intents once, then called `get_token` per card, and `find` read each intent twice (`in`, then `[]`). Each read is a network round trip of about a quarter of a second. Every workstation shares the shelf, so every one was affected.

**Fix.** `find` reads once; `GovernedActionShelf.list_cards_with_tokens()` returns each card with its token from the one listing, and the state builder uses it. A test counts store reads (`tests/cockpit/test_shelf_read_cost.py`): one read per `find`, one list and no per-card reads for 22 cards.

**After `[MEASURED]`, same setup, real HTTP.** Warm calls about 0.5 s, first call after start-up 0.8 to 2.6 s, for the executive, AML and partner workstations (the compliance workstation is below).

**Follow-up: compliance reads and client resilience (2026-10-16).**
- The compliance request now lists the intents, WORM checkpoints and ledger entries once each, concurrently, and reuses the intent listing the shelf already makes (`compliance_ledger.read_ledger`, `tests/cockpit/test_compliance_read_cost.py`). `[MEASURED]` over real HTTP against the dev Firestore from a laptop, warm calls: compliance workstation 4.1 s to 1.1 s, ledger endpoint 3.4 s to 0.9 s. Executive and AML are unchanged at about 0.6 to 0.9 s (the shelf listing and the state build).
- Engine cost: not cached. On local stores the engine-backed workstations answer in 2 to 105 ms and the case routes in 20 to 55 ms `[MEASURED]`, so the 0.1 to 0.4 s per request quoted earlier is not reproducible, and a per-build cache would add an invalidation risk for no measured gain. Revisit only if a deployed measurement shows it.
- The shelf's intent listing now overlaps the ledger and checkpoint reads instead of preceding them. `[MEASURED]` through the user's API on 8002 (same dev Firestore, laptop), warm: compliance workstation 2.9 to 4.3 s on the old process, 0.7 to 0.85 s after; executive 0.6 to 0.85 s.
- Client: the cockpit keeps the last live answer per workstation, shows it at once on a switch and refreshes behind it; a failed refresh keeps that data labelled "Stale" rather than dropping to the replay; the proxy retries once with a 25 s budget (`?patient=1`); a request still running after 3 s shows "Slow". The replay is shown only when there is no live data to keep. The workstation answer is `Cache-Control: private, no-cache` with an ETag; a replay is `no-store`. The shelf is never taken from the client cache. One second after the visible workstation is live, the other four are fetched one at a time (one attempt each, silent on failure) to fill the cache, so most first switches start from data.

**Not fixed.**
- Compliance still scans every ledger entry on each request (the audit walk), so its cost grows with the ledger. A stored verified head with incremental verification would fix that; it changes the audit semantics, so it needs a decision first.
- The deployed API sits beside Firestore, so the production figure should be lower (not measured).
- No production measurement yet; deploy is pending approval.
