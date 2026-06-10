import { getWholesaleSummary } from "@/lib/api/django";
import { KPICard } from "@/components/KPICard";
import { StatusBadge } from "@/components/StatusBadge";
import { Phone, Mail, Map, Zap } from "lucide-react";

const STAGES = [
  { key: "lead",      label: "Lead",      accent: "#888888" },
  { key: "qualified", label: "Qualified", accent: "#3B82F6" },
  { key: "offer",     label: "Offer",     accent: "#F59E0B" },
  { key: "contract",  label: "Contract",  accent: "#A855F7" },
  { key: "closed",    label: "Closed",    accent: "#22C55E" },
] as const;

export default async function WholesalePage() {
  const summary = await getWholesaleSummary();
  const total = STAGES.reduce((sum, s) => sum + (summary.byStage[s.key] ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard label="Active Leads"  value={String(summary.totalLeads)} status={summary.totalLeads > 0 ? "active" : "idle"} accent="#D97706" />
        <KPICard label="In Contract"   value={String(summary.byStage.contract ?? 0)} status="neutral" accent="#A855F7" />
        <KPICard label="Closed YTD"    value={String(summary.byStage.closed ?? 0)}   status="active"  accent="#22C55E" />
        <KPICard label="Cleveland"     value={`${summary.topCities.find((c) => c.city.toLowerCase() === "cleveland")?.count ?? 0}`} hint="niche focus" status="neutral" accent="#06B6D4" />
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <h2 className="font-display text-xl font-semibold">Pipeline kanban</h2>
          <StatusBadge variant={total > 0 ? "active" : "muted"}>
            {total} total in pipeline
          </StatusBadge>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {STAGES.map((s) => {
            const count = summary.byStage[s.key] ?? 0;
            return (
              <div key={s.key} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span
                    className="text-[10px] uppercase tracking-widest font-medium"
                    style={{ color: s.accent }}
                  >
                    {s.label}
                  </span>
                  <span className="font-mono text-sm font-semibold">{count}</span>
                </div>
                <div className="h-px w-full" style={{ background: s.accent, opacity: 0.3 }} />
                {count === 0 && (
                  <div className="text-xs text-[var(--color-muted)] italic mt-2">empty</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Phone size={16} style={{ color: "var(--accent)" }} />
            <h3 className="font-display text-base font-semibold">Phone-first</h3>
          </div>
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            Cold calls run inside state_gates rules. NC out (HB 797). TX cold SMS blocked (SB 140). CA pre-foreclosure blocked (CC 2945).
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Mail size={16} style={{ color: "var(--accent)" }} />
            <h3 className="font-display text-base font-semibold">Direct mail</h3>
          </div>
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            Lob integration ready, awaiting LOB_API_KEY + budget. Yellow letter + postcard sequence built.
          </p>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Map size={16} style={{ color: "var(--accent)" }} />
            <h3 className="font-display text-base font-semibold">JV scout</h3>
          </div>
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            Buyer list builder + jv_wholesaler_scout active. Cleveland-niche scoring tightened on institutional filter.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={16} style={{ color: "var(--accent)" }} />
          <h2 className="font-display text-xl font-semibold">Open levers (NEXT_LEVERS.md)</h2>
        </div>
        <ul className="space-y-2 text-sm">
          {[
            { lever: "Skip-trace integration", status: "blocked", note: "needs vendor (BatchSkipTracing or DealMachine)" },
            { lever: "ATTOM property discovery", status: "blocked", note: "needs API key" },
            { lever: "IMAP IDLE inbox watcher", status: "ready", note: "code drafted, deploy pending" },
            { lever: "VA hire (CALLBACKS)", status: "blocked", note: "VA_HIRING_KIT shipped, waiting on first hire" },
            { lever: "GOOGLE_PLACES_API_KEY", status: "blocked", note: "blocks buyer_list_builder enrichment" },
          ].map((l) => (
            <li key={l.lever} className="flex items-start justify-between gap-3 p-3 rounded border border-[var(--color-border)] bg-[var(--color-bg)]/30">
              <div className="flex-1 min-w-0">
                <div className="font-medium">{l.lever}</div>
                <div className="text-xs text-[var(--color-muted)] mt-0.5">{l.note}</div>
              </div>
              <StatusBadge variant={l.status === "blocked" ? "alert" : "info"}>{l.status}</StatusBadge>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
