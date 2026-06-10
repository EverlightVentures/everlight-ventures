import Link from "next/link";
import { loadLeads, hasContact, isIndividual, leadARV } from "@/lib/data";
import { compactMoney, humanStatus, statusColor, timeAgo } from "@/lib/utils";
import { ArrowRight } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

const STAGES: { key: string; title: string; hint: string }[] = [
  { key: "new",              title: "New",              hint: "just landed in the book" },
  { key: "contacted",        title: "In sequence",      hint: "Piper touching them" },
  { key: "negotiating",      title: "Negotiating",      hint: "Rex working the reply" },
  { key: "verbal_agreement", title: "Verbal YES",       hint: "Marcus drafting contract" },
  { key: "contract_sent",    title: "Contract sent",    hint: "awaiting your signature" },
  { key: "signed",           title: "Signed",           hint: "blasting to buyers" },
  { key: "buyer_blast",      title: "Buyer blast",      hint: "fishing for assignment" },
  { key: "contract_assigned",title: "Assigned",         hint: "at title" },
  { key: "title_hold",       title: "At title",         hint: "closing in progress" },
  { key: "closed",           title: "Closed",           hint: "funds wiring" },
  { key: "funds_received",   title: "Funds received",   hint: "money landed" },
];

export default async function PipelinePage() {
  const leads = await loadLeads();

  const byStage: Record<string, typeof leads> = {};
  for (const s of STAGES) byStage[s.key] = [];
  for (const l of leads) {
    const s = (l.status || "new") as string;
    if (byStage[s]) byStage[s].push(l);
    else (byStage.new ??= []).push(l);
  }

  // Totals
  const totalActive = Object.entries(byStage)
    .filter(([k]) => k !== "new")
    .reduce((n, [, arr]) => n + arr.length, 0);
  const totalClosed = (byStage.closed?.length ?? 0) + (byStage.funds_received?.length ?? 0);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Pipeline" }]} />
      <header className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Funnel view</div>
          <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">Pipeline</h1>
          <p className="text-fog text-sm mt-2 max-w-2xl">
            Every lead by stage. Watch deals move left-to-right as the machine works.
          </p>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Active</div>
            <div className="kpi-num text-3xl">{totalActive}</div>
          </div>
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Closed</div>
            <div className="kpi-num text-3xl">{totalClosed}</div>
          </div>
        </div>
      </header>

      <div className="flex gap-3 overflow-x-auto pb-4 -mx-6 px-6">
        {STAGES.map((s) => {
          const items = byStage[s.key] || [];
          const sumArv = items.reduce((n, l) => n + leadARV(l), 0);
          return (
            <div
              key={s.key}
              className="min-w-[260px] max-w-[260px] flex-shrink-0 bg-card-gradient border border-ash rounded-xl flex flex-col"
            >
              <div className="p-3 border-b border-ash/60">
                <div className="flex items-center justify-between">
                  <div className="text-[10px] tracking-[0.25em] text-fog uppercase">{s.title}</div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full border ${statusColor(s.key)}`}
                  >
                    {items.length}
                  </span>
                </div>
                <div className="text-[11px] text-smoke mt-0.5">{s.hint}</div>
                {sumArv > 0 && (
                  <div className="text-[11px] text-gold/80 mt-1 font-mono">
                    {compactMoney(sumArv)} ARV total
                  </div>
                )}
              </div>

              <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[600px]">
                {items.length === 0 && (
                  <div className="text-[11px] text-smoke text-center py-6 italic">empty</div>
                )}
                {items.slice(0, 25).map((l) => (
                  <Link
                    key={l.id}
                    href={`/leads/${l.id}`}
                    className="block p-2.5 bg-graphite hover:bg-ash border border-ash/50 hover:border-gold/50 rounded-lg transition-colors"
                  >
                    <div className="text-[12px] font-medium text-ivory truncate">
                      {(l.owner_name || "Unknown").replace(/\s+/g, " ").trim()}
                    </div>
                    <div className="text-[11px] text-smoke truncate">
                      {l.address}
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-[10px] text-fog">{l.state}</span>
                      <span className="text-[10px] text-gold font-mono">
                        {compactMoney(leadARV(l))}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      {Array.from({ length: 7 }).map((_, i) => (
                        <span
                          key={i}
                          className={`h-0.5 flex-1 rounded-full ${i < (l.outreach_count ?? 0) ? "bg-gold" : "bg-ash"}`}
                        />
                      ))}
                    </div>
                    {l.last_outreach && (
                      <div className="text-[10px] text-smoke mt-1">{timeAgo(l.last_outreach)}</div>
                    )}
                  </Link>
                ))}
                {items.length > 25 && (
                  <div className="text-[11px] text-fog text-center py-2 border-t border-ash/50">
                    +{items.length - 25} more
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}