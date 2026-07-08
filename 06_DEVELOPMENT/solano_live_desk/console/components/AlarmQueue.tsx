"use client";
import { motion } from "framer-motion";
import type { Incident } from "@/lib/types";
import { THREAT_COLORS, THREAT_RANK } from "@/lib/types";

export default function AlarmQueue({
  incidents, selectedId, onSelect, open, onToggle,
}: {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
  open: boolean;
  onToggle: () => void;
}) {
  const sorted = [...incidents].sort(
    (a, b) =>
      THREAT_RANK[b.threat_level] - THREAT_RANK[a.threat_level] ||
      (a.distance_mi ?? 9999) - (b.distance_mi ?? 9999)
  );
  if (!open) {
    return (
      <button
        onClick={onToggle}
        className="glass"
        style={{
          position: "absolute", top: 76, left: 12, zIndex: 16, borderRadius: 10,
          padding: "8px 11px", color: "var(--gold)", border: "1px solid var(--line)",
          cursor: "pointer", fontSize: 12, fontWeight: 600,
        }}
      >
        &#9654; Alarms ({incidents.length})
      </button>
    );
  }
  return (
    <aside
      className="glass scroll-thin"
      style={{
        position: "absolute", top: 76, left: 12, bottom: 12, width: 340, maxWidth: "85vw",
        borderRadius: 14, padding: 12, overflowY: "auto", zIndex: 15,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
        <span
          style={{
            fontSize: 11, color: "var(--muted)", textTransform: "uppercase",
            letterSpacing: 1, paddingLeft: 2,
          }}
        >
          Alarm queue
        </span>
        <button
          onClick={onToggle}
          title="collapse"
          style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 15 }}
        >
          &#9664;
        </button>
      </div>
      {sorted.map((ev, i) => (
        <motion.button
          key={ev.id}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: Math.min(i * 0.012, 0.25) }}
          onClick={() => onSelect(ev)}
          style={{
            display: "block", width: "100%", textAlign: "left",
            background: ev.id === selectedId ? "rgba(212,175,55,0.12)" : "transparent",
            border: "1px solid var(--line)", borderRadius: 10, padding: "8px 10px",
            marginBottom: 6, cursor: "pointer", color: "var(--text)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 8, height: 8, borderRadius: "50%",
                background: THREAT_COLORS[ev.threat_level] || "#888", flex: "0 0 auto",
              }}
            />
            <span
              style={{
                fontSize: 13, fontWeight: 600, overflow: "hidden",
                textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}
            >
              {ev.type || "Incident"}
            </span>
            {ev.status && (
              <span
                style={{
                  marginLeft: "auto", fontSize: 10,
                  color: ev.status === "LIVE" ? "#2ecc71" : "var(--muted)",
                }}
              >
                {ev.status}
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
            {ev.geo_label || ev.source}
            {ev.distance_mi != null ? ` · ${ev.distance_mi} mi` : ""}
          </div>
        </motion.button>
      ))}
    </aside>
  );
}
