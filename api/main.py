from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import races, replay, strategy
from api.settings import ALLOWED_ORIGINS, FRONTEND_DIST_DIR

app = FastAPI(
    title="F1 Race Strategy Simulator API",
    description="FastF1-calibrated Monte Carlo race strategy simulation and optimization.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # set via the ALLOWED_ORIGINS env var in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(races.router)
app.include_router(strategy.router)
app.include_router(replay.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Serve the built website from the same server when configured (single-URL
# deploys, e.g. Hugging Face Spaces). Mounted last so every API route above
# takes precedence over the static catch-all at `/`.
if FRONTEND_DIST_DIR is not None:
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
