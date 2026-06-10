import { cn } from "@/lib/utils";
import { relativeTime } from "@/lib/utils";

export type ActivityItem = {
  id: string;
  ts: string;
  agent: string;
  action: string;
  detail?: string;
  accent?: string;
};

export function ActivityFeed({ items, className }: { items: ActivityItem[]; className?: string }) {
  if (!items.length) {
    return (
      <div className={cn("text-sm text-[var(--color-muted)] italic", className)}>
        No activity yet.
      </div>
    );
  }

  return (
    <ul className={cn("space-y-3", className)}>
      {items.map((it) => (
        <li key={it.id} className="flex gap-3">
          <div
            className="mt-1.5 h-2 w-2 rounded-full flex-shrink-0"
            style={{ background: it.accent ?? "var(--color-gold-500)" }}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="font-medium text-sm">{it.agent}</span>
              <span className="text-xs text-[var(--color-muted)]">{relativeTime(it.ts)}</span>
            </div>
            <div className="text-sm text-[var(--color-fg)]">{it.action}</div>
            {it.detail && (
              <div className="text-xs text-[var(--color-muted)] mt-0.5">{it.detail}</div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
