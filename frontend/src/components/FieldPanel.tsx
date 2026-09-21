import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DriverPositionProbability, RaceSummary } from "../api/types";
import { teamColor } from "../teamColors";

interface Props {
  race: RaceSummary | null;
  onSimulate: () => void;
  loading: boolean;
  results: DriverPositionProbability[] | null;
}

export default function FieldPanel({ race, onSimulate, loading, results }: Props) {
  const driverTeam: Record<string, string> = {};
  race?.drivers.forEach((d) => {
    driverTeam[d.driver] = d.team;
  });

  return (
    <section className="panel">
      <h2>Field simulation</h2>
      <p className="hint">
        Simulates every finisher's actual historical strategy together to estimate finishing
        position probabilities.
      </p>
      <button disabled={loading} onClick={onSimulate}>
        {loading ? "Simulating field…" : "Simulate field"}
      </button>

      {results && (
        <>
          <ResponsiveContainer width="100%" height={Math.max(200, results.length * 26)}>
            <BarChart data={toChartData(results)} layout="vertical" margin={{ left: 24, right: 24 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
              <XAxis
                type="number"
                domain={[0, 1]}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                stroke="var(--text-dim)"
                fontSize={12}
              />
              <YAxis
                type="category"
                dataKey="driver"
                width={50}
                tick={(props) => <DriverTick {...props} color={teamColor(driverTeam[props.payload.value])} />}
              />
              <Tooltip
                cursor={{ fill: "rgba(255, 255, 255, 0.04)" }}
                content={(props) => <FieldTooltip {...props} driverTeam={driverTeam} />}
              />
              <Bar dataKey="prob_win" radius={3} name="P(win)">
                {toChartData(results).map((entry) => (
                  <Cell key={entry.driver} fill={teamColor(driverTeam[entry.driver])} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <table className="results-table">
            <thead>
              <tr>
                <th>Driver</th>
                <th>Expected finish</th>
                <th>P(win)</th>
                <th>P(podium)</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.driver}>
                  <td style={{ color: teamColor(driverTeam[r.driver]), fontWeight: 700 }}>{r.driver}</td>
                  <td>{r.expected_position.toFixed(1)}</td>
                  <td>{(r.prob_win * 100).toFixed(1)}%</td>
                  <td>{(r.prob_podium * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function DriverTick({ x, y, payload, color }: { x: number; y: number; payload: { value: string }; color: string }) {
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fill={color} fontSize={12} fontWeight={700}>
      {payload.value}
    </text>
  );
}

interface FieldTooltipProps {
  active?: boolean;
  payload?: { payload: DriverPositionProbability }[];
  driverTeam: Record<string, string>;
}

function FieldTooltip({ active, payload, driverTeam }: FieldTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  const color = teamColor(driverTeam[d.driver]);
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${color}`,
        borderRadius: 3,
        padding: "8px 12px",
        fontSize: "0.8rem",
        minWidth: 150,
      }}
    >
      <div style={{ color, fontWeight: 700, marginBottom: 4 }}>
        {d.driver}
        {driverTeam[d.driver] && <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> · {driverTeam[d.driver]}</span>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--text)" }}>
        <span style={{ color: "var(--text-dim)" }}>Expected finish</span>
        <span>P{d.expected_position.toFixed(1)}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--text)" }}>
        <span style={{ color: "var(--text-dim)" }}>P(win)</span>
        <span>{(d.prob_win * 100).toFixed(1)}%</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--text)" }}>
        <span style={{ color: "var(--text-dim)" }}>P(podium)</span>
        <span>{(d.prob_podium * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

function toChartData(results: DriverPositionProbability[]) {
  return [...results].sort((a, b) => a.expected_position - b.expected_position).slice(0, 12);
}
