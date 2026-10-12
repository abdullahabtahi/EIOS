# SC-001: every gate fails on its own faulty change

**Date**: 2026-10-02. **Scenario**: quickstart scenario 1. **Method**: for each gate in `config/gates.yaml`, the clean skeleton (`tests/fixtures/clean_skeleton/`) was copied, the gate's `proof_fixture` overlay was applied, and that gate alone was run through `tools.gates.runner.run_gates` with the same settings `make check` uses. The same procedure is the automated test `tests/integration/test_faulty_changes.py`, which was also run with `EIOS_TEST_NETWORK=1` (re-run after the move into `FEIOS/`).

## Clean skeleton

All fourteen gates (11 pr, 2 promote, 1 release_candidate) `pass`; run `ae62c88c97964ca098d816cfb159af19`, state `passed`, exit 0. The run included `vuln_scan`, which queries a live advisory database.

## Faulty changes

Each row: the clean skeleton plus that gate's `proof_fixture` overlay (`tests/fixtures/faulty_changes/<gate>`), that gate alone, same settings as `make check`. Every run ended in state `failed` with exit code 1.

| Gate | Stage | Outcome | Run id |
|---|---|---|---|
| `lint` | pr | fail | `c2e5f8385f72447d9bf5429729513506` |
| `types` | pr | fail | `26a9d632870641f29a98b7e84d2c9268` |
| `coverage` | pr | fail | `66585915800240028c1b493d89454724` |
| `contract` | pr | fail | `a7d6e930e6a042bcbd9e9f9ab60d87e5` |
| `eval_smoke` | pr | fail | `9c9ab35276814b1f9b4fdfd2b2bec118` |
| `red_line` | pr | fail | `01805b5efba34c5da5694ba8277b2237` |
| `vuln_scan` | pr | fail | `61320c8a4ba24de2ab239c81d6115e2c` |
| `secret_scan` | pr | fail | `cb280b21943e417983d142fdfc3b5ae4` |
| `iac_plan` | pr | fail | `de2bda4df4af4e01abcce1bdadbbead2` |
| `infra_policy` | pr | fail | `f2a1a550aec64aee9a7ba9e82ec1d1c9` |
| `open_decision_check` | pr | fail | `91709217c0154bc7b097393e51d0c60f` |
| `validation` | promote | fail | `7a8f08b51d6542c8aeb9e99b2b12b8a4` |
| `resilience` | promote | fail | `83dfce00aa60480489b5ec8522658195` |
| `sealed_eval` | release_candidate | fail | `4355c996e75f4ee5ba68a79ca7119a4e` |

Result: 14 of 14 gates fail on their own faulty change and pass on the clean skeleton. The run records were written under temporary directories and are not retained; the test reproduces them on demand.

## Real tree

`make check` from `FEIOS/` (the 11 pr gates): run `e42adc44ce6b4ffb837a0afcd0dabaa5`, all `pass`, quarantined gates 0. Record under `evals/reports/run-records/` (generated, git-ignored). The promote and release_candidate gates run only in their workflows, not in `make check`.

## Limits of this evidence

- `tflint`, `trivy`, `gitleaks` and `syft` are not installed on this machine. The `iac_plan` fault is caught by `terraform fmt` and `terraform validate`; `tflint` is required in CI (`EIOS_REQUIRE_TFLINT=1`). No container or image scan exists until T216.
- The secret fixture generates its secret at test time from `tests/support/secret_shapes.py`; no secret-shaped string is stored in the repository.
- `resilience` and `validation` overlap on the `resilience-*` suites (the former is an id-prefix slice of the latter). `contract`, `eval_smoke` and `red_line` have no registered suites in F00 on the real tree. Their faulty-change proof registers a failing suite in the overlay, which shows the hook blocks; it does not show any real suite passing.
- The history secret scan needs a `.git` directory and was not exercised on the real tree.
- The dependency advisory audit queries a live database, so its clean result is true only for the run date.
