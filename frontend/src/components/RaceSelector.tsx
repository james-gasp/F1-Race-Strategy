import { useEffect, useState } from "react";
import { ApiError, getSeason, getSeasons } from "../api/client";
import type { SeasonRace } from "../api/types";

interface Props {
  onLoad: (year: number, event: string) => void;
  loading: boolean;
  // The race currently on screen, so the dropdowns open on it.
  currentYear?: number;
  currentEvent?: string;
}

// Fallback if the server's season list can't be fetched: FastF1 has full
// timing + telemetry from 2018 onwards.
const FIRST_YEAR = 2018;
const THIS_YEAR = new Date().getFullYear();
const ALL_YEARS = Array.from({ length: THIS_YEAR - FIRST_YEAR + 1 }, (_, i) => THIS_YEAR - i);

// A deployed server may only offer the seasons it has race data for.
let yearsPromise: Promise<number[]> | null = null;
function fetchYears(): Promise<number[]> {
  yearsPromise ??= getSeasons()
    .then((s) => s.years)
    .catch(() => {
      yearsPromise = null;
      return ALL_YEARS;
    });
  return yearsPromise;
}

// Schedules don't change within a page session (bar the current season
// gaining a race), so fetch each year once.
const seasonCache = new Map<number, Promise<SeasonRace[]>>();

function fetchSeason(year: number): Promise<SeasonRace[]> {
  let p = seasonCache.get(year);
  if (!p) {
    p = getSeason(year).then((s) => s.races);
    p.catch(() => seasonCache.delete(year));
    seasonCache.set(year, p);
  }
  return p;
}

export default function RaceSelector({ onLoad, loading, currentYear, currentEvent }: Props) {
  const [years, setYears] = useState<number[] | null>(null);
  const [year, setYear] = useState(currentYear ?? THIS_YEAR - 1);
  const [season, setSeason] = useState<{ year: number; races: SeasonRace[] } | null>(null);
  const [seasonError, setSeasonError] = useState<{ year: number; message: string } | null>(null);
  const [event, setEvent] = useState<string>(currentEvent ?? "");

  useEffect(() => {
    let cancelled = false;
    fetchYears().then((ys) => {
      if (cancelled) return;
      setYears(ys);
      // Open on the newest season offered unless it already has a valid pick.
      setYear((y) => (ys.includes(y) || ys.length === 0 ? y : ys[0]));
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchSeason(year)
      .then((races) => {
        if (cancelled) return;
        setSeason({ year, races });
        setSeasonError(null);
        // Keep the chosen race if it ran this year, else default to the latest one.
        setEvent((prev) => (races.some((r) => r.event_name === prev) ? prev : races[races.length - 1]?.event_name ?? ""));
      })
      .catch((err) => {
        if (!cancelled) {
          setSeasonError({ year, message: err instanceof ApiError ? err.message : "Could not load the schedule" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [year]);

  const races = season?.year === year ? season.races : null;
  const error = seasonError?.year === year ? seasonError.message : null;
  const seasonLoading = races == null && error == null;

  return (
    <section className="panel">
      <h2>Race</h2>
      <div className="row">
        <label>
          Season
          <select value={year} onChange={(e) => setYear(Number(e.target.value))} disabled={loading || !years}>
            {!years && <option value={year}>{year}</option>}
            {years?.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0 flex-1">
          Grand Prix
          <select
            value={event}
            onChange={(e) => setEvent(e.target.value)}
            disabled={loading || !races || races.length === 0}
            className="w-full"
          >
            {seasonLoading && <option>Loading schedule…</option>}
            {races?.length === 0 && <option>No races available</option>}
            {races?.map((r) => (
              <option key={r.round} value={r.event_name}>
                R{r.round} · {r.event_name} — {r.location}
              </option>
            ))}
          </select>
        </label>
        <button disabled={loading || !races?.some((r) => r.event_name === event)} onClick={() => onLoad(year, event)}>
          {loading ? "Loading…" : "Load race"}
        </button>
      </div>
      {error && <p className="error-text mb-0 mt-3">{error}</p>}
    </section>
  );
}
