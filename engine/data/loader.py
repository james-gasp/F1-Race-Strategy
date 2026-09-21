"""Loads and cleans race session data from FastF1 into a flat lap-by-lap DataFrame.

This is the only module that talks to FastF1 directly — everything downstream
(models, strategy, optimizer) consumes the plain DataFrame this produces, so it
stays testable without needing network access or a live FastF1 session.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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


@lru_cache(maxsize=16)
def _load_session(year: int, event: str, *, telemetry: bool = False, weather: bool = False):
    """Fetch + process a race session once per process, shared by
    `load_race_laps` and `load_race_results` so requesting both for the same
    race doesn't re-run FastF1's (CPU-bound) timing data processing twice.

    `telemetry`/`weather` are part of the cache key (via `lru_cache`), so a
    laps-only call and a telemetry call for the same race are cached and kept
    independently — existing callers that only need laps stay on the cheap
    path and don't pay for telemetry they never asked for.
    """
    ensure_cache()
    session = fastf1.get_session(year, event, "R")
    session.load(telemetry=telemetry, weather=weather, messages=False)
    return session


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
    "Sector1Time",
    "Sector2Time",
    "Sector3Time",
    "Time",
]


def load_race_laps(race: RaceIdentifier) -> pd.DataFrame:
    """Load a race session and return a cleaned lap-by-lap DataFrame.

    Output columns (one row per driver-lap):
        driver, team, lap_number, lap_time_s, compound, tyre_life, fresh_tyre,
        stint, is_pit_lap, track_status, position, sector1_s, sector2_s, sector3_s,
        lap_end_time_s

    `lap_time_s` is a float number of seconds (NaN for in/out laps with no
    recorded time). `is_pit_lap` is True for the lap a driver pitted on.
    Sector times come straight off `session.laps` and don't require telemetry.
    `lap_end_time_s` is the cumulative session time (seconds since session
    start) at which the lap was completed — used to compute gaps between
    drivers at the same lap number.
    """
    session = _load_session(race.year, race.event)

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
            "sector1_s": laps["Sector1Time"].dt.total_seconds(),
            "sector2_s": laps["Sector2Time"].dt.total_seconds(),
            "sector3_s": laps["Sector3Time"].dt.total_seconds(),
            "lap_end_time_s": laps["Time"].dt.total_seconds(),
        }
    )
    return out.sort_values(["driver", "lap_number"]).reset_index(drop=True)


def load_weather(race: RaceIdentifier) -> pd.DataFrame:
    """Load weather/track-condition samples for a race session.

    Output columns: time_s (seconds from session start), air_temp_c,
    track_temp_c, humidity_pct, rainfall, wind_speed_kmh, wind_direction_deg.
    """
    session = _load_session(race.year, race.event, weather=True)
    weather = session.weather_data
    return pd.DataFrame(
        {
            "time_s": weather["Time"].dt.total_seconds(),
            "air_temp_c": weather["AirTemp"],
            "track_temp_c": weather["TrackTemp"],
            "humidity_pct": weather["Humidity"],
            "rainfall": weather["Rainfall"],
            "wind_speed_kmh": weather["WindSpeed"],
            "wind_direction_deg": weather["WindDirection"],
        }
    ).reset_index(drop=True)


def _telemetry_for_one_driver(session, driver: str) -> pd.DataFrame:
    """Fetch one driver's whole-session telemetry in a single bulk call
    (`Laps.get_telemetry()`), then tag each sample with its lap number via
    an as-of join against each lap's start time — much faster than calling
    `get_telemetry()` once per lap."""
    drv_laps = session.laps.pick_drivers(driver)
    tel = drv_laps.get_telemetry()
    if tel.empty:
        return pd.DataFrame(
            columns=["driver", "lap_number", "time_s", "x", "y", "speed_kmh", "distance_m"]
        )

    lap_starts = drv_laps[["LapNumber", "LapStartTime"]].dropna().sort_values("LapStartTime")
    tel = tel.sort_values("SessionTime")
    tagged = pd.merge_asof(
        tel,
        lap_starts.rename(columns={"LapStartTime": "SessionTime"}),
        on="SessionTime",
        direction="backward",
    )

    return pd.DataFrame(
        {
            "driver": driver,
            "lap_number": tagged["LapNumber"].astype("Int64"),
            "time_s": tagged["SessionTime"].dt.total_seconds(),
            "x": tagged["X"],
            "y": tagged["Y"],
            "speed_kmh": tagged["Speed"],
            "distance_m": tagged["Distance"],
        }
    ).dropna(subset=["lap_number"]).reset_index(drop=True)


def load_car_telemetry(race: RaceIdentifier, driver: str | None = None) -> pd.DataFrame:
    """Load per-lap car position/speed telemetry.

    `driver=None` loads every driver (expensive — full-session telemetry, one
    bulk fetch per car); pass a driver code (e.g. "VER") to scope the fetch to
    one car, which is all a circuit-outline extraction needs.

    Output columns: driver, lap_number, time_s (session-relative), x, y,
    speed_kmh, distance_m (distance traveled within the lap).
    """
    session = _load_session(race.year, race.event, telemetry=True)
    drivers = [driver] if driver is not None else sorted(session.laps["Driver"].unique())

    frames = [_telemetry_for_one_driver(session, d) for d in drivers]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(
            columns=["driver", "lap_number", "time_s", "x", "y", "speed_kmh", "distance_m"]
        )
    return pd.concat(frames, ignore_index=True)


def load_race_results(race: RaceIdentifier) -> pd.DataFrame:
    """Load starting grid position, finishing position, and status for a race.

    Output columns: driver, team, grid_position, finish_position, status.
    `finish_position` is NaN for retirements (use `status` to check).
    """
    session = _load_session(race.year, race.event)

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
