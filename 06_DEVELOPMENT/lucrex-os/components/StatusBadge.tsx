import { cn } from "@/lib/utils";

type Variant = "active" | "pending" | "closed" | "alert" | "warn" | "info" | "muted";

const STYLES: Record<Variant, string> = {
  active:  "bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/30",
  pending: "bg-[var(--color-warn)]/10 text-[var(--color-warn)] border-[var(--color-warn)]/30",
  closed:  "bg-[var(--color-muted)]/10 text-[var(--color-muted)] border-[var(--color-faint)]/30",
  alert:   "bg-[var(--color-alert)]/10 text-[var(--color-alert)] border-[var(--color-alert)]/30",
  warn:    "bg-[var(--color-warn)]/10 text-[var(--color-warn)] border-[var(--color-warn)]/30",
  info:    "bg-[var(--color-ops)]/10 text-[var(--color-ops)] border-[var(--color-ops)]/30",
  muted:   "bg-[var(--color-elevated)] text-[var(--color-muted)] border-[var(--color-border)]",
};

export function StatusBadge({
  variant = "muted",
  children,
  className,
}: {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider font-medium border",
        STYLES[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
