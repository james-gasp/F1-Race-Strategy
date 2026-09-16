import type {
  ApiErrorBody,
  CompareResponse,
  FieldResponse,
  OptimizeResponse,
  RaceSummary,
  StrategyIn,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function getRace(year: number, event: string): Promise<RaceSummary> {
  return request(`/races/${year}/${encodeURIComponent(event)}`);
}

export function compareStrategies(params: {
  year: number;
  event: string;
  strategies: StrategyIn[];
  n_sims?: number;
  seed?: number;
}): Promise<CompareResponse> {
  return request("/strategy/compare", { method: "POST", body: JSON.stringify(params) });
}

export function optimizePitStop(params: {
  year: number;
  event: string;
  driver: string;
  current_compound: string;
  current_tyre_life: number;
  next_lap_number: number;
  total_race_laps?: number;
  compounds_used_so_far?: string[];
  lap_step?: number;
  n_sims?: number;
  seed?: number;
}): Promise<OptimizeResponse> {
  return request("/strategy/optimize", { method: "POST", body: JSON.stringify(params) });
}

export function simulateField(params: {
  year: number;
  event: string;
  n_sims?: number;
  seed?: number;
}): Promise<FieldResponse> {
  return request("/strategy/field", { method: "POST", body: JSON.stringify(params) });
}
