"use client";
import { sourceMeta } from "@/lib/util";

export default function SourceBadge({ source }: { source?: string }) {
  const m = sourceMeta(source);
  return (
    <span
      title={`${m.tier} source`}
      style={{
        fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
        background: m.color + "22", color: m.color, border: `1px solid ${m.color}55`, whiteSpace: "nowrap",
      }}
    >
      {m.label} &middot; {m.tier}
    </span>
  );
}
