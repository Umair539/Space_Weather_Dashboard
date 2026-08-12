// Bakes the genuinely static parts of each page - headings, About-section
// prose, the SDO image gallery, nav, footer - into real HTML at build time,
// so a crawler (or a link-preview bot, or a slow connection) sees real
// content immediately instead of the empty <div id="root"> React starts
// from. Charts, live readings, and anything else that depends on a fetch
// are deliberately left out: they were never candidates for this, since
// they don't exist yet at build time and would just be stale.
//
// No headless browser, no new dependency: this reads the exact same
// content.json the React components render from, and turns it into HTML
// with plain string templates - the two can't drift, because there's only
// one copy of the words.
//
// createRoot(...).render() (main.tsx) fully replaces whatever is inside
// #root on mount - it doesn't try to reconcile against it - so this is
// safe to prepopulate: real content is visible immediately, then React
// swaps in the live, interactive version a moment later. Not hydration,
// just an overwrite.

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const content = JSON.parse(readFileSync(join(root, "src/content.json"), "utf8"));
const template = readFileSync(join(root, "dist/index.html"), "utf8");

const escape = (s) =>
  String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function renderAbout(sections) {
  return sections
    .map(
      (s) => `
        <details class="about">
          <summary>${escape(s.title)}</summary>
          <p>${escape(s.body)}</p>
        </details>`,
    )
    .join("");
}

// Only the solar-activity route has anything genuinely static to show here
// (the still images and their fixed captions) - matches SolarImages() in
// pages/SolarActivity.tsx, minus the animate toggle, which is interactive
// and has nothing to show before JS runs anyway.
function renderSdoPanel() {
  const cards = content.sdoImages
    .map(
      (img) => `
          <figure class="sdo-card">
            <img class="sdo-media" src="${escape(img.still)}" alt="${escape(img.key)}" loading="lazy">
            <figcaption class="sdo-caption">
              <span class="sdo-badge" style="color:${escape(img.color)}">${escape(img.badge)}</span>
              <div class="sdo-sub">${escape(img.subtitle)}</div>
              <div class="sdo-desc">${escape(img.description)}</div>
            </figcaption>
          </figure>`,
    )
    .join("");

  return `
      <section class="panel">
        <header class="panel-head">
          <span class="panel-title">Latest Solar View</span>
          <span class="panel-sub">NASA SDO</span>
        </header>
        <div class="panel-body pad">
          <div class="image-grid">${cards}
          </div>
        </div>
      </section>`;
}

function renderShell(page, bodyExtra) {
  const nav = content.site.nav
    .map((p) => `<a href="${p.path}">${escape(p.label)}</a>`)
    .join("");

  return `
    <header class="topbar">
      <a href="/" class="brand">
        <span class="brand-mark" aria-hidden="true">${content.site.brandEmoji}</span>
        ${escape(content.site.name)}
      </a>
      <div class="topbar-spacer"></div>
      <nav class="static-nav" aria-label="Sections">${nav}</nav>
    </header>
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">${escape(page.title)}</h1>
        <p class="page-sub">${escape(page.subtitle)}</p>
      </div>
      ${bodyExtra}
      ${renderAbout(page.about)}
      <footer class="footer">
        <a href="${content.site.githubLink}" target="_blank" rel="noreferrer" aria-label="View this project on GitHub">GitHub</a>
        <span>${escape(content.site.footerPrefix)}
          <a href="${content.site.footerLink}" target="_blank" rel="noreferrer">${escape(content.site.footerLinkText)}</a>
        </span>
      </footer>
    </div>`;
}

for (const [key, page] of Object.entries(content.pages)) {
  const extra = key === "solarActivity" ? renderSdoPanel() : "";
  const html = template
    .replace(/<title>.*?<\/title>/s, `<title>${escape(page.documentTitle)}</title>`)
    .replace(
      /<meta\s+name="description"\s+content=".*?"\s*\/>/s,
      `<meta name="description" content="${escape(page.subtitle)}" />`,
    )
    .replace('<div id="root"></div>', `<div id="root">${renderShell(page, extra)}</div>`);

  const outDir = page.path === "/" ? "dist" : join("dist", page.path.replace(/^\//, ""));
  const outFile = join(outDir, "index.html");
  mkdirSync(join(root, outDir), { recursive: true });
  writeFileSync(join(root, outFile), html);
  console.log(`prerendered ${page.path} -> ${outFile}`);
}
