import { useReplay } from "../context/ReplayContext";
import type { DriverFrame } from "../api/types";
import { teamColor } from "../teamColors";

type SectorKey = "sector1_s" | "sector2_s" | "sector3_s";
const SECTOR_KEYS: SectorKey[] = ["sector1_s", "sector2_s", "sector3_s"];
type TimeKey = SectorKey | "lap";

function formatGap(gap: number | null): string {
  if (gap == null) return "";
  return gap === 0 ? "LEADER" : `+${gap.toFixed(1)}`;
}

function formatSector(value: number | null): string {
  if (value == null) return "—";
  return value.toFixed(3);
}

// F1-style lap time format, e.g. 92.184s -> "1:32.184".
function formatLapTime(value: number | null): string {
  if (value == null) return "—";
  const minutes = Math.floor(value / 60);
  const seconds = value - minutes * 60;
  return `${minutes}:${seconds.toFixed(3).padStart(6, "0")}`;
}

// Broadcast pit-wall convention: purple = fastest of the whole session, green =
// driver's own personal best (but not the overall fastest), yellow = fastest set
// on this lap specifically. Filled as cell backgrounds, the way a real timing
// tower colors them, rather than just tinting the text.
function classify(
  value: number | null,
  sessionBest: number | null,
  personalBest: number | null,
  lapBest: number | null,
): string {
  if (value == null) return "";
  if (sessionBest != null && value === sessionBest) return "tt-cell-purple";
  if (personalBest != null && value === personalBest) return "tt-cell-green";
  if (lapBest != null && value === lapBest) return "tt-cell-yellow";
  return "";
}

export default function TimingTower() {
  const { currentFrame, frames, lapIndex, loading } = useReplay();

  if (loading) {
    return (
      <section className="panel timing-tower">
        <h2>Timing Tower</h2>
        <p className="hint">Loading replay…</p>
      </section>
    );
  }

  if (!currentFrame) {
    return (
      <section className="panel timing-tower">
        <h2>Timing Tower</h2>
        <p className="hint">Load a race to see live timing.</p>
      </section>
    );
  }

  const sessionBest: Record<TimeKey, number | null> = {
    sector1_s: null,
    sector2_s: null,
    sector3_s: null,
    lap: null,
  };
  const personalBest: Record<string, Record<TimeKey, number | null>> = {};
  const lapBest: Record<TimeKey, number | null> = {
    sector1_s: null,
    sector2_s: null,
    sector3_s: null,
    lap: null,
  };

  frames.slice(0, lapIndex + 1).forEach((frame) => {
    const isCurrentLap = frame.lap_number === currentFrame.lap_number;
    frame.drivers.forEach((d) => {
      if (d.sector1_s == null || d.sector2_s == null || d.sector3_s == null) return;
      const lapTime = d.sector1_s + d.sector2_s + d.sector3_s;
      if (!personalBest[d.driver]) {
        personalBest[d.driver] = { sector1_s: null, sector2_s: null, sector3_s: null, lap: null };
      }
      const pb = personalBest[d.driver];

      for (const key of SECTOR_KEYS) {
        const value = d[key] as number;
        if (sessionBest[key] == null || value < sessionBest[key]!) sessionBest[key] = value;
        if (pb[key] == null || value < pb[key]!) pb[key] = value;
        if (isCurrentLap && (lapBest[key] == null || value < lapBest[key]!)) lapBest[key] = value;
      }
      if (sessionBest.lap == null || lapTime < sessionBest.lap) sessionBest.lap = lapTime;
      if (pb.lap == null || lapTime < pb.lap) pb.lap = lapTime;
      if (isCurrentLap && (lapBest.lap == null || lapTime < lapBest.lap)) lapBest.lap = lapTime;
    });
  });

  function statusOf(d: DriverFrame): { label: string; className: string } {
    if (d.pit_this_lap) return { label: "IN PIT", className: "tt-status-pit" };
    return { label: "ON TRACK", className: "tt-status-track" };
  }

  return (
    <section className="panel timing-tower">
      <h2>Timing Tower{` — Lap ${currentFrame.lap_number}`}</h2>
      <div className="table-scroll timing-tower-scroll">
        <table className="timing-tower-table">
          <thead>
            <tr>
              <th>Pos</th>
              <th>Driver</th>
              <th>Gap</th>
              <th>Int</th>
              <th>Tyre</th>
              <th>Sector 1</th>
              <th>Sector 2</th>
              <th>Sector 3</th>
              <th>Lap Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {currentFrame.drivers.map((d) => {
              const pb = personalBest[d.driver];
              const hasSectors = d.sector1_s != null && d.sector2_s != null && d.sector3_s != null;
              const lapTime = hasSectors ? d.sector1_s! + d.sector2_s! + d.sector3_s! : null;
              const status = statusOf(d);
              const color = teamColor(d.team);
              return (
                <tr key={d.driver}>
                  <td className="tt-pos">{d.position}</td>
                  <td className="tt-driver" style={{ borderLeft: `3px solid ${color}` }}>
                    <strong style={{ color }}>{d.driver}</strong>
                    <span className="hint tt-team">{d.team}</span>
                  </td>
                  <td className="tt-gap">{formatGap(d.gap_to_leader_s)}</td>
                  <td className="tt-gap">{formatGap(d.gap_ahead_s)}</td>
                  <td className="tt-tyre">
                    {d.compound && (
                      <>
                        <span className={`compound-dot compound-${d.compound.toLowerCase()}`} />
                        {d.compound[0]}
                        {d.tyre_life != null ? Math.round(d.tyre_life) : "?"}
                      </>
                    )}
                  </td>
                  <td className={classify(d.sector1_s, sessionBest.sector1_s, pb?.sector1_s ?? null, lapBest.sector1_s)}>
                    {formatSector(d.sector1_s)}
                  </td>
                  <td className={classify(d.sector2_s, sessionBest.sector2_s, pb?.sector2_s ?? null, lapBest.sector2_s)}>
                    {formatSector(d.sector2_s)}
                  </td>
                  <td className={classify(d.sector3_s, sessionBest.sector3_s, pb?.sector3_s ?? null, lapBest.sector3_s)}>
                    {formatSector(d.sector3_s)}
                  </td>
                  <td className={classify(lapTime, sessionBest.lap, pb?.lap ?? null, lapBest.lap)}>
                    {formatLapTime(lapTime)}
                  </td>
                  <td>
                    <span className={`tt-status ${status.className}`}>{status.label}</span>
                    {d.undercut_threat?.is_threat && (
                      <span className="undercut-badge" title={`${d.undercut_threat.laps_to_undercut?.toFixed(1)} laps to undercut`}>
                        UC
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
