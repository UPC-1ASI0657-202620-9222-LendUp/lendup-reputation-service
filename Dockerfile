# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.12.12-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12.12-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 lendup && useradd --system --uid 10001 --gid lendup lendup
WORKDIR /app
COPY --from=builder --chown=lendup:lendup /app/.venv /app/.venv
COPY --chown=lendup:lendup src ./src
COPY --chown=lendup:lendup alembic ./alembic
COPY --chown=lendup:lendup alembic.ini pyproject.toml ./
USER lendup
EXPOSE 8082
CMD ["python", "-m", "lendup_reputation.server"]
