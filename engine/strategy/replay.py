"""Lap-indexed race replay: turns a race's raw laps into a per-lap sequence of
driver state (position, gaps, tire, sector times, undercut threat) that a
frontend can step/scrub through.

Lap-indexed rather than time-indexed deliberately: car telemetry timestamps
aren't synchronized across drivers, while `laps` is already one row per
driver per lap. A "replay" here is nothing more than that table reshaped lap
by lap — which also means a future live-data source could populate the same
shape incrementally (one lap frame at a time) without changing this contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.models.pace import PaceModel
from engine.models.pitloss import PitLossModel
from engine.strategy.undercut import UndercutThreat, undercut_threat


@dataclass(frozen=True)
class DriverFrame:
    driver: str
    team: str
    position: int | None
    gap_to_leader_s: float | None
    gap_ahead_s: float | None
    compound: str | None
    tyre_life: float | None
    stint: int | None
    pit_this_lap: bool
    sector1_s: float | None
    sector2_s: float | None
    sector3_s: float | None
    undercut_threat: UndercutThreat | None


@dataclass(frozen=True)
class LapFrame:
    lap_number: int
    drivers: tuple[DriverFrame, ...]


def _nan_to_none(value):
    return None if pd.isna(value) else value


def build_lap_frames(
    laps: pd.DataFrame,
    pace_model: PaceModel,
    pit_loss_model: PitLossModel,
) -> list[LapFrame]:
    """Build one `LapFrame` per lap number from a full `load_race_laps` DataFrame."""
    frames: list[LapFrame] = []

    for lap_number, lap_rows in laps.groupby("lap_number"):
        by_position = lap_rows.dropna(subset=["position"]).sort_values("position")
        leader_time = by_position["lap_end_time_s"].iloc[0] if not by_position.empty else None

        driver_frames: list[DriverFrame] = []
        prev_row = None
        for row in by_position.itertuples():
            gap_to_leader_s = (
                float(row.lap_end_time_s - leader_time)
                if leader_time is not None and not pd.isna(row.lap_end_time_s)
                else None
            )
            gap_ahead_s = (
                float(row.lap_end_time_s - prev_row.lap_end_time_s)
                if prev_row is not None
                and not pd.isna(row.lap_end_time_s)
                and not pd.isna(prev_row.lap_end_time_s)
                else None
            )

            threat = None
            if (
                gap_ahead_s is not None
                and not pd.isna(row.compound)
                and not pd.isna(row.tyre_life)
            ):
                threat = undercut_threat(
                    gap_s=gap_ahead_s,
                    compound=row.compound,
                    tyre_life_behind=float(row.tyre_life),
                    pace_model=pace_model,
                    pit_loss_model=pit_loss_model,
                )

            driver_frames.append(
                DriverFrame(
                    driver=row.driver,
                    team=row.team,
                    position=int(row.position),
                    gap_to_leader_s=gap_to_leader_s,
                    gap_ahead_s=gap_ahead_s,
                    compound=_nan_to_none(row.compound),
                    tyre_life=_nan_to_none(row.tyre_life),
                    stint=_nan_to_none(row.stint),
                    pit_this_lap=bool(row.is_pit_lap),
                    sector1_s=_nan_to_none(row.sector1_s),
                    sector2_s=_nan_to_none(row.sector2_s),
                    sector3_s=_nan_to_none(row.sector3_s),
                    undercut_threat=threat,
                )
            )
            prev_row = row

        frames.append(LapFrame(lap_number=int(lap_number), drivers=tuple(driver_frames)))

    return sorted(frames, key=lambda f: f.lap_number)
