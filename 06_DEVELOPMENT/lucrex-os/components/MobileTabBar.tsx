"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Crown, Network, MoreHorizontal, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/",          label: "Hub",       Icon: Home,        accent: "#D4A843" },
  { href: "/wealth",    label: "Wealth",    Icon: Crown,       accent: "#D4A843" },
  { href: "/wholesale", label: "Wholesale", Icon: TrendingUp,  accent: "#D97706" },
  { href: "/hive",      label: "Hive",      Icon: Network,     accent: "#3B82F6" },
  { href: "/more",      label: "More",      Icon: MoreHorizontal, accent: "#888888" },
];

export function MobileTabBar() {
  const path = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 h-16 border-t border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur-md">
      <div className="grid grid-cols-5 h-full">
        {TABS.map(({ href, label, Icon, accent }) => {
          const active =
            href === "/"
              ? path === "/"
              : path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 transition",
                active ? "text-[var(--color-fg)]" : "text-[var(--color-muted)]"
              )}
            >
              <Icon size={18} style={{ color: active ? accent : undefined }} />
              <span className="text-[10px] tracking-wide">{label}</span>
              {active && (
                <span
                  className="absolute top-0 h-0.5 w-8 rounded-b"
                  style={{ background: accent }}
                />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
