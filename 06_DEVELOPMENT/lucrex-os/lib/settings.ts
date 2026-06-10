"use client";
import { useEffect, useState, useCallback } from "react";

export type LucrexSettings = {
  // Display
  refreshInterval: 15 | 30 | 60;
  compactMode: boolean;
  defaultLanding: "/" | "/trading" | "/wholesale" | "/intel" | "/revenue";
  // Trading display
  defaultSymbol: string;
  equityWindow: "24h" | "7d" | "30d";
  pnlDisplay: "usd" | "pct";
  // Intro
  splashEnabled: boolean;
};

export const DEFAULT_SETTINGS: LucrexSettings = {
  refreshInterval: 30,
  compactMode: false,
  defaultLanding: "/",
  defaultSymbol: "XLM-USD",
  equityWindow: "7d",
  pnlDisplay: "usd",
  splashEnabled: true,
};

const KEY = "lucrex.settings.v1";

function loadSettings(): LucrexSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<LucrexSettings>;
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<LucrexSettings>(DEFAULT_SETTINGS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
    setHydrated(true);
  }, []);

  const update = useCallback(<K extends keyof LucrexSettings>(key: K, value: LucrexSettings[K]) => {
    setSettings((s) => {
      const next = { ...s, [key]: value };
      try {
        window.localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        // quota or disabled, fail soft
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    try {
      window.localStorage.removeItem(KEY);
    } catch {
      // ignore
    }
    setSettings(DEFAULT_SETTINGS);
  }, []);

  return { settings, update, reset, hydrated };
}
