import Link from "next/link";
import { ArrowRight, Sparkles, AlertTriangle, Calendar } from "lucide-react";
import { getPriorities, tierForNetWorth, readWealthRoot } from "@/lib/wealth";
import { RadarPriorities } from "@/components/RadarPriorities";
import { KPICard } from "@/components/KPICard";
import { StatusBadge } from "@/components/StatusBadge";
import { CountdownClock } from "@/components/CountdownClock";
import { daysUntil } from "@/lib/utils";

const NET_WORTH_TODAY = 0;
const TCJA_SUNSET = "2026-12-31T00:00:00Z";

export default async function WealthOverviewPage() {
  const { weights, allFilled } = await getPriorities();
  const tierInfo = tierForNetWorth(NET_WORTH_TODAY);
  const readme = await readWealthRoot("README.md");

  const freeMovesLine = readme?.content.match(/\*\*Free moves available now:\*\*\s*(.+)/);
  const freeMoves = freeMovesLine?.[1]
    ?.split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    ?? [];

  const sunsetDays = daysUntil(TCJA_SUNSET);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPICard
          label="Current Tier"
          value={tierInfo.current.tier}
          hint={tierInfo.current.label}
          status="active"
          accent="#D4A843"
        />
        <KPICard
          label="Net Worth"
          value="$0"
          hint="Sole prop DBA, free-path-only"
          status="idle"
        />
        <KPICard
          label="Next Trigger"
          value={tierInfo.next?.tier ?? "max"}
          hint={tierInfo.next ? `at $${(tierInfo.next.minNetWorth / 1000).toFixed(0)}k` : "top tier"}
          status="neutral"
          accent="#D4A843"
        />
        <KPICard
          label="TCJA Sunset"
          value={`${sunsetDays}d`}
          hint="estate exemption halves Dec 31"
          status={sunsetDays < 90 ? "alert" : "neutral"}
          accent={sunsetDays < 90 ? "#EF4444" : "#F59E0B"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)]">
                Priorities
              </div>
              <h2 className="font-display text-xl font-semibold">10-Dimension Weight Vector</h2>
            </div>
            {allFilled ? (
              <StatusBadge variant="active">Calibrated</StatusBadge>
            ) : (
              <StatusBadge variant="warn">Awaiting input</StatusBadge>
            )}
          </div>
          <RadarPriorities weights={weights} />
          {!allFilled && (
            <Link
              href="/wealth/priorities"
              className="mt-3 inline-flex items-center gap-2 text-sm text-[var(--color-gold-500)] hover:text-[var(--color-gold-300)] transition"
            >
              <Sparkles size={14} />
              <span>Set your weights</span>
              <ArrowRight size={14} />
            </Link>
          )}
        </div>

        <div className="lg:col-span-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)]">
            Next 3 Moves
          </div>
          <h2 className="font-display text-xl font-semibold mb-4">Today's playbook</h2>
          <ol className="space-y-3 list-decimal list-inside marker:text-[var(--color-gold-500)] marker:font-mono">
            <li className="text-sm">
              <span className="font-medium">R&amp;D credit retroactive filing prep</span>
              <div className="text-xs text-[var(--color-muted)] mt-0.5 ml-5">
                Document AI and code work since Jan 2024. Up to 3 amended returns when entity forms.
              </div>
            </li>
            <li className="text-sm">
              <span className="font-medium">QSBS C-corp formation timing</span>
              <div className="text-xs text-[var(--color-muted)] mt-0.5 ml-5">
                Section 1202 caps $10M tax-free at exit. Must form before any major equity event.
              </div>
            </li>
            <li className="text-sm">
              <span className="font-medium">First commission close + T1 trigger</span>
              <div className="text-xs text-[var(--color-muted)] mt-0.5 ml-5">
                $10k to $15k unlocks WY anonymous LLC, business banking, S-Corp election study.
              </div>
            </li>
          </ol>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center gap-2 mb-3">
          <Calendar size={16} className="text-[var(--color-gold-500)]" />
          <h2 className="font-display text-xl font-semibold">Free moves available right now</h2>
          <StatusBadge variant="info">$0 cost</StatusBadge>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {freeMoves.length ? freeMoves.map((m) => (
            <div
              key={m}
              className="flex items-center gap-2 p-3 rounded-md border border-[var(--color-border)] hover:border-[var(--color-gold-700)] hover:bg-[var(--color-elevated)] transition cursor-default"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-gold-500)]" />
              <span className="text-sm capitalize">{m}</span>
            </div>
          )) : (
            <div className="col-span-full text-sm text-[var(--color-muted)] italic">
              No free moves listed in README. Check WEALTH_OS_ROOT path.
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/5 p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-[var(--color-warn)] flex-shrink-0 mt-0.5" />
          <div className="space-y-2">
            <div className="font-medium text-[var(--color-warn)]">Reality check</div>
            <p className="text-sm text-[var(--color-muted)]">
              This OS is research and education, not legal, tax, or financial advice. Every active strategy
              requires licensed professionals to execute. Tax law changes constantly: a strategy current
              today may not work in 18 months. The Quarterly Intel Engine exists for this reason.
            </p>
            <div className="text-xs text-[var(--color-muted)] mt-2">
              <CountdownClock targetIso={TCJA_SUNSET} label="Lifetime gift and estate exemption sunset" />
              {" · halves from $13.99M to roughly $7M on Dec 31"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
