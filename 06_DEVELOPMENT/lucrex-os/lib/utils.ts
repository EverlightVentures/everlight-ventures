import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(n: number, opts?: { compact?: boolean }) {
  if (opts?.compact && Math.abs(n) >= 1000) {
    const units = [
      { v: 1e9, s: "B" },
      { v: 1e6, s: "M" },
      { v: 1e3, s: "k" },
    ];
    for (const u of units) {
      if (Math.abs(n) >= u.v) {
        return `$${(n / u.v).toFixed(1)}${u.s}`;
      }
    }
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatNumber(n: number, decimals = 0) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  }).format(n);
}

export function formatDelta(n: number, prefix = "") {
  const sign = n > 0 ? "+" : "";
  return `${sign}${prefix}${formatNumber(n, 1)}%`;
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/**
 * Days until a target date. Negative if past.
 */
export function daysUntil(iso: string): number {
  const then = new Date(iso).getTime();
  const now = Date.now();
  return Math.ceil((then - now) / (1000 * 60 * 60 * 24));
}

/**
 * Server-safe USD formatter. Mirrors lib/api/client.ts:formatUSD but with no
 * "use client" boundary, so it can be imported from server components.
 */
export function formatUSD(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
}

export function formatPrice(n: number | null | undefined, decimals = 5): string {
  if (n == null || !Number.isFinite(n)) return "0";
  return n.toFixed(decimals);
}
