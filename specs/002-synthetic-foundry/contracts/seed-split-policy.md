# Seed Split & Anti-Circularity Policy (ADR-015)

**Feature**: `002-synthetic-foundry` | **Date**: 2026-10-02 | **Plan**: [plan.md](../plan.md)

This policy establishes the rules and security boundaries for seed-based data partitioning, preventing data leakage and synthetic self-validation per Constitution Principle VI (Eval-First, Anti-Circularity).

---

## 1. Seed Tiers

```
┌────────────────────────────────────────────────────────────────────────┐
│                          SEED TIER TAXONOMY                            │
├─────────────────┬───────────────────┬──────────────────────────────────┤
│ Tier            │ Access Level      │ Intended Use                     │
├─────────────────┼───────────────────┼──────────────────────────────────┤
│ `dev`           │ Unrestricted      │ Local engineering, model author- │
│                 │                   │ ing, unit & contract tests       │
├─────────────────┼───────────────────┼──────────────────────────────────┤
│ `validation`    │ CI & Team Lead    │ Model selection, hyperparameter  │
│                 │                   │ tuning, integration CI runs      │
├─────────────────┼───────────────────┼──────────────────────────────────┤
│ `sealed`        │ Automated CI Only │ Release-candidate gating, final  │
│                 │ (RC builds)       │ benchmark scoring                │
└─────────────────┴───────────────────┴──────────────────────────────────┘
```

### 1.1 `dev` Tier
- Default root seed: `42`.
- Free for model developers to inspect, visualize, and debug.
- Ground truth is inspectable in local fixtures (`fixtures/eval_truth/`).

### 1.2 `validation` Tier
- Seed range: `1001`–`1010` (10 distinct seeds used for bootstrap confidence intervals).
- Executed on Git pull request merges to `stage`.
- Generates standard distribution parameters matching the baseline domain specifications.

### 1.3 `sealed` Tier
- Seed range: `9001`–`9005` (5 distinct seeds withheld from model developers).
- Executed strictly on release-candidate tags (`v*.*.*-rc*`).
- **Enforcement Mechanism**: The CLI tool fails immediately unless `CI_RELEASE_CANDIDATE=true` is set.
- **Distribution Shifts (`FR-005`)**:
  - Global transaction volume shifted by $\pm 15\%$.
  - Seasonal partner login volatility altered by $+25\%$.
  - Base false positive alert rate shifted between $93.0\%$ and $97.0\%$.
- **Novel Typologies (`FR-006`, `SC-009`)**:
  - Includes at least 2 typologies not documented in developer training guides:
    1. *Typology Alpha (Dormant Crypto Structuring)*: Reactivation of 180-day dormant accounts depositing via high-risk crypto nodes.
    2. *Typology Beta (Multi-Hop Commission Funneling)*: Referral commissions split across 4 layers of inactive dummy affiliates.

---

## 2. Eval-Only Ground Truth Isolation & IAM Policy

### 2.1 Bucket Segregation
- In GCP environments, ground truth is deposited to `gs://<project-id>-eval-truth/`.
- In local development, ground truth is stored in `.eval_truth_isolated/` with restricted POSIX file permissions (`0700`).

### 2.2 Access Control Matrix

| Role / Identity | Read Public Telemetry (`data/raw/*`) | Read Ground Truth (`eval-truth/*`) |
|---|---|---|
| Developer Workstation | Yes | Yes (dev tier only) |
| CI Pipeline (`sa-ci-eval`) | Yes | Yes (all tiers) |
| Evaluation Harness (`sa-eval-harness`) | Yes | Yes (all tiers) |
| Reasoning Mesh (`sa-reasoning-mesh`) | Yes | **DENY (0 permissions)** `[SC-004]` |
| Cockpit Backend (`sa-cockpit-api`) | Yes | **DENY (0 permissions)** |

---

## 3. Label Noise Calibration (`FR-050`)

To prevent supervised classifiers from trivially achieving 100% precision on synthetic data:
- A random flipping mask is applied to analyst ground-truth labels (`is_aml_alert_true_positive`).
- Noise rate: Uniformly sampled between $3.0\%$ and $8.0\%$ `[ASSUMPTION]`.
- Flipped records are flagged internally in the manifest metadata for auditing but presented as authoritative historical decisions to downstream models.
