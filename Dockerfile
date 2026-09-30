# Full app image: the FastAPI + FastF1 backend, also serving the built website,
# so everything runs from one server and one URL.
# Build:  docker build -t f1-race-strategy .
# Run:    docker run -p 8080:8080 f1-race-strategy   ->  http://localhost:8080

# ---- Frontend build ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# "/" = call the API on the same origin the page was loaded from.
RUN VITE_API_BASE_URL=/ npm run build

# ---- Backend ----
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so code-only changes reuse this cached layer.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api ./api
COPY engine ./engine
COPY --from=frontend /frontend/dist ./frontend_dist

# Run as an unprivileged user; the cache folder must be writable by it (on
# Render a mounted disk replaces it).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /var/data \
    && chown -R app:app /var/data
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    F1_CACHE_DIR=/var/data \
    FRONTEND_DIST_DIR=/app/frontend_dist \
    PORT=8080

EXPOSE 8080

# One worker: each worker keeps its own in-memory race cache, and a race with
# telemetry loaded costs ~150-350 MB. Cloud Run / Render inject their own $PORT.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
