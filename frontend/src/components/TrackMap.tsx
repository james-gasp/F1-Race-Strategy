import { useEffect, useMemo, useRef, useState } from "react";
import type { DriverSummary, LapFrame } from "../api/types";
import { useReplay } from "../context/ReplayContext";
import { teamColor } from "../teamColors";

// Grid slots are 8m apart; pole sits a few metres behind the line.
const GRID_SLOT_M = 8;
const POLE_OFFSET_M = 5;

// Typical lap time for converting between a time gap and a fraction of a lap:
// the median complete lap of the race, so a slow lap 1 or safety-car lap
// doesn't skew every car's spacing.
function typicalLapSeconds(frames: LapFrame[], fallback: number): number {
  const times: number[] = [];
  for (const f of frames) {
    for (const d of f.drivers) {
      if (d.sector1_s != null && d.sector2_s != null && d.sector3_s != null) {
        times.push(d.sector1_s + d.sector2_s + d.sector3_s);
      }
    }
  }
  if (times.length === 0) return fallback;
  times.sort((a, b) => a - b);
  return times[Math.floor(times.length / 2)];
}

export default function TrackMap({ drivers }: { drivers: DriverSummary[] }) {
  const { circuit, frames, currentFrame, isPlaying, effectiveSpeedMs, lapIndex, loading } = useReplay();
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);

  // Animate the leader's progress around the lap, resetting whenever the lap
  // changes. Every other driver's dot is offset behind the leader by its
  // real `gap_to_leader_s` -- no per-driver telemetry needed for the base
  // animation, only the leader's actual lap-time-derived scale.
  //
  // Orbit duration matches `effectiveSpeedMs`, the same (floored) interval
  // the replay clock uses to advance the lap index, so the orbit always
  // finishes exactly as the next lap's frame arrives instead of getting cut
  // off mid-lap (which looked like the cars jumping/skipping ahead).
  useEffect(() => {
    setProgress(0);
    if (!isPlaying) return;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / effectiveSpeedMs);
      setProgress(t);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [lapIndex, isPlaying, effectiveSpeedMs]);

  const bounds = useMemo(() => {
    if (!circuit) return null;
    const xs = circuit.points.map((p) => p[0]);
    const ys = circuit.points.map((p) => p[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const pad = Math.max(maxX - minX, maxY - minY) * 0.1;
    return {
      minX: minX - pad,
      minY: minY - pad,
      width: maxX - minX + pad * 2,
      height: maxY - minY + pad * 2,
    };
  }, [circuit]);

  if (loading) {
    return (
      <section className="panel track-map-panel">
        <h2>Track Map</h2>
        <p className="hint">Loading circuit…</p>
      </section>
    );
  }

  if (!circuit || !bounds) {
    return (
      <section className="panel track-map-panel">
        <h2>Track Map</h2>
        <p className="hint">No circuit telemetry available for this race.</p>
      </section>
    );
  }

  const pathD = `M ${circuit.points.map((p) => `${p[0]},${p[1]}`).join(" L ")} Z`;
  const n = circuit.points.length;
  const strokeWidth = bounds.width * 0.006;
  const dotRadius = bounds.width * 0.011;
  // ~200 km/h average if no lap has complete sector times.
  const lapS = typicalLapSeconds(frames, circuit.length_m / 55);

  // Where each car is at the *start* of the displayed lap, as a time gap
  // behind the leader: the starting grid for lap 1, else the previous lap's
  // finishing gaps. The orbit then eases each gap towards this lap's
  // finishing gap, so a lap's animation ends exactly where the next begins.
  const startGaps = new Map<string, number>();
  if (lapIndex === 0) {
    const maxGrid = Math.max(0, ...drivers.map((d) => d.grid_position));
    for (const d of drivers) {
      // Grid position 0 = pit-lane start: line those cars up behind the grid.
      const slot = d.grid_position > 0 ? d.grid_position : maxGrid + 1;
      const metres = POLE_OFFSET_M + (slot - 1) * GRID_SLOT_M;
      startGaps.set(d.driver, (metres / circuit.length_m) * lapS);
    }
  } else {
    for (const d of frames[lapIndex - 1]?.drivers ?? []) {
      if (d.gap_to_leader_s != null) startGaps.set(d.driver, d.gap_to_leader_s);
    }
  }

  function dotPosition(driver: string, endGap: number | null): [number, number] {
    const start = startGaps.get(driver) ?? endGap ?? 0;
    const end = endGap ?? start;
    const gap = start + (end - start) * progress;
    let p = (progress - gap / lapS) % 1;
    if (p < 0) p += 1;
    // Interpolate between outline points so dots glide rather than step.
    const f = p * n;
    const i = Math.floor(f) % n;
    const j = (i + 1) % n;
    const t = f - Math.floor(f);
    const a = circuit!.points[i];
    const b = circuit!.points[j];
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  }

  // Draw the leader last so it sits on top of any car it's lapping.
  const ordered = [...(currentFrame?.drivers ?? [])].reverse();

  return (
    <section className="panel track-map-panel">
      <h2>
        Track Map{" "}
        {currentFrame && <span className="hint" style={{ display: "inline" }}>— lap {currentFrame.lap_number}</span>}
      </h2>
      <svg
        viewBox={`${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`}
        className="track-map-svg"
      >
        <path d={pathD} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} strokeLinejoin="round" />
        {ordered.map((d) => {
          const [x, y] = dotPosition(d.driver, d.gap_to_leader_s);
          return (
            <g key={d.driver} transform={`translate(${x}, ${y})`}>
              <circle r={dotRadius} fill={teamColor(d.team)} stroke="#0b0e14" strokeWidth={dotRadius * 0.25} />
              <text
                y={-dotRadius * 1.8}
                fontSize={dotRadius * 1.3}
                textAnchor="middle"
                fill="var(--text)"
                fontWeight={600}
              >
                {d.driver}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
