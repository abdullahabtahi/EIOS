# Quickstart: validating Agent Quality Gates

Run from `EIOS/` with `PYTHONPATH=src:.` for the module commands. Details: [data-model.md](data-model.md), [contracts/](contracts/).

## 1. The faithfulness gate

```bash
uv run pytest tests/agent_gates/test_faithfulness_pinned.py tests/agent_gates/test_faithfulness_mutation.py tests/agent_gates/test_faithfulness_regressions.py -q
python -m evals.agent.faithfulness_suite --records evals/recorded --twice
```

Expect all pass, 0 failures and `deterministic=True` over 244 stored turns. Also runs through the repo harness: `python -m evals.cli run --tier eval_smoke --id-prefix agent-`.

## 2. All suites, offline, against today's copilot

```bash
python -m evals.agent.baseline --runtime copilot --repeats 3
```

Writes `evals/reports/agent_baseline/{report.md,report.json,records.jsonl}`. Red results are expected and are the point.

## 3. The live baseline (model path)

```bash
export GOOGLE_CLOUD_PROJECT=eios-hackathon GOOGLE_CLOUD_QUOTA_PROJECT=eios-hackathon GOOGLE_CLOUD_LOCATION=global EIOS_AGENT_EVAL_MAX_TURNS=45
python -m evals.agent.baseline --runtime copilot --live --repeats 1 --out evals/reports/agent_baseline_live
```

Refuses to start without the turn cap. Compare two runs with `--compare earlier/report.json`.

## 4. Parity and the Google eval CLI

```bash
python -m evals.agent.baseline --runtime always42
uv run pytest tests/agent_gates/test_parity.py tests/agent_gates/test_agents_cli_grade.py -q
```

The stand-in fails faithfulness and trajectory; `agents-cli eval grade` reproduces our verdicts (the test is skipped if the CLI is absent).

## 5. Telemetry and policy

```bash
uv run pytest tests/agent_gates/test_telemetry.py tests/agent_gates/test_gate_policy.py -q
```

## Done when

All tests pass, the thresholds file is committed before a run, and `docs/agent-baseline.md` holds the "before" picture.
