import { useReplay } from "../context/ReplayContext";

export default function WeatherPanel() {
  const { currentWeather } = useReplay();

  return (
    <section className="panel weather-panel">
      <h2>Conditions</h2>
      {!currentWeather && <p className="hint">No weather data for this race.</p>}
      {currentWeather && (
        <div className="stat-row">
          <div className="stat">
            <span className="stat-value">{currentWeather.air_temp_c.toFixed(1)}°C</span>
            <span className="stat-label">air temp</span>
          </div>
          <div className="stat">
            <span className="stat-value">{currentWeather.track_temp_c.toFixed(1)}°C</span>
            <span className="stat-label">track temp</span>
          </div>
          <div className="stat">
            <span className="stat-value">{currentWeather.humidity_pct.toFixed(0)}%</span>
            <span className="stat-label">humidity</span>
          </div>
          <div className="stat">
            <span className="stat-value">{currentWeather.wind_speed_kmh.toFixed(1)} km/h</span>
            <span className="stat-label">wind</span>
          </div>
          <div className="stat">
            <span className={currentWeather.rainfall ? "stat-value laps-warning" : "stat-value laps-ok"}>
              {currentWeather.rainfall ? "Rain" : "Dry"}
            </span>
            <span className="stat-label">track</span>
          </div>
        </div>
      )}
    </section>
  );
}
