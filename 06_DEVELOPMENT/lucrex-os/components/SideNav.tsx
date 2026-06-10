"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, Crown, TrendingUp, Brain, Wallet, AlertOctagon,
  DollarSign, Briefcase, Building2,
  History, Activity, ListChecks, Network, FileText, Filter, Settings,
  X
} from "lucide-react";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>;
  color: string;
};

type NavSection = { label: string; items: NavItem[] };

const NAV: NavSection[] = [
  {
    label: "COMMAND",
    items: [
      { href: "/",          label: "Hive Mind",   icon: Crown,        color: "#FFD740" },
      { href: "/trading",   label: "Trading",     icon: TrendingUp,   color: "#00e676" },
      { href: "/intel",     label: "Market Intel",icon: Brain,        color: "#b388ff" },
      { href: "/wealth",    label: "Wealth OS",   icon: Wallet,       color: "#FFD740" },
      { href: "/control",   label: "Control",     icon: AlertOctagon, color: "#ff1744" },
    ],
  },
  {
    label: "BUSINESS",
    items: [
      { href: "/revenue",   label: "Revenue",     icon: DollarSign,   color: "#00e676" },
      { href: "/broker",    label: "Broker OS",   icon: Briefcase,    color: "#448aff" },
      { href: "/wholesale", label: "Wholesale",   icon: Home,         color: "#ff9100" },
      { href: "/business",  label: "Business OS", icon: Building2,    color: "#b388ff" },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { href: "/trade-history", label: "Trade History", icon: History,    color: "#FFD740" },
      { href: "/changelog",     label: "Changelog",     icon: Activity,   color: "#84cc16" },
      { href: "/taskboard",     label: "Taskboard",     icon: ListChecks, color: "#06B6D4" },
      { href: "/sessions",      label: "Hive Sessions", icon: Network,    color: "#ec4899" },
      { href: "/reports",       label: "Reports",       icon: FileText,   color: "#448aff" },
      { href: "/funnel",        label: "Funnel",        icon: Filter,     color: "#ff9100" },
      { href: "/settings",      label: "Settings",      icon: Settings,   color: "#888" },
    ],
  },
];

const EXTERNAL = [
  { label: "XLM Live :8502",  href: "http://163.192.19.196:8502/" },
  { label: "Django Ops :8504", href: "http://127.0.0.1:2200/" },
  { label: "Hive Directory",   href: "http://163.192.19.196:8080/hive/" },
  { label: "Blinko RAG",       href: "http://163.192.19.196:1111/" },
  { label: "n8n",              href: "http://163.192.19.196:5678/" },
  { label: "everlightventures.io", href: "https://everlightventures.io/" },
];

type Props = { open: boolean; onClose: () => void };

export function SideNav({ open, onClose }: Props) {
  const path = usePathname();
  const isActive = (href: string) => {
    if (href === "/") return path === "/";
    return path === href || path.startsWith(href + "/");
  };

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={cn(
          "fixed md:sticky top-0 left-0 z-40 h-dvh md:h-auto md:flex-shrink-0",
          "w-56 bg-[#0d0d14] border-r border-white/[0.04]",
          "flex flex-col transition-transform duration-300 overflow-hidden",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          "md:top-[57px] md:h-[calc(100dvh-57px)]"
        )}
      >
        <div className="flex items-center justify-between p-4 md:hidden border-b border-white/[0.04]">
          <span className="font-display text-lg gradient-gold">Lucrex</span>
          <button onClick={onClose} className="p-2 hover:text-[var(--color-gold-500)]">
            <X size={20} />
          </button>
        </div>

        {/* Branded logo block (desktop only since mobile uses TopBar) */}
        <div className="hidden md:flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.04]">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-300 via-amber-500 to-orange-600 flex items-center justify-center text-xs font-black text-black shadow-lg shadow-amber-500/20 flex-shrink-0">
            L
          </div>
          <div>
            <div className="text-xs font-bold tracking-[0.2em] gradient-gold">LUCREX</div>
            <div className="text-[7px] text-gray-600 tracking-[0.15em]">COMMAND CENTER</div>
            <div className="text-[6px] text-gray-700 italic tracking-[0.1em] -mt-0.5">By Everlight Ventures</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV.map((section) => (
            <div key={section.label} className="mb-3">
              <div className="px-4 py-1 text-[9px] font-medium tracking-[0.2em] text-gray-600">
                {section.label}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-4 py-2 text-left transition-all",
                      active
                        ? "bg-white/[0.06] border-r-2 border-amber-400 text-white"
                        : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]"
                    )}
                  >
                    <Icon
                      size={14}
                      className="flex-shrink-0"
                      style={{ color: active ? item.color : undefined }}
                    />
                    <span className="text-[12px] font-medium truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}

          {/* External links */}
          <div className="mb-3">
            <div className="px-4 py-1 text-[9px] font-medium tracking-[0.2em] text-gray-600">
              EXTERNAL
            </div>
            {EXTERNAL.map((t) => (
              <a
                key={t.href}
                href={t.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-4 py-1.5 text-[11px] text-gray-500 hover:text-gray-300 hover:bg-white/[0.02] transition"
              >
                <span className="truncate">{t.label}</span>
                <span className="text-gray-700 ml-2">↗</span>
              </a>
            ))}
          </div>
        </nav>

        {/* Status footer */}
        <div className="px-4 py-3 border-t border-white/[0.04]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 pulse-live" />
            <span className="text-[10px] text-gray-500 font-mono">ORACLE E5 ONLINE</span>
          </div>
          <div className="text-[9px] text-gray-700 mt-1 font-mono">Marquise Smith</div>
        </div>
      </aside>
    </>
  );
}
