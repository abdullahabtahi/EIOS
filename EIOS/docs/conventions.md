# Conventions (F00 Platform Foundations)

Authority: the F00 spec, plan and tasks (kept in the planning workspace, outside this repository) and this repository's contribution rules. Every figure below is tagged; see "Tags and provenance".

## Layout

| Path | Holds |
|---|---|
| `src/eios/common/` | errors, boundary validation, provenance tags |
| `src/eios/llm_gateway/` | the single model-call access point (F00 ships the stub provider only) |
| `tools/` | gate and check tools, run as `uv run python -m tools.<name>` |
| `services/` | deployable skeleton services |
| `evals/` | `registry.yaml`, suites, fixtures, generated `reports/` |
| `config/` | gates, open decisions, gateway and label configuration |
| `docs/adr/`, `docs/runbooks/`, `docs/evidence/` | decision records, runbooks, recorded evidence |
| `infra/` | `bootstrap/`, `modules/`, `envs/` Terraform |
| `schemas/` | JSON Schemas (copies of the F00 contract schemas; byte-identity with the planning-workspace sources is checked when that workspace is present) |
| `tests/` | `unit/`, `contract/`, `integration/`, `support/`, `fixtures/` |

## Ceilings `[TARGET]`

- Files: 200-400 lines typical, 800 maximum.
- Functions: at most 50 statements, 12 branches, 7 arguments (enforced by ruff).
- Nesting: no more than 4 levels.
- Line length: 100.

## Immutability

Create new objects; never mutate inputs. Models are frozen (`ConfigDict(frozen=True, extra="forbid")`). Functions return updated copies rather than changing arguments.

## Error handling

Errors are explicit at every level and derive from `EiosError`. Never swallow an exception. User-facing messages are plain and carry no internals; detailed context is logged server side with the correlation id.

## Boundary validation

Everything crossing a boundary (CLI input, files, HTTP, provider output) is validated by schema before use, failing fast with a clear message.

## Untrusted text

Text from outside the repository (documents, user input, model output) is data, never instructions. It enters prompts only through the `untrusted_text` wrapper.

## Tool exit codes

`0` pass, `1` findings, `2` tool or configuration error. Each tool writes `evals/reports/<tool>.json`.

## Tags and provenance

Every figure or claim carries one of `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`. A shown number traces to a brief citation, a generator run (seed + revision + dataset hash), or an eval report. Without git, a content hash is the revision id.

## Runtime check `[ASSUMPTION]`

`.python-version` pins `3.14`. Check recorded 2026-09-30: the Cloud Run Python runtime documentation lists `python314` (stack `google-24`) as supported, and the local interpreter is 3.14.4. All tools in the register below resolved and installed under it. Owner: platform engineer; verify by re-running this check on the next toolchain bump.

## Tooling register

Versions are those `uv lock` resolved on 2026-09-30, read from `uv.lock`, not typed by hand `[ASSUMPTION]`; owner: platform engineer, verify by the next `uv lock`.

| Role | Tool | Chosen on | Verified version | Tag |
|---|---|---|---|---|
| Package and environment manager | uv | 2026-09-30 | 0.10.7 | `[ASSUMPTION]` |
| Test runner | pytest | 2026-09-30 | 9.1.1 | `[ASSUMPTION]` |
| Test parallelization | pytest-xdist | 2026-10-02 | 3.8.0 | `[ASSUMPTION]` |
| Coverage | pytest-cov | 2026-09-30 | 7.1.0 | `[ASSUMPTION]` |
| Linter and formatter | ruff | 2026-09-30 | 0.16.10 | `[ASSUMPTION]` |
| Strict type checker | mypy | 2026-09-30 | 2.4.0 | `[ASSUMPTION]` |
| YAML parsing | pyyaml | 2026-09-30 | 6.0.3 | `[ASSUMPTION]` |
| JSON Schema validation | jsonschema | 2026-09-30 | 4.26.0 | `[ASSUMPTION]` |
| HTTP client for ASGI tests | httpx | 2026-09-30 | 0.28.1 | `[ASSUMPTION]` |
| Tracing | opentelemetry-sdk | 2026-09-30 | 1.45.0 | `[ASSUMPTION]` |
| Web framework | fastapi | 2026-09-30 | 0.142.2 | `[ASSUMPTION]` |
| Data models | pydantic | 2026-09-30 | 2.13.5 | `[ASSUMPTION]` |
| Dependency advisory audit (`vuln_scan` gate) | pip-audit, fed by `uv export` of `uv.lock` | 2026-10-02 | 2.10.1 | `[ASSUMPTION]` choice and version |
| SBOM (`sbom.py`, T049) | `uv export --format cyclonedx1.5` (CycloneDX 1.5, offline, from `uv.lock`) | 2026-10-02 | uv 0.10.7 (export is marked experimental by uv) | `[ASSUMPTION]` choice and version |
| Secret scan (`secret_scan` gate) | In-repo regex scanner `tools/gates/secret_scan.py` (patterns as data, tested) | 2026-10-02 | not applicable | `[ASSUMPTION]` |
| IaC check (`iac_plan` gate) | terraform `fmt -check`, `init -backend=false`, `validate` | 2026-10-02 | 1.15.7 (local) | `[ASSUMPTION]` choice and version |
| Terraform lint | tflint, used if present; `EIOS_REQUIRE_TFLINT=1` makes absence a tool error (CI sets it) | 2026-10-02 | not installed locally, unverified | `[ASSUMPTION]` |
| Terraform static checks (`tools/infra_checks`) | python-hcl2, parsing `*.tf` and `*.tfvars` statically; no Terraform binary or network needed for the structural rules | 2026-10-02 | 8.1.4 (read from `uv.lock`) | `[ASSUMPTION]` choice and version |
| Container and image scan | none yet (no image builds exist); arrives with T216 | 2026-10-02 | not chosen | `[ASSUMPTION]` |

