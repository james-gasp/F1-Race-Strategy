"""Strategy optimizer: given the current race state for one driver, search
over candidate pit-lap + compound choices for the rest of the race and rank
them by expected remaining race time.

This is the MVP version of "should I pit now, and on what tire" — the core
question a race strategist answers live. It reuses the same Monte Carlo
machinery as `engine.strategy.simulate`, just seeded from mid-race state
(current lap, current tire age) instead of a fresh green flag.

Regulatory constraint: F1's sporting regulations require every driver to use
at least two different dry-weather tire compounds during a dry race (unless
the race is run, or partly run, under wet conditions — not modeled here).
`RaceState.compounds_used_so_far` tracks what's already been used, and any
candidate that wouldn't satisfy the rule by the end of the race is dropped
before ranking, so the optimizer never recommends an illegal strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.simulate import Stint, Strategy, compare_strategies

DRY_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


@dataclass(frozen=True)
class RaceState:
    driver: str
    current_compound: str
    current_tyre_life: int
    """Laps already run on the current tire set (the tire age right now)."""
    next_lap_number: int
    """The next lap about to be driven, i.e. laps completed so far + 1."""
    total_race_laps: int
    compounds_used_so_far: frozenset[str] = field(default_factory=frozenset)
    """Distinct dry compounds used in stints completed before the current one.
    Does not need to include `current_compound` — that's added automatically.
    """
    enforce_two_compound_rule: bool = True
    """F1's dry-race regulation: at least two distinct compounds must be used
    across the race. Set False to model a wet/mixed race, where it doesn't
    apply, or a rules variant that doesn't require it (e.g. sprint races)."""

    def __post_init__(self):
        if self.next_lap_number > self.total_race_laps:
            raise ValueError("next_lap_number is beyond the race distance")
        if self.current_tyre_life <= 0:
            raise ValueError("current_tyre_life must be positive")
        object.__setattr__(
            self,
            "compounds_used_so_far",
            frozenset(self.compounds_used_so_far) | {self.current_compound},
        )


def compounds_used_before_lap(laps: pd.DataFrame, driver: str, lap_number: int) -> frozenset[str]:
    """Distinct compounds a driver has already used, from a `load_race_laps`
    DataFrame, strictly before `lap_number` — convenient for building a
    `RaceState` from real mid-race data instead of specifying it by hand."""
    prior_laps = laps[(laps["driver"] == driver) & (laps["lap_number"] < lap_number)]
    return frozenset(prior_laps["compound"].dropna().unique())


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


def _satisfies_two_compound_rule(state: RaceState, strategy: Strategy) -> bool:
    if not state.enforce_two_compound_rule:
        return True
    compounds_used = state.compounds_used_so_far | {s.compound for s in strategy.stints}
    return len(compounds_used & set(DRY_COMPOUNDS)) >= 2


def generate_pit_candidates(
    state: RaceState,
    compounds: list[str] | None = None,
    lap_step: int = 1,
    min_stint_laps: int = 1,
) -> list[Strategy]:
    """Generate one candidate Strategy per (pit lap, next compound) combination,
    plus a "stay out to the end" candidate — excluding any candidate that
    would leave the driver having used only one dry compound for the whole
    race, which isn't a legal strategy under F1's regulations.

    `lap_step` coarsens the search grid (e.g. 3 = only consider pitting every
    3rd lap) to keep the number of Monte Carlo runs manageable.
    """
    all_compounds = compounds or list(DRY_COMPOUNDS)
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

    legal_candidates = [c for c in candidates if _satisfies_two_compound_rule(state, c)]
    if not legal_candidates:
        raise ValueError(
            "No candidate strategy satisfies F1's two-compound rule from this race state "
            f"(compounds already used: {sorted(state.compounds_used_so_far)}, "
            f"{state.total_race_laps - state.next_lap_number + 1} laps remaining). "
            "A mandatory pit stop should have happened earlier to leave this possible."
        )
    return legal_candidates


def optimize_pit_stop(
    state: RaceState,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    compounds: list[str] | None = None,
    lap_step: int = 1,
    n_sims: int = 1000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Rank every legal candidate pit lap + compound choice by expected
    remaining race time. Row 0 of the result is the recommended strategy.
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
