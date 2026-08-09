import { surface } from "../theme";

/**
 * Placeholder that reserves the chart's height, so the page doesn't jump
 * when data lands - a poll refresh keeps the previous chart on screen, so
 * this only ever shows on the very first load.
 */
export function ChartSkeleton({ height = 400 }: { height?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading chart"
      style={{
        height,
        borderRadius: 8,
        border: `1px solid ${surface.border}`,
        background: `${surface.panel}55`,
        display: "grid",
        placeItems: "center",
        color: surface.muted,
        fontSize: 13,
      }}
    >
      Loading…
    </div>
  );
}

/**
 * The API being unreachable is the expected first-run failure (it has to be
 * started separately), so the message says how to fix it rather than just
 * reporting that something broke.
 */
export function ErrorPanel({ message }: { message: string }) {
  return (
    <div
      role="alert"
      style={{
        border: `1px solid ${surface.border}`,
        borderLeft: "4px solid #c93030",
        borderRadius: 8,
        padding: "14px 16px",
        background: `${surface.panel}80`,
        color: surface.text,
        fontSize: 14,
      }}
    >
      {message}
    </div>
  );
}

/** Renders whichever of loading / error / content applies. */
export function Async<T>({
  state,
  height,
  children,
}: {
  state: { data: T | undefined; error: string | undefined };
  height?: number;
  children: (data: T) => React.ReactNode;
}) {
  if (state.error) return <ErrorPanel message={state.error} />;
  if (state.data === undefined) return <ChartSkeleton height={height} />;
  return <>{children(state.data)}</>;
}
