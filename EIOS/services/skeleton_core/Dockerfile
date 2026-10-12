# skeleton_core image. Build from the FEIOS root: docker build -f services/skeleton_core/Dockerfile .
# [SPIKE] Base image tag and uv installation are unverified and deliberately not version-pinned;
# confirm and pin them (digest included) before relying on this image (task T216).
# Nothing secret is copied or baked in: configuration arrives through environment variables
# (EIOS_PORT, EIOS_SERVICE_NAME, EIOS_OTEL_EXPORTER_ENDPOINT) at run time.

FROM python:3.14-slim AS builder
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src:/app PATH=/app/.venv/bin:$PATH \
    EIOS_PORT=8080 EIOS_SERVICE_NAME=skeleton_core
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/eios ./src/eios
COPY services/__init__.py ./services/__init__.py
COPY services/skeleton_core ./services/skeleton_core
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn --factory services.skeleton_core.app:create_app --host 0.0.0.0 --port ${EIOS_PORT}"]
