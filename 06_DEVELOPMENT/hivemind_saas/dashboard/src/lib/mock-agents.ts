import type { Agent } from "@/types";

/**
 * Shared mock agent data used across dashboard components.
 * Replace with real API data when the backend is live.
 */
export const MOCK_AGENTS: Agent[] = [
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
