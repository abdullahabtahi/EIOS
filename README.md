# Real-Time Enterprise Intelligence Operating System (FEIOS / EIOS)

[![Security Scan](https://img.shields.io/badge/security-passed-0e6935.svg)](#security--credentials-policy)
[![Design System](https://img.shields.io/badge/design-Sovereign_Light-1c4587.svg)](DESIGN.MD)
[![Python](https://img.shields.io/badge/python-3.12%2B%20%7C%20uv-blue.svg)](EIOS/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20React%2019-black.svg)](EIOS/web-prototype/)

Institutional-grade, real-time risk surveillance, transaction monitoring, and intelligence operations platform designed for financial crime investigators, compliance officers, and risk operations teams.

---

## Executive Overview

FEIOS provides deterministic, real-time detection and graph-based investigation capabilities across massive transaction streams. Combining an event-driven Python core with an institutional operator cockpit, the platform turns complex financial graphs into actionable compliance dossiers and SAR filings.

### Architecture Highlights

- **Dual-Plane Architecture**: High-throughput asynchronous event ingestion plane paired with an institutional operator cockpit.
- **Topological Risk Graph**: Real-time entity-link resolution, hop exploration, and cyclic transaction ring detection.
- **Automated SAR Generation**: Deterministic structuring of suspicious activity reports backed by verifiable audit evidence.
- **Sovereign Light UI**: High-density, zero-slop analytical interface engineered strictly for enterprise compliance workflows.

---

## Repository Structure

```
.
├── EIOS/                      # Production platform implementation
│   ├── src/eios/              # Python core packages
│   │   ├── api/               # FastAPI route handlers & sentinel webhooks
│   │   ├── conversation/      # Copilot engine & deterministic case assistants
│   │   ├── graph/             # Entity link resolution & network topology
│   │   ├── ingestion/         # L1 event streaming & lakehouse storage
│   │   └── llm_gateway/       # Model gateway with offline deterministic replay
│   ├── infra/                 # Terraform IaC modules (GCP, Cloud Run, Pub/Sub)
│   ├── tools/                 # Quality gates, secret scanners, and compliance linters
│   ├── tests/                 # Unit, integration, and security verification suites
│   └── web-prototype/         # Institutional Next.js Operator Cockpit
│       ├── src/app/cockpit/   # Unified workstation & AML investigator surface
│       └── src/components/    # Sovereign light design system components
├── specs/                     # Formal engineering specifications (001–020)
├── docs/                      # Architectural decisions, runbooks, and threat models
├── DESIGN.MD                  # Sovereign Light design specification
├── CLAUDE.md                  # Project commands and operational reference
└── .github/                   # CI/CD workflows and deployment pipelines
```

---

## Quickstart

### Prerequisites

- **Python**: 3.12 or newer (managed with [`uv`](https://docs.astral.sh/uv/))
- **Node.js**: 20+ and `npm`
- **Terraform**: 1.8+ (optional, for infrastructure deployment)

### 1. Backend Service (EIOS Core)

```bash
# Navigate to the core platform directory
cd EIOS

# Initialize local environment variables
cp .env.example .env

# Install locked dependencies
uv sync

# Start the FastAPI core service
uv run uvicorn eios.api.server:app --host 127.0.0.1 --port 8002 --reload
```

The backend health endpoint will be available at `http://127.0.0.1:8002/health`.

### 2. Operator Cockpit (Frontend UI)

In a separate terminal:

```bash
# Navigate to the cockpit web application
cd EIOS/web-prototype

# Initialize local frontend environment
cp .env.example .env.local

# Install dependencies and launch development server
npm install
npm run dev
```

Open [http://localhost:3000/cockpit](http://localhost:3000/cockpit) to access the Institutional Operator Cockpit.

---

## Quality Gates & Verification

FEIOS enforces strict automated quality gates prior to integration and deployment:

```bash
cd EIOS

# Run the complete test suite
uv run pytest

# Execute security & secret scan
uv run python -m tools.gates.secret_scan

# Run forbidden literal check
uv run python -m tools.repo_checks.forbidden_literals

# Run specific CI gates (lint, types, coverage, contract, etc.)
uv run python -m tools.gates.run_gate lint
uv run python -m tools.gates.run_gate types
```

---

## Security & Credentials Policy

1. **Zero Secret Footprint**: No production secrets, private keys, or credentials exist in the codebase. All sensitive values are managed through Google Cloud Secret Manager.
2. **Workload Identity Federation**: GitHub Actions and service runners authenticate via OIDC Workload Identity; static JSON service account keys are prohibited.
3. **Redaction & Anonymization**: Sensitive transaction data and PII are deterministically hashed using HMAC-SHA256 prior to ingestion.
4. **Environment Isolation**: Always copy `.env.example` templates to `.env` or `.env.local`. Local `.env*` files are strictly excluded via `.gitignore`.

---

## Design System

The platform strictly implements the **Sovereign Light** design aesthetic:
- **100% Light Mode**: High-contrast, stark paper-white surfaces (`#fafafa` / `#ffffff`) with deep charcoal typography (`#111111`).
- **Data Over Chrome**: 1px structural hairline borders (`#e5e5e5`), zero neon glows, zero decorative clutter.
- See [DESIGN.MD](DESIGN.MD) for complete visual tokens and interaction rules.

---

## Contributing

1. Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
2. Follow all specifications documented in [`specs/`](specs/)
3. Ensure all quality gates pass: `uv run python -m tools.gates.run_gate all`
4. Submit a Pull Request following the established conventional commits format.
