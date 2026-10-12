# Runbook: Pipeline-Unavailable Emergency Path

**Owner**: Repository Administrators / Engineering Lead

## Trigger
The primary CI/CD pipeline provider (e.g., GitHub Actions) is completely unavailable, but a critical emergency hotfix must be deployed to `prod-like` to prevent or mitigate severe business impact.

## Steps
1. **Identify the Fix**: Develop the hotfix locally and ensure it passes the local check (`make check` / `uv run python -m tools.gates.local`).
2. **Commit locally**: Commit the change to a local branch.
3. **Emergency Local Promotion**: Use the authenticated federated identity locally (if emergency roles permit) or break-glass cloud credentials to deploy the image and infrastructure to `prod-like`.
4. **Retroactive Review**: Once the pipeline is restored, push the emergency hotfix branch to the repository.
5. **Merge via Normal Process**: Open a pull request for the hotfix, get standard approvals, pass all automated gates, and merge it into the main line to sync the repository state.

## Incident Recording
The break-glass action must be recorded immediately in a tracking system. A full incident report must be added to `docs/evidence/` detailing the timeline, the reason for the emergency path, who authorized it, and linking to the retroactive PR that formally merged the fix.
