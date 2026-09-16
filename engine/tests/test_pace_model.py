"""Unit tests for engine.models.pace — uses synthetic data with known ground-truth
coefficients so CI never needs network access to FastF1."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pandas as pd
import pytest

from engine.models.pace import fit_pace_model

TRUE_INTERCEPT = 90.0
TRUE_FUEL_EFFECT = -0.06  # seconds per lap, pace improves as fuel burns off
TRUE_DRIVER_OFFSET = {"HAM": 0.0, "VER": -0.3, "NOR": 0.2}
TRUE_COMPOUND_OFFSET = {"MEDIUM": 0.0, "SOFT": -0.4, "HARD": 0.3}
TRUE_DEG_LINEAR = {"MEDIUM": 0.03, "SOFT": 0.08, "HARD": 0.015}
TRUE_DEG_QUAD = {"MEDIUM": 0.0005, "SOFT": 0.001, "HARD": 0.0002}


def _make_synthetic_laps(noise_std: float = 0.0, seed: int = 0, n_stints: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for driver, d_off in TRUE_DRIVER_OFFSET.items():
        lap_number = 1
        for stint in range(n_stints):
            compound = list(TRUE_COMPOUND_OFFSET.keys())[stint % 3]
            stint_len = 12
            for tyre_life in range(1, stint_len + 1):
                lap_time = (
                    TRUE_INTERCEPT
                    + d_off
                    + TRUE_COMPOUND_OFFSET[compound]
                    + TRUE_FUEL_EFFECT * lap_number
                    + TRUE_DEG_LINEAR[compound] * tyre_life
                    + TRUE_DEG_QUAD[compound] * tyre_life**2
                    + (rng.normal(0, noise_std) if noise_std else 0.0)
                )
                rows.append(
                    {
                        "driver": driver,
                        "compound": compound,
                        "tyre_life": float(tyre_life),
                        "lap_number": lap_number,
                        "lap_time_s": lap_time,
                    }
                )
                lap_number += 1
    return pd.DataFrame(rows)


def test_fit_recovers_true_coefficients_without_noise():
    laps = _make_synthetic_laps(noise_std=0.0)
    model = fit_pace_model(laps, min_laps=10)

    assert model.intercept == pytest.approx(
        TRUE_INTERCEPT + TRUE_DRIVER_OFFSET[model.reference_driver], abs=1e-6
    )
    for driver, true_off in TRUE_DRIVER_OFFSET.items():
        relative_true = true_off - TRUE_DRIVER_OFFSET[model.reference_driver]
        assert model.driver_offset[driver] == pytest.approx(relative_true, abs=1e-6)

    assert model.fuel_effect_per_lap == pytest.approx(TRUE_FUEL_EFFECT, abs=1e-6)

    for compound, true_lin in TRUE_DEG_LINEAR.items():
        assert model.deg_linear[compound] == pytest.approx(true_lin, abs=1e-6)
    for compound, true_quad in TRUE_DEG_QUAD.items():
        assert model.deg_quad[compound] == pytest.approx(true_quad, abs=1e-6)


def test_fit_is_robust_to_noise():
    laps = _make_synthetic_laps(noise_std=0.3, seed=1)
    model = fit_pace_model(laps, min_laps=10)
    # With noise, the fuel effect (identified from ~150 laps spread across the
    # whole race) should recover tightly.
    assert model.fuel_effect_per_lap == pytest.approx(TRUE_FUEL_EFFECT, abs=0.02)

    # The linear/quadratic split for a single compound is only weakly identified
    # from one noisy 12-lap stint (they're collinear over a narrow tyre_life
    # range), so check the net degradation effect across the stint instead of
    # the individual coefficients.
    true_delta = (
        TRUE_DEG_LINEAR["SOFT"] * 12
        + TRUE_DEG_QUAD["SOFT"] * 12**2
        - (TRUE_DEG_LINEAR["SOFT"] * 1 + TRUE_DEG_QUAD["SOFT"] * 1**2)
    )
    fitted_delta = (
        model.deg_linear["SOFT"] * 12
        + model.deg_quad["SOFT"] * 12**2
        - (model.deg_linear["SOFT"] * 1 + model.deg_quad["SOFT"] * 1**2)
    )
    assert fitted_delta == pytest.approx(true_delta, abs=0.3)
    assert model.residual_std > 0


def test_degradation_is_monotonic_increasing_with_tyre_age():
    laps = _make_synthetic_laps(noise_std=0.0)
    model = fit_pace_model(laps, min_laps=10)
    times = [
        model.predict(driver="HAM", compound="SOFT", tyre_life=t, lap_number=1)
        for t in range(1, 15)
    ]
    assert all(b >= a for a, b in pairwise(times))


def test_more_fuel_burned_means_faster_laps():
    laps = _make_synthetic_laps(noise_std=0.0)
    model = fit_pace_model(laps, min_laps=10)
    early = model.predict(driver="HAM", compound="MEDIUM", tyre_life=1, lap_number=1)
    late = model.predict(driver="HAM", compound="MEDIUM", tyre_life=1, lap_number=40)
    assert late < early


def test_raises_on_too_few_laps():
    laps = _make_synthetic_laps(noise_std=0.0).head(5)
    with pytest.raises(ValueError):
        fit_pace_model(laps, min_laps=10)


def test_sample_adds_noise_around_prediction():
    laps = _make_synthetic_laps(noise_std=0.3, seed=2)
    model = fit_pace_model(laps, min_laps=10)
    rng = np.random.default_rng(42)
    mean = model.predict(driver="VER", compound="HARD", tyre_life=5, lap_number=10)
    samples = [
        model.sample(driver="VER", compound="HARD", tyre_life=5, lap_number=10, rng=rng)
        for _ in range(2000)
    ]
    assert np.mean(samples) == pytest.approx(mean, abs=0.05)
    assert np.std(samples) == pytest.approx(model.residual_std, rel=0.15)
