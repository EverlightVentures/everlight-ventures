import type { Buyer, Lead } from "@/lib/types";
import { Mail, Phone, MapPin, Flame, CheckCircle2 } from "lucide-react";
import { compactMoney } from "@/lib/utils";
import { leadARV } from "@/lib/data";

/** Ranks buyers for a given lead.
 *  Priority: state match > market match > price-band compatibility > recent activity. */
export function MatchedBuyers({ lead, buyers }: { lead: Lead; buyers: Buyer[] }) {
  const state = (lead.state || "").toUpperCase();
  const city = (lead.city || "").toLowerCase();
  const arv = leadARV(lead);

  const scored: { buyer: Buyer; score: number; reasons: string[] }[] = [];
  for (const b of buyers) {
    const bState = (b.state || "").toUpperCase();
    if (bState !== state) continue;
    let score = 10;
    const reasons: string[] = [`${bState} buy-box`];

    // Market match
    const bCity = (b.city || "").toLowerCase();
    const bMarket = (b.market || "").toLowerCase();
    if (city && (bCity === city || bMarket.includes(city) || city.includes(bMarket))) {
      score += 20;
      reasons.push(`${b.market || b.city} specialist`);
    }

    // Price band: look for ARV number in criteria text
    const crit = (b.buy_criteria || "").toLowerCase();
    if (arv > 0) {
      if (crit.includes("any price") || crit.includes("all prices")) {
        score += 5;
      }
      // crude: pick up `$50k-$250k` style bands
      const m = crit.match(/\$([\d.]+)k[^\d]+\$([\d.]+)k/);
      if (m) {
        const lo = Number(m[1]) * 1000;
        const hi = Number(m[2]) * 1000;
        if (arv >= lo && arv <= hi) {
          score += 15;
          reasons.push(`buy-box fits ${compactMoney(arv)}`);
        }
      }
    }

    // Recent activity
    if (b.on_deal_list) { score += 10; reasons.push("active on list"); }
    if (b.responded)    { score += 5;  reasons.push("responsive"); }

    scored.push({ buyer: b, score, reasons });
  }

  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, 6);

  if (top.length === 0) {
    return (
      <div className="p-5 border border-dashed border-ash rounded-xl text-center">
        <div className="text-sm text-fog">No {state} buyers in the book yet.</div>
        <div className="text-[11px] text-smoke mt-1">
          Add {state} cash buyers to buyers_db so Marcus can assign this deal.
        </div>
      </div>
    );
  }

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
      {top.map(({ buyer: b, score, reasons }, i) => (
        <div
          key={`${b.email || b.name}-${i}`}
          className={`border rounded-xl p-4 transition hover:border-gold/50 ${
            i === 0 ? "border-gold/40 bg-gold/5" : "border-ash bg-card-gradient"
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                {i === 0 && <Flame className="w-4 h-4 text-gold" />}
                <span className="text-[10px] tracking-[0.25em] text-fog uppercase">
                  #{i + 1} match &middot; score {score}
                </span>
              </div>
              <div className="font-medium text-ivory mt-1 truncate">
                {b.company || b.name}
              </div>
              {b.company && b.name && b.name !== b.company && (
                <div className="text-[11px] text-fog truncate">{b.name}</div>
              )}
            </div>
            {b.on_deal_list && (
              <CheckCircle2 className="w-4 h-4 text-success" />
            )}
          </div>

          <div className="text-[12px] text-fog space-y-1 mt-2">
            {b.email && (
              <div className="flex items-center gap-2 min-w-0">
                <Mail className="w-3 h-3 text-smoke flex-none" />
                <span className="truncate">{b.email}</span>
              </div>
            )}
            {b.phone && (
              <div className="flex items-center gap-2">
                <Phone className="w-3 h-3 text-smoke" />
                <span>{b.phone}</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <MapPin className="w-3 h-3 text-smoke" />
              <span>{b.market || b.city || b.state}</span>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-ash/50">
            <div className="flex flex-wrap gap-1.5">
              {reasons.slice(0, 3).map((r, j) => (
                <span
                  key={j}
                  className="text-[10px] tracking-wide bg-graphite border border-ash px-2 py-0.5 rounded-full text-fog"
                >
                  {r}
                </span>
              ))}
            </div>
            {b.buy_criteria && (
              <p className="text-[11px] text-smoke mt-2 leading-relaxed line-clamp-2">
                {b.buy_criteria}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
