import { useState } from "react";
import type { RaceSummary, StintIn, StrategyIn } from "../api/types";

interface Props {
  race: RaceSummary;
  onCompare: (strategies: StrategyIn[]) => void;
  loading: boolean;
}

const COMPOUNDS = ["SOFT", "MEDIUM", "HARD"];

function emptyStrategy(name: string, driver: string, totalLaps: number): StrategyIn {
  const half = Math.floor(totalLaps / 2);
  return {
    name,
    driver,
    stints: [
      { compound: "MEDIUM", laps: half, start_tyre_life: 1 },
      { compound: "HARD", laps: totalLaps - half, start_tyre_life: 1 },
    ],
  };
}

export default function StrategyBuilder({ race, onCompare, loading }: Props) {
  const defaultDriver = race.drivers[0]?.driver ?? "VER";
  const [strategies, setStrategies] = useState<StrategyIn[]>(() => [
    emptyStrategy("1-stop", defaultDriver, race.total_race_laps),
    {
      name: "2-stop",
      driver: defaultDriver,
      stints: [
        { compound: "SOFT", laps: Math.floor(race.total_race_laps / 3), start_tyre_life: 1 },
        { compound: "SOFT", laps: Math.floor(race.total_race_laps / 3), start_tyre_life: 1 },
        {
          compound: "HARD",
          laps: race.total_race_laps - 2 * Math.floor(race.total_race_laps / 3),
          start_tyre_life: 1,
        },
      ],
    },
  ]);

  const updateStrategy = (index: number, next: StrategyIn) => {
    setStrategies((prev) => prev.map((s, i) => (i === index ? next : s)));
  };

  const addStrategy = () => {
    setStrategies((prev) => [
      ...prev,
      emptyStrategy(`strategy-${prev.length + 1}`, defaultDriver, race.total_race_laps),
    ]);
  };

  const removeStrategy = (index: number) => {
    setStrategies((prev) => prev.filter((_, i) => i !== index));
  };

  const strategyLaps = (s: StrategyIn) => s.stints.reduce((sum, st) => sum + st.laps, 0);

  return (
    <section className="panel">
      <h2>Strategy builder</h2>
      <p className="hint">
        Compare candidate strategies for {race.event} {race.year} ({race.total_race_laps} laps).
      </p>
      {strategies.map((strategy, i) => {
        const laps = strategyLaps(strategy);
        const lapsMismatch = laps !== race.total_race_laps;
        return (
          <div className="strategy-card" key={i}>
            <div className="strategy-card-header">
              <input
                className="strategy-name-input"
                value={strategy.name}
                onChange={(e) => updateStrategy(i, { ...strategy, name: e.target.value })}
              />
              <select
                value={strategy.driver}
                onChange={(e) => updateStrategy(i, { ...strategy, driver: e.target.value })}
              >
                {race.drivers.map((d) => (
                  <option key={d.driver} value={d.driver}>
                    {d.driver}
                  </option>
                ))}
              </select>
              <button className="ghost-button" onClick={() => removeStrategy(i)}>
                Remove
              </button>
            </div>

            {strategy.stints.map((stint, si) => (
              <StintRow
                key={si}
                stint={stint}
                onChange={(next) => {
                  const stints = strategy.stints.map((s, j) => (j === si ? next : s));
                  updateStrategy(i, { ...strategy, stints });
                }}
                onRemove={
                  strategy.stints.length > 1
                    ? () => {
                        const stints = strategy.stints.filter((_, j) => j !== si);
                        updateStrategy(i, { ...strategy, stints });
                      }
                    : undefined
                }
              />
            ))}
            <div className="strategy-card-footer">
              <button
                className="ghost-button"
                onClick={() =>
                  updateStrategy(i, {
                    ...strategy,
                    stints: [...strategy.stints, { compound: "MEDIUM", laps: 10, start_tyre_life: 1 }],
                  })
                }
              >
                + Add stint
              </button>
              <span className={lapsMismatch ? "laps-warning" : "laps-ok"}>
                {laps} / {race.total_race_laps} laps
              </span>
            </div>
          </div>
        );
      })}

      <div className="row">
        <button className="ghost-button" onClick={addStrategy}>
          + Add strategy
        </button>
        <button disabled={loading || strategies.length === 0} onClick={() => onCompare(strategies)}>
          {loading ? "Simulating…" : "Compare strategies"}
        </button>
      </div>
    </section>
  );
}

function StintRow({
  stint,
  onChange,
  onRemove,
}: {
  stint: StintIn;
  onChange: (s: StintIn) => void;
  onRemove?: () => void;
}) {
  return (
    <div className="stint-row">
      <select value={stint.compound} onChange={(e) => onChange({ ...stint, compound: e.target.value })}>
        {COMPOUNDS.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <label className="inline-label">
        laps
        <input
          type="number"
          min={1}
          value={stint.laps}
          onChange={(e) => onChange({ ...stint, laps: Number(e.target.value) })}
        />
      </label>
      <label className="inline-label">
        start tire age
        <input
          type="number"
          min={1}
          value={stint.start_tyre_life}
          onChange={(e) => onChange({ ...stint, start_tyre_life: Number(e.target.value) })}
        />
      </label>
      {onRemove && (
        <button className="ghost-button small" onClick={onRemove}>
          ×
        </button>
      )}
    </div>
  );
}
