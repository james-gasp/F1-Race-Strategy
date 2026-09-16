import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DriverPositionProbability } from "../api/types";

interface Props {
  onSimulate: () => void;
  loading: boolean;
  results: DriverPositionProbability[] | null;
}

export default function FieldPanel({ onSimulate, loading, results }: Props) {
  return (
    <section className="panel">
      <h2>Field simulation</h2>
      <p className="hint">
        Simulates every finisher's actual historical strategy together to estimate finishing
        position probabilities — this is what makes it a strategy simulator rather than a
        single-car lap-time calculator.
      </p>
      <button disabled={loading} onClick={onSimulate}>
        {loading ? "Simulating field…" : "Simulate field"}
      </button>

      {results && (
        <>
          <ResponsiveContainer width="100%" height={Math.max(200, results.length * 26)}>
            <BarChart data={toChartData(results)} layout="vertical" margin={{ left: 24, right: 24 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 1]}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
              />
              <YAxis type="category" dataKey="driver" width={50} />
              <Tooltip formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`} />
              <Bar dataKey="prob_win" fill="#3b82f6" radius={3} name="P(win)" />
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
                  <td>{r.driver}</td>
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

function toChartData(results: DriverPositionProbability[]) {
  return [...results].sort((a, b) => a.expected_position - b.expected_position).slice(0, 12);
}
