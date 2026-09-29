from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.context import get_circuit_outline, get_driver_telemetry, get_race_context, get_weather
from api.schemas.replay import (
    CircuitOutlineOut,
    DriverFrameOut,
    DriverTelemetryOut,
    LapFrameOut,
    ReplayOut,
    TelemetryPointOut,
    UndercutThreatOut,
    WeatherOut,
    WeatherSampleOut,
)
from engine.strategy.replay import build_lap_frames

router = APIRouter(prefix="/races/{year}/{event}", tags=["replay"])


@router.get("/circuit", response_model=CircuitOutlineOut)
def get_circuit(year: int, event: str) -> CircuitOutlineOut:
    try:
        outline = get_circuit_outline(year, event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Could not build circuit outline for {year} {event}: {exc}"
        ) from exc
    return CircuitOutlineOut(points=list(outline.points), length_m=outline.length_m)


@router.get("/replay/frames", response_model=ReplayOut)
def get_replay_frames(year: int, event: str) -> ReplayOut:
    try:
        ctx = get_race_context(year, event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Could not load race {year} {event}: {exc}"
        ) from exc

    lap_frames = build_lap_frames(ctx.laps, ctx.pace_model, ctx.pit_loss_model)

    frames = [
        LapFrameOut(
            lap_number=lap.lap_number,
            drivers=[
                DriverFrameOut(
                    driver=d.driver,
                    team=d.team,
                    position=d.position,
                    gap_to_leader_s=d.gap_to_leader_s,
                    gap_ahead_s=d.gap_ahead_s,
                    compound=d.compound,
                    tyre_life=d.tyre_life,
                    stint=d.stint,
                    pit_this_lap=d.pit_this_lap,
                    sector1_s=d.sector1_s,
                    sector2_s=d.sector2_s,
                    sector3_s=d.sector3_s,
                    undercut_threat=(
                        UndercutThreatOut(
                            gap_s=d.undercut_threat.gap_s,
                            pit_loss_s=d.undercut_threat.pit_loss_s,
                            est_pace_gain_per_lap_s=d.undercut_threat.est_pace_gain_per_lap_s,
                            laps_to_undercut=d.undercut_threat.laps_to_undercut,
                            is_threat=d.undercut_threat.is_threat,
                        )
                        if d.undercut_threat is not None
                        else None
                    ),
                )
                for d in lap.drivers
            ],
        )
        for lap in lap_frames
    ]
    return ReplayOut(total_laps=ctx.total_race_laps, frames=frames)


@router.get("/replay/telemetry", response_model=DriverTelemetryOut)
def get_replay_telemetry(year: int, event: str, driver: str, lap: int) -> DriverTelemetryOut:
    try:
        telemetry = get_driver_telemetry(year, event, driver)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Could not load telemetry for {driver} in {year} {event}: {exc}",
        ) from exc

    lap_telemetry = telemetry[telemetry["lap_number"] == lap]
    if lap_telemetry.empty:
        raise HTTPException(
            status_code=404, detail=f"No telemetry for {driver} on lap {lap} of {year} {event}"
        )

    lap_telemetry = lap_telemetry.sort_values("time_s")
    start_distance = lap_telemetry["distance_m"].min()
    start_time = lap_telemetry["time_s"].min()
    points = [
        TelemetryPointOut(
            time_s=float(row.time_s),
            x=float(row.x),
            y=float(row.y),
            speed_kmh=float(row.speed_kmh),
            distance_m=float(row.distance_m - start_distance),
            lap_time_s=float(row.time_s - start_time),
            throttle_pct=float(row.throttle_pct),
            brake=bool(row.brake),
            gear=int(row.gear),
        )
        for row in lap_telemetry.itertuples()
    ]
    return DriverTelemetryOut(driver=driver, lap_number=lap, points=points)


@router.get("/weather", response_model=WeatherOut)
def get_race_weather(year: int, event: str) -> WeatherOut:
    try:
        ctx = get_race_context(year, event)
        weather = get_weather(year, event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Could not load weather for {year} {event}: {exc}"
        ) from exc

    # Join each weather sample to the nearest lap number by elapsed session
    # time, so the frontend can show "current" conditions at a given replay lap.
    lap_times = (
        ctx.laps.dropna(subset=["lap_end_time_s"])
        .groupby("lap_number")["lap_end_time_s"]
        .min()
        .sort_values()
    )
    weather_sorted = weather.sort_values("time_s")
    lap_lookup = pd.merge_asof(
        weather_sorted,
        lap_times.rename("lap_end_time_s").reset_index(),
        left_on="time_s",
        right_on="lap_end_time_s",
        direction="forward",
    )

    samples = [
        WeatherSampleOut(
            time_s=float(row.time_s),
            lap_number=(None if pd.isna(row.lap_number) else int(row.lap_number)),
            air_temp_c=float(row.air_temp_c),
            track_temp_c=float(row.track_temp_c),
            humidity_pct=float(row.humidity_pct),
            rainfall=bool(row.rainfall),
            wind_speed_kmh=float(row.wind_speed_kmh),
            wind_direction_deg=float(row.wind_direction_deg),
        )
        for row in lap_lookup.itertuples()
    ]
    return WeatherOut(samples=samples)
