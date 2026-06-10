"use client";
import { useEffect, useRef, useState, useCallback } from "react";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/**
 * Hook that polls a path on an interval. Returns { data, error, refetch }.
 * Automatically prefixes basePath. All paths should start with /api/...
 */
export function useApi<T = unknown>(path: string, interval = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      const r = await fetch(`${BASE_PATH}${path}`, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const json = (await r.json()) as T;
      if (mounted.current) {
        setData(json);
        setError(null);
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "fetch failed");
    }
  }, [path]);

  useEffect(() => {
    mounted.current = true;
    fetchData();
    if (interval <= 0) return () => { mounted.current = false; };
    const id = setInterval(fetchData, interval);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [fetchData, interval]);

  return { data, error, refetch: fetchData };
}

/** Format a number as USD currency. */
export function formatUSD(val: number | null | undefined): string {
  if (val == null || isNaN(val as number)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(val));
}

/** Compact USD ($1.2k, $3.4M). */
export function formatUSDCompact(val: number | null | undefined): string {
  if (val == null || isNaN(val as number)) return "$0";
  const n = Number(val);
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}

/** Format an XLM-style price (5 decimals). */
export function formatPrice(val: number | null | undefined, dp = 5): string {
  if (val == null || isNaN(val as number)) return "0.00000";
  return Number(val).toFixed(dp);
}

/** Relative time short ("3m ago", "2h ago", "now"). */
export function timeAgo(iso: string | number | Date | null | undefined): string {
  if (!iso) return "--";
  const d = new Date(iso).getTime();
  if (!d) return "--";
  const sec = Math.max(0, Math.floor((Date.now() - d) / 1000));
  if (sec < 5) return "now";
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

/** Short percent ("+1.2%", "-3.4%"). */
export function formatPct(val: number | null | undefined, dp = 1): string {
  if (val == null || isNaN(val as number)) return "0.0%";
  const n = Number(val);
  return `${n >= 0 ? "+" : ""}${n.toFixed(dp)}%`;
}
