"""Download races into the local FastF1 cache, ready to upload to a deployed server.

F1's live-timing server blocks cloud hosts (e.g. Google Cloud), so a deployed
server can't fetch race data itself. Run this on your own machine instead,
then upload the cache folder (see "Adding races" in the README).

Usage (from the repo root):
    uv run python -m scripts.download_races 2023 "British Grand Prix" "Japanese Grand Prix"
    uv run python -m scripts.download_races 2024 --all
"""

from __future__ import annotations

import argparse
import sys

from engine.data.loader import (
    RaceIdentifier,
    is_race_downloaded,
    load_car_telemetry,
    load_race_laps,
    load_race_results,
    load_season_races,
    load_weather,
    race_folder_name,
)


def download_race(year: int, event: str) -> None:
    """Load everything the app needs for one race, which fills FastF1's cache."""
    race = RaceIdentifier(year=year, event=event)
    laps = load_race_laps(race)
    load_race_results(race)
    load_weather(race)
    # Telemetry is loaded for the whole session at once, so one driver is
    # enough to cache every car's data.
    load_car_telemetry(race, driver=str(laps["driver"].iloc[0]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("year", type=int)
    parser.add_argument("events", nargs="*", help='Grand Prix names, e.g. "British Grand Prix"')
    parser.add_argument("--all", action="store_true", help="every race run so far that season")
    args = parser.parse_args(argv)

    season = load_season_races(args.year)
    if args.all:
        events = season["event_name"].tolist()
    elif args.events:
        events = args.events
    else:
        parser.error('name at least one Grand Prix, or pass --all')

    failed = []
    for event in events:
        row = season[season["event_name"] == event]
        if not row.empty and is_race_downloaded(
            args.year, race_folder_name(row["event_date"].iloc[0], event)
        ):
            print(f"  already downloaded  {args.year} {event}")
            continue
        print(f"  downloading         {args.year} {event} ...", flush=True)
        try:
            download_race(args.year, event)
        except Exception as exc:  # noqa: BLE001 -- keep going; report every failure at the end
            failed.append(event)
            print(f"  FAILED              {args.year} {event}: {exc}", file=sys.stderr)

    print(f"\nDone: {len(events) - len(failed)} of {len(events)} races ready.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
