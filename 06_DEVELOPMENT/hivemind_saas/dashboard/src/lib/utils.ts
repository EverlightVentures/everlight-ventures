import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AgentId, AgentStatus } from "@/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
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

