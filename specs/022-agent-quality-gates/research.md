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
