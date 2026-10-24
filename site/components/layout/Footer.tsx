import Link from "next/link";
import { Mail } from "lucide-react";
import { BITCOIN_ADDRESS, CONTACT_EMAIL, REPO_URL } from "@/lib/site";

const footerLinks = {
  Study: [
    { label: "Results", href: "/results/" },
    { label: "Signer explorer", href: "/explorer/" },
    { label: "Method", href: "/method/" },
  ],
  Read: [
    { label: "Paper (draft)", href: "/paper/" },
    { label: "Executive summary", href: "/paper/#summary" },
    { label: "Reproduce", href: "/reproduce/" },
  ],
  Connect: [
    { label: "Email", href: `mailto:${CONTACT_EMAIL}`, external: true },
    ...(REPO_URL ? [{ label: "Source code", href: REPO_URL, external: true }] : []),
  ],
};

export default function Footer() {
  return (
    <footer className="bg-surface-dark text-on-dark-soft" aria-label="Site footer">
      <div className="max-w-5xl mx-auto px-6 md:px-12 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <p className="font-display text-lg text-on-dark mb-3">
              <span className="text-accent-steel">◆</span> GRINDSTONE
            </p>
            <p className="text-sm leading-relaxed">
              An open measurement of grinding costs for Bitcoin-tuned hash-based signatures.
            </p>
          </div>
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <p className="text-xs font-medium tracking-widest uppercase text-on-dark mb-4">{category}</p>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    {"external" in link && link.external ? (
                      <a
                        href={link.href}
                        target={link.href.startsWith("http") ? "_blank" : undefined}
                        rel="noopener noreferrer"
                        className="text-sm text-on-dark-soft hover:text-on-dark transition-colors"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link href={link.href} className="text-sm text-on-dark-soft hover:text-on-dark transition-colors">
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="pb-8 mb-8 border-b border-surface-dark-elevated">
          <p className="text-xs font-medium tracking-widest uppercase text-on-dark mb-2">Support with Bitcoin</p>
          <p className="font-mono text-xs text-on-dark-soft break-all select-all">{BITCOIN_ADDRESS}</p>
        </div>

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <p className="text-xs">© 2026 Georgios Nanos · Code MIT · Data and figures CC-BY-4.0</p>
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="inline-flex items-center gap-1.5 text-xs hover:text-on-dark transition-colors"
            aria-label={`Email ${CONTACT_EMAIL}`}
          >
            <Mail size={13} aria-hidden /> {CONTACT_EMAIL}
          </a>
        </div>
      </div>
    </footer>
  );
}
