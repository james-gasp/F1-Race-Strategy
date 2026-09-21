import { useEffect, useMemo, useRef, useState } from "react";
import type { DriverFrame } from "../api/types";
import { useReplay } from "../context/ReplayContext";
import { teamColor } from "../teamColors";

export default function TrackMap() {
  const { circuit, currentFrame, isPlaying, effectiveSpeedMs, lapIndex, loading } = useReplay();
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

  const leaderLapTimeS = (() => {
    const leader = currentFrame?.drivers.find((d) => d.position === 1);
    if (leader?.sector1_s && leader?.sector2_s && leader?.sector3_s) {
      return leader.sector1_s + leader.sector2_s + leader.sector3_s;
    }
    return 90;
  })();

  function dotPosition(driver: DriverFrame): [number, number] {
    const gapFraction = ((driver.gap_to_leader_s ?? 0) / leaderLapTimeS) % 1;
    let p = (progress - gapFraction) % 1;
    if (p < 0) p += 1;
    const idx = Math.floor(p * n) % n;
    return circuit!.points[idx];
  }

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
        {currentFrame?.drivers.map((d) => {
          const [x, y] = dotPosition(d);
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
