import { cn } from "@/lib/utils";
import { humanStatus, statusColor } from "@/lib/utils";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-medium uppercase tracking-wide",
        statusColor(status)
      )}
    >
      {humanStatus(status)}
    </span>
  );
}
