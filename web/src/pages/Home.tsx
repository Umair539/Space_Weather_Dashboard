import { useMemo } from "react";

import { api } from "../api";
import { KpGauge } from "../components/KpGauge";
import { MetricCard } from "../components/MetricCard";
import { Async, ChartSkeleton, ErrorPanel } from "../components/States";
import { TimeSeriesChart, toPoints } from "../components/TimeSeriesChart";
import { formatUtc, parseApiTime, useApi, useLastUpdated } from "../hooks";
import { bzSeverity, dstSeverity, kpSeverity, speedSeverity } from "../severity";
import { dstColors, surface } from "../theme";

// Matches the 120s st.fragment(run_every=...) on the Streamlit home page.
const REFRESH_MS = 120_000;

export function Home() {
  const lastUpdated = useLastUpdated();

  const dst = useApi((s) => api.dst("1mo", s), [], REFRESH_MS);
  const prediction = useApi((s) => api.dstNextPrediction(s), [], REFRESH_MS);
  const dstNow = useApi((s) => api.dstLatest(s), [], REFRESH_MS);
  const kpNow = useApi((s) => api.kpLatest(s), [], REFRESH_MS);
  const solarNow = useApi(
    (s) => api.solarWindLatest(["speed", "bz"], s),
    [],
    REFRESH_MS,
  );

  return (
    <>
      <h1>Space Weather Dashboard 🪐</h1>
      <p style={{ color: surface.text, maxWidth: "68ch" }}>
        This Space Weather Dashboard provides frequently updated data on key
        space environment properties, including solar wind parameters and
        geomagnetic indices, collected from the{" "}
        <a
          href="https://www.swpc.noaa.gov"
          target="_blank"
          rel="noreferrer"
          style={{ color: surface.accent }}
        >
          NOAA Space Weather Prediction Center
        </a>
        .
      </p>

      <div
        style={{
          textAlign: "right",
          fontStyle: "italic",
          color: surface.muted,
          fontSize: 13,
        }}
      >
        {lastUpdated}
      </div>

      <section aria-labelledby="dst-heading" style={{ marginTop: 8 }}>
        <div style={{ textAlign: "center" }}>
          <h2 id="dst-heading" style={{ fontSize: 24, marginBottom: 4 }}>
            Dst Index — Last Month
          </h2>
          <div style={{ fontSize: 14, color: surface.muted }}>
            {prediction.data
              ? `Predicted: ${prediction.data.dst_predictions.toFixed(2)} nT | ${predictionWindow(
                  prediction.data.time,
                )} UTC`
              : " "}
          </div>
        </div>
        <Async state={dst}>{(rows) => <DstChart rows={rows} />}</Async>
      </section>

      <section aria-labelledby="kp-heading" style={{ marginTop: 24 }}>
        <div style={{ textAlign: "center" }}>
          <h2 id="kp-heading" style={{ fontSize: 24, marginBottom: 4 }}>
            Kp Index
          </h2>
          <div
            style={{
              fontSize: 14,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: kpNow.data ? kpSeverity(kpNow.data.Kp).color : surface.muted,
            }}
          >
            {kpNow.data ? kpSeverity(kpNow.data.Kp).label : " "}
          </div>
        </div>
        <Async state={kpNow} height={350}>
          {(row) =>
            row ? <KpGauge value={row.Kp} /> : <ErrorPanel message="No Kp data." />
          }
        </Async>
      </section>

      <div className="metric-grid" style={{ marginTop: 12 }}>
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

      <Advisory />
    </>
  );
}

function DstChart({ rows }: { rows: import("../api").DstRow[] }) {
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

  // Padded 5 either side, matching the Altair scale domain - and computed
  // across both series so neither can leave the frame.
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

/** "08 Aug 19:00 - 20:00" - predictions are for the hour they open. */
function predictionWindow(iso: string): string {
  const start = parseApiTime(iso);
  const end = new Date(start.getTime() + 3_600_000);
  return `${formatUtc(start, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })} – ${formatUtc(end, { hour: "2-digit", minute: "2-digit" })}`;
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
    <section aria-labelledby="advisory-heading" style={{ marginTop: 32 }}>
      <h2 id="advisory-heading" style={{ fontSize: 20 }}>
        Official SWPC Advisory
      </h2>
      {state.data === undefined && !state.error ? (
        <ChartSkeleton height={120} />
      ) : (
        <pre
          style={{
            border: `1px solid ${surface.border}`,
            borderRadius: 8,
            padding: 16,
            background: `${surface.panel}80`,
            color: surface.text,
            fontSize: 12.5,
            lineHeight: 1.5,
            overflowX: "auto",
            whiteSpace: "pre-wrap",
            margin: 0,
          }}
        >
          {state.error ? "Advisory temporarily unavailable." : state.data}
        </pre>
      )}
      <p style={{ fontSize: 12, color: surface.muted, marginTop: 6 }}>
        Source: NOAA/SWPC Advisory Outlook
      </p>
    </section>
  );
}
