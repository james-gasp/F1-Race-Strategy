import { useState } from "react";
import type { RaceSummary, StrategyResult } from "../api/types";

interface Props {
  race: RaceSummary;
  onOptimize: (params: {
    driver: string;
    current_compound: string;
    current_tyre_life: number;
    next_lap_number: number;
  }) => void;
  loading: boolean;
  error: string | null;
  recommended: StrategyResult | null;
  candidates: StrategyResult[] | null;
}

const COMPOUNDS = ["SOFT", "MEDIUM", "HARD"];

export default function OptimizerPanel({ race, onOptimize, loading, error, recommended, candidates }: Props) {
  const [driver, setDriver] = useState(race.drivers[0]?.driver ?? "VER");
  const [compound, setCompound] = useState("MEDIUM");
  const [tyreLife, setTyreLife] = useState(15);
  const [lapNumber, setLapNumber] = useState(Math.floor(race.total_race_laps / 2));

  return (
    <section className="panel">
      <h2>Pit stop optimizer</h2>
      <p className="hint">
        "Should I pit now, and on what tire?" — ranks every legal pit-lap/compound choice for the
        rest of the race, enforcing F1's two-compound rule.
      </p>
      <div className="row">
        <label>
          Driver
          <select value={driver} onChange={(e) => setDriver(e.target.value)}>
            {race.drivers.map((d) => (
              <option key={d.driver} value={d.driver}>
                {d.driver}
              </option>
            ))}
          </select>
        </label>
        <label>
          Current compound
          <select value={compound} onChange={(e) => setCompound(e.target.value)}>
            {COMPOUNDS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tire age (laps)
          <input type="number" min={1} value={tyreLife} onChange={(e) => setTyreLife(Number(e.target.value))} />
        </label>
        <label>
          Current lap
          <input
            type="number"
            min={1}
            max={race.total_race_laps}
            value={lapNumber}
            onChange={(e) => setLapNumber(Number(e.target.value))}
          />
        </label>
        <button
          disabled={loading}
          onClick={() =>
            onOptimize({
              driver,
              current_compound: compound,
              current_tyre_life: tyreLife,
              next_lap_number: lapNumber,
            })
          }
        >
          {loading ? "Optimizing…" : "Recommend strategy"}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {recommended && (
        <div className="recommendation">
          Recommended: <strong>{recommended.strategy}</strong> — mean {recommended.mean_s.toFixed(1)}s,
          P(fastest option) {(recommended.prob_fastest * 100).toFixed(1)}%
        </div>
      )}

      {candidates && (
        <table className="results-table">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Mean</th>
              <th>P10–P90</th>
              <th>P(fastest)</th>
            </tr>
          </thead>
          <tbody>
            {candidates.slice(0, 8).map((c) => (
              <tr key={c.strategy} className={c === recommended ? "row-fastest" : undefined}>
                <td>{c.strategy}</td>
                <td>{c.mean_s.toFixed(1)}s</td>
                <td>
                  {c.p10_s.toFixed(1)}s – {c.p90_s.toFixed(1)}s
                </td>
                <td>{(c.prob_fastest * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
