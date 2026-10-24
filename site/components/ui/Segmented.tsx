"use client";

interface SegmentedProps<T extends string | number> {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}

/** Pill group for a single choice. Filters sit in one row above the chart they drive. */
export default function Segmented<T extends string | number>({ label, options, value, onChange }: SegmentedProps<T>) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 bg-surface-soft rounded-lg p-1">
      {options.map((o) => (
        <button
          key={String(o.value)}
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            o.value === value ? "bg-canvas text-ink shadow-[0_1px_2px_rgba(20,20,19,0.08)]" : "text-muted hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
