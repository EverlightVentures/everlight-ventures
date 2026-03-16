"use client";

import React from "react";
import Link from "next/link";
import {
  Bell,
  Search,
  Settings,
  Users,
  CheckCircle2,
  TrendingUp,
  DollarSign,
  ArrowUpRight,
  Clock,
  Zap,
  FileText,
  GitMerge,
  AlertCircle,
} from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import KpiCard from "@/components/dashboard/KpiCard";
import HiveStatusPanel from "@/components/dashboard/HiveStatusPanel";
import { formatRelativeTime } from "@/lib/utils";
import type { KpiMetric, ActivityItem } from "@/types";

// ============================================================
// Mock data
// ============================================================
const KPI_DATA: KpiMetric[] = [
  {
    id: "sessions",
    label: "Sessions Today",
    value: 47,
    previousValue: 38,
    change: 23.7,
    trend: "up",
    description: "vs. yesterday",
    glowColor: "violet",
  },
  {
    id: "tasks",
    label: "Tasks Completed",
    value: 184,
    previousValue: 201,
    change: -8.5,
    trend: "down",
    description: "across all agents",
    glowColor: "gold",
  },
  {
    id: "agents",
    label: "Active Agents",
    value: 3,
    previousValue: 2,
    change: 50.0,
    trend: "up",
    description: "of 4 available",
    glowColor: "success",
  },
  {
    id: "revenue",
    label: "Revenue This Month",
    value: 18420,
    previousValue: 15900,
    change: 15.8,
    trend: "up",
    prefix: "$",
    description: "MRR growing",
    glowColor: "gold",
  },
];

const ACTIVITY_ITEMS: ActivityItem[] = [
  {
    id: "a1",
    type: "agent_completed",
    title: "Claude completed report draft",
    description: "Q4 Investor Summary -- 3 pages, 1,200 words",
    agentId: "claude",
    timestamp: new Date(Date.now() - 4 * 60 * 1000),
  },
  {
    id: "a2",
    type: "integration_connected",
    title: "Notion workspace connected",
    description: "12 databases indexed, 847 pages scanned",
    timestamp: new Date(Date.now() - 18 * 60 * 1000),
  },
  {
    id: "a3",
    type: "workflow_triggered",
    title: "Daily digest workflow triggered",
    description: "Summarizing 43 Slack threads from #product",
    agentId: "gemini",
    timestamp: new Date(Date.now() - 35 * 60 * 1000),
  },
  {
    id: "a4",
    type: "document_generated",
    title: "Codex built Slack automation",
    description: "New workflow: auto-post standup summaries to #leadership",
    agentId: "codex",
    timestamp: new Date(Date.now() - 62 * 60 * 1000),
  },
  {
    id: "a5",
    type: "error",
    title: "GitHub API rate limit reached",
    description: "Perplexity repo scan paused -- retrying in 15 minutes",
    timestamp: new Date(Date.now() - 78 * 60 * 1000),
  },
  {
    id: "a6",
    type: "agent_completed",
    title: "Gemini finished competitor analysis",
    description: "12 SaaS products benchmarked, report saved to Drive",
    agentId: "gemini",
    timestamp: new Date(Date.now() - 2.5 * 60 * 60 * 1000),
  },
];

const AGENT_COLORS: Record<string, string> = {
  claude: "#F59E0B",
  gemini: "#3B82F6",
  codex: "#10B981",
  perplexity: "#7C3AED",
};

const ACTIVITY_ICONS: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  agent_completed: CheckCircle2,
  integration_connected: GitMerge,
  workflow_triggered: Zap,
  document_generated: FileText,
  error: AlertCircle,
  user_action: Users,
  trade_executed: TrendingUp,
};

