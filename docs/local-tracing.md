# Local tracing (development only)

Watch every copilot turn as a waterfall on this machine, with no cloud call. ADK already emits the spans
(`invoke_agent`, `call_llm`, `generate_content`, `execute_tool`); `EIOS_TRACE_EXPORT=otlp` sends them to a collector
on `127.0.0.1`. Cloud Trace for deployed services is in `docs/cloud-trace.md`.

## Run it

1. Viewer (one container, Arize Phoenix; UI and OTLP/HTTP on 6006):
   `docker run -d --name eios-phoenix -p 127.0.0.1:6006:6006 arizephoenix/phoenix:latest`
2. Gateway, from `EIOS/`, the usual local command (`reference-local-gateway-command`) plus:
   `EIOS_TRACE_EXPORT=otlp EIOS_TRACE_CAPTURE_CONTENT=1 EIOS_SERVICE_NAME=eios-api-local`
3. Open `http://127.0.0.1:6006`, project `default`, ask a question in the cockpit.
4. Done: `docker rm -f eios-phoenix`. Traces live in the container only.

## What you see

One turn is a tree: `invocation` > `invoke_agent <workstation>` > `prefetch`, `drafter` (a `call_llm` and
`generate_content` per model call, an `execute_tool <name>` between them), `assembler`. Each model span has the model id
and token counts; each span has the request's `correlation_id`. With content on, `gcp.vertex.agent.llm_request` and
`llm_response` hold the prompt and the draft, so a turn that failed closed shows the placeholder the model wrote.

## Safety rules (enforced, tested in `tests/observability/test_local_otlp_trace.py`)

- `otlp` is refused unless `EIOS_ENVIRONMENT` is `dev` or `test` (an unset value is refused too), so a deployed service
  cannot start it.
- Prompt and answer text is captured only with `otlp` plus `EIOS_TRACE_CAPTURE_CONTENT=1`. In every other mode and
  environment it stays off, whatever the environment says; the choice is made once at start-up. The text can hold account
  data (synthetic in this build), so keep the collector on localhost and do not share the container.
- Phoenix is a local tool, not part of the product; nothing in the repo depends on it. Any OTLP collector works: set
  `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (Jaeger takes `http://127.0.0.1:4318/v1/traces`).
