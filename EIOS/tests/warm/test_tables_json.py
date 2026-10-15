"""The Terraform layout is the generated one: a contract change that is not regenerated fails here."""

from tools.gen_warm_tables import main


def test_the_committed_table_layout_matches_the_contracts() -> None:
    assert main(["--check"]) == 0
