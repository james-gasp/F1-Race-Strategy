import { useEffect, useMemo, useRef, useState } from "react";

export interface TraceSeries {
  values: number[];
  color: string;
  // Filled pill colors for the value readout at the cursor.
  pillBg: string;
  pillText: string;
}

interface Props {
  label: string;
  unit?: string;
  distance: number[];
  series: TraceSeries[];
  tint: string;
  height: number;
  domain?: [number, number];
  ticks?: number[];
  cursor: number | null;
  onCursor: (index: number) => void;
  format: (v: number) => string;
  zeroLine?: boolean;
  showAxis?: boolean;
}

const GUTTER_L = 46;
const GUTTER_R = 12;
const PAD_Y = 10;
const AXIS_H = 20;

function niceTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || 1;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let t = Math.ceil(min / step) * step; t <= max + 1e-9; t += step) out.push(+t.toFixed(6));
  return out;
}

export default function TraceChart({
  label,
  unit,
  distance,
  series,
  tint,
  height,
  domain,
  ticks,
  cursor,
  onCursor,
  format,
  zeroLine,
  showAxis,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const [yMin, yMax] = useMemo<[number, number]>(() => {
    if (domain) return domain;
    let lo = Infinity;
    let hi = -Infinity;
    for (const s of series) {
      for (const v of s.values) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    if (!isFinite(lo)) return [0, 1];
    if (zeroLine) {
      const m = Math.max(Math.abs(lo), Math.abs(hi), 0.05);
      return [-m * 1.1, m * 1.1];
    }
    const pad = (hi - lo) * 0.08 || 1;
    return [lo - pad, hi + pad];
  }, [domain, series, zeroLine]);

  const totalH = height + (showAxis ? AXIS_H : 0);
  const plotW = Math.max(10, width - GUTTER_L - GUTTER_R);
  const maxD = distance[distance.length - 1] || 1;
  const sx = (d: number) => GUTTER_L + (d / maxD) * plotW;
  const sy = (v: number) => PAD_Y + (1 - (v - yMin) / (yMax - yMin)) * (height - PAD_Y * 2);

  const paths = series.map((s) => {
    let d = "";
    for (let i = 0; i < s.values.length; i++) {
      d += `${i === 0 ? "M" : "L"}${sx(distance[i]).toFixed(1)},${sy(s.values[i]).toFixed(1)}`;
    }
    return d;
  });

  const yTicks = ticks ?? niceTicks(yMin, yMax);
  const xTicks = niceTicks(0, maxD, 8).filter((t) => t < maxD);

  const handleMove = (el: SVGSVGElement, clientX: number) => {
    const rect = el.getBoundingClientRect();
    const frac = (clientX - rect.left - GUTTER_L) / plotW;
    const idx = Math.round(Math.max(0, Math.min(1, frac)) * (distance.length - 1));
    onCursor(idx);
  };

  const cx = cursor != null ? sx(distance[cursor]) : null;
  // Place pills to the right of the cursor, flipping to the left near the edge.
  const pillsLeft = cx != null && cx > width - 90;

  return (
    <div ref={wrapRef} className="trace-lane" style={{ background: tint }}>
      <svg
        width={width}
        height={totalH}
        onMouseMove={(e) => handleMove(e.currentTarget, e.clientX)}
        onTouchMove={(e) => handleMove(e.currentTarget, e.touches[0].clientX)}
        style={{ display: "block", cursor: "crosshair", touchAction: "pan-y" }}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={GUTTER_L} x2={width - GUTTER_R} y1={sy(t)} y2={sy(t)} className="trace-grid" />
            <text x={GUTTER_L - 6} y={sy(t)} dy={3} textAnchor="end" className="trace-tick">
              {format(t)}
            </text>
          </g>
        ))}
        {zeroLine && (
          <line x1={GUTTER_L} x2={width - GUTTER_R} y1={sy(0)} y2={sy(0)} className="trace-zero" />
        )}
        {paths.map((d, i) => (
          <path
            key={i}
            d={d}
            fill="none"
            stroke={series[i].color}
            strokeWidth={i === 0 ? 1.6 : 1.2}
            strokeOpacity={i === 0 ? 1 : 0.75}
            strokeLinejoin="round"
          />
        ))}
        <text x={GUTTER_L + 8} y={height - 8} className="trace-label">
          {label}
          {unit && <tspan className="trace-unit"> {unit}</tspan>}
        </text>

        {showAxis &&
          xTicks.map((t) => (
            <text key={t} x={sx(t)} y={height + 14} textAnchor="middle" className="trace-tick">
              {t >= 1000 ? `${(t / 1000).toFixed(1)}km` : `${t}m`}
            </text>
          ))}

        {cx != null && cursor != null && (
          <g>
            <line x1={cx} x2={cx} y1={0} y2={height} className="trace-cursor" />
            {series.map((s, i) => {
              const v = s.values[cursor];
              const text = format(v);
              const w = text.length * 6.6 + 12;
              const y = Math.max(2, Math.min(height - 36, sy(series[0].values[cursor]) - 20)) + i * 17;
              const x = pillsLeft ? cx - w - 4 : cx + 4;
              return (
                <g key={i} transform={`translate(${x}, ${y})`}>
                  <rect width={w} height={15} rx={3} fill={s.pillBg} />
                  <text x={w / 2} y={11} textAnchor="middle" className="trace-pill" fill={s.pillText}>
                    {text}
                  </text>
                </g>
              );
            })}
          </g>
        )}
      </svg>
    </div>
  );
}
