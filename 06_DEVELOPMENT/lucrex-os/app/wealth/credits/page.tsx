import { StatusBadge } from "@/components/StatusBadge";
import { Calendar, AlertTriangle } from "lucide-react";

type Credit = {
  code: string;
  name: string;
  eligibility: "eligible" | "maybe" | "later";
  estValue: string;
  deadline?: string;
  status: "research" | "ready" | "claimed" | "blocked";
  notes: string;
};

const CREDITS: Credit[] = [
  { code: "Sec 41",  name: "R&D Tax Credit",          eligibility: "eligible", estValue: "$5k-15k",
    deadline: "Retroactive 3yr", status: "research",
    notes: "AI development, code, prompt engineering qualify. File on amended return after entity forms." },
  { code: "Sec 1202", name: "QSBS (Qualified Small Business Stock)", eligibility: "later", estValue: "$10M cap",
    status: "research", deadline: "Pre-equity-event",
    notes: "C-corp formation must precede major liquidity event. 5-year hold for full exclusion." },
  { code: "Sec 280A", name: "Augusta Rule",            eligibility: "eligible", estValue: "$2k-15k/yr",
    deadline: "Annual", status: "research",
    notes: "Rent home to your business 14 days/yr tax-free. Need fair-market rent comps." },
  { code: "Sec 469", name: "REPS (Real Estate Professional)", eligibility: "later", estValue: "100% RE losses",
    status: "blocked", notes: "Need 750 hrs/yr in RE, more than half of all work time. Spouse can qualify." },
  { code: "Sec 1400Z", name: "Opportunity Zone",       eligibility: "later", estValue: "Defer + step-up",
    deadline: "180 days from gain", status: "research",
    notes: "Defer cap gains by reinvesting in QOZ. 10-year hold = basis step-up to FMV." },
  { code: "Sec 1031", name: "Like-Kind Exchange",      eligibility: "later", estValue: "Defer 100%",
    deadline: "45/180 day windows", status: "research",
    notes: "Real estate only post-TCJA. Identify in 45 days, close in 180." },
  { code: "Sec 168", name: "Bonus Depreciation + Cost Seg", eligibility: "later", estValue: "$10k-100k+/property",
    deadline: "Year of acquisition", status: "research",
    notes: "Phasing down: 60% in 2024, 40% in 2025, 20% in 2026. Cost seg breaks property into 5/7/15-yr classes." },
  { code: "Sec 199A", name: "QBI Deduction",           eligibility: "eligible", estValue: "20% of business income",
    deadline: "Sunsets Dec 31", status: "ready",
    notes: "20% deduction on pass-through income. SSTB phaseouts apply. CRITICAL: TCJA sunset risk." },
  { code: "WOTC",    name: "Work Opportunity Tax Credit", eligibility: "later", estValue: "$2400-9600/hire",
    status: "research", notes: "Hire from targeted groups. Need pre-screening Form 8850 day-one." },
  { code: "Sec 179", name: "Section 179 Expensing",     eligibility: "eligible", estValue: "Up to $1.16M/yr",
    deadline: "Annual", status: "research",
    notes: "Equipment, software, vehicles over 6,000 lbs GVWR. Immediate full deduction." },
];

const ELIGIBILITY_BADGE: Record<Credit["eligibility"], "active" | "warn" | "muted"> = {
  eligible: "active",
  maybe: "warn",
  later: "muted",
};

const STATUS_BADGE: Record<Credit["status"], "active" | "info" | "warn" | "alert"> = {
  research: "warn",
  ready: "info",
  claimed: "active",
  blocked: "alert",
};

export default function CreditsPage() {
  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          Layer 4
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Credits Engine</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          Stack what you qualify for. Some are timing-locked (R&amp;D retroactive, QSBS pre-event) and you cannot recover them later.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/5 p-4 mb-6 flex items-start gap-3">
        <AlertTriangle size={18} className="text-[var(--color-warn)] mt-0.5 flex-shrink-0" />
        <div className="text-sm">
          <span className="font-medium text-[var(--color-warn)]">Timing-locked credits:</span>{" "}
          <span className="text-[var(--color-fg)]">R&amp;D retroactive filing (3yr lookback) and QSBS C-corp formation must happen BEFORE specific events. Section 199A QBI sunsets Dec 31.</span>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-elevated)] border-b border-[var(--color-border)]">
              <tr className="text-left">
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Code</th>
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Credit</th>
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Eligibility</th>
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Estimated Value</th>
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Deadline</th>
                <th className="px-4 py-3 font-medium text-[var(--color-muted)] text-[11px] uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {CREDITS.map((c, i) => (
                <tr
                  key={c.code}
                  className={`border-b border-[var(--color-border)] last:border-0 ${i % 2 ? "bg-[var(--color-surface)]" : "bg-[var(--color-bg)]/40"} hover:bg-[var(--color-elevated)] transition`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-[var(--color-gold-400)]">{c.code}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{c.name}</div>
                    <div className="text-xs text-[var(--color-muted)] mt-0.5 max-w-md">{c.notes}</div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge variant={ELIGIBILITY_BADGE[c.eligibility]}>{c.eligibility}</StatusBadge>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{c.estValue}</td>
                  <td className="px-4 py-3 text-xs text-[var(--color-muted)]">
                    {c.deadline ? (
                      <span className="inline-flex items-center gap-1">
                        <Calendar size={10} /> {c.deadline}
                      </span>
                    ) : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge variant={STATUS_BADGE[c.status]}>{c.status}</StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
