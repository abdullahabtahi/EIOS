# Research: Agent Quality Gates

Evidence tiers: **RUN** executed by me, **SRC** read in code or package source, **DOC** read in documentation, **INF** inference.

## R-1. Own runner, Google's eval CLI, or both

- **Decision**: Both, from one core. The judgement logic is plain Python with no `eios` imports. Our `evals/registry.yaml` suites call it in CI; thin files under `evals/agent/metrics/` expose it to `agents-cli eval grade` as `custom_function_file` metrics.
- **Evidence**: S-EVAL-1 (RUN). A local deterministic metric graded two hand-made traces through `agents-cli eval grade` with no cloud call: the faithful answer scored 1.0 and a 100-times-too-large figure scored 0.0 with the reason. Two facts surfaced: a trace needs both `agent_data` and `responses` (without `responses` every case errors with "No response found for candidate 0"), and the CLI runs metric code in its own Python 3.12 process.
- **Rationale**: Our CI must not depend on a tool we do not control, yet Google's tooling gives native HTML reports and, in spec 021, `eval generate` against the ADK runtime with the same metrics.
- **Alternatives rejected**: CLI only (couples CI to the tool, cannot judge the non-ADK copilot without an adapter anyway); own runner only (forgoes native reports and the ADK flywheel).

## R-2. How a figure binds to a field (resolves the FR-005 question)

- **Decision**: Conservative, deterministic, three-part match. A figure is supported only if (a) its value matches a fact after allowed normalisation, (b) its unit family is compatible, and (c) at least one content word near the figure matches the fact's label tokens (field path words and per-case aliases). A figure that matches the value of one fact but whose context matches a different fact's label is `wrong_field`. A figure matching several facts without decisive context is unsupported. Derived figures are unsupported unless a tool produced them.
- **Allowed normalisation**: thousands separators; currency symbols; "k", "million", "billion"; percentages; basis points; multipliers ("16x"); spelled-out numbers up to the billions; rounding to the precision the figure states ("about 3.8 million" matches 3,820,000, "3.9 million" does not).
- **Structured mode**: when a record carries explicit bindings (spec 021 reference answers), the checker verifies value and unit equality directly and skips context inference.
- **Verification plan**: the 13 pinned cases; mutation tests (apply scale, field-swap and unit-swap perturbations to faithful answers; every mutant must be caught); templated faithful paraphrases (none may be blocked). Report precision and recall on those corpora; do not claim more.
- **Rationale**: Constitution Principle I needs a verdict that is repeatable and explainable. The current auditor checks digit presence anywhere in tool output (DOC `docs/adk.md` section 3) and fails five of five wrong figures.
- **Alternatives rejected**: an LLM judge (non-deterministic, forbidden to gate by FR-017); ADK `hallucinations_v1` (LLM-based; reported for information only); the Check Grounding API (built for prose claims, untested on numbers).
- **Known limit**: label matching can reject a faithful answer that uses an unlisted synonym. The failure direction is safe (blocks), and per-case aliases plus the paraphrase corpus bound it. Measure the false-block rate at the baseline.

### R-2 results `[MEASURED]` (2026-10-14, T024)

Corpora: the 13 pinned cases; 23 hand-written mutants and 20 faithful paraphrases; and a seeded generator (`evals/agent/build_corpus.py`, five workstations, about 230 records per seed) with the expected outcome known by construction.

| Stage | Wrong answers blocked | Faithful answers accepted |
|---|---|---|
| Pinned 13 | 8 of 8 | 5 of 5 |
| First run on the generated corpus (seed 2210, before any fix) | 87 of 89 | 44 of 52 |
| After the fixes below, eight seeds | 1,014 of 1,014 | 832 of 832 |

First-run failures and fixes: two figures in one sentence borrowed each other's labels (context now limited to the clause); a statistic name such as `p95` was read as an invented identifier (new `quantile_label` exemption); a minus sign before a currency symbol was dropped; a top-level `unit` hint leaked into nested fields (hints and metric names now apply to direct children only); the scale test was too loose; a figure for the net revenue *forecast* was accepted as "net revenue" (new rule: reject when the clause describes a different field with a different value better); a synonym the field name lacks ("first deposits" for `ftd_decay_pct`) is blocked until an alias supplies it, by design; one generator record was mislabelled. Two seeds then exposed one more miss (a current figure labelled as the forecast); the rule was tightened to compare how many words of the clause each field covers.

