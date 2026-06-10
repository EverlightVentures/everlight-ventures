"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/wealth",                label: "Overview" },
  { href: "/wealth/layers",         label: "Layers" },
  { href: "/wealth/tiers",          label: "Tiers" },
  { href: "/wealth/credits",        label: "Credits" },
  { href: "/wealth/intel",          label: "Intel" },
  { href: "/wealth/professionals",  label: "Professionals" },
  { href: "/wealth/scenarios",      label: "Scenarios" },
];

export function WealthTabs() {
  const path = usePathname();
  const isActive = (href: string) =>
    href === "/wealth" ? path === "/wealth" : path.startsWith(href);

  return (
    <div className="border-b border-[var(--color-border)] -mx-4 md:-mx-8 lg:-mx-12 px-4 md:px-8 lg:px-12 overflow-x-auto">
      <div className="flex gap-1 min-w-max">
        {TABS.map((t) => {
          const active = isActive(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "relative px-4 py-3 text-sm font-medium transition whitespace-nowrap",
                active
                  ? "text-[var(--color-gold-400)]"
                  : "text-[var(--color-muted)] hover:text-[var(--color-fg)]"
              )}
            >
              {t.label}
              {active && (
                <span className="absolute bottom-0 left-3 right-3 h-0.5 bg-[var(--color-gold-500)] rounded-t" />
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
