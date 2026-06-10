export default function TradingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-trading">
      <div className="px-4 md:px-8 lg:px-12 pt-6 md:pt-10 max-w-[1600px] mx-auto">
        <div className="flex items-center gap-2 mb-2 text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--accent)" }}>
          <span>Domain</span>
          <span className="h-px w-6" style={{ background: "var(--accent)", opacity: 0.4 }} />
          <span>Trading</span>
        </div>
        <h1 className="font-display text-3xl md:text-5xl font-semibold leading-tight mb-1">
          XLM Perp Bot
        </h1>
        <p className="text-sm text-[var(--color-muted)] mb-6 max-w-3xl font-mono">
          Coinbase XLP-20DEC30-CDE  ·  sniper mode  ·  Oracle E5 production
        </p>
      </div>
      <div className="px-4 md:px-8 lg:px-12 pb-8 max-w-[1600px] mx-auto">{children}</div>
    </div>
  );
}
