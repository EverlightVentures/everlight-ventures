"use client";
import { cn } from "@/lib/utils";

export type StateFilter = "ALL" | "GA" | "FL" | "TX" | "MO" | "AZ" | "TN";

const ALL_STATES: { key: StateFilter; label: string; hint: string }[] = [
  { key: "ALL", label: "All", hint: "across the book" },
  { key: "GA",  label: "Georgia",    hint: "legal_unlicensed" },
  { key: "FL",  label: "Florida",    hint: "email-first (FTSA)" },
  { key: "TX",  label: "Texas",      hint: "email-first (SB 140)" },
  { key: "MO",  label: "Missouri",   hint: "legal_unlicensed" },
  { key: "AZ",  label: "Arizona",    hint: "with disclosures" },
  { key: "TN",  label: "Tennessee",  hint: "solicitor reg required" },
];

export function StateTabs({
  value,
  onChange,
  counts,
}: {
  value: StateFilter;
  onChange: (v: StateFilter) => void;
  counts: Record<string, number>;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {ALL_STATES.map((s) => {
        const n = s.key === "ALL"
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[s.key] ?? 0;
        const active = value === s.key;
        return (
          <button
            key={s.key}
            onClick={() => onChange(s.key)}
            className={cn(
              "group flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition-all",
              active
                ? "bg-gold text-obsidian border-gold shadow-gold-glow"
                : "bg-charcoal border-ash text-ivory hover:border-gold/60 hover:text-gold"
            )}
          >
            <span className="font-medium">{s.label}</span>
            <span
              className={cn(
                "text-[11px] font-mono tabular-nums px-1.5 py-0.5 rounded",
                active ? "bg-obsidian/20 text-obsidian" : "bg-ash/60 text-fog group-hover:bg-gold/10 group-hover:text-gold"
              )}
            >
              {n}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export { ALL_STATES };
