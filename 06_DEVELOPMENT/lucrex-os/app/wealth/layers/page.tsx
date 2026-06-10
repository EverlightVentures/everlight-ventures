import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getLayers } from "@/lib/wealth";
import { StatusBadge } from "@/components/StatusBadge";

const LAYER_ACCENT: Record<string, string> = {
  L1: "#D4A843", L2: "#B8902F", L3: "#06B6D4",
  L4: "#22C55E", L5: "#EF4444", L6: "#A855F7", L7: "#3B82F6",
};

const ONE_LINER: Record<string, string> = {
  L1: "Holdco, IP Co, Captive, FLP, FOMC. The orchestra of operating entities.",
  L2: "RLT, ILIT, GRAT, IDGT, SLAT, Dynasty, CRT, DAPT, CLT. Trusts that hold the entities.",
  L3: "FL, TX, NV personal. WY, DE, SD entities. PR Act 60 sovereignty.",
  L4: "R&D, QSBS, Augusta, REPS, OZ, 1031, cost segregation. Stack what you qualify for.",
  L5: "DAPT, Series LLC, equity stripping, PPLI, Cook Islands. Judgment-proof wrap.",
  L6: "SBLOC, HELOC, policy loans, step-up basis at death. Liquidity without realization.",
  L7: "Annual exclusion, 529 superfund, Dynasty Trust, Family Bank. Wealth that compounds across generations.",
};

export default async function LayersPage() {
  const layers = await getLayers();
  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          Strategic Stack
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Seven layers, timeless</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          Each layer is independent and tier-gated. Activate from L1 forward as you cross net-worth thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {layers.map((l) => {
          const code = l.slug.match(/^(L\d)/)?.[1] ?? l.slug;
          const accent = LAYER_ACCENT[code] ?? "#D4A843";
          const cleanTitle = l.title.replace(/^L\d[_\s:-]*/, "").replace(/_/g, " ");
          return (
            <Link
              key={l.slug}
              href={`/wealth/layers/${l.slug}`}
              className="group relative block rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 hover:border-[var(--color-gold-700)] hover:bg-[var(--color-elevated)] transition overflow-hidden"
            >
              <div
                className="absolute top-0 left-0 right-0 h-0.5"
                style={{ background: accent }}
              />
              <div className="flex items-start justify-between mb-3">
                <div
                  className="font-mono text-[10px] tracking-widest px-2 py-1 rounded border"
                  style={{ color: accent, borderColor: `${accent}40`, background: `${accent}08` }}
                >
                  {code}
                </div>
                <ArrowRight
                  size={14}
                  className="text-[var(--color-muted)] group-hover:text-[var(--color-gold-400)] group-hover:translate-x-1 transition"
                />
              </div>
              <h3 className="font-display text-lg font-semibold mb-2 leading-snug">
                {cleanTitle}
              </h3>
              <p className="text-xs text-[var(--color-muted)] leading-relaxed">
                {ONE_LINER[code] ?? "See full layer for activations and professionals."}
              </p>
              <div className="mt-4 flex gap-2">
                <StatusBadge variant="muted">{`${(l.content.match(/\n/g) ?? []).length} lines`}</StatusBadge>
                <StatusBadge variant="info">tier-gated</StatusBadge>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
