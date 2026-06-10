import { WealthTabs } from "@/components/wealth/WealthTabs";

export default function WealthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-wealth">
      <div className="px-4 md:px-8 lg:px-12 pt-6 md:pt-10 max-w-[1600px] mx-auto">
        <div className="flex items-center gap-2 mb-2 text-[10px] uppercase tracking-[0.3em] text-[var(--color-gold-500)]">
          <span>Domain</span>
          <span className="h-px w-6 bg-[var(--color-gold-700)]" />
          <span>Wealth OS</span>
        </div>
        <h1 className="font-display text-3xl md:text-5xl font-semibold leading-tight mb-1">
          Sovereign Wealth OS
        </h1>
        <p className="text-sm text-[var(--color-muted)] mb-5 max-w-3xl">
          Family-office architecture from $0 to $100M+. Seven layers, twelve tiers, five always-on engines.
          You direct the professionals, not the other way around.
        </p>
        <WealthTabs />
      </div>
      <div className="px-4 md:px-8 lg:px-12 py-6 md:py-8 max-w-[1600px] mx-auto">
        {children}
      </div>
    </div>
  );
}
