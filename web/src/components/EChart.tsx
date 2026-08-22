import * as echarts from "echarts/core";
import { GaugeChart, LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

// Registered once at module scope. Tree-shaken imports rather than the full
// `echarts` bundle - this pulls roughly a third of it.
echarts.use([
  LineChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

interface Props {
  option: echarts.EChartsCoreOption;
  height: number;
  /** Announced to screen readers, which can't read a canvas. */
  ariaLabel: string;
  /**
   * Fixed pixel width instead of filling the container. The chart itself
   * sits in a horizontally-scrollable wrapper, so a narrow (mobile) viewport
   * scrolls to see the rest rather than squeezing the axis labels together.
   */
  width?: number;
}

/**
 * Thin ECharts wrapper. Canvas rather than SVG deliberately: the 7-day solar
 * wind window is ~10k points per series, which as SVG would be tens of
 * thousands of DOM nodes for React to reconcile on every hover.
 */
export function EChart({ option, height, ariaLabel, width }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts>(null);

  useEffect(() => {
    if (!container.current) return;
    const instance = echarts.init(container.current, undefined, {
      renderer: "canvas",
    });
    chart.current = instance;

    // ECharts needs an explicit resize; a ResizeObserver covers both window
    // resizes and the sidebar collapsing, which a window listener misses.
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(container.current);

    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    // notMerge: deselecting a series must remove it, not leave the previous
    // one merged underneath.
    chart.current?.setOption(option, { notMerge: true });
  }, [option]);

  const canvas = (
    <div
      ref={container}
      role="img"
      aria-label={ariaLabel}
      style={{ width: width ?? "100%", height }}
    />
  );

  // Fixed-width charts need their own scroll wrapper - without one a narrow
  // viewport would just clip the chart against the container edge instead
  // of letting it scroll into view.
  return width === undefined ? canvas : <div className="chart-scroll">{canvas}</div>;
}
