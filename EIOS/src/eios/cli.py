"""Command-Line Interface (CLI) for EIOS platform operations (T049).

Supported commands:
- eios ontology benchmark: Execute cold-boot and concurrency benchmarks for Layer 2.
- eios ontology audit: Audit an agent response text against tool execution traces.
"""

import argparse
import json
import sys
from collections.abc import Sequence

from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.benchmark import run_benchmark


def create_parser() -> argparse.ArgumentParser:
    """Create root argument parser with subcommand tree."""
    parser = argparse.ArgumentParser(
        prog="eios",
        description="Real-Time Enterprise Intelligence Operating System (EIOS) CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Platform domain command")

    # ontology group
    ontology_parser = subparsers.add_parser(
        "ontology", help="Kinetic Ontology and Metric Layer commands"
    )
    ontology_subparsers = ontology_parser.add_subparsers(
        dest="ontology_command", help="Ontology operation"
    )

    # eios ontology benchmark
    ontology_subparsers.add_parser(
        "benchmark", help="Run cold-boot graph rebuild and query benchmarks"
    )

    # eios ontology audit
    audit_parser = ontology_subparsers.add_parser(
        "audit", help="Audit agent response text against tool traces"
    )
    audit_parser.add_argument(
        "--text", required=True, help="Agent narrative text containing numbers to audit"
    )
    audit_parser.add_argument(
        "--trace",
        required=False,
        default="[]",
        help="JSON string or file path containing tool traces",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = create_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0

    if args.subcommand == "ontology":
        if args.ontology_command == "benchmark":
            print("=" * 60)
            print("EIOS LAYER 2 BENCHMARK RUNNING...")
            print("=" * 60)
            results = run_benchmark()
            for k, v in results.items():
                print(f"  {k:28s}: {v}")
            print("=" * 60)
            passed = results.get("graph_rebuild_passed", False) and results.get(
                "metric_latency_passed", False
            )
            return 0 if passed else 1

        elif args.ontology_command == "audit":
            # Parse trace argument (either raw JSON string or JSON file)
            trace_arg = args.trace
            try:
                if trace_arg.startswith("[") or trace_arg.startswith("{"):
                    traces = json.loads(trace_arg)
                    if isinstance(traces, dict):
                        traces = [traces]
                else:
                    with open(trace_arg) as f:
                        traces = json.load(f)
            except Exception as e:
                print(f"Error parsing --trace JSON: {e}", file=sys.stderr)
                return 1

            auditor = MetricAuditorGate()
            rec = auditor.audit(args.text, traces)
            print(f"Audit Status : {'PASS' if rec.audit_passed else 'FAIL'}")
            print(f"Extracted    : {rec.extracted_numbers}")
            print(f"Anchored     : {rec.anchored_numbers}")
            print(f"Untraceable  : {rec.untraceable_numbers}")
            if rec.rejection_reason:
                print(f"Reason       : {rec.rejection_reason}")
            return 0 if rec.audit_passed else 2

        else:
            parser.parse_args(["ontology", "--help"])
            return 1

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
