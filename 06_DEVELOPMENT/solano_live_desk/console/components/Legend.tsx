"use client";
import { useState } from "react";

const THREAT: [string, string][] = [
  ["#ff2d2d", "EXTREME"], ["#ff8c1a", "HIGH"], ["#ffd21a", "MEDIUM"], ["#D4AF37", "LOW"],
];
const SYMBOLS: [string, string][] = [
  ["!", "incident (# = newest)"], ["◆", "fused / correlated"],
  ["\u{1F525}", "fire"], ["\u{1F6A8}", "crime"], ["\u{1F697}", "traffic / medical"],
  ["▲", "aircraft"], ["\u{1F686}", "train"], ["\u{1F68C}", "bus"],
  ["\u{1F3E5}", "safe haven"], ["\u{1F4F7}", "camera"], ["\u{1F4E1}", "mesh node"],
  ["\u{1F525}", "social hotspot"],
];

export default function Legend() {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="glass"
        style={{ position: "absolute", bottom: 118, left: 12, zIndex: 16, borderRadius: 8, padding: "5px 9px", color: "var(--gold)", border: "1px solid var(--line)", fontSize: 11, cursor: "pointer" }}
      >
        Legend
      </button>
    );
  }
  return (
    <div
      className="glass scroll-thin"
      style={{ position: "absolute", bottom: 118, left: 12, zIndex: 16, borderRadius: 10, padding: "8px 10px", maxHeight: "46vh", overflowY: "auto", width: 184 }}
    >
      <div style={{ display: "flex", alignItems: "center", marginBottom: 5 }}>
        <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)" }}>Legend</span>
        <button onClick={() => setOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text)", cursor: "pointer", fontSize: 14 }}>&times;</button>
      </div>
      <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 3 }}>THREAT</div>
      {THREAT.map(([c, l]) => (
        <div key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, marginBottom: 2 }}>
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: c, flex: "0 0 auto" }} />
          {l}
        </div>
      ))}
      <div style={{ fontSize: 10, color: "var(--muted)", margin: "6px 0 3px" }}>MARKERS</div>
      {SYMBOLS.map(([s, l], i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, marginBottom: 2 }}>
          <span style={{ width: 15, textAlign: "center", flex: "0 0 auto" }}>{s}</span>
          {l}
        </div>
      ))}
      <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 5 }}>Older incidents fade over ~6h.</div>
    </div>
  );
}
