import { useState } from "react";

interface Props {
  onLoad: (year: number, event: string) => void;
  loading: boolean;
}

const PRESETS = [
  { label: "2023 Silverstone (British GP)", year: 2023, event: "Silverstone" },
  { label: "2023 Monza (Italian GP)", year: 2023, event: "Monza" },
  { label: "2023 Spa (Belgian GP)", year: 2023, event: "Spa" },
  { label: "2023 Suzuka (Japanese GP)", year: 2023, event: "Suzuka" },
];

export default function RaceSelector({ onLoad, loading }: Props) {
  const [year, setYear] = useState(2023);
  const [event, setEvent] = useState("Silverstone");

  return (
    <section className="panel">
      <h2>Race</h2>
      <div className="row">
        <label>
          Year
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            min={2018}
            max={2025}
          />
        </label>
        <label>
          Event
          <input value={event} onChange={(e) => setEvent(e.target.value)} placeholder="e.g. Silverstone" />
        </label>
        <button disabled={loading} onClick={() => onLoad(year, event)}>
          {loading ? "Loading…" : "Load race"}
        </button>
      </div>
      <div className="presets">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            className="preset-chip"
            disabled={loading}
            onClick={() => {
              setYear(p.year);
              setEvent(p.event);
              onLoad(p.year, p.event);
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
    </section>
  );
}
