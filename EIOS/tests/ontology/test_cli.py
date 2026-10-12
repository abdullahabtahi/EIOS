"""Test for EIOS CLI Layer 2 commands (T049/T050)."""

from eios.cli import main


def test_cli_ontology_help():
    code = main(["ontology", "--help"])
    assert code == 0


def test_cli_ontology_benchmark():
    code = main(["ontology", "benchmark"])
    assert code == 0


def test_cli_ontology_audit_pass():
    code = main(
        [
            "ontology",
            "audit",
            "--text",
            "The calculated metric stands at $5,000.00.",
            "--trace",
            '[{"output": {"metric": 5000.0}}]',
        ]
    )
    assert code == 0


def test_cli_ontology_audit_fail():
    code = main(
        [
            "ontology",
            "audit",
            "--text",
            "The calculated metric stands at $99,999.00.",
            "--trace",
            '[{"output": {"metric": 5000.0}}]',
        ]
    )
    assert code == 2
