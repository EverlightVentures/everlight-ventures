"use client";
import { useEffect, useState } from "react";
import { daysUntil } from "@/lib/utils";

const TCJA_SUNSET = "2026-12-31T00:00:00Z";

export function CountdownClock({ targetIso = TCJA_SUNSET, label = "TCJA Sunset" }: { targetIso?: string; label?: string }) {
  const [days, setDays] = useState<number | null>(null);

  useEffect(() => {
    setDays(daysUntil(targetIso));
    const id = setInterval(() => setDays(daysUntil(targetIso)), 60_000);
    return () => clearInterval(id);
  }, [targetIso]);

  if (days === null) return null;

  const urgency =
    days < 90 ? "text-[var(--color-alert)]"
    : days < 270 ? "text-[var(--color-warn)]"
    : "text-[var(--color-muted)]";

  return (
    <span className={`font-mono ${urgency}`}>
      {label}: <span className="font-semibold">{days}d</span>
    </span>
  );
}
