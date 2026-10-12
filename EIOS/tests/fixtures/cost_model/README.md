# Cost model fixtures

Inputs to `tests/unit/tools/cost_check/`. Not collected by pytest.

Every price, quantity and date in these files is a placeholder `[ILLUSTRATIVE]`. None is a real
tariff or a real vendor price; they exist only so the checker rules can be exercised. Nothing
here may be quoted as a cost figure.

Layout (assembled into a throwaway repo by `tests/support/cost_repo.py`):

- `clean/` is a repo tree that passes: `docs/cost_model.csv`, `config/cost_linkage.yaml`, and
  `config/llm_gateway.{dev,stage}.yaml` (dev carries a stub price, stage carries none).
- `csv/<name>.csv` replaces `docs/cost_model.csv`. Each failure file keeps the two model-token rows
  on lines 2 and 3 (the linkage needs them) and puts its fault on line 4.
- `gateways/<name>.yaml` replaces `config/llm_gateway.dev.yaml`.
- `linkage/<name>.yaml` replaces `config/cost_linkage.yaml`.

The fixtures' dates sit shortly before the fixed test clock (2026-01-01), except
`csv/stale_price.csv` (2025-01-01), which is older than the 90-day threshold on purpose.
