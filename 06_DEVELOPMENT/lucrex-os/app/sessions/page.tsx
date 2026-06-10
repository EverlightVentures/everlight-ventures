"use client";
import { useState } from "react";
import Link from "next/link";
import { Network, ExternalLink, FileText, MessageSquare, Database, Globe, FileJson, Filter } from "lucide-react";
import { useApi } from "@/lib/api/client";

type Artifact = {
  id: number;
  kind: string;
  agent: string;
  title: string;
  url: string;
  path: string;
  tags: string[];
  created_at: string;
  session_id: string | null;
};

type ArtifactSearch = { ok: boolean; count: number; results: Artifact[] };

const KIND_META: Record<string, { color: string; bg: string; icon: React.ComponentType<{ size?: number; className?: string }>; label: string }> = {
  gdoc:        { color: "text-amber-400",    bg: "bg-amber-400/15",      icon: FileText,      label: "Google Doc" },
  html:        { color: "text-amber-300",    bg: "bg-amber-400/10",      icon: Globe,         label: "HTML Report" },
  slack_post:  { color: "text-[#E8E8E8]",    bg: "bg-white/[0.04]",      icon: MessageSquare, label: "Slack Post" },
  blinko_note: { color: "text-amber-200/80", bg: "bg-amber-400/[0.06]",  icon: FileJson,      label: "Blinko Note" },
  supabase_row:{ color: "text-amber-400/70", bg: "bg-amber-400/[0.06]",  icon: Database,      label: "Supabase Row" },
  file:        { color: "text-gray-400",     bg: "bg-white/[0.03]",      icon: FileText,      label: "File" },
};

function kindMeta(k: string) {
  return KIND_META[k] ?? { color: "text-gray-400", bg: "bg-white/[0.03]", icon: FileText, label: k };
}

function relTime(iso: string): string {
  if (!iso) return "--";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

export default function HiveSessionsPage() {
  const [kind, setKind] = useState<string>("");
  const qs = new URLSearchParams({ since_days: "14", limit: "100" });
  if (kind) qs.set("kind", kind);
  const { data, error } = useApi<ArtifactSearch>(
    `/api/django/proxy/hive/api/artifacts/search/?${qs.toString()}`,
    60_000
  );

  const artifacts = data?.results ?? [];
  const byAgent: Record<string, number> = {};
  const byKind: Record<string, number> = {};
  for (const a of artifacts) {
    byAgent[a.agent] = (byAgent[a.agent] ?? 0) + 1;
    byKind[a.kind] = (byKind[a.kind] ?? 0) + 1;
  }
  const topAgents = Object.entries(byAgent).sort(([, a], [, b]) => b - a).slice(0, 5);

  const kindFilters = ["", "gdoc", "html", "slack_post", "blinko_note", "supabase_row"];

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <Network size={20} /> HIVE SESSIONS
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Last 14 days of artifacts produced by the Hive, {artifacts.length} items
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : "bg-green-400 pulse-live"}`} />
          <span className="text-[9px] text-gray-500 font-mono">60s refresh</span>
        </div>
      </div>

      {error && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">Django unreachable, showing nothing</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{error}</div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Artifacts (14d)</div>
          <div className="font-mono text-2xl font-bold text-amber-400">{artifacts.length}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Distinct Agents</div>
          <div className="font-mono text-2xl font-bold text-amber-300">{Object.keys(byAgent).length}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Reports (HTML)</div>
          <div className="font-mono text-2xl font-bold text-[#E8E8E8]">{byKind.html ?? 0}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Slack Posts</div>
          <div className="font-mono text-2xl font-bold text-amber-200/80">{byKind.slack_post ?? 0}</div>
        </div>
      </div>

      {/* Top agents */}
      {topAgents.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80 mb-3">Top Agents</h2>
          <div className="flex flex-wrap gap-2">
            {topAgents.map(([agent, count]) => (
              <span key={agent} className="px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-[11px]">
                <span className="text-gray-300">{agent}</span>
                <span className="ml-2 font-mono text-amber-400/80">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Kind filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={12} className="text-gray-500" />
        {kindFilters.map((k) => (
          <button
            key={k || "all"}
            onClick={() => setKind(k)}
            className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-wider border transition ${
              kind === k
                ? "bg-amber-400/15 border-amber-400/40 text-amber-300"
                : "bg-white/[0.02] border-white/[0.06] text-gray-500 hover:text-gray-300"
            }`}
          >
            {k || "all"}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Artifact Stream</h2>
        </div>
        <div className="divide-y divide-white/[0.03]">
          {artifacts.length === 0 && !error && (
            <div className="text-center py-8 text-gray-500 text-sm">
              {data ? "No artifacts in window" : "Loading..."}
            </div>
          )}
          {artifacts.map((a) => {
            const meta = kindMeta(a.kind);
            const Icon = meta.icon;
            return (
              <div key={a.id} className="px-4 py-3 hover:bg-white/[0.02] transition flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg ${meta.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon size={14} className={meta.color} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-semibold ${meta.bg} ${meta.color}`}>
                      {a.kind}
                    </span>
                    <span className="text-[10px] text-gray-500">{a.agent || "unknown"}</span>
                    <span className="text-[10px] text-gray-600">{relTime(a.created_at)}</span>
                  </div>
                  <div className="text-[12px] text-gray-200 mt-0.5 truncate">{a.title || "(untitled)"}</div>
                  {a.tags?.length > 0 && (
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {a.tags.slice(0, 4).map((t) => (
                        <span key={t} className="text-[9px] text-gray-600">#{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {a.session_id && (
                    <Link
                      href={`/sessions/${a.session_id}`}
                      className="px-2 py-1 rounded text-[10px] text-amber-400 hover:bg-amber-400/10 transition"
                    >
                      session
                    </Link>
                  )}
                  {a.url && (
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1 rounded text-[10px] text-amber-300 hover:bg-amber-400/10 transition flex items-center gap-1"
                    >
                      open <ExternalLink size={9} />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
