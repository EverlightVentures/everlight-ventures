import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function money(n: number | string | undefined | null): string {
  const v = typeof n === "string" ? parseFloat(n) : n;
  if (!v || !Number.isFinite(v)) return "--";
  return USD.format(v);
}

export function compactMoney(n: number | string | undefined | null): string {
  const v = typeof n === "string" ? parseFloat(n) : n;
  if (!v || !Number.isFinite(v)) return "--";
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${Math.round(v / 1_000)}k`;
  return `$${Math.round(v)}`;
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return "--";
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "--";
  const diff = Date.now() - t;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function humanStatus(s: string): string {
  const map: Record<string, string> = {
    new: "New",
    contacted: "In sequence",
    negotiating: "Negotiating",
    verbal_agreement: "Verbal yes",
    contract_sent: "Contract sent",
    signed: "Signed",
    buyer_blast: "Blasting buyers",
    contract_assigned: "Assigned",
    title_hold: "At title",
    closed: "Closed",
    funds_received: "Funds received",
    dead: "Dead",
  };
  return map[s] ?? s;
}

export function statusColor(s: string): string {
  const map: Record<string, string> = {
    new:                "bg-ash text-fog border-ash",
    contacted:          "bg-gold/10 text-gold border-gold/30",
    negotiating:        "bg-goldsoft/10 text-goldsoft border-goldsoft/30",
    verbal_agreement:   "bg-success/10 text-success border-success/30",
    contract_sent:      "bg-success/20 text-success border-success/50",
    signed:             "bg-success/30 text-success border-success/60",
    buyer_blast:        "bg-gold/20 text-gold border-gold/50",
    contract_assigned:  "bg-gold/30 text-gold border-gold/70",
    title_hold:         "bg-warning/10 text-warning border-warning/30",
    closed:             "bg-success/40 text-success border-success",
    funds_received:     "bg-success text-obsidian border-success",
    dead:               "bg-ash text-smoke border-ash",
  };
  return map[s] ?? "bg-ash text-fog border-ash";
}
