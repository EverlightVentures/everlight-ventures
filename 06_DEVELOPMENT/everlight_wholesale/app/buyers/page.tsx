import { loadBuyers } from "@/lib/data";
import { Mail, Phone, MapPin } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

export default async function BuyersPage() {
  const buyers = await loadBuyers();

  // Group by state
  const byState = new Map<string, typeof buyers>();
  for (const b of buyers) {
    const st = (b.state || "??").toUpperCase();
    const arr = byState.get(st) ?? [];
    arr.push(b);
    byState.set(st, arr);
  }
  const states = [...byState.keys()].sort();

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Cash buyers" }]} />
      <header>
        <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">The buy side</div>
        <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">Cash buyers</h1>
        <p className="text-fog text-sm mt-2 max-w-2xl">
          When a seller says yes, these are the investors who get the deal blasted. Ranked by state, ready to match.
        </p>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
        {states.map((st) => (
          <a key={st} href={`#${st}`}
            className="bg-card-gradient border border-ash rounded-lg px-3 py-3 text-center hover:border-gold/50 transition">
            <div className="text-[10px] tracking-[0.2em] text-fog uppercase">{st}</div>
            <div className="kpi-num text-xl mt-1">{byState.get(st)!.length}</div>
          </a>
        ))}
      </div>

      <div className="space-y-10">
        {states.map((st) => (
          <section key={st} id={st}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gold/10 border border-gold/30 rounded flex items-center justify-center">
                <span className="font-display text-gold text-lg">{st}</span>
              </div>
              <div>
                <h2 className="font-display text-xl text-ivory">{st} buyers</h2>
                <p className="text-[11px] text-fog">{byState.get(st)!.length} in queue</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {byState.get(st)!.map((b, i) => (
                <div key={`${b.email}-${i}`}
                  className="card-hover bg-card-gradient border border-ash rounded-xl p-4 transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-ivory">{b.company || b.name}</div>
                      {b.company && b.name && b.name !== b.company && (
                        <div className="text-[11px] text-fog">{b.name}</div>
                      )}
                    </div>
                    {b.on_deal_list && (
                      <span className="text-[10px] tracking-widest bg-gold/10 text-gold border border-gold/30 rounded-full px-2 py-0.5">ACTIVE</span>
                    )}
                  </div>
                  <div className="text-[12px] text-fog mt-3 space-y-1">
                    {b.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-3 h-3 text-smoke" />
                        <span className="truncate">{b.email}</span>
                      </div>
                    )}
                    {b.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-3 h-3 text-smoke" />
                        <span>{b.phone}</span>
                      </div>
                    )}
                    {(b.city || b.market) && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3 h-3 text-smoke" />
                        <span>{b.city || b.market}</span>
                      </div>
                    )}
                  </div>
                  {b.buy_criteria && (
                    <p className="text-[11px] text-smoke mt-3 leading-relaxed line-clamp-3">
                      {b.buy_criteria}
                    </p>
                  )}
                  <div className="mt-3 pt-3 border-t border-ash/50 flex items-center justify-between text-[10px] text-fog">
                    <span>sent {b.deals_sent ?? 0}</span>
                    <span>closed {b.deals_closed ?? 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}