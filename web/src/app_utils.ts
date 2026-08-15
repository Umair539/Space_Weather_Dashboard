/**
 * The React equivalent of app/app_utils.py: everything the pages share that
 * isn't a rendered component, in one file - the API client, data fetching,
 * colours, and severity thresholds. Kept as one file deliberately, the same
 * way the Streamlit version was, rather than split by convention into
 * api.ts/hooks.ts/theme.ts/severity.ts; those existed briefly and were
 * merged back after the split turned out to cost more (four places to
 * check) than it saved.
 */

import { useEffect, useRef, useState } from "react";

/* ============================================================ API client
 * Typed client for the FastAPI caching layer (api/). One function per
 * endpoint, with the interval literals matching the server's Literal[...]
 * annotations - so an unsupported window is a compile error here rather
 * than a 422 at runtime.
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

/** OVATION nowcast point: [longitude -180..180, latitude, probability %]. */
export type AuroraPoint = [number, number, number];

export interface AuroraForecast {
  /** When the underlying solar wind measurement was taken. */
  observation_time: string | null;
  /** The time the forecast is *for* - roughly an hour ahead of observation. */
  forecast_time: string | null;
  max_probability: number;
  point_count: number;
  points: AuroraPoint[];
  retrieved_at?: string;
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

  aurora: (signal?: AbortSignal) => get<AuroraForecast>("/aurora", undefined, signal),
};

export const apiBaseUrl = BASE;

/* ============================================================ data fetching
 * React's answer to @st.cache_data(ttl=...): a hook that fetches on mount,
 * optionally re-polls, and hands back {data, error, loading}.
 */

export interface AsyncState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
}

/**
 * Fetch-on-mount plus optional polling, mirroring Streamlit's
 * `@st.fragment(run_every=120)`. `deps` is the dependency list that should
 * trigger a refetch - passed explicitly because `fetcher` is a fresh closure
 * on every render and can't be a dependency itself.
 *
 * A poll tick keeps the previous data visible while it refreshes, so a
 * routine background update doesn't blank the chart out - but a `deps`
 * change (the user picked a different range, a different set of feature
 * columns) is a genuinely different query, not a refresh of the same one.
 * The old rows can be actively wrong for it: they may be a different
 * time span (mismatched against a tickFormat/axis already computed for
 * the new range) or missing a newly-selected column entirely. So this
 * resets to loading only when the effect (re)starts - mount or a deps
 * change - and leaves it alone for ticks from the interval timer, which
 * fire without the effect restarting.
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  refreshMs?: number,
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: undefined,
    error: undefined,
    loading: true,
  });
  // Held in a ref so the polling effect never restarts when the callback
  // identity changes - only `deps` and `refreshMs` should restart it.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    setState({ data: undefined, error: undefined, loading: true });

    const load = async () => {
      try {
        const data = await fetcherRef.current(controller.signal);
        if (!cancelled) setState({ data, error: undefined, loading: false });
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: error instanceof ApiError ? error.message : String(error),
        }));
      }
    };

    void load();
    const timer = refreshMs ? setInterval(load, refreshMs) : undefined;
    return () => {
      cancelled = true;
      controller.abort();
      if (timer) clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refreshMs]);

  return state;
}

/**
 * The API serves naive timestamps that are already UTC, so they must be
 * formatted as UTC - letting the browser apply a local offset would shift
 * every label by the viewer's timezone.
 */
export function formatUtc(date: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat("en-GB", {
    ...options,
    timeZone: "UTC",
    hour12: false,
  })
    .format(date)
    .replace(",", "");
}

/** Naive ISO string from the API -> Date, pinned to UTC. */
export function parseApiTime(iso: string): Date {
  return new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
}

/* ============================================================ theme
 * Ported verbatim from the Streamlit dashboard so the two render the same
 * palette: .streamlit/config.toml for the surfaces, app/views/home.py for
 * the severity ramp, app/views/solar_wind.py for the per-parameter hues.
 *
 * The dashboard is dark-only by design (it's read in dark rooms, and the
 * SDO imagery is on black), so these are single values rather than
 * light/dark pairs.
 *
 * Mirrors the custom properties in index.css. Canvas charts can't read CSS
 * variables, so ECharts needs the literal values - these two must be kept
 * in step.
 */

export const surface = {
  bg: "#0b0e14",
  panel: "#12161f",
  raised: "#1b212c",
  border: "#232a36",
  text: "#e6edf3",
  muted: "#8b949e",
  faint: "#6b7280",
  accent: "#ff6f00",
} as const;

/** Status palette - reserved for severity, never reused as a series colour. */
export const severityColor = {
  extreme: "#9d1a8a",
  severe: "#c93030",
  moderate: "#e05d0b",
  minor: "#d29922",
  quiet: "#2ea043",
} as const;

export type SeverityLevel = keyof typeof severityColor;

export const severityLabel: Record<SeverityLevel, string> = {
  extreme: "Extreme",
  severe: "Severe",
  moderate: "Moderate",
  minor: "Minor",
  quiet: "Quiet",
};

/**
 * Colour follows the parameter, not its position in the selection - picking
 * "Bz" alone must give the same violet as picking it alongside seven others.
 */
export const paramColors = {
  speed: "#00bcd4",
  density: "#69db7c",
  temperature: "#f4c430",
  bz: "#c084fc",
  bx: "#60a5fa",
  by: "#2dd4bf",
  bt: "#fbbf24",
  pressure: "#fb923c",
} as const;

/** The two Dst series. Red is observation, white is the model. */
export const dstColors = {
  observed: "#ff0000",
  predicted: "#ffffff",
} as const;

/** Single-series charts (Kp, sunspot number) keep the original red. */
export const singleSeries = "#ff0000";

/** Kp gauge band fills - deep and desaturated so the value arc stays dominant. */
export const gaugeBands: [number, number, string][] = [
  [0, 4, "#16281a"],
  [4, 5, "#2d2408"],
  [5, 7, "#2f1a08"],
  [7, 8, "#2e1013"],
  [8, 9, "#25102a"],
];

/* ============================================================ severity
 * Thresholds copied exactly from app/views/home.py's _kp_severity /
 * _dst_severity / _sw_severity / _bz_severity, so both dashboards classify
 * a given reading identically.
 */

export interface Severity {
  level: SeverityLevel;
  label: string;
  color: string;
}

function severityOf(level: SeverityLevel): Severity {
  return { level, label: severityLabel[level], color: severityColor[level] };
}

export function kpSeverity(kp: number): Severity {
  if (kp >= 8) return severityOf("extreme");
  if (kp >= 7) return severityOf("severe");
  if (kp >= 5) return severityOf("moderate");
  if (kp >= 4) return severityOf("minor");
  return severityOf("quiet");
}

export function dstSeverity(dst: number): Severity {
  if (dst <= -200) return severityOf("extreme");
  if (dst <= -100) return severityOf("severe");
  if (dst <= -50) return severityOf("moderate");
  if (dst <= -30) return severityOf("minor");
  return severityOf("quiet");
}

/** Solar wind speed and Bz top out at "Severe" - there is no Extreme band. */
export function speedSeverity(speed: number): Severity {
  if (speed >= 600) return severityOf("severe");
  if (speed >= 500) return severityOf("moderate");
  if (speed >= 450) return severityOf("minor");
  return severityOf("quiet");
}

export function bzSeverity(bz: number): Severity {
  if (bz <= -20) return severityOf("severe");
  if (bz <= -10) return severityOf("moderate");
  if (bz <= -5) return severityOf("minor");
  return severityOf("quiet");
}
