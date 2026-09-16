"""Loads and cleans race session data from FastF1 into a flat lap-by-lap DataFrame.

This is the only module that talks to FastF1 directly — everything downstream
(models, strategy, optimizer) consumes the plain DataFrame this produces, so it
stays testable without needing network access or a live FastF1 session.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fastf1
import pandas as pd

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / ".fastf1_cache"

_cache_enabled = False


def ensure_cache(cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
    """Enable FastF1's on-disk cache once per process."""
    global _cache_enabled
    if _cache_enabled:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    _cache_enabled = True


@dataclass(frozen=True)
class RaceIdentifier:
    year: int
    event: str  # circuit/event name or round number, anything fastf1.get_session accepts


LAP_COLUMNS = [
    "Driver",
    "Team",
    "LapNumber",
    "LapTime",
    "Compound",
    "TyreLife",
    "FreshTyre",
    "Stint",
    "PitInTime",
    "PitOutTime",
    "TrackStatus",
    "Position",
    "IsAccurate",
]


def load_race_laps(race: RaceIdentifier) -> pd.DataFrame:
    """Load a race session and return a cleaned lap-by-lap DataFrame.

    Output columns (one row per driver-lap):
        driver, team, lap_number, lap_time_s, compound, tyre_life, fresh_tyre,
        stint, is_pit_lap, track_status, position

    `lap_time_s` is a float number of seconds (NaN for in/out laps with no
    recorded time). `is_pit_lap` is True for the lap a driver pitted on.
    """
    ensure_cache()
    session = fastf1.get_session(race.year, race.event, "R")
    session.load(telemetry=False, weather=False, messages=False)

    laps = session.laps[LAP_COLUMNS].copy()

    # Only keep laps FastF1 marked as accurate timing (drops in/out-lap noise,
    # red-flag artifacts, etc.) OR laps that are pit laps, which we want to
    # keep for pit-loss modeling even though their lap time isn't representative pace.
    is_pit_lap = laps["PitInTime"].notna() | laps["PitOutTime"].notna()

    out = pd.DataFrame(
        {
            "driver": laps["Driver"],
            "team": laps["Team"],
            "lap_number": laps["LapNumber"].astype(int),
            "lap_time_s": laps["LapTime"].dt.total_seconds(),
            "compound": laps["Compound"],
            "tyre_life": laps["TyreLife"],
            "fresh_tyre": laps["FreshTyre"],
            "stint": laps["Stint"].astype("Int64"),
            "is_pit_lap": is_pit_lap,
            "is_accurate": laps["IsAccurate"],
            "track_status": laps["TrackStatus"],
            "position": laps["Position"],
        }
    )
    return out.sort_values(["driver", "lap_number"]).reset_index(drop=True)


def load_race_results(race: RaceIdentifier) -> pd.DataFrame:
    """Load starting grid position, finishing position, and status for a race.

    Output columns: driver, team, grid_position, finish_position, status.
    `finish_position` is NaN for retirements (use `status` to check).
    """
    ensure_cache()
    session = fastf1.get_session(race.year, race.event, "R")
    session.load(telemetry=False, weather=False, messages=False)

    results = session.results
    return pd.DataFrame(
        {
            "driver": results["Abbreviation"],
            "team": results["TeamName"],
            "grid_position": results["GridPosition"].astype(int),
            "finish_position": results["Position"],
            "status": results["Status"],
        }
    ).reset_index(drop=True)


def clean_pace_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Filter to laps suitable for fitting a tire degradation / pace model.

    Drops pit laps (in/out laps run at reduced pace) and laps FastF1 flagged
    as inaccurate (safety car, red flag, etc.) or with a missing lap time.
    """
    return laps[
        (~laps["is_pit_lap"]) & laps["is_accurate"] & laps["lap_time_s"].notna()
    ].reset_index(drop=True)


def safety_car_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Return laps run under Safety Car (status '4') or VSC (status '6')."""
    return laps[laps["track_status"].astype(str).str.contains("4|6", regex=True, na=False)]
