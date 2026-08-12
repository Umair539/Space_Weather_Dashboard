import { useMemo, useState } from "react";

import {
  api,
  dstColors,
  formatUtc,
  parseApiTime,
  singleSeries,
  useApi,
  type DstRow,
  type GeomagInterval,
  type KpRow,
} from "../app_utils";
import { About, Segmented, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async, ErrorPanel } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import content from "../content.json";

const { title, subtitle, about } = content.pages.geomagIndices;

const RANGES = [
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
  { value: "1mo", label: "30 days" },
] as const;

export function GeomagIndices() {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="stack">
        <DstPanel />
        <KpPanel />
      </div>
      <div style={{ marginTop: 16 }} className="stack">
        {about.map((section) => (
          <About key={section.title} title={section.title}>
            {section.body}
          </About>
        ))}
      </div>
    </>
  );
}

function DstPanel() {
  // Defaults to 30 days, matching the Streamlit radio's index=2.
  const [range, setRange] = useState<GeomagInterval>("1mo");
  const state = useApi((s) => api.dst(range, s), [range], 120_000);

  return (
    <Panel
      title="Dst Index"
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
            legend="Dst time range"
          />
        </>
      }
    >
      <Async state={state}>{(rows) => <DstChart rows={rows} />}</Async>
    </Panel>
  );
}

function DstChart({ rows }: { rows: DstRow[] }) {
  const series = useMemo(
    () => [
      { name: "Observed", color: dstColors.observed, points: toPoints(rows, "dst") },
      {
        name: "Model prediction",
        color: dstColors.predicted,
        points: toPoints(rows, "dst_predictions"),
      },
    ],
    [rows],
  );

  const hasData = rows.some((r) => r.dst !== null || r.dst_predictions !== null);
  if (!hasData) return <ErrorPanel message="No Dst data in this window." />;

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Dst (nT)"
      tickFormat="%b %d, %H:%M"
      // No explicit min/max - see the identical note in Home.tsx's
      // DstChart. scale:true picks round, evenly-spaced ticks on its own.
      height={340}
      ariaLabel="Observed and predicted Dst index"
    />
  );
}

function KpPanel() {
  const [range, setRange] = useState<GeomagInterval>("1mo");
  const state = useApi((s) => api.kp(range, s), [range], 120_000);

  return (
    <Panel
      title="Kp Index"
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
            legend="Kp time range"
          />
        </>
      }
    >
      <Async state={state}>{(rows) => <KpChart rows={rows} />}</Async>
    </Panel>
  );
}

function KpChart({ rows }: { rows: KpRow[] }) {
  const series = useMemo(
    () => [{ name: "Kp", color: singleSeries, points: toPoints(rows, "Kp") }],
    [rows],
  );
  return (
    <TimeSeriesChart
      series={series}
      yTitle="Kp Index"
      tickFormat="%b %d, %H:%M"
      yMin={0}
      yMax={9}
      height={340}
      ariaLabel="Kp index over time"
    />
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
