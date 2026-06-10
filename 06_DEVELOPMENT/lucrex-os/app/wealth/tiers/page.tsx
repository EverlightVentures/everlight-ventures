import Link from "next/link";
import { Lock, Check, Target } from "lucide-react";
import { getTiers, tierForNetWorth } from "@/lib/wealth";
import { cn } from "@/lib/utils";

const NET_WORTH = 0;

export default async function TiersPage() {
  const tiers = await getTiers();
  const info = tierForNetWorth(NET_WORTH);
  const currentTier = info.current.tier;

  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          Activation Map
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Twelve tiers, one path</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          Net-worth gates trigger which strategies activate. You are at <span className="text-[var(--color-gold-400)] font-semibold">{currentTier}</span>.
          Locked tiers are visible so you know what is coming.
        </p>
      </div>

      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-px bg-[var(--color-border)]" />
        <ol className="space-y-3">
          {tiers.map((t) => {
            const code = t.slug.match(/^(T\d{2})/)?.[1] ?? t.slug.slice(0, 3);
            const gate = info.allTiers.find((x) => x.tier === code);
            const isCurrent = code === currentTier;
            const isUnlocked = gate ? NET_WORTH >= gate.minNetWorth : false;
            const cleanTitle = t.title.replace(/^T\d{2}[_\s:-]*/, "").replace(/_/g, " ");

            return (
              <li key={t.slug} className="relative pl-14">
                <div
                  className={cn(
                    "absolute left-3 top-3 h-6 w-6 rounded-full border-2 flex items-center justify-center",
                    isCurrent
                      ? "bg-[var(--color-gold-500)] border-[var(--color-gold-500)] animate-pulse-gold"
                      : isUnlocked
                      ? "bg-[var(--color-success)]/20 border-[var(--color-success)]"
                      : "bg-[var(--color-bg)] border-[var(--color-border)]"
                  )}
                >
                  {isCurrent ? <Target size={12} className="text-black" /> :
                   isUnlocked ? <Check size={12} className="text-[var(--color-success)]" /> :
                   <Lock size={10} className="text-[var(--color-faint)]" />}
                </div>

                <Link
                  href={`/wealth/tiers/${t.slug}`}
                  className={cn(
                    "block rounded-lg border p-4 transition",
                    isCurrent
                      ? "border-[var(--color-gold-500)] bg-[var(--color-elevated)]"
                      : isUnlocked
                      ? "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-gold-700)]"
                      : "border-[var(--color-border)]/50 bg-[var(--color-surface)]/40 hover:bg-[var(--color-surface)]"
                  )}
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-xs text-[var(--color-gold-500)]">{code}</span>
                        {isCurrent && (
                          <span className="text-[10px] uppercase tracking-widest text-[var(--color-gold-400)]">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="font-display text-lg font-semibold capitalize">
                        {cleanTitle}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-base font-semibold">
                        {gate ? `$${(gate.minNetWorth / 1000).toLocaleString()}k+` : ""}
                      </div>
                      <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">
                        Trigger
                      </div>
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
