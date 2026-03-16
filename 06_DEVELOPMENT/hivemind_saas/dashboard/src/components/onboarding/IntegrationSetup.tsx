"use client";

import React, { useState } from "react";
import {
  Check,
  Loader2,
  ChevronRight,
  Eye,
  EyeOff,
  ExternalLink,
  AlertCircle,
  Mail,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { IntegrationProvider, IntegrationStatus } from "@/types";

// ============================================================
// Provider definitions
// ============================================================
interface ProviderConfig {
  id: IntegrationProvider;
  name: string;
  description: string;
  icon: string;
  authType: "oauth" | "api_key";
  color: string;
  borderColor: string;
  category: "ai" | "productivity" | "communication" | "dev";
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: "anthropic",
    name: "Anthropic (Claude)",
    description: "Strategic analysis, writing, and reasoning",
    icon: "A",
    authType: "api_key",
    color: "rgba(245,158,11,0.1)",
    borderColor: "rgba(245,158,11,0.25)",
    category: "ai",
  },
  {
    id: "openai",
    name: "OpenAI (Codex)",
    description: "Code generation and automation workflows",
    icon: "O",
    authType: "api_key",
    color: "rgba(16,185,129,0.1)",
    borderColor: "rgba(16,185,129,0.25)",
    category: "ai",
  },
  {
    id: "google_ai",
    name: "Google (Gemini)",
    description: "Research, multimodal analysis, and search",
    icon: "G",
    authType: "api_key",
    color: "rgba(59,130,246,0.1)",
    borderColor: "rgba(59,130,246,0.25)",
    category: "ai",
  },
  {
    id: "perplexity",
    name: "Perplexity",
    description: "Real-time web research and citations",
    icon: "P",
    authType: "api_key",
    color: "rgba(124,58,237,0.1)",
    borderColor: "rgba(124,58,237,0.25)",
    category: "ai",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Post messages, read channels, trigger workflows",
    icon: "S",
    authType: "oauth",
    color: "rgba(74,21,75,0.2)",
    borderColor: "rgba(154,65,155,0.25)",
    category: "communication",
  },
  {
    id: "notion",
    name: "Notion",
    description: "Read and write pages, databases, and docs",
    icon: "N",
    authType: "oauth",
    color: "rgba(255,255,255,0.04)",
    borderColor: "rgba(255,255,255,0.1)",
    category: "productivity",
  },
  {
    id: "google_drive",
    name: "Google Drive",
    description: "Access files, sheets, and docs from Drive",
    icon: "D",
    authType: "oauth",
    color: "rgba(59,130,246,0.08)",
    borderColor: "rgba(59,130,246,0.2)",
    category: "productivity",
  },
  {
    id: "github",
    name: "GitHub",
    description: "Read repos, create PRs, manage issues",
    icon: "GH",
    authType: "oauth",
    color: "rgba(255,255,255,0.04)",
    borderColor: "rgba(255,255,255,0.1)",
    category: "dev",
  },
];

// ============================================================
// Types
// ============================================================
type IntegrationState = {
  status: IntegrationStatus;
  apiKey?: string;
  showKey?: boolean;
  error?: string;
};

interface IntegrationSetupProps {
  onComplete?: () => void;
  initialStep?: number;
  className?: string;
}

// ============================================================
// Step indicator
// ============================================================
const STEPS = [
  { id: 0, label: "Connect APIs" },
  { id: 1, label: "Project Folder" },
  { id: 2, label: "Notifications" },
];

