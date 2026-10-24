import type { Metadata } from "next";
import { Cormorant_Garamond, Inter } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/layout/Navigation";
import Footer from "@/components/layout/Footer";
import { DRAFT } from "@/lib/site";

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const description =
  "11.16 million verified grinds on a laptop GPU: what signing work buys how many bytes in the hash-based post-quantum signatures proposed for Bitcoin.";

export const metadata: Metadata = {
  title: { default: "GRINDSTONE — Grinding costs for post-quantum Bitcoin signatures", template: "%s — GRINDSTONE" },
  description,
  openGraph: { type: "website", locale: "en_US", siteName: "GRINDSTONE", title: "GRINDSTONE", description },
  twitter: { card: "summary", title: "GRINDSTONE", description },
  robots: DRAFT ? { index: false, follow: false } : { index: true, follow: true },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${cormorant.variable} ${inter.variable}`}>
      <body className="antialiased bg-canvas text-ink font-sans">
        <Navigation />
        <main className="pt-16">
          {DRAFT && (
            <div className="no-print bg-surface-soft border-b border-hairline px-6 md:px-12 py-2">
              <p className="max-w-5xl mx-auto text-xs text-muted">
                <span className="font-medium text-primary-active">Draft</span> · Results are final for run 196e7e91e907;
                the paper is a draft under review.
              </p>
            </div>
          )}
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
