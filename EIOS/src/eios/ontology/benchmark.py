"""Cold-boot and throughput benchmark suite for Layer 2 Kinetic Ontology (T048).

Tests:
1. Cold-boot graph rebuild latency (< 1.5s target)
2. 500 concurrent metric registry queries (<= 10ms p95 target)
3. Metric Auditor Gate egress firewall verification throughput
"""

import concurrent.futures
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.graph.property_graph import InMemPropertyGraph
from eios.ontology.metrics.catalog import create_default_registry
from eios.ontology.metrics.engine import MetricEngine, MetricQuery


def seed_benchmark_dataset(
    engine: HotStateEngine, client_count: int = 2000, txn_count: int = 10000
) -> None:
    """Populate DuckDB hot-state with realistic scale dataset for benchmarking."""
    now = datetime.now(UTC)

    # 1. Seed clients
    for i in range(1, client_count + 1):
        engine.insert_event(
            DataProductEnum.CLIENT_360,
            {
                "client_id": f"C-{1000 + i}",
                "tax_id": f"TAX-{i}",
                "full_name": f"Benchmark Trader {i}",
                "email": f"trader{i}@benchmark.test",
                "phone": f"+1555000{i:04d}",
                "dob": "1992-05-15",
                "country": "CYP" if i % 2 == 0 else "GBR",
                "kyc_status": "APPROVED",
                "kyc_approved_at": now,
                "partner_id": f"P-{100 + (i % 20) + 1}",
                "declared_monthly_income": 8000.0,
                "lifetime_value": float(i * 120),
                "segment": "VIP" if i % 10 == 0 else "STANDARD",
            },
        )

    # 2. Seed partners
    for p in range(1, 21):
        engine.insert_event(
            DataProductEnum.PARTNER_360,
            {
                "partner_id": f"P-{100 + p}",
                "tier": "TIER_1" if p <= 5 else "TIER_2",
                "region": "LATAM" if p % 2 == 0 else "EMEA",
                "tenure_months": p * 6,
                "value_at_risk": float(p * 25000),
                "manager_id": f"MGR-{p}",
                "status": "ACTIVE",
            },
        )

    # 3. Seed transactions
    for t in range(1, txn_count + 1):
        is_dep = t % 3 != 0
        engine.insert_event(
            DataProductEnum.TRANSACTIONS_AML,
            {
                "txn_id": f"TXN-BENCH-{t}",
                "client_id": f"C-{1000 + (t % client_count) + 1}",
                "txn_type": "deposit" if is_dep else "withdrawal",
                "amount": float(100 + (t % 500)),
                "currency": "USD" if t % 2 == 0 else "EUR",
                "payment_method_id": f"PM-{(t % 5) + 1}",
                "payment_agent_id": None,
                "timestamp": now,
                "is_first_deposit": (t <= client_count and is_dep),
                "status": "SETTLED",
            },
        )

    # 4. Seed device network graph
    for c in range(1, min(500, client_count)):
        engine.insert_event(
            DataProductEnum.DEVICE_NETWORK_GRAPH,
            {
                "edge_id": f"EDGE-DEV-{c}",
                "source_id": f"C-{1000 + c}",
                "target_id": "DEV-BENCH-HUB" if c <= 50 else f"DEV-{c // 3}",
                "edge_type": "USES_DEVICE",
                "first_seen": now,
                "last_seen": now,
                "session_count": 10,
                "is_shared_context": (c <= 50),
            },
        )

    cur = engine.get_cursor()
    try:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txn_bench ON transactions_aml (currency, txn_type)"
        )
    finally:
        cur.close()


