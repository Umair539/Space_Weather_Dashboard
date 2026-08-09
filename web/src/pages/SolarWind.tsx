import { useMemo, useState } from "react";

import { SOLAR_COLUMNS, api, type SolarColumn, type SolarRow } from "../api";
import { Expander, MultiSelect, RangeCaption, RangeSelector } from "../components/Controls";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import { formatUtc, parseApiTime, useApi, useLastUpdated } from "../hooks";
import { paramColors, surface } from "../theme";

const RANGES = [
  { value: "24h", label: "Last 24 Hours" },
  { value: "7d", label: "Last Week" },
  { value: "1mo", label: "Last Month" },
] as const;

type Range = (typeof RANGES)[number]["value"];

// Axis titles, copied from the `label` dict in app/views/solar_wind.py.
const AXIS_TITLES: Record<SolarColumn, string> = {
  density: "Particle density (p/cm3)",
  speed: "Solar wind speed (km/s)",
  temperature: "Solar wind temperature (K)",
  pressure: "Solar wind dynamic pressure (nPa)",
  bz: "IMF Z-component (nT)",
  by: "IMF Y-component (nT)",
  bx: "IMF X-component (nT)",
  bt: "IMF magnitude (nT)",
};

const titleCase = (column: SolarColumn) =>
  column.charAt(0).toUpperCase() + column.slice(1);

const OPTIONS = SOLAR_COLUMNS.map((c) => ({
  value: c,
  label: titleCase(c),
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
      // "Last Month" is served pre-aggregated to hourly means (the API
      // applies the same complete-hours-only rule the old SQL did), so it's
      // a different endpoint rather than a different interval.
      range === "1mo"
        ? api.solarWindMonthly(features, signal)
        : api.solarWindRaw(range, features, signal),
    [range, key],
    120_000,
  );

  return (
    <>
      <h1>Solar Wind Properties 🛰️</h1>

      <MultiSelect
        options={OPTIONS}
        selected={features}
        onChange={(values) => setFeatures(values)}
        legend="Select features"
      />

      <div className="controls-row">
        <RangeSelector
          options={RANGES}
          value={range}
          onChange={setRange}
          legend="Solar wind time range"
        />
        <Async state={state} height={20}>
          {(rows) => (
            <RangeCaption
              from={captionTime(rows.at(0)?.time)}
              to={captionTime(rows.at(-1)?.time)}
              lastUpdated={lastUpdated}
            />
          )}
        </Async>
      </div>

      {features.length === 0 && (
        <p style={{ color: surface.muted }}>
          Select a feature above to plot it.
        </p>
      )}

      <Async state={state}>
        {(rows) => (
          <>
            {features.map((feature) => (
              <FeatureChart
                key={feature}
                feature={feature}
                rows={rows}
                monthly={range === "1mo"}
              />
            ))}
          </>
        )}
      </Async>

      <Expander title="More information on Solar Wind">
        The solar wind is a continuous stream of charged particles (plasma)
        emitted by the Sun's atmosphere. When this stream of particles reaches
        Earth, it transfers energy into the Earth's magnetosphere. Solar wind is
        made up of two components: the properties of the plasma (e.g. speed and
        density), and the properties of the embedded magnetic field, which is
        called the Interplanetary Magnetic Field (IMF). Geomagnetic storms are
        typically triggered due to high speed solar wind combined with a strong
        IMF in the southward direction (Z-component). Storm intensity increases
        as the Bz value becomes more negative.
      </Expander>
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
        name: titleCase(feature),
        color: paramColors[feature],
        points: toPoints(rows, feature),
      },
    ],
    [rows, feature],
  );

  return (
    <section aria-labelledby={`sw-${feature}`} style={{ marginTop: 8 }}>
      <h2
        id={`sw-${feature}`}
        style={{ textAlign: "center", fontSize: 20, marginBottom: 4 }}
      >
        Solar Wind {titleCase(feature)}
        {monthly && (
          <span style={{ fontSize: 13, color: surface.muted, marginLeft: 8 }}>
            hourly mean
          </span>
        )}
      </h2>
      <TimeSeriesChart
        series={series}
        yTitle={AXIS_TITLES[feature]}
        tickFormat="%b %d, %H:%M"
        ariaLabel={`${titleCase(feature)} over time`}
      />
    </section>
  );
}

function captionTime(iso: string | undefined): string {
  if (!iso) return "—";
  return formatUtc(parseApiTime(iso), {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
