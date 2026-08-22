import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { api, kpSeverity, useApi } from "../app_utils";
import content from "../content.json";

// url_path values match app/run_app.py's st.Page registrations, so links
// into either dashboard resolve the same way. Labels/icons come from
// content.json - the same data the build-time prerender script reads, so
// the nav can never drift between what's server-rendered and what React
// mounts.
const PAGES = content.site.nav.map((p) => ({ ...p, to: p.path, end: p.path === "/" }));

export function Layout() {
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden>
            {content.site.brandEmoji}
          </span>
          {content.site.name}
        </Link>
        <div className="topbar-spacer" />
        <LiveConditions />
        <SectionMenu />
      </header>
      <div className="page">
        <Outlet />
        <Footer />
      </div>
    </>
  );
}

/**
 * Compact section switcher. A dropdown anchored to the bar rather than a
 * sliding drawer - the nav is four links, so it doesn't warrant permanent
 * screen real estate or a full-height panel.
 */
function SectionMenu() {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();

  const current =
    PAGES.find((p) => (p.end ? pathname === p.to : pathname.startsWith(p.to))) ??
    PAGES[0];

  // Close on route change, so picking an item dismisses the menu.
  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (!menu.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="menu" ref={menu}>
      <button
        type="button"
        className="menu-button"
        aria-expanded={open}
        aria-haspopup="menu"
        // The label itself hides below the width breakpoint (CSS), leaving
        // an icon-only button - this keeps naming it for screen readers.
        aria-label={`Section: ${current.label}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="menu-button-icon" aria-hidden>
          {current.icon}
        </span>
        <span className="menu-button-label">{current.label}</span>
        <svg
          className="menu-chevron"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          {PAGES.map((page) => (
            <NavLink
              key={page.to}
              to={page.to}
              end={page.end}
              role="menuitem"
              className={({ isActive }) => (isActive ? "menu-item active" : "menu-item")}
            >
              <span className="menu-item-icon" aria-hidden>
                {page.icon}
              </span>
              {page.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

/** Current Kp, always visible - the headline number for "is anything happening". */
function LiveConditions() {
  const { data } = useApi((s) => api.kpLatest(s), [], 120_000);
  if (!data) return null;
  const { color, label } = kpSeverity(data.Kp);

  return (
    <div className="status-chip" title="Current planetary K-index">
      <span className="status-dot" style={{ background: color }} aria-hidden />
      Kp <strong>{data.Kp.toFixed(2)}</strong>
      <span style={{ color }}>{label}</span>
    </div>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <a
        href={content.site.githubLink}
        target="_blank"
        rel="noreferrer"
        aria-label="View this project on GitHub"
      >
        <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16" aria-hidden>
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8" />
        </svg>
      </a>
      <span>
        {content.site.footerPrefix}{" "}
        <a href={content.site.footerLink} target="_blank" rel="noreferrer">
          {content.site.footerLinkText}
        </a>
      </span>
    </footer>
  );
}
