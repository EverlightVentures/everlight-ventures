"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Swords,
  Send,
  Loader2,
  Cpu,
  Clock,
  ChevronDown,
  Zap,
  RotateCcw,
  StopCircle,
  ArrowLeft,
} from "lucide-react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import { cn, getAgentColor, getStatusBadgeClass, getStatusLabel, getPulseDotClass } from "@/lib/utils";
import type { Agent, AgentId, HiveLogEntry } from "@/types";

// ============================================================
// Mock data
// ============================================================
const AGENTS: Agent[] = [
  {
    id: "claude",
    name: "Claude",
    role: "Strategic Advisor",
    status: "active",
    currentTask: "Analyzing Q4 revenue trends and drafting executive narrative",
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
    currentTask: "Running competitive pricing analysis across 12 SaaS benchmarks",
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
    currentTask: "Writing Slack digest workflow script for #sales-updates",
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

const MOCK_LOG: HiveLogEntry[] = [
  {
    id: "l1",
    sessionId: "sess_01",
    agentId: "claude",
    message: "Session initialized. Reading context from Google Drive Q4_sales.xlsx...",
    type: "system",
    timestamp: new Date(Date.now() - 18 * 60 * 1000),
    tokens: 0,
  },
  {
    id: "l2",
    sessionId: "sess_01",
    agentId: "gemini",
    message: "Pulling market benchmarks for SaaS companies in $10M-$50M ARR range. Found 14 relevant comparables.",
    type: "output",
    timestamp: new Date(Date.now() - 16 * 60 * 1000),
    tokens: 2840,
  },
  {
    id: "l3",
    sessionId: "sess_01",
    agentId: "claude",
    message: "Identified 3 key growth levers from Q4 data: enterprise upsell (+34%), churn reduction (-12%), and new logo acquisition (+8%). Drafting narrative...",
    type: "output",
    timestamp: new Date(Date.now() - 14 * 60 * 1000),
    tokens: 4120,
  },
  {
    id: "l4",
    sessionId: "sess_01",
    agentId: "codex",
    message: "Tool call: write_file('Q4_Report_Draft.md') -- success. Formatting as branded PDF template.",
    type: "tool_call",
    timestamp: new Date(Date.now() - 11 * 60 * 1000),
    tokens: 890,
  },
  {
    id: "l5",
    sessionId: "sess_01",
    agentId: "gemini",
    message: "Competitive context appended: Competitors averaged 18% MoM growth. Everlight outperformed by 6.2 points.",
    type: "output",
    timestamp: new Date(Date.now() - 9 * 60 * 1000),
    tokens: 1760,
  },
  {
    id: "l6",
    sessionId: "sess_01",
    agentId: "claude",
    message: "Executive summary complete: 3 pages, 1,247 words. Key sections: Performance Highlights, Market Position, Q1 Outlook, Risk Factors.",
    type: "output",
    timestamp: new Date(Date.now() - 4 * 60 * 1000),
    tokens: 6200,
  },
];

// ============================================================
// Log type styling
// ============================================================
const LOG_TYPE_STYLE = {
  system: { color: "#5C5C7A", prefix: "SYS" },
  output: { color: "#A0A0B8", prefix: "OUT" },
  input: { color: "#7C3AED", prefix: "IN" },
  tool_call: { color: "#F59E0B", prefix: "TOOL" },
  error: { color: "#EF4444", prefix: "ERR" },
} as const;

// ============================================================
// Agent card component
// ============================================================
function AgentCard({ agent }: { agent: Agent }) {
  const color = getAgentColor(agent.id as AgentId);
  const pulseDotClass = getPulseDotClass(agent.status);
  const usagePct = Math.round((agent.tokensUsed / agent.tokensLimit) * 100);
  const isRunning = agent.status === "active" || agent.status === "thinking";

  return (
    <div
      className={cn(
        "rounded-2xl p-4 transition-all duration-300 flex flex-col gap-3",
        isRunning && "animate-glow-pulse"
      )}
      style={{
        background: `linear-gradient(135deg, ${color}08 0%, #111118 100%)`,
        border: `1px solid ${color}25`,
        boxShadow: isRunning
          ? `0 0 20px ${color}15, 0 4px 16px rgba(0,0,0,0.4)`
          : "0 4px 16px rgba(0,0,0,0.3)",
      }}
    >
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          {/* Agent color dot */}
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center text-[13px] font-bold flex-shrink-0"
            style={{
              background: `${color}18`,
              border: `1px solid ${color}30`,
              color,
            }}
          >
            {agent.name.charAt(0)}
          </div>
          <div>
            <p
              className="text-[14px] font-semibold leading-none"
              style={{ color: "#F1F1F8", fontFamily: "'DM Sans', sans-serif" }}
            >
              {agent.name}
            </p>
            <p className="text-[11px] text-[#5C5C7A] mt-0.5">{agent.role}</p>
          </div>
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-1.5">
          <span className={cn("flex-shrink-0", pulseDotClass)} />
          <span className={getStatusBadgeClass(agent.status)}>
            {getStatusLabel(agent.status)}
          </span>
        </div>
      </div>

      {/* Current task */}
      <div
        className="rounded-lg px-3 py-2.5 min-h-[52px] flex items-start"
        style={{
          background: "rgba(0,0,0,0.3)",
          border: "1px solid rgba(255,255,255,0.04)",
        }}
      >
        {agent.currentTask ? (
          <p className="text-[12px] text-[#A0A0B8] leading-snug">{agent.currentTask}</p>
        ) : (
          <p className="text-[12px] text-[#3A3A52] italic">Awaiting task...</p>
        )}
      </div>

      {/* Token usage */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-[#5C5C7A] flex items-center gap-1">
            <Cpu size={10} />
            Token usage
          </span>
          <span style={{ color }}>
            {(agent.tokensUsed / 1000).toFixed(1)}k / {(agent.tokensLimit / 1000).toFixed(0)}k
          </span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1E1E2E" }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${usagePct}%`,
              background: `linear-gradient(90deg, ${color}60 0%, ${color} 100%)`,
              boxShadow: `0 0 6px ${color}40`,
            }}
          />
        </div>
      </div>

      {/* Response time */}
      <div className="flex items-center justify-between text-[11px] text-[#5C5C7A]">
        <span className="flex items-center gap-1">
          <Clock size={10} />
          Avg response
        </span>
        <span className={isRunning ? "font-medium" : ""} style={{ color: isRunning ? color : "#5C5C7A" }}>
          {agent.responseTime}ms
        </span>
      </div>
    </div>
  );
}

// ============================================================
// Log entry row
// ============================================================
function LogEntry({ entry }: { entry: HiveLogEntry }) {
  const agentColor = getAgentColor(entry.agentId);
  const typeCfg = LOG_TYPE_STYLE[entry.type] ?? LOG_TYPE_STYLE.output;
  const timeStr = entry.timestamp.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <div
      className="flex gap-3 py-2.5 group hover:bg-white/[0.02] px-4 rounded-lg transition-colors"
      style={{ borderBottom: "1px solid rgba(30,30,46,0.4)" }}
    >
      {/* Time */}
      <span className="text-[10px] font-mono text-[#3A3A52] flex-shrink-0 mt-0.5 w-16">
        {timeStr}
      </span>

      {/* Agent dot */}
      <div
        className="w-4 h-4 rounded-full flex-shrink-0 mt-0.5 flex items-center justify-center text-[8px] font-bold"
        style={{
          background: `${agentColor}20`,
          border: `1px solid ${agentColor}40`,
          color: agentColor,
        }}
      >
        {entry.agentId.charAt(0).toUpperCase()}
      </div>

      {/* Type tag */}
      <span
        className="flex-shrink-0 text-[9px] font-bold uppercase px-1 py-0.5 rounded mt-0.5 h-fit"
        style={{
          background: `${typeCfg.color}15`,
          color: typeCfg.color,
          border: `1px solid ${typeCfg.color}25`,
        }}
      >
        {typeCfg.prefix}
      </span>

      {/* Message */}
      <p className="text-[12.5px] text-[#A0A0B8] leading-relaxed flex-1 font-mono">
        {entry.message}
      </p>

      {/* Tokens */}
      {entry.tokens && entry.tokens > 0 ? (
        <span className="flex-shrink-0 text-[10px] text-[#3A3A52] mt-0.5">
          {entry.tokens.toLocaleString()}t
        </span>
      ) : null}
    </div>
  );
}

// ============================================================
// Main War Room Page
// ============================================================
export default function WarRoomPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(true);
  const [logEntries, setLogEntries] = useState<HiveLogEntry[]>(MOCK_LOG);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logEntries]);

  const totalTokens = logEntries.reduce((sum, e) => sum + (e.tokens ?? 0), 0);
  const activeAgentCount = AGENTS.filter((a) => a.status === "active" || a.status === "thinking").length;

  const handleStartSession = () => {
    if (!prompt.trim()) return;
    setIsSubmitting(true);

    // Simulate session start
    setTimeout(() => {
      const newEntry: HiveLogEntry = {
        id: `l${Date.now()}`,
        sessionId: "sess_new",
        agentId: "claude",
        message: `New session started: "${prompt.trim()}"`,
        type: "system",
        timestamp: new Date(),
        tokens: 0,
      };
      setLogEntries((prev) => [...prev, newEntry]);
      setPrompt("");
      setIsSubmitting(false);
      setIsRunning(true);
    }, 1200);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleStartSession();
    }
  };

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
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#5C5C7A] hover:bg-white/[0.05] transition-colors"
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
            <Swords size={15} className="text-violet-400" />
          </div>
          <div>
            <h1
              className="text-[15px] font-semibold text-[#F1F1F8] leading-none"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              War Room
            </h1>
            <p className="text-[11px] text-[#5C5C7A] mt-0.5">
              {activeAgentCount} agents active -- live coordination view
            </p>
          </div>

          {/* Session stats */}
          <div
            className="ml-auto flex items-center gap-4 text-[11px] text-[#5C5C7A]"
            style={{ borderLeft: "1px solid #1E1E2E", paddingLeft: "16px" }}
          >
            <span className="flex items-center gap-1.5">
              <Cpu size={11} className="text-violet-400" />
              <span className="text-[#A0A0B8] font-medium">{(totalTokens / 1000).toFixed(1)}k</span> tokens
            </span>
            <span className="flex items-center gap-1.5">
              <span className="pulse-dot pulse-dot-green" style={{ width: 6, height: 6 }} />
              <span className={isRunning ? "text-emerald-400 font-medium" : "text-[#5C5C7A]"}>
                {isRunning ? "Session active" : "Idle"}
              </span>
            </span>
            {isRunning && (
              <button
                onClick={() => setIsRunning(false)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors border border-transparent hover:border-red-500/20"
              >
                <StopCircle size={12} />
                <span className="text-[11px] font-medium">Stop</span>
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-hidden flex flex-col">

          {/* 4-agent grid */}
          <div className="grid grid-cols-4 gap-3 p-4 flex-shrink-0">
            {AGENTS.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>

          {/* Lower section: session log + prompt input */}
          <div className="flex-1 flex flex-col overflow-hidden mx-4 mb-4 rounded-2xl"
            style={{
              background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
              border: "1px solid #1E1E2E",
              boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
            }}
          >
            {/* Log header */}
            <div
              className="flex items-center justify-between px-4 py-3 flex-shrink-0"
              style={{ borderBottom: "1px solid #1E1E2E" }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: "#10B981", boxShadow: "0 0 6px rgba(16,185,129,0.6)" }}
                />
                <span className="text-[13px] font-semibold text-[#F1F1F8]" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  Hive Session Log
                </span>
                <span className="badge badge-active text-[9px]">{logEntries.length} entries</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="flex items-center gap-1.5 text-[11px] text-[#5C5C7A] hover:text-[#A0A0B8] transition-colors"
                  onClick={() => setLogEntries([])}
                >
                  <RotateCcw size={11} />
                  Clear
                </button>
                <button className="flex items-center gap-1 text-[11px] text-[#5C5C7A] hover:text-[#A0A0B8] transition-colors">
                  <span>Export</span>
                  <ChevronDown size={11} />
                </button>
              </div>
            </div>

            {/* Log entries */}
            <div className="flex-1 overflow-y-auto py-2">
              {logEntries.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-12">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(124,58,237,0.08)", border: "1px solid rgba(124,58,237,0.15)" }}
                  >
                    <Zap size={20} className="text-violet-400" />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-[#A0A0B8]">No session running</p>
                    <p className="text-[12px] text-[#5C5C7A] mt-1">Start a session below to see live agent output</p>
                  </div>
                </div>
              ) : (
                logEntries.map((entry) => (
                  <LogEntry key={entry.id} entry={entry} />
                ))
              )}
              <div ref={logEndRef} />
            </div>

            {/* Prompt input */}
            <div
              className="p-3 flex-shrink-0"
              style={{ borderTop: "1px solid #1E1E2E" }}
            >
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe the task for the Hive... (Cmd+Enter to send)"
                  rows={2}
                  className="input-dark resize-none pr-24 py-3 text-[13px] leading-relaxed"
                  style={{ minHeight: "72px" }}
                />
                <div className="absolute right-3 bottom-3 flex items-center gap-2">
                  <span className="text-[10px] text-[#3A3A52] hidden sm:block">Cmd+Enter</span>
                  <button
                    onClick={handleStartSession}
                    disabled={!prompt.trim() || isSubmitting}
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center transition-all",
                      prompt.trim() && !isSubmitting
                        ? "bg-violet-600 hover:bg-violet-500 text-white shadow-[0_0_12px_rgba(124,58,237,0.4)]"
                        : "bg-[#1E1E2E] text-[#3A3A52] cursor-not-allowed"
                    )}
                  >
                    {isSubmitting ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Send size={14} />
                    )}
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-[#3A3A52] mt-1.5 px-1">
                All 4 agents will be assigned roles automatically based on the task type.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
