import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AgentId, AgentStatus, TrendDirection } from "@/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number, decimals = 0): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(decimals || 1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(decimals || 1)}k`;
  }
  return value.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

export function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function getTrendColor(trend: TrendDirection, inverted = false): string {
  if (trend === "neutral") return "text-[#A0A0B8]";
  const isPositive = inverted ? trend === "down" : trend === "up";
  return isPositive ? "text-emerald-400" : "text-red-400";
}

export function getTrendSign(change: number): string {
  if (change > 0) return "+";
  return "";
}

export function getAgentColor(agentId: AgentId): string {
  const colors: Record<AgentId, string> = {
    claude: "#F59E0B",
    gemini: "#3B82F6",
    codex: "#10B981",
    perplexity: "#7C3AED",
  };
  return colors[agentId] ?? "#A0A0B8";
}

export function getAgentGradient(agentId: AgentId): string {
  const gradients: Record<AgentId, string> = {
    claude: "from-amber-500/20 to-amber-900/5",
    gemini: "from-blue-500/20 to-blue-900/5",
    codex: "from-emerald-500/20 to-emerald-900/5",
    perplexity: "from-violet-500/20 to-violet-900/5",
  };
  return gradients[agentId] ?? "from-zinc-500/20 to-zinc-900/5";
}

export function getStatusBadgeClass(status: AgentStatus): string {
  const classes: Record<AgentStatus, string> = {
    active: "badge-active",
    thinking: "badge-thinking",
    idle: "badge-idle",
    error: "badge badge-warning",
    offline: "badge-idle",
  };
  return `badge ${classes[status] ?? "badge-idle"}`;
}

export function getStatusLabel(status: AgentStatus): string {
  const labels: Record<AgentStatus, string> = {
    active: "Active",
    thinking: "Thinking",
    idle: "Idle",
    error: "Error",
    offline: "Offline",
  };
  return labels[status] ?? "Unknown";
}

export function getPulseDotClass(status: AgentStatus): string {
  const classes: Record<AgentStatus, string> = {
    active: "pulse-dot pulse-dot-green",
    thinking: "pulse-dot pulse-dot-violet",
    idle: "pulse-dot pulse-dot-gray",
    error: "pulse-dot" ,
    offline: "pulse-dot pulse-dot-gray",
  };
  return classes[status] ?? "pulse-dot pulse-dot-gray";
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

export function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}
