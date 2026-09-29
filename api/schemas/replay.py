from __future__ import annotations

from pydantic import BaseModel


class CircuitOutlineOut(BaseModel):
    points: list[tuple[float, float]]
    length_m: float


class UndercutThreatOut(BaseModel):
    gap_s: float
    pit_loss_s: float
    est_pace_gain_per_lap_s: float
    laps_to_undercut: float | None
    is_threat: bool


class DriverFrameOut(BaseModel):
    driver: str
    team: str
    position: int | None
    gap_to_leader_s: float | None
    gap_ahead_s: float | None
    compound: str | None
    tyre_life: float | None
    stint: int | None
    pit_this_lap: bool
    sector1_s: float | None
    sector2_s: float | None
    sector3_s: float | None
    undercut_threat: UndercutThreatOut | None


class LapFrameOut(BaseModel):
    lap_number: int
    drivers: list[DriverFrameOut]


class ReplayOut(BaseModel):
    total_laps: int
    frames: list[LapFrameOut]


class TelemetryPointOut(BaseModel):
    time_s: float
    x: float
    y: float
    speed_kmh: float
    # Lap-relative: distance/time since this lap's first sample, so two laps
    # (or two drivers) can be overlaid on a shared distance axis.
    distance_m: float
    lap_time_s: float
    throttle_pct: float
    brake: bool
    gear: int


class DriverTelemetryOut(BaseModel):
    driver: str
    lap_number: int
    points: list[TelemetryPointOut]


class WeatherSampleOut(BaseModel):
    time_s: float
    lap_number: int | None
    air_temp_c: float
    track_temp_c: float
    humidity_pct: float
    rainfall: bool
    wind_speed_kmh: float
    wind_direction_deg: float


class WeatherOut(BaseModel):
    samples: list[WeatherSampleOut]
