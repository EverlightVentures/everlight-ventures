import type { Metadata } from "next";
import { Playfair_Display, Inter } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

const playfair = Playfair_Display({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-playfair",
  weight: ["400", "500", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Wholesale Command Center | Everlight Ventures",
  description: "Live pipeline, deals, title companies, and outreach history",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${playfair.variable} ${inter.variable}`}>
      <body className="min-h-screen bg-obsidian text-ivory antialiased">
        <div className="fixed inset-0 -z-10 bg-grid opacity-40" />
        <div className="fixed inset-0 -z-10 bg-gradient-to-br from-obsidian via-charcoal to-obsidian" />
        <SiteHeader />
        <main className="max-w-[1400px] mx-auto px-6 py-8">{children}</main>
        <footer className="max-w-[1400px] mx-auto px-6 py-10 text-xs text-smoke flex items-center justify-between">
          <div className="tracking-[0.3em] text-gold/70">EVERLIGHT VENTURES</div>
          <div>The mind behind the money.</div>
        </footer>
      </body>
    </html>
  );
}
