import { ReactNode } from "react";

interface FeatureCardProps {
  children: ReactNode;
  className?: string;
  dark?: boolean;
}

export default function FeatureCard({ children, className = "", dark = false }: FeatureCardProps) {
  const base = dark
    ? "bg-surface-dark-elevated text-on-dark"
    : "bg-surface-card text-ink";

  return (
    <div className={`${base} rounded-xl p-8 ${className}`}>{children}</div>
  );
}
