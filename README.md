# F1 Race Strategy Simulator

A Formula 1 race strategy simulator that goes beyond a single car's lap time:
it fits tire degradation, fuel burn-off, and pit-loss models from real
telemetry, then runs Monte Carlo simulations of the **whole field** to
produce finishing-position probabilities and a live pit-stop optimizer —
the kind of tool a strategy team actually uses.

Built to demonstrate three things together: the statistical modeling of a
data science project, the strategic reasoning of a race strategy tool, and
the engineering of a properly separated, typed, tested system rather than a
single notebook script.

## Key result

Every claim below is reproducible from real 2023 British Grand Prix
(Silverstone) data — nothing here is hand-tuned:

- **Field simulation accuracy**: simulating all 17 race finishers together,
  using only their actual historical strategies run through the fitted pace
  and pit-loss models (no hand-coded team strengths), the resulting expected
  finishing order has a **0.94 Spearman correlation** with the real result.
  The model correctly makes Max Verstappen the clear favorite (44.6% win
  probability, 73.0% podium probability) — he won.
- **Pit stop optimizer**: given Verstappen's actual mid-race state at lap 26
  (15 laps into a MEDIUM stint, hasn't pitted yet), the optimizer searches
  every legal pit lap × compound combination and its top recommendation is
  **pit after lap 34** — the exact lap he pitted on in the real race.
- **Regulatory correctness**: the optimizer enforces F1's mandatory
  two-compound rule. Without it, the model can recommend "never pit again"
  whenever the current tire's fitted degradation happens to be mild — a real
  bug that was caught and fixed by validating against live data, not just
  unit tests.

## Architecture

```
engine/            pure Python simulation core — no web framework dependencies,
                    independently testable, this is where the statistical/
                    strategic substance lives
  data/loader.py      FastF1 session -> clean lap-by-lap DataFrame
  models/pace.py       OLS fit: lap_time ~ driver + compound + fuel burn-off
                        (lap_number) + per-compound tire degradation (tyre_life,
                        tyre_life^2) -- separable because tyre_life resets every
                        stint while lap_number is monotonic across the race
  models/pitloss.py    pit lane time loss, from the delta between actual and
                        model-predicted in/out-lap times
  strategy/simulate.py  Monte Carlo simulation of one strategy; compares
                         multiple strategies with a per-draw win probability
  strategy/field.py     simulates the whole grid together -> finishing
                         position probability distributions
  optimize/optimizer.py  mid-race "should I pit now, and on what tire" search,
                          constrained to strategies that satisfy F1's
                          two-compound regulation

api/              FastAPI layer -- a thin, typed contract over the engine
  context.py        per-race model fitting, cached in-process
  schemas/            Pydantic request/response models (the frontend's type
                       contract)
  routers/             /races, /strategy/simulate, /compare, /optimize, /field

frontend/         React + TypeScript (Vite) dashboard
  src/api/           typed fetch client mirroring the Pydantic schemas
  src/components/      race selector, strategy builder, results charts
                        (recharts), field simulation, pit stop optimizer
  src/pages/            page-level state and data flow
```

The engine has no web dependencies on purpose: it's independently testable
and readable without wading through API or UI code, and it's the part that
actually demonstrates the modeling work. The API is a thin typed boundary.
The frontend was built last, after the engine and API were already complete
and demoable through Swagger UI alone — so the project never depended on the
frontend being finished to be a working product.

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

## Known limitations

These are deliberate MVP scope decisions, not oversights:

- **No explicit overtaking/traffic model** — the field simulation ranks
  finishing order purely by total race time, equivalent to assuming a pace
  advantage always converts to track position. A probabilistic
  overtake-difficulty adjustment is a natural extension.
- **DNFs are excluded from field simulation** — the model doesn't simulate
  mechanical failures or accidents, so only finishers are compared.
- **No safety car / VSC probability modeling yet** — track status is loaded
  and available (`engine/data/loader.py:safety_car_laps`), but the optimizer
  doesn't yet weight pit timing against SC/VSC probability.
- **No ML degradation model yet** — degradation is a per-compound linear +
  quadratic OLS fit, not a gradient-boosted model with feature importance.
- **No historical backtest/replay UI yet** — the engine can already answer
  "what would the optimizer have recommended at any point in a real race,"
  but there's no dedicated replay view for it.

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

## Tech stack

Python 3.12, [FastF1](https://docs.fastf1.dev/), pandas, NumPy, SciPy,
FastAPI, Pydantic, pytest, [uv](https://docs.astral.sh/uv/) — React 19,
TypeScript, Vite, Recharts, oxlint.