def run_benchmark() -> dict[str, Any]:
    """Execute Layer 2 benchmark suite and return metrics."""
    hot_state = HotStateEngine(db_path=":memory:")
    try:
        seed_benchmark_dataset(hot_state, client_count=1000, txn_count=5000)

        # 1. Cold-boot graph rebuild latency
        t0 = time.perf_counter()
        graph = InMemPropertyGraph(hub_threshold=5)
        graph.rehydrate_from_hot_state(hot_state)
        graph_rebuild_sec = time.perf_counter() - t0

        # 2. 500 Concurrent Metric Registry Queries
        registry = create_default_registry()
        engine = MetricEngine(hot_state=hot_state, registry=registry)

        # Warmup query to initialize DuckDB query plan cache
        engine.execute(MetricQuery(metric_id="net_deposit_volume_usd", filters={"currency": "USD"}))

        query_latencies_ms: list[float] = []

        def execute_sample_query(i: int) -> float:
            metric_ids = ["net_deposit_volume_usd", "ftd_count_28d"]
            chosen = metric_ids[i % len(metric_ids)]
            filters = {"currency": "USD"} if chosen == "net_deposit_volume_usd" else {}
            q = MetricQuery(metric_id=chosen, filters=filters)
            t_start = time.perf_counter()
            engine.execute(q)
            return (time.perf_counter() - t_start) * 1000.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(execute_sample_query, i) for i in range(500)]
            for fut in concurrent.futures.as_completed(futures):
                query_latencies_ms.append(fut.result())

        latencies_arr = np.array(query_latencies_ms)
        p50 = float(np.percentile(latencies_arr, 50))
        p90 = float(np.percentile(latencies_arr, 90))
        p95 = float(np.percentile(latencies_arr, 95))
        p99 = float(np.percentile(latencies_arr, 99))

        # 3. Auditor Gate Throughput Benchmark (100 response evaluations)
        auditor = MetricAuditorGate()
        sample_trace = [{"output": {"net_deposit": 50000.0, "payout": 1250.0, "rate": 0.15}}]
        sample_text = "Net deposit is $50,000.00 with payout of $1,250.00 and rate of 15%."
        t0_audit = time.perf_counter()
        for _ in range(100):
            auditor.audit(sample_text, sample_trace)
        audit_duration_sec = time.perf_counter() - t0_audit
        audit_rps = 100.0 / audit_duration_sec

        # 4. Synthesis OMCP Tools Benchmark
        from eios.ontology.omcp.server import OMCPServer

        omcp_server = OMCPServer(hot_state=hot_state)
        causal_latencies: list[float] = []
        for _ in range(100):
            t_c = time.perf_counter()
            omcp_server.call_tool("get_causal_chain", {"outcome_metric": "net_deposit_volume_usd"})
            causal_latencies.append((time.perf_counter() - t_c) * 1000.0)
        causal_p95_ms = float(np.percentile(np.array(causal_latencies), 95))

        scenario_latencies: list[float] = []
        for _ in range(100):
            t_s = time.perf_counter()
            omcp_server.call_tool("run_scenario", {"shock_spec": {"competitor_payout_rate": 0.05}})
            scenario_latencies.append((time.perf_counter() - t_s) * 1000.0)
        scenario_p95_ms = float(np.percentile(np.array(scenario_latencies), 95))

        results = {
            "graph_rebuild_sec": round(graph_rebuild_sec, 4),
            "graph_nodes": graph.node_count,
            "graph_edges": graph.edge_count,
            "query_count": len(query_latencies_ms),
            "latency_p50_ms": round(p50, 3),
            "latency_p90_ms": round(p90, 3),
            "latency_p95_ms": round(p95, 3),
            "latency_p99_ms": round(p99, 3),
            "auditor_throughput_rps": round(audit_rps, 1),
            "graph_rebuild_passed": graph_rebuild_sec < 1.5,
            "metric_latency_passed": p95 <= 10.0,
            "synthesis_causal_chain_p95_ms": round(causal_p95_ms, 3),
            "synthesis_scenario_p95_ms": round(scenario_p95_ms, 3),
            "synthesis_causal_chain_passed": causal_p95_ms < 100.0,
            "synthesis_scenario_passed": scenario_p95_ms < 200.0,
        }

        return results
    finally:
        hot_state.close()


if __name__ == "__main__":
    res = run_benchmark()
    print("=" * 60)
    print("EIOS LAYER 2 BENCHMARK RESULTS")
    print("=" * 60)
    for k, v in res.items():
        print(f"  {k:28s}: {v}")
    print("=" * 60)
