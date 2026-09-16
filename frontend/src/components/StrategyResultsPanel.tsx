import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StrategyResult } from "../api/types";

interface Props {
  results: StrategyResult[];
}

const BAR_COLOR = "#3b82f6";
const FASTEST_COLOR = "#22c55e";

export default function StrategyResultsPanel({ results }: Props) {
  if (results.length === 0) return null;

  const fastestMean = Math.min(...results.map((r) => r.mean_s));
  const chartData = results.map((r) => ({
    name: r.strategy,
    mean_s: r.mean_s,
    // recharts ErrorBar expects [lower_delta, upper_delta] relative to the value
    errorRange: [r.mean_s - r.p10_s, r.p90_s - r.mean_s] as [number, number],
    isFastest: r.mean_s === fastestMean,
  }));

  return (
    <section className="panel">
      <h2>Comparison results</h2>
      <ResponsiveContainer width="100%" height={Math.max(180, results.length * 60)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={["dataMin - 15", "dataMax + 15"]}
            tickFormatter={(v: number) => `${Math.round(v)}s`}
          />
          <YAxis type="category" dataKey="name" width={110} />
          <Tooltip
            formatter={(value) => `${Number(value).toFixed(1)}s`}
            labelStyle={{ color: "#111" }}
          />
          <Bar dataKey="mean_s" radius={4}>
            <ErrorBar dataKey="errorRange" width={4} strokeWidth={1.5} stroke="#64748b" />
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.isFastest ? FASTEST_COLOR : BAR_COLOR} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <table className="results-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Stops</th>
            <th>Mean</th>
            <th>Median</th>
            <th>P10–P90</th>
            <th>P(fastest)</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.strategy} className={r.mean_s === fastestMean ? "row-fastest" : undefined}>
              <td>{r.strategy}</td>
              <td>{r.n_stops}</td>
              <td>{r.mean_s.toFixed(1)}s</td>
              <td>{r.median_s.toFixed(1)}s</td>
              <td>
                {r.p10_s.toFixed(1)}s – {r.p90_s.toFixed(1)}s
              </td>
              <td>{(r.prob_fastest * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
