import { useMemo, useState } from "react";
import type { RaceSummary } from "../api/types";
import { useReplay } from "../context/ReplayContext";
import { teamColor } from "../teamColors";
import TraceChart from "../telemetry/TraceChart";
import type { TraceSeries } from "../telemetry/TraceChart";
import {
  fastestLapForDriver,
  formatLapTime,
  lapsForDriver,
  sameLap,
  sessionFastestLap,
  useLapComparison,
} from "../telemetry/lapTelemetry";
import type { Comparison, LapRef } from "../telemetry/lapTelemetry";
import type { LapFrame } from "../api/types";

interface Picks {
  frames: LapFrame[] | null;
  browse?: string;
  lap?: LapRef | null;
  ref?: LapRef | null;
}

const REF_COLOR = "#facc15";

const LANES = {
  delta: { tint: "var(--lane-delta)", color: "#b794ff" },
  speed: { tint: "var(--lane-speed)", color: "#5aa9ff" },
  throttle: { tint: "var(--lane-throttle)", color: "#4ade80" },
  brake: { tint: "var(--lane-brake)", color: "#ff6b6b" },
  gear: { tint: "var(--lane-gear)", color: "#2dd4bf" },
};

function pair(lap: number[], ref: number[], color: string): TraceSeries[] {
  return [
    { values: lap, color, pillBg: color, pillText: "#0b0a12" },
    { values: ref, color: REF_COLOR, pillBg: REF_COLOR, pillText: "#0b0a12" },
  ];
}

