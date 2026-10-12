## Description

<!-- Provide a concise explanation of what this pull request changes and why. -->

## Changes Made

- 

## Verification & Quality Gates

Please verify that the following checks have been executed:

- [ ] `uv run pytest` passes without failures.
- [ ] `uv run python -m tools.gates.secret_scan` passes with 0 findings.
- [ ] `uv run python -m tools.repo_checks.forbidden_literals` passes with 0 findings.
- [ ] Frontend tests pass (`npm run test` in `EIOS/web-prototype`).
- [ ] No hardcoded secrets, API keys, or live credentials committed.
- [ ] Compliant with Sovereign Light design tokens (if UI changes).

## Invariants & Principles Checklist

- [ ] **Principle I (Deterministic Semantic Layer)**: LLMs do not compute business metrics.
- [ ] **Principle II (No Autonomous Write-Back)**: State alterations require explicit operator staging and 2PC.
- [ ] **Principle III (Attribution Rigor)**: Causal driver attributions sum to 100.0% +/- 0.01%.
