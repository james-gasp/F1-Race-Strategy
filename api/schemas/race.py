from __future__ import annotations

from pydantic import BaseModel


class DriverStintOut(BaseModel):
    compound: str
    laps: int


class DriverSummaryOut(BaseModel):
    driver: str
    team: str
    grid_position: int
    finish_position: float | None
    status: str
    historical_strategy: list[DriverStintOut]


class PaceModelSummaryOut(BaseModel):
    reference_driver: str
    reference_compound: str
    fuel_effect_per_lap: float
    compound_offset: dict[str, float]
    deg_linear: dict[str, float]
    deg_quad: dict[str, float]
    residual_std: float


class RaceSummaryOut(BaseModel):
    year: int
    event: str
    total_race_laps: int
    pit_loss_s: float
    pace_model: PaceModelSummaryOut
    drivers: list[DriverSummaryOut]
