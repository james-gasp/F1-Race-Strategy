"""Shared, cached access to a race's fitted models.

Fitting the pace and pit-loss models involves a FastF1 fetch (cached on disk
by FastF1 itself) plus an OLS fit — cheap once done, but wasteful to redo on
every request. `get_race_context` memoizes the fitted `RaceContext` per
(year, event) in-process, so repeated API calls for the same race are fast.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from engine.data.loader import RaceIdentifier, clean_pace_laps, load_race_laps, load_race_results
from engine.models.pace import PaceModel, fit_pace_model
from engine.models.pitloss import PitLossModel, fit_pit_loss_model


@dataclass(frozen=True)
class RaceContext:
    race: RaceIdentifier
    laps: pd.DataFrame
    results: pd.DataFrame
    pace_model: PaceModel
    pit_loss_model: PitLossModel

    @property
    def total_race_laps(self) -> int:
        return int(self.laps["lap_number"].max())


@lru_cache(maxsize=16)
def get_race_context(year: int, event: str) -> RaceContext:
    race = RaceIdentifier(year=year, event=event)
    laps = load_race_laps(race)
    results = load_race_results(race)
    pace_model = fit_pace_model(clean_pace_laps(laps))
    pit_loss_model = fit_pit_loss_model(laps, pace_model)
    return RaceContext(
        race=race, laps=laps, results=results, pace_model=pace_model, pit_loss_model=pit_loss_model
    )
