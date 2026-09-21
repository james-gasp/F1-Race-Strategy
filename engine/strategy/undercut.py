"""Undercut/overcut threat estimation.

An "undercut" is when a driver pits before the car ahead, bolts on fresh
tires, and uses their pace advantage on out-laps to jump ahead once the car
ahead eventually pits too. Whether it's a live threat comes down to a simple
race: can the chasing car's fresh-tire pace advantage close the current gap
faster than the pit-loss time it costs to stop?

MVP simplification (deliberate, matching `engine/strategy/field.py`'s MVP
note): this assumes both cars keep lapping at their *current* tyre-age pace
trend and ignores traffic, fuel-load differences, and the car ahead's own
future stop — it's a same-lap "is the gap inside the pit-loss window and
closing" signal, not a full race simulation.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel


@dataclass(frozen=True)
class UndercutThreat:
    gap_s: float
    pit_loss_s: float
    est_pace_gain_per_lap_s: float
    laps_to_undercut: float | None
    is_threat: bool


def undercut_threat(
    *,
    gap_s: float,
    compound: str,
    tyre_life_behind: float,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
) -> UndercutThreat:
    """Estimate whether the chasing car (with `gap_s` to the car ahead) is in
    an undercut window, given its current tire's degradation-driven pace loss.

    `est_pace_gain_per_lap_s` is how much lap time the chasing car would gain
    per lap by switching to a fresh tire right now (degradation cost of its
    current tyre age minus the near-zero cost of a fresh one). If that pace
    gain can close `gap_s` within a `pit_loss_model.pit_loss_s` in a small
    number of laps, the undercut is live.
    """
    linear = pace_model.deg_linear.get(compound, 0.0)
    quad = pace_model.deg_quad.get(compound, 0.0)
    current_deg_cost = linear * tyre_life_behind + quad * tyre_life_behind**2
    est_pace_gain_per_lap_s = max(0.0, current_deg_cost)

    if est_pace_gain_per_lap_s <= 0:
        laps_to_undercut = None
    else:
        laps_to_undercut = pit_loss_model.pit_loss_s / est_pace_gain_per_lap_s

    is_threat = (
        gap_s < pit_loss_model.pit_loss_s
        and laps_to_undercut is not None
        and laps_to_undercut <= 3
    )

    return UndercutThreat(
        gap_s=gap_s,
        pit_loss_s=pit_loss_model.pit_loss_s,
        est_pace_gain_per_lap_s=est_pace_gain_per_lap_s,
        laps_to_undercut=laps_to_undercut,
        is_threat=is_threat,
    )
