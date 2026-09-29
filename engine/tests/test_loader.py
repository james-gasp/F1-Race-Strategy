"""Unit tests for the pure (non-network) helpers in engine.data.loader.

`load_race_laps` itself talks to FastF1 and is exercised separately as an
integration check (run manually / in CI with network access), not here.
"""

from __future__ import annotations

import pandas as pd

from engine.data.loader import clean_pace_laps, raced_events, safety_car_laps

COLUMNS = ["driver", "lap_number", "lap_time_s", "is_pit_lap", "is_accurate", "track_status"]


def _row(driver, lap_number, lap_time_s, is_pit_lap, is_accurate, track_status="1"):
    return {
        "driver": driver,
        "lap_number": lap_number,
        "lap_time_s": lap_time_s,
        "is_pit_lap": is_pit_lap,
        "is_accurate": is_accurate,
        "track_status": track_status,
    }


def test_clean_pace_laps_drops_pit_laps():
    laps = pd.DataFrame(
        [
            _row("HAM", 1, 91.0, is_pit_lap=False, is_accurate=True),
            _row("HAM", 2, 130.0, is_pit_lap=True, is_accurate=True),
        ]
    )
    clean = clean_pace_laps(laps)
    assert len(clean) == 1
    assert clean.iloc[0]["lap_number"] == 1


def test_clean_pace_laps_drops_inaccurate_laps():
    laps = pd.DataFrame(
        [
            _row("HAM", 1, 91.0, is_pit_lap=False, is_accurate=True),
            _row("HAM", 2, 200.0, is_pit_lap=False, is_accurate=False),  # e.g. red flag
        ]
    )
    clean = clean_pace_laps(laps)
    assert len(clean) == 1
    assert clean.iloc[0]["lap_number"] == 1


def test_clean_pace_laps_drops_missing_lap_time():
    laps = pd.DataFrame(
        [
            _row("HAM", 1, 91.0, is_pit_lap=False, is_accurate=True),
            _row("HAM", 2, float("nan"), is_pit_lap=False, is_accurate=True),
        ]
    )
    clean = clean_pace_laps(laps)
    assert len(clean) == 1


def test_safety_car_laps_matches_sc_and_vsc_status_codes():
    laps = pd.DataFrame(
        [
            _row("HAM", 1, 91.0, False, True, track_status="1"),  # green
            _row("HAM", 2, 110.0, False, True, track_status="4"),  # safety car
            _row("HAM", 3, 105.0, False, True, track_status="6"),  # VSC
            _row("HAM", 4, 91.0, False, True, track_status="126"),  # SC mixed with other flags
        ]
    )
    sc = safety_car_laps(laps)
    assert set(sc["lap_number"]) == {2, 3, 4}


def test_safety_car_laps_excludes_green_flag():
    laps = pd.DataFrame([_row("HAM", 1, 91.0, False, True, track_status="1")])
    assert len(safety_car_laps(laps)) == 0


def _event(round_number, name, race_start):
    return {
        "RoundNumber": round_number,
        "EventName": name,
        "Location": f"{name} town",
        "Country": "Somewhere",
        "Session5DateUtc": pd.Timestamp(race_start) if race_start else pd.NaT,
    }


def test_raced_events_keeps_only_races_already_started_in_round_order():
    schedule = pd.DataFrame(
        [
            _event(3, "Third GP", "2026-03-29 05:00"),
            _event(1, "First GP", "2026-03-08 04:00"),
            _event(4, "Future GP", "2026-05-03 17:00"),
            _event(2, "Cancelled GP", None),
        ]
    )
    raced = raced_events(schedule, now=pd.Timestamp("2026-04-01"))
    assert raced["event_name"].tolist() == ["First GP", "Third GP"]
    assert raced["round"].tolist() == [1, 3]
    assert raced.columns.tolist() == ["round", "event_name", "location", "country", "race_start_utc"]


def test_raced_events_is_empty_before_the_season_starts():
    schedule = pd.DataFrame([_event(1, "First GP", "2026-03-08 04:00")])
    raced = raced_events(schedule, now=pd.Timestamp("2026-01-01"))
    assert raced.empty
