import argparse
import sys
import tempfile
import time
from pathlib import Path

# Ensure src/ is on sys.path
_src_dir = Path(__file__).resolve().parents[2]
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import duckdb  # noqa: E402

from eios.contracts.base import DataProductEnum  # noqa: E402
from eios.ingestion.hot_state import HotStateEngine  # noqa: E402
from eios.ingestion.validator import ContractValidator  # noqa: E402
from eios.ingestion.warm_start import ParquetWarmStartLoader  # noqa: E402


def benchmark_warm_start(record_count: int = 100000) -> None:
    """Benchmark cold-boot Parquet warm start rehydration (ADR-012)."""
    print(f"[*] Generating {record_count:,} synthetic parquet records...")
    with tempfile.TemporaryDirectory() as tmpdir:
        prod_dir = Path(tmpdir) / "raw" / "trading_activity"
        prod_dir.mkdir(parents=True, exist_ok=True)
        pq_path = prod_dir / "bench.parquet"

        con = duckdb.connect()
        con.execute(f"""
            COPY (
                SELECT
                    'trd_' || range::VARCHAR AS trade_id,
                    'cli_' || (range % 1000)::VARCHAR AS client_id,
                    'VOL_75' AS symbol,
                    'BUY' AS side,
                    1.5 AS volume,
                    100.0 + (range % 50) AS open_price,
                    now() - INTERVAL (range % 3600) SECOND AS open_ts
                FROM range({record_count})
            ) TO '{pq_path}' (FORMAT PARQUET)
        """)  # noqa: S608
        con.close()

        engine = HotStateEngine()
        loader = ParquetWarmStartLoader(engine=engine, base_dir=tmpdir)

        start = time.perf_counter()
        summary = loader.load_all()
        elapsed_s = time.perf_counter() - start

        print(
            f"[+] Warm Start Completed: {summary.total_rows_loaded:,} rows loaded in {elapsed_s:.4f}s ({summary.load_duration_ms:.2f}ms)"
        )
        if elapsed_s < 3.0:
            print("[✓] PASS: Met ADR-012 cold-boot SLA (< 3.0s)")
        else:
            print("[✗] FAIL: Breached ADR-012 SLA (>= 3.0s)")


def verify_contracts() -> None:
    """Validate all 14 data product schemas against the validator catalog."""
    validator = ContractValidator()
    print("[*] Verifying contract validator catalog across all 14 Data Products...")
    for product in DataProductEnum:
        assert product in validator.supported_products  # noqa: S101
        print(f"  [✓] {product.value:<30} -> Registered and active")
    print(f"[+] All {len(validator.supported_products)} contracts verified successfully.")


def run_gateway(host: str = "0.0.0.0", port: int = 8000) -> None:  # noqa: S104
    """Start uvicorn gateway server."""
    import uvicorn

    from eios.ingestion.router import create_ingestion_app

    app = create_ingestion_app()
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="EIOS Layer 1 Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # benchmark-warm-start
    bench_parser = subparsers.add_parser(
        "benchmark-warm-start", help="Benchmark Parquet cold-boot rehydration"
    )
    bench_parser.add_argument(
        "--records", type=int, default=100000, help="Number of synthetic records"
    )

    # verify-contracts
    subparsers.add_parser("verify-contracts", help="Verify all 14 data product contracts")

    # run-gateway
    run_parser = subparsers.add_parser("run-gateway", help="Run FastAPI Ingestion Gateway")
    run_parser.add_argument("--host", default="0.0.0.0", help="Bind host")  # noqa: S104
    run_parser.add_argument("--port", type=int, default=8000, help="Bind port")

    args = parser.parse_args()

    if args.command == "benchmark-warm-start":
        benchmark_warm_start(args.records)
    elif args.command == "verify-contracts":
        verify_contracts()
    elif args.command == "run-gateway":
        run_gateway(args.host, args.port)


if __name__ == "__main__":
    main()
