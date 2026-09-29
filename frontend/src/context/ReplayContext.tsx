import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
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
  // Everything fetched for a race is stored together with the race it belongs
  // to, and only exposed while that race is still the selected one -- so when
  // the user switches races, the previous race's frames/circuit can never be
  // rendered against the new race while its data is in flight.
  const raceKey = year != null && event != null ? `${year}/${event}` : null;
  const [loaded, setLoaded] = useState<{
    key: string;
    frames: LapFrame[];
    circuit: CircuitOutline | null;
    weather: WeatherSample[];
    error: string | null;
  } | null>(null);
  const [lapState, setLapState] = useState({ key: raceKey, index: 0, playing: false });
  const [speedMs, setSpeedMs] = useState(800);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (year == null || event == null) return;
    const key = `${year}/${event}`;
    let cancelled = false;

    Promise.all([
      getReplayFrames(year, event),
      getCircuitOutline(year, event).catch(() => null),
      getWeather(year, event).catch(() => ({ samples: [] })),
    ])
      .then(([replay, circuitOutline, weatherResp]) => {
        if (cancelled) return;
        setLoaded({ key, frames: replay.frames, circuit: circuitOutline, weather: weatherResp.samples, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Failed to load replay data";
        setLoaded({ key, frames: [], circuit: null, weather: [], error: message });
      });

    return () => {
      cancelled = true;
    };
  }, [year, event]);

  const current = loaded != null && loaded.key === raceKey ? loaded : null;
  const loading = raceKey != null && current == null;
  const error = current?.error ?? null;
  const circuit = current?.circuit ?? null;
  const frames = useMemo(() => current?.frames ?? [], [current]);
  const weather = useMemo(() => current?.weather ?? [], [current]);

  // Lap position/playback also resets per race: a lap index from the old
  // race would otherwise carry over (and keep playing) on the new one.
  const lapIndex = lapState.key === raceKey ? lapState.index : 0;
  const isPlaying = lapState.key === raceKey && lapState.playing;
  const setLapIndexState = useCallback(
    (update: (i: number) => number) =>
      setLapState((s) => {
        const base = s.key === raceKey ? s : { key: raceKey, index: 0, playing: false };
        return { ...base, index: update(base.index) };
      }),
    [raceKey],
  );
  const setIsPlaying = useCallback(
    (playing: boolean) =>
      setLapState((s) => ({ ...(s.key === raceKey ? s : { key: raceKey, index: 0 }), playing })),
    [raceKey],
  );

  const effectiveSpeedMs = Math.max(speedMs, MIN_LAP_MS);

  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;
    intervalRef.current = setInterval(() => {
      setLapState((s) => {
        if (s.key !== raceKey) return s;
        return s.index >= frames.length - 1 ? { ...s, playing: false } : { ...s, index: s.index + 1 };
      });
    }, effectiveSpeedMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, effectiveSpeedMs, frames.length, raceKey]);

  const setLapIndex = useCallback(
    (index: number) => {
      setLapIndexState(() => Math.max(0, Math.min(index, Math.max(frames.length - 1, 0))));
    },
    [frames.length, setLapIndexState],
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
