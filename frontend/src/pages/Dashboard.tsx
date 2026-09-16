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
import StrategyBuilder from "../components/StrategyBuilder";
import StrategyResultsPanel from "../components/StrategyResultsPanel";

export default function Dashboard() {
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
    <div className="dashboard">
      <header className="app-header">
        <h1>F1 Race Strategy Simulator</h1>
        <p>FastF1-calibrated Monte Carlo strategy simulation and optimization.</p>
      </header>

      <RaceSelector onLoad={loadRace} loading={raceLoading} />
      {raceError && <p className="error-text">{raceError}</p>}

      {race && (
        <>
          <RaceSummaryPanel race={race} />
          <StrategyBuilder race={race} onCompare={handleCompare} loading={compareLoading} />
          {compareError && <p className="error-text">{compareError}</p>}
          <StrategyResultsPanel results={compareResults} />
          <FieldPanel onSimulate={handleSimulateField} loading={fieldLoading} results={fieldResults} />
          <OptimizerPanel
            race={race}
            onOptimize={handleOptimize}
            loading={optLoading}
            error={optError}
            recommended={optRecommended}
            candidates={optCandidates}
          />
        </>
      )}
    </div>
  );
}
