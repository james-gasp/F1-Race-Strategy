"""Whole-field Monte Carlo simulation: turns per-driver strategy simulations into
finishing-position probability distributions.

MVP simplification (deliberate, not an oversight): finishing order on each
simulated draw is determined purely by total race time — there's no explicit
traffic/overtaking-difficulty model. This is the standard first-pass approach
for strategy simulation (it's equivalent to assuming a driver can always
convert a pace/time advantage into track position) and is what makes the
"probability of finishing position" output meaningful without needing full
lap-by-lap gap tracking. A probabilistic overtake-difficulty adjustment is a
natural later extension, not required for this to be a legitimate field model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.simulate import Stint, Strategy, monte_carlo_strategy


@dataclass(frozen=True)
class Competitor:
    driver: str
    team: str
    grid_position: int
    strategy: Strategy


def extract_historical_strategies(laps: pd.DataFrame) -> dict[str, Strategy]:
    """Reconstruct each driver's actual stint sequence (compound + lap count) as
    a Strategy, from a full `load_race_laps` DataFrame (not pre-filtered)."""
    stints = (
        laps.dropna(subset=["stint", "compound"])
        .groupby(["driver", "stint"])
        .agg(compound=("compound", "first"), n_laps=("lap_number", "count"))
        .reset_index()
        .sort_values(["driver", "stint"])
    )

    strategies: dict[str, Strategy] = {}
    for driver, group in stints.groupby("driver"):
        stint_objs = tuple(
            Stint(compound=row.compound, laps=int(row.n_laps)) for row in group.itertuples()
        )
        if stint_objs:
            strategies[driver] = Strategy(
                name=f"{driver}-historical", driver=driver, stints=stint_objs
            )
    return strategies


def build_field_from_history(laps: pd.DataFrame, results: pd.DataFrame) -> list[Competitor]:
    """Build the field's competitors using each driver's actual historical
    strategy and grid position, from `load_race_laps` / `load_race_results` output.

    Only drivers with `status == "Finished"` are included. This model doesn't
    simulate mechanical failures or accidents, so a retiree's partial stint
    data (fewer laps than a full race distance) isn't a comparable strategy —
    including it would make "5 laps before retiring" look like the fastest
    strategy on the grid purely because it took less total time.
    """
    strategies = extract_historical_strategies(laps)
    finishers = results[results["status"] == "Finished"]
    competitors = []
    for row in finishers.itertuples():
        strategy = strategies.get(row.driver)
        if strategy is None:
            continue  # e.g. driver with no recorded stint data
        competitors.append(
            Competitor(
                driver=row.driver,
                team=row.team,
                grid_position=int(row.grid_position),
                strategy=strategy,
            )
        )
    return sorted(competitors, key=lambda c: c.grid_position)


def simulate_field(
    competitors: list[Competitor],
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
    n_sims: int = 2000,
    seed: int | None = None,
) -> pd.DataFrame:
    """Simulate every competitor's strategy `n_sims` times and return a finishing
    position probability table: rows = driver, columns = position (1..N).
    """
    n = len(competitors)
    if n == 0:
        raise ValueError("competitors must be non-empty")

    times_matrix = np.zeros((n, n_sims))
    for i, comp in enumerate(competitors):
        comp_seed = None if seed is None else seed + i
        times_matrix[i] = monte_carlo_strategy(
            comp.strategy, pace_model, pit_loss_model, n_sims=n_sims, seed=comp_seed
        )

    # ranks[i, j] = finishing position (1 = fastest) of competitor i on draw j
    ranks = times_matrix.argsort(axis=0).argsort(axis=0) + 1

    position_counts = np.zeros((n, n), dtype=float)
    for i in range(n):
        position_counts[i] = np.bincount(ranks[i].astype(int) - 1, minlength=n)

    probs = position_counts / n_sims
    return pd.DataFrame(
        probs, index=[c.driver for c in competitors], columns=range(1, n + 1)
    )


def summarize_field_result(position_probs: pd.DataFrame) -> pd.DataFrame:
    """Convenience summary: expected finishing position, P(win), P(podium)."""
    positions = position_probs.columns.to_numpy()
    expected_position = (position_probs.to_numpy() * positions).sum(axis=1)
    p_win = position_probs[1] if 1 in position_probs.columns else 0.0
    podium_cols = [c for c in position_probs.columns if c <= 3]
    p_podium = position_probs[podium_cols].sum(axis=1)
    return pd.DataFrame(
        {
            "driver": position_probs.index,
            "expected_position": expected_position,
            "prob_win": p_win.to_numpy() if hasattr(p_win, "to_numpy") else p_win,
            "prob_podium": p_podium.to_numpy(),
        }
    ).sort_values("expected_position").reset_index(drop=True)
