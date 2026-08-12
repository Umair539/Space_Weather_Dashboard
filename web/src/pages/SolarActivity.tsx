import { useMemo, useState } from "react";

import {
  api,
  formatUtc,
  parseApiTime,
  singleSeries,
  useApi,
  type SsnRow,
} from "../app_utils";
import { About, Segmented, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import content from "../content.json";

const { title, subtitle, about } = content.pages.solarActivity;
// services.swpc.noaa.gov's image feed sits behind an AWS WAF challenge that
// blocks non-browser clients - and since these load as sub-resources, even
// real browsers can't solve that challenge for them. NASA SDO publishes
// pre-rendered rolling animations with no such block. 512px keeps the total
// payload to ~21MB across all three instead of ~130MB at full resolution.
// The array itself lives in content.json - it's fixed metadata plus fixed
// NASA URLs, no different from the About text, and the prerender script
// needs the same data to bake real <img> tags into the static shell.
const SDO = content.sdoImages;

const RANGES = [
  { value: "1mo", label: "30 days" },
  { value: "1y", label: "1 year" },
  { value: "cycle", label: "Full cycle" },
] as const;

type Range = (typeof RANGES)[number]["value"];

export function SolarActivity() {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="stack">
        <SolarImages />
        <SunspotPanel />
      </div>
      <div style={{ marginTop: 16 }}>
        {about.map((section) => (
          <About key={section.title} title={section.title}>
            {section.body}
          </About>
        ))}
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
