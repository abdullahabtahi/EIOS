# Contract: configuring the ADK analytics plugin (spec 021 uses this, spec 022 defines it)

Spec 021 writes per-turn events with the first-party BigQuery agent analytics plugin; no telemetry writer is built in this feature. This note fixes what that configuration must achieve, so it is configuration and not new code.

| Requirement | How the plugin is configured |
|---|---|
| Only the fields in `telemetry-event.schema.json` reach the table | Event allow-list limited to model, tool and final-response events; a content formatter that projects each event onto the schema fields |
| No raw identifiers | The content formatter replaces operator and session identifiers with `tok_` tokens (`eios.agent_gates.telemetry.token`) and redacts text with `redact_excerpt` (emails and identifier shapes, 200 characters). It is a redaction boundary: if it fails, the row is written without content |
| Full prompts and responses stay out | Do not enable the prompt-response logging tier that exports full content to Cloud Storage and BigQuery; keep trace-content capture off (`NO_CONTENT`) |
| Field names follow OpenTelemetry GenAI conventions | `runtime` to `gen_ai.agent.name`, `tokens_in` and `tokens_out` to `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`, `tool_names` to `gen_ai.tool.name`, `session_token` to `gen_ai.conversation.id`; conventions are in Development status, so pin the version |
| Provable | After a suite run, `eios.agent_gates.telemetry.scan_events` over the written rows returns an empty list (SC-008) |
| Dataset | A dedicated dataset with customer-managed encryption; the table is the source of lighthouse M3 and M5 in production |
