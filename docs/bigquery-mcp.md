# BigQuery MCP: where it connects, and where it must not

**Question.** Google ships a BigQuery MCP server and ADK ships `BigQueryToolset`. What do we connect, and to what?

**Checked, not assumed** (ADK 2.11, the deployed warm tier read through the BigQuery MCP tools, read-only):
- The deployed `warm_aml.transactions_aml` matches `warm/schema.py`: day-partitioned on `timestamp` with `requirePartitionFilter`, clustered on `client_id, txn_type`, labelled by Terraform; 17,646 rows in 31 partitions `[MEASURED]`. The API's identity holds dataset *reader* only. The named query `account_daily_activity` over a 30-day window processes about 0.8 MB against the 100 MB cap `[MEASURED, dry run]`. So the warm store's own cost guard (`maximum_bytes_billed`, a required partition filter) is already the server-side pattern Google's BigQuery guidance recommends; an earlier claim that it was hand-rolled was wrong.
- `BigQueryToolset` (`google.adk.integrations.bigquery`; the old `google.adk.tools.bigquery` path is deprecated) exposes `execute_sql`, `forecast`, `analyze_contribution`, `detect_anomalies`, `ask_data_insights`, `search_catalog` and metadata tools. `BigQueryToolConfig` caps bytes billed and rows returned and blocks writes (SELECT-only, checked by a dry run). It has **no dataset allow-list**: what the credentials can read is what the model can read.
- Google's remote BigQuery MCP server offers the same shape: metadata tools and a SELECT-only `execute_sql`, jobs labelled `goog-mcp-server: true`, billed to the named project.

**Why the copilot does not get raw SQL (either route).**
1. *Figures.* The assembler shows a number only when a governed tool returned it this turn, with a fact id, unit and data origin. A foreign tool's rows carry none, so every figure drawn from them fails closed: safe, and useless.
2. *Metric definitions.* A model that writes the SQL chooses what "deposits" means each time. The metric registry (ADR-003) exists so a definition is made once and measured once; named queries keep that, free SQL gives it up.
3. *Roles and PII.* The port scopes tools per workstation and marks PII. One BigQuery identity behind free SQL has neither; the only scope control is IAM on the dataset.

**Where BigQuery MCP does belong.**
- *Engineering and analysis (now).* Claude Code, Gemini CLI and analysts use the BigQuery MCP plugin against dev data, read-only, to check parity, inspect schemas and measure query cost. This note was grounded that way.
- *Our port as an MCP server (phase 7).* Outside agents reach BigQuery-backed answers only through the governed port, never around it.
- *A governed SQL capability, if the named-query catalogue proves too narrow.* A port tool, not a toolset: a dedicated service account that can read one authorised-view dataset (PII columns tokenised), a dry run that refuses any table outside it, the byte and row caps, job labels, and results returned as typed facts. It needs three decisions from the owner: which datasets, what stays hidden, which roles. Not built.

**Changed with this note.** Warm-tier query jobs now carry labels (`app`, `component`, `query`, `environment`), so spend per named query can be read from `INFORMATION_SCHEMA.JOBS`; before, every job was anonymous. Labels BigQuery would reject are dropped with a warning, never sent.

**Not done.** No `McpToolset` or `BigQueryToolset` wired into the copilot; no new IAM; nothing deployed.
