"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";

const navItems = [
  { label: "Results", href: "/results/" },
  { label: "Explorer", href: "/explorer/" },
  { label: "Method", href: "/method/" },
  { label: "Paper", href: "/paper/" },
  { label: "Reproduce", href: "/reproduce/" },
];

/** Same chrome as nanos.work: fixed canvas bar, hairline until scrolled, card-tinted active item. */
export default function Navigation() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const active = (href: string) => pathname.replace(/\/?$/, "/") === href;

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 bg-canvas transition-shadow duration-300 ${
        scrolled ? "shadow-[0_1px_3px_rgba(20,20,19,0.08)]" : "border-b border-hairline"
      }`}
      role="banner"
    >
      <nav
        className="max-w-5xl mx-auto flex items-center justify-between h-16 px-6 md:px-12"
        aria-label="Main navigation"
      >
        <Link
          href="/"
          className="font-display text-lg font-medium text-ink hover:text-primary transition-colors"
          aria-label="GRINDSTONE — Home"
        >
          <span className="text-accent-steel">◆</span> <span>GRINDSTONE</span>
        </Link>

        <ul className="hidden md:flex items-center gap-1" role="list">
          {navItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  active(item.href)
                    ? "text-ink bg-surface-card"
                    : "text-muted hover:text-ink hover:bg-surface-soft"
                }`}
                aria-current={active(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>

        <button
          className="md:hidden p-2 rounded-md text-muted hover:text-ink hover:bg-surface-soft transition-colors"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          aria-controls="mobile-menu"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {mobileOpen && (
        <div id="mobile-menu" className="md:hidden bg-canvas border-t border-hairline px-6 py-4">
          <ul className="space-y-1" role="list">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`block px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    active(item.href) ? "text-ink bg-surface-card" : "text-muted hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
}
