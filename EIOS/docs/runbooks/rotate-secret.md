# Runbook: Rotate and Purge of a Committed Secret

**Owner**: Security Responder / Repository Administrators

## Trigger
A secret or secret-shaped literal is inadvertently committed to the repository, or `secret_scan` gate fails indicating a leaked secret in logs, images, or history.

## Steps
1. **Rotate the Secret Immediately**: Invalidate the leaked secret at the source (e.g., cloud provider, third-party API) and generate a new one.
2. **Update the Secret Store**: Inject the new secret into the managed secret store via the designated secure path, completely external to the codebase.
3. **Purge from History**:
   - Use a tool like `git filter-repo` to purge the secret from the git repository history entirely.
   - Force push the scrubbed history to the remote repository.
4. **Purge from Artifacts**: If the secret was captured in images or logs, delete the compromised container images from the Artifact Registry and redact/purge the logs in Cloud Logging.
5. **Verify**: Ensure the pipeline passes the `secret_scan` gate on the main branch without any warnings.

## Incident Recording
The rotation and purging action must be recorded in an incident report in `docs/evidence/` that references the commit or PR where the leak happened. The incident report must confirm that the old secret was successfully invalidated and purged, and that no secrets remain in the repository.
