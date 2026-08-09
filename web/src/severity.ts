/**
 * Thresholds copied exactly from app/views/home.py's _kp_severity /
 * _dst_severity / _sw_severity / _bz_severity, so both dashboards classify a
 * given reading identically.
 */
import { severity, severityLabel, type SeverityLevel } from "./theme";

export interface Severity {
  level: SeverityLevel;
  label: string;
  color: string;
}

function of(level: SeverityLevel): Severity {
  return { level, label: severityLabel[level], color: severity[level] };
}

export function kpSeverity(kp: number): Severity {
  if (kp >= 8) return of("extreme");
  if (kp >= 7) return of("severe");
  if (kp >= 5) return of("moderate");
  if (kp >= 4) return of("minor");
  return of("quiet");
}

export function dstSeverity(dst: number): Severity {
  if (dst <= -200) return of("extreme");
  if (dst <= -100) return of("severe");
  if (dst <= -50) return of("moderate");
  if (dst <= -30) return of("minor");
  return of("quiet");
}

/** Solar wind speed and Bz top out at "Severe" - there is no Extreme band. */
export function speedSeverity(speed: number): Severity {
  if (speed >= 600) return of("severe");
  if (speed >= 500) return of("moderate");
  if (speed >= 450) return of("minor");
  return of("quiet");
}

export function bzSeverity(bz: number): Severity {
  if (bz <= -20) return of("severe");
  if (bz <= -10) return of("moderate");
  if (bz <= -5) return of("minor");
  return of("quiet");
}
