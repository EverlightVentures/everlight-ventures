"use client";
import { useState } from "react";
import { useApi, formatUSD, timeAgo } from "@/lib/api/client";

type Stream = "wholesale" | "broker" | "bot" | "consulting" | "publishing" | "saas";

const STREAMS: Array<{ key: Stream; label: string; icon: string; color: string; bg: string }> = [
  { key: "wholesale",  label: "Wholesale",     icon: "W", color: "text-green-400",  bg: "bg-green-400/10" },
  { key: "broker",     label: "Broker OS",     icon: "B", color: "text-amber-400",  bg: "bg-amber-400/10" },
  { key: "bot",        label: "XLM Bot",       icon: "X", color: "text-blue-400",   bg: "bg-blue-400/10" },
  { key: "consulting", label: "AI Consulting", icon: "C", color: "text-purple-400", bg: "bg-purple-400/10" },
  { key: "publishing", label: "Publishing",    icon: "P", color: "text-pink-400",   bg: "bg-pink-400/10" },
  { key: "saas",       label: "SaaS Products", icon: "S", color: "text-cyan-400",   bg: "bg-cyan-400/10" },
];

const MONTHLY_GOAL = 10000;

type Tx = {
  id?: string;
  type?: string;
  amount?: number;
  description?: string;
  customer?: string;
  source?: string;
  status?: string;
  created_at?: string;
};

type RevenueData = {
  mrr?: number;
  monthly_revenue?: number;
  today_revenue?: number;
  active_subscriptions?: number;
  total_customers?: number;
  streams?: Partial<Record<Stream, number>>;
  recent_transactions?: Tx[];
};

function KpiCard({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: string }) {
  return (
    <div className="card">
      <div className="text-[8px] uppercase tracking-widest text-gray-500">{label}</div>
      <div className={`font-mono text-2xl font-bold ${accent ?? "text-white"}`}>{value}</div>
      {sub && <div className="text-[9px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function RevenuePage() {
  const { data, error } = useApi<RevenueData>("/api/trading/proxy/django/revenue", 30000);
  const [expandedTx, setExpandedTx] = useState<number | null>(null);

  const mrr = data?.mrr ?? 0;
  const monthlyRev = data?.monthly_revenue ?? 0;
  const todayRev = data?.today_revenue ?? 0;
  const activeSubs = data?.active_subscriptions ?? 0;
  const totalCustomers = data?.total_customers ?? 0;
  const streams = data?.streams ?? {};
  const transactions = data?.recent_transactions ?? [];
  const goalPct = Math.min((monthlyRev / MONTHLY_GOAL) * 100, 100);

  if (!data && !error) {
    return (
      <div className="p-6 space-y-4 animate-pulse max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card">
              <div className="h-2 w-12 bg-white/[0.05] rounded mb-2" />
              <div className="h-6 w-16 bg-white/[0.08] rounded" />
            </div>
          ))}
        </div>
        <div className="card h-48 flex items-center justify-center">
          <div className="text-[10px] text-gray-600 tracking-widest">Loading Revenue...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider">REVENUE</h1>
          <p className="text-xs text-gray-500 mt-1">Everlight Ventures revenue dashboard</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : "bg-green-400 pulse-live"}`} />
          <span className="text-[9px] text-gray-500 font-mono">30s refresh</span>
        </div>
      </div>

      {error && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">API connection issue, data may be stale</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard label="MRR"         value={formatUSD(mrr)}        accent="text-amber-400" sub="monthly recurring" />
        <KpiCard label="This Month"  value={formatUSD(monthlyRev)} accent="text-green-400" sub={`${goalPct.toFixed(0)}% of goal`} />
        <KpiCard label="Today"       value={formatUSD(todayRev)}   accent="text-white" />
        <KpiCard label="Active Subs" value={activeSubs}             accent="text-blue-400" />
        <KpiCard label="Customers"   value={totalCustomers}         accent="text-purple-400" />
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Monthly Goal</div>
          <div className="text-[10px] text-gray-500 font-mono">{formatUSD(monthlyRev)} / {formatUSD(MONTHLY_GOAL)}</div>
        </div>
        <div className="w-full h-4 bg-white/[0.03] rounded-full overflow-hidden relative">
          <div
            className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all duration-1000"
            style={{ width: `${Math.max(goalPct, 1)}%` }}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono text-[10px] font-bold text-white drop-shadow-lg">{goalPct.toFixed(1)}%</span>
          </div>
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-[9px] text-gray-600">$0</span>
          <span className="text-[9px] text-amber-400/60 font-mono">{formatUSD(MONTHLY_GOAL)} target</span>
        </div>
      </div>

      <div className="card">
        <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider mb-4">Revenue Streams</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {STREAMS.map((s) => {
            const val = streams[s.key] ?? 0;
            return (
              <div
                key={s.key}
                className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.08] transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center font-bold text-sm ${s.color}`}>
                  {s.icon}
                </div>
                <div className="flex-1">
                  <div className="text-[11px] text-gray-300 font-medium">{s.label}</div>
                  <div className={`font-mono text-lg font-bold ${s.color}`}>{formatUSD(val)}</div>
                </div>
                <div className="text-[9px] text-gray-600">{monthlyRev > 0 ? ((val / monthlyRev) * 100).toFixed(0) : 0}%</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Recent Transactions</div>
          <span className="text-[9px] text-gray-500">{transactions.length} transactions</span>
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          {transactions.length === 0 ? (
            <div className="text-center py-8 text-gray-600 text-xs">No recent transactions</div>
          ) : (
            transactions.map((tx, i) => (
              <div
                key={tx.id || i}
                className="px-4 py-3 border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors cursor-pointer"
                onClick={() => setExpandedTx(expandedTx === i ? null : i)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
                      tx.type === "subscription" ? "bg-blue-400/10 text-blue-300" :
                      tx.type === "commission"   ? "bg-green-400/10 text-green-300" :
                      "bg-gray-400/10 text-gray-300"
                    }`}>{tx.type || "payment"}</span>
                    <span className="text-[11px] text-gray-300">{tx.description || tx.customer || "Transaction"}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm font-bold text-amber-400">{formatUSD(tx.amount)}</div>
                    <div className="text-[9px] text-gray-600">{tx.created_at ? timeAgo(tx.created_at) : "--"}</div>
                  </div>
                </div>
                {expandedTx === i && (
                  <div className="mt-2 pt-2 border-t border-white/[0.04] grid grid-cols-3 gap-2 text-[10px]">
                    <div><span className="text-gray-500">Source:</span> <span className="text-gray-300">{tx.source || "--"}</span></div>
                    <div><span className="text-gray-500">Status:</span> <span className="text-gray-300">{tx.status || "completed"}</span></div>
                    <div><span className="text-gray-500">ID:</span> <span className="text-gray-400 font-mono">{tx.id || "--"}</span></div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
