import { NavLink, Outlet } from "react-router-dom";

import { surface } from "../theme";

// url_path values match app/run_app.py's st.Page registrations, so links
// into either dashboard resolve the same way.
const PAGES = [
  { to: "/", label: "Home", end: true },
  { to: "/solar-wind", label: "Solar Wind", end: false },
  { to: "/geomagnetic-indices", label: "Geomagnetic Indices", end: false },
  { to: "/solar-activity", label: "Solar Activity", end: false },
];

export function Layout() {
  return (
    <div className="app-shell">
      {/* The column stretches to the full page height so its panel fill is
          continuous; the nav inside it is what sticks to the viewport. */}
      <div className="sidebar-col">
        <nav aria-label="Sections" className="sidebar">
          {PAGES.map((page) => (
            <NavLink
              key={page.to}
              to={page.to}
              end={page.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {page.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <main className="content">
        <Outlet />
        <GithubLink />
      </main>
    </div>
  );
}

function GithubLink() {
  return (
    <div style={{ marginTop: 32 }}>
      <a
        href="https://github.com/Umair539/Space_Weather_Dashboard"
        target="_blank"
        rel="noreferrer"
        aria-label="View this project on GitHub"
        style={{ color: surface.muted, display: "inline-block" }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="40"
          height="40"
          fill="currentColor"
          viewBox="0 0 16 16"
          aria-hidden
        >
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8" />
        </svg>
      </a>
    </div>
  );
}
