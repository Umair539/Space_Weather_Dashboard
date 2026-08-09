import type { ReactNode } from "react";

/**
 * Reserves the chart's height so the page doesn't jump when data lands. A
 * poll refresh keeps the previous chart on screen, so this only ever shows
 * on the very first load.
 */
export function ChartSkeleton({ height = 400 }: { height?: number }) {
  return <div className="skeleton" role="status" aria-label="Loading" style={{ height }} />;
}

/**
 * The API being unreachable is the expected first-run failure (it has to be
 * started separately), so the message says how to fix it rather than just
 * reporting that something broke.
 */
export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="alert" role="alert">
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
  children: (data: T) => ReactNode;
}) {
  if (state.error) return <ErrorPanel message={state.error} />;
  if (state.data === undefined) return <ChartSkeleton height={height} />;
  return <>{children(state.data)}</>;
}
