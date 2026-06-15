import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoverForge - Print-Ready KDP Covers + Listing Bundle",
  description:
    "AI-generated print-ready KDP covers and the complete listing bundle in one click. Free watermarked preview, then unlock the full wrap PDF + keywords + blurb.",
  openGraph: {
    title: "CoverForge - Print-Ready KDP Covers + Listing Bundle",
    description:
      "Print-ready KDP covers + the listing that sells them, in one click.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen" style={{ background: "#0A0A0A" }}>
        {children}
      </body>
    </html>
  );
}
