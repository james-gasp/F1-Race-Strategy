import { useRef, useState } from "react";
import { ApiError, compareStrategies, getRace, optimizePitStop, simulateField } from "../api/client";
import type {
  DriverPositionProbability,
  RaceSummary,
  StrategyIn,
  StrategyResult,
} from "../api/types";
import FieldPanel from "../components/FieldPanel";
import OptimizerPanel from "../components/OptimizerPanel";
import RaceSelector from "../components/RaceSelector";
import RaceSummaryPanel from "../components/RaceSummaryPanel";
import ReplayControls from "../components/ReplayControls";
import StrategyBuilder from "../components/StrategyBuilder";
import StrategyResultsPanel from "../components/StrategyResultsPanel";
import TimingTower from "../components/TimingTower";
import TrackMap from "../components/TrackMap";
import WeatherPanel from "../components/WeatherPanel";
import { ReplayProvider } from "../context/ReplayContext";
import AppShell from "../components/AppShell";
import type { View } from "../components/AppShell";
import TelemetryView from "./TelemetryView";

export default function RaceControl() {
  const [race, setRace] = useState<RaceSummary | null>(null);
  const [pendingRace, setPendingRace] = useState<{ year: number; event: string } | null>(null);
  const raceLoading = pendingRace != null;
  // Bumped on every race load; any response (race or simulation) that comes
  // back after the user has moved on to another race is dropped.
  const loadId = useRef(0);
  const [raceError, setRaceError] = useState<string | null>(null);
  const [view, setView] = useState<View>("telemetry");

  const [compareResults, setCompareResults] = useState<StrategyResult[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [fieldResults, setFieldResults] = useState<DriverPositionProbability[] | null>(null);
  const [fieldLoading, setFieldLoading] = useState(false);

  const [optRecommended, setOptRecommended] = useState<StrategyResult | null>(null);
  const [optCandidates, setOptCandidates] = useState<StrategyResult[] | null>(null);
  const [optLoading, setOptLoading] = useState(false);
  const [optError, setOptError] = useState<string | null>(null);

  const loadRace = async (year: number, event: string) => {
    const id = ++loadId.current;
    setPendingRace({ year, event });
    setRaceError(null);
    setCompareResults([]);
    setFieldResults(null);
    setOptRecommended(null);
    setOptCandidates(null);
    try {
      const summary = await getRace(year, event);
      if (id !== loadId.current) return;
      setRace(summary);
    } catch (err) {
      if (id !== loadId.current) return;
      setRaceError(err instanceof ApiError ? err.message : "Failed to load race");
    } finally {
      if (id === loadId.current) setPendingRace(null);
    }
  };

  const handleCompare = async (strategies: StrategyIn[]) => {
    if (!race) return;
    const id = loadId.current;
    setCompareLoading(true);
    setCompareError(null);
    try {
      const res = await compareStrategies({
        year: race.year,
        event: race.event,
        strategies,
        n_sims: 2000,
        seed: 0,
      });
      if (id === loadId.current) setCompareResults(res.results);
    } catch (err) {
      setCompareError(err instanceof ApiError ? err.message : "Comparison failed");
    } finally {
      setCompareLoading(false);
    }
  };

  const handleSimulateField = async () => {
    if (!race) return;
    const id = loadId.current;
    setFieldLoading(true);
    try {
      const res = await simulateField({ year: race.year, event: race.event, n_sims: 2000, seed: 0 });
      if (id === loadId.current) setFieldResults(res.drivers);
    } finally {
      setFieldLoading(false);
    }
  };

  const handleOptimize = async (params: {
    driver: string;
    current_compound: string;
    current_tyre_life: number;
    next_lap_number: number;
  }) => {
    if (!race) return;
    const id = loadId.current;
    setOptLoading(true);
    setOptError(null);
    setOptRecommended(null);
    setOptCandidates(null);
    try {
      const res = await optimizePitStop({
        year: race.year,
        event: race.event,
        ...params,
        total_race_laps: race.total_race_laps,
        lap_step: 2,
        n_sims: 1000,
        seed: 0,
      });
      if (id !== loadId.current) return;
      setOptRecommended(res.recommended);
      setOptCandidates(res.candidates);
    } catch (err) {
      setOptError(err instanceof ApiError ? err.message : "Optimization failed");
    } finally {
      setOptLoading(false);
    }
  };

  return (
    <ReplayProvider year={race?.year ?? null} event={race?.event ?? null}>
      <AppShell race={race} view={view} onView={setView} onLoadRace={loadRace} raceLoading={raceLoading}>
        {raceError && <p className="error-text mb-3">{raceError}</p>}

        {pendingRace && race && (
          <div className="race-loading">
            <span className="spinner" />
            <div>
              <strong>
                Loading {pendingRace.event} {pendingRace.year}…
              </strong>
              <p className="hint m-0">
                The first load of a race downloads its timing data from FastF1 and can take up to a minute.
              </p>
            </div>
          </div>
        )}

        {!race && (
          <div className="landing">
            <span className="eyebrow">Race Control · Pit Wall</span>
            <h1>Analyse every lap like a race engineer.</h1>
            <p>
              Overlay real FastF1 telemetry lap-against-lap, replay the race from the pit wall, and
              run Monte Carlo strategy simulations for the whole field.
            </p>
            <RaceSelector onLoad={loadRace} loading={raceLoading} />
            {pendingRace && (
              <p className="hint m-0 flex items-center gap-2">
                <span className="spinner" /> Loading {pendingRace.event} {pendingRace.year}… the first load of a race
                downloads its data from FastF1 and can take up to a minute.
              </p>
            )}
          </div>
        )}

        {race && !pendingRace && view === "telemetry" && <TelemetryView race={race} />}

        {race && !pendingRace && view === "timing" && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <div className="lg:col-span-8">
                <TrackMap drivers={race.drivers} />
              </div>
              <div className="flex flex-col gap-4 lg:col-span-4">
                <WeatherPanel />
                <ReplayControls />
              </div>
            </div>
            <TimingTower />
          </div>
        )}

        {race && !pendingRace && view === "strategy" && (
          <div className="flex flex-col gap-4">
            <RaceSummaryPanel race={race} />
            <StrategyBuilder race={race} onCompare={handleCompare} loading={compareLoading} />
            {compareError && <p className="error-text">{compareError}</p>}
            <StrategyResultsPanel results={compareResults} />
            <FieldPanel race={race} onSimulate={handleSimulateField} loading={fieldLoading} results={fieldResults} />
            <OptimizerPanel
              race={race}
              onOptimize={handleOptimize}
              loading={optLoading}
              error={optError}
              recommended={optRecommended}
              candidates={optCandidates}
            />
          </div>
        )}
      </AppShell>
    </ReplayProvider>
  );
}
