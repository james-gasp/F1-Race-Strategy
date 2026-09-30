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

## Deploying

The app is two pieces hosted separately: the **backend** (FastAPI, in a
Docker container) and the **frontend** (a static Vite build).

**1. Backend on [Render](https://render.com)**

1. Render dashboard → **New → Blueprint** → select this repo. It reads
   [`render.yaml`](render.yaml): a Docker web service with a 5 GB persistent
   disk for the FastF1 cache.
2. When prompted, set `ALLOWED_ORIGINS` to your frontend's URL (you can
   leave it as a placeholder and update it after step 2).
3. Deploy, then check `https://<your-service>.onrender.com/health` returns
   `{"status":"ok"}`.

The blueprint uses the 2 GB `standard` plan: one race with telemetry loaded
takes ~350 MB, so the 512 MB plans run out of memory on the Telemetry view.

**2. Frontend on [Vercel](https://vercel.com)**

1. **Add New → Project** → import this repo.
2. Set **Root Directory** to `frontend` (Vite is auto-detected).
3. Add the environment variable `VITE_API_BASE_URL` =
   `https://<your-service>.onrender.com`.
4. Deploy, then put the Vercel URL into the backend's `ALLOWED_ORIGINS`
   on Render (comma-separate several, e.g. a custom domain too).

Both redeploy automatically on every push to `main`.

**Configuration**

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `ALLOWED_ORIGINS` | backend | `http://localhost:5173` | Comma-separated origins allowed to call the API (CORS) |
| `F1_CACHE_DIR` | backend | repo's `.fastf1_cache/` + `.circuit_cache/` | Root folder for on-disk caches; point at a persistent disk |
| `F1_MAX_CACHED_RACES` | backend | `16` | Races kept in memory; lower it on small servers |
| `VITE_API_BASE_URL` | frontend (build time) | `http://localhost:8000` | Backend URL |

To run the backend image yourself:

```bash
docker build -t f1-race-strategy-api .
docker run -p 8000:8000 -v f1cache:/var/data f1-race-strategy-api
```

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
