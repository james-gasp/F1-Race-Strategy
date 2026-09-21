"""Circuit outline extraction from car position telemetry.

A track map needs the physical shape of the circuit. FastF1 doesn't ship
circuit geometry directly, but a clean lap's X/Y position telemetry traces
the track itself — so we pick one accurate, non-pit lap from a reference
driver and resample it to an evenly-spaced outline, which is cheap to cache
and reuse for every driver's dot on the track map.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine.data.loader import RaceIdentifier, load_car_telemetry, load_race_laps

DEFAULT_CIRCUIT_CACHE_DIR = Path(__file__).resolve().parents[2] / ".circuit_cache"


@dataclass(frozen=True)
class CircuitOutline:
    """A resampled, evenly-spaced circuit outline.

    `points` are (x, y) pairs in track-local meters (FastF1's native
    telemetry units), ordered around the lap starting at start/finish.
    """

    points: tuple[tuple[float, float], ...]
    length_m: float

    def to_dict(self) -> dict:
        return {"points": [list(p) for p in self.points], "length_m": self.length_m}

    @classmethod
    def from_dict(cls, data: dict) -> CircuitOutline:
        return cls(
            points=tuple((float(x), float(y)) for x, y in data["points"]),
            length_m=float(data["length_m"]),
        )


def _pick_reference_lap(laps: pd.DataFrame, driver: str | None) -> tuple[str, int]:
    """Pick a clean (accurate, non-pit) lap to trace the circuit from.

    Prefers the fastest accurate lap overall (least likely to include pit
    lane or a safety car period) unless a specific driver is requested.
    """
    candidates = laps[(~laps["is_pit_lap"]) & laps["is_accurate"] & laps["lap_time_s"].notna()]
    if driver is not None:
        candidates = candidates[candidates["driver"] == driver]
    if candidates.empty:
        raise ValueError("No clean (accurate, non-pit) lap available to trace the circuit from")
    best = candidates.loc[candidates["lap_time_s"].idxmin()]
    return str(best["driver"]), int(best["lap_number"])


def build_circuit_outline(
    telemetry: pd.DataFrame, n_points: int = 400
) -> CircuitOutline:
    """Resample one lap's X/Y telemetry to `n_points` evenly-spaced-by-distance points.

    `telemetry` must already be scoped to a single driver+lap (columns:
    distance_m, x, y), e.g. one group from `load_car_telemetry`.
    """
    telemetry = telemetry.sort_values("distance_m")
    distance = telemetry["distance_m"].to_numpy(dtype=float)
    x = telemetry["x"].to_numpy(dtype=float)
    y = telemetry["y"].to_numpy(dtype=float)

    if len(distance) < 2 or distance[-1] <= distance[0]:
        raise ValueError("Telemetry does not cover a full lap of distance")

    # Drop any non-increasing distance samples (can happen near lap boundaries)
    # so np.interp's x-array is strictly increasing.
    keep = np.concatenate([[True], np.diff(distance) > 0])
    distance, x, y = distance[keep], x[keep], y[keep]

    sample_distances = np.linspace(distance[0], distance[-1], n_points, endpoint=False)
    x_resampled = np.interp(sample_distances, distance, x)
    y_resampled = np.interp(sample_distances, distance, y)

    points = tuple(zip(x_resampled.tolist(), y_resampled.tolist()))
    return CircuitOutline(points=points, length_m=float(distance[-1] - distance[0]))


def project_position_onto_outline(x: float, y: float, outline: CircuitOutline) -> float:
    """Return the outline's nearest-point track progress (0..1) for an (x, y) position.

    Used to place a driver's dot on the map between recorded telemetry
    samples, or when only a coarse (lap-level) position is available.
    """
    pts = np.array(outline.points)
    dists = np.hypot(pts[:, 0] - x, pts[:, 1] - y)
    return float(np.argmin(dists) / len(pts))


def _cache_path(race: RaceIdentifier, cache_dir: Path) -> Path:
    return cache_dir / f"{race.year}_{race.event.replace(' ', '_')}.json"


def load_or_build_circuit_outline(
    race: RaceIdentifier, cache_dir: Path = DEFAULT_CIRCUIT_CACHE_DIR
) -> CircuitOutline:
    """Return a race's circuit outline, building and caching it on first use.

    Caches only the small resampled outline (a few hundred points), not the
    raw telemetry that was used to build it — reloading full car telemetry on
    every server restart would be needlessly slow.
    """
    path = _cache_path(race, cache_dir)
    if path.exists():
        return CircuitOutline.from_dict(json.loads(path.read_text()))

    laps = load_race_laps(race)
    driver, lap_number = _pick_reference_lap(laps, driver=None)
    telemetry = load_car_telemetry(race, driver=driver)
    lap_telemetry = telemetry[telemetry["lap_number"] == lap_number]
    outline = build_circuit_outline(lap_telemetry)

    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outline.to_dict()))
    return outline