// ============================================================
// Header component
// ============================================================
function Header() {
  return (
    <header
      className="fixed top-0 right-0 z-30 flex items-center gap-3 px-6"
      style={{
        left: "260px",
        height: "64px",
        background: "rgba(10,10,15,0.85)",
        borderBottom: "1px solid #1E1E2E",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      {/* Search */}
      <div className="flex-1 max-w-md relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C5C7A]"
        />
        <input
          type="text"
          placeholder="Search tasks, sessions, documents..."
          className="input-dark pl-9 h-9 text-[13px]"
        />
      </div>

      <div className="flex items-center gap-1 ml-auto">
        {/* Notification bell */}
        <button
          className="relative w-9 h-9 rounded-xl flex items-center justify-center text-[#5C5C7A] hover:bg-white/[0.05] hover:text-[#A0A0B8] transition-colors"
          aria-label="Notifications"
        >
          <Bell size={17} strokeWidth={1.8} />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{
              background: "#7C3AED",
              boxShadow: "0 0 6px rgba(124,58,237,0.7)",
            }}
          />
        </button>

        {/* Settings */}
        <Link
          href="/settings"
          className="w-9 h-9 rounded-xl flex items-center justify-center text-[#5C5C7A] hover:bg-white/[0.05] hover:text-[#A0A0B8] transition-colors"
          aria-label="Settings"
        >
          <Settings size={17} strokeWidth={1.8} />
        </Link>

        {/* Status indicator */}
        <div
          className="flex items-center gap-2 ml-2 pl-3"
          style={{ borderLeft: "1px solid #1E1E2E" }}
        >
          <span className="pulse-dot pulse-dot-green" style={{ width: 6, height: 6 }} />
          <span className="text-[12px] text-[#A0A0B8] font-medium hidden sm:block">
            Hive Active
          </span>
        </div>
      </div>
    </header>
  );
}

// ============================================================
// Activity feed item
// ============================================================
function ActivityRow({ item }: { item: ActivityItem }) {
  const IconComponent = ACTIVITY_ICONS[item.type] ?? CheckCircle2;
  const agentColor = item.agentId ? AGENT_COLORS[item.agentId] : null;
  const isError = item.type === "error";

  return (
    <div className="flex items-start gap-3 py-3 group" style={{ borderBottom: "1px solid rgba(30,30,46,0.5)" }}>
      {/* Icon */}
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{
          background: isError
            ? "rgba(239,68,68,0.1)"
            : agentColor
            ? `${agentColor}18`
            : "rgba(124,58,237,0.1)",
          border: isError
            ? "1px solid rgba(239,68,68,0.2)"
            : agentColor
            ? `1px solid ${agentColor}30`
            : "1px solid rgba(124,58,237,0.2)",
        }}
      >
        <IconComponent
          size={13}
          className={isError ? "text-red-400" : undefined}
          style={{ color: isError ? undefined : agentColor ?? "#A78BFA" }}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-[#F1F1F8] leading-snug">{item.title}</p>
        <p className="text-[11.5px] text-[#5C5C7A] mt-0.5 truncate">{item.description}</p>
      </div>

      {/* Time */}
      <div className="flex-shrink-0 flex items-center gap-1 text-[#3A3A52]">
        <Clock size={10} />
        <span className="text-[10.5px] font-medium">{formatRelativeTime(item.timestamp)}</span>
      </div>
    </div>
  );
}

// ============================================================
// KPI icon map
// ============================================================
const KPI_ICONS: Record<string, React.ReactNode> = {
  sessions: <TrendingUp size={17} strokeWidth={2} />,
  tasks: <CheckCircle2 size={17} strokeWidth={2} />,
  agents: <Users size={17} strokeWidth={2} />,
  revenue: <DollarSign size={17} strokeWidth={2} />,
};

// ============================================================
// Main Dashboard Page
// ============================================================
export default function DashboardPage() {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex min-h-screen bg-void">
      <Sidebar />

      {/* Main area */}
      <div
        className="flex-1 flex flex-col"
        style={{ marginLeft: "260px" }}
      >
        <Header />

        {/* Content */}
        <main
          className="flex-1 overflow-auto"
          style={{ paddingTop: "64px" }}
        >
          <div className="px-6 py-6 max-w-[1440px]">

            {/* Page header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1
                  className="text-[22px] font-bold text-[#F1F1F8] leading-none"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                >
                  Command Center
                </h1>
                <p className="text-[13px] text-[#5C5C7A] mt-1.5">{today}</p>
              </div>
              <Link
                href="/war-room"
                className="btn-primary"
              >
                <Zap size={14} />
                Start Hive Session
                <ArrowUpRight size={13} />
              </Link>
            </div>

            {/* KPI grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {KPI_DATA.map((metric, i) => (
                <KpiCard
                  key={metric.id}
                  metric={metric}
                  icon={KPI_ICONS[metric.id]}
                  animate
                  className={`animation-delay-${i * 100}`}
                />
              ))}
            </div>

            {/* Lower grid: Activity + Hive Status */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

              {/* Activity feed -- 3 cols */}
              <div
                className="lg:col-span-3 rounded-2xl overflow-hidden"
                style={{
                  background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
                  border: "1px solid #1E1E2E",
                  boxShadow: "0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)",
                }}
              >
                {/* Feed header */}
                <div
                  className="flex items-center justify-between px-4 py-3.5"
                  style={{ borderBottom: "1px solid #1E1E2E" }}
                >
                  <h2
                    className="text-[13px] font-semibold text-[#F1F1F8]"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    Recent Activity
                  </h2>
                  <button className="text-[12px] text-[#5C5C7A] hover:text-violet-400 transition-colors flex items-center gap-1">
                    View all
                    <ArrowUpRight size={12} />
                  </button>
                </div>

                {/* Feed list */}
                <div className="px-4 overflow-y-auto" style={{ maxHeight: "420px" }}>
                  {ACTIVITY_ITEMS.map((item) => (
                    <ActivityRow key={item.id} item={item} />
                  ))}
                </div>
              </div>

              {/* Hive status -- 2 cols */}
              <div className="lg:col-span-2">
                <HiveStatusPanel />
              </div>
            </div>

            {/* Quick actions strip */}
            <div className="grid grid-cols-3 gap-3 mt-4">
              {[
                {
                  href: "/mindmap",
                  label: "View Mindmap",
                  sub: "Last session 12m ago",
                  color: "#7C3AED",
                  icon: <GitMerge size={18} strokeWidth={1.8} />,
                },
                {
                  href: "/integrations",
                  label: "Add Integration",
                  sub: "3 pending setup",
                  color: "#F59E0B",
                  icon: <Zap size={18} strokeWidth={1.8} />,
                },
                {
                  href: "/workflows",
                  label: "Build Workflow",
                  sub: "7 active automations",
                  color: "#10B981",
                  icon: <Settings size={18} strokeWidth={1.8} />,
                },
              ].map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-3 p-4 rounded-xl group transition-all hover:-translate-y-0.5"
                  style={{
                    background: "#111118",
                    border: "1px solid #1E1E2E",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                  }}
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                      background: `${action.color}15`,
                      border: `1px solid ${action.color}25`,
                      color: action.color,
                    }}
                  >
                    {action.icon}
                  </div>
                  <div>
                    <p className="text-[13px] font-semibold text-[#F1F1F8] group-hover:text-violet-300 transition-colors">
                      {action.label}
                    </p>
                    <p className="text-[11px] text-[#5C5C7A]">{action.sub}</p>
                  </div>
                  <ArrowUpRight
                    size={14}
                    className="ml-auto text-[#3A3A52] group-hover:text-violet-400 transition-colors"
                  />
                </Link>
              ))}
            </div>

          </div>
        </main>
      </div>
    </div>
  );
}
