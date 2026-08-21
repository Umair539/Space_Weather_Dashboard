import type { ReactNode } from "react";

/** Markdown-style `[text](url)` links, the only inline markup About bodies
 *  need - parsed by hand rather than pulling in a markdown renderer for one
 *  pattern. */
const LINK_PATTERN = /\[([^\]]+)\]\(([^)]+)\)/g;

function withLinks(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  for (const match of text.matchAll(LINK_PATTERN)) {
    const [full, label, href] = match;
    if (match.index! > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(
      <a key={key++} href={href} target="_blank" rel="noreferrer">
        {label}
      </a>,
    );
    lastIndex = match.index! + full.length;
  }
  parts.push(text.slice(lastIndex));
  return parts;
}

interface SegmentedProps<T extends string> {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  /** Distinguishes the two selectors on the geomagnetic page for a11y. */
  legend: string;
}

/**
 * Time-range picker as one segmented control rather than separate buttons -
 * it reads as a single choice of N, which is what it is. Real radio inputs
 * underneath, so arrow keys work and it's announced correctly.
 */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  legend,
}: SegmentedProps<T>) {
  return (
    <fieldset className="segmented">
      <legend className="visually-hidden">{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className={option.value === value ? "on" : undefined}>
          <input
            type="radio"
            name={legend}
            className="visually-hidden"
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}

interface ChipsProps<T extends string> {
  options: readonly { value: T; label: string; color: string }[];
  selected: readonly T[];
  onChange: (values: T[]) => void;
  legend: string;
}

/**
 * Feature picker. Each chip carries its own chart colour, so the mapping
 * from control to chart is visible before you select anything - and the
 * colour belongs to the parameter, so it never shifts with the selection.
 */
export function Chips<T extends string>({
  options,
  selected,
  onChange,
  legend,
}: ChipsProps<T>) {
  const toggle = (value: T) =>
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : // Keep canonical option order rather than click order, so the
          // charts below don't reshuffle as you select.
          options
            .filter((o) => o.value === value || selected.includes(o.value))
            .map((o) => o.value),
    );

  return (
    <fieldset className="chips">
      <legend className="visually-hidden">{legend}</legend>
      {options.map((option) => {
        const on = selected.includes(option.value);
        return (
          <label key={option.value} className={on ? "chip on" : "chip"}>
            <input
              type="checkbox"
              className="visually-hidden"
              checked={on}
              onChange={() => toggle(option.value)}
            />
            <span
              className="chip-swatch"
              aria-hidden
              style={{
                background: on ? option.color : "transparent",
                boxShadow: `inset 0 0 0 1px ${option.color}`,
              }}
            />
            {option.label}
          </label>
        );
      })}
    </fieldset>
  );
}

/** Collapsible explainer. Closed by default - it's reference, not the point. */
export function About({ title, children }: { title: string; children: string }) {
  // A blank line in the source string breaks it into separate paragraphs.
  return (
    <details className="about">
      <summary>{title}</summary>
      {children.split("\n\n").map((paragraph, i) => (
        <p key={i}>{withLinks(paragraph)}</p>
      ))}
    </details>
  );
}

/** "12 Jul 08:00 → 09 Aug 19:00", for a panel header's right side. */
export function Span({ from, to }: { from: string; to: string }) {
  return (
    <span>
      {from} <span style={{ opacity: 0.5 }}>→</span> {to}
    </span>
  );
}
