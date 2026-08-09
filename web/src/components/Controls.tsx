import { surface } from "../theme";

interface RangeSelectorProps<T extends string> {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  /** Distinguishes the two selectors on the geomagnetic page for a11y. */
  legend: string;
}

/**
 * The horizontal time-range radio. A real radiogroup rather than styled
 * buttons, so arrow keys work and the choice is announced as one of N.
 */
export function RangeSelector<T extends string>({
  options,
  value,
  onChange,
  legend,
}: RangeSelectorProps<T>) {
  return (
    <fieldset
      style={{
        border: "none",
        margin: 0,
        padding: 0,
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      <legend className="visually-hidden">{legend}</legend>
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <label
            key={option.value}
            style={{
              cursor: "pointer",
              padding: "6px 14px",
              borderRadius: 6,
              fontSize: 13,
              whiteSpace: "nowrap",
              color: selected ? surface.text : surface.muted,
              background: selected ? surface.panel : "transparent",
              border: `1px solid ${selected ? surface.accent : surface.border}`,
            }}
          >
            <input
              type="radio"
              name={legend}
              className="visually-hidden"
              checked={selected}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        );
      })}
    </fieldset>
  );
}

interface MultiSelectProps<T extends string> {
  options: readonly { value: T; label: string; color: string }[];
  selected: readonly T[];
  onChange: (values: T[]) => void;
  legend: string;
}

/**
 * Feature picker. Each option carries its own chart colour as a swatch, so
 * the mapping from control to chart is visible before you select anything -
 * and the colour never shifts with the size of the selection.
 */
export function MultiSelect<T extends string>({
  options,
  selected,
  onChange,
  legend,
}: MultiSelectProps<T>) {
  const toggle = (value: T) =>
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : // Keep the canonical option order rather than click order, so
          // charts don't reshuffle as you select.
          options.filter((o) => o.value === value || selected.includes(o.value)).map((o) => o.value),
    );

  return (
    <fieldset
      style={{
        border: "none",
        margin: 0,
        padding: 0,
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      <legend
        style={{ fontSize: 13, color: surface.muted, padding: 0, marginBottom: 8 }}
      >
        {legend}
      </legend>
      {options.map((option) => {
        const on = selected.includes(option.value);
        return (
          <label
            key={option.value}
            style={{
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 7,
              padding: "6px 12px",
              borderRadius: 6,
              fontSize: 13,
              color: on ? surface.text : surface.muted,
              background: on ? surface.panel : "transparent",
              border: `1px solid ${on ? option.color : surface.border}`,
            }}
          >
            <input
              type="checkbox"
              className="visually-hidden"
              checked={on}
              onChange={() => toggle(option.value)}
            />
            <span
              aria-hidden
              style={{
                width: 9,
                height: 9,
                borderRadius: 2,
                background: on ? option.color : "transparent",
                border: `1px solid ${option.color}`,
              }}
            />
            {option.label}
          </label>
        );
      })}
    </fieldset>
  );
}

/** The "More information on ..." disclosure, open by default as in Streamlit. */
export function Expander({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <details
      open
      style={{
        border: `1px solid ${surface.border}`,
        borderRadius: 8,
        padding: "12px 16px",
        marginTop: 24,
        background: `${surface.panel}80`,
      }}
    >
      <summary style={{ cursor: "pointer", fontSize: 14, color: surface.text }}>
        {title}
      </summary>
      <p style={{ color: surface.muted, lineHeight: 1.65, marginBottom: 0 }}>
        {children}
      </p>
    </details>
  );
}

/** "Displaying data from X to Y" + the freshness line, right-aligned. */
export function RangeCaption({
  from,
  to,
  lastUpdated,
}: {
  from: string;
  to: string;
  lastUpdated: string;
}) {
  return (
    <div style={{ textAlign: "right", fontSize: 13 }}>
      <div style={{ color: surface.text }}>
        Displaying data from {from} to {to}
      </div>
      <div style={{ fontStyle: "italic", color: surface.muted }}>{lastUpdated}</div>
    </div>
  );
}
