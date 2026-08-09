import type { ReactNode } from "react";

/**
 * The unit every chart lives in: a titled surface with its metadata on the
 * right of the header. Charts sitting loose on the page under a centred
 * heading was the main thing that read as a notebook rather than a product.
 */
export function Panel({
  title,
  subtitle,
  right,
  pad,
  children,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  /** Padded body, for content that isn't a full-bleed chart. */
  pad?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      {(title || right) && (
        <header className="panel-head">
          {title && <span className="panel-title">{title}</span>}
          {subtitle && <span className="panel-sub">{subtitle}</span>}
          {right && <span className="panel-head-right">{right}</span>}
        </header>
      )}
      <div className={pad ? "panel-body pad" : "panel-body"}>{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  meta,
}: {
  title: string;
  subtitle?: string;
  meta?: ReactNode;
}) {
  return (
    <div className="page-header">
      <h1 className="page-title">{title}</h1>
      {subtitle && <p className="page-sub">{subtitle}</p>}
      {meta && <div className="page-meta">{meta}</div>}
    </div>
  );
}
