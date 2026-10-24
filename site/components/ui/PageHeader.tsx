import { ReactNode } from "react";
import FadeIn from "./FadeIn";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}

export default function PageHeader({ eyebrow, title, children }: PageHeaderProps) {
  return (
    <section className="bg-canvas pt-20 pb-10 px-6 md:px-12">
      <div className="max-w-5xl mx-auto">
        <FadeIn>
          <p className="text-xs font-medium tracking-widest uppercase text-accent-steel mb-4">{eyebrow}</p>
          <h1
            className="font-display text-4xl md:text-5xl font-normal leading-tight text-ink mb-6"
            style={{ letterSpacing: "-1px" }}
          >
            {title}
          </h1>
          {children && <div className="text-base text-body leading-relaxed max-w-2xl">{children}</div>}
        </FadeIn>
      </div>
    </section>
  );
}
