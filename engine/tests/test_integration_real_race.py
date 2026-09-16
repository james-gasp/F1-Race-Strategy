"""End-to-end integration check against real FastF1 data.

Skipped automatically if the FastF1 API can't be reached (no network, e.g. in
a sandboxed CI runner) — this is deliberately excluded from the fast unit-test
path and is meant to be run manually (`uv run pytest -m integration`) or in a
CI job that has network access.
"""

from __future__ import annotations

import pytest

from engine.data.loader import RaceIdentifier, clean_pace_laps, load_race_laps
from engine.models.pace import fit_pace_model
from engine.models.pitloss import fit_pit_loss_model

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_race_laps():
    try:
        return load_race_laps(RaceIdentifier(2023, "Silverstone"))
    except Exception as exc:  # noqa: BLE001 - any failure here means "skip, no network"
        pytest.skip(f"FastF1 data unavailable: {exc}")


def test_full_pipeline_produces_sane_outputs(real_race_laps):
    laps = real_race_laps
    pace_laps = clean_pace_laps(laps)
    assert len(pace_laps) > 500

    model = fit_pace_model(pace_laps)
    assert 60 < model.intercept < 130  # plausible lap time in seconds for a dry race
    assert model.residual_std < 3.0  # a well-fit model shouldn't have huge lap-to-lap noise

    pit_model = fit_pit_loss_model(laps, model)
    assert 10 < pit_model.pit_loss_s < 40  # plausible pit lane loss range across F1 tracks
    assert pit_model.n_stops_observed > 5
