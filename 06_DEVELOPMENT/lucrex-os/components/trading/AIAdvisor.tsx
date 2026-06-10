import { Brain, Eye, AlertTriangle, Sparkles } from "lucide-react";
import type { BotSnapshot } from "@/lib/api/xlm-bot";
import { StatusBadge } from "../StatusBadge";

type Props = { snap: BotSnapshot };

export function AIAdvisor({ snap }: Props) {
  // Snapshot may have rich AI fields we want to surface:
  const foresight = (snap as unknown as { foresight?: { summary?: string } }).foresight;
  const trap = snap.trap_analysis as { warning?: string; conviction?: string } | null;
  const narrative = snap.unified_narrative;
  const recommendation = snap.unified_recommendation;
  const tier = (snap as unknown as { unified_tier?: string }).unified_tier;
  const eyeballRaw = (snap as unknown as { unified_eyeball?: unknown }).unified_eyeball;
  const eyeball = typeof eyeballRaw === "string" ? eyeballRaw : null;

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-bg)] p-5 relative overflow-hidden">
      <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-[var(--color-gold-500)]/5 blur-3xl pointer-events-none" />

      <div className="flex items-center justify-between mb-4 flex-wrap gap-2 relative">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-[var(--color-gold-500)]/10 border border-[var(--color-gold-700)]/30 flex items-center justify-center">
            <Brain size={16} className="text-[var(--color-gold-500)]" />
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold leading-tight">Lucrex Advisor</h2>
            <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">
              executive AI mode
            </div>
          </div>
        </div>
        {recommendation && (
          <StatusBadge variant={recommendation === "ENTER" ? "active" : recommendation === "WAIT" ? "warn" : "info"}>
            {recommendation}
            {snap.unified_direction && ` ${snap.unified_direction}`}
          </StatusBadge>
        )}
      </div>

      {/* Primary thought */}
      <div className="relative mb-4">
        <div className="absolute -left-1 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[var(--color-gold-500)] to-transparent rounded-full" />
        <div className="pl-3">
          <div className="text-[10px] uppercase tracking-widest text-[var(--color-gold-500)] mb-1 flex items-center gap-1.5">
            <Sparkles size={10} /> Thought
          </div>
          <p className="text-sm text-[var(--color-fg)] leading-relaxed">
            {snap.thought || "(no thought)"}
          </p>
        </div>
      </div>

      {/* Narrative + foresight */}
      {(narrative || foresight?.summary) && (
        <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {narrative && (
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-1 flex items-center gap-1.5">
                <Brain size={10} /> Narrative
              </div>
              <p className="text-xs text-[var(--color-muted)] leading-relaxed">{narrative}</p>
            </div>
          )}
          {foresight?.summary && (
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-1 flex items-center gap-1.5">
                <Eye size={10} /> Foresight
              </div>
              <p className="text-xs text-[var(--color-muted)] leading-relaxed">{foresight.summary}</p>
            </div>
          )}
        </div>
      )}

      {/* Trap warning */}
      {trap?.warning && (
        <div className="rounded-md border border-[var(--color-alert)]/30 bg-[var(--color-alert)]/5 p-3 flex items-start gap-2">
          <AlertTriangle size={14} className="text-[var(--color-alert)] flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-[10px] uppercase tracking-widest text-[var(--color-alert)] mb-0.5">
              Trap analysis
            </div>
            <p className="text-xs text-[var(--color-fg)]">{trap.warning}</p>
            {trap.conviction && (
              <span className="text-[10px] text-[var(--color-muted)] mt-1 inline-block">
                conviction: {trap.conviction}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Score / eyeball footer */}
      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-[var(--color-border)] text-[10px] font-mono text-[var(--color-muted)]">
        {tier && <span>Tier: <span className="text-[var(--color-gold-400)]">{tier}</span></span>}
        {snap.unified_p_win != null && <span>P(win): <span className="text-[var(--color-gold-400)]">{(snap.unified_p_win * 100).toFixed(0)}%</span></span>}
        {snap.unified_rr_ratio != null && <span>R:R: <span className="text-[var(--color-gold-400)]">{snap.unified_rr_ratio.toFixed(1)}</span></span>}
        {eyeball && <span className="ml-auto italic">{eyeball}</span>}
      </div>
    </div>
  );
}
