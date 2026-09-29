// Mirrors the Pydantic schemas in api/schemas/*.py -- kept in sync by hand
// since this project doesn't (yet) generate the client from the OpenAPI spec.

export interface StintIn {
  compound: string;
  laps: number;
  start_tyre_life: number;
}

export interface StrategyIn {
  name: string;
  driver: string;
  stints: StintIn[];
}

export interface DriverStint {
  compound: string;
  laps: number;
}

export interface DriverSummary {
  driver: string;
  team: string;
  grid_position: number;
  finish_position: number | null;
  status: string;
  historical_strategy: DriverStint[];
}

export interface PaceModelSummary {
  reference_driver: string;
  reference_compound: string;
  fuel_effect_per_lap: number;
  compound_offset: Record<string, number>;
  deg_linear: Record<string, number>;
  deg_quad: Record<string, number>;
  residual_std: number;
}

export interface RaceSummary {
  year: number;
  event: string;
  total_race_laps: number;
  pit_loss_s: number;
  pace_model: PaceModelSummary;
  drivers: DriverSummary[];
}

export interface StrategyResult {
  strategy: string;
  n_stops: number;
  total_laps: number;
  mean_s: number;
  median_s: number;
  std_s: number;
  p10_s: number;
  p90_s: number;
  prob_fastest: number;
}

export interface CompareResponse {
  results: StrategyResult[];
}

export interface OptimizeResponse {
  recommended: StrategyResult;
  candidates: StrategyResult[];
}

export interface DriverPositionProbability {
  driver: string;
  expected_position: number;
  prob_win: number;
  prob_podium: number;
  position_probabilities: Record<string, number>;
}

export interface FieldResponse {
  drivers: DriverPositionProbability[];
}

export interface ApiErrorBody {
  detail: string;
}

export interface CircuitOutline {
  points: [number, number][];
  length_m: number;
}

export interface UndercutThreat {
  gap_s: number;
  pit_loss_s: number;
  est_pace_gain_per_lap_s: number;
  laps_to_undercut: number | null;
  is_threat: boolean;
}

export interface DriverFrame {
  driver: string;
  team: string;
  position: number | null;
  gap_to_leader_s: number | null;
  gap_ahead_s: number | null;
  compound: string | null;
  tyre_life: number | null;
  stint: number | null;
  pit_this_lap: boolean;
  sector1_s: number | null;
  sector2_s: number | null;
  sector3_s: number | null;
  undercut_threat: UndercutThreat | null;
}

export interface LapFrame {
  lap_number: number;
  drivers: DriverFrame[];
}

export interface ReplayResponse {
  total_laps: number;
  frames: LapFrame[];
}

export interface TelemetryPoint {
  time_s: number;
  x: number;
  y: number;
  speed_kmh: number;
  distance_m: number;
  lap_time_s: number;
  throttle_pct: number;
  brake: boolean;
  gear: number;
}

export interface DriverTelemetry {
  driver: string;
  lap_number: number;
  points: TelemetryPoint[];
}

export interface WeatherSample {
  time_s: number;
  lap_number: number | null;
  air_temp_c: number;
  track_temp_c: number;
  humidity_pct: number;
  rainfall: boolean;
  wind_speed_kmh: number;
  wind_direction_deg: number;
}

export interface WeatherResponse {
  samples: WeatherSample[];
}

export interface SeasonRace {
  round: number;
  event_name: string;
  location: string;
  country: string;
  race_date: string;
}

export interface SeasonResponse {
  year: number;
  races: SeasonRace[];
}
