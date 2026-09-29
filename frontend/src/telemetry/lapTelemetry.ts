import { useEffect, useRef, useState } from "react";
import { ApiError, getDriverLapTelemetry } from "../api/client";
import type { DriverFrame, LapFrame, TelemetryPoint } from "../api/types";

export interface LapRef {
  driver: string;
  lap: number;
}

export function sameLap(a: LapRef | null, b: LapRef | null): boolean {
  return a != null && b != null && a.driver === b.driver && a.lap === b.lap;
}

// One lap resampled onto a shared distance grid, so the analysis lap and the
// reference lap can be plotted (and diffed) point-for-point.
export interface ResampledLap {
  time: number[];
  speed: number[];
  throttle: number[];
  brake: number[];
  gear: number[];
  x: number[];
  y: number[];
}

export interface Comparison {
  distance: number[];
  lap: ResampledLap;
  ref: ResampledLap;
  // lap time minus reference time at the same distance; negative = lap is ahead.
  delta: number[];
}

const GRID_STEP_M = 5;

// Linear interpolation of ys(xs) at `x`. `xs` must be ascending; `hint`
// carries the search position between calls since grid points are ascending too.
function interp(xs: number[], ys: number[], x: number, hint: { i: number }): number {
  while (hint.i < xs.length - 2 && xs[hint.i + 1] < x) hint.i++;
  const x0 = xs[hint.i];
  const x1 = xs[hint.i + 1];
  if (x1 === x0) return ys[hint.i];
  const t = Math.max(0, Math.min(1, (x - x0) / (x1 - x0)));
  return ys[hint.i] + (ys[hint.i + 1] - ys[hint.i]) * t;
}

// Step (sample-and-hold) lookup for discrete channels like gear and brake,
// where interpolating would invent values that never happened.
function hold(xs: number[], ys: number[], x: number, hint: { i: number }): number {
  while (hint.i < xs.length - 1 && xs[hint.i + 1] <= x) hint.i++;
  return ys[hint.i];
}

function resample(points: TelemetryPoint[], grid: number[]): ResampledLap {
  const sorted = [...points].sort((a, b) => a.distance_m - b.distance_m);
  const d = sorted.map((p) => p.distance_m);
  const channel = (pick: (p: TelemetryPoint) => number, stepwise = false) => {
    const ys = sorted.map(pick);
    const hint = { i: 0 };
    return grid.map((g) => (stepwise ? hold(d, ys, g, hint) : interp(d, ys, g, hint)));
  };
  return {
    time: channel((p) => p.lap_time_s),
    speed: channel((p) => p.speed_kmh),
    throttle: channel((p) => p.throttle_pct),
    brake: channel((p) => (p.brake ? 100 : 0), true),
    gear: channel((p) => p.gear, true),
    x: channel((p) => p.x),
    y: channel((p) => p.y),
  };
}

export function buildComparison(lap: TelemetryPoint[], ref: TelemetryPoint[]): Comparison | null {
  if (lap.length < 2 || ref.length < 2) return null;
  const maxD = Math.min(
    Math.max(...lap.map((p) => p.distance_m)),
    Math.max(...ref.map((p) => p.distance_m)),
  );
  const distance: number[] = [];
  for (let g = 0; g <= maxD; g += GRID_STEP_M) distance.push(g);
  const l = resample(lap, distance);
  const r = resample(ref, distance);
  return { distance, lap: l, ref: r, delta: l.time.map((t, i) => t - r.time[i]) };
}

// Fetches (and memoizes per driver+lap) the telemetry for two laps, returning
// their comparison once both have arrived.
export function useLapComparison(
  year: number,
  event: string,
  lap: LapRef | null,
  ref: LapRef | null,
): { comparison: Comparison | null; loading: boolean; error: string | null } {
  const cache = useRef(new Map<string, Promise<TelemetryPoint[]>>());
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    cache.current.clear();
  }, [year, event]);

  // Keyed on strings so a fresh-but-equal LapRef object doesn't refetch.
  const lapKey = lap ? `${lap.driver}:${lap.lap}` : null;
  const refKey = ref ? `${ref.driver}:${ref.lap}` : null;

  useEffect(() => {
    if (!lapKey || !refKey) return;
    let cancelled = false;
    const fetchLap = (key: string) => {
      let p = cache.current.get(key);
      if (!p) {
        const [driver, lapNo] = key.split(":");
        p = getDriverLapTelemetry(year, event, driver, Number(lapNo)).then((t) => t.points);
        p.catch(() => cache.current.delete(key));
        cache.current.set(key, p);
      }
      return p;
    };
    setLoading(true);
    setError(null);
    Promise.all([fetchLap(lapKey), fetchLap(refKey)])
      .then(([l, r]) => {
        if (!cancelled) setComparison(buildComparison(l, r));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load telemetry");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [year, event, lapKey, refKey]);

  return { comparison, loading, error };
}

export function lapTimeOf(d: DriverFrame | undefined): number | null {
  if (!d || d.sector1_s == null || d.sector2_s == null || d.sector3_s == null) return null;
  return d.sector1_s + d.sector2_s + d.sector3_s;
}

export interface DriverLap {
  lap: number;
  frame: DriverFrame;
  lapTime: number | null;
}

export function lapsForDriver(frames: LapFrame[], driver: string): DriverLap[] {
  const out: DriverLap[] = [];
  for (const f of frames) {
    const d = f.drivers.find((x) => x.driver === driver);
    if (d) out.push({ lap: f.lap_number, frame: d, lapTime: lapTimeOf(d) });
  }
  return out;
}

// Fastest timed lap across the whole race, skipping pit in-laps.
export function sessionFastestLap(frames: LapFrame[]): LapRef | null {
  let best: { ref: LapRef; t: number } | null = null;
  for (const f of frames) {
    for (const d of f.drivers) {
      const t = lapTimeOf(d);
      if (t != null && !d.pit_this_lap && (best == null || t < best.t)) {
        best = { ref: { driver: d.driver, lap: f.lap_number }, t };
      }
    }
  }
  return best?.ref ?? null;
}

export function fastestLapForDriver(frames: LapFrame[], driver: string, exclude?: LapRef | null): LapRef | null {
  let best: { lap: number; t: number } | null = null;
  for (const l of lapsForDriver(frames, driver)) {
    if (l.lapTime == null || l.frame.pit_this_lap) continue;
    if (exclude && exclude.driver === driver && exclude.lap === l.lap) continue;
    if (best == null || l.lapTime < best.t) best = { lap: l.lap, t: l.lapTime };
  }
  return best ? { driver, lap: best.lap } : null;
}

// F1-style lap time format, e.g. 92.184s -> "1:32.184".
export function formatLapTime(value: number | null | undefined): string {
  if (value == null) return "—";
  const minutes = Math.floor(value / 60);
  const seconds = value - minutes * 60;
  return `${minutes}:${seconds.toFixed(3).padStart(6, "0")}`;
}
