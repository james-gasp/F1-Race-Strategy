"""Unit tests for the pure (non-network) helpers in engine.data.circuit."""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.data.circuit import (
    CircuitOutline,
    build_circuit_outline,
    project_position_onto_outline,
)


def _circular_telemetry(n=200, radius=100.0):
    """Synthetic telemetry tracing a circle, so distance/x/y are easy to reason about."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    distance = np.linspace(0, 2 * np.pi * radius, n, endpoint=False)
    return pd.DataFrame({"distance_m": distance, "x": x, "y": y})


def test_build_circuit_outline_resamples_to_requested_point_count():
    outline = build_circuit_outline(_circular_telemetry(), n_points=50)
    assert len(outline.points) == 50
    assert outline.length_m > 0


def test_build_circuit_outline_traces_a_circle():
    outline = build_circuit_outline(_circular_telemetry(radius=100.0), n_points=100)
    radii = [np.hypot(x, y) for x, y in outline.points]
    assert all(abs(r - 100.0) < 1.0 for r in radii)


def test_project_position_onto_outline_finds_nearest_point():
    outline = build_circuit_outline(_circular_telemetry(radius=100.0), n_points=360)
    # Point at index 90 of 360 evenly-spaced points around the circle -> progress 0.25
    x, y = outline.points[90]
    progress = project_position_onto_outline(x, y, outline)
    assert abs(progress - 0.25) < 0.01


def test_circuit_outline_round_trips_through_dict():
    outline = CircuitOutline(points=((1.0, 2.0), (3.0, 4.0)), length_m=123.4)
    restored = CircuitOutline.from_dict(outline.to_dict())
    assert restored == outline
