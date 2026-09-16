"""Unit tests for engine.strategy.field — synthetic data, no network required."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.field import (
    Competitor,
    build_field_from_history,
    extract_historical_strategies,
    simulate_field,
    summarize_field_result,
)
from engine.strategy.simulate import Stint, Strategy

MODEL = PaceModel(
    intercept=90.0,
    reference_driver="A",
    reference_compound="MEDIUM",
    driver_offset={"A": 0.0, "B": 1.0, "C": 5.0},  # C is much slower
    compound_offset={"MEDIUM": 0.0, "SOFT": -0.4, "HARD": 0.3},
    fuel_effect_per_lap=-0.05,
    deg_linear={"MEDIUM": 0.02, "SOFT": 0.06, "HARD": 0.01},
    deg_quad={"MEDIUM": 0.0003, "SOFT": 0.0008, "HARD": 0.0001},
    residual_std=0.2,
    n_laps_fit=300,
    compounds=("MEDIUM", "SOFT", "HARD"),
)
PIT = PitLossModel(pit_loss_s=20.0, pit_loss_std=1.0, n_stops_observed=10, per_stop_losses=())


def _make_synthetic_race_laps() -> pd.DataFrame:
    rows = []
    for driver, n_stints, compound in [("A", 2, "MEDIUM"), ("B", 2, "MEDIUM"), ("C", 1, "HARD")]:
        for stint in range(1, n_stints + 1):
            for lap in range(1, 11):
                rows.append(
                    {"driver": driver, "stint": stint, "compound": compound, "lap_number": lap}
                )
    return pd.DataFrame(rows)


def test_extract_historical_strategies_recovers_stint_structure():
    laps = _make_synthetic_race_laps()
    strategies = extract_historical_strategies(laps)
    assert set(strategies) == {"A", "B", "C"}
    assert strategies["A"].n_stops == 1  # 2 stints -> 1 stop
    assert strategies["A"].total_laps == 20
    assert strategies["C"].n_stops == 0  # 1 stint -> no stop
    assert strategies["C"].total_laps == 10


def test_build_field_from_history_sorts_by_grid_position():
    laps = _make_synthetic_race_laps()
    results = pd.DataFrame(
        [
            {"driver": "C", "team": "T3", "grid_position": 3, "status": "Finished"},
            {"driver": "A", "team": "T1", "grid_position": 1, "status": "Finished"},
            {"driver": "B", "team": "T2", "grid_position": 2, "status": "Finished"},
        ]
    )
    field = build_field_from_history(laps, results)
    assert [c.driver for c in field] == ["A", "B", "C"]


def test_simulate_field_slower_driver_rarely_wins():
    fast_strategy = Strategy(name="s", driver="A", stints=(Stint("MEDIUM", 20),))
    mid_strategy = Strategy(name="s", driver="B", stints=(Stint("MEDIUM", 20),))
    slow_strategy = Strategy(name="s", driver="C", stints=(Stint("HARD", 20),))
    competitors = [
        Competitor(driver="A", team="T1", grid_position=1, strategy=fast_strategy),
        Competitor(driver="B", team="T2", grid_position=2, strategy=mid_strategy),
        Competitor(driver="C", team="T3", grid_position=3, strategy=slow_strategy),
    ]
    probs = simulate_field(competitors, MODEL, PIT, n_sims=3000, seed=0)

    assert list(probs.columns) == [1, 2, 3]
    # every driver's row sums to 1 (they finish in exactly one position per draw)
    assert np.allclose(probs.sum(axis=1), 1.0)
    # A (fastest, no driver offset) should win far more often than C (5s/lap slower)
    assert probs.loc["A", 1] > probs.loc["C", 1]
    assert probs.loc["C", 3] > probs.loc["A", 3]


def test_summarize_field_result_ranks_by_expected_position():
    fast_strategy = Strategy(name="s", driver="A", stints=(Stint("MEDIUM", 20),))
    slow_strategy = Strategy(name="s", driver="C", stints=(Stint("HARD", 20),))
    competitors = [
        Competitor(driver="A", team="T1", grid_position=1, strategy=fast_strategy),
        Competitor(driver="C", team="T3", grid_position=2, strategy=slow_strategy),
    ]
    probs = simulate_field(competitors, MODEL, PIT, n_sims=2000, seed=1)
    summary = summarize_field_result(probs)
    assert summary.iloc[0]["driver"] == "A"
    assert summary.iloc[0]["expected_position"] < summary.iloc[1]["expected_position"]
    assert summary.iloc[0]["prob_win"] > summary.iloc[1]["prob_win"]


def test_simulate_field_rejects_empty_competitors():
    with pytest.raises(ValueError):
        simulate_field([], MODEL, PIT, n_sims=10)


def test_build_field_from_history_excludes_dnfs():
    laps = _make_synthetic_race_laps()
    results = pd.DataFrame(
        [
            {"driver": "A", "team": "T1", "grid_position": 1, "status": "Finished"},
            {"driver": "B", "team": "T2", "grid_position": 2, "status": "Finished"},
            {"driver": "C", "team": "T3", "grid_position": 3, "status": "Retired"},
        ]
    )
    field = build_field_from_history(laps, results)
    assert [c.driver for c in field] == ["A", "B"]
