import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string;
  delta?: number;
  deltaLabel?: string;
  status?: "active" | "idle" | "alert" | "neutral";
  hint?: string;
  accent?: string;
  className?: string;
};

const STATUS_DOT = {
  active:  "bg-[var(--color-success)]",
  idle:    "bg-[var(--color-muted)]",
  alert:   "bg-[var(--color-alert)]",
  neutral: "bg-[var(--color-gold-500)]",
};

export function KPICard({
  label,
  value,
  delta,
  deltaLabel,
  status = "neutral",
  hint,
  accent,
  className,
}: Props) {
  const trendIcon =
    delta == null ? null
    : delta > 0 ? <TrendingUp size={12} />
    : delta < 0 ? <TrendingDown size={12} />
    : <Minus size={12} />;

  const trendColor =
    delta == null ? "text-[var(--color-muted)]"
    : delta > 0 ? "text-[var(--color-success)]"
    : delta < 0 ? "text-[var(--color-alert)]"
    : "text-[var(--color-muted)]";

  return (
    <div
      className={cn(
        "relative rounded-lg border bg-[var(--color-surface)] p-4 transition",
        "border-[var(--color-border)] hover:border-[var(--color-gold-700)]",
        className
      )}
      style={accent ? { borderTopColor: accent, borderTopWidth: 2 } : undefined}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">
          {label}
        </span>
        <span className={cn("h-2 w-2 rounded-full mt-0.5", STATUS_DOT[status])} />
      </div>
      <div className="font-mono text-2xl font-semibold tracking-tight" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      {(delta != null || deltaLabel) && (
        <div className={cn("mt-1.5 flex items-center gap-1 text-xs", trendColor)}>
          {trendIcon}
          {delta != null && <span>{delta > 0 ? "+" : ""}{delta.toFixed(1)}%</span>}
          {deltaLabel && <span className="text-[var(--color-muted)]">{deltaLabel}</span>}
        </div>
      )}
      {hint && <div className="mt-1 text-[11px] text-[var(--color-muted)]">{hint}</div>}
    </div>
  );
}
