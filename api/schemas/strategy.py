from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.common import StintIn, StrategyIn


class SimulateRequest(BaseModel):
    year: int
    event: str
    driver: str
    stints: list[StintIn] = Field(..., min_length=1)
    n_sims: int = Field(2000, gt=0, le=20000)
    seed: int | None = None
    start_lap_number: int = Field(1, gt=0)


class SimulationSummaryOut(BaseModel):
    mean_s: float
    median_s: float
    std_s: float
    p10_s: float
    p90_s: float
    n_sims: int


class CompareRequest(BaseModel):
    year: int
    event: str
    strategies: list[StrategyIn] = Field(..., min_length=1)
    n_sims: int = Field(2000, gt=0, le=20000)
    seed: int | None = None
    start_lap_number: int = Field(1, gt=0)


class StrategyResultOut(BaseModel):
    strategy: str
    n_stops: int
    total_laps: int
    mean_s: float
    median_s: float
    std_s: float
    p10_s: float
    p90_s: float
    prob_fastest: float


class CompareResponse(BaseModel):
    results: list[StrategyResultOut]


class OptimizeRequest(BaseModel):
    year: int
    event: str
    driver: str
    current_compound: str
    current_tyre_life: int = Field(..., gt=0)
    next_lap_number: int = Field(..., gt=0)
    total_race_laps: int | None = Field(
        None, description="Defaults to the full race distance from the loaded race data"
    )
    compounds_used_so_far: list[str] = Field(default_factory=list)
    enforce_two_compound_rule: bool = True
    lap_step: int = Field(1, ge=1)
    n_sims: int = Field(1000, gt=0, le=20000)
    seed: int | None = None


class OptimizeResponse(BaseModel):
    recommended: StrategyResultOut
    candidates: list[StrategyResultOut]


class FieldRequest(BaseModel):
    year: int
    event: str
    n_sims: int = Field(2000, gt=0, le=20000)
    seed: int | None = None


class DriverPositionProbabilityOut(BaseModel):
    driver: str
    expected_position: float
    prob_win: float
    prob_podium: float
    position_probabilities: dict[int, float]


class FieldResponse(BaseModel):
    drivers: list[DriverPositionProbabilityOut]
