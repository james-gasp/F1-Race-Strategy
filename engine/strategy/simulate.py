"""Single-car Monte Carlo race strategy simulation.

A `Strategy` is a sequence of stints (compound + lap count) for one driver.
Simulating it once walks lap-by-lap through each stint, sampling a noisy lap
time from the fitted `PaceModel` and adding a sampled pit stop cost (from
`PitLossModel`) between stints. Running that thousands of times gives a
distribution of total race time, which is what lets us compare strategies
under uncertainty rather than off a single deterministic number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel


@dataclass(frozen=True)
class Stint:
    compound: str
    laps: int

    def __post_init__(self):
        if self.laps <= 0:
            raise ValueError(f"Stint laps must be positive, got {self.laps}")


@dataclass(frozen=True)
class Strategy:
    name: str
    driver: str
    stints: tuple[Stint, ...]

    @property
    def total_laps(self) -> int:
        return sum(s.laps for s in self.stints)

    @property
    def n_stops(self) -> int:
        return max(0, len(self.stints) - 1)


def simulate_strategy_once(
    strategy: Strategy,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    rng: np.random.Generator,
) -> float:
    """Run one stochastic realization of `strategy`, return total race time (s)."""
    total_time = 0.0
    lap_number = 1
    for i, stint in enumerate(strategy.stints):
        for tyre_life in range(1, stint.laps + 1):
            total_time += pace_model.sample(
                driver=strategy.driver,
                compound=stint.compound,
                tyre_life=float(tyre_life),
                lap_number=float(lap_number),
                rng=rng,
            )
            lap_number += 1
        is_last_stint = i == len(strategy.stints) - 1
        if not is_last_stint:
            total_time += pit_loss_model.sample(rng)
    return total_time


def monte_carlo_strategy(
    strategy: Strategy,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    n_sims: int = 2000,
    seed: int | None = None,
) -> np.ndarray:
    """Simulate `strategy` `n_sims` times, return an array of total race times."""
    rng = np.random.default_rng(seed)
    return np.array(
        [
            simulate_strategy_once(strategy, pace_model, pit_loss_model, rng)
            for _ in range(n_sims)
        ]
    )


def compare_strategies(
    strategies: list[Strategy],
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    n_sims: int = 2000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Simulate each strategy and summarize + rank the resulting time distributions.

    Each strategy gets its own reproducible RNG stream (seed offset by index),
    then results are compared per-simulation-index (draw 0 of strategy A vs.
    draw 0 of strategy B, etc.) to compute `prob_fastest` — the fraction of
    paired draws where that strategy was fastest.
    """
    all_times = {}
    for i, strategy in enumerate(strategies):
        strategy_seed = None if seed is None else seed + i
        all_times[strategy.name] = monte_carlo_strategy(
            strategy, pace_model, pit_loss_model, n_sims=n_sims, seed=strategy_seed
        )

    # times_matrix[i, j] = strategy i's total time on simulation draw j.
    names = [s.name for s in strategies]
    times_matrix = np.stack([all_times[name] for name in names])  # (n_strategies, n_sims)
    winner_idx_per_draw = np.argmin(times_matrix, axis=0)  # (n_sims,)

    rows = []
    for i, strategy in enumerate(strategies):
        times = all_times[strategy.name]
        win_prob = float(np.mean(winner_idx_per_draw == i))
        rows.append(
            {
                "strategy": strategy.name,
                "n_stops": strategy.n_stops,
                "total_laps": strategy.total_laps,
                "mean_s": float(np.mean(times)),
                "median_s": float(np.median(times)),
                "std_s": float(np.std(times)),
                "p10_s": float(np.percentile(times, 10)),
                "p90_s": float(np.percentile(times, 90)),
                "prob_fastest": win_prob,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_s").reset_index(drop=True)
