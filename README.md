# F1 Race Strategy Simulator

A Formula 1 race strategy simulator that goes beyond a single car's lap time:
it fits tire degradation, fuel burn-off, and pit-loss models from real
telemetry, then runs Monte Carlo simulations of the **whole field** to
produce finishing-position probabilities and a live pit-stop optimizer.

Planning on updating this project to add more features and more realistic.

## How the model works

1. **Pace model** — for each race, an OLS fit separates four effects from
   real lap times: driver/car pace, compound base pace, fuel burn-off (a
   function of lap number), and tire degradation (a function of tire age,
   per compound, with both linear and quadratic terms). The residual spread
   becomes the noise distribution for Monte Carlo sampling.
2. **Pit loss model** — the time cost of a pit stop is isolated by comparing
   the actual in-lap and out-lap times against what the pace model predicts
   a clean lap would have taken, then taking the median across observed
   stops (robust to one anomalous long stop).
3. **Single-car Monte Carlo** — a strategy (compound sequence + pit laps) is
   simulated thousands of times, sampling noisy lap times and pit stop
   durations, producing a full time distribution rather than one number.
4. **Field simulation** — every finisher's real historical strategy is
   simulated together; ranking by total time on each Monte Carlo draw
   produces a finishing-position probability table per driver.
5. **Optimizer** — from a given mid-race state (current lap, tire, tire
   age), it searches candidate pit laps and compounds, drops any candidate
   that wouldn't satisfy F1's two-compound rule by race end, and ranks the
   rest by expected remaining race time.

## Getting started

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+.

**Backend:**

```bash
uv sync
uv run uvicorn api.main:app --reload
```

API docs at `http://localhost:8000/docs`.

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:5173`. It talks to `http://localhost:8000` by
default; override with `frontend/.env.local` (`VITE_API_BASE_URL=...`) if
your backend runs elsewhere.

The first request for a given race fetches and caches data from the FastF1
API (a few seconds); subsequent requests for the same race are served from
FastF1's on-disk cache plus an in-process fitted-model cache.

## Testing

```bash
uv run pytest                 # unit tests -- synthetic data, no network, fast
uv run pytest -m integration  # end-to-end checks against real FastF1 data
uv run ruff check .           # lint

cd frontend
npm run build                 # typecheck + production build
npm run lint                  # oxlint
```

Unit tests use synthetic data with known ground-truth coefficients so they
run offline and deterministically; integration tests validate the full
pipeline against real race data and are run separately (they need network
access to FastF1 on first run).
