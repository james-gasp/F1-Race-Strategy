import { useState } from "react";
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

export default function RaceControl() {
  const [race, setRace] = useState<RaceSummary | null>(null);
  const [raceLoading, setRaceLoading] = useState(false);
  const [raceError, setRaceError] = useState<string | null>(null);

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
    setRaceLoading(true);
    setRaceError(null);
    setCompareResults([]);
    setFieldResults(null);
    setOptRecommended(null);
    setOptCandidates(null);
    try {
      const summary = await getRace(year, event);
      setRace(summary);
    } catch (err) {
      setRaceError(err instanceof ApiError ? err.message : "Failed to load race");
      setRace(null);
    } finally {
      setRaceLoading(false);
    }
  };

  const handleCompare = async (strategies: StrategyIn[]) => {
    if (!race) return;
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
      setCompareResults(res.results);
    } catch (err) {
      setCompareError(err instanceof ApiError ? err.message : "Comparison failed");
    } finally {
      setCompareLoading(false);
    }
  };

  const handleSimulateField = async () => {
    if (!race) return;
    setFieldLoading(true);
    try {
      const res = await simulateField({ year: race.year, event: race.event, n_sims: 2000, seed: 0 });
      setFieldResults(res.drivers);
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
      <div className="mx-auto flex max-w-[1400px] flex-col gap-5 px-4 pb-16 pt-6">
        <header className="app-header flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <span className="eyebrow">Race Control · Pit Wall</span>
            <h1 className="m-0">F1 Race Control</h1>
            <p className="m-0">
              FastF1-calibrated race replay, live pit-wall telemetry, and Monte Carlo strategy simulation.
            </p>
          </div>
        </header>

        <RaceSelector onLoad={loadRace} loading={raceLoading} />
        {raceError && <p className="error-text">{raceError}</p>}

        {race && (
          <>
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
              <div className="lg:col-span-8">
                <TrackMap />
              </div>
              <div className="lg:col-span-4">
                <WeatherPanel />
              </div>
            </div>

            <ReplayControls />

            <TimingTower />

            <section>
              <h2 className="mb-3 mt-2 border-l-3 border-(--accent) pl-2.5 text-[0.8rem] font-bold uppercase tracking-[0.08em] text-(--text)">
                Strategy Lab
              </h2>
              <div className="flex flex-col gap-5">
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
            </section>
          </>
        )}
      </div>
    </ReplayProvider>
  );
}
