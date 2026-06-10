"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Home, Crown, TrendingUp, Handshake, Sparkles, DollarSign, Brain, Network, Dice5, ArrowUpRight,
  type LucideIcon,
} from "lucide-react";
import type { DomainMeta } from "@/lib/theme";

const ICONS: Record<string, LucideIcon> = {
  Home, Crown, TrendingUp, Handshake, Sparkles, DollarSign, Brain, Network, Dice5,
};

type Props = {
  domain: DomainMeta;
  kpiLabel: string;
  kpiValue: string;
  delta?: string;
  status?: "active" | "idle" | "alert" | "neutral";
  index: number;
};

const STATUS_DOT = {
  active:  "bg-[var(--color-success)]",
  idle:    "bg-[var(--color-muted)]",
  alert:   "bg-[var(--color-alert)]",
  neutral: "bg-[var(--color-gold-500)]",
};

export function DomainTile({ domain, kpiLabel, kpiValue, delta, status = "neutral", index }: Props) {
  const Icon = ICONS[domain.icon] ?? Home;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4, ease: "easeOut" }}
    >
      <Link
        href={domain.href}
        className="group relative block rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 hover:border-[var(--color-gold-700)] hover:bg-[var(--color-elevated)] hover:-translate-y-0.5 overflow-hidden"
        style={{ "--tile-accent": domain.accent } as React.CSSProperties}
      >
        {/* Accent bar */}
        <div
          className="absolute top-0 left-0 right-0 h-0.5 opacity-60 group-hover:opacity-100 transition-opacity"
          style={{ background: domain.accent }}
        />

        {/* Glow on hover */}
        <div
          className="absolute -top-12 -right-12 h-40 w-40 rounded-full opacity-0 group-hover:opacity-15 transition-opacity duration-500 blur-2xl"
          style={{ background: domain.accent }}
        />

        <div className="flex items-start justify-between mb-4">
          <div
            className="h-10 w-10 rounded-lg flex items-center justify-center border border-[var(--color-border)]"
            style={{ background: `${domain.accent}10` }}
          >
            <Icon size={18} style={{ color: domain.accent }} />
          </div>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${STATUS_DOT[status]}`} />
            <ArrowUpRight
              size={14}
              className="text-[var(--color-muted)] group-hover:text-[var(--color-gold-400)] group-hover:rotate-12 transition"
            />
          </div>
        </div>

        <div className="font-display text-xl font-semibold mb-0.5 leading-tight">
          {domain.label}
        </div>
        <div className="text-xs text-[var(--color-muted)] mb-4">{domain.tagline}</div>

        <div className="border-t border-[var(--color-border)] pt-3">
          <div className="text-[10px] uppercase tracking-widest text-[var(--color-faint)] mb-1">
            {kpiLabel}
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span
              className="font-mono text-xl font-semibold"
              style={{ color: domain.accent }}
            >
              {kpiValue}
            </span>
            {delta && (
              <span className="text-xs text-[var(--color-success)] font-mono">
                {delta}
              </span>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
