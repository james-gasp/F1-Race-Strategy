from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException

from api.context import RaceContext, get_race_context
from api.schemas.common import StintIn
from api.schemas.strategy import (
    CompareRequest,
    CompareResponse,
    DriverPositionProbabilityOut,
    FieldRequest,
    FieldResponse,
    OptimizeRequest,
    OptimizeResponse,
    SimulateRequest,
    SimulationSummaryOut,
    StrategyResultOut,
)
from engine.optimize.optimizer import RaceState, optimize_pit_stop
from engine.strategy.field import build_field_from_history, simulate_field, summarize_field_result
from engine.strategy.simulate import Stint, Strategy, compare_strategies, monte_carlo_strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


def _to_stints(stints_in: list[StintIn]) -> tuple[Stint, ...]:
    return tuple(
        Stint(compound=s.compound, laps=s.laps, start_tyre_life=s.start_tyre_life)
        for s in stints_in
    )


def _load_context(year: int, event: str) -> RaceContext:
    try:
        return get_race_context(year, event)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Could not load race {year} {event}: {exc}"
        ) from exc


@router.post("/simulate", response_model=SimulationSummaryOut)
def simulate(req: SimulateRequest) -> SimulationSummaryOut:
    ctx = _load_context(req.year, req.event)
    strategy = Strategy(name="simulate", driver=req.driver, stints=_to_stints(req.stints))
    times = monte_carlo_strategy(
        strategy,
        ctx.pace_model,
        ctx.pit_loss_model,
        n_sims=req.n_sims,
        seed=req.seed,
        start_lap_number=req.start_lap_number,
    )
    return SimulationSummaryOut(
        mean_s=float(np.mean(times)),
        median_s=float(np.median(times)),
        std_s=float(np.std(times)),
        p10_s=float(np.percentile(times, 10)),
        p90_s=float(np.percentile(times, 90)),
        n_sims=req.n_sims,
    )


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    ctx = _load_context(req.year, req.event)
    strategies = [
        Strategy(name=s.name, driver=s.driver, stints=_to_stints(s.stints)) for s in req.strategies
    ]
    df = compare_strategies(
        strategies,
        ctx.pace_model,
        ctx.pit_loss_model,
        n_sims=req.n_sims,
        seed=req.seed,
        start_lap_number=req.start_lap_number,
    )
    return CompareResponse(results=[StrategyResultOut(**row) for row in df.to_dict("records")])


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    ctx = _load_context(req.year, req.event)
    total_laps = req.total_race_laps or ctx.total_race_laps
    try:
        state = RaceState(
            driver=req.driver,
            current_compound=req.current_compound,
            current_tyre_life=req.current_tyre_life,
            next_lap_number=req.next_lap_number,
            total_race_laps=total_laps,
            compounds_used_so_far=frozenset(req.compounds_used_so_far),
            enforce_two_compound_rule=req.enforce_two_compound_rule,
        )
        df = optimize_pit_stop(
            state,
            ctx.pace_model,
            ctx.pit_loss_model,
            lap_step=req.lap_step,
            n_sims=req.n_sims,
            seed=req.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results = [StrategyResultOut(**row) for row in df.to_dict("records")]
    return OptimizeResponse(recommended=results[0], candidates=results)


@router.post("/field", response_model=FieldResponse)
def field(req: FieldRequest) -> FieldResponse:
    ctx = _load_context(req.year, req.event)
    competitors = build_field_from_history(ctx.laps, ctx.results)
    if not competitors:
        raise HTTPException(
            status_code=400, detail="No finishing drivers with recorded stint data for this race"
        )

    probs = simulate_field(competitors, ctx.pace_model, ctx.pit_loss_model, n_sims=req.n_sims, seed=req.seed)
    summary = summarize_field_result(probs).set_index("driver")

    drivers = [
        DriverPositionProbabilityOut(
            driver=driver,
            expected_position=float(summary.loc[driver, "expected_position"]),
            prob_win=float(summary.loc[driver, "prob_win"]),
            prob_podium=float(summary.loc[driver, "prob_podium"]),
            position_probabilities={
                int(pos): float(probs.loc[driver, pos]) for pos in probs.columns
            },
        )
        for driver in probs.index
    ]
    drivers.sort(key=lambda d: d.expected_position)
    return FieldResponse(drivers=drivers)
