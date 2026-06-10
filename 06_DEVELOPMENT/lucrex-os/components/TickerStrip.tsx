"use client";

const TICKER_ITEMS = [
  { label: "Wholesale", value: "0 active leads" },
  { label: "XLM Bot", value: "live · sniper mode" },
  { label: "Hive", value: "63 agents online" },
  { label: "Wealth Tier", value: "T0 · $0" },
  { label: "First Deal", value: "01a87094 · intro · $47.50" },
  { label: "Branded Comms", value: "5 channels live" },
  { label: "Quarterly Intel", value: "next scan May 1" },
  { label: "TCJA Sunset", value: "251 days" },
];

export function TickerStrip() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS];

  return (
    <div className="hidden md:block fixed bottom-0 left-0 right-0 z-20 h-8 border-t border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-sm overflow-hidden">
      <div className="flex animate-marquee whitespace-nowrap h-full items-center">
        {items.map((it, i) => (
          <span key={i} className="inline-flex items-center gap-2 px-6 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-gold-500)]" />
            <span className="text-[var(--color-muted)] uppercase tracking-wider text-[10px]">
              {it.label}
            </span>
            <span className="text-[var(--color-fg)] font-mono">{it.value}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
