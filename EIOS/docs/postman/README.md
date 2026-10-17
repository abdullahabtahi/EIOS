# EIOS Postman Quality Gate & Interactive Showcase

This directory provides standalone, portable Postman assets to run and verify the **Enterprise Intelligence Operating System (EIOS)** API locally or in CI/CD pipelines.

## Contents
- **`eios_showcase.postman_collection.json`**: Complete showcase test collection covering AML triage, Google Cloud KMS Action Intent signing, DoWhy causal scenario propagation (<200ms [TARGET]), Cashier Sentinel HMAC interception (<150ms SLA [TARGET]), and deterministic figure replay.
- **`eios_environment.postman_environment.json`**: Pre-configured environment variables for both Local (`http://127.0.0.1:8002`) and Cloud Run (`https://eios-web-562008989053.us-central1.run.app`).
- **Dynamic OpenAPI 3.1.0 Contract**: Served live directly by FastAPI at `/openapi.json` (and interactive Swagger documentation at `/docs`).

---

## 1. Quick Start via CLI (Newman)

Run the entire showcase test suite headlessly from the repository root:

```bash
# 1. Start the API gateway locally (if not already running)
PYTHONPATH=src uv run uvicorn eios.api.app:app --host 127.0.0.1 --port 8002 &

# 2. Execute the test collection via Newman
npx newman run docs/postman/eios_showcase.postman_collection.json \
  -e docs/postman/eios_environment.postman_environment.json
```

---

## 2. Quick Start in Postman Desktop / Web

1. Open Postman.
2. Click **Import** in the upper-left corner.
3. Drag and drop both `eios_showcase.postman_collection.json` and `eios_environment.postman_environment.json`.
4. In the environment selector (top-right), select **`EIOS Environment (Cloud Run & Local)`**.
5. Click **Run Collection** -> **Run EIOS Enterprise Intelligence — Showcase & Quality Gate**.
6. View the visual graphs in the **Visualize** tab for Request 4.2 (Attribution Waterfall) and Request 1.2 (Risk Dossier).

---

## 3. Verified Invariants
- **RL-1 (No LLM-Computed Arithmetic)**: Proven in Request 2.1 via deterministic provenance citations.
- **RL-2 (KMS Four-Eyes Governance)**: Proven in Request 1.3 with Cloud KMS ECDSA P-256 intent signatures.
- **RL-6 (Causal What-If Attribution)**: Proven in Request 4.2: latency < 200ms [TARGET] and attribution summing exactly to 100.0%.
- **RL-7 (Deterministic Replay Gate)**: Proven in Request 2.2: 100% figure parity replay against read models [TARGET].
