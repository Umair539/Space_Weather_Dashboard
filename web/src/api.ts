/**
 * Typed client for the FastAPI caching layer (api/). One function per
 * endpoint, with the interval literals matching the server's Literal[...]
 * annotations - so an unsupported window is a compile error here rather than
 * a 422 at runtime.
 */

const BASE = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export const SOLAR_COLUMNS = [
  "density",
  "speed",
  "temperature",
  "bz",
  "bx",
  "by",
  "bt",
  "pressure",
] as const;

export type SolarColumn = (typeof SOLAR_COLUMNS)[number];

/** Every row carries "time"; value columns are present only when requested. */
export type SolarRow = { time: string } & Partial<Record<SolarColumn, number>>;
/** "dst" is null where a prediction has no matching observation yet. */
export interface DstRow {
  time: string;
  dst: number | null;
  dst_predictions: number;
}
export interface DstObservation {
  time: string;
  dst: number;
}
export interface DstPrediction {
  time: string;
  dst_predictions: number;
}
export interface KpRow {
  time: string;
  Kp: number;
}
export interface SsnRow {
  time: string;
  swpc_ssn: number;
}
export interface Health {
  status: "ok" | "warming_up";
  tables: Record<string, { rows: number; last_updated_at: string | null }>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(
  path: string,
  params?: Record<string, string | string[] | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(BASE + path);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined) continue;
    // Repeated key per item is what FastAPI's list[str] Query expects
    for (const v of Array.isArray(value) ? value : [value]) {
      url.searchParams.append(key, v);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (cause) {
    if (signal?.aborted) throw cause;
    throw new ApiError(
      `Could not reach the API at ${BASE}. Start it with \`run_api\` or set VITE_API_BASE_URL.`,
    );
  }
  if (!response.ok) {
    // The API returns {"detail": "..."} for 400s; surface it rather than a
    // bare status code, since it names the offending column.
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body - keep the status line */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export type SolarInterval = "24h" | "7d";
export type GeomagInterval = "24h" | "7d" | "1mo";
export type SsnInterval = "1mo" | "1y";

export const api = {
  solarWindRaw: (
    interval: SolarInterval,
    columns?: readonly SolarColumn[],
    signal?: AbortSignal,
  ) =>
    get<SolarRow[]>(
      "/solar-wind/raw",
      { interval, columns: columns as string[] | undefined },
      signal,
    ),

  solarWindMonthly: (columns?: readonly SolarColumn[], signal?: AbortSignal) =>
    get<SolarRow[]>(
      "/solar-wind/monthly",
      { columns: columns as string[] | undefined },
      signal,
    ),

  solarWindLatest: (columns?: readonly SolarColumn[], signal?: AbortSignal) =>
    get<SolarRow | null>(
      "/solar-wind/latest",
      { columns: columns as string[] | undefined },
      signal,
    ),

  dst: (interval: GeomagInterval, signal?: AbortSignal) =>
    get<DstRow[]>("/dst", { interval }, signal),

  dstLatest: (signal?: AbortSignal) =>
    get<DstObservation | null>("/dst/latest", undefined, signal),

  dstNextPrediction: (signal?: AbortSignal) =>
    get<DstPrediction | null>("/dst/next-prediction", undefined, signal),

  kp: (interval: GeomagInterval, signal?: AbortSignal) =>
    get<KpRow[]>("/kp", { interval }, signal),

  kpLatest: (signal?: AbortSignal) =>
    get<KpRow | null>("/kp/latest", undefined, signal),

  ssnRaw: (interval: SsnInterval, signal?: AbortSignal) =>
    get<SsnRow[]>("/ssn/raw", { interval }, signal),

  ssnFullCycle: (signal?: AbortSignal) =>
    get<SsnRow[]>("/ssn/full-cycle", undefined, signal),

  health: (signal?: AbortSignal) => get<Health>("/health", undefined, signal),
};

export const apiBaseUrl = BASE;
