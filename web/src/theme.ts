/**
 * Ported verbatim from the Streamlit dashboard so the two render the same
 * palette: .streamlit/config.toml for the surfaces, app/views/home.py for the
 * severity ramp, app/views/solar_wind.py for the per-parameter hues.
 *
 * The dashboard is dark-only by design (it's read in dark rooms, and the SDO
 * imagery is on black), so these are single values rather than light/dark
 * pairs.
 */

export const surface = {
  bg: "#0d1117", // config.toml backgroundColor
  panel: "#161b22", // config.toml secondaryBackgroundColor
  border: "#30363d",
  text: "#e6edf3",
  muted: "#8b949e",
  accent: "#ff6f00", // config.toml primaryColor
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

/** Kp gauge band fills - deep, desaturated so the needle stays dominant. */
export const gaugeBands: [number, number, string][] = [
  [0, 4, "#0d2b0d"],
  [4, 5, "#2d2200"],
  [5, 7, "#2d1500"],
  [7, 8, "#2d0000"],
  [8, 9, "#200020"],
];
