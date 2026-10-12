# Contributing to EIOS

Thank you for your interest in contributing to the **Enterprise Intelligence Operating System (EIOS)**. This document outlines the engineering guidelines and pull request lifecycle followed by the team.

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Development Setup

### Prerequisites

- **Python**: 3.12+ managed via [`uv`](https://docs.astral.sh/uv/)
- **Node.js**: 20+ and `npm`
- **Git**: 2.30+

### Quickstart

```bash
# Clone the repository
git clone https://github.com/abdullahabtahi/EIOS.git
cd EIOS

# 1. Set up Python backend
cd EIOS
cp .env.example .env
uv sync
uv run pytest tests/unit/tools/gates/ -q

# 2. Set up Next.js Operator Cockpit
cd web-prototype
cp .env.example .env.local
npm install
npm run test
```

---

## Engineering Standards

### 1. Branch Strategy

- Base branch: `main`
- Branch naming conventions:
  - `feat/feature-name` (New capability or workstation feature)
  - `fix/bug-description` (Bug fixes and patches)
  - `refactor/scope` (Code refactoring with zero behavioral change)
  - `perf/optimization` (Performance enhancements)
  - `docs/topic` (Documentation updates)

### 2. Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat(graph): implement dynamic hub suppression in topological network canvas`
- `fix(ledger): validate HMAC nonce expiry on two-phase commit tokens`
- `refactor(cockpit): align color tokens with Sovereign Light mode`

### 3. Automated Quality Gates

Before submitting a pull request, ensure all local verification checks pass:

```bash
cd EIOS

# Run unit tests
uv run pytest

# Run secret scan gate
uv run python -m tools.gates.secret_scan

# Run forbidden literals check
uv run python -m tools.repo_checks.forbidden_literals

# Run specific gates
uv run python -m tools.gates.run_gate lint
uv run python -m tools.gates.run_gate types
```

For frontend contributions:

```bash
cd EIOS/web-prototype
npm run test
```

---

## Pull Request Process

1. Ensure existing tests pass and add coverage for new behaviors.
2. Confirm zero secrets, keys, or credentials are added.
3. Fill out the pull request template completely.
4. All CI matrix gates in `.github/workflows/pr.yml` must turn green before merging.
5. Pull requests require code review approval prior to landing on `main`.
