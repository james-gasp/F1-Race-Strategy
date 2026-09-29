import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { RaceSummary } from "../api/types";
import RaceSelector from "./RaceSelector";

export type View = "telemetry" | "timing" | "strategy";

const svgProps = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const ICONS: Record<View, ReactNode> = {
  telemetry: (
    <svg {...svgProps}>
      <path d="M3 17l4-6 4 3 4-8 6 9" />
      <path d="M3 21h18" />
    </svg>
  ),
  timing: (
    <svg {...svgProps}>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l2.5 2.5M9.5 2h5M12 2v3" />
    </svg>
  ),
  strategy: (
    <svg {...svgProps}>
      <path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 006 21h12a1.7 1.7 0 001.5-2.5L14 9V3" />
      <path d="M7 15h10" />
    </svg>
  ),
};

const NAV: { view: View; label: string }[] = [
  { view: "telemetry", label: "Telemetry" },
  { view: "timing", label: "Live Timing" },
  { view: "strategy", label: "Strategy Lab" },
];

function Logo() {
  return (
    <div className="logo" aria-label="F1 Race Control">
      <span className="logo-badge">F1</span>
      <span className="logo-word">RACE CONTROL</span>
      <svg width="22" height="16" viewBox="0 0 22 16" aria-hidden>
        {[0, 1, 2, 3].map((r) =>
          [0, 1, 2, 3, 4].map((c) =>
            (r + c) % 2 === 0 ? (
              <rect key={`${r}-${c}`} x={c * 4.4 + r * 1.2} y={r * 4} width="4.4" height="4" fill="#fff" transform="skewX(-12)" />
            ) : null,
          ),
        )}
      </svg>
    </div>
  );
}

export default function AppShell({
  race,
  view,
  onView,
  onLoadRace,
  raceLoading,
  children,
}: {
  race: RaceSummary | null;
  view: View;
  onView: (v: View) => void;
  onLoadRace: (year: number, event: string) => void;
  raceLoading: boolean;
  children: ReactNode;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pickerOpen) return;
    const close = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) setPickerOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [pickerOpen]);

  return (
    <div className="shell">
      <header className="topbar">
        <Logo />
        {race && (
          <div className="session-tab">
            <span className="session-dot" />
            {race.event.toUpperCase()} · {race.year}
          </div>
        )}
        <div className="ml-auto" ref={pickerRef} style={{ position: "relative" }}>
          {race && (
            <button className="topbar-button" onClick={() => setPickerOpen((o) => !o)}>
              {raceLoading ? "Loading…" : "Change race"}
            </button>
          )}
          {pickerOpen && (
            <div className="picker-popover">
              <RaceSelector
                onLoad={(y, e) => {
                  setPickerOpen(false);
                  onLoadRace(y, e);
                }}
                loading={raceLoading}
                currentYear={race?.year}
                currentEvent={race?.event}
              />
            </div>
          )}
        </div>
      </header>

      <nav className="rail">
        {NAV.map((n) => (
          <button
            key={n.view}
            className={`rail-button${view === n.view ? " is-active" : ""}`}
            onClick={() => onView(n.view)}
            disabled={!race}
            title={n.label}
            aria-label={n.label}
          >
            {ICONS[n.view]}
            <span className="rail-label">{n.label}</span>
          </button>
        ))}
      </nav>

      <main className="shell-main">{children}</main>
    </div>
  );
}
