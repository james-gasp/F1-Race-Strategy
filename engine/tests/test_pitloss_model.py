"""Unit tests for engine.models.pitloss — synthetic laps with a known injected
pit loss, checked against a hand-built PaceModel so no network access is needed."""

from __future__ import annotations

import pandas as pd
import pytest

from engine.models.pace import PaceModel
from engine.models.pitloss import fit_pit_loss_model

SIMPLE_MODEL = PaceModel(
    intercept=90.0,
    reference_driver="HAM",
    reference_compound="MEDIUM",
    driver_offset={"HAM": 0.0, "VER": -0.2},
    compound_offset={"MEDIUM": 0.0, "SOFT": -0.3},
    fuel_effect_per_lap=-0.05,
    deg_linear={"MEDIUM": 0.03, "SOFT": 0.08},
    deg_quad={"MEDIUM": 0.0005, "SOFT": 0.001},
    residual_std=0.4,
    n_laps_fit=100,
    compounds=("MEDIUM", "SOFT"),
)

TRUE_PIT_LOSS = 22.0


def _make_pit_event_row(driver, lap_number, compound, tyre_life, extra_loss=0.0):
    expected = SIMPLE_MODEL.predict(
        driver=driver, compound=compound, tyre_life=tyre_life, lap_number=lap_number
    )
    return {
        "driver": driver,
        "lap_number": lap_number,
        "compound": compound,
        "tyre_life": tyre_life,
        "lap_time_s": expected + extra_loss,
        "is_pit_lap": True,
    }


def _make_laps_with_pit_stops(losses: list[float]) -> pd.DataFrame:
    rows = []
    for i, loss in enumerate(losses):
        driver = "HAM" if i % 2 == 0 else "VER"
        base_lap = 20 + i * 5
        # split the injected loss across in-lap and out-lap
        rows.append(_make_pit_event_row(driver, base_lap, "MEDIUM", 15.0, extra_loss=loss * 0.6))
        rows.append(_make_pit_event_row(driver, base_lap + 1, "SOFT", 1.0, extra_loss=loss * 0.4))
        # a normal, non-pit lap in between events so lookup indexing has non-pit rows too
        rows.append(
            {
                "driver": driver,
                "lap_number": base_lap + 2,
                "compound": "SOFT",
                "tyre_life": 2.0,
                "lap_time_s": SIMPLE_MODEL.predict(
                    driver=driver, compound="SOFT", tyre_life=2.0, lap_number=base_lap + 2
                ),
                "is_pit_lap": False,
            }
        )
    return pd.DataFrame(rows)


def test_recovers_known_pit_loss_exactly_with_no_variance():
    laps = _make_laps_with_pit_stops([TRUE_PIT_LOSS] * 5)
    result = fit_pit_loss_model(laps, SIMPLE_MODEL)
    assert result.pit_loss_s == pytest.approx(TRUE_PIT_LOSS, abs=1e-6)
    assert result.n_stops_observed == 5


def test_median_is_robust_to_one_outlier_stop():
    losses = [20.0, 21.0, 22.0, 23.0, 24.0, 90.0]  # one anomalous long stop (e.g. damage)
    laps = _make_laps_with_pit_stops(losses)
    result = fit_pit_loss_model(laps, SIMPLE_MODEL)
    # median of [20, 21, 22, 23, 24, 90] is the average of the two middle values (22, 23)
    assert result.pit_loss_s == pytest.approx(22.5, abs=1e-6)
    assert result.n_stops_observed == 6


def test_raises_when_no_pit_events_present():
    laps = pd.DataFrame(
        [
            {
                "driver": "HAM",
                "lap_number": 1,
                "compound": "MEDIUM",
                "tyre_life": 1.0,
                "lap_time_s": 91.0,
                "is_pit_lap": False,
            }
        ]
    )
    with pytest.raises(ValueError):
        fit_pit_loss_model(laps, SIMPLE_MODEL)


def test_skips_pit_events_with_missing_lap_time():
    laps = _make_laps_with_pit_stops([TRUE_PIT_LOSS] * 3)
    laps.loc[0, "lap_time_s"] = float("nan")  # corrupt the first event's in-lap
    result = fit_pit_loss_model(laps, SIMPLE_MODEL)
    assert result.n_stops_observed == 2
    assert result.pit_loss_s == pytest.approx(TRUE_PIT_LOSS, abs=1e-6)
