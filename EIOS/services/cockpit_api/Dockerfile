# cockpit_api image. Build from the repository root (it needs specs/ for the card contracts):
#   docker build -f EIOS/services/cockpit_api/Dockerfile .
# Nothing secret is baked in: configuration arrives through environment variables and Secret Manager
# references at run time. The directory layout mirrors the repository because the code resolves
# schemas/, prompts/ and specs/ relative to its own location.

FROM python:3.14-slim AS builder
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /repo/EIOS
RUN pip install --no-cache-dir uv
COPY EIOS/pyproject.toml EIOS/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/repo/EIOS/src PATH=/repo/EIOS/.venv/bin:$PATH \
    PORT=8080
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /repo/EIOS
COPY --from=builder /repo/EIOS/.venv /repo/EIOS/.venv
COPY EIOS/src/eios ./src/eios
COPY EIOS/schemas ./schemas
COPY EIOS/prompts ./prompts
COPY specs/012-cockpit/contracts /repo/specs/012-cockpit/contracts
COPY specs/013-observability-sre/contracts /repo/specs/013-observability-sre/contracts
COPY specs/014-flywheel/contracts /repo/specs/014-flywheel/contracts
COPY specs/015-hardening-dr/contracts /repo/specs/015-hardening-dr/contracts
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn eios.api.app:app --host 0.0.0.0 --port ${PORT}"]
