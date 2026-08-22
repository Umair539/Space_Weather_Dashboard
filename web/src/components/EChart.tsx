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
   * Floor on the chart's width; above it the chart fills its container. The
   * chart sits in a horizontally-scrollable wrapper, so a narrow (mobile)
   * viewport scrolls to see the rest rather than squeezing the axis labels
   * together, while a wide one gets the whole width rather than leaving the
   * panel half empty.
   */
  minWidth?: number;
  /**
   * The chart's rendered width, on mount and on every resize. Lets a caller
   * scale things that depend on how much room there actually is - axis tick
   * density, chiefly - which the option alone can't know.
   */
  onResize?: (width: number) => void;
}

/**
 * Thin ECharts wrapper. Canvas rather than SVG deliberately: the 7-day solar
 * wind window is ~10k points per series, which as SVG would be tens of
 * thousands of DOM nodes for React to reconcile on every hover.
 */
export function EChart({ option, height, ariaLabel, minWidth, onResize }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts>(null);

  // Read through a ref so a caller can pass an inline callback without the
  // observer being torn down and rebuilt on every render.
  const resizeCallback = useRef(onResize);
  resizeCallback.current = onResize;

  useEffect(() => {
    if (!container.current) return;
    const instance = echarts.init(container.current, undefined, {
      renderer: "canvas",
    });
    chart.current = instance;

    // ECharts needs an explicit resize; a ResizeObserver covers both window
    // resizes and the sidebar collapsing, which a window listener misses.
    const observer = new ResizeObserver(() => {
      instance.resize();
      resizeCallback.current?.(instance.getWidth());
    });
    observer.observe(container.current);
    resizeCallback.current?.(instance.getWidth());

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
      // width:100% resolves against the scroll wrapper's visible width, so
      // the chart grows with the panel; minWidth then holds the floor and
      // pushes the overflow into the wrapper instead of compressing the plot.
      style={{ width: "100%", minWidth, height }}
    />
  );

  // Charts with a width floor need their own scroll wrapper - without one a
  // narrow viewport would just clip the chart against the container edge
  // instead of letting it scroll into view.
  return minWidth === undefined ? canvas : <div className="chart-scroll">{canvas}</div>;
}
