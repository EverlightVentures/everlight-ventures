"use client";
import { Settings as SettingsIcon, RotateCcw, Server, Activity, Database, Brain } from "lucide-react";
import { useSettings, type LucrexSettings } from "@/lib/settings";

const ENV_INFO: Array<{ label: string; value: string | undefined; icon: React.ComponentType<{ size?: number; className?: string }> }> = [
  { label: "Django Ops",    value: process.env.NEXT_PUBLIC_DJANGO_BASE ?? "http://127.0.0.1:2200", icon: Server },
  { label: "XLM Dashboard", value: process.env.NEXT_PUBLIC_XLM_BASE   ?? "http://163.192.19.196:8502", icon: Activity },
  { label: "Blinko RAG",    value: process.env.NEXT_PUBLIC_BLINKO_BASE ?? "http://163.192.19.196:1111", icon: Brain },
  { label: "Base Path",     value: process.env.NEXT_PUBLIC_BASE_PATH  ?? "/", icon: Database },
];

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-widest text-gray-500">{label}</span>
        {hint && <span className="text-[9px] text-gray-600">{hint}</span>}
      </div>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

const inputCls =
  "w-full px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded text-[12px] text-gray-200 focus:border-amber-400/40 focus:outline-none transition";

export default function SettingsPage() {
  const { settings, update, reset, hydrated } = useSettings();

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 page-enter">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <SettingsIcon size={20} /> SETTINGS
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Personal preferences, stored locally in your browser
          </p>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] text-gray-500 border border-white/[0.06] hover:text-amber-400 hover:border-amber-400/30 transition"
        >
          <RotateCcw size={11} /> Reset
        </button>
      </div>

      {!hydrated && <div className="card text-[11px] text-gray-500">Loading preferences...</div>}

      {hydrated && (
        <>
          {/* Display */}
          <div className="card space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Display</h2>

            <Field label="Refresh interval" hint="how often live cards re-poll">
              <div className="flex gap-1.5">
                {([15, 30, 60] as const).map((n) => (
                  <button
                    key={n}
                    onClick={() => update("refreshInterval", n as LucrexSettings["refreshInterval"])}
                    className={`flex-1 py-1.5 rounded text-[11px] border transition ${
                      settings.refreshInterval === n
                        ? "bg-amber-400/15 border-amber-400/40 text-amber-300"
                        : "bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {n}s
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Compact mode" hint="tighter spacing across cards">
              <button
                onClick={() => update("compactMode", !settings.compactMode)}
                className={`relative w-12 h-6 rounded-full transition ${
                  settings.compactMode ? "bg-amber-400/40" : "bg-white/[0.06]"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    settings.compactMode ? "translate-x-6" : "translate-x-0.5"
                  }`}
                />
              </button>
            </Field>

            <Field label="Default landing">
              <select
                value={settings.defaultLanding}
                onChange={(e) => update("defaultLanding", e.target.value as LucrexSettings["defaultLanding"])}
                className={inputCls}
              >
                <option value="/">Hive Mind (/)</option>
                <option value="/trading">Trading</option>
                <option value="/wholesale">Wholesale</option>
                <option value="/intel">Market Intel</option>
                <option value="/revenue">Revenue</option>
              </select>
            </Field>
          </div>

          {/* Trading */}
          <div className="card space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Trading</h2>

            <Field label="Default symbol">
              <input
                type="text"
                value={settings.defaultSymbol}
                onChange={(e) => update("defaultSymbol", e.target.value)}
                className={inputCls}
                placeholder="XLM-USD"
              />
            </Field>

            <Field label="Equity curve window">
              <div className="flex gap-1.5">
                {(["24h", "7d", "30d"] as const).map((w) => (
                  <button
                    key={w}
                    onClick={() => update("equityWindow", w)}
                    className={`flex-1 py-1.5 rounded text-[11px] border transition ${
                      settings.equityWindow === w
                        ? "bg-amber-400/15 border-amber-400/40 text-amber-300"
                        : "bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {w}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="PnL display">
              <div className="flex gap-1.5">
                {(["usd", "pct"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => update("pnlDisplay", m)}
                    className={`flex-1 py-1.5 rounded text-[11px] uppercase border transition ${
                      settings.pnlDisplay === m
                        ? "bg-amber-400/15 border-amber-400/40 text-amber-300"
                        : "bg-white/[0.02] border-white/[0.06] text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {m === "usd" ? "Dollars" : "Percent"}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          {/* Intro */}
          <div className="card space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Intro</h2>
            <Field label="Splash screen" hint="play logo intro at start of session">
              <button
                onClick={() => update("splashEnabled", !settings.splashEnabled)}
                className={`relative w-12 h-6 rounded-full transition ${
                  settings.splashEnabled ? "bg-amber-400/40" : "bg-white/[0.06]"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    settings.splashEnabled ? "translate-x-6" : "translate-x-0.5"
                  }`}
                />
              </button>
            </Field>
          </div>

          {/* TODO: User-defined preferences */}
          {/*
            ┌──────────────────────────────────────────────────────────┐
            │  YOUR INPUT WANTED, see chat.                            │
            │                                                          │
            │  This is the spot for any extra toggles you actually     │
            │  want, currency formatting, dashboard density, voice     │
            │  agent output mode, default agent persona, etc.          │
            │                                                          │
            │  Add fields to lib/settings.ts LucrexSettings type,      │
            │  then drop a Field block here following the patterns     │
            │  above.                                                  │
            └──────────────────────────────────────────────────────────┘
          */}

          {/* System (read-only) */}
          <div className="card space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">System</h2>
            <p className="text-[10px] text-gray-600">Read-only, configured via environment variables on Oracle.</p>
            <div className="space-y-1.5">
              {ENV_INFO.map((row) => {
                const Icon = row.icon;
                return (
                  <div key={row.label} className="flex items-center justify-between py-1.5 border-b border-white/[0.03] last:border-0">
                    <div className="flex items-center gap-2">
                      <Icon size={11} className="text-gray-500" />
                      <span className="text-[11px] text-gray-400">{row.label}</span>
                    </div>
                    <span className="font-mono text-[10px] text-amber-400/70 truncate max-w-[60%]">{row.value || "-"}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
