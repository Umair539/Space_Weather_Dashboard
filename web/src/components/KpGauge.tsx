import type { EChartsCoreOption } from "echarts/core";
import { useMemo } from "react";

import { kpSeverity } from "../severity";
import { gaugeBands, surface } from "../theme";
import { EChart } from "./EChart";

const MIN = 0;
const MAX = 9;

/**
 * The Kp dial. A single headline reading, so it gets a gauge rather than a
 * chart - there is no series here, just "where does now sit on a 0-9 scale".
 *
 * Ported from the Plotly Indicator in app/views/home.py: same half-circle
 * sweep, same band fills, same 0-9 integer ticks, same value-arc rather than
 * a needle.
 */
export function KpGauge({ value }: { value: number }) {
  const { color, label } = kpSeverity(value);

  const option = useMemo<EChartsCoreOption>(() => {
    // ECharts wants cumulative fractions of the axis, Plotly wanted absolute
    // ranges - convert so the band table stays readable in theme.ts.
    const stops = gaugeBands.map(
      ([, end, fill]) => [(end - MIN) / (MAX - MIN), fill] as [number, string],
    );

    return {
      backgroundColor: "transparent",
      animation: false,
      series: [
        {
          type: "gauge",
          min: MIN,
          max: MAX,
          startAngle: 180,
          endAngle: 0,
          // A half-circle only fills the top of its box, so the centre sits
          // low and the radius is generous - otherwise the dial floats in a
          // block of dead space.
          center: ["50%", "82%"],
          radius: "96%",
          splitNumber: MAX,
          axisLine: { lineStyle: { width: 30, color: stops } },
          // The value arc. Sits inside the band ring so both stay legible.
          progress: {
            show: true,
            width: 30,
            itemStyle: { color, opacity: 0.95 },
          },
          pointer: { show: false },
          axisTick: {
            distance: -30,
            length: 5,
            lineStyle: { color: surface.border, width: 1 },
          },
          splitLine: {
            distance: -30,
            length: 10,
            lineStyle: { color: surface.border, width: 1 },
          },
          axisLabel: {
            distance: -22,
            color: surface.muted,
            fontSize: 11,
            formatter: (v: number) => String(Math.round(v)),
          },
          detail: {
            valueAnimation: false,
            offsetCenter: [0, "-8%"],
            fontSize: 52,
            fontWeight: 700,
            color,
            formatter: (v: number) => v.toFixed(2),
          },
          data: [{ value }],
        },
      ],
    };
  }, [value, color]);

  return (
    <EChart
      option={option}
      height={290}
      ariaLabel={`Kp index ${value.toFixed(2)} of 9, ${label} conditions`}
    />
  );
}
