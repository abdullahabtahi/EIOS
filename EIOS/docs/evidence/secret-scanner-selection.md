# Secret scanner selection (T050)

Date: 2026-10-02. Tags: `[ASSUMPTION]` decision, `[SPIKE]` tool version.

## Trial

`detect-secrets` 1.5.0 was added as a dev dependency and run on one file per shape from `tests/support/secret_shapes.py` (`key = "<value>"`, and the bare block for the private key):

| Shape | detect-secrets result |
|---|---|
| cloud access key | flagged (AWS Access Key plugin) |
| API key | flagged only by the generic Base64 High Entropy plugin, not by a named rule |
| VCS token | flagged (GitHub Token plugin, plus the entropy plugin) |
| private key block | flagged (Private Key plugin) |

## Decision

Use an in-repo regex scanner (`tools/gates/secret_scan.py`) with one named rule per shape, because the API-key shape was detected only through an entropy heuristic that depends on surrounding context. Named rules give a stable rule id per finding, a tested pattern table, and no matched text in any output. `detect-secrets` was removed from the dev dependencies.

## Not covered yet

- Git history: scanned when `.git` exists (tested against a temporary repository); the project is not a git repo today.
- Built images: no image builds exist; arrives with T216.
- `gitleaks` is not installed locally. Re-evaluate it as an additional CI-side scanner once history exists.
