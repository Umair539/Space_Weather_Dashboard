import { useMemo, useState } from "react";

import {
  SOLAR_COLUMNS,
  api,
  formatUtc,
  paramColors,
  parseApiTime,
  useApi,
  useLastUpdated,
  type SolarColumn,
  type SolarRow,
} from "../app_utils";
import { About, Chips, Segmented, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";

const RANGES = [
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
  { value: "1mo", label: "30 days" },
] as const;

type Range = (typeof RANGES)[number]["value"];

// Axis titles, copied from the `label` dict in app/views/solar_wind.py.
const AXIS_TITLES: Record<SolarColumn, string> = {
  density: "Particle density (p/cm³)",
  speed: "Speed (km/s)",
  temperature: "Temperature (K)",
  pressure: "Dynamic pressure (nPa)",
  bz: "IMF Bz (nT)",
  by: "IMF By (nT)",
  bx: "IMF Bx (nT)",
  bt: "IMF magnitude (nT)",
};

const PANEL_TITLES: Record<SolarColumn, string> = {
  density: "Particle Density",
  speed: "Wind Speed",
  temperature: "Temperature",
  pressure: "Dynamic Pressure",
  bz: "IMF Bz",
  by: "IMF By",
  bx: "IMF Bx",
  bt: "IMF Magnitude",
};

const OPTIONS = SOLAR_COLUMNS.map((c) => ({
  value: c,
  label: PANEL_TITLES[c],
  color: paramColors[c],
}));

export function SolarWind() {
  const lastUpdated = useLastUpdated();
  const [range, setRange] = useState<Range>("24h");
  const [features, setFeatures] = useState<SolarColumn[]>(["speed", "bz"]);

  // Requesting only the selected columns cuts the 7-day payload roughly
  // 2.5x versus asking for all eight.
  const key = features.join(",");
  const state = useApi(
    (signal) =>
      // "30 days" is served pre-aggregated to hourly means (the API applies
      // the same complete-hours-only rule the old SQL did), so it's a
      // different endpoint rather than a different interval.
      range === "1mo"
        ? api.solarWindMonthly(features, signal)
        : api.solarWindRaw(range, features, signal),
    [range, key],
    120_000,
  );

  return (
    <>
      <PageHeader
        title="Solar Wind"
        subtitle="Plasma and interplanetary magnetic field measured at L1, one minute apart."
        meta={lastUpdated}
      />

      <div className="toolbar">
        <Segmented
          options={RANGES}
          value={range}
          onChange={setRange}
          legend="Solar wind time range"
        />
        <Chips
          options={OPTIONS}
          selected={features}
          onChange={setFeatures}
          legend="Select measurements"
        />
      </div>

      {features.length === 0 ? (
        <Panel pad>
          <span style={{ color: "var(--muted)", fontSize: 13.5 }}>
            Select a measurement above to plot it.
          </span>
        </Panel>
      ) : (
        <Async state={state}>
          {(rows) => (
            <div className="stack">
              {features.map((feature) => (
                <FeatureChart
                  key={feature}
                  feature={feature}
                  rows={rows}
                  monthly={range === "1mo"}
                />
              ))}
            </div>
          )}
        </Async>
      )}

      <div style={{ marginTop: 16 }}>
        <About title="About the solar wind">
          The solar wind is a continuous stream of charged particles (plasma) emitted
          by the Sun's atmosphere. When this stream reaches Earth, it transfers energy
          into the magnetosphere. It has two components: the properties of the plasma
          (speed, density, temperature) and those of the embedded magnetic field, the
          Interplanetary Magnetic Field. Geomagnetic storms are typically triggered by
          high-speed solar wind combined with a strong southward IMF — storm intensity
          increases as the Bz value becomes more negative.
        </About>
      </div>
    </>
  );
}

function FeatureChart({
  feature,
  rows,
  monthly,
}: {
  feature: SolarColumn;
  rows: SolarRow[];
  monthly: boolean;
}) {
  const series = useMemo(
    () => [
      {
        name: PANEL_TITLES[feature],
        color: paramColors[feature],
        points: toPoints(rows, feature),
      },
    ],
    [rows, feature],
  );

  return (
    <Panel
      title={
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <span
            aria-hidden
            style={{
              width: 8,
              height: 8,
              borderRadius: 2,
              background: paramColors[feature],
            }}
          />
          {PANEL_TITLES[feature]}
        </span>
      }
      subtitle={monthly ? "hourly mean" : undefined}
      right={
        rows.length ? (
          <Span from={caption(rows.at(0)?.time)} to={caption(rows.at(-1)?.time)} />
        ) : null
      }
    >
      <TimeSeriesChart
        series={series}
        yTitle={AXIS_TITLES[feature]}
        tickFormat="%b %d, %H:%M"
        height={320}
        ariaLabel={`${PANEL_TITLES[feature]} over time`}
      />
    </Panel>
  );
}

function caption(iso: string | undefined): string {
  if (!iso) return "—";
  return formatUtc(parseApiTime(iso), {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
