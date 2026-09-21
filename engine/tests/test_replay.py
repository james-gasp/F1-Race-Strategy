from __future__ import annotations

import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.replay import build_lap_frames


def _pace_model():
    return PaceModel(
        intercept=90.0,
        reference_driver="HAM",
        reference_compound="MEDIUM",
        driver_offset={"HAM": 0.0, "VER": -0.5},
        compound_offset={"MEDIUM": 0.0},
        fuel_effect_per_lap=-0.05,
        deg_linear={"MEDIUM": 0.1},
        deg_quad={"MEDIUM": 0.0},
        residual_std=0.3,
        n_laps_fit=100,
        compounds=("MEDIUM",),
    )


def _pit_loss():
    return PitLossModel(pit_loss_s=20.0, pit_loss_std=1.0, n_stops_observed=5, per_stop_losses=())


def _laps():
    return pd.DataFrame(
        [
            {
                "driver": "VER",
                "team": "Red Bull",
                "lap_number": 1,
                "lap_time_s": 90.0,
                "compound": "MEDIUM",
                "tyre_life": 1.0,
                "stint": 1,
                "is_pit_lap": False,
                "position": 1,
                "sector1_s": 30.0,
                "sector2_s": 30.0,
                "sector3_s": 30.0,
                "lap_end_time_s": 90.0,
            },
            {
                "driver": "HAM",
                "team": "Mercedes",
                "lap_number": 1,
                "lap_time_s": 92.0,
                "compound": "MEDIUM",
                "tyre_life": 10.0,
                "stint": 1,
                "is_pit_lap": False,
                "position": 2,
                "sector1_s": 30.5,
                "sector2_s": 30.5,
                "sector3_s": 31.0,
                "lap_end_time_s": 92.0,
            },
        ]
    )


def test_build_lap_frames_orders_by_position_and_computes_gaps():
    frames = build_lap_frames(_laps(), _pace_model(), _pit_loss())
    assert len(frames) == 1
    frame = frames[0]
    assert frame.lap_number == 1
    assert [d.driver for d in frame.drivers] == ["VER", "HAM"]

    leader, chaser = frame.drivers
    assert leader.gap_to_leader_s == 0.0
    assert leader.gap_ahead_s is None
    assert chaser.gap_to_leader_s == 2.0
    assert chaser.gap_ahead_s == 2.0


def test_build_lap_frames_flags_undercut_threat_for_worn_tyres():
    frames = build_lap_frames(_laps(), _pace_model(), _pit_loss())
    chaser = frames[0].drivers[1]
    assert chaser.undercut_threat is not None
    assert chaser.undercut_threat.gap_s == 2.0
