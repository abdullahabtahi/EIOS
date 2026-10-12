# Architectural Research & Design Decisions: Observability, SRE & Telemetry Spine (013-observability-sre)

**Feature**: Observability, SRE & Telemetry Spine (`013-observability-sre` / F12 / Slice S5)  
**Spec**: [`specs/013-observability-sre/spec.md`](spec.md)  
**Status**: Completed  
**Authoritative References**: `initial_plan.md` §3.3 (L5), §10; `docs/engagement_plan.md` §2, §5; `.specify/memory/constitution.md` (Principles I, II, IV, V, VI, VIII)

---

## 1. Decision 1: Distributed Tracing Spine & Cross-Boundary Context Propagation

### Context & Challenge
The platform operates a distributed multi-agent system spanning browser Cockpit workstations, OMCP tool servers, a Multi-Agent Reasoning Mesh (Arbitrating Coordinator + domain specialists), hot-state analytical engines (DuckDB), and cryptographic decision sequencers. To comply with Constitution Principle VIII and `docs/engagement_plan.md` §5, every client turn, tool call, database lookup, and action intent must maintain unbroken distributed trace context and enterprise correlation identity.

### Options Evaluated
1. **Option A (Recommended): Native OpenTelemetry Python SDK with Custom Span Processors & W3C TraceContext Carrier.**
   - Uses standard W3C `traceparent` headers (`version-traceid-spanid-traceflags`) combined with an enterprise `correlation_id` baggage attribute.
   - Attaches `_CorrelationSpanProcessor` to automatically stamp the ambient `correlation_id` on every span at instantiation.
   - Exports via `InMemorySpanExporter` for sub-millisecond local tests and `BatchSpanProcessor` for production OTLP/Cloud Trace.
2. **Option B: Proprietary Context Middleware without OpenTelemetry Spans.**
   - Uses Python `contextvars` to pass correlation IDs in log strings only.
   - *Rejected*: Lacks standardized span hierarchy, parent-child causal relationships, latency percentiles, and interoperability with Google Cloud Trace or Jaeger.
3. **Option C: Monkey-Patching Third-Party Client Libraries.**
   - Auto-instruments libraries via runtime byte-code manipulation.
   - *Rejected*: Violates Constitution small-file, clean-architecture, and explicit-error invariants; introduces unpredictable behavior across Python 3.14 runtimes.

### Decision & Rationale
**Adopt Option A.** Native OpenTelemetry SDK with W3C carrier injection/extraction provides vendor-neutral, portable, and battle-tested distributed tracing. It introduces $< 2$ ms overhead per request while providing complete causal attribution.

---

## 2. Decision 2: Real-Time 10-SLO Engine & 28-Day Error Budget Architecture

### Context & Challenge
`docs/engagement_plan.md` §2 mandates strict continuous tracking of 10 Service Level Objectives:
1. Ingestion freshness: $p95 \le 30$ s
2. Contract enforcement: $0$ invalid records reaching hot state
3. Metric query latency: $p95 \le 500$ ms
4. Agent turn first token: $p95 \le 3$ s
5. Agent turn full answer: $p95 \le 20$ s
6. Alert dossier assembly: $p95 \le 10$ s
7. Pre-withdrawal check decision: $p95 \le 2$ s
8. Morning briefing availability: $99\%$ of scheduled days
9. Approval service availability: $99.5\%$
10. Ledger chain verification: $100\%$ pass (any break = SEV-1)
11. Hallucination gate: $0$ unregistered metric claims

In addition, an error budget policy dictates that if any Tier-1 error budget is exhausted over a rolling 28-day window, non-critical feature merges are frozen (`FEATURE_FREEZE`).

### Options Evaluated
1. **Option A (Recommended): In-Memory Rolling Time-Bucket Ring Buffer with Exact Discrete Math.**
   - Records observed SLI outcomes (timestamp, metric category, observed value, pass/fail status).
   - Aggregates over sliding 1-hour, 6-hour, 24-hour, and 28-day buckets.
   - Computes `budget_remaining_pct = 1.0 - (failed_events / max_allowed_failures)` and instantaneous burn rates in $< 10$ ms.
