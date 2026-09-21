from __future__ import annotations

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.undercut import undercut_threat


def _pace_model(deg_linear: float) -> PaceModel:
    return PaceModel(
        intercept=90.0,
        reference_driver="HAM",
        reference_compound="MEDIUM",
        driver_offset={"HAM": 0.0},
        compound_offset={"MEDIUM": 0.0},
        fuel_effect_per_lap=-0.05,
        deg_linear={"MEDIUM": deg_linear},
        deg_quad={"MEDIUM": 0.0},
        residual_std=0.3,
        n_laps_fit=100,
        compounds=("MEDIUM",),
    )


def _pit_loss(pit_loss_s: float) -> PitLossModel:
    return PitLossModel(pit_loss_s=pit_loss_s, pit_loss_std=1.0, n_stops_observed=10, per_stop_losses=())


def test_undercut_is_a_threat_when_gap_small_and_tyres_worn():
    threat = undercut_threat(
        gap_s=2.0,
        compound="MEDIUM",
        tyre_life_behind=20.0,
        pace_model=_pace_model(deg_linear=0.5),
        pit_loss_model=_pit_loss(pit_loss_s=20.0),
    )
    assert threat.is_threat
    assert threat.laps_to_undercut is not None
    assert threat.laps_to_undercut <= 3


def test_undercut_not_a_threat_when_gap_exceeds_pit_loss():
    threat = undercut_threat(
        gap_s=30.0,
        compound="MEDIUM",
        tyre_life_behind=20.0,
        pace_model=_pace_model(deg_linear=0.1),
        pit_loss_model=_pit_loss(pit_loss_s=20.0),
    )
    assert not threat.is_threat


def test_undercut_not_a_threat_on_fresh_tyres():
    threat = undercut_threat(
        gap_s=2.0,
        compound="MEDIUM",
        tyre_life_behind=1.0,
        pace_model=_pace_model(deg_linear=0.1),
        pit_loss_model=_pit_loss(pit_loss_s=20.0),
    )
    assert threat.laps_to_undercut is None or threat.laps_to_undercut > 3
    assert not threat.is_threat
