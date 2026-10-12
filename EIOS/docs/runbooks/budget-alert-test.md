# Runbook: Budget Alert Test (T215)

**Owner**: Repository Administrators / Operations

## Trigger
Periodic validation (at least quarterly) to ensure that the cloud environment budget alerts are correctly configured and actively firing to the designated notification channels.

## Steps
1. **Trigger Alert**: Manually trigger a budget alert via the Cloud Console by temporarily lowering a budget threshold in a non-production environment (`dev` or `stage`) so that current spend exceeds the threshold, or use the cloud provider's alert simulation tools.
2. **Verify Notification**: Confirm that the alert successfully routes to the expected notification channels (e.g., email, Slack, PagerDuty).
3. **Restore Configuration**: Revert the budget threshold to its original value as defined in `config/budgets.yaml` or equivalent infrastructure code.
4. **End-to-End Probe**: Execute the budget probe tool `uv run python -m tools.budget_probe` and verify it reports the correct status and limits.

## Incident Recording
The successful (or failed) outcome of the budget alert test must be recorded in `docs/evidence/` as a budget test rehearsal. This record should note the date, who performed the test, the thresholds tested, and confirmation of receipt in the notification channel.
