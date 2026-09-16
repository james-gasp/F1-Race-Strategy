from __future__ import annotations

from pydantic import BaseModel, Field


class StintIn(BaseModel):
    compound: str = Field(..., description="Tire compound, e.g. SOFT/MEDIUM/HARD")
    laps: int = Field(..., gt=0)
    start_tyre_life: int = Field(
        1, gt=0, description="Tire age (laps already run) at the start of this stint; 1 = fresh"
    )


class StrategyIn(BaseModel):
    name: str
    driver: str
    stints: list[StintIn] = Field(..., min_length=1)