function StepIndicator({ currentStep, completedSteps }: { currentStep: number; completedSteps: number[] }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => {
        const isCompleted = completedSteps.includes(step.id);
        const isActive = step.id === currentStep;
        const isLast = i === STEPS.length - 1;

        return (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-bold transition-all duration-300"
                style={{
                  background: isCompleted
                    ? "linear-gradient(135deg, #10B981 0%, #059669 100%)"
                    : isActive
                    ? "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)"
                    : "#16161F",
                  border: isCompleted
                    ? "1px solid rgba(16,185,129,0.4)"
                    : isActive
                    ? "1px solid rgba(124,58,237,0.4)"
                    : "1px solid #2A2A3E",
                  boxShadow: isActive ? "0 0 16px rgba(124,58,237,0.3)" : "none",
                  color: isCompleted || isActive ? "#F1F1F8" : "#5C5C7A",
                }}
              >
                {isCompleted ? <Check size={14} strokeWidth={2.5} /> : step.id + 1}
              </div>
              <span
                className={cn(
                  "text-[10px] font-medium mt-1.5 whitespace-nowrap",
                  isActive ? "text-violet-400" : isCompleted ? "text-emerald-400" : "text-[#5C5C7A]"
                )}
              >
                {step.label}
              </span>
            </div>
            {!isLast && (
              <div
                className="flex-1 h-px mx-3 mb-5 transition-all duration-500"
                style={{
                  background: completedSteps.includes(step.id)
                    ? "linear-gradient(90deg, #10B981 0%, #2A2A3E 100%)"
                    : "#2A2A3E",
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ============================================================
// Integration card
// ============================================================
function IntegrationCard({
  provider,
  state,
  onConnect,
  onApiKeyChange,
  onToggleKey,
}: {
  provider: ProviderConfig;
  state: IntegrationState;
  onConnect: (id: IntegrationProvider) => void;
  onApiKeyChange: (id: IntegrationProvider, key: string) => void;
  onToggleKey: (id: IntegrationProvider) => void;
}) {
  const isConnected = state.status === "connected";
  const isPending = state.status === "pending";

  return (
    <div
      className={cn(
        "rounded-xl p-4 transition-all duration-300",
        isConnected && "ring-1 ring-emerald-500/20"
      )}
      style={{
        background: isConnected
          ? "linear-gradient(135deg, rgba(16,185,129,0.06) 0%, #111118 100%)"
          : `linear-gradient(135deg, ${provider.color} 0%, #111118 100%)`,
        border: isConnected
          ? "1px solid rgba(16,185,129,0.2)"
          : `1px solid ${provider.borderColor}`,
        boxShadow: isConnected
          ? "0 0 16px rgba(16,185,129,0.08)"
          : "0 2px 8px rgba(0,0,0,0.3)",
      }}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-[13px] font-bold flex-shrink-0"
          style={{
            background: provider.color,
            border: `1px solid ${provider.borderColor}`,
            color: "#F1F1F8",
          }}
        >
          {provider.icon}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[13px] font-semibold text-[#F1F1F8]">{provider.name}</span>
            {isConnected && (
              <span className="badge badge-active text-[9px]">Connected</span>
            )}
          </div>
          <p className="text-[11.5px] text-[#5C5C7A] leading-snug">{provider.description}</p>
        </div>

        {/* Action */}
        <div className="flex-shrink-0">
          {isConnected ? (
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center"
              style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)" }}
            >
              <Check size={13} className="text-emerald-400" />
            </div>
          ) : (
            <button
              onClick={() => onConnect(provider.id)}
              disabled={isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11.5px] font-semibold transition-all disabled:opacity-60"
              style={{
                background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
                color: "#F1F1F8",
                border: "1px solid rgba(124,58,237,0.3)",
                boxShadow: "0 0 12px rgba(124,58,237,0.2)",
              }}
            >
              {isPending ? (
                <>
                  <Loader2 size={12} className="animate-spin" />
                  <span>Connecting</span>
                </>
              ) : provider.authType === "oauth" ? (
                <>
                  <ExternalLink size={11} />
                  <span>Authorize</span>
                </>
              ) : (
                <span>Enter Key</span>
              )}
            </button>
          )}
        </div>
      </div>

      {/* API key input (for api_key type) */}
      {provider.authType === "api_key" && !isConnected && (
        <div className="mt-3">
          <div className="relative">
            <input
              type={state.showKey ? "text" : "password"}
              placeholder={`Paste your ${provider.name} API key`}
              value={state.apiKey ?? ""}
              onChange={(e) => onApiKeyChange(provider.id, e.target.value)}
              className="input-dark pr-10 text-[12px] py-2"
              style={{ fontSize: "12px" }}
            />
            <button
              type="button"
              onClick={() => onToggleKey(provider.id)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5C5C7A] hover:text-[#A0A0B8] transition-colors"
            >
              {state.showKey ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          </div>
          {state.error && (
            <div className="flex items-center gap-1.5 mt-1.5">
              <AlertCircle size={11} className="text-red-400" />
              <span className="text-[11px] text-red-400">{state.error}</span>
            </div>
          )}
          {state.apiKey && state.apiKey.length > 8 && (
            <button
              onClick={() => onConnect(provider.id)}
              disabled={isPending}
              className="mt-2 w-full btn-primary py-2 text-[12px]"
            >
              {isPending ? (
                <>
                  <Loader2 size={12} className="animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <Check size={12} />
                  Save and Connect
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Step 2: Project folder
// ============================================================
function ProjectFolderStep({ onNext }: { onNext: () => void }) {
  const [driveConnected, setDriveConnected] = useState(false);
  const [manualPath, setManualPath] = useState("");
  const [connecting, setConnecting] = useState(false);

  const handleDriveConnect = () => {
    setConnecting(true);
    setTimeout(() => {
      setConnecting(false);
      setDriveConnected(true);
    }, 1800);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-[16px] font-semibold text-[#F1F1F8] mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Connect Your Project Folder
        </h3>
        <p className="text-[13px] text-[#5C5C7A]">
          The Hive reads your files to understand your business context and generate relevant output.
        </p>
      </div>

      {/* Google Drive option */}
      <div
        className="rounded-xl p-4"
        style={{
          background: driveConnected
            ? "linear-gradient(135deg, rgba(16,185,129,0.06) 0%, #111118 100%)"
            : "linear-gradient(135deg, rgba(59,130,246,0.06) 0%, #111118 100%)",
          border: driveConnected ? "1px solid rgba(16,185,129,0.2)" : "1px solid rgba(59,130,246,0.2)",
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-[13px] font-bold"
              style={{
                background: "rgba(59,130,246,0.1)",
                border: "1px solid rgba(59,130,246,0.2)",
                color: "#60A5FA",
              }}
            >
              D
            </div>
            <div>
              <p className="text-[13px] font-semibold text-[#F1F1F8]">Google Drive</p>
              <p className="text-[11.5px] text-[#5C5C7A]">
                {driveConnected ? "Connected -- My Drive" : "Browse and select project folders"}
              </p>
            </div>
          </div>
          {driveConnected ? (
            <span className="badge badge-active">Connected</span>
          ) : (
            <button
              onClick={handleDriveConnect}
              disabled={connecting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11.5px] font-semibold"
              style={{
                background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
                color: "#F1F1F8",
                border: "1px solid rgba(124,58,237,0.3)",
              }}
            >
              {connecting ? (
                <><Loader2 size={12} className="animate-spin" /> Connecting</>
              ) : (
                <><ExternalLink size={11} /> Open Drive Picker</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Manual path option */}
      <div className="relative flex items-center gap-3">
        <hr className="divider flex-1" />
        <span className="section-label flex-shrink-0">or enter path manually</span>
        <hr className="divider flex-1" />
      </div>

      <div>
        <label className="text-[12px] font-medium text-[#A0A0B8] mb-2 block">
          Project folder path
        </label>
        <input
          type="text"
          placeholder="/Users/you/Documents/MyProject"
          value={manualPath}
          onChange={(e) => setManualPath(e.target.value)}
          className="input-dark"
        />
        <p className="text-[11px] text-[#5C5C7A] mt-1.5">
          The Hive will index this folder and keep it in context for all sessions.
        </p>
      </div>

      <button
        onClick={onNext}
        disabled={!driveConnected && !manualPath}
        className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed mt-2"
      >
        Continue
        <ChevronRight size={15} />
      </button>
    </div>
  );
}

// ============================================================
// Step 3: Notifications
// ============================================================
function NotificationsStep({ onComplete }: { onComplete: () => void }) {
  const [slackChannel, setSlackChannel] = useState("#hive-updates");
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [emailAddress, setEmailAddress] = useState("");
  const [taskComplete, setTaskComplete] = useState(true);
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [dailyDigest, setDailyDigest] = useState(true);

  const ToggleSwitch = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => (
    <button
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
      style={{
        background: checked
          ? "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)"
          : "#2A2A3E",
        border: checked ? "1px solid rgba(124,58,237,0.4)" : "1px solid #3A3A52",
        boxShadow: checked ? "0 0 10px rgba(124,58,237,0.25)" : "none",
      }}
    >
      <span
        className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full transition-all duration-200"
        style={{
          background: "#F1F1F8",
          transform: checked ? "translateX(16px)" : "translateX(0)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
        }}
      />
    </button>
  );

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-[16px] font-semibold text-[#F1F1F8] mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
          Configure Notifications
        </h3>
        <p className="text-[13px] text-[#5C5C7A]">
          Choose how and where the Hive keeps you updated on task progress.
        </p>
      </div>

      {/* Slack */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare size={15} className="text-violet-400" />
          <span className="text-[13px] font-semibold text-[#F1F1F8]">Slack</span>
        </div>
        <div>
          <label className="text-[11.5px] font-medium text-[#A0A0B8] mb-1.5 block">
            Default channel
          </label>
          <input
            type="text"
            value={slackChannel}
            onChange={(e) => setSlackChannel(e.target.value)}
            placeholder="#hive-updates"
            className="input-dark text-[12px]"
          />
        </div>
      </div>

      {/* Email */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Mail size={15} className="text-violet-400" />
            <span className="text-[13px] font-semibold text-[#F1F1F8]">Email</span>
          </div>
          <ToggleSwitch checked={emailEnabled} onChange={() => setEmailEnabled((v) => !v)} />
        </div>
        {emailEnabled && (
          <input
            type="email"
            value={emailAddress}
            onChange={(e) => setEmailAddress(e.target.value)}
            placeholder="you@company.com"
            className="input-dark text-[12px]"
          />
        )}
      </div>

      {/* Notification preferences */}
      <div className="glass-card p-4 space-y-3">
        <span className="text-[12px] font-semibold text-[#A0A0B8] uppercase tracking-wider">
          Notify me when...
        </span>
        {[
          { label: "Task completes", value: taskComplete, set: setTaskComplete },
          { label: "Errors or failures only", value: errorsOnly, set: setErrorsOnly },
          { label: "Daily digest (9 AM)", value: dailyDigest, set: setDailyDigest },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-[13px] text-[#A0A0B8]">{item.label}</span>
            <ToggleSwitch checked={item.value} onChange={() => item.set((v: boolean) => !v)} />
          </div>
        ))}
      </div>

      <button onClick={onComplete} className="w-full btn-primary">
        <Check size={15} />
        Finish Setup
      </button>
    </div>
  );
}

// ============================================================
// Main IntegrationSetup Component
// ============================================================
export default function IntegrationSetup({ onComplete, initialStep = 0, className }: IntegrationSetupProps) {
  const [currentStep, setCurrentStep] = useState(initialStep);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [integrations, setIntegrations] = useState<Record<string, IntegrationState>>(
    Object.fromEntries(PROVIDERS.map((p) => [p.id, { status: "disconnected" as IntegrationStatus }]))
  );

  const completeStep = (step: number) => {
    setCompletedSteps((prev) => [...new Set([...prev, step])]);
    setCurrentStep(step + 1);
  };

  const handleConnect = (id: IntegrationProvider) => {
    const provider = PROVIDERS.find((p) => p.id === id);
    if (!provider) return;

    if (provider.authType === "api_key") {
      const key = integrations[id]?.apiKey ?? "";
      if (!key || key.length < 8) {
        setIntegrations((prev) => ({
          ...prev,
          [id]: { ...prev[id], error: "Please enter a valid API key (at least 8 characters)" },
        }));
        return;
      }
    }

    // Set pending state
    setIntegrations((prev) => ({
      ...prev,
      [id]: { ...prev[id], status: "pending", error: undefined },
    }));

    // Simulate OAuth/API verification
    setTimeout(() => {
      setIntegrations((prev) => ({
        ...prev,
        [id]: { ...prev[id], status: "connected" },
      }));
    }, 1500);
  };

  const handleApiKeyChange = (id: IntegrationProvider, key: string) => {
    setIntegrations((prev) => ({
      ...prev,
      [id]: { ...prev[id], apiKey: key, error: undefined },
    }));
  };

  const handleToggleKey = (id: IntegrationProvider) => {
    setIntegrations((prev) => ({
      ...prev,
      [id]: { ...prev[id], showKey: !prev[id]?.showKey },
    }));
  };

  const connectedCount = Object.values(integrations).filter((i) => i.status === "connected").length;
  const aiProviders = PROVIDERS.filter((p) => p.category === "ai");
  const productivityProviders = PROVIDERS.filter((p) => p.category !== "ai");

  return (
    <div
      className={cn("rounded-2xl p-6 max-w-2xl mx-auto", className)}
      style={{
        background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
        border: "1px solid #1E1E2E",
        boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
    >
      <StepIndicator currentStep={currentStep} completedSteps={completedSteps} />

      {/* Step 1: Connect APIs */}
      {currentStep === 0 && (
        <div className="space-y-4">
          <div>
            <h3 className="text-[16px] font-semibold text-[#F1F1F8] mb-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Connect Your APIs
            </h3>
            <p className="text-[13px] text-[#5C5C7A]">
              Link your AI services and productivity tools. The Hive coordinates them to handle your workflows.
            </p>
          </div>

          {connectedCount > 0 && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.15)" }}
            >
              <Check size={13} className="text-emerald-400" />
              <span className="text-[12px] text-emerald-400 font-medium">
                {connectedCount} of {PROVIDERS.length} integrations connected
              </span>
            </div>
          )}

          <div>
            <p className="section-label mb-3">AI Agents</p>
            <div className="space-y-2">
              {aiProviders.map((provider) => (
                <IntegrationCard
                  key={provider.id}
                  provider={provider}
                  state={integrations[provider.id] ?? { status: "disconnected" }}
                  onConnect={handleConnect}
                  onApiKeyChange={handleApiKeyChange}
                  onToggleKey={handleToggleKey}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="section-label mb-3">Productivity Tools</p>
            <div className="space-y-2">
              {productivityProviders.map((provider) => (
                <IntegrationCard
                  key={provider.id}
                  provider={provider}
                  state={integrations[provider.id] ?? { status: "disconnected" }}
                  onConnect={handleConnect}
                  onApiKeyChange={handleApiKeyChange}
                  onToggleKey={handleToggleKey}
                />
              ))}
            </div>
          </div>

          <button
            onClick={() => completeStep(0)}
            disabled={connectedCount === 0}
            className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            Continue
            <ChevronRight size={15} />
          </button>
          {connectedCount === 0 && (
            <button
              onClick={() => completeStep(0)}
              className="w-full text-[12px] text-[#5C5C7A] hover:text-[#A0A0B8] transition-colors"
            >
              Skip for now
            </button>
          )}
        </div>
      )}

      {/* Step 2: Project folder */}
      {currentStep === 1 && (
        <ProjectFolderStep onNext={() => completeStep(1)} />
      )}

      {/* Step 3: Notifications */}
      {currentStep === 2 && (
        <NotificationsStep onComplete={() => {
          completeStep(2);
          onComplete?.();
        }} />
      )}

      {/* Completion screen */}
      {currentStep >= 3 && (
        <div className="text-center py-8 space-y-4">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mx-auto"
            style={{
              background: "linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(16,185,129,0.05) 100%)",
              border: "1px solid rgba(16,185,129,0.3)",
              boxShadow: "0 0 24px rgba(16,185,129,0.2)",
            }}
          >
            <Check size={28} className="text-emerald-400" strokeWidth={2.5} />
          </div>
          <div>
            <h3 className="text-[18px] font-bold text-[#F1F1F8] mb-2" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              Hive is Ready
            </h3>
            <p className="text-[13px] text-[#5C5C7A]">
              Your AI agents are configured and connected. Head to the War Room to start your first session.
            </p>
          </div>
          <button
            onClick={onComplete}
            className="btn-primary mx-auto"
          >
            Launch War Room
            <ChevronRight size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
