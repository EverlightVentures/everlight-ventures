import type { Metadata, Viewport } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import KillSW from "@/components/KillSW";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  weight: ["600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AroundMe",
  description: "Know what's happening around you, right now.",
  applicationName: "AroundMe",
  // Lets iOS "Add to Home Screen" open AroundMe fullscreen, like an installed app.
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "AroundMe" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#0A0A0A",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover", // draw under the notch so it feels native
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${playfair.variable}`}>
        <KillSW />
        {children}
      </body>
    </html>
  );
}
