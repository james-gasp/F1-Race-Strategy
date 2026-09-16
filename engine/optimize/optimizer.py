"""Strategy optimizer: given the current race state for one driver, search
over candidate pit-lap + compound choices for the rest of the race and rank
them by expected remaining race time.

This is the MVP version of "should I pit now, and on what tire" — the core
question a race strategist answers live. It reuses the same Monte Carlo
machinery as `engine.strategy.simulate`, just seeded from mid-race state
(current lap, current tire age) instead of a fresh green flag.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.simulate import Stint, Strategy, compare_strategies


@dataclass(frozen=True)
class RaceState:
    driver: str
    current_compound: str
    current_tyre_life: int
    """Laps already run on the current tire set (the tire age right now)."""
    next_lap_number: int
    """The next lap about to be driven, i.e. laps completed so far + 1."""
    total_race_laps: int

    def __post_init__(self):
        if self.next_lap_number > self.total_race_laps:
            raise ValueError("next_lap_number is beyond the race distance")
        if self.current_tyre_life <= 0:
            raise ValueError("current_tyre_life must be positive")


def build_candidate_strategy(
    name: str, state: RaceState, pit_after_lap: int, next_compound: str
) -> Strategy:
    """Build the remaining-race Strategy for "finish the current stint through
    `pit_after_lap`, then (if any race remains) switch to `next_compound`"."""
    if pit_after_lap < state.next_lap_number or pit_after_lap > state.total_race_laps:
        raise ValueError(
            f"pit_after_lap ({pit_after_lap}) must be within "
            f"[{state.next_lap_number}, {state.total_race_laps}]"
        )

    stint1_laps = pit_after_lap - state.next_lap_number + 1
    stints = [
        Stint(state.current_compound, stint1_laps, start_tyre_life=state.current_tyre_life)
    ]
    if pit_after_lap < state.total_race_laps:
        stint2_laps = state.total_race_laps - pit_after_lap
        stints.append(Stint(next_compound, stint2_laps, start_tyre_life=1))

    return Strategy(name=name, driver=state.driver, stints=tuple(stints))


def generate_pit_candidates(
    state: RaceState,
    compounds: list[str] | None = None,
    lap_step: int = 1,
    min_stint_laps: int = 1,
) -> list[Strategy]:
    """Generate one candidate Strategy per (pit lap, next compound) combination,
    plus a "stay out to the end" candidate.

    `lap_step` coarsens the search grid (e.g. 3 = only consider pitting every
    3rd lap) to keep the number of Monte Carlo runs manageable.
    """
    all_compounds = compounds or ["SOFT", "MEDIUM", "HARD"]
    other_compounds = [c for c in all_compounds if c != state.current_compound] or all_compounds

    candidates: list[Strategy] = []

    # "Stay out" — no further stop this race.
    candidates.append(
        build_candidate_strategy(
            f"stay out on {state.current_compound}",
            state,
            pit_after_lap=state.total_race_laps,
            next_compound=state.current_compound,
        )
    )

    earliest_pit = state.next_lap_number + min_stint_laps - 1
    latest_pit = state.total_race_laps - 1  # must leave at least 1 lap on the new tire
    for pit_after_lap in range(earliest_pit, latest_pit + 1, lap_step):
        for compound in other_compounds:
            name = f"pit@{pit_after_lap}->{compound}"
            candidates.append(build_candidate_strategy(name, state, pit_after_lap, compound))

    return candidates


def optimize_pit_stop(
    state: RaceState,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    compounds: list[str] | None = None,
    lap_step: int = 1,
    n_sims: int = 1000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Rank every candidate pit lap + compound choice by expected remaining race
    time. Row 0 of the result is the recommended strategy.
    """
    candidates = generate_pit_candidates(state, compounds=compounds, lap_step=lap_step)
    return compare_strategies(
        candidates,
        pace_model,
        pit_loss_model,
        n_sims=n_sims,
        seed=seed,
        start_lap_number=state.next_lap_number,
    )
