"use client";
import { useState } from "react";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";
import { TickerStrip } from "./TickerStrip";
import { MobileTabBar } from "./MobileTabBar";

export function Shell({ children }: { children: React.ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="min-h-dvh flex flex-col">
      <TopBar onMenuClick={() => setNavOpen((v) => !v)} />
      <div className="flex flex-1 overflow-hidden">
        <SideNav open={navOpen} onClose={() => setNavOpen(false)} />
        <main className="flex-1 overflow-y-auto pb-24 md:pb-12">
          {children}
        </main>
      </div>
      <TickerStrip />
      <MobileTabBar />
    </div>
  );
}
