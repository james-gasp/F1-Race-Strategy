# Backend image: FastAPI + FastF1 strategy engine.
# Build:  docker build -t f1-race-strategy-api .
# Run:    docker run -p 8000:8000 -v f1cache:/var/data f1-race-strategy-api
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so code-only changes reuse this cached layer.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api ./api
COPY engine ./engine

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    F1_CACHE_DIR=/var/data \
    PORT=8000

EXPOSE 8000

# One worker: each worker keeps its own in-memory race cache, and a race with
# telemetry loaded costs ~150-350 MB. Hosts like Render inject $PORT.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
