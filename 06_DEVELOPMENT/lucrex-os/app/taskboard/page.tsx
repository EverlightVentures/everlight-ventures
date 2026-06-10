"use client";
import { ListChecks, ExternalLink, Clock, CheckCircle2, AlertCircle, Bot, User } from "lucide-react";
import { useApi } from "@/lib/api/client";

const DJANGO_BASE = process.env.NEXT_PUBLIC_DJANGO_BASE ?? "http://127.0.0.1:2200";

type TaskStats = {
  pending?: number;
  in_progress?: number;
  completed_today?: number;
  total_completed?: number;
  awaiting_retrieval?: number;
  ai_open?: number;
  human_open?: number;
};

function StatCard({
  label, value, accent, sub, icon: Icon,
}: {
  label: string;
  value: number;
  accent: string;
  sub?: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-1">
        <div className="text-[8px] uppercase tracking-widest text-gray-500">{label}</div>
        <Icon size={12} className={accent} />
      </div>
      <div className={`font-mono text-3xl font-bold ${accent}`}>{value ?? 0}</div>
      {sub && <div className="text-[9px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function TaskboardPage() {
  const { data, error } = useApi<TaskStats>("/api/django/proxy/taskboard/api/status/", 30_000);

  const pending = data?.pending ?? 0;
  const inProgress = data?.in_progress ?? 0;
  const completedToday = data?.completed_today ?? 0;
  const awaiting = data?.awaiting_retrieval ?? 0;
  const aiOpen = data?.ai_open ?? 0;
  const humanOpen = data?.human_open ?? 0;
  const totalCompleted = data?.total_completed ?? 0;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <ListChecks size={20} /> TASKBOARD
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            AI-to-human handoff nerve center, live counts from Django
          </p>
        </div>
        <a
          href={`${DJANGO_BASE}/taskboard/`}
          target="_blank"
          rel="noopener noreferrer"
          className="card flex items-center gap-2 hover:border-amber-400/40 transition"
        >
          <span className="text-[11px] text-amber-400 font-medium">Open in Django</span>
          <ExternalLink size={12} className="text-amber-400" />
        </a>
      </div>

      {error && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">API connection issue, counts may be stale</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{error}</div>
        </div>
      )}

      {/* Top: status grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Pending" value={pending} accent="text-amber-400" icon={Clock}
          sub={pending > 0 ? "needs attention" : "queue clear"} />
        <StatCard label="In Progress" value={inProgress} accent="text-amber-300" icon={Bot}
          sub="agents working" />
        <StatCard label="Completed Today" value={completedToday} accent="text-[#E8E8E8]" icon={CheckCircle2}
          sub={`${totalCompleted} all-time`} />
        <StatCard label="Awaiting Retrieval" value={awaiting} accent="text-amber-400/70" icon={AlertCircle}
          sub={awaiting > 0 ? "agents need to pull results" : "all clear"} />
      </div>

      {/* Open work split */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 flex items-center gap-2">
              <Bot size={14} className="text-amber-400" /> AI Execution Queue
            </h2>
            <span className="font-mono text-2xl font-bold text-amber-400">{aiOpen}</span>
          </div>
          <p className="text-[11px] text-gray-500">
            Tasks routed to agents for autonomous execution. Agents poll the
            Django board and pick up pending work in priority order.
          </p>
          <a
            href={`${DJANGO_BASE}/taskboard/?status=pending&owner_type=ai`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-[10px] text-amber-400 hover:underline"
          >
            View AI queue <ExternalLink size={10} />
          </a>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 flex items-center gap-2">
              <User size={14} className="text-amber-300" /> Human Input Needed
            </h2>
            <span className="font-mono text-2xl font-bold text-amber-300">{humanOpen}</span>
          </div>
          <p className="text-[11px] text-gray-500">
            Tasks that need a human, credential entry, approvals, decisions
            the agents cannot make alone.
          </p>
          <a
            href={`${DJANGO_BASE}/taskboard/?status=pending&request_kind=input`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-[10px] text-amber-300 hover:underline"
          >
            View human queue <ExternalLink size={10} />
          </a>
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 mb-2">
          Why a Read-Only View?
        </h2>
        <p className="text-[11px] text-gray-500 leading-relaxed">
          Task contents are encrypted Django-side, and the retrieval endpoint
          marks tasks as retrieved on access (one-time agent handoff). To avoid
          breaking the agent pipeline, Lucrex shows live counts only, click
          through to Django for full task editing, batch creation, and history.
        </p>
      </div>
    </div>
  );
}