2. **Option B: Periodic Batch BigQuery SQL Queries.**
   - Executes scheduled queries against BigQuery raw telemetry tables every hour.
   - *Rejected*: Incurs significant query latency ($15$–$30$ seconds), costs per query, and cannot trigger real-time feature freezes or sub-minute alerting.
3. **Option C: External Prometheus / Cloud Monitoring Aggregation Only.**
   - Relies exclusively on external cloud metrics.
   - *Rejected*: Prevents self-contained automated testing within the repository; breaks local CI evaluation gates mandated by Constitution Principle VI.

### Decision & Rationale
**Adopt Option A.** An in-memory rolling time-bucket engine guarantees deterministic sub-100ms evaluation during runtime execution and automated unit testing, while continuously exposing structured states that can be mirrored to Cloud Monitoring.

---

## 3. Decision 3: Multi-Window Multi-Burn-Rate Alerting Algorithm

### Context & Challenge
Static threshold alerting (e.g. "error rate $> 1\%$ for 5 minutes") suffers from severe SRE anti-patterns:
- High false positives: brief 30-second bursts trigger unnecessary pages.
- Slow detection: slow degradations that consume $100\%$ of the budget in a few days never cross high static thresholds.

### Options Evaluated
1. **Option A (Recommended): Google SRE Handbook Multi-Window Multi-Burn-Rate Standard.**
   - Evaluates budget consumption across paired short and long windows:
     - **Fast Burn (SEV-1 Page)**: Consumes $\ge 2\%$ of 28-day budget in 1 hour ($14.4\times$ burn rate). Short window: 5 min ($14.4\times$), Long window: 1 hour ($14.4\times$).
     - **Medium Burn (SEV-2 Ticket)**: Consumes $\ge 5\%$ of budget in 6 hours ($6\times$ burn rate). Short window: 30 min ($6\times$), Long window: 6 hours ($6\times$).
     - **Slow Burn (SEV-3 Ticket)**: Consumes $\ge 10\%$ of budget in 24 hours ($1.0\times$ burn rate over 24h).
   - Requires *both* short and long windows to agree before firing, preventing transient spike false alarms.
2. **Option B: Fixed Single-Window Percentage Thresholds.**
   - Simple check: `if errors / requests > 0.05: alert()`.
   - *Rejected*: Causes alert fatigue and violates Google/Palantir SRE operational doctrine.
3. **Option C: Anomaly Detection via Unsupervised ML.**
   - Dynamic thresholding via Holt-Winters or auto-encoders.
   - *Rejected*: Opaque, non-deterministic, hard to reason about during high-stress production incidents.

### Decision & Rationale
**Adopt Option A.** Multi-window multi-burn-rate alerting provides mathematically grounded, highly reliable alerting with high precision and rapid time-to-detect.

---

## 4. Decision 4: Adaptive Sampling & Backpressure Management

### Context & Challenge
Under high platform throughput ($> 10,000$ transactions per minute), exporting 100% of telemetry traces can create memory pressure and network saturation.

### Decision & Rationale
Implement **Tail-Based Adaptive Sampling**:
- **100% Retention Rule**: All traces containing errors (`status = ERROR`), HTTP $5xx$ status codes, or latency exceeding the $p95$ threshold ($> 500$ ms for queries, $> 10$ s for dossiers) are **always retained**.
- **Routine Downsampling**: Successful, low-latency traces ($< p50$) are sampled at a configurable rate (default $10\%$ in production, $100\%$ in test environments).
- This guarantees zero loss of diagnostic value while maintaining predictable memory footprints.

---

## 5. Decision 5: Open Architecture & Technology-Agnostic Boundaries

### Context & Challenge
In accordance with Constitution constraints, open architectural decisions `ADR-009` (frontend stack) and `ADR-014` (API transport: REST+SSE vs GraphQL+SSE) must not be prematurely closed.

### Decision & Rationale
- The Observability & SRE module exposes pure Python domain models, Pydantic schemas, and JSON-serializable payloads.
- All telemetry structures conform to standard JSON Schema contracts located in `specs/013-observability-sre/contracts/`.
- SRE metrics are accessible via standard internal Python APIs and can be wired to OMCP tools or REST/GraphQL endpoints without architectural coupling.
