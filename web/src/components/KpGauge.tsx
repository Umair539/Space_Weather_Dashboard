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
          // low. The radius leaves headroom for the tick labels, which are
          // drawn inside the band but still need clearance at 0 and 9.
          center: ["50%", "78%"],
          radius: "82%",
          splitNumber: MAX,
          axisLine: { lineStyle: { width: 24, color: stops } },
          // The value arc. Sits over the band ring so both stay legible.
          progress: {
            show: true,
            width: 24,
            itemStyle: { color, opacity: 0.95 },
          },
          pointer: { show: false },
          axisTick: {
            distance: -24,
            length: 4,
            lineStyle: { color: surface.border, width: 1 },
          },
          splitLine: {
            distance: -24,
            length: 8,
            lineStyle: { color: surface.border, width: 1 },
          },
          axisLabel: {
            distance: -18,
            color: surface.faint,
            fontSize: 10,
            formatter: (v: number) => String(Math.round(v)),
          },
          detail: {
            valueAnimation: false,
            offsetCenter: [0, "-6%"],
            fontSize: 44,
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