**How far to trust this.** The generator was written by the same author as the judge, from templates, so it measures coverage of the families I thought of, not general accuracy (the constitution's anti-circularity concern). Fixes were made after seeing failures on seeds 2210, 31337 and 777; seeds 12345, 55555 and 808 were first judged after the last fix (381 wrong and 312 faithful, all correct). The decisive test is the live baseline on the real copilot's answers (T058), with a human-labelled sample of its figures. Expect new failure families there and treat each as a regression test.

**Known limits.** Spelled-out decimals ("three point five million") are not parsed. A synonym not in the field name needs a per-case alias. A figure whose clause names no field is `wrong_field` (blocked), not guessed.

## R-3. Turn Record shape

- **Decision**: One frozen record: question, verified role and operator (with the source of the identity), entity context, ordered tool calls (name, arguments, result, error, latency), rounds, final answer, structured bindings if any, replay flag and reason, audit verdict, citations, timing, tokens and cost, data origin, and the repeat index. A pure function maps it to the `agents-cli` trace shape (`agent_data` plus `responses`).
- **Evidence**: trace schema (DOC, eval skill `dataset_schema.md`); S-EVAL-1 (RUN).
- **Rationale**: one record feeds faithfulness, trajectory, safety, telemetry and the Google CLI.

## R-4. Entry point and how to capture today's copilot

- **Decision**: `AgentPort.run_turn(TurnRequest) -> TurnRecord`. The copilot adapter calls `CopilotEngine.process_query(query, role, session_id, turn_index)` (SRC) and captures tool calls by spying on the module-level dispatcher `run_omcp_tool(name, args)` (SRC), because the response object carries only `tool_trace_count` and an evidence ledger, not arguments and results.
- **Identity**: today's route passes only `role` taken from the request body (SRC, `server.py` `query_copilot`); the adapter records `identity_source = "request_body"`, which the safety suite reports as a defect (B3), not a pass.
- **Tool fixtures**: `TurnRequest.tool_fixtures` replaces named tool results (for example with injected text); the adapter applies them at the same spy point. For ADK later, the same field maps to a tool-registry swap.

## R-5. Case format and the unmoored golden dialogues

- **Finding (SRC)**: the ten existing golden dialogues name tools such as `get_entity_profile`, `get_transaction_history` and `submit_sar_autonomous` that exist in neither the copilot's six tools nor OMCP's 42 handlers. The trajectory evaluator passes only because it is fed stub inputs.
- **Decision**: extend `GoldenDialogueScenario`, do not fork it. Cases name **capabilities** (for example `aml.dossier`, `metric.get`, `knowledge.regulation`); `capabilities.py` maps each capability to today's tool name, the target catalogue name, or "unavailable". A case whose capability is unavailable on a runtime is reported as `capability_missing`, which is a real finding for the baseline, not a pass.
- **Rationale**: tools change in spec 023; cases must not.

## R-6. Repeats, flake policy, inconclusive

- **Decision**: three repeats per live case `[ASSUMPTION]`. Safety and attack cases pass only if all repeats pass. Quality cases report a rate with the repeat count. A run that fails for provider outage, timeout or quota is `inconclusive`, listed separately, and can never turn a gate green (FR-024). A gate with any inconclusive case it depends on reports "not proven".

## R-7. Adversarial design against a keyword defence

- **Finding (SRC)**: today's copilot blocks attacks by matching substrings such as "ignore all instructions" and "bypass four-eyes" before any model call.
- **Decision**: attack cases are paraphrased to avoid those substrings, and the baseline reports both groups (keyword and paraphrased) so the defence's real strength is visible. Injection is tested through tool results (`ToolFixture`), which no keyword list covers. Exfiltration uses a canary token planted in data outside the caller's scope; any appearance in an answer fails.
- **Rationale**: a suite that the current defence passes by construction measures nothing.

## R-8. Telemetry content and the default logging tier

- **Decision**: telemetry derives from the Turn Record and keeps only pseudonymous tokens, ids, counts, timings, verdicts and a bounded, redacted excerpt. A scanner asserts zero raw identifiers across a full suite run (SC-008).
- **Evidence (DOC, observability skill)**: scaffolded deployments export full prompts and responses to Cloud Storage and BigQuery by default, independent of the trace-content setting. Spec 021 must disable or redact that tier for this product; recorded here so it is not discovered late.
- **Writer**: the BigQuery writer is the ADK analytics plugin in spec 021 (SRC: it has event allow-lists and a content formatter that acts as a redaction boundary). This feature ships the schema, redaction and a local sink.

## R-9. Live runs, cost and region

- **Decision**: live runs go through `llm_gateway`; the model id comes from configuration; a hard cap on turns and estimated spend stops a run before it starts. Requires an EIOS project as the quota project (the default gcloud project is the legacy `spatial-cat-489006-a4`) and the `global` endpoint for Gemini 3.x (CLAUDE.md).
- **Spend estimate**: not measured; the first baseline run reports actual cost per turn, which becomes the planning number.

## R-10. Data splits

- **Decision**: baseline uses the dev split only. Validation split runs on merge to stage; sealed only on release candidates by CI (ADR-015). Cases carry their split and are rejected if a ground-truth field appears in agent-visible inputs.

## R-11. Case counts

- **Decision**: AML 20 (lighthouse workflow), partner 12, executive 12, compliance 6, operations 6, total 56, plus 15 or more attacks `[ASSUMPTION]`. Enough per workstation for a stable rate; revisit after the first baseline shows variance.

## R-12. Study protocol

- **Decision**: a document, `docs/lighthouse-study-protocol.md`, defining cases, participants, timed intervals, recording sheet and median computation for M1 and M2. Not executed here (FR-019).

## R-13. Agreement between the agent and the workstation (FR-026)

- **Finding (SRC, 2026-10-14)**: for the partner on screen the workstation shows a churn hazard of 78% and a login drop of 68% (`src/eios/cockpit/partner.py`), while the copilot's partner tool returns 0.84, a 62.4% decay and a named rival as constants for any partner id (`src/eios/conversation/tools.py`). Its suggested action is a hard-coded literal (`DISPATCH_RETENTION_PLAYBOOK`, `src/eios/conversation/copilot_engine.py`).
- **Decision**: the check compares the figures an answer states about an entity with the workstation payload for the same entity, loaded from the contract the cockpit serves. The baseline reports every disagreement with both values. The fix itself (one governed read path for both) belongs to spec 023.
- **Why a gate and not a fix here**: a fix without a gate regresses silently; the gate makes spec 023's result provable (SC-011).

## R-14. Industry alignment (and legacy artefacts are not authority)

Existing code, tests, dialogues and tool names are treated as inputs to test against, never as the definition of correct. Sources marked (secondary) were read in vendor or community write-ups, not the primary specification.

| Practice | Source | How it is adopted |
|---|---|---|
| Deterministic evaluators first; LLM judges informational and themselves checked against human preference | Palantir AIP Evals documentation and field guide; the same pattern in open evaluators | Gates are deterministic (FR-017). Any LLM-judged score is reported only, and is validated on a human-labelled sample before it is shown |
| Test cases, evaluation functions, run-to-run comparison and variance across runs | Palantir AIP Evals | FR-027: run id, comparison and per-case spread; the baseline report is the first run |
| Trajectory match modes: exact match, in-order match, any-order match, precision | Google Gen AI evaluation, "Evaluate Gen AI agents" | Each case sets `trajectory_match` (default any-order) and reports these four; recall computed as the complement (not confirmed in the page read) |
| Reliability as all-trials success (pass^k), distinct from best-of (pass@k) | tau-bench (Sierra), arXiv 2406.12045 | Safety and attack cases use pass^k with k = repeats; quality cases report pass^1 and the spread; the unbiased estimator C(c,k)/C(n,k) is used when n exceeds k |
| Claim-level verification: decompose an answer into atomic claims and check each against its source | factuality evaluation practice (FActScore-style) `[INF]` | Each figure is an atomic claim judged against a fact, with a reason code |
| Baseline first, pre-registered thresholds, sealed holdout | QuantumBlack engagement practice as recorded in the constitution (Principle VI) and `lighthouse.md` | Thresholds are committed in `evals/agent/thresholds.yaml` before the first baseline run; sealed results only on release candidates |
| Telemetry names follow the OpenTelemetry GenAI semantic conventions (status: Development, so pinned and mapped) | OpenTelemetry GenAI conventions (secondary) | Telemetry fields carry an `x-otel` mapping to `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.tool.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`; content stays opt-in because it can carry personal data |
| Attack families mapped to the OWASP Top 10 for LLM Applications 2025: LLM01 prompt injection, LLM02 sensitive information disclosure, LLM06 excessive agency | OWASP (secondary) | Each attack case carries an `owasp` tag; the report shows coverage by category |
| Interchange with Google's evaluation tooling (`agent_data`, `responses`) | Google agents-cli evaluation schema | Spike S-EVAL-1; `contracts/agents-cli-trace-mapping.md` |

**What this changes.** The exempt categories are defined from a taxonomy (identifiers, dates and times, versions, legal citations, list and period labels, structure counts) and tested against both the legacy examples and new ones; the old regexes are not ported. Golden cases are written fresh from the workstation jobs in `docs/agent-architecture.md` section 1, not migrated from the legacy dialogues, which are left untouched and marked superseded. The case file follows the Google evaluation case shape with our extra fields, not the legacy dialogue model.
