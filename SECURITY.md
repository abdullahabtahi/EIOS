# Security Policy

## Supported Versions

Security updates and critical patches are actively provided for the following releases:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

---

## Reporting a Vulnerability

The EIOS engineering team takes the security of financial surveillance and operational intelligence systems seriously. If you discover a potential vulnerability, please follow our responsible disclosure process:

1. **Do NOT open a public GitHub issue.**
2. Send an email to [abdullahabtahi21@gmail.com](mailto:abdullahabtahi21@gmail.com) with the subject line `[SECURITY REPORT] EIOS - Vulnerability Discovery`.
3. Provide a detailed summary including:
   - Type of vulnerability (e.g., secret leakage, token tampering, SSRF, injection).
   - Step-by-step instructions or proof-of-concept to reproduce the issue.
   - Any potential impact on event streams, audit logs, or cryptographic anchors.
4. You will receive an initial response acknowledging receipt within **48 hours**.
5. Once a fix is verified, a patch will be deployed, and credit will be acknowledged in release notes with your consent.

---

## Security Invariants

All contributors and operators must strictly respect these system invariants:
- **Zero Hardcoded Secrets**: Secrets and tokens must never be committed to source control. Use Google Cloud Secret Manager or local `.env` files (never committed).
- **Two-Phase Commit (2PC)**: No state-altering action may bypass operator authorization and Cloud KMS signature validation.
- **Cryptographic Auditability**: State alterations must generate immutable, verifiable audit records anchored to retention-locked storage.
