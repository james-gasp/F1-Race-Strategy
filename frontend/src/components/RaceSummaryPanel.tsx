import type { RaceSummary } from "../api/types";

interface Props {
  race: RaceSummary;
}

export default function RaceSummaryPanel({ race }: Props) {
  const compounds = Object.keys(race.pace_model.compound_offset);

  return (
    <section className="panel">
      <h2>
        {race.event} {race.year}
      </h2>
      <div className="stat-row">
        <div className="stat">
          <span className="stat-value">{race.total_race_laps}</span>
          <span className="stat-label">race laps</span>
        </div>
        <div className="stat">
          <span className="stat-value">{race.pit_loss_s.toFixed(1)}s</span>
          <span className="stat-label">pit lane loss</span>
        </div>
        <div className="stat">
          <span className="stat-value">{race.pace_model.fuel_effect_per_lap.toFixed(3)}s/lap</span>
          <span className="stat-label">fuel burn-off effect</span>
        </div>
      </div>

      <table className="model-table">
        <thead>
          <tr>
            <th>Compound</th>
            <th>Pace offset (s)</th>
            <th>Deg. (s/lap)</th>
            <th>Deg. (s/lap²)</th>
          </tr>
        </thead>
        <tbody>
          {compounds.map((c) => (
            <tr key={c}>
              <td>
                <span className={`compound-dot compound-${c.toLowerCase()}`} />
                {c}
              </td>
              <td>{race.pace_model.compound_offset[c].toFixed(3)}</td>
              <td>{race.pace_model.deg_linear[c].toFixed(4)}</td>
              <td>{race.pace_model.deg_quad[c].toFixed(5)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        Model fit from real lap data, relative to {race.pace_model.reference_compound} on the
        reference driver's pace. Residual std: {race.pace_model.residual_std.toFixed(3)}s/lap.
      </p>
    </section>
  );
}
