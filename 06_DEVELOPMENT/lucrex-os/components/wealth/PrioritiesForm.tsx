"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Save, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const KEYS = [
  { k: "TAX_MINIMIZATION",     label: "Tax Minimization",       hint: "Lowest current-year tax bill possible." },
  { k: "LIQUIDITY",            label: "Liquidity",              hint: "Cash accessible for next deal in 24-72 hrs." },
  { k: "ASSET_PROTECTION",     label: "Asset Protection",       hint: "Lawsuit, divorce, judgment proofing." },
  { k: "GROWTH_LEVERAGE",      label: "Growth Leverage",        hint: "Reinvest into more businesses vs preserve." },
  { k: "GEOGRAPHIC_FREEDOM",   label: "Geographic Freedom",     hint: "Willing to physically move (FL, TX, PR, abroad)." },
  { k: "PRIVACY",              label: "Privacy",                hint: "Anonymous LLCs, trusts, no public records." },
  { k: "GENERATIONAL",         label: "Generational",           hint: "Heirs locked in vs spend it all." },
  { k: "SPEED_OF_DEPLOY",      label: "Speed of Deploy",        hint: "Aggressive moves now vs deliberate sequencing." },
  { k: "COMPLEXITY_TOLERANCE", label: "Complexity Tolerance",   hint: "Eight entities + four trusts vs keep it simple." },
  { k: "ETHICS_FLOOR",         label: "Ethics Floor",           hint: "Aggressive but legal vs squeaky clean." },
] as const;

type Props = {
  initialWeights: Record<string, number>;
};

export function PrioritiesForm({ initialWeights }: Props) {
  const [weights, setWeights] = useState(initialWeights);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const allFilled = KEYS.every(({ k }) => weights[k] >= 1);

  function setW(k: string, v: number) {
    setWeights((prev) => ({ ...prev, [k]: v }));
    setSaved(false);
  }

  async function save() {
    setErr(null);
    try {
      const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
      const r = await fetch(`${base}/api/wealth/priorities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weights }),
      });
      if (!r.ok) throw new Error(await r.text());
      setSaved(true);
      startTransition(() => router.refresh());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div>
      <div className="space-y-3 mb-6">
        {KEYS.map(({ k, label, hint }) => {
          const v = weights[k] ?? 0;
          const intensity = v / 10;
          return (
            <div key={k} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
              <div className="flex items-baseline justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{label}</div>
                  <div className="text-xs text-[var(--color-muted)] mt-0.5">{hint}</div>
                </div>
                <div className="font-mono text-2xl font-semibold w-12 text-right" style={{
                  color: v === 0 ? "var(--color-faint)" : `hsl(${45 + intensity * 12}, ${60 + intensity * 30}%, ${50 + intensity * 10}%)`,
                }}>
                  {v || "?"}
                </div>
              </div>
              <input
                type="range"
                min={0}
                max={10}
                step={1}
                value={v}
                onChange={(e) => setW(k, Number(e.target.value))}
                className="w-full accent-[var(--color-gold-500)]"
                aria-label={label}
              />
              <div className="flex justify-between text-[10px] text-[var(--color-faint)] mt-1 px-0.5">
                <span>doesn't matter</span>
                <span>flexible</span>
                <span>non-negotiable</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="sticky bottom-20 md:bottom-12 z-10 rounded-xl border border-[var(--color-gold-700)] bg-[var(--color-surface)]/95 backdrop-blur-md p-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-sm">
          {!allFilled ? (
            <>
              <AlertCircle size={14} className="text-[var(--color-warn)]" />
              <span className="text-[var(--color-muted)]">
                {KEYS.filter(({ k }) => weights[k] < 1).length} weight(s) still 0
              </span>
            </>
          ) : (
            <>
              <CheckCircle2 size={14} className="text-[var(--color-success)]" />
              <span className="text-[var(--color-fg)]">All 10 weights set</span>
            </>
          )}
          {saved && <span className="text-[var(--color-success)] text-xs ml-2">saved</span>}
          {err && <span className="text-[var(--color-alert)] text-xs ml-2">{err}</span>}
        </div>
        <button
          onClick={save}
          disabled={pending}
          className={cn(
            "inline-flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition",
            "bg-[var(--color-gold-500)] text-black hover:bg-[var(--color-gold-400)]",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          <Save size={14} />
          {pending ? "Saving..." : "Save weights"}
        </button>
      </div>
    </div>
  );
}
