import {
  api,
  auroraSeverity,
  bzSeverity,
  dstSeverity,
  speedSeverity,
  useApi,
} from "../app_utils";
import { KpGauge } from "../components/KpGauge";
import { MetricCard } from "../components/MetricCard";
import { PageHeader, Panel } from "../components/Panel";
import { Async, ChartSkeleton, ErrorPanel } from "../components/States";
import content from "../content.json";

const { title, subtitle } = content.pages.home;

// Matches the 120s st.fragment(run_every=...) on the Streamlit home page.
const REFRESH_MS = 120_000;

export function Home() {
  const dstNow = useApi((s) => api.dstLatest(s), [], REFRESH_MS);
  const kpNow = useApi((s) => api.kpLatest(s), [], REFRESH_MS);
  const aurora = useApi((s) => api.aurora(s), [], REFRESH_MS);
  const solarNow = useApi((s) => api.solarWindLatest(["speed", "bz"], s), [], REFRESH_MS);

  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />

      {/* The four readings lead - they answer what it is doing right now. */}
      <div className="metric-grid">
        {aurora.data && (
          <MetricCard
            label="Aurora Chance"
            value={aurora.data.max_probability.toFixed(0)}
            unit="%"
            severity={auroraSeverity(aurora.data.max_probability)}
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
