from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.context import get_race_context
from api.schemas.race import DriverStintOut, DriverSummaryOut, PaceModelSummaryOut, RaceSummaryOut
from engine.strategy.field import extract_historical_strategies

router = APIRouter(prefix="/races", tags=["races"])


@router.get("/{year}/{event}", response_model=RaceSummaryOut)
def get_race(year: int, event: str) -> RaceSummaryOut:
    try:
        ctx = get_race_context(year, event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Could not load race {year} {event}: {exc}"
        ) from exc

    historical_strategies = extract_historical_strategies(ctx.laps)
    drivers = []
    for row in ctx.results.itertuples():
        strategy = historical_strategies.get(row.driver)
        stints = (
            [DriverStintOut(compound=s.compound, laps=s.laps) for s in strategy.stints]
            if strategy
            else []
        )
        drivers.append(
            DriverSummaryOut(
                driver=row.driver,
                team=row.team,
                grid_position=int(row.grid_position),
                finish_position=(
                    None if pd.isna(row.finish_position) else float(row.finish_position)
                ),
                status=row.status,
                historical_strategy=stints,
            )
        )

    pace = ctx.pace_model
    return RaceSummaryOut(
        year=year,
        event=event,
        total_race_laps=ctx.total_race_laps,
        pit_loss_s=ctx.pit_loss_model.pit_loss_s,
        pace_model=PaceModelSummaryOut(
            reference_driver=pace.reference_driver,
            reference_compound=pace.reference_compound,
            fuel_effect_per_lap=pace.fuel_effect_per_lap,
            compound_offset=pace.compound_offset,
            deg_linear=pace.deg_linear,
            deg_quad=pace.deg_quad,
            residual_std=pace.residual_std,
        ),
        drivers=drivers,
    )
