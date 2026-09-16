"""Unit tests for the pure (non-network) helpers in engine.data.loader.

`load_race_laps` itself talks to FastF1 and is exercised separately as an
integration check (run manually / in CI with network access), not here.
"""

from __future__ import annotations

import pandas as pd

from engine.data.loader import clean_pace_laps, safety_car_laps

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
