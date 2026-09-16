"""Unit tests for engine.strategy.simulate — uses a hand-built PaceModel/PitLossModel
so results are deterministic and don't require network access."""

from __future__ import annotations

import numpy as np
import pytest

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.simulate import Stint, Strategy, compare_strategies, monte_carlo_strategy

ZERO_NOISE_MODEL = PaceModel(
    intercept=90.0,
    reference_driver="HAM",
    reference_compound="MEDIUM",
    driver_offset={"HAM": 0.0},
    compound_offset={"MEDIUM": 0.0, "SOFT": -0.5, "HARD": 0.5},
    fuel_effect_per_lap=-0.05,
    deg_linear={"MEDIUM": 0.02, "SOFT": 0.06, "HARD": 0.01},
    deg_quad={"MEDIUM": 0.0003, "SOFT": 0.0008, "HARD": 0.0001},
    residual_std=0.0,
    n_laps_fit=500,
    compounds=("MEDIUM", "SOFT", "HARD"),
)
ZERO_NOISE_PIT = PitLossModel(pit_loss_s=22.0, pit_loss_std=0.0, n_stops_observed=10, per_stop_losses=())

NOISY_MODEL = PaceModel(
    **{**ZERO_NOISE_MODEL.__dict__, "residual_std": 0.4},
)
NOISY_PIT = PitLossModel(pit_loss_s=22.0, pit_loss_std=2.0, n_stops_observed=10, per_stop_losses=())


def test_stint_rejects_non_positive_laps():
    with pytest.raises(ValueError):
        Stint(compound="SOFT", laps=0)


def test_zero_noise_simulation_is_deterministic():
    strategy = Strategy(
        name="1-stop",
        driver="HAM",
        stints=(Stint("MEDIUM", 20), Stint("HARD", 20)),
    )
    times = monte_carlo_strategy(strategy, ZERO_NOISE_MODEL, ZERO_NOISE_PIT, n_sims=5, seed=0)
    assert np.allclose(times, times[0])  # no noise anywhere -> every draw identical


def test_total_time_matches_hand_calculation_with_zero_noise():
    strategy = Strategy(name="1-stop", driver="HAM", stints=(Stint("MEDIUM", 3), Stint("HARD", 2)))
    times = monte_carlo_strategy(strategy, ZERO_NOISE_MODEL, ZERO_NOISE_PIT, n_sims=1, seed=0)

    expected = 0.0
    lap_number = 1
    for compound, n_laps in [("MEDIUM", 3), ("HARD", 2)]:
        for tyre_life in range(1, n_laps + 1):
            expected += ZERO_NOISE_MODEL.predict(
                driver="HAM", compound=compound, tyre_life=tyre_life, lap_number=lap_number
            )
            lap_number += 1
    expected += ZERO_NOISE_PIT.pit_loss_s  # one pit stop between the two stints

    assert times[0] == pytest.approx(expected, abs=1e-9)


def test_more_stops_adds_pit_loss_time():
    one_stop = Strategy(name="1-stop", driver="HAM", stints=(Stint("MEDIUM", 20), Stint("HARD", 20)))
    two_stop = Strategy(
        name="2-stop",
        driver="HAM",
        stints=(Stint("SOFT", 13), Stint("SOFT", 13), Stint("HARD", 14)),
    )
    assert one_stop.n_stops == 1
    assert two_stop.n_stops == 2


def test_compare_strategies_ranks_by_mean_and_probabilities_sum_to_one():
    fast = Strategy(name="fast", driver="HAM", stints=(Stint("SOFT", 20), Stint("SOFT", 20)))
    slow = Strategy(name="slow", driver="HAM", stints=(Stint("HARD", 20), Stint("HARD", 20)))

    result = compare_strategies([fast, slow], NOISY_MODEL, NOISY_PIT, n_sims=3000, seed=0)

    assert list(result["strategy"]) == ["fast", "slow"]  # sorted by mean_s ascending
    assert result["prob_fastest"].sum() == pytest.approx(1.0, abs=1e-9)
    assert result.loc[result["strategy"] == "fast", "prob_fastest"].iloc[0] > 0.5


def test_reproducible_with_same_seed():
    strategy = Strategy(name="s", driver="HAM", stints=(Stint("MEDIUM", 10), Stint("HARD", 10)))
    times_a = monte_carlo_strategy(strategy, NOISY_MODEL, NOISY_PIT, n_sims=100, seed=7)
    times_b = monte_carlo_strategy(strategy, NOISY_MODEL, NOISY_PIT, n_sims=100, seed=7)
    assert np.array_equal(times_a, times_b)
