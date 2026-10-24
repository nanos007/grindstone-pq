interface BadgePillProps {
  children: React.ReactNode;
  variant?: "default" | "coral" | "steel" | "muted";
}

export default function BadgePill({ children, variant = "default" }: BadgePillProps) {
  const variants = {
    default: "bg-surface-card text-ink",
    coral: "bg-primary text-on-primary",
    steel: "bg-accent-steel text-white",
    muted: "bg-surface-soft text-muted",
  };

  return (
    <span
      className={`inline-block text-xs font-medium tracking-widest uppercase px-3 py-1 rounded-full ${variants[variant]}`}
    >
      {children}
    </span>
  );
}
