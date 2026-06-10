import Link from "next/link";
import { loadLeads, offerRange, leadARV, strategyLane } from "@/lib/data";
import { compactMoney, humanStatus, timeAgo } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { MapPin, ArrowRight } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

// Active deal statuses: anything that's moving, not raw new and not dead.
const ACTIVE = new Set([
  "contacted", "negotiating", "verbal_agreement", "contract_sent",
  "signed", "buyer_blast", "contract_assigned", "title_hold", "closed",
]);

export default async function DealsPage() {
  const leads = await loadLeads();
  const active = leads.filter((l) => ACTIVE.has(l.status as string));

  // Order: closer-to-close-first (reverse status weight), then by ARV
  const WEIGHT: Record<string, number> = {
    contacted: 10, negotiating: 20, verbal_agreement: 30,
    contract_sent: 40, signed: 50, buyer_blast: 60,
    contract_assigned: 70, title_hold: 80, closed: 90,
  };
  active.sort((a, b) =>
    (WEIGHT[b.status as string] ?? 0) - (WEIGHT[a.status as string] ?? 0) ||
    leadARV(b) - leadARV(a)
  );

  const totalARV = active.reduce((n, l) => n + leadARV(l), 0);
  const totalOfferMid = active.reduce((n, l) => n + offerRange(l).mid, 0);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Active deals" }]} />
      <header className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">The movers</div>
          <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">
            Active deals
          </h1>
          <p className="text-fog text-sm mt-2 max-w-2xl">
            Every lead past first touch, not yet dead. Sorted by how close they are to close.
          </p>
        </div>
        <div className="flex gap-5 text-right">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Active</div>
            <div className="kpi-num text-3xl">{active.length}</div>
          </div>
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Combined ARV</div>
            <div className="kpi-num text-3xl">{compactMoney(totalARV)}</div>
          </div>
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Offer pool</div>
            <div className="kpi-num text-3xl">{compactMoney(totalOfferMid)}</div>
          </div>
        </div>
      </header>

      {active.length === 0 && (
        <div className="text-center py-20 border border-ash border-dashed rounded-xl">
          <div className="text-fog text-sm">
            No active deals yet. The first touch of Belfort's next cron will populate this list.
          </div>
        </div>
      )}

      <div className="space-y-3">
        {active.map((l) => {
          const offer = offerRange(l);
          const lane = strategyLane(l);
          return (
            <Link
              key={l.id}
              href={`/leads/${l.id}`}
              className="group block bg-card-gradient border border-ash rounded-xl p-4 hover:border-gold/50 hover:shadow-gold-glow transition-all"
            >
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <StatusBadge status={l.status as string} />
                    <span className="text-[11px] tracking-wide text-gold/80">{lane}</span>
                    {l.detected_distress && (
                      <span className="text-[11px] text-smoke">
                        distress: <code className="text-fog">{l.detected_distress}</code>
                      </span>
                    )}
                  </div>
                  <div className="font-medium text-ivory mt-1.5">
                    {(l.owner_name || "Unknown").replace(/\s+/g, " ").trim()}
                  </div>
                  <div className="text-[12px] text-fog flex items-center gap-1 mt-0.5">
                    <MapPin className="w-3 h-3" />
                    {l.address}, {l.city}, {l.state}
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-[10px] tracking-[0.2em] text-fog uppercase">ARV</div>
                    <div className="font-mono text-ivory">{compactMoney(leadARV(l))}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] tracking-[0.2em] text-fog uppercase">Offer</div>
                    <div className="font-mono text-gold">{compactMoney(offer.mid)}</div>
                  </div>
                  <div className="text-right min-w-[80px]">
                    <div className="text-[10px] tracking-[0.2em] text-fog uppercase">Touches</div>
                    <div className="flex items-center gap-1 mt-0.5 justify-end">
                      {Array.from({ length: 7 }).map((_, i) => (
                        <span
                          key={i}
                          className={`w-1 h-3 rounded-sm ${i < (l.outreach_count ?? 0) ? "bg-gold" : "bg-ash"}`}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="text-right min-w-[70px]">
                    <div className="text-[10px] tracking-[0.2em] text-fog uppercase">Last</div>
                    <div className="text-[11px] text-fog">{timeAgo(l.last_outreach)}</div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-smoke group-hover:text-gold transition-colors" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}