"use client";
import type { Incident, SpaceWx } from "@/lib/types";
import { THREAT_RANK } from "@/lib/types";

const POSTURE_BG: Record<string, string> = {
  EXTREME: "#ff2d2d", HIGH: "#ff8c1a", MEDIUM: "#ffd21a", LOW: "#1a7f37", LOG: "#1a7f37",
};

export default function StatusBar({
  incidents, spacewx, county, live,
}: {
  incidents: Incident[];
  spacewx: SpaceWx | null;
  county: string;
  live: boolean;
}) {
  const top = incidents.reduce(
    (a, e) => (THREAT_RANK[e.threat_level] > THREAT_RANK[a] ? e.threat_level : a),
    "LOG"
  );
  const posture = top === "LOG" ? "GREEN" : top;
  return (
    <header
      className="glass"
      style={{
        position: "absolute", top: 12, left: 12, right: 12, height: 52, borderRadius: 14,
        display: "flex", alignItems: "center", gap: 16, padding: "0 18px", zIndex: 20,
      }}
    >
      <span className="display" style={{ color: "var(--gold)", fontSize: 18, fontWeight: 700 }}>
        Survival Console
      </span>
      <span className="pulse" style={{ color: "#2ecc71", fontSize: 11, fontWeight: 700 }}>
        &#9679; {live ? "LIVE" : "connecting"}
      </span>
      <span
        style={{
          background: POSTURE_BG[top], color: top === "MEDIUM" ? "#08080a" : "#fff",
          fontWeight: 700, fontSize: 12, padding: "3px 10px", borderRadius: 6,
        }}
      >
        {posture}
      </span>
      {county && <span style={{ color: "var(--muted)", fontSize: 12 }}>{county}</span>}
      {spacewx && (
        <span
          style={{
            fontSize: 11, padding: "2px 8px", borderRadius: 6,
            background: spacewx.alert ? "#4a0000" : "#143a1f",
            color: spacewx.alert ? "#ff6b6b" : "#8fe3a8",
          }}
        >
          Kp {spacewx.kp ?? "?"} &middot; {spacewx.gps}
        </span>
      )}
      <span style={{ marginLeft: "auto", color: "var(--muted)", fontSize: 12 }}>
        {incidents.length} incidents
      </span>
    </header>
  );
}
