import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, getCircuitOutline, getReplayFrames, getWeather } from "../api/client";
import type { CircuitOutline, LapFrame, WeatherSample } from "../api/types";

interface ReplayContextValue {
  loading: boolean;
  error: string | null;
  circuit: CircuitOutline | null;
  frames: LapFrame[];
  weather: WeatherSample[];
  totalLaps: number;
  lapIndex: number;
  currentFrame: LapFrame | null;
  currentWeather: WeatherSample | null;
  isPlaying: boolean;
  speedMs: number;
  effectiveSpeedMs: number;
  setLapIndex: (index: number) => void;
  play: () => void;
  pause: () => void;
  setSpeedMs: (ms: number) => void;
}

const ReplayContext = createContext<ReplayContextValue | null>(null);

// Floor on how fast the replay clock is allowed to advance laps. The track
// map animates each lap's cars orbiting the circuit over this same span, so
// this also doubles as the minimum, comfortable orbit duration -- without a
// shared floor, raising playback speed would advance the lap index faster
// than the orbit animation can finish, making the cars jump/skip mid-lap.
const MIN_LAP_MS = 1800;

export function ReplayProvider({
  year,
  event,
  children,
}: {
  year: number | null;
  event: string | null;
  children: ReactNode;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [circuit, setCircuit] = useState<CircuitOutline | null>(null);
  const [frames, setFrames] = useState<LapFrame[]>([]);
  const [weather, setWeather] = useState<WeatherSample[]>([]);
  const [lapIndex, setLapIndexState] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(800);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (year == null || event == null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setIsPlaying(false);
    setLapIndexState(0);

    Promise.all([
      getReplayFrames(year, event),
      getCircuitOutline(year, event).catch(() => null),
      getWeather(year, event).catch(() => ({ samples: [] })),
    ])
      .then(([replay, circuitOutline, weatherResp]) => {
        if (cancelled) return;
        setFrames(replay.frames);
        setCircuit(circuitOutline);
        setWeather(weatherResp.samples);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Failed to load replay data");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [year, event]);

  const effectiveSpeedMs = Math.max(speedMs, MIN_LAP_MS);

  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;
    intervalRef.current = setInterval(() => {
      setLapIndexState((i) => {
        if (i >= frames.length - 1) {
          setIsPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, effectiveSpeedMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, effectiveSpeedMs, frames.length]);

  const setLapIndex = useCallback(
    (index: number) => {
      setLapIndexState(Math.max(0, Math.min(index, Math.max(frames.length - 1, 0))));
    },
    [frames.length],
  );

  const currentFrame = frames[lapIndex] ?? null;
  const currentWeather =
    currentFrame == null
      ? null
      : [...weather].reverse().find((w) => (w.lap_number ?? 0) <= currentFrame.lap_number) ??
        weather[0] ??
        null;

  const value: ReplayContextValue = {
    loading,
    error,
    circuit,
    frames,
    weather,
    totalLaps: frames.length,
    lapIndex,
    currentFrame,
    currentWeather,
    isPlaying,
    speedMs,
    effectiveSpeedMs,
    setLapIndex,
    play: () => frames.length > 0 && setIsPlaying(true),
    pause: () => setIsPlaying(false),
    setSpeedMs,
  };

  return <ReplayContext.Provider value={value}>{children}</ReplayContext.Provider>;
}

export function useReplay(): ReplayContextValue {
  const ctx = useContext(ReplayContext);
  if (!ctx) throw new Error("useReplay must be used within a ReplayProvider");
  return ctx;
}
