import { useMemo } from "react";

import { api, type DstRow } from "../api";
import { MetricCard } from "../components/MetricCard";
import { PageHeader, Panel } from "../components/Panel";
import { Async, ChartSkeleton, ErrorPanel } from "../components/States";
import { KpGauge } from "../components/KpGauge";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import { formatUtc, parseApiTime, useApi, useLastUpdated } from "../hooks";
import { bzSeverity, dstSeverity, kpSeverity, speedSeverity } from "../severity";
import { dstColors } from "../theme";

// Matches the 120s st.fragment(run_every=...) on the Streamlit home page.
const REFRESH_MS = 120_000;

export function Home() {
  const lastUpdated = useLastUpdated();

  const dst = useApi((s) => api.dst("1mo", s), [], REFRESH_MS);
  const prediction = useApi((s) => api.dstNextPrediction(s), [], REFRESH_MS);
  const dstNow = useApi((s) => api.dstLatest(s), [], REFRESH_MS);
  const kpNow = useApi((s) => api.kpLatest(s), [], REFRESH_MS);
  const solarNow = useApi((s) => api.solarWindLatest(["speed", "bz"], s), [], REFRESH_MS);

  return (
    <>
      <PageHeader
        title="Current Conditions"
        subtitle="Solar wind parameters and geomagnetic indices, updated continuously from the NOAA Space Weather Prediction Center."
        meta={lastUpdated}
      />

      {/* The four readings lead, before any chart - they answer "what is it
          doing right now", which the charts then put in context. */}
      <div className="metric-grid">
        {kpNow.data && (
          <MetricCard
            label="Kp Index"
            value={kpNow.data.Kp.toFixed(2)}
            severity={kpSeverity(kpNow.data.Kp)}
          />
        )}
        {dstNow.data && (
          <MetricCard
            label="Dst Index"
            value={signed(dstNow.data.dst, 0)}
            unit="nT"
            severity={dstSeverity(dstNow.data.dst)}
          />
        )}
        {solarNow.data?.speed !== undefined && (
          <MetricCard
            label="Solar Wind"
            value={solarNow.data.speed.toFixed(0)}
            unit="km/s"
            severity={speedSeverity(solarNow.data.speed)}
          />
        )}
        {solarNow.data?.bz !== undefined && (
          <MetricCard
            label="IMF Bz"
            value={signed(solarNow.data.bz, 1)}
            unit="nT"
            severity={bzSeverity(solarNow.data.bz)}
          />
        )}
      </div>

      <div className="stack" style={{ marginTop: 16 }}>
        <Panel
          title="Dst Index"
          subtitle="last 30 days"
          right={
            prediction.data ? (
              <span>
                next hour{" "}
                <strong style={{ color: "var(--text)", fontVariantNumeric: "tabular-nums" }}>
                  {prediction.data.dst_predictions.toFixed(2)} nT
                </strong>{" "}
                · {predictionWindow(prediction.data.time)} UTC
              </span>
            ) : null
          }
        >
          <Async state={dst}>{(rows) => <DstChart rows={rows} />}</Async>
        </Panel>

        <div className="split">
          <Panel title="Planetary K-index" subtitle="now">
            <Async state={kpNow} height={290}>
              {(row) =>
                row ? <KpGauge value={row.Kp} /> : <ErrorPanel message="No Kp data." />
              }
            </Async>
          </Panel>
          <Advisory />
        </div>
      </div>
    </>
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

  // Padded 5 either side and computed across both series, so neither can
  // leave the frame.
  const values = rows
    .flatMap((r) => [r.dst, r.dst_predictions])
    .filter((v): v is number => v !== null);
  if (!values.length) return <ErrorPanel message="No Dst data in this window." />;

  return (
    <TimeSeriesChart
      series={series}
      yTitle="Dst (nT)"
      tickFormat="%d %b"
      yMin={Math.min(...values) - 5}
      yMax={Math.max(...values) + 5}
      ariaLabel="Observed and predicted Dst index over the last month"
    />
  );
}

/** "09 Aug 19:00 – 20:00" - predictions are for the hour they open. */
function predictionWindow(iso: string): string {
  const start = parseApiTime(iso);
  const end = new Date(start.getTime() + 3_600_000);
  return `${formatUtc(start, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })}–${formatUtc(end, { hour: "2-digit", minute: "2-digit" })}`;
}

function signed(value: number, digits: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

const ADVISORY_URL = "https://services.swpc.noaa.gov/text/advisory-outlook.txt";

/**
 * Fetched straight from NOAA rather than through our API - the endpoint
 * sends Access-Control-Allow-Origin: *, so the browser can read it directly
 * and there's nothing to proxy.
 */
function Advisory() {
  const state = useApi(
    async (signal) => {
      const response = await fetch(ADVISORY_URL, { signal });
      if (!response.ok) throw new Error("Advisory temporarily unavailable.");
      const text = await response.text();
      const marker = "**** SPACE WEATHER OUTLOOK ****";
      if (text.includes(marker)) return text.split(marker).pop()!.trim();
      return text.trim() || "Advisory temporarily unavailable.";
    },
    [],
    3_600_000,
  );

  return (
    <Panel title="SWPC Advisory Outlook" right={<span>NOAA / SWPC</span>}>
      {state.data === undefined && !state.error ? (
        <ChartSkeleton height={140} />
      ) : (
        <pre className="advisory">
          {state.error ? "Advisory temporarily unavailable." : state.data}
        </pre>
      )}
    </Panel>
  );
}
