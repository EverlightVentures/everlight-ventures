import { ExternalLink } from "lucide-react";
import { EXTERNAL_TOOLS, type ExternalTool } from "@/lib/external-tools";
import { StatusBadge } from "./StatusBadge";

const STATUS_VARIANT: Record<ExternalTool["status"], "active" | "info" | "muted" | "warn"> = {
  live: "active",
  internal: "info",
  legacy: "muted",
  deprecated: "warn",
};

export function ExternalTools() {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center gap-2 mb-3">
        <ExternalLink size={16} className="text-[var(--color-gold-500)]" />
        <h2 className="font-display text-xl font-semibold">External tools and legacy dashboards</h2>
      </div>
      <p className="text-xs text-[var(--color-muted)] mb-4">
        Bridge to every other surface. Click out, come back.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {EXTERNAL_TOOLS.map((t) => (
          <a
            key={t.key}
            href={t.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group block rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-3 hover:border-[var(--color-gold-700)] hover:bg-[var(--color-elevated)] transition"
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <span className="font-medium text-sm">{t.label}</span>
              <ExternalLink
                size={12}
                className="text-[var(--color-muted)] group-hover:text-[var(--color-gold-400)] flex-shrink-0 mt-0.5"
              />
            </div>
            <div className="text-[11px] text-[var(--color-muted)] leading-relaxed mb-2 line-clamp-2">
              {t.blurb}
            </div>
            <StatusBadge variant={STATUS_VARIANT[t.status]}>{t.status}</StatusBadge>
          </a>
        ))}
      </div>
    </div>
  );
}
