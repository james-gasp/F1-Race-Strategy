import type React from "react";
import { useReplay } from "../context/ReplayContext";

const SPEEDS = [
  { label: "0.5×", ms: 1600 },
  { label: "1×", ms: 800 },
  { label: "2×", ms: 400 },
  { label: "4×", ms: 200 },
];

export default function ReplayControls() {
  const { totalLaps, lapIndex, setLapIndex, isPlaying, play, pause, speedMs, setSpeedMs, currentFrame, loading } =
    useReplay();

  if (loading) return <section className="panel replay-controls"><p className="hint">Loading replay…</p></section>;
  if (totalLaps === 0) return null;

  return (
    <section className="panel replay-controls">
      <div className="row" style={{ alignItems: "center" }}>
        <button onClick={isPlaying ? pause : play}>{isPlaying ? "Pause" : "Play"}</button>
        <input
          type="range"
          min={0}
          max={totalLaps - 1}
          value={lapIndex}
          onChange={(e) => setLapIndex(Number(e.target.value))}
          style={
            {
              flex: 1,
              minWidth: 200,
              "--range-progress": `${totalLaps > 1 ? (lapIndex / (totalLaps - 1)) * 100 : 0}%`,
            } as React.CSSProperties
          }
        />
        <span className="hint" style={{ minWidth: 90 }}>
          Lap {currentFrame?.lap_number ?? "—"} / {totalLaps}
        </span>
        <label className="inline-label">
          Speed
          <select value={speedMs} onChange={(e) => setSpeedMs(Number(e.target.value))}>
            {SPEEDS.map((s) => (
              <option key={s.ms} value={s.ms}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
