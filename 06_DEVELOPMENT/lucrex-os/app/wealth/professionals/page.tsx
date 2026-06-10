import { getProfessionals } from "@/lib/wealth";
import { StatusBadge } from "@/components/StatusBadge";
import { UserCircle, Briefcase, Scale, Shield, Building2 } from "lucide-react";

type ProMeta = {
  role: string;
  icon: typeof UserCircle;
  tier: string;
  blurb: string;
};

const ROLES: ProMeta[] = [
  { role: "CPA / Tax Strategist",       icon: Briefcase,  tier: "T01", blurb: "Entity setup, S-Corp election, R&D documentation. Hire one who understands WY/DE entity stack and Section 174." },
  { role: "Estate Attorney",             icon: Scale,      tier: "T05", blurb: "DAPT, ILIT, GRAT, dynasty trust drafting. Domicile-licensed (NV, SD, WY, DE preferred)." },
  { role: "Real Estate Attorney",        icon: Building2,  tier: "T03", blurb: "Title work, 1031, Series LLC for property holdings, asset protection on RE side." },
  { role: "Independent Fiduciary",       icon: Shield,     tier: "T08", blurb: "Trust company OR licensed individual. Cannot be you. Required for DAPT and Dynasty trusts." },
  { role: "Asset Protection Counsel",    icon: Shield,     tier: "T05", blurb: "Equity stripping, Cook Islands, captive insurance. Specialized practice, not GP attorney." },
  { role: "Investment Manager / RIA",    icon: UserCircle, tier: "T08", blurb: "Family office IM. Fee-only fiduciary, no commissioned products. Manages PPLI and direct allocations." },
];

export default async function ProfessionalsPage() {
  const docs = await getProfessionals();

  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          Roster
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Professionals</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          You direct them, they execute. Build progressively from T1 forward. Always interview at least
          three per role and use the Layer 4 question scripts.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {ROLES.map((r) => {
          const Icon = r.icon;
          return (
            <div key={r.role} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 hover:border-[var(--color-gold-700)] transition">
              <div className="flex items-start gap-3 mb-3">
                <div className="h-10 w-10 rounded-lg bg-[var(--color-gold-500)]/10 border border-[var(--color-gold-700)]/30 flex items-center justify-center flex-shrink-0">
                  <Icon size={18} className="text-[var(--color-gold-500)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="font-display text-base font-semibold">{r.role}</h3>
                    <StatusBadge variant="info">activate at {r.tier}</StatusBadge>
                  </div>
                  <p className="text-xs text-[var(--color-muted)] leading-relaxed">{r.blurb}</p>
                </div>
              </div>
              <div className="text-xs text-[var(--color-muted)] border-t border-[var(--color-border)] pt-3 flex items-center justify-between">
                <span>0 candidates shortlisted</span>
                <span className="text-[var(--color-faint)]">Build at activation</span>
              </div>
            </div>
          );
        })}
      </div>

      {docs.length > 0 && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <h3 className="font-display text-lg font-semibold mb-3">Notes from 05_Professionals</h3>
          <ul className="space-y-2">
            {docs.map((d) => (
              <li key={d.slug} className="text-sm">
                <span className="text-[var(--color-gold-400)] font-mono text-xs mr-2">{d.slug}</span>
                {d.title}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