### Scanner notes `[ASSUMPTION]`

- Secret scan scope today: the working tree (including captured logs under `evals/reports/`) and, when a `.git` directory exists, every added line in all commits. Built-image scanning arrives with T216. Findings carry file, line and rule id only; matched text is never printed, logged or reported.
- A third-party scanner (`detect-secrets` 1.5.0) was tried on 2026-10-02 against the four shapes in `tests/support/secret_shapes.py` and was removed again: see `docs/evidence/secret-scanner-selection.md`.
- `gitleaks`, `trivy`, `syft` and `tflint` are not installed locally; no system package was installed. The dependency audit needs network access to the advisory database; there is no allowlist yet (R-03 calls for an expiring, owned allowlist; add it when the first accepted exception appears).

## Infrastructure notes

- The `secret_store` module creates a KMS key ring and one asymmetric signing key (ECDSA P-256) only when `signing_key_enabled` is true (prod-like). This key ring **extends `plan.md`**, which lists Secret Manager but no key ring; it exists so Action Intents can be signed (CLAUDE.md invariant 5).
- Terraform and provider versions are not pinned as facts: `required_version = ">= 1.6"` and an unpinned `hashicorp/google` provider carry a spike-tagged comment until the first reviewed `init` on a real project. Lock files (`.terraform.lock.hcl`) are committed.
- Static infra rules run as `uv run python -m tools.infra_checks`; apply is never run from this repository's tooling. See `docs/environments.md` and `docs/runbooks/bootstrap.md`.

## Provenance labels (`label_check`)

`uv run python -m tools.label_check` reads `config/labels.yaml` and checks every governed document (`specs/**/*.md`, `docs/**/*.md`, minus the exclusions in that file) at review time. The unit of a claim is a sentence, a table row or a list item. A unit with a numeric claim (percentage, currency amount, count of a configured unit, duration or ratio) needs exactly one tag, or an origin reference. Worked examples, one per tag:

```text
Churn fell 3 points in the quarter [BRIEF] (docs/brief/churn, section 2).
The pilot covers 40 partners [ASSUMPTION] owner: delivery lead, verify by P1 exit.
The demo shows 12 clients [ILLUSTRATIVE].
Alert latency stays under 300 ms [TARGET] metric: alert_latency_p95, reported in evals/reports/latency.json.
A 30-prompt benchmark fixes the gateway default [SPIKE] S-01.
Precision is 91 percent eval-report: evals/reports/model_a.json.
The seeded sample has 500 clients generator-run: seed=7 revision=abc1234 dataset=sha256-of-the-file.
```

What is machine-checked:

- A brief-tagged claim, or an untagged figure that cites `docs/brief/<file>`, must cite a file that exists and name a section (`section 2`, `§2` or `#anchor`).
- A spike-tagged claim must carry an `S-NN` id that resolves to a record in `docs/adr/` or a row in `docs/spikes_and_adrs.md`. A spike counts as open unless its record says closed.
- A generator-run origin needs `seed=`, `revision=` and `dataset=`; an eval-report origin must point under `evals/reports/`.
- Two tags on one figure, an unknown bracketed tag, a competitor brand, an unverified version pin or a secret-shaped string is a finding. Messages never echo the offending text.
- Structured files listed under `structured_rules` (gateway config `verification` block, `docs/cost_model.csv` tag column) need a valid tag next to every number.

`[ASSUMPTION]` (owner and verify-by) and `[TARGET]` (metric and report) evidence is documented but not machine-checked; reviewers check it.

Exceptions live in `config/label_allowlist.yaml` as `{path, literal, reason}`. Request one in a pull request: name the file, quote the literal and give a non-blank reason that a reviewer accepts. An entry that matches nothing is reported as stale and fails the check, so delete entries when the text goes away.

## Planned deviations from plan.md

- Extra common modules (e.g. `src/eios/common/secret_reader.py`) introduced by Foundational and US2.
- Extra tool packages: `tools/records/` (T020), `tools/common/` (T018), `tools/infra_checks/` (T069), `tools/prompt_lock/` (US3), `tools/budget_probe/` (US6).
- Extra configuration files: `config/repo_checks.yaml` (T048), `config/gates.yaml` (T042), `config/quarantine.yaml` (T047), `config/rollback.yaml` (T089), `config/cost_linkage.yaml` (US6), `config/budgets.yaml` (US6), `config/risk_exceptions.yaml`, `config/label_allowlist.yaml` (US4).
- Extra infrastructure and data files: `infra/identities.yaml` (T086), the KMS key ring inside `secret_store` (T079), `docs/feature_register.yaml` (T174), `docker-compose.dev.yml` (T125).
- Extra supporting trees: `tests/support/` (T009), `schemas/` (T021), `docs/evidence/` (T056), `specs/<feature>/dependencies.yaml`.
