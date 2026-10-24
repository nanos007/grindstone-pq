interface StatTileProps {
  label: string;
  value: string;
  note?: string;
  dark?: boolean;
}

/** Figure tile: sentence-case label, sans semibold value (never the display serif), optional note. */
export default function StatTile({ label, value, note, dark = false }: StatTileProps) {
  return (
    <div className={`${dark ? "bg-surface-dark-elevated" : "bg-surface-card"} rounded-xl p-6 h-full`}>
      <p className={`text-sm mb-2 ${dark ? "text-on-dark-soft" : "text-muted"}`}>{label}</p>
      <p className={`text-3xl font-semibold tracking-tight ${dark ? "text-on-dark" : "text-ink"}`}>{value}</p>
      {note && <p className={`text-xs mt-2 leading-relaxed ${dark ? "text-on-dark-soft" : "text-muted"}`}>{note}</p>}
    </div>
  );
}
