// ============================================================
// Everlight Hive Mind -- Shared TypeScript Types
// ============================================================

// Agent types
export type AgentId = "claude" | "gemini" | "codex" | "perplexity";
export type AgentStatus = "active" | "idle" | "thinking" | "error" | "offline";

export interface Agent {
  id: AgentId;
  name: string;
  role: string;
  status: AgentStatus;
  currentTask: string | null;
  tokensUsed: number;
  tokensLimit: number;
  responseTime: number; // ms
  color: string;
  accentColor: string;
}

// KPI / Metric types
export type TrendDirection = "up" | "down" | "neutral";

export interface KpiMetric {
  id: string;
  label: string;
  value: string | number;
  previousValue?: string | number;
  change: number; // percentage
  trend: TrendDirection;
  prefix?: string;
  suffix?: string;
  description?: string;
  glowColor: "violet" | "gold" | "success" | "danger";
}

// Activity feed
export type ActivityType =
  | "agent_completed"
  | "integration_connected"
  | "workflow_triggered"
  | "trade_executed"
  | "document_generated"
  | "error"
  | "user_action";

export interface ActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  agentId?: AgentId;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

// Integration types
export type IntegrationProvider =
  | "slack"
  | "notion"
  | "google_drive"
  | "github"
  | "anthropic"
  | "openai"
  | "google_ai"
  | "perplexity"
  | "linear"
  | "jira"
  | "salesforce"
  | "hubspot";

export type IntegrationStatus = "connected" | "disconnected" | "pending" | "error";
export type IntegrationAuthType = "oauth" | "api_key" | "webhook";

export interface Integration {
  id: string;
  provider: IntegrationProvider;
  name: string;
  description: string;
  icon: string;
  status: IntegrationStatus;
  authType: IntegrationAuthType;
  connectedAt?: Date;
  lastSyncAt?: Date;
  scopes?: string[];
}

// Mindmap / Hive session graph
export type MindmapNodeType = "root" | "agent" | "action" | "result" | "error";

export interface MindmapNodeData {
  label: string;
  type: MindmapNodeType;
  agentId?: AgentId;
  content?: string;
  status?: "pending" | "running" | "done" | "failed";
  timestamp?: string;
  tokens?: number;
}

// Hive session
export interface HiveSession {
  id: string;
  prompt: string;
  status: "running" | "completed" | "failed" | "paused";
  startedAt: Date;
  completedAt?: Date;
  agentsInvolved: AgentId[];
  totalTokens: number;
  result?: string;
}

export interface HiveLogEntry {
  id: string;
  sessionId: string;
  agentId: AgentId;
  message: string;
  type: "input" | "output" | "tool_call" | "error" | "system";
  timestamp: Date;
  tokens?: number;
}

// Navigation
export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: string; // Lucide icon name
  badge?: string | number;
  group?: "main" | "tools" | "settings";
}

// User / Account
export type PlanTier = "starter" | "pro" | "team" | "enterprise";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  plan: PlanTier;
  company?: string;
  role: string;
}

// Onboarding
export type OnboardingStep = "connect_apis" | "connect_storage" | "configure_notifications" | "complete";

export interface OnboardingState {
  currentStep: OnboardingStep;
  completedSteps: OnboardingStep[];
  integrations: Partial<Record<IntegrationProvider, IntegrationStatus>>;
}

// Workflow
export type WorkflowTrigger = "schedule" | "webhook" | "manual" | "event";
export type WorkflowStatus = "active" | "paused" | "draft" | "error";

export interface Workflow {
  id: string;
  name: string;
  description: string;
  trigger: WorkflowTrigger;
  status: WorkflowStatus;
  lastRunAt?: Date;
  runCount: number;
  agentsUsed: AgentId[];
}
