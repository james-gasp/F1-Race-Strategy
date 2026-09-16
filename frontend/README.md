# Frontend

React + TypeScript + Vite dashboard for the F1 race strategy simulator. See the
[root README](../README.md) for the full project overview.

## Develop

```bash
npm install
npm run dev
```

Runs against `http://localhost:8000` by default (the FastAPI backend — see
the root README to start it). Override with a `.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Scripts

- `npm run dev` — Vite dev server with HMR
- `npm run build` — typecheck (`tsc -b`) + production build
- `npm run lint` — oxlint
- `npm run preview` — serve the production build locally

## Structure

- `src/api/` — typed fetch client + TS types mirroring the backend's Pydantic
  schemas (`api/schemas/*.py`)
- `src/components/` — one component per dashboard panel (race selector,
  strategy builder, results charts, field simulation, optimizer)
- `src/pages/Dashboard.tsx` — page-level state and data flow between panels
