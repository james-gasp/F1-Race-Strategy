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
