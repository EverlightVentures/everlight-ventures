"use client";

import React, { useState } from "react";
import { GitBranch, ChevronDown, Clock, Cpu, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import ConversationMindmap from "@/components/mindmap/ConversationMindmap";
import { cn } from "@/lib/utils";
import type { HiveSession, AgentId } from "@/types";

// ============================================================
// Mock session list
// ============================================================
const MOCK_SESSIONS: HiveSession[] = [
  {
    id: "sess_01",
    prompt: "Generate Q4 Investor Report from Drive data",
    status: "running",
    startedAt: new Date(Date.now() - 18 * 60 * 1000),
    agentsInvolved: ["claude", "gemini", "codex"],
    totalTokens: 30550,
  },
  {
    id: "sess_02",
    prompt: "Analyze Slack threads and draft product update",
    status: "completed",
    startedAt: new Date(Date.now() - 3 * 60 * 60 * 1000),
    completedAt: new Date(Date.now() - 2.5 * 60 * 60 * 1000),
    agentsInvolved: ["claude", "gemini"],
    totalTokens: 18200,
    result: "Product update posted to #leadership",
  },
  {
    id: "sess_03",
    prompt: "Competitor pricing analysis across 12 SaaS tools",
    status: "completed",
    startedAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
    completedAt: new Date(Date.now() - 5.5 * 60 * 60 * 1000),
    agentsInvolved: ["gemini", "perplexity"],
    totalTokens: 24800,
    result: "Analysis saved to Google Drive",
  },
  {
    id: "sess_04",
    prompt: "Build automated daily standup workflow for Slack",
    status: "completed",
    startedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
    completedAt: new Date(Date.now() - 11.8 * 60 * 60 * 1000),
    agentsInvolved: ["codex"],
    totalTokens: 8100,
    result: "Workflow deployed and active",
  },
];

const AGENT_COLORS: Record<AgentId, string> = {
  claude: "#F59E0B",
  gemini: "#3B82F6",
  codex: "#10B981",
  perplexity: "#7C3AED",
};

const AGENT_LABELS: Record<AgentId, string> = {
  claude: "Claude",
  gemini: "Gemini",
  codex: "Codex",
  perplexity: "Perplexity",
};

// ============================================================
// Session selector item
// ============================================================
function SessionItem({
  session,
  isSelected,
  onClick,
}: {
  session: HiveSession;
  isSelected: boolean;
  onClick: () => void;
}) {
  const duration = session.completedAt
    ? Math.round((session.completedAt.getTime() - session.startedAt.getTime()) / 60000)
    : Math.round((Date.now() - session.startedAt.getTime()) / 60000);

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-3 rounded-xl transition-all duration-200 group",
        isSelected
          ? "ring-1 ring-violet-500/30"
          : "hover:bg-white/[0.03]"
      )}
      style={{
        background: isSelected
          ? "linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(124,58,237,0.04) 100%)"
          : "transparent",
        border: isSelected
          ? "1px solid rgba(124,58,237,0.2)"
          : "1px solid transparent",
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-[12.5px] font-medium text-[#F1F1F8] line-clamp-2 leading-snug flex-1">
          {session.prompt}
        </p>
        <span
          className={cn(
            "flex-shrink-0 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded",
            session.status === "running" && "text-violet-400 bg-violet-500/10 border border-violet-500/20",
            session.status === "completed" && "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20",
            session.status === "failed" && "text-red-400 bg-red-500/10 border border-red-500/20"
          )}
        >
          {session.status}
        </span>
      </div>

      <div className="flex items-center gap-3 text-[10.5px] text-[#5C5C7A]">
        <span className="flex items-center gap-1">
          <Clock size={9} />
          {duration}m
        </span>
        <span className="flex items-center gap-1">
          <Cpu size={9} />
          {(session.totalTokens / 1000).toFixed(1)}k tokens
        </span>
        <div className="flex items-center gap-0.5 ml-auto">
          {session.agentsInvolved.map((agentId) => (
            <div
              key={agentId}
              title={AGENT_LABELS[agentId]}
              className="w-3 h-3 rounded-full border border-void"
              style={{ backgroundColor: AGENT_COLORS[agentId], boxShadow: `0 0 3px ${AGENT_COLORS[agentId]}60` }}
            />
          ))}
        </div>
      </div>
    </button>
  );
}

// ============================================================
// Main Mindmap Page
// ============================================================
export default function MindmapPage() {
  const router = useRouter();
  const [selectedSessionId, setSelectedSessionId] = useState(MOCK_SESSIONS[0].id);

  const selectedSession = MOCK_SESSIONS.find((s) => s.id === selectedSessionId) ?? MOCK_SESSIONS[0];

  return (
    <div className="flex min-h-screen bg-void">
      <Sidebar />

      <div className="flex-1 flex flex-col" style={{ marginLeft: "260px" }}>
        {/* Header */}
        <header
          className="sticky top-0 z-30 flex items-center gap-3 px-6"
          style={{
            height: "64px",
            background: "rgba(10,10,15,0.85)",
            borderBottom: "1px solid #1E1E2E",
            backdropFilter: "blur(12px)",
          }}
        >
          <button
            onClick={() => router.back()}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#5C5C7A] hover:bg-white/[0.05] hover:text-[#A0A0B8] transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "rgba(124,58,237,0.12)",
              border: "1px solid rgba(124,58,237,0.2)",
            }}
          >
            <GitBranch size={15} className="text-violet-400" />
          </div>
          <div>
            <h1
              className="text-[15px] font-semibold text-[#F1F1F8] leading-none"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Hive Mindmap
            </h1>
            <p className="text-[11px] text-[#5C5C7A] mt-0.5">
              Visualize agent reasoning and task graphs
            </p>
          </div>

          {/* Session selector dropdown (simple) */}
          <div className="ml-auto">
            <button
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-[12px] text-[#A0A0B8] transition-colors hover:bg-white/[0.04]"
              style={{ border: "1px solid #1E1E2E" }}
            >
              <span className="pulse-dot pulse-dot-violet" style={{ width: 6, height: 6 }} />
              <span className="font-medium">{selectedSession.prompt.slice(0, 30)}...</span>
              <ChevronDown size={13} className="text-[#5C5C7A]" />
            </button>
          </div>
        </header>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">

          {/* Session sidebar */}
          <aside
            className="flex-shrink-0 overflow-y-auto"
            style={{
              width: "280px",
              background: "#0E0E16",
              borderRight: "1px solid #1E1E2E",
            }}
          >
            <div className="p-3">
              <p className="section-label mb-3 px-1">Recent Sessions</p>
              <div className="space-y-1">
                {MOCK_SESSIONS.map((session) => (
                  <SessionItem
                    key={session.id}
                    session={session}
                    isSelected={session.id === selectedSessionId}
                    onClick={() => setSelectedSessionId(session.id)}
                  />
                ))}
              </div>
            </div>
          </aside>

          {/* Mindmap canvas */}
          <main className="flex-1 p-4 overflow-hidden">
            <ConversationMindmap
              sessionTitle={selectedSession.prompt}
              className="h-full"
            />
          </main>
        </div>
      </div>
    </div>
  );
}
