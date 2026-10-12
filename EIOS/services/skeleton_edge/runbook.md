# Runbook: skeleton_edge

Stub (FR-039). Edge skeleton: exposes a health endpoint and forwards a correlated call to skeleton_core. The owning feature extends each section with service-specific steps.

## Symptoms

- The health endpoint reports unhealthy or times out.
- A forwarded request fails or returns no correlation identifier.
- The identifier in the response differs from the one sent.

## First checks

- Read the structured logs for the failing correlation identifier.
- Check the service revision and its last deployment.
- Check that skeleton_core answers its own health endpoint.
- Check the edge service identity can still invoke skeleton_core.

## Escalation

Page the on-call engineer of the owning feature. Include the correlation identifier from the failing request, the environment and the revision identifier. If skeleton_core is the failing side, escalate through its runbook.

## Rollback

Shift traffic back to the previous Cloud Run revision, and turn off any configuration flag that was introduced with the faulty revision. Confirm the health endpoint answers and the correlation echo returns the identifier that was sent.
