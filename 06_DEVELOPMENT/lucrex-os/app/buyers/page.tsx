import { Users, MapPin, Phone, Mail, CheckCircle2 } from "lucide-react";
import { getBuyers, computeBuyerStats } from "@/lib/api/wholesale";

export const dynamic = "force-dynamic";

const STATUS_BADGE: Record<string, string> = {
  active:     "bg-green-400/10 text-green-400 border-green-400/30",
  contacted:  "bg-blue-400/10 text-blue-400 border-blue-400/30",
  pending:    "bg-amber-400/10 text-amber-400 border-amber-400/30",
  closed:     "bg-purple-400/10 text-purple-400 border-purple-400/30",
  cold:       "bg-gray-400/10 text-gray-400 border-gray-400/30",
};

export default async function BuyersPage() {
  const buyers = await getBuyers();
  const stats = computeBuyerStats(buyers);
  const sorted = [...buyers].sort((a, b) => (b.outreach_count ?? 0) - (a.outreach_count ?? 0));

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
          <Users size={20} /> CASH BUYERS
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Live buyer database · {stats.total} contacts · {Object.keys(stats.byState).length} states
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Total</div>
          <div className="font-mono text-2xl font-bold text-amber-400">{stats.total}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Responded</div>
          <div className="font-mono text-2xl font-bold text-green-400">{stats.responded}</div>
          <div className="text-[9px] text-gray-600 mt-0.5">
            {stats.total > 0 ? `${((stats.responded / stats.total) * 100).toFixed(0)}% rate` : "-"}
          </div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">On Deal List</div>
          <div className="font-mono text-2xl font-bold text-blue-400">{stats.onDealList}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Total Outreach</div>
          <div className="font-mono text-2xl font-bold text-purple-400">{stats.totalOutreach}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">States Active</div>
          <div className="font-mono text-2xl font-bold text-cyan-400">{Object.keys(stats.byState).length}</div>
        </div>
      </div>

      {/* By state + top cities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 mb-3">By State</h2>
          <div className="space-y-2">
            {Object.entries(stats.byState).sort(([, a], [, b]) => b - a).slice(0, 12).map(([s, n]) => (
              <div key={s} className="flex items-center gap-2">
                <span className="font-mono text-xs text-amber-400 w-8">{s}</span>
                <div className="flex-1 h-2 bg-white/[0.03] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full"
                    style={{ width: `${(n / stats.total) * 100}%` }}
                  />
                </div>
                <span className="font-mono text-xs text-gray-400 w-8 text-right">{n}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 mb-3">Top Cities</h2>
          <div className="space-y-2">
            {stats.topCities.map((c) => (
              <div key={c.city} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin size={11} className="text-gray-500" />
                  <span className="text-sm text-gray-300">{c.city}</span>
                </div>
                <span className="font-mono text-xs text-amber-400">{c.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Buyer list */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">All Buyers</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-white/[0.02] border-b border-white/[0.04]">
              <tr className="text-left">
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium">Company</th>
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium">Location</th>
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium">Criteria</th>
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium">Contact</th>
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium">Status</th>
                <th className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500 font-medium text-right">Activity</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((b, i) => (
                <tr key={`${b.company}-${i}`} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-gray-200">{b.company}</div>
                    {b.responded && (
                      <div className="flex items-center gap-1 text-[10px] text-green-400 mt-0.5">
                        <CheckCircle2 size={10} /> responded
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-400">
                    <div>{b.city}</div>
                    <div className="text-[10px] font-mono text-amber-400/70">{b.state}</div>
                  </td>
                  <td className="px-4 py-2.5 text-[11px] text-gray-400 max-w-[200px] truncate">{b.buy_criteria}</td>
                  <td className="px-4 py-2.5 text-[11px] text-gray-400">
                    {b.email && <div className="flex items-center gap-1"><Mail size={10} /> <a href={`mailto:${b.email}`} className="hover:text-amber-400 truncate max-w-[150px] block">{b.email}</a></div>}
                    {b.phone && <div className="flex items-center gap-1 mt-0.5"><Phone size={10} /> {b.phone}</div>}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold border ${STATUS_BADGE[b.status ?? "cold"] ?? STATUS_BADGE.cold}`}>
                      {b.status || "cold"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-[10px] font-mono">
                    <div className="text-gray-300">{b.outreach_count ?? 0} touches</div>
                    {b.last_outreach && <div className="text-gray-600">{b.last_outreach}</div>}
                  </td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr><td colSpan={6} className="text-center py-8 text-gray-500 text-sm">No buyers loaded.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
