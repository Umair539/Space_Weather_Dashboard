import type { EChartsCoreOption } from "echarts/core";
import { useMemo } from "react";

import { formatUtc, parseApiTime, surface } from "../app_utils";
import { EChart } from "./EChart";

export interface Series {
  name: string;
  color: string;
  /** [epoch ms, value] - null values leave a genuine gap, never a zero. */
  points: [number, number | null][];
}

interface Props {
  series: Series[];
  yTitle: string;
  /** Axis tick format, matching the Altair `format` strings one for one. */
  tickFormat: "%b %d, %H:%M" | "%b %d %Y" | "%b %Y" | "%Y" | "%d %b";
  yMin?: number;
  yMax?: number;
  height?: number;
  ariaLabel: string;
}

const TICK_OPTIONS: Record<Props["tickFormat"], Intl.DateTimeFormatOptions> = {
  "%b %d, %H:%M": { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" },
  "%b %d %Y": { month: "short", day: "2-digit", year: "numeric" },
  "%b %Y": { month: "short", year: "numeric" },
  "%Y": { year: "numeric" },
  "%d %b": { day: "2-digit", month: "short" },
};

const HOUR_MS = 3_600_000;
const TICK_COUNT = 6;

/**
 * Explicit tick positions, anchored to whole hours near each true edge of
 * the data, evenly spread between - as opposed to leaving the axis's own
 * bounds untouched (they still match the real data exactly, so the line
 * always fills the full width) and separately controlling where labels
 * land within that.
 *
 * A rolling window (always "newest minus N") can start or end at any
 * arbitrary minute, and ECharts' automatic tick algorithm doesn't know or
 * care where the window's real edges are - it picks round hours aligned
 * to its own absolute clock grid, which can land anywhere from right at
 * an edge to hours short of it, by chance, differently every time new
 * data polls in. This computes the tick values directly instead: the
 * nearest hour at-or-after the true start, the nearest hour at-or-before
 * the true end, and evenly interpolated (then hour-snapped) points
 * between the two - so the first and last labelled ticks are always close
 * to the edges, not wherever the absolute clock grid happens to fall.
 */
function hourAnchoredTicks(series: Series[]): number[] | undefined {
  let min = Infinity;
  let max = -Infinity;
  for (const s of series) {
    for (const [t] of s.points) {
      if (t < min) min = t;
      if (t > max) max = t;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined;

  const first = Math.ceil(min / HOUR_MS) * HOUR_MS;
  const last = Math.floor(max / HOUR_MS) * HOUR_MS;
  if (last <= first) return [min, max];

  const ticks = new Set<number>();
  for (let i = 0; i < TICK_COUNT; i++) {
    const raw = first + ((last - first) * i) / (TICK_COUNT - 1);
    ticks.add(Math.round(raw / HOUR_MS) * HOUR_MS);
  }
  return [...ticks].sort((a, b) => a - b);
}

export function TimeSeriesChart({
  series,
  yTitle,
  tickFormat,
  yMin,
  yMax,
  height = 400,
  ariaLabel,
}: Props) {
  const option = useMemo<EChartsCoreOption>(() => {
    const label = (value: number) =>
      formatUtc(new Date(value), TICK_OPTIONS[tickFormat]);
    const ticks = hourAnchoredTicks(series);

    return {
      backgroundColor: "transparent",
      animation: false,
      // Room on the left for the axis title, and above only when a legend
      // is actually drawn. Right is wider than it looks like it needs to
      // be: the rightmost tick's label is centred on its point, so half
      // its width sits past the plot area - too little room here clips
      // that label against the container edge rather than wrapping or
      // hiding it.
      // left/right both carry two jobs: left fits the y-axis's own numbers
      // and rotated title, right has no furniture to fit at all - but both
      // also need to hold half of whichever x-axis label sits nearest that
      // edge, since ECharts centres a label on its tick rather than
      // clamping it inside the plot area.
      grid: {
        left: 72,
        right: 44,
        top: series.length > 1 ? 48 : 16,
        bottom: 44,
      },
      // A legend is required once identity is in play; with one series the
      // heading already names it, so the box would be noise.
      legend:
        series.length > 1
          ? {
              top: 0,
              left: 0,
              itemGap: 16,
              icon: "roundRect",
              itemWidth: 14,
              itemHeight: 3,
              // Text stays in ink, never the series colour - the swatch
              // beside it carries identity.
              textStyle: { color: surface.muted, fontSize: 12 },
            }
          : undefined,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross", label: { show: false } },
        backgroundColor: surface.panel,
        borderColor: surface.border,
        textStyle: { color: surface.text, fontSize: 12 },
        formatter: (params: unknown) => {
          const points = params as {
            axisValue: number;
            seriesName: string;
            color: string;
            value: [number, number | null];
          }[];
          if (!points.length) return "";
          const when = formatUtc(new Date(points[0].axisValue), {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
          const rows = points
            // A null dst (prediction with no observation yet) is omitted
            // rather than shown as an empty row.
            .filter((p) => p.value?.[1] !== null && p.value?.[1] !== undefined)
            .map(
              (p) =>
                `<div style="display:flex;gap:8px;align-items:center;margin-top:4px;">
                   <span style="width:8px;height:8px;border-radius:2px;background:${p.color};"></span>
                   <span style="color:${surface.muted};">${p.seriesName}</span>
                   <span style="margin-left:auto;font-variant-numeric:tabular-nums;">${p.value[1]}</span>
                 </div>`,
            )
            .join("");
          return `<div style="color:${surface.muted};font-size:11px;">${when} UTC</div>${rows}`;
        },
      },
      xAxis: {
        type: "time",
        // No min/max override - the axis matches the real data exactly,
        // so the line always fills the full width. Only which ticks get
        // labelled is controlled, via customValues below.
        axisLabel: {
          color: surface.muted,
          fontSize: 11,
          formatter: label,
          hideOverlap: true,
          customValues: ticks,
        },
        axisTick: { customValues: ticks, lineStyle: { color: surface.border } },
        axisLine: { lineStyle: { color: surface.border } },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: yTitle,
        nameLocation: "middle",
        nameGap: 46,
        nameTextStyle: { color: surface.muted, fontSize: 12 },
        min: yMin,
        max: yMax,
        // Fit the data instead of forcing a zero baseline. Solar wind speed
        // lives around 300-500 km/s and never approaches zero, so anchoring
        // at zero spent most of the plot on empty space. Series where zero
        // is meaningful (Kp, Dst) pass explicit bounds instead.
        scale: yMin === undefined && yMax === undefined,
        axisLabel: { color: surface.muted, fontSize: 11 },
        axisLine: { show: false },
        // Recessive grid: present enough to read a value against, quiet
        // enough that the line stays the figure.
        splitLine: { lineStyle: { color: surface.border, opacity: 0.4 } },
      },
      series: series.map((s) => ({
        name: s.name,
        type: "line",
        data: s.points,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 2, color: s.color },
        itemStyle: { color: s.color },
        emphasis: { disabled: true },
        // Canvas fast paths for the ~10k-point solar wind window.
        large: true,
        largeThreshold: 2000,
        sampling: "lttb",
      })),
    };
  }, [series, yTitle, tickFormat, yMin, yMax]);

  return <EChart option={option} height={height} ariaLabel={ariaLabel} />;
}

/** Rows from the API -> chart points, dropping absent columns safely. */
export function toPoints<T extends { time: string }>(
  rows: T[],
  key: keyof T,
): [number, number | null][] {
  return rows.map((row) => {
    const value = row[key];
    return [
      parseApiTime(row.time).getTime(),
      typeof value === "number" ? value : null,
    ];
  });
}
