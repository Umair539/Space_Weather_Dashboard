import { useMemo, useState } from "react";

import { api, type DstRow, type GeomagInterval, type KpRow } from "../api";
import { Expander, RangeCaption, RangeSelector } from "../components/Controls";
import { Async, ErrorPanel } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import { formatUtc, parseApiTime, useApi, useLastUpdated } from "../hooks";
import { dstColors, singleSeries } from "../theme";

const RANGES = [
  { value: "24h", label: "Last 24 Hours" },
  { value: "7d", label: "Last Week" },
  { value: "1mo", label: "Last Month" },
] as const;

export function GeomagIndices() {
  return (
    <>
      <h1>Geomagnetic Indices 📡</h1>
      <DstSection />
      <KpSection />
    </>
  );
}

function DstSection() {
  const lastUpdated = useLastUpdated();
  // Defaults to "Last Month", matching the Streamlit radio's index=2.
  const [range, setRange] = useState<GeomagInterval>("1mo");
  const state = useApi((s) => api.dst(range, s), [range], 120_000);

  return (
    <section aria-labelledby="dst-heading" style={{ marginTop: 8 }}>
      <div className="controls-row">
        <RangeSelector
          options={RANGES}
          value={range}
          onChange={setRange}
          legend="Dst time range"
        />
        <h2 id="dst-heading" style={{ fontSize: 20, textAlign: "center", margin: 0 }}>
          Dst Index
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

      <Async state={state}>{(rows) => <DstChart rows={rows} />}</Async>

      <Expander title="More information on Dst index">
        The Disturbance Storm Time (Dst) index is a measure of geomagnetic
        activity used to assess the severity of geomagnetic storms. It is
        expressed in nanoTeslas and is based on the average value of the
        horizontal component of the Earth's magnetic field measured at four
        near-equatorial geomagnetic observatories at hourly intervals. It
        measures the growth and recovery of the ring current in the Earth's
        magnetosphere. The lower these values get, the more energy is stored in
        Earth's magnetosphere. If the Dst index drops below -50 nT, this
        indicates a moderate storm is taking place, and below -100 nT indicates
        a severe storm taking place. The chart compares these observed
        measurements with the corresponding predicted values.
      </Expander>
    </section>
  );
}

function DstChart({ rows }: { rows: DstRow[] }) {
  const series = useMemo(
    () => [
      { name: "Observed Dst", color: dstColors.observed, points: toPoints(rows, "dst") },
      {
        name: "Model Prediction",
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
      ariaLabel="Observed and predicted Dst index"
    />
  );
}

function KpSection() {
  const lastUpdated = useLastUpdated();
  const [range, setRange] = useState<GeomagInterval>("1mo");
  const state = useApi((s) => api.kp(range, s), [range], 120_000);

  return (
    <section aria-labelledby="kp-heading" style={{ marginTop: 32 }}>
      <div className="controls-row">
        <RangeSelector
          options={RANGES}
          value={range}
          onChange={setRange}
          legend="Kp time range"
        />
        <h2 id="kp-heading" style={{ fontSize: 20, textAlign: "center", margin: 0 }}>
          Kp Index
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

      <Async state={state}>{(rows) => <KpChart rows={rows} />}</Async>

      <Expander title="More information on Kp index">
        The Kp-index is a geomagnetic activity index based on data from
        magnetometers around the world measured every 3 hours. The graph above
        displays the observed Kp-value from the Planetary K-index of the NOAA
        SWPC and can be used to make a rough estimate of the current global
        geomagnetic conditions. It is a quasi-logarithmic index from 0 to 9
        where a value of 5 indicates that a moderate storm is occuring, a value
        of 7 indicates a severe storm is occuring, and a value of 9 indicates an
        extreme storm is occuring.
      </Expander>
    </section>
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
