"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ReactNode } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

interface FadeInProps {
  children: ReactNode;
  delay?: number;
  className?: string;
  direction?: "up" | "down" | "left" | "right" | "none";
}

/**
 * Fade/slide in on first view. Always renders a motion.div: the static HTML carries opacity 0, and
 * swapping in a plain div for reduced motion would leave that inline style in place after hydration
 * (content stays invisible). Reduced motion instead drops the offset and the duration.
 */
export default function FadeIn({ children, delay = 0, className, direction = "up" }: FadeInProps) {
  const reduce = useReducedMotion();

  const offset = {
    up: { y: 24, x: 0 },
    down: { y: -24, x: 0 },
    left: { x: 24, y: 0 },
    right: { x: -24, y: 0 },
    none: { x: 0, y: 0 },
  }[reduce ? "none" : direction];

  return (
    <motion.div
      initial={{ opacity: 0, ...offset }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, margin: "-64px" }}
      transition={reduce ? { duration: 0 } : { duration: 0.6, delay, ease: EASE }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
