import type { Severity } from "../severity";
import { surface } from "../theme";

interface Props {
  label: string;
  value: string;
  unit?: string;
  severity: Severity;
}

/**
 * Stat tile - a current reading with its severity band. Ported from
 * _metric_card in app/views/home.py.
 *
 * Status is carried by the written label as well as the colour, so the band
 * is still readable without colour vision.
 */
export function MetricCard({ label, value, unit, severity }: Props) {
  return (
    <div
      style={{
        background: `linear-gradient(135deg, ${severity.color}22 0%, #161b2280 100%)`,
        border: `1px solid ${severity.color}55`,
        borderLeft: `4px solid ${severity.color}`,
        borderRadius: 8,
        padding: 16,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: surface.muted,
          textTransform: "uppercase",
          letterSpacing: 1,
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 30,
          fontWeight: 700,
          color: severity.color,
          lineHeight: 1.1,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
        {unit && (
          <span style={{ fontSize: 14, color: surface.muted, marginLeft: 3 }}>
            {unit}
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: 11,
          color: severity.color,
          marginTop: 5,
          textTransform: "uppercase",
          letterSpacing: 0.5,
        }}
      >
        {severity.label}
      </div>
    </div>
  );
}
