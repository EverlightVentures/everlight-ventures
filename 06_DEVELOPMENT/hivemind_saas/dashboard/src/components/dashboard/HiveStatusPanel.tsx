"use client";

import React, { useState, useEffect } from "react";
import { Zap, Clock, ChevronRight, Activity } from "lucide-react";
import { cn, getAgentColor, getStatusLabel, getPulseDotClass, formatRelativeTime } from "@/lib/utils";
import type { Agent, AgentId, AgentStatus } from "@/types";

// ============================================================
// Mock data -- replace with real API calls
// ============================================================
const MOCK_AGENTS: Agent[] = [
  {
    id: "claude",
    name: "Claude",
    role: "Strategic Advisor",
    status: "active",
    currentTask: "Drafting Q4 investor report from Google Drive data",
    tokensUsed: 14820,
    tokensLimit: 100000,
    responseTime: 1240,
    color: "#F59E0B",
    accentColor: "#FCD34D",
  },
  {
    id: "gemini",
    name: "Gemini",
    role: "Research Engine",
    status: "thinking",
    currentTask: "Analyzing competitor pricing across 12 SaaS products",
    tokensUsed: 8430,
    tokensLimit: 100000,
    responseTime: 980,
    color: "#3B82F6",
    accentColor: "#60A5FA",
  },
  {
    id: "codex",
    name: "Codex",
    role: "Automation Builder",
    status: "active",
    currentTask: "Writing Slack digest workflow for #sales-updates",
    tokensUsed: 5200,
    tokensLimit: 100000,
    responseTime: 760,
    color: "#10B981",
    accentColor: "#34D399",
  },
  {
    id: "perplexity",
    name: "Perplexity",
    role: "Live Researcher",
    status: "idle",
    currentTask: null,
    tokensUsed: 2100,
    tokensLimit: 100000,
    responseTime: 1820,
    color: "#7C3AED",
    accentColor: "#A78BFA",
  },
];

// ============================================================
// Types
// ============================================================
interface HiveStatusPanelProps {
  agents?: Agent[];
  className?: string;
}

// ============================================================
// Agent row sub-component
// ============================================================
function AgentRow({ agent }: { agent: Agent }) {
  const color = getAgentColor(agent.id as AgentId);
  const statusLabel = getStatusLabel(agent.status as AgentStatus);
  const pulseDotClass = getPulseDotClass(agent.status as AgentStatus);
  const usagePct = Math.round((agent.tokensUsed / agent.tokensLimit) * 100);

  return (
    <div
      className="group flex items-start gap-3 p-3 rounded-xl transition-all duration-200 hover:bg-white/[0.03] cursor-default"
      style={{ borderBottom: "1px solid rgba(30,30,46,0.6)" }}
    >
      {/* Agent color indicator */}
      <div className="flex flex-col items-center gap-1.5 pt-0.5">
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}80` }}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[13px] font-semibold text-[#F1F1F8]">{agent.name}</span>
          <span className="text-[10px] text-[#5C5C7A] font-medium">{agent.role}</span>

          <div className="ml-auto flex items-center gap-1.5">
            <span className={cn("flex-shrink-0", pulseDotClass)} />
            <span
              className={cn(
                "text-[10px] font-semibold uppercase tracking-wide",
                agent.status === "active" && "text-emerald-400",
                agent.status === "thinking" && "text-violet-400",
                agent.status === "idle" && "text-[#5C5C7A]",
                agent.status === "error" && "text-red-400"
              )}
            >
              {statusLabel}
            </span>
          </div>
        </div>

        {agent.currentTask ? (
          <p className="text-[12px] text-[#A0A0B8] leading-snug mb-2 truncate">
            {agent.currentTask}
          </p>
        ) : (
          <p className="text-[12px] text-[#3A3A52] italic mb-2">Waiting for task...</p>
        )}

        {/* Token usage bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1 bg-[#1E1E2E] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${usagePct}%`,
                background: `linear-gradient(90deg, ${color}80 0%, ${color} 100%)`,
                boxShadow: `0 0 6px ${color}40`,
              }}
            />
          </div>
          <span className="text-[10px] text-[#5C5C7A] flex-shrink-0">
            {(agent.tokensUsed / 1000).toFixed(1)}k tokens
          </span>
          {agent.status !== "idle" && (
            <span className="flex items-center gap-0.5 text-[10px] text-[#5C5C7A] flex-shrink-0">
              <Clock size={9} />
              {agent.responseTime}ms
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Main HiveStatusPanel Component
// ============================================================
export default function HiveStatusPanel({ agents = MOCK_AGENTS, className }: HiveStatusPanelProps) {
  const [sessionTime, setSessionTime] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);

  const activeCount = agents.filter((a) => a.status === "active" || a.status === "thinking").length;

  useEffect(() => {
    setTotalTokens(agents.reduce((sum, a) => sum + a.tokensUsed, 0));

    // Simulated session timer
    const interval = setInterval(() => {
      setSessionTime((t) => t + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [agents]);

  const formatDuration = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div
      className={cn("rounded-2xl overflow-hidden", className)}
      style={{
        background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
        border: "1px solid #1E1E2E",
        boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-[#1E1E2E]">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{
              background: activeCount > 0
                ? "linear-gradient(135deg, rgba(124,58,237,0.2) 0%, rgba(124,58,237,0.08) 100%)"
                : "rgba(30,30,46,0.6)",
              border: activeCount > 0 ? "1px solid rgba(124,58,237,0.25)" : "1px solid #1E1E2E",
            }}
          >
            <Activity
              size={14}
              className={activeCount > 0 ? "text-violet-400" : "text-[#5C5C7A]"}
            />
          </div>
          <div>
            <h3
              className="text-[13px] font-semibold text-[#F1F1F8] leading-none"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Active Hive
            </h3>
            <p className="text-[10.5px] text-[#5C5C7A] mt-0.5">
              {activeCount} of {agents.length} agents running
            </p>
          </div>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-3">
          {activeCount > 0 && (
            <div className="flex items-center gap-1.5 text-[11px] text-[#5C5C7A]">
              <Zap size={11} className="text-violet-400" />
              <span className="font-mono">{formatDuration(sessionTime)}</span>
            </div>
          )}
          <div className="text-[11px] text-[#5C5C7A]">
            <span className="text-[#A0A0B8] font-medium">{(totalTokens / 1000).toFixed(1)}k</span>
            <span className="ml-1">tokens</span>
          </div>
          <button className="flex items-center gap-1 text-[11px] text-[#5C5C7A] hover:text-violet-400 transition-colors">
            <span>View all</span>
            <ChevronRight size={12} />
          </button>
        </div>
      </div>

      {/* Agent list */}
      <div className="divide-y divide-[#1E1E2E]/40">
        {agents.map((agent) => (
          <AgentRow key={agent.id} agent={agent} />
        ))}
      </div>

      {/* Footer status strip */}
      {activeCount > 0 && (
        <div
          className="px-4 py-2.5 flex items-center gap-2"
          style={{
            background: "linear-gradient(90deg, rgba(124,58,237,0.06) 0%, transparent 100%)",
            borderTop: "1px solid rgba(124,58,237,0.1)",
          }}
        >
          <span className="pulse-dot pulse-dot-violet" style={{ width: 6, height: 6 }} />
          <span className="text-[11px] text-violet-400 font-medium">
            Hive session active
          </span>
          <span className="text-[11px] text-[#5C5C7A] ml-auto">
            Last activity {formatRelativeTime(new Date(Date.now() - 12000))}
          </span>
        </div>
      )}
    </div>
  );
}
