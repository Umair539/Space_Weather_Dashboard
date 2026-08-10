import { useMemo, useState } from "react";

import {
  api,
  dstColors,
  formatUtc,
  parseApiTime,
  singleSeries,
  useApi,
  useLastUpdated,
  type DstRow,
  type GeomagInterval,
  type KpRow,
} from "../app_utils";
import { About, Segmented, Span } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async, ErrorPanel } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";

const RANGES = [
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
  { value: "1mo", label: "30 days" },
] as const;

export function GeomagIndices() {
  const lastUpdated = useLastUpdated();

  return (
    <>
      <PageHeader
        title="Geomagnetic Indices"
        subtitle="How strongly Earth's magnetic field is currently being disturbed."
        meta={lastUpdated}
      />
      <div className="stack">
        <DstPanel />
        <KpPanel />
      </div>
      <div style={{ marginTop: 16 }} className="stack">
        <About title="About the Dst index">
          The Disturbance Storm Time index measures geomagnetic storm severity in
          nanoTeslas, from the average horizontal magnetic field at four
          near-equatorial observatories, hourly. It tracks the growth and recovery of
          the ring current in Earth's magnetosphere — the lower the value, the more
          energy is stored there. Below −50 nT indicates a moderate storm, below
          −100 nT a severe one. The chart compares observations against the model's
          predictions.
        </About>
        <About title="About the Kp index">
          The Kp index is a geomagnetic activity index derived from magnetometers
          around the world, measured every three hours. It is quasi-logarithmic from
          0 to 9, where 5 indicates a moderate storm, 7 a severe storm, and 9 an
          extreme storm.
        </About>
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

  const values = rows
    .flatMap((r) => [r.dst, r.dst_predictions])
    .filter((v): v is number => v !== null);
  if (!values.length) return <ErrorPanel message="No Dst data in this window." />;

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Dst (nT)"
      tickFormat="%b %d, %H:%M"
      yMin={Math.min(...values) - 5}
      yMax={Math.max(...values) + 5}
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
