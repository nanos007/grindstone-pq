"use client";

import Link from "next/link";
import { motion, useReducedMotion, Variants } from "framer-motion";
import { ArrowRight } from "lucide-react";

const EASE = [0.22, 1, 0.36, 1] as const;

/** Grind visual: WOTS+C retries the counter until the digest's base-w digits sum to S (decorative). */
function GrindGlyph() {
  const reduce = useReducedMotion();
  const rows = [
    { ctr: "00000000", sum: 231, ok: false },
    { ctr: "00000001", sum: 252, ok: false },
    { ctr: "00000002", sum: 244, ok: false },
    { ctr: "00000003", sum: 227, ok: false },
    { ctr: "00000004", sum: 238, ok: false },
    { ctr: "00000005", sum: 240, ok: true },
  ];
  return (
    <div className="bg-surface-dark rounded-2xl p-6 font-mono text-xs text-on-dark-soft shadow-sm" aria-hidden>
      <p className="text-on-dark mb-4">grind(m, S = 240)</p>
      <ul className="space-y-2">
        {rows.map((r, i) => (
          <motion.li
            key={r.ctr}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={reduce ? { duration: 0 } : { delay: 0.5 + i * 0.18, duration: 0.4, ease: EASE }}
            className="flex justify-between gap-4"
          >
            <span>ctr {r.ctr}</span>
            <span className={r.ok ? "text-accent-teal" : ""}>
              Σaᵢ = {r.sum} {r.ok ? "✓" : ""}
            </span>
          </motion.li>
        ))}
      </ul>
      <p className="mt-4 pt-4 border-t border-surface-dark-elevated">6 tries · no checksum chains in the signature</p>
    </div>
  );
}

export default function Hero() {
  const reduce = useReducedMotion();
  // Same variants either way (see FadeIn): reduced motion only removes the offset and the duration.
  const container: Variants = { hidden: {}, visible: { transition: { staggerChildren: reduce ? 0 : 0.12 } } };
  const item: Variants = {
    hidden: { opacity: 0, y: reduce ? 0 : 24 },
    visible: { opacity: 1, y: 0, transition: reduce ? { duration: 0 } : { duration: 0.7, ease: EASE } },
  };

  return (
    <section className="bg-canvas py-20 md:py-24 px-6 md:px-12">
      <div className="max-w-5xl mx-auto grid md:grid-cols-[1fr_300px] gap-12 items-center">
        <motion.div variants={container} initial="hidden" animate="visible">
          <motion.p variants={item} className="text-xs font-medium tracking-widest uppercase text-accent-steel mb-4">
            Open measurement · Post-quantum Bitcoin
          </motion.p>
          <motion.h1
            variants={item}
            className="font-display text-5xl md:text-6xl font-normal leading-tight text-ink mb-6"
            style={{ letterSpacing: "-1.5px" }}
          >
            What signing work buys
            <br />
            in post-quantum bytes
          </motion.h1>
          <motion.p variants={item} className="text-base text-body leading-relaxed mb-8 max-w-xl">
            Hash-based signatures for Bitcoin get smaller when the signer <em>grinds</em>: retries a hash until a condition
            holds. GRINDSTONE measured the cost of 11.16 million grinds on a 45 W laptop GPU and checked every one against a
            reference implementation.
          </motion.p>
          <motion.div variants={item} className="flex flex-wrap gap-3">
            <Link
              href="/explorer/"
              className="inline-flex items-center gap-2 bg-primary text-on-primary text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-primary-active transition-colors"
            >
              Try the signer explorer <ArrowRight size={16} />
            </Link>
            <Link
              href="/results/"
              className="inline-flex items-center gap-2 bg-canvas text-ink text-sm font-medium px-5 py-2.5 rounded-lg border border-hairline hover:bg-surface-soft transition-colors"
            >
              See the results
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: reduce ? 1 : 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={reduce ? { duration: 0 } : { duration: 0.9, delay: 0.3, ease: EASE }}
        >
          <GrindGlyph />
        </motion.div>
      </div>
    </section>
  );
}
