# Runbook: skeleton_core

Stub (FR-039). Core skeleton: exposes a health endpoint and echoes the correlation identifier it receives. The owning feature extends each section with service-specific steps.

## Symptoms

- The health endpoint reports unhealthy or times out.
- The echo returns an error, or a different identifier than the one received.
- Callers report authorisation failures.

## First checks

- Read the structured logs for the failing correlation identifier.
- Check the service revision and its last deployment.
- Check the service identity and that the caller is permitted to invoke the service.

## Escalation

Page the on-call engineer of the owning feature. Include the correlation identifier from the failing request, the environment and the revision identifier. If the edge is the failing side, escalate through the skeleton_edge runbook.

## Rollback

Shift traffic back to the previous Cloud Run revision, and turn off any configuration flag that was introduced with the faulty revision. Confirm the health endpoint answers and the correlation echo returns the identifier that was sent.
