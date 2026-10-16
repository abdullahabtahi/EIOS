# Why the cockpit fell back to Replay, and the fix

**Symptom.** The cockpit showed "Pipeline: Replay" and the cached snapshot although the backend was up and `/health` answered in milliseconds.

**Cause `[MEASURED]`.** `GET /api/cockpit/workstations/<role>` took about 11 s per call against the dev setup (Firestore for approvals, Cloud KMS signing, from a laptop). The Next route gives the backend 8 s (`DEFAULT_TIMEOUT_MS` in `web-prototype/src/lib/server/backend.ts`), then serves the labelled replay. A profile showed 44 sequential Firestore reads: the server listed the 22 staged intents once, then called `get_token` per card, and `find` read each intent twice (`in`, then `[]`). Each read is a network round trip of about a quarter of a second. Every workstation shares the shelf, so every one was affected.

**Fix.** `find` reads once; `GovernedActionShelf.list_cards_with_tokens()` returns each card with its token from the one listing, and the state builder uses it. A test counts store reads (`tests/cockpit/test_shelf_read_cost.py`): one read per `find`, one list and no per-card reads for 22 cards.

**After `[MEASURED]`, same setup, real HTTP.** Warm calls about 0.5 s, first call after start-up 0.8 to 2.6 s, for the executive, AML and partner workstations (the compliance workstation is below).

**Not fixed.**
- The compliance workstation still takes 3 to 5 s: it lists the same intent collection three times and the WORM checkpoints three times in one request. Under the proxy limit, but a request-scoped read would cut it to one each.
- The 8 s limit is still a cliff: a slow backend looks like an outage and shows the replay. A distinct "slow, still loading" state would be more honest.
- The engines add about 0.1 to 0.4 s per request (hazard model per partner); they could be cached per data-plane build.
- Running against Firestore from a far-away laptop is slow by nature; the deployed API sits beside Firestore, so the production figure should be much lower (not measured).
