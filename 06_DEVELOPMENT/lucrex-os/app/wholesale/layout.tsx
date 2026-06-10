export default function WholesaleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-wholesale">
      <div className="px-4 md:px-8 lg:px-12 pt-6 md:pt-10 max-w-[1600px] mx-auto">
        <div className="flex items-center gap-2 mb-2 text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--accent)" }}>
          <span>Domain</span>
          <span className="h-px w-6" style={{ background: "var(--accent)", opacity: 0.4 }} />
          <span>Wholesale</span>
        </div>
        <h1 className="font-display text-3xl md:text-5xl font-semibold leading-tight mb-1">
          Distressed Pipeline
        </h1>
        <p className="text-sm text-[var(--color-muted)] mb-6 max-w-3xl">
          Cleveland niche. Phone-and-mail-first since the April pivot. Boomerang state-gated, JV scout active.
        </p>
      </div>
      <div className="px-4 md:px-8 lg:px-12 pb-8 max-w-[1600px] mx-auto">{children}</div>
    </div>
  );
}
