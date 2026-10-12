# Runbook: Rollback (FR-010)

**Owner**: Repository Administrators / On-call Engineer

## Trigger
A deployed revision in `stage` or `prod-like` exhibits critical regressions, data loss, or systemic failures that cannot be fixed by a fast-follow forward promotion within the time bound specified in `config/rollback.yaml`.

## Steps
1. **Identify Revision**: Identify the previous stable revision (commit hash or image digest) to rollback to.
2. **Execute Rollback**: Use the rollback CLI (`uv run python -m tools.gates.rollback <environment>`) or execute the fallback deployment workflow using the previous stable artifact.
3. **Verify**: Ensure the environment is running the expected previous stable revision and telemetry shows recovery.
4. **Configuration**: If the rollback relies on a configuration toggle or feature flag, ensure the flag is flipped as per `config/rollback.yaml`.

## Incident Recording
The rollback execution time is automatically recorded on the Pipeline Run Record. The incident must be documented in `docs/evidence/` with the reason for rollback, time elapsed, and subsequent post-mortem linking to the failed Pipeline Run Record.
