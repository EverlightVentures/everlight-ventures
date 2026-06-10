import { getPriorities } from "@/lib/wealth";
import { PrioritiesForm } from "@/components/wealth/PrioritiesForm";
import { classifyWealthMode, modeConfidence, MODE_PROFILES } from "@/lib/wealth-mode";
import { StatusBadge } from "@/components/StatusBadge";
import { Sparkles, ArrowRight } from "lucide-react";

export const dynamic = "force-dynamic";

const KEYS = [
  "TAX_MINIMIZATION", "LIQUIDITY", "ASSET_PROTECTION", "GROWTH_LEVERAGE",
  "GEOGRAPHIC_FREEDOM", "PRIVACY", "GENERATIONAL", "SPEED_OF_DEPLOY",
  "COMPLEXITY_TOLERANCE", "ETHICS_FLOOR",
];

export default async function PrioritiesPage() {
  const { rawWeights, weights, allFilled } = await getPriorities();

  const initial: Record<string, number> = {};
  for (const k of KEYS) initial[k] = rawWeights?.[k] ?? 0;

  const mode = weights ? classifyWealthMode(weights) : null;
  const confidence = weights ? modeConfidence(weights) : null;
  const profile = mode ? MODE_PROFILES[mode] : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
            Calibration
          </div>
          <h2 className="font-display text-2xl md:text-3xl font-semibold">Your weight vector</h2>
          <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
            Set each dimension 1 (doesn't matter) to 10 (non-negotiable). The Hive uses these to choose
            which strategies surface per tier and which mode you operate in.
          </p>
        </div>

        <PrioritiesForm initialWeights={initial} />
      </div>

      <aside className="lg:col-span-1">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sticky top-20">
          <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
            Live classification
          </div>
          <h3 className="font-display text-xl font-semibold mb-3">Wealth Mode</h3>

          {!allFilled || !profile ? (
            <div className="text-center py-6">
              <Sparkles className="mx-auto mb-3 text-[var(--color-faint)]" size={28} />
              <div className="text-sm text-[var(--color-muted)]">
                Fill all 10 weights to reveal your archetype.
              </div>
            </div>
          ) : (
            <>
              <div className="mb-4">
                <div className="font-display text-3xl font-bold text-gold-gradient capitalize">
                  {profile.label}
                </div>
                <div className="text-sm text-[var(--color-muted)] mt-1">{profile.blurb}</div>
                {confidence && confidence.spread < 2 && (
                  <div className="mt-2 text-xs text-[var(--color-warn)]">
                    Close call: {profile.label} edges {MODE_PROFILES[confidence.secondary].label} by {confidence.spread.toFixed(1)} pts.
                  </div>
                )}
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-1">
                    Emphasis
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.emphasis.map((e) => (
                      <StatusBadge key={e} variant="active">{e}</StatusBadge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-1">
                    De-emphasis
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.deemphasis.map((e) => (
                      <StatusBadge key={e} variant="muted">{e}</StatusBadge>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-1">
                    Early-tier focus
                  </div>
                  <ul className="space-y-1">
                    {profile.earlyTierFocus.map((e) => (
                      <li key={e} className="flex items-start gap-2 text-xs">
                        <ArrowRight size={11} className="mt-1 text-[var(--color-gold-500)] flex-shrink-0" />
                        <span>{e}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
