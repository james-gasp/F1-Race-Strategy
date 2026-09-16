"""API integration tests — hit real endpoints against real (disk-cached) FastF1
data for 2023 Silverstone. Marked `integration` like the engine's equivalent
test, since it needs the FastF1 API reachable at least once to populate cache.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

pytestmark = pytest.mark.integration

YEAR = 2023
EVENT = "Silverstone"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def race_summary(client):
    resp = client.get(f"/races/{YEAR}/{EVENT}")
    if resp.status_code != 200:
        pytest.skip(f"FastF1 data unavailable: {resp.text}")
    return resp.json()


def test_health_check_does_not_need_network(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_race_returns_full_grid(race_summary):
    assert race_summary["year"] == YEAR
    assert race_summary["total_race_laps"] > 40
    assert race_summary["pit_loss_s"] > 0
    assert len(race_summary["drivers"]) == 20
    ver = next(d for d in race_summary["drivers"] if d["driver"] == "VER")
    assert ver["grid_position"] == 1  # pole position
    assert ver["finish_position"] == 1.0
    assert len(ver["historical_strategy"]) >= 1


def test_get_race_404_for_unknown_event(client):
    # FastF1 fuzzy-matches event name strings to the nearest real event, so a
    # garbage event name doesn't reliably fail -- an out-of-range year does.
    resp = client.get("/races/1800/Silverstone")
    assert resp.status_code == 404


def test_simulate_strategy(client, race_summary):
    total_laps = race_summary["total_race_laps"]
    resp = client.post(
        "/strategy/simulate",
        json={
            "year": YEAR,
            "event": EVENT,
            "driver": "VER",
            "stints": [
                {"compound": "MEDIUM", "laps": total_laps // 2},
                {"compound": "HARD", "laps": total_laps - total_laps // 2},
            ],
            "n_sims": 200,
            "seed": 0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mean_s"] > 0
    assert body["n_sims"] == 200
    assert body["p10_s"] <= body["median_s"] <= body["p90_s"]


def test_compare_strategies_ranks_results(client, race_summary):
    total_laps = race_summary["total_race_laps"]
    half = total_laps // 2
    resp = client.post(
        "/strategy/compare",
        json={
            "year": YEAR,
            "event": EVENT,
            "strategies": [
                {
                    "name": "1-stop",
                    "driver": "VER",
                    "stints": [
                        {"compound": "MEDIUM", "laps": half},
                        {"compound": "HARD", "laps": total_laps - half},
                    ],
                },
                {
                    "name": "2-stop",
                    "driver": "VER",
                    "stints": [
                        {"compound": "SOFT", "laps": half // 2},
                        {"compound": "SOFT", "laps": half // 2},
                        {"compound": "HARD", "laps": total_laps - 2 * (half // 2)},
                    ],
                },
            ],
            "n_sims": 300,
            "seed": 0,
        },
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[0]["mean_s"] <= results[1]["mean_s"]  # sorted ascending
    assert sum(r["prob_fastest"] for r in results) == pytest.approx(1.0, abs=1e-9)


def test_optimize_recommends_a_legal_strategy(client, race_summary):
    total_laps = race_summary["total_race_laps"]
    resp = client.post(
        "/strategy/optimize",
        json={
            "year": YEAR,
            "event": EVENT,
            "driver": "VER",
            "current_compound": "MEDIUM",
            "current_tyre_life": 15,
            "next_lap_number": 26,
            "total_race_laps": total_laps,
            "lap_step": 5,
            "n_sims": 300,
            "seed": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommended"] == body["candidates"][0]
    assert len(body["candidates"]) > 1


def test_optimize_400_when_two_compound_rule_impossible(client, race_summary):
    total_laps = race_summary["total_race_laps"]
    resp = client.post(
        "/strategy/optimize",
        json={
            "year": YEAR,
            "event": EVENT,
            "driver": "VER",
            "current_compound": "SOFT",
            "current_tyre_life": 30,
            "next_lap_number": total_laps,  # 1 lap left, no time for a legal stop
            "total_race_laps": total_laps,
            "n_sims": 100,
        },
    )
    assert resp.status_code == 400
    assert "two-compound" in resp.json()["detail"]


def test_field_simulation_returns_probabilities_for_finishers(client):
    resp = client.post("/strategy/field", json={"year": YEAR, "event": EVENT, "n_sims": 500, "seed": 0})
    assert resp.status_code == 200
    drivers = resp.json()["drivers"]
    assert len(drivers) > 0
    assert drivers[0]["driver"] == "VER"  # VER should come out as the expected favorite
    for d in drivers:
        assert abs(sum(d["position_probabilities"].values()) - 1.0) < 1e-9
