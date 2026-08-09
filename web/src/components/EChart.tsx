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
}

/**
 * Thin ECharts wrapper. Canvas rather than SVG deliberately: the 7-day solar
 * wind window is ~10k points per series, which as SVG would be tens of
 * thousands of DOM nodes for React to reconcile on every hover.
 */
export function EChart({ option, height, ariaLabel }: Props) {
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

  return (
    <div
      ref={container}
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height }}
    />
  );
}
