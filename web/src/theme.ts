/**
 * Ported verbatim from the Streamlit dashboard so the two render the same
 * palette: .streamlit/config.toml for the surfaces, app/views/home.py for the
 * severity ramp, app/views/solar_wind.py for the per-parameter hues.
 *
 * The dashboard is dark-only by design (it's read in dark rooms, and the SDO
 * imagery is on black), so these are single values rather than light/dark
 * pairs.
 */

/**
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

/**
 * Status palette - reserved for severity, never reused as a series colour.
 * Thresholds live with the data in severity.ts.
 */
export const severity = {
  extreme: "#9d1a8a",
  severe: "#c93030",
  moderate: "#e05d0b",
  minor: "#d29922",
  quiet: "#2ea043",
} as const;

export type SeverityLevel = keyof typeof severity;

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
