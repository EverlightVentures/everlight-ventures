import { loadLeads, computeKPIs } from "@/lib/data";
import { KPIStrip } from "@/components/kpi-strip";
import { PipelineChart } from "@/components/pipeline-chart";
import { LeadTable } from "@/components/lead-table";
import { AutoRefresh } from "@/components/auto-refresh";

export const dynamic = "force-dynamic";

export default async function DashboardHome() {
  const [leads, kpis] = await Promise.all([loadLeads(), computeKPIs()]);

  const chartData = Object.entries(kpis.by_state)
    .filter(([st]) => ["GA", "FL", "TX", "MO", "AZ", "TN"].includes(st))
    .sort((a, b) => b[1].total - a[1].total)
    .map(([state, v]) => ({
      state,
      total: v.total,
      contactable: v.contactable,
      in_seq: v.in_seq,
      replied: v.replied,
    }));

  return (
    <div className="space-y-8">
      <section className="flex items-end justify-between">
        <div>
          <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Wholesale Command</div>
          <h1 className="font-display text-4xl md:text-5xl text-ivory mt-2 tracking-tight">
            Your pipeline at a glance
          </h1>
          <p className="text-fog text-sm mt-2 max-w-2xl">
            Every seller reached, every reply, every offer on the table. Built so you can watch the deal come to you.
          </p>
        </div>
        <div className="hidden md:block text-right">
          <AutoRefresh intervalSeconds={45} label="live" />
          <div className="text-gold font-mono text-sm mt-1">
            {new Date().toLocaleString("en-US", {
              timeZone: "America/Los_Angeles",
              month: "short", day: "numeric",
              hour: "numeric", minute: "2-digit",
              timeZoneName: "short",
            })}
          </div>
        </div>
      </section>

      <KPIStrip kpis={kpis} />

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <PipelineChart data={chartData} />
        </div>
        <div className="bg-card-gradient border border-ash rounded-xl p-5">
          <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Next deal</div>
          <h3 className="font-display text-xl text-ivory mt-1">What moves next</h3>
          <ul className="space-y-3 mt-4 text-sm">
            <BulletItem label="In sequence" value={kpis.in_sequence}
              hint="Piper is actively working these" />
            <BulletItem label="Waiting reply" value={kpis.in_sequence - kpis.replied}
              hint="midway through the 7-touch cadence" />
            <BulletItem label="Replied" value={kpis.replied} highlight
              hint="warm -- Rex is negotiating" />
            <BulletItem label="Contract-ready" value={0} highlight
              hint="Marcus will DM you when one hits" />
          </ul>
          <div className="mt-6 pt-4 border-t border-ash/60">
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Your loop</div>
            <ol className="text-[12px] text-fog mt-2 space-y-1">
              <li className="flex gap-2"><span className="text-gold">1.</span>Morning brief lands in #ceo-brief</li>
              <li className="flex gap-2"><span className="text-gold">2.</span>#hive-alerts pings when action needed</li>
              <li className="flex gap-2"><span className="text-gold">3.</span>Sign contract, pick up title call</li>
              <li className="flex gap-2"><span className="text-gold">4.</span>Funds wire in. Repeat.</li>
            </ol>
          </div>
        </div>
      </div>

      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">The book</div>
            <h2 className="font-display text-2xl text-ivory mt-1">All leads</h2>
          </div>
        </div>
        <LeadTable leads={leads} />
      </section>
    </div>
  );
}

function BulletItem({
  label, value, hint, highlight,
}: { label: string; value: number; hint?: string; highlight?: boolean }) {
  return (
    <li className="flex items-start justify-between gap-3">
      <div>
        <div className={highlight ? "text-gold font-medium" : "text-ivory"}>{label}</div>
        {hint && <div className="text-[11px] text-smoke mt-0.5">{hint}</div>}
      </div>
      <span className={`font-mono tabular-nums text-lg ${highlight ? "text-gold" : "text-ivory"}`}>
        {value}
      </span>
    </li>
  );
}
