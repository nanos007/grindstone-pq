import { ReactNode } from "react";

interface SectionBandProps {
  children: ReactNode;
  className?: string;
  dark?: boolean;
  card?: boolean;
  id?: string;
}

export default function SectionBand({
  children,
  className = "",
  dark = false,
  card = false,
  id,
}: SectionBandProps) {
  const base = dark
    ? "bg-surface-dark text-on-dark"
    : card
    ? "bg-surface-card"
    : "bg-canvas";

  return (
    <section
      id={id}
      className={`py-14 md:py-20 lg:py-24 px-6 md:px-12 ${base} ${className}`}
    >
      <div className="max-w-5xl mx-auto">{children}</div>
    </section>
  );
}
