"""Pit lane time-loss model.

A pit stop costs time on two laps: the in-lap (driving into the pits instead
of finishing the lap at racing pace) and the out-lap (pit lane speed limit +
rejoining at reduced pace). Neither lap's raw time is a "pit loss" number by
itself — we isolate the loss by comparing each pit lap's actual time against
what the fitted `PaceModel` would have predicted for a *clean* lap by that
driver, on that compound, at that point in the race, then sum the two deltas
per stop. The track-level pit loss is the median of those per-stop totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import pandas as pd

from engine.models.pace import PaceModel


@dataclass(frozen=True)
class PitLossModel:
    pit_loss_s: float
    n_stops_observed: int
    per_stop_losses: tuple[float, ...]


def _find_pit_events(laps: pd.DataFrame) -> list[tuple[str, int, int]]:
    """Return (driver, in_lap_number, out_lap_number) for each consecutive
    pair of pit-flagged laps for the same driver."""
    events: list[tuple[str, int, int]] = []
    pit_laps = laps[laps["is_pit_lap"]].sort_values(["driver", "lap_number"])
    for driver, group in pit_laps.groupby("driver"):
        lap_numbers = group["lap_number"].tolist()
        for a, b in pairwise(lap_numbers):
            if b == a + 1:
                events.append((driver, a, b))
    return events


def fit_pit_loss_model(laps: pd.DataFrame, pace_model: PaceModel) -> PitLossModel:
    """Estimate pit lane time loss (seconds) from a race's raw laps.

    `laps` should be the full `load_race_laps` output (not pre-filtered to
    pace laps, since pit laps are excluded there by design).
    """
    events = _find_pit_events(laps)
    if not events:
        raise ValueError("No pit stop events (consecutive pit-flagged lap pairs) found")

    lookup = laps.set_index(["driver", "lap_number"])
    per_stop_losses: list[float] = []

    for driver, in_lap, out_lap in events:
        try:
            in_row = lookup.loc[(driver, in_lap)]
            out_row = lookup.loc[(driver, out_lap)]
        except KeyError:
            continue

        actual_total = 0.0
        expected_total = 0.0
        valid = True
        for row, lap_number in ((in_row, in_lap), (out_row, out_lap)):
            lap_time = row["lap_time_s"]
            compound = row["compound"]
            tyre_life = row["tyre_life"]
            if pd.isna(lap_time) or pd.isna(compound) or pd.isna(tyre_life):
                valid = False
                break
            actual_total += float(lap_time)
            expected_total += pace_model.predict(
                driver=driver,
                compound=compound,
                tyre_life=float(tyre_life),
                lap_number=float(lap_number),
            )
        if valid:
            per_stop_losses.append(actual_total - expected_total)

    if not per_stop_losses:
        raise ValueError("Found pit events but none had usable lap times to estimate loss from")

    return PitLossModel(
        pit_loss_s=float(np.median(per_stop_losses)),
        n_stops_observed=len(per_stop_losses),
        per_stop_losses=tuple(per_stop_losses),
    )
