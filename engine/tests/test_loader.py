"""Unit tests for the pure (non-network) helpers in engine.data.loader.

`load_race_laps` itself talks to FastF1 and is exercised separately as an
integration check (run manually / in CI with network access), not here.
"""

from __future__ import annotations

import pandas as pd

from engine.data.loader import (
    available_years,
    clean_pace_laps,
    is_race_downloaded,
    link_race_data,
    race_folder_name,
    raced_events,
    safety_car_laps,
)

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
        "EventDate": pd.Timestamp(race_start).normalize() if race_start else pd.NaT,
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
    assert raced.columns.tolist() == [
        "round",
        "event_name",
        "location",
        "country",
        "event_date",
        "race_start_utc",
    ]


def test_raced_events_is_empty_before_the_season_starts():
    schedule = pd.DataFrame([_event(1, "First GP", "2026-03-08 04:00")])
    raced = raced_events(schedule, now=pd.Timestamp("2026-01-01"))
    assert raced.empty


def _fake_race(root, year, folder, complete=True):
    session = root / str(year) / folder / f"{folder[:10]}_Race"
    session.mkdir(parents=True)
    (session / "timing_app_data.ff1pkl").write_bytes(b"x")
    if complete:
        (session / "car_data.ff1pkl").write_bytes(b"x")


def test_race_folder_name_matches_fastf1_cache_layout():
    assert (
        race_folder_name(pd.Timestamp("2023-07-09"), "British Grand Prix")
        == "2023-07-09_British_Grand_Prix"
    )


def test_is_race_downloaded_needs_telemetry_in_cache_or_race_data(tmp_path):
    cache, store = tmp_path / "cache", tmp_path / "store"
    _fake_race(cache, 2023, "2023-07-09_British_Grand_Prix")
    _fake_race(store, 2024, "2024-06-23_Spanish_Grand_Prix")
    _fake_race(cache, 2025, "2025-07-06_British_Grand_Prix", complete=False)

    def downloaded(year, folder):
        return is_race_downloaded(year, folder, cache_dir=cache, race_data_dir=store)

    assert downloaded(2023, "2023-07-09_British_Grand_Prix")
    assert downloaded(2024, "2024-06-23_Spanish_Grand_Prix")
    assert not downloaded(2025, "2025-07-06_British_Grand_Prix")  # laps only, no telemetry
    assert not downloaded(2023, "2023-09-03_Italian_Grand_Prix")


def test_link_race_data_links_each_race_once_and_keeps_existing_folders(tmp_path):
    cache, store = tmp_path / "cache", tmp_path / "store"
    _fake_race(store, 2023, "2023-07-09_British_Grand_Prix")
    _fake_race(store, 2023, "2023-09-03_Italian_Grand_Prix")
    _fake_race(cache, 2023, "2023-09-03_Italian_Grand_Prix")  # already local: leave it

    link_race_data(2023, cache_dir=cache, race_data_dir=store)
    link_race_data(2023, cache_dir=cache, race_data_dir=store)  # idempotent

    british = cache / "2023" / "2023-07-09_British_Grand_Prix"
    assert british.is_symlink()
    assert british.resolve() == (store / "2023" / "2023-07-09_British_Grand_Prix").resolve()
    assert not (cache / "2023" / "2023-09-03_Italian_Grand_Prix").is_symlink()
    link_race_data(2024, cache_dir=cache, race_data_dir=store)  # no data for 2024: no-op
    assert not (cache / "2024").exists()


def test_available_years_all_seasons_or_only_downloaded_ones(tmp_path):
    cache, store = tmp_path / "cache", tmp_path / "store"
    _fake_race(cache, 2023, "2023-07-09_British_Grand_Prix")
    _fake_race(store, 2024, "2024-06-23_Spanish_Grand_Prix")
    _fake_race(cache, 2025, "2025-07-06_British_Grand_Prix", complete=False)
    today = pd.Timestamp("2026-09-30")

    every = available_years(False, cache_dir=cache, race_data_dir=store, today=today)
    assert every[0] == 2026 and every[-1] == 2018
    downloaded = available_years(True, cache_dir=cache, race_data_dir=store, today=today)
    assert downloaded == [2024, 2023]
