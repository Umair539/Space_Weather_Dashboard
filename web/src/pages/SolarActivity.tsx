import { useMemo, useState } from "react";

import { api, type SsnRow } from "../api";
import { Expander, RangeCaption, RangeSelector } from "../components/Controls";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import { formatUtc, parseApiTime, useApi, useLastUpdated } from "../hooks";
import { singleSeries, surface } from "../theme";

// services.swpc.noaa.gov's image feed sits behind an AWS WAF challenge that
// blocks non-browser clients - and since these load as sub-resources, even
// real browsers can't solve that challenge for them. NASA SDO publishes
// pre-rendered rolling animations with no such block. 512px keeps the total
// payload to ~21MB across all three instead of ~130MB at full resolution.
const SDO = [
  {
    key: "Sunspots (Visible/HMI)",
    badge: "SDO / HMI",
    color: "#e05d0b",
    subtitle: "Continuum · Visible Light",
    description: "Active regions and sunspots on the photosphere",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_HMIIC.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_HMIIC.mp4",
  },
  {
    key: "Solar Eruptions (Red/304Å)",
    badge: "GOES SUVI · 304Å",
    color: "#f82f0c",
    subtitle: "He II · Chromosphere / Transition Region",
    description: "Filaments, prominences and coronal holes (75 MK)",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0304.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0304.mp4",
  },
  {
    key: "Solar Flares (Teal/131Å)",
    badge: "GOES SUVI · 131Å",
    color: "#2dd4bf",
    subtitle: "Fe VIII/XXI · Flare Plasma",
    description: "High-energy flare and eruptive plasma (10 MK)",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0131.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0131.mp4",
  },
];

const RANGES = [
  { value: "1mo", label: "Last Month" },
  { value: "1y", label: "Last Year" },
  { value: "cycle", label: "Last Full Cycle" },
] as const;

type Range = (typeof RANGES)[number]["value"];

export function SolarActivity() {
  return (
    <>
      <h1>Solar Activity ☀️</h1>
      <SolarImages />
      <SunspotSection />
    </>
  );
}

function SolarImages() {
  // Animations are ~21MB total; stills are ~0.6MB. Default to stills and let
  // people opt into the heavier animated view.
  const [animate, setAnimate] = useState(false);

  return (
    <section aria-labelledby="imagery-heading">
      <div className="controls-row">
        <h2 id="imagery-heading" style={{ fontSize: 20, margin: 0 }}>
          Latest Solar View
        </h2>
        <label
          style={{
            fontSize: 13,
            color: surface.muted,
            display: "inline-flex",
            gap: 8,
            alignItems: "center",
            cursor: "pointer",
            justifySelf: "end",
          }}
        >
          <input
            type="checkbox"
            checked={animate}
            onChange={(e) => setAnimate(e.target.checked)}
          />
          Animate (~21MB)
        </label>
      </div>

      <div className="image-grid">
        {SDO.map((image) => (
          <figure key={image.key} style={{ margin: 0 }}>
            <figcaption
              style={{
                border: `1px solid ${image.color}55`,
                borderRadius: 8,
                padding: "12px 14px",
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  border: `1px solid ${image.color}`,
                  color: image.color,
                  borderRadius: 4,
                  padding: "3px 10px",
                  fontWeight: 700,
                  letterSpacing: 1,
                  fontSize: 12,
                }}
              >
                {image.badge}
              </span>
              <div style={{ color: "#c9d1d9", marginTop: 8, fontSize: 13 }}>
                {image.subtitle}
              </div>
              <div
                style={{
                  color: `${image.color}cc`,
                  fontStyle: "italic",
                  marginTop: 4,
                  fontSize: 13,
                }}
              >
                {image.description}
              </div>
            </figcaption>
            {animate ? (
              <video
                autoPlay
                loop
                muted
                playsInline
                aria-label={image.key}
                style={{ width: "100%", aspectRatio: "1/1", borderRadius: 8, display: "block" }}
              >
                <source src={image.video} type="video/mp4" />
              </video>
            ) : (
              <img
                src={image.still}
                alt={image.key}
                loading="lazy"
                style={{ width: "100%", aspectRatio: "1/1", borderRadius: 8, display: "block" }}
              />
            )}
          </figure>
        ))}
      </div>
    </section>
  );
}

function SunspotSection() {
  const lastUpdated = useLastUpdated();
  // Defaults to "Last Full Cycle", matching the Streamlit radio's index=2.
  const [range, setRange] = useState<Range>("cycle");

  const state = useApi(
    (signal) =>
      range === "cycle" ? api.ssnFullCycle(signal) : api.ssnRaw(range, signal),
    [range],
    300_000,
  );

  // The x-axis span changes by two orders of magnitude across these ranges,
  // so the tick format has to change with it - days, months, then years.
  const tickFormat =
    range === "1mo" ? "%b %d %Y" : range === "1y" ? "%b %Y" : "%Y";

  return (
    <section aria-labelledby="ssn-heading" style={{ marginTop: 32 }}>
      <div className="controls-row">
        <RangeSelector
          options={RANGES}
          value={range}
          onChange={setRange}
          legend="Sunspot time range"
        />
        <h2 id="ssn-heading" style={{ fontSize: 20, textAlign: "center", margin: 0 }}>
          Sunspots
        </h2>
        <Async state={state} height={20}>
          {(rows) => (
            <RangeCaption
              from={caption(rows.at(0)?.time)}
              to={caption(rows.at(-1)?.time)}
              lastUpdated={lastUpdated}
            />
          )}
        </Async>
      </div>

      <Async state={state}>
        {(rows) => <SsnChart rows={rows} tickFormat={tickFormat} monthly={range === "cycle"} />}
      </Async>

      <Expander title="More information on Solar Activity">
        The Sun follows a periodic 11-year cycle of activity driven by its
        internal magnetic field, which completely flips its orientation once per
        decade. This progression is most visibly tracked by the number of
        sunspots, which are dark, cooler regions of intense magnetic activity on
        the surface of the sun that indicate how active the Sun is. During solar
        minimum, very few sunspots are observed, whereas solar maximum brings a
        high concentration of spots, often leading to more frequent solar
        flares. These cycles are closely linked to the solar wind, as a more
        active Sun releases a more turbulent stream of particles that can impact
        Earth's magnetic field.
      </Expander>
    </section>
  );
}

function SsnChart({
  rows,
  tickFormat,
  monthly,
}: {
  rows: SsnRow[];
  tickFormat: "%b %d %Y" | "%b %Y" | "%Y";
  monthly: boolean;
}) {
  const series = useMemo(
    () => [
      {
        name: monthly ? "Monthly mean sunspot number" : "Sunspot number",
        color: singleSeries,
        points: toPoints(rows, "swpc_ssn"),
      },
    ],
    [rows, monthly],
  );

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Sunspot Count"
      tickFormat={tickFormat}
      ariaLabel="Sunspot number over time"
    />
  );
}

function caption(iso: string | undefined): string {
  if (!iso) return "—";
  return formatUtc(parseApiTime(iso), {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}
