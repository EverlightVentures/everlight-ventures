import Link from "next/link";
import { loadDealEvents, loadLeads } from "@/lib/data";
import { timeAgo } from "@/lib/utils";
import { Clock } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

const EVENT_STYLE: Record<string, { emoji: string; label: string; glow?: string }> = {
  wholesale_lead_new:       { emoji: "+", label: "new lead ingested" },
  wholesale_reply:          { emoji: "R", label: "seller replied", glow: "text-success" },
  magnet_click:             { emoji: "*", label: "CashOfferScan click" },
  magnet_accept:            { emoji: "A", label: "seller ACCEPTED offer", glow: "text-success" },
  magnet_counter:           { emoji: "?", label: "seller countered", glow: "text-warning" },
  magnet_call:              { emoji: "C", label: "seller requested a call", glow: "text-gold" },
  magnet_not_interested:    { emoji: "-", label: "seller passed" },
  stripe_charge:            { emoji: "$", label: "Stripe payment", glow: "text-gold" },
};

export default async function ActivityPage() {
  const [events, leads] = await Promise.all([loadDealEvents(), loadLeads()]);
  const leadMap = new Map(leads.map((l) => [String(l.id ?? ""), l]));

  // Newest first, cap at 200
  const sorted = [...events].reverse().slice(0, 200);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Activity" }]} />
      <header className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Event stream</div>
          <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">Activity</h1>
          <p className="text-fog text-sm mt-2 max-w-2xl">
            Everything that happened, newest first. Every lead opened, reply caught, magnet clicked, call requested.
          </p>
        </div>
        <div>
          <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Last 200</div>
          <div className="kpi-num text-3xl">{sorted.length}</div>
        </div>
      </header>

      <ol className="space-y-1.5">
        {sorted.map((ev) => {
          const payload: any = ev.payload || {};
          const leadId: string = payload.lead_id
            || (payload.record && payload.record.id)
            || "";
          const lead = leadMap.get(leadId);
          const style = EVENT_STYLE[ev.type] || { emoji: "-", label: ev.type };
          return (
            <li
              key={ev.id}
              className="flex items-center gap-3 p-3 bg-card-gradient border border-ash/60 rounded-lg hover:border-gold/40 transition-colors"
            >
              <span className={`flex-none w-8 h-8 rounded-full bg-ash flex items-center justify-center font-mono text-sm ${style.glow || "text-ivory"}`}>
                {style.emoji}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ivory">{style.label}</div>
                <div className="text-[11px] text-smoke truncate">
                  {lead
                    ? <>{(lead.owner_name || "Unknown").replace(/\s+/g, " ").trim()}
                        {" -- "}{lead.address} ({lead.state})</>
                    : <>lead <code className="text-fog">{leadId || "?"}</code></>
                  }
                </div>
              </div>
              {lead && (
                <Link
                  href={`/leads/${leadId}`}
                  className="text-[11px] text-gold/80 hover:text-gold"
                >
                  open
                </Link>
              )}
              <div className="text-[11px] text-fog font-mono whitespace-nowrap">
                <Clock className="inline w-3 h-3 mr-1 text-smoke" />
                {timeAgo(ev.ts)}
              </div>
            </li>
          );
        })}
      </ol>

      {sorted.length === 0 && (
        <div className="text-center py-16 text-smoke">
          No events yet. The moment Belfort fires or a magnet clicks, it lands here.
        </div>
      )}
    </div>
  );
}