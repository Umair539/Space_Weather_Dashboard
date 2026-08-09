import type { Severity } from "../severity";

interface Props {
  label: string;
  value: string;
  unit?: string;
  severity: Severity;
}

/**
 * Stat tile. Severity is a spine down the left edge plus the written band
 * name, rather than a wash across the whole tile - four tinted blocks side
 * by side compete with the charts, and the word carries the state without
 * relying on colour vision.
 */
export function MetricCard({ label, value, unit, severity }: Props) {
  return (
    <div className="metric" style={{ ["--metric-color" as string]: severity.color }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      <div className="metric-status">{severity.label}</div>
    </div>
  );
}
