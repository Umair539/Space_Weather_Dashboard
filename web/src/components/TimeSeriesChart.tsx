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

/** Date and time split onto their own line each, rather than run together as
 *  "13 Jul 15:00" - the only format here that carries both, and on the axis
 *  the two halves read as one heavier label unless something separates them. */
const DATE_PART: Intl.DateTimeFormatOptions = { month: "short", day: "2-digit" };
const TIME_PART: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };

const HOUR_MS = 3_600_000;
const TARGET_TICKS = 7;

// Which kind of calendar unit each format's ticks step through - hours (or
// whole days, which are just a 24h step) for anything with a day or finer
// in it, months/years for the two coarsest formats.
type TickKind = "hour" | "month" | "year";
const TICK_KIND: Record<Props["tickFormat"], TickKind> = {
  "%b %d, %H:%M": "hour",
  "%b %d %Y": "hour",
  "%d %b": "hour",
  "%b %Y": "month",
  "%Y": "year",
};

// Spacings to try, smallest first, until the span fits in TARGET_TICKS
// ticks - so a 24h chart gets one tick every 4h, a 7d chart one per
// midnight, a 30d chart one every 5 days, and so on, rather than a fixed
// count of ticks landing wherever that happens to divide the span.
// Every value here divides evenly into a day, so stepping from the Unix
// epoch (itself a UTC midnight) always lands on a round clock time or a
// midnight, never an arbitrary offset.
const HOUR_STEPS = [1, 2, 3, 4, 6, 8, 12, 24, 48, 72, 120, 144, 240, 360, 720];
// Calendar steps for the month/year axes. Both divide evenly into 12, so
// stepping from a fixed origin lands on the same months/years every time
// (Jan/Apr/Jul/Oct for a 3-month step) rather than drifting with wherever
// the data happens to start.
const CALENDAR_STEPS = [1, 2, 3, 4, 6, 12];

function hourTicks(min: number, max: number): number[] {
  for (const stepH of HOUR_STEPS) {
    const stepMs = stepH * HOUR_MS;
    const first = Math.ceil(min / stepMs) * stepMs;
    const last = Math.floor(max / stepMs) * stepMs;
    const count = last >= first ? Math.round((last - first) / stepMs) + 1 : 0;
    if (count <= TARGET_TICKS || stepH === HOUR_STEPS[HOUR_STEPS.length - 1]) {
      const ticks: number[] = [];
      for (let t = first; t <= last; t += stepMs) ticks.push(t);
      return ticks.length ? ticks : [min, max];
    }
  }
  return [min, max];
}

const monthIndex = (t: number) => {
  const d = new Date(t);
  return d.getUTCFullYear() * 12 + d.getUTCMonth();
};
const fromMonthIndex = (i: number) => Date.UTC(Math.floor(i / 12), i % 12, 1);

function calendarTicks(min: number, max: number, unit: "month" | "year"): number[] {
  const toIndex = unit === "month" ? monthIndex : (t: number) => new Date(t).getUTCFullYear();
  const fromIndex = unit === "month" ? fromMonthIndex : (i: number) => Date.UTC(i, 0, 1);
  const minIdx = toIndex(min);
  const maxIdx = toIndex(max);

  for (const step of CALENDAR_STEPS) {
    const first = Math.ceil(minIdx / step) * step;
    const last = Math.floor(maxIdx / step) * step;
    const count = last >= first ? Math.round((last - first) / step) + 1 : 0;
    if (count <= TARGET_TICKS || step === CALENDAR_STEPS[CALENDAR_STEPS.length - 1]) {
      const ticks: number[] = [];
      for (let i = first; i <= last; i += step) ticks.push(fromIndex(i));
      return ticks.length ? ticks : [min, max];
    }
  }
  return [min, max];
}

/**
 * Explicit tick positions, chosen at a calendar-nice spacing (whole hours,
 * days, months or years - never an arbitrary fraction of the span) and
 * anchored to a fixed origin, as opposed to leaving the axis's own bounds
 * untouched (they still match the real data exactly, so the line always
 * fills the full width) and separately controlling where labels land
 * within that.
 *
 * A rolling window (always "newest minus N") can start or end at any
 * arbitrary minute, and ECharts' automatic tick algorithm doesn't know or
 * care where the window's real edges are. This computes the tick values
 * directly instead, at the coarsest nice spacing that still keeps the
 * axis under TARGET_TICKS labels.
 */
function niceTicks(series: Series[], tickFormat: Props["tickFormat"]): number[] | undefined {
  let min = Infinity;
  let max = -Infinity;
  for (const s of series) {
    for (const [t] of s.points) {
      if (t < min) min = t;
      if (t > max) max = t;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined;

  const kind = TICK_KIND[tickFormat];
  return kind === "hour" ? hourTicks(min, max) : calendarTicks(min, max, kind);
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
    const label = (value: number) => {
      const date = new Date(value);
      // Wrapped onto two lines only for the format that carries both parts -
      // a date-only or year-only tick has nothing to split.
      if (tickFormat === "%b %d, %H:%M") {
        return `${formatUtc(date, DATE_PART)}\n${formatUtc(date, TIME_PART)}`;
      }
      return formatUtc(date, TICK_OPTIONS[tickFormat]);
    };
    const ticks = niceTicks(series, tickFormat);

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
        // Extra room when the label wraps to two lines - unwrapped labels
        // only need enough for one.
        bottom: tickFormat === "%b %d, %H:%M" ? 56 : 44,
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
          lineHeight: 14,
          formatter: label,
          // niceTicks already spaces these deliberately to avoid crowding -
          // both of ECharts' own thinning heuristics (hideOverlap, and the
          // default auto interval that applies even with customValues set)
          // were dropping some of them anyway, so both are switched off.
          hideOverlap: false,
          interval: 0,
          showMinLabel: true,
          showMaxLabel: true,
          customValues: ticks,
        },
        axisTick: { customValues: ticks, lineStyle: { color: surface.muted } },
        // onZero:false keeps the axis pinned to the bottom of the plot -
        // ECharts otherwise draws it through the y-axis's zero line, which
        // for a signed series (Bz, By, Bx) puts it through the middle of
        // the chart instead.
        axisLine: { onZero: false, lineStyle: { color: surface.muted } },
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
