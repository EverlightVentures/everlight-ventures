import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Everlight Hive Mind",
    template: "%s | Everlight Hive Mind",
  },
  description:
    "AI-native office suite. Connect your tools and let the Hive handle workflows, support, sales, and operations autonomously.",
  keywords: ["AI", "automation", "workflow", "hive mind", "Claude", "Gemini", "Codex", "SaaS"],
  authors: [{ name: "Everlight Ventures" }],
  creator: "Everlight Ventures",
  openGraph: {
    type: "website",
    locale: "en_US",
    title: "Everlight Hive Mind",
    description: "AI-native business automation. Your entire office, automated.",
    siteName: "Everlight Hive Mind",
  },
  twitter: {
    card: "summary_large_image",
    title: "Everlight Hive Mind",
    description: "AI-native business automation. Your entire office, automated.",
  },
  robots: {
    index: false,
    follow: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0A0A0F",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-void text-text-primary antialiased">
        <div
          className="fixed inset-0 pointer-events-none z-0"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(ellipse 80% 50% at 20% -10%, rgba(124,58,237,0.08) 0%, transparent 60%), radial-gradient(ellipse 60% 40% at 80% 100%, rgba(245,158,11,0.05) 0%, transparent 60%)",
          }}
        />
        <div className="relative z-10 min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
