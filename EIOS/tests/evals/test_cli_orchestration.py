"""Tests for evals.cli orchestration and tier selection (T058)."""

from evals.cli import main


def test_cli_help_exits_cleanly(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "Run evaluation suites from the gate hook registry" in captured.out


def test_cli_unknown_tier_exits_with_error():
    try:
        code = main(["run", "--tier", "unknown_tier_xyz"])
    except SystemExit as exc:
        code = exc.code
    assert code == 2


def test_cli_run_eval_smoke():
    code = main(["run", "--tier", "eval_smoke"])
    # 0 indicates success (whether empty or passing suites)
    assert code == 0


def test_cli_run_red_line():
    code = main(["run", "--tier", "red_line"])
    assert code in (0, 1)


def test_cli_id_prefix_filtering():
    code = main(["run", "--tier", "eval_smoke", "--id-prefix", "nonexistent-prefix-xyz"])
    assert code == 0
