import type { KPIs } from "@/lib/types";
import { TrendingUp, Users, Mail, HandshakeIcon, DollarSign, Eye } from "lucide-react";

export function KPIStrip({ kpis }: { kpis: KPIs }) {
  const cards = [
    { label: "Total leads",    value: kpis.total,         sub: `${kpis.new_today} new today`,       Icon: TrendingUp },
    { label: "Contactable",    value: kpis.contactable,   sub: `${pct(kpis.contactable, kpis.total)}% of book`, Icon: Users },
    { label: "In sequence",    value: kpis.in_sequence,   sub: "active Piper touches",              Icon: Mail },
    { label: "Replies",        value: kpis.replied,       sub: `${pct(kpis.replied, kpis.contactable)}% reply rate`, Icon: HandshakeIcon },
    { label: "Closed",         value: kpis.closed,        sub: "funded deals",                      Icon: DollarSign },
    { label: "Clicks (24h)",   value: kpis.clicks_24h,    sub: "CashOfferScan",                     Icon: Eye },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="card-hover bg-card-gradient border border-ash rounded-xl px-4 py-4 transition-all"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] tracking-[0.25em] text-fog uppercase">{c.label}</span>
            <c.Icon className="w-4 h-4 text-gold/60" />
          </div>
          <div className="kpi-num text-3xl">{c.value.toLocaleString()}</div>
          <div className="text-[11px] text-smoke mt-1">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}

function pct(num: number, den: number): number {
  if (!den) return 0;
  return Math.round((num / den) * 100);
}
