"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

/** Silently re-fetches server components every N seconds.
 *  Shows a small "updating" chip during the refresh + a "just refreshed" flash. */
export function AutoRefresh({
  intervalSeconds = 45,
  label = "live",
}: {
  intervalSeconds?: number;
  label?: string;
}) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "loading" | "flash">("idle");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    let id: ReturnType<typeof setInterval>;
    const tick = async () => {
      if (document.hidden) return;
      setState("loading");
      try {
        router.refresh();
      } finally {
        // small optimistic delay so the spinner is visible
        setTimeout(() => {
          setState("flash");
          setLastRefresh(new Date());
          setTimeout(() => setState("idle"), 1200);
        }, 400);
      }
    };
    id = setInterval(tick, intervalSeconds * 1000);
    return () => clearInterval(id);
  }, [router, intervalSeconds]);

  return (
    <div className="inline-flex items-center gap-2 text-[11px] text-fog">
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full transition-colors",
          state === "loading" ? "bg-warning animate-pulse" :
          state === "flash" ? "bg-success" :
          "bg-gold/70"
        )}
      />
      <span className="tracking-[0.3em] uppercase">
        {state === "loading" ? "refreshing" : state === "flash" ? "updated" : label}
      </span>
      {lastRefresh && state === "idle" && (
        <span className="text-smoke">
          {Math.round((Date.now() - lastRefresh.getTime()) / 1000)}s ago
        </span>
      )}
    </div>
  );
}