function fmtDelta(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(3)}`;
}

export default function TelemetryView({ race }: { race: RaceSummary }) {
  const { frames, loading: replayLoading, error: replayError } = useReplay();
  const [cursor, setCursor] = useState<number | null>(null);
  const driverTeam = useMemo(
    () => Object.fromEntries(race.drivers.map((d) => [d.driver, d.team])),
    [race],
  );
  const driversByFinish = useMemo(
    () =>
      [...race.drivers].sort(
        (a, b) => (a.finish_position ?? 99) - (b.finish_position ?? 99),
      ),
    [race],
  );

  // Default comparison: the winner's fastest lap against the session's fastest
  // lap (or, if the winner set that, against the runner-up's fastest).
  const defaults = useMemo(() => {
    const winner = driversByFinish[0]?.driver ?? null;
    if (frames.length === 0 || !winner) return { browse: winner, lap: null, ref: null };
    const myLap = fastestLapForDriver(frames, winner);
    let refLap = sessionFastestLap(frames);
    if (sameLap(myLap, refLap) || refLap == null) {
      const runnerUp = driversByFinish[1]?.driver;
      refLap = runnerUp ? fastestLapForDriver(frames, runnerUp) : fastestLapForDriver(frames, winner, myLap);
    }
    return { browse: winner, lap: myLap, ref: refLap };
  }, [frames, driversByFinish]);

  // User picks are tied to the frames they were made against, so loading a
  // new race falls back to that race's defaults without a reset effect.
  const [picks, setPicks] = useState<Picks>({ frames: null });
  const current = picks.frames === frames ? picks : { frames };
  const browseDriver = current.browse ?? defaults.browse;
  const lap = current.lap !== undefined ? current.lap : defaults.lap;
  const ref = current.ref !== undefined ? current.ref : defaults.ref;
  const pick = (p: Omit<Picks, "frames">) => setPicks({ ...current, ...p, frames });
  const setBrowseDriver = (browse: string) => pick({ browse });
  const setLap = (l: LapRef | null) => pick({ lap: l });
  const setRef = (r: LapRef | null) => pick({ ref: r });

  const { comparison, loading, error } = useLapComparison(race.year, race.event, lap, ref);

  if (replayLoading || (frames.length === 0 && !replayError)) {
    return <div className="panel"><p className="hint">Loading session…</p></div>;
  }
  if (replayError) return <div className="panel"><p className="error-text">{replayError}</p></div>;

  return (
    <div className="telemetry-grid">
      <aside className="flex min-w-0 flex-col gap-3">
        <SessionCard race={race} />
        <ReferenceCard
          lap={lap}
          refLap={ref}
          drivers={driversByFinish.map((d) => d.driver)}
          driverTeam={driverTeam}
          onChange={(which, r) => {
            // Show the newly picked driver's laps in the list below too.
            pick(which === "lap" ? { lap: r, browse: r.driver } : { ref: r, browse: r.driver });
          }}
          onSwap={() => pick({ lap: ref, ref: lap })}
          onRefFastest={() => {
            const f = sessionFastestLap(frames);
            if (f) setRef(f);
          }}
        />
        {browseDriver && (
          <LapList
            driver={browseDriver}
            drivers={driversByFinish.map((d) => d.driver)}
            driverTeam={driverTeam}
            onDriver={setBrowseDriver}
            lap={lap}
            refLap={ref}
            onPickLap={(l) => setLap({ driver: browseDriver, lap: l })}
            onPickRef={(l) => setRef({ driver: browseDriver, lap: l })}
          />
        )}
      </aside>

      <section className="trace-stack min-w-0">
        {error && <p className="error-text px-4 py-3">{error}</p>}
        {!comparison && !error && (
          <div className="trace-empty">
            <span className="spinner" />
            {loading ? "Loading telemetry… first load for a driver can take a few seconds" : "Pick a lap to compare"}
          </div>
        )}
        {comparison && (
          <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>
            <Traces comparison={comparison} cursor={cursor} onCursor={setCursor} />
          </div>
        )}
      </section>

      <aside className="flex min-w-0 flex-col gap-3">
        <MiniTrack comparison={comparison} cursor={cursor} />
        <SectorCompare lap={lap} refLap={ref} />
        <LiveValues comparison={comparison} cursor={cursor} />
      </aside>
    </div>
  );
}

function Traces({
  comparison: c,
  cursor,
  onCursor,
}: {
  comparison: Comparison;
  cursor: number | null;
  onCursor: (i: number) => void;
}) {
  const series = useMemo(
    () => ({
      delta: [{ values: c.delta, color: LANES.delta.color, pillBg: LANES.delta.color, pillText: "#0b0a12" }],
      speed: pair(c.lap.speed, c.ref.speed, LANES.speed.color),
      throttle: pair(c.lap.throttle, c.ref.throttle, LANES.throttle.color),
      brake: pair(c.lap.brake, c.ref.brake, LANES.brake.color),
      gear: pair(c.lap.gear, c.ref.gear, LANES.gear.color),
    }),
    [c],
  );
  const common = { distance: c.distance, cursor, onCursor };
  return (
    <>
      <TraceChart {...common} label="Delta" unit="s" series={series.delta} tint={LANES.delta.tint} height={130} zeroLine format={fmtDelta} />
      <TraceChart {...common} label="Speed" unit="km/h" series={series.speed} tint={LANES.speed.tint} height={190} format={(v) => v.toFixed(0)} />
      <TraceChart {...common} label="Throttle" unit="%" series={series.throttle} tint={LANES.throttle.tint} height={130} domain={[-5, 108]} ticks={[0, 50, 100]} format={(v) => `${v.toFixed(0)}`} />
      <TraceChart {...common} label="Brake" series={series.brake} tint={LANES.brake.tint} height={100} domain={[-12, 112]} ticks={[0, 100]} format={(v) => (v > 50 ? "ON" : "OFF")} />
      <TraceChart {...common} label="Gear" series={series.gear} tint={LANES.gear.tint} height={110} domain={[0.5, 8.5]} ticks={[2, 4, 6, 8]} format={(v) => v.toFixed(0)} showAxis />
    </>
  );
}

function SessionCard({ race }: { race: RaceSummary }) {
  const { weather } = useReplay();
  const avg = (k: "air_temp_c" | "track_temp_c") =>
    weather.length ? weather.reduce((s, w) => s + w[k], 0) / weather.length : null;
  const air = avg("air_temp_c");
  const track = avg("track_temp_c");
  const rain = weather.some((w) => w.rainfall);
  const winner = race.drivers.find((d) => d.finish_position === 1);
  return (
    <div className="card">
      <div className="card-title text-center">{race.event}</div>
      <div className="kv-list">
        <div className="kv"><span>Season</span><strong>{race.year} · Race</strong></div>
        <div className="kv"><span>Laps</span><strong>{race.total_race_laps}</strong></div>
        {air != null && track != null && (
          <div className="kv">
            <span>Air / Track</span>
            <strong>{air.toFixed(0)}°C / {track.toFixed(0)}°C</strong>
          </div>
        )}
        <div className="kv">
          <span>Conditions</span>
          <strong className={rain ? "text-(--warn)" : "text-(--good)"}>{rain ? "WET" : "DRY"}</strong>
        </div>
        <div className="kv"><span>Pit loss</span><strong>{race.pit_loss_s.toFixed(1)}s</strong></div>
        {winner && (
          <div className="kv">
            <span>Winner</span>
            <strong style={{ color: teamColor(winner.team) }}>{winner.driver}</strong>
          </div>
        )}
      </div>
    </div>
  );
}

function ReferenceCard({
  lap,
  refLap,
  drivers,
  driverTeam,
  onChange,
  onSwap,
  onRefFastest,
}: {
  lap: LapRef | null;
  refLap: LapRef | null;
  drivers: string[];
  driverTeam: Record<string, string>;
  onChange: (which: "lap" | "ref", r: LapRef) => void;
  onSwap: () => void;
  onRefFastest: () => void;
}) {
  const { frames } = useReplay();

  // Switching driver lands on their fastest lap -- or, if they already hold
  // the other slot, their next-fastest so the comparison isn't a lap vs itself.
  const pickDriver = (which: "lap" | "ref", driver: string) => {
    const other = which === "lap" ? refLap : lap;
    const best = fastestLapForDriver(frames, driver, other?.driver === driver ? other : null);
    const fallback = lapsForDriver(frames, driver).at(-1);
    const target = best ?? (fallback ? { driver, lap: fallback.lap } : null);
    if (target) onChange(which, target);
  };

  const row = (which: "lap" | "ref", r: LapRef | null) => (
    <RefRow
      tag={which === "lap" ? "LAP" : "REF"}
      cls={which === "lap" ? "ref-row-lap" : "ref-row-ref"}
      r={r}
      drivers={drivers}
      driverTeam={driverTeam}
      onDriver={(d) => pickDriver(which, d)}
      onLap={(l) => r && onChange(which, { driver: r.driver, lap: l })}
    />
  );

  return (
    <div className="card">
      <div className="card-eyebrow">Comparison</div>
      {row("lap", lap)}
      {row("ref", refLap)}
      <div className="mt-2 flex gap-2">
        <button className="ghost-button flex-1" onClick={onSwap}>Swap</button>
        <button className="ghost-button flex-1" onClick={onRefFastest}>Ref: fastest</button>
      </div>
    </div>
  );
}

function RefRow({
  tag,
  cls,
  r,
  drivers,
  driverTeam,
  onDriver,
  onLap,
}: {
  tag: string;
  cls: string;
  r: LapRef | null;
  drivers: string[];
  driverTeam: Record<string, string>;
  onDriver: (driver: string) => void;
  onLap: (lap: number) => void;
}) {
  const { frames } = useReplay();
  const laps = useMemo(() => (r ? lapsForDriver(frames, r.driver) : []), [frames, r]);
  const best = useMemo(() => (r ? fastestLapForDriver(frames, r.driver)?.lap : undefined), [frames, r]);
  const time = laps.find((l) => l.lap === r?.lap)?.lapTime ?? null;

  return (
    <div className={`ref-row ${cls}`}>
      <span className="ref-tag">{tag}</span>
      <select
        className="ref-select ref-select-driver"
        value={r?.driver ?? ""}
        onChange={(e) => onDriver(e.target.value)}
        style={{ color: teamColor(r ? driverTeam[r.driver] : undefined) }}
        aria-label={`${tag} driver`}
      >
        {!r && <option value="">—</option>}
        {drivers.map((d) => (
          <option key={d} value={d}>
            {d} · {driverTeam[d]}
          </option>
        ))}
      </select>
      <select
        className="ref-select ref-select-lap"
        value={r?.lap ?? ""}
        onChange={(e) => onLap(Number(e.target.value))}
        disabled={!r}
        aria-label={`${tag} lap`}
      >
        {laps.map((l) => (
          <option key={l.lap} value={l.lap}>
            L{l.lap} · {formatLapTime(l.lapTime)}
            {l.lap === best ? " ★" : ""}
            {l.frame.pit_this_lap ? " (pit)" : ""}
          </option>
        ))}
      </select>
      <span className="ml-auto font-mono">{formatLapTime(time)}</span>
    </div>
  );
}

function LapList({
  driver,
  drivers,
  driverTeam,
  onDriver,
  lap,
  refLap,
  onPickLap,
  onPickRef,
}: {
  driver: string;
  drivers: string[];
  driverTeam: Record<string, string>;
  onDriver: (d: string) => void;
  lap: LapRef | null;
  refLap: LapRef | null;
  onPickLap: (l: number) => void;
  onPickRef: (l: number) => void;
}) {
  const { frames } = useReplay();
  const laps = useMemo(() => lapsForDriver(frames, driver), [frames, driver]);
  const best = useMemo(() => fastestLapForDriver(frames, driver), [frames, driver]);

  return (
    <div className="card flex min-h-0 flex-col">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="card-eyebrow m-0">Laps</span>
        <select
          value={driver}
          onChange={(e) => onDriver(e.target.value)}
          style={{ color: teamColor(driverTeam[driver]) }}
          className="driver-select"
        >
          {drivers.map((d) => (
            <option key={d} value={d}>{d} · {driverTeam[d]}</option>
          ))}
        </select>
      </div>
      <div className="lap-list">
        {laps.map((l) => {
          const isLap = sameLap(lap, { driver, lap: l.lap });
          const isRef = sameLap(refLap, { driver, lap: l.lap });
          const isBest = best?.lap === l.lap;
          const compound = l.frame.compound?.toLowerCase();
          return (
            <div
              key={l.lap}
              role="button"
              tabIndex={0}
              className={`lap-row${isLap ? " is-lap" : ""}${isRef ? " is-ref" : ""}`}
              onClick={() => onPickLap(l.lap)}
              onKeyDown={(e) => e.key === "Enter" && onPickLap(l.lap)}
            >
              <span className="lap-num">{l.lap}</span>
              <span className={`lap-time${isBest ? " is-best" : ""}`}>{formatLapTime(l.lapTime)}</span>
              <span className="lap-tyre">
                {compound && <span className={`compound-dot compound-${compound}`} />}
                {l.frame.tyre_life != null ? Math.round(l.frame.tyre_life) : ""}
              </span>
              {l.frame.pit_this_lap && <span className="lap-pit">PIT</span>}
              <button
                className="lap-ref-btn"
                title="Use as reference lap"
                onClick={(e) => {
                  e.stopPropagation();
                  onPickRef(l.lap);
                }}
              >
                REF
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MiniTrack({ comparison: c, cursor }: { comparison: Comparison | null; cursor: number | null }) {
  const { circuit } = useReplay();

  const geo = useMemo(() => {
    const pts: [number, number][] = c
      ? c.lap.x.map((x, i) => [x, c.lap.y[i]])
      : circuit?.points ?? [];
    if (pts.length < 2) return null;
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const pad = Math.max(maxX - minX, maxY - minY) * 0.08;
    return {
      pts,
      box: [minX - pad, minY - pad, maxX - minX + 2 * pad, maxY - minY + 2 * pad],
    };
  }, [c, circuit]);

  // Colour the racing line by where the analysis lap gains (purple) or
  // loses (red) time against the reference, over ~50m windows.
  const segments = useMemo(() => {
    if (!c) return [];
    const W = 10;
    const out: { d: string; gain: boolean }[] = [];
    for (let i = 0; i + W < c.delta.length; i += W) {
      let d = "";
      for (let j = i; j <= i + W; j++) d += `${j === i ? "M" : "L"}${c.lap.x[j]},${c.lap.y[j]}`;
      out.push({ d, gain: c.delta[i + W] <= c.delta[i] });
    }
    return out;
  }, [c]);

  if (!geo) return <div className="card"><p className="hint m-0">No track outline</p></div>;
  const [bx, by, bw, bh] = geo.box;
  const sw = bw * 0.012;
  const outline = `M${geo.pts.map((p) => p.join(",")).join("L")}Z`;
  const at = (lx: number[], ly: number[]) => (cursor != null ? [lx[cursor], ly[cursor]] : null);
  const lapPos = c ? at(c.lap.x, c.lap.y) : null;
  const refPos = c ? at(c.ref.x, c.ref.y) : null;

  return (
    <div className="card p-2">
      <svg viewBox={`${bx} ${by} ${bw} ${bh}`} className="mini-track" preserveAspectRatio="xMidYMid meet">
        <path d={outline} fill="none" stroke="var(--track)" strokeWidth={sw * 2.2} strokeLinejoin="round" />
        {segments.map((s, i) => (
          <path key={i} d={s.d} fill="none" stroke={s.gain ? "#b794ff" : "#ff6b6b"} strokeWidth={sw} strokeLinecap="round" />
        ))}
        {geo.pts[0] && <circle cx={geo.pts[0][0]} cy={geo.pts[0][1]} r={sw * 1.6} fill="#fff" />}
        {refPos && <circle cx={refPos[0]} cy={refPos[1]} r={sw * 2.2} fill={REF_COLOR} stroke="#0b0a12" strokeWidth={sw * 0.5} />}
        {lapPos && <circle cx={lapPos[0]} cy={lapPos[1]} r={sw * 2.2} fill="#5aa9ff" stroke="#0b0a12" strokeWidth={sw * 0.5} />}
      </svg>
      {c && (
        <div className="flex justify-center gap-4 pb-1 text-[0.65rem] font-semibold uppercase tracking-wider text-(--text-dim)">
          <span><span className="legend-swatch" style={{ background: "#b794ff" }} />Gaining</span>
          <span><span className="legend-swatch" style={{ background: "#ff6b6b" }} />Losing</span>
        </div>
      )}
    </div>
  );
}

function SectorCompare({ lap, refLap }: { lap: LapRef | null; refLap: LapRef | null }) {
  const { frames } = useReplay();
  const find = (r: LapRef | null) =>
    r ? lapsForDriver(frames, r.driver).find((l) => l.lap === r.lap) : undefined;
  const a = find(lap);
  const b = find(refLap);
  const rows: { label: string; a: number | null; b: number | null; lapRow?: boolean }[] = [
    { label: "S1", a: a?.frame.sector1_s ?? null, b: b?.frame.sector1_s ?? null },
    { label: "S2", a: a?.frame.sector2_s ?? null, b: b?.frame.sector2_s ?? null },
    { label: "S3", a: a?.frame.sector3_s ?? null, b: b?.frame.sector3_s ?? null },
    { label: "LAP", a: a?.lapTime ?? null, b: b?.lapTime ?? null, lapRow: true },
  ];
  const fmt = (v: number | null, lapRow?: boolean) => (v == null ? "—" : lapRow ? formatLapTime(v) : v.toFixed(3));
  return (
    <div className="card">
      <div className="card-eyebrow text-center">Sectors</div>
      <div className="sector-grid">
        {rows.map((r) => {
          const aFaster = r.a != null && r.b != null && r.a < r.b;
          const bFaster = r.a != null && r.b != null && r.b < r.a;
          return (
            <div key={r.label} className="contents">
              <span className={`sector-cell${aFaster ? " is-faster" : ""}`}>{fmt(r.a, r.lapRow)}</span>
              <span className="sector-label">{r.label}</span>
              <span className={`sector-cell${bFaster ? " is-faster" : ""}`}>{fmt(r.b, r.lapRow)}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between text-[0.6rem] font-bold tracking-wider text-(--text-dim)">
        <span className="text-[#5aa9ff]">LAP</span>
        <span style={{ color: REF_COLOR }}>REF</span>
      </div>
    </div>
  );
}

function LiveValues({ comparison: c, cursor }: { comparison: Comparison | null; cursor: number | null }) {
  const i = cursor ?? 0;
  const has = c != null && cursor != null;
  const delta = has ? c!.delta[i] : null;
  const rows = [
    { icon: "◷", label: "Speed", lane: LANES.speed.color, a: c?.lap.speed[i], b: c?.ref.speed[i], f: (v: number) => v.toFixed(1) },
    { icon: "▲", label: "Throttle", lane: LANES.throttle.color, a: c?.lap.throttle[i], b: c?.ref.throttle[i], f: (v: number) => `${v.toFixed(0)}%` },
    { icon: "■", label: "Brake", lane: LANES.brake.color, a: c?.lap.brake[i], b: c?.ref.brake[i], f: (v: number) => (v > 50 ? "ON" : "OFF") },
    { icon: "⚙", label: "Gear", lane: LANES.gear.color, a: c?.lap.gear[i], b: c?.ref.gear[i], f: (v: number) => v.toFixed(0) },
  ];
  return (
    <div className="card">
      <div className="live-row">
        <span className="live-label"><span className="live-icon">Δ</span>Delta</span>
        <span
          className="live-pill"
          style={{
            background: delta == null ? "var(--panel-raised)" : delta <= 0 ? "var(--good)" : "var(--bad)",
            color: delta == null ? "var(--text-dim)" : "#0b0a12",
          }}
        >
          {delta == null ? "—" : fmtDelta(delta)}
        </span>
      </div>
      {rows.map((r) => (
        <div className="live-row" key={r.label}>
          <span className="live-label"><span className="live-icon" style={{ color: r.lane }}>{r.icon}</span>{r.label}</span>
          <span className="flex gap-1">
            <span className="live-pill" style={{ background: has ? r.lane : "var(--panel-raised)", color: has ? "#0b0a12" : "var(--text-dim)" }}>
              {has && r.a != null ? r.f(r.a) : "—"}
            </span>
            <span className="live-pill live-pill-ref">{has && r.b != null ? r.f(r.b) : "—"}</span>
          </span>
        </div>
      ))}
      <Pedals c={c} i={has ? i : null} />
      {!has && <p className="hint mt-2 mb-0 text-center text-[0.7rem]">Hover the traces to scrub the lap</p>}
    </div>
  );
}

function Pedals({ c, i }: { c: Comparison | null; i: number | null }) {
  const bars = [
    { label: "THR", v: c && i != null ? c.lap.throttle[i] : 0, color: LANES.throttle.color },
    { label: "THR", v: c && i != null ? c.ref.throttle[i] : 0, color: REF_COLOR },
    { label: "BRK", v: c && i != null ? c.lap.brake[i] : 0, color: LANES.brake.color },
    { label: "BRK", v: c && i != null ? c.ref.brake[i] : 0, color: REF_COLOR },
  ];
  return (
    <div className="pedals">
      {bars.map((b, k) => (
        <div key={k} className="pedal">
          <div className="pedal-track">
            <div className="pedal-fill" style={{ height: `${Math.max(0, Math.min(100, b.v))}%`, background: b.color }} />
          </div>
          <span>{b.label}</span>
        </div>
      ))}
    </div>
  );
}
