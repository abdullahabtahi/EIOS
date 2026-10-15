# Cloud Trace for the copilot

**Why.** ADK wraps each turn in `invoke_agent`, `call_llm` and `execute_tool` spans. No tracer provider was ever installed (`setup_telemetry` in `common/otel.py` has no caller), so on Cloud Run those spans went nowhere and a slow turn could only be explained from our own `timing_ms` field. The advice in `docs/assistant-latency.md` to "measure per stage before blaming code" now has a standard tool: Trace explorer.

**What changed.** `observability/cloud_trace.py`:
- `configure_cloud_trace()` runs at start-up. `EIOS_TRACE_EXPORT=cloud_trace` installs ADK's own Google Cloud exporter (traces only, not metrics or logs) and a processor that stamps the request's `correlation_id` on each span, so a trace joins to its log lines. Unset or `off` installs nothing (dev and tests). Any other value fails start-up, so a typo cannot silently disable tracing. An exporter that cannot be set up is logged and the service runs without traces.
- Message content stays off. ADK puts the prompt and the answer on some spans by default; here that is account data. The process environment is forced to no-content at start-up (even with export off, so adding an OTLP endpoint later cannot start shipping text), and every run carries `RunConfig(telemetry=TelemetryConfig(capture_message_content=NO_CONTENT))`. Tests pin both.

**Infra (not applied).** `cockpit.tf` sets `EIOS_TRACE_EXPORT` and `EIOS_SERVICE_NAME` on `eios-api` and declares `cloudtrace.googleapis.com`; the runtime identity already holds `roles/cloudtrace.agent`. A deploy needs its own go.

**Not done, on purpose.**
- The BigQuery Agent Analytics plugin: the standing decision is no telemetry to BigQuery.
- The structured JSON log handler in `common/otel.py` is also unused in production, so Cloud Logging lines carry no trace id yet. Wiring it is a separate change.
- `observability/tracing.py` is a hand-written span model that duplicates OpenTelemetry. Nothing on the agent path uses it; remove it in its own change once its callers are confirmed.
