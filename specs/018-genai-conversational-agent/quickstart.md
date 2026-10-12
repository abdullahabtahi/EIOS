# Quickstart: Production-Grade Gen AI Conversational Agent Mesh (F018)

**Feature Branch**: `018-genai-conversational-agent`  
**Date**: 2026-10-10  
**Target Environment**: Google Cloud Project `spatial-cat-489006-a4` (Region: `us-central1`)  

---

## 1. Prerequisites & Environment Setup

Verify that Application Default Credentials (ADC) and required environment variables are set:

```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login

# 2. Configure project variables
export GOOGLE_CLOUD_PROJECT="spatial-cat-489006-a4"
export GOOGLE_CLOUD_LOCATION="us-central1"
export EIOS_GEMINI_MODEL="gemini-3.8-flash"

# 3. Enter FEIOS repository
cd FEIOS
```

---

## 2. Interactive CLI Verification (Live Vertex AI Turn)

Execute an interactive turn using the unified `google-genai` conversational agent:

```bash
PYTHONPATH=src .venv/bin/python -m eios.conversation.cli \
  --query "Investigate account CR84920 and check our Q3 AML filing thresholds" \
  --role "aml_investigator" \
  --project "spatial-cat-489006-a4"
```

**Expected Output:**
```text
[SUPERVISOR] Routing intent to: AMLInvestigator
[OMCP_TOOL] Executing inspect_aml_entity(entity_id='CR84920')... -> Multiplier: 16.0x, Volume: $8,000 USD
[VERTEX_SEARCH] Executing query_policy_search('SAR filing threshold')... -> 31 CFR § 1020.320 ($5,000 trigger)
[AUDITOR_GATE] Verifying numerical tokens against tool trace... -> PASS (0 unanchored numbers)
[AGENT_RESPONSE]
Entity CR84920 presents an elevated composite risk score of 89 with a 16.0x discrepancy multiplier between declared monthly income ($500 USD) and realized 30-day deposit volume ($8,000 USD). Under 31 CFR § 1020.320 and our internal AML Policy, transactions exceeding $5,000 with unverified wealth origins mandate filing FinCEN Form 111.
[STAGED_ACTION]
- Type: HoldWithdrawal
- Target: CR84920
- Intent ID: act_1791624891002
- KMS Signature: ECDSA P-256 [VERIFIED]
- Status: STAGED_FOR_REVIEW (Requires Four-Eyes Authorization)
```

---

## 3. Automated Red-Line Suite & Deterministic Fallback Test

Run the offline deterministic test suite (ensuring Constitution Principle VIII fallback operates when offline):

```bash
PYTHONPATH=src .venv/bin/pytest tests/conversation/test_red_line_gates.py -v
```

**Validates:**
- `RL-1`: Zero metric hallucination on synthetic gold sets.
- `RL-2`: Zero direct database writes (static AST assertion + runtime deny).
- `RL-3`: 100% citation coverage on generated narratives.
- `RL-4`: Honest refusal ("insufficient data") on speculative queries.
- `RL-5`: Statutory legal citation exemption without false-positive blocks.
- `RL-6`: Turn latency $\le 3.5\text{s}$ at p95.

---

## 4. Vertex AI Evaluation Harness (`EvalTask`)

Run the automated Vertex AI Gen AI evaluation pipeline:

```bash
PYTHONPATH=src .venv/bin/python -m eios.evals.run_vertex_eval \
  --model "gemini-3.8-flash" \
  --test-suite "tests/fixtures/eval_golden_turns.json"
```

**Metrics Evaluated:**
- `groundedness`: $\ge 0.95$ threshold (CI blocking).
- `faithfulness`: $\ge 0.95$ threshold (CI blocking).
- `safety`: $1.00$ threshold (0 toxicity or prompt injection leaks).
