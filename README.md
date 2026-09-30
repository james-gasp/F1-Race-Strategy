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

The [`Dockerfile`](Dockerfile) builds the whole app into one container: the
FastAPI backend also serves the built website, so it runs from a single URL.

### Free: Hugging Face Spaces

Hugging Face's free Docker Spaces have enough memory for FastF1 telemetry (one
race with telemetry loaded takes ~350 MB) and need no credit card. A GitHub
Action ([`deploy-huggingface.yml`](.github/workflows/deploy-huggingface.yml))
pushes the app to your Space on every push to `main`.

1. Sign up at [huggingface.co](https://huggingface.co) and create a Space:
   **New Space** → any name → SDK **Docker** → **Blank** → **Public** →
   free **CPU basic** hardware.
2. Create a token at **Settings → Access Tokens** with **Write** access.
3. In this GitHub repo, **Settings → Secrets and variables → Actions**:
   - **Secrets** tab → `HF_TOKEN` = the token
   - **Variables** tab → `HF_SPACE` = `<your-hf-username>/<space-name>`
4. **Actions** tab → **Deploy to Hugging Face Spaces** → **Run workflow**
   (or just push to `main`).

The Space builds for a few minutes, then the app is live at
`https://<your-hf-username>-<space-name>.hf.space`.

Free-tier caveats: the Space sleeps after ~48 hours without visitors (the next
visit wakes it in about a minute), and its disk isn't persistent, so downloaded
race data is re-fetched from FastF1 after a restart.

### Paid alternative: Render

[`render.yaml`](render.yaml) is a Render Blueprint for the same container with
a persistent disk for the FastF1 cache (**New → Blueprint** → select this
repo). It needs the 2 GB `standard` plan; the 512 MB plans run out of memory
on the Telemetry view.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `F1_CACHE_DIR` | repo's `.fastf1_cache/` + `.circuit_cache/` (image: `/var/data`) | Root folder for on-disk caches |
| `F1_MAX_CACHED_RACES` | `16` | Races kept in memory; lower it on small servers |
| `FRONTEND_DIST_DIR` | unset (image: built site) | Serve a built frontend from the API at `/` |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS origins, only needed if the frontend is hosted separately |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend build-time API URL (`/` = same origin) |

To run the production image yourself:

```bash
docker build -t f1-race-strategy .
docker run -p 7860:7860 f1-race-strategy
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
