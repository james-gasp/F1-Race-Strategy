"""Unit tests for engine.optimize.optimizer — synthetic models, no network required."""

from __future__ import annotations

import pytest

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.optimize.optimizer import (
    RaceState,
    build_candidate_strategy,
    generate_pit_candidates,
    optimize_pit_stop,
)

# HARD barely degrades; SOFT degrades fast. A driver deep into a SOFT stint
# with many laps left should clearly prefer pitting onto HARD soon.
MODEL = PaceModel(
    intercept=90.0,
    reference_driver="HAM",
    reference_compound="MEDIUM",
    driver_offset={"HAM": 0.0},
    compound_offset={"MEDIUM": 0.0, "SOFT": -1.0, "HARD": 0.5},
    fuel_effect_per_lap=-0.04,
    deg_linear={"MEDIUM": 0.03, "SOFT": 0.15, "HARD": 0.01},
    deg_quad={"MEDIUM": 0.0005, "SOFT": 0.002, "HARD": 0.0001},
    residual_std=0.1,
    n_laps_fit=300,
    compounds=("MEDIUM", "SOFT", "HARD"),
)
PIT = PitLossModel(pit_loss_s=20.0, pit_loss_std=0.5, n_stops_observed=10, per_stop_losses=())


def test_race_state_rejects_lap_beyond_race_distance():
    with pytest.raises(ValueError):
        RaceState(
            driver="HAM",
            current_compound="SOFT",
            current_tyre_life=5,
            next_lap_number=60,
            total_race_laps=50,
        )


def test_build_candidate_strategy_no_stop_has_one_stint():
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=10,
        next_lap_number=20,
        total_race_laps=50,
    )
    strategy = build_candidate_strategy("stay", state, pit_after_lap=50, next_compound="HARD")
    assert len(strategy.stints) == 1
    assert strategy.stints[0].laps == 31  # laps 20..50 inclusive
    assert strategy.stints[0].start_tyre_life == 10


def test_build_candidate_strategy_with_stop_has_two_stints():
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=10,
        next_lap_number=20,
        total_race_laps=50,
    )
    strategy = build_candidate_strategy("pit@30", state, pit_after_lap=30, next_compound="HARD")
    assert len(strategy.stints) == 2
    assert strategy.stints[0].laps == 11  # laps 20..30 inclusive
    assert strategy.stints[0].start_tyre_life == 10
    assert strategy.stints[1].laps == 20  # laps 31..50
    assert strategy.stints[1].start_tyre_life == 1
    assert strategy.stints[1].compound == "HARD"


def test_generate_pit_candidates_includes_stay_out_option():
    # Already pitted once earlier in the race (onto SOFT), now on MEDIUM --
    # two compounds used, so "stay out" the rest of the way is legal.
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=5,
        next_lap_number=10,
        total_race_laps=30,
        compounds_used_so_far=frozenset({"SOFT"}),
    )
    candidates = generate_pit_candidates(state, lap_step=5)
    names = [c.name for c in candidates]
    assert any("stay out" in n for n in names)
    assert all(c.total_laps == 21 for c in candidates)  # laps 10..30 inclusive, every candidate


def test_optimizer_recommends_pitting_off_worn_soft_tires():
    # Deep into a long SOFT stint with plenty of race left: pitting onto HARD
    # should clearly beat staying out on badly degraded SOFTs.
    state = RaceState(
        driver="HAM",
        current_compound="SOFT",
        current_tyre_life=25,
        next_lap_number=26,
        total_race_laps=50,
    )
    result = optimize_pit_stop(state, MODEL, PIT, lap_step=4, n_sims=500, seed=0)
    best = result.iloc[0]
    assert best["n_stops"] == 1
    assert "stay out" not in best["strategy"]


def test_optimizer_recommends_staying_out_near_end_of_race():
    # Already used HARD earlier in the race, now on MEDIUM with only a
    # handful of laps left: two compounds already used (rule satisfied), and
    # any further stop costs far more than it could save this late.
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=15,
        next_lap_number=48,
        total_race_laps=50,
        compounds_used_so_far=frozenset({"HARD"}),
    )
    result = optimize_pit_stop(state, MODEL, PIT, lap_step=1, n_sims=500, seed=0)
    best = result.iloc[0]
    assert "stay out" in best["strategy"]


def test_two_compound_rule_forces_a_stop_even_late_in_the_race():
    # Only used MEDIUM all race so far, 5 laps left: "stay out" would violate
    # the two-compound rule, so the optimizer must recommend a (late, cheap
    # as possible) stop instead, even though it costs time.
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=40,
        next_lap_number=46,
        total_race_laps=50,
    )
    result = optimize_pit_stop(state, MODEL, PIT, lap_step=1, n_sims=500, seed=0)
    assert "stay out" not in result.iloc[0]["strategy"]
    assert all("stay out" not in name for name in result["strategy"])


def test_two_compound_rule_can_be_disabled():
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=40,
        next_lap_number=46,
        total_race_laps=50,
        enforce_two_compound_rule=False,
    )
    candidates = generate_pit_candidates(state, lap_step=1)
    assert any("stay out" in c.name for c in candidates)


def test_no_legal_candidates_raises_clear_error():
    # Only 1 lap left in the race, only ever used SOFT, and no time left to
    # both pit and complete a lap on a second compound: genuinely impossible
    # to comply with the two-compound rule from here (a real team would have
    # needed to pit earlier).
    state = RaceState(
        driver="HAM",
        current_compound="SOFT",
        current_tyre_life=30,
        next_lap_number=50,
        total_race_laps=50,
    )
    with pytest.raises(ValueError, match="two-compound rule"):
        generate_pit_candidates(state)


def test_compounds_used_so_far_always_includes_current_compound():
    state = RaceState(
        driver="HAM",
        current_compound="MEDIUM",
        current_tyre_life=5,
        next_lap_number=10,
        total_race_laps=30,
    )
    assert state.compounds_used_so_far == frozenset({"MEDIUM"})
