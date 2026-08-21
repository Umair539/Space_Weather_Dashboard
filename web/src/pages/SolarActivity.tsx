import { useMemo, useState } from "react";

import {
  api,
  formatUtc,
  parseApiTime,
  singleSeries,
  useApi,
  type SsnRow,
} from "../app_utils";
import { About, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import content from "../content.json";

const { title, subtitle, about } = content.pages.solarActivity;
// services.swpc.noaa.gov's image feed sits behind an AWS WAF challenge that
// blocks non-browser clients - and since these load as sub-resources, even
// real browsers can't solve that challenge for them. NASA SDO publishes
// pre-rendered rolling animations with no such block. 512px keeps each
// animation to a few MB instead of tens of MB at full resolution, and each
// only loads once someone plays it (see SolarCard) rather than all at once.
// The array itself lives in content.json - it's fixed metadata plus fixed
// NASA URLs, no different from the About text, and the prerender script
// needs the same data to bake real <img> tags into the static shell.
const SDO = content.sdoImages;

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
  return (
    <Panel title="Latest Solar View" subtitle="NASA SDO" pad>
      <div className="image-grid">
        {SDO.map((image) => (
          <SolarCard key={image.key} image={image} />
        ))}
      </div>
    </Panel>
  );
}

/**
 * Each still starts static (~0.6MB); the ~21MB animation only loads once
 * someone actually wants it. Hovering (or, on touch, the first tap) shows
 * a play icon over the still as a hint; clicking it fetches and starts the
 * animation. Playing shows the same hint as a pause icon, which drops the
 * video and reverts to the still.
 */
function SolarCard({ image }: { image: (typeof SDO)[number] }) {
  const [playing, setPlaying] = useState(false);

  return (
    <figure className="sdo-card">
      <button
        type="button"
        className="sdo-media-wrap"
        data-playing={playing}
        onClick={() => setPlaying((p) => !p)}
        aria-label={playing ? `Pause ${image.key} animation` : `Play ${image.key} animation`}
      >
        {playing ? (
          <video className="sdo-media" autoPlay loop muted playsInline aria-label={image.key}>
            <source src={image.video} type="video/mp4" />
          </video>
        ) : (
          <img className="sdo-media" src={image.still} alt={image.key} loading="lazy" />
        )}
        <span className="sdo-play" aria-hidden>
          {playing ? "⏸" : "▶"}
        </span>
      </button>
      <figcaption className="sdo-caption">
        <span className="sdo-badge" style={{ color: image.color }}>
          {image.badge}
        </span>
        <div className="sdo-sub">{image.subtitle}</div>
        <div className="sdo-desc">{image.description}</div>
      </figcaption>
    </figure>
  );
}

function SunspotPanel() {
  // Full cycle only - the daily/monthly ranges added little over the raw
  // ~12 years, which already renders fine at full resolution.
  const state = useApi(api.ssnFullCycle, [], 300_000);

  return (
    <Panel
      title="Sunspot Number"
      subtitle="daily"
      right={
        state.data?.length ? (
          <Span
            from={caption(state.data.at(0)?.time)}
            to={caption(state.data.at(-1)?.time)}
          />
        ) : null
      }
    >
      <Async state={state}>{(rows) => <SsnChart rows={rows} />}</Async>
    </Panel>
  );
}

function SsnChart({ rows }: { rows: SsnRow[] }) {
  const series = useMemo(
    () => [
      {
        name: "Sunspot number",
        color: singleSeries,
        points: toPoints(rows, "swpc_ssn"),
      },
      {
        name: "Monthly mean",
        color: "#fff",
        points: monthlyMeanPoints(rows),
      },
    ],
    [rows],
  );

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Sunspot count"
      tickFormat="%Y"
      height={340}
      ariaLabel="Sunspot number over time"
    />
  );
}

/** One point per calendar month, averaging whatever daily values it has -
 *  a trend line over the raw daily series, not a replacement for it. */
function monthlyMeanPoints(rows: SsnRow[]): [number, number | null][] {
  const buckets = new Map<number, { sum: number; count: number }>();
  for (const row of rows) {
    if (typeof row.swpc_ssn !== "number") continue;
    const d = parseApiTime(row.time);
    const month = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
    const bucket = buckets.get(month) ?? { sum: 0, count: 0 };
    bucket.sum += row.swpc_ssn;
    bucket.count += 1;
    buckets.set(month, bucket);
  }
  return [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([month, { sum, count }]) => [month, Math.round((sum / count) * 100) / 100]);
}

function caption(iso: string | undefined): string {
  if (!iso) return "—";
  return formatUtc(parseApiTime(iso), {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}
