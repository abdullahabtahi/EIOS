# Quickstart: validating Agent Quality Gates

Run from `EIOS/`. Each scenario states what proves the feature works. Details: [data-model.md](data-model.md), [contracts/](contracts/).

## 0. Prerequisites

- `make setup`. No cloud access is needed for scenarios 1 to 4 and 6.
- Scenario 5 (live baseline) needs an EIOS Google Cloud project as quota project, `EIOS_GEMINI_MODEL` set from configuration, and `EIOS_AGENT_EVAL_MAX_TURNS` for the spend cap.

## 1. The faithfulness gate on the 13 pinned cases (US1)

```bash
uv run pytest tests/agent_gates/test_faithfulness_pinned.py -q
```

Expect 13 passed: 8 answers blocked (5 known-wrong figures plus 3 invented ones) and 5 accepted. Then the mutation corpus:

```bash
uv run pytest tests/agent_gates/test_faithfulness_mutation.py -q
```

Expect every mutant caught and no faithful paraphrase blocked.

## 2. Determinism and speed (US1, SC-002, SC-003)

```bash
uv run python -m evals.agent.faithfulness_suite --records evals/recorded --twice
```

Expect identical verdicts on both passes, no network calls, and the 200-turn corpus judged in under two minutes.

## 3. Safety suites against today's copilot (US2)

```bash
uv run python -m evals.agent.safety_suite --runtime copilot --records-out evals/reports/safety_records.jsonl
```

Expect a pass or fail per red line and per attack family, paraphrased attacks reported separately from keyword ones, and the request-body identity listed as a defect.

## 4. Parity with a stand-in (US6, SC-007)

```bash
uv run pytest tests/agent_gates/test_parity.py -q
```

Expect the same case ids run against the copilot and the `always42` stand-in, with the stand-in failing faithfulness and trajectory for the stated reasons.

## 5. The baseline on today's copilot (US4)

```bash
uv run python -m evals.agent.baseline --runtime copilot --split dev --repeats 3
```

Expect one report at `evals/reports/agent_baseline.md` with M3 and M5 per workstation, capability coverage, red-line and attack results, the share of fixture-data turns, and every failure with evidence. Red results are expected and correct.

## 6. Google eval CLI on the recorded corpus (US6)

```bash
agents-cli eval grade --traces evals/reports/traces.json --config evals/agent/eval_config.yaml --output evals/reports/grade
```

Expect the same verdicts as scenario 2. Confirms the checker runs as a native eval metric.

## 7. Telemetry (US5, SC-008)

```bash
uv run pytest tests/agent_gates/test_telemetry.py -q
```

Expect complete events and zero raw identifiers in the scan of a full suite run's events.

## Done when

All scenarios behave as stated, `make check` passes (the quarantined gates excepted), and the baseline report is committed under `docs/` as the "before" picture.
