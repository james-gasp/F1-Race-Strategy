from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import races, strategy

app = FastAPI(
    title="F1 Race Strategy Simulator API",
    description="FastF1-calibrated Monte Carlo race strategy simulation and optimization.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server, added ahead of the Phase 3 frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(races.router)
app.include_router(strategy.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
