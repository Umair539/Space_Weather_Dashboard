import { useMemo, useState } from "react";

import {
  api,
  formatUtc,
  parseApiTime,
  singleSeries,
  useApi,
  useLastUpdated,
  type SsnRow,
} from "../app_utils";
import { About, Segmented, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";

// services.swpc.noaa.gov's image feed sits behind an AWS WAF challenge that
// blocks non-browser clients - and since these load as sub-resources, even
// real browsers can't solve that challenge for them. NASA SDO publishes
// pre-rendered rolling animations with no such block. 512px keeps the total
// payload to ~21MB across all three instead of ~130MB at full resolution.
const SDO = [
  {
    key: "Sunspots",
    badge: "SDO · HMI",
    color: "#e8913c",
    subtitle: "Continuum · visible light",
    description: "Active regions and sunspots on the photosphere",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_HMIIC.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_HMIIC.mp4",
  },
  {
    key: "Eruptions",
    badge: "SUVI · 304Å",
    color: "#f2564a",
    subtitle: "He II · chromosphere",
    description: "Filaments, prominences and coronal holes (75 MK)",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0304.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0304.mp4",
  },
  {
    key: "Flares",
    badge: "SUVI · 131Å",
    color: "#2dd4bf",
    subtitle: "Fe VIII/XXI · flare plasma",
    description: "High-energy flare and eruptive plasma (10 MK)",
    still: "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0131.jpg",
    video: "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0131.mp4",
  },
];

const RANGES = [
  { value: "1mo", label: "30 days" },
  { value: "1y", label: "1 year" },
  { value: "cycle", label: "Full cycle" },
] as const;

type Range = (typeof RANGES)[number]["value"];

export function SolarActivity() {
  const lastUpdated = useLastUpdated();

  return (
    <>
      <PageHeader
        title="Solar Activity"
        subtitle="The Sun's current face, and where we sit in its 11-year cycle."
        meta={lastUpdated}
      />
      <div className="stack">
        <SolarImages />
        <SunspotPanel />
      </div>
      <div style={{ marginTop: 16 }}>
        <About title="About the solar cycle">
          The Sun follows a periodic 11-year cycle driven by its internal magnetic
          field, which completely flips orientation once per decade. The progression is
          most visibly tracked by sunspot number — dark, cooler regions of intense
          magnetic activity. During solar minimum very few sunspots appear; solar
          maximum brings a high concentration, often with more frequent flares. A more
          active Sun releases a more turbulent stream of particles, which is what ties
          this cycle to everything else on this dashboard.
        </About>
      </div>
    </>
  );
}

function SolarImages() {
  // Animations are ~21MB total; stills are ~0.6MB. Default to stills and let
  // people opt into the heavier animated view.
  const [animate, setAnimate] = useState(false);

  return (
    <Panel
      title="Latest Solar View"
      subtitle="NASA SDO"
      right={
        <label style={{ display: "inline-flex", gap: 7, alignItems: "center", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={animate}
            onChange={(e) => setAnimate(e.target.checked)}
          />
          Animate (~21 MB)
        </label>
      }
      pad
    >
      <div className="image-grid">
        {SDO.map((image) => (
          <figure key={image.key} className="sdo-card">
            {animate ? (
              <video
                className="sdo-media"
                autoPlay
                loop
                muted
                playsInline
                aria-label={image.key}
              >
                <source src={image.video} type="video/mp4" />
              </video>
            ) : (
              <img className="sdo-media" src={image.still} alt={image.key} loading="lazy" />
            )}
            <figcaption className="sdo-caption">
              <span className="sdo-badge" style={{ color: image.color }}>
                {image.badge}
              </span>
              <div className="sdo-sub">{image.subtitle}</div>
              <div className="sdo-desc">{image.description}</div>
            </figcaption>
          </figure>
        ))}
      </div>
    </Panel>
  );
}

function SunspotPanel() {
  // Defaults to the full cycle, matching the Streamlit radio's index=2.
  const [range, setRange] = useState<Range>("cycle");
  const state = useApi(
    (signal) => (range === "cycle" ? api.ssnFullCycle(signal) : api.ssnRaw(range, signal)),
    [range],
    300_000,
  );

  // The x-axis span changes by two orders of magnitude across these ranges,
  // so the tick format has to change with it - days, months, then years.
  const tickFormat = range === "1mo" ? "%b %d %Y" : range === "1y" ? "%b %Y" : "%Y";

  return (
    <Panel
      title="Sunspot Number"
      subtitle={range === "cycle" ? "monthly mean" : "daily"}
      right={
        <>
          {state.data?.length ? (
            <Span
              from={caption(state.data.at(0)?.time)}
              to={caption(state.data.at(-1)?.time)}
            />
          ) : null}
          <Segmented
            options={RANGES}
            value={range}
            onChange={setRange}
            legend="Sunspot time range"
          />
        </>
      }
    >
      <Async state={state}>
        {(rows) => (
          <SsnChart rows={rows} tickFormat={tickFormat} monthly={range === "cycle"} />
        )}
      </Async>
    </Panel>
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
        name: monthly ? "Monthly mean" : "Sunspot number",
        color: singleSeries,
        points: toPoints(rows, "swpc_ssn"),
      },
    ],
    [rows, monthly],
  );

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Sunspot count"
      tickFormat={tickFormat}
      height={340}
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
