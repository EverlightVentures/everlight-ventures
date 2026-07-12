"use client";
import { useEffect, useRef, useState } from "react";
import { postReport, postPresence } from "@/lib/api";

// Warn other drivers (not the police). Reckless markers decay fast; hazards linger.
const RECKLESS = [
  { kind: "reckless_shoulder", label: "Shoulder driving", icon: "\u{1F6D1}" },
  { kind: "reckless_weaving", label: "Weaving / swerving", icon: "\u{2194}\u{FE0F}" },
  { kind: "reckless_wrongway", label: "Wrong-way driver", icon: "\u{26A0}\u{FE0F}" },
  { kind: "reckless_tailgating", label: "Aggressive tailgating", icon: "\u{1F697}" },
  { kind: "reckless_racing", label: "Street racing", icon: "\u{1F3C1}" },
];
const HAZARDS = [
  { kind: "hazard_object", label: "Object on road", icon: "\u{1F4E6}" },
  { kind: "hazard_pothole", label: "Pothole", icon: "\u{1F573}\u{FE0F}" },
  { kind: "hazard_flood", label: "Flooded road", icon: "\u{1F30A}" },
];

function clientId(): string {
  try {
    let id = localStorage.getItem("aroundme_client");
    if (!id) { id = "c" + Math.random().toString(36).slice(2, 10); localStorage.setItem("aroundme_client", id); }
    return id;
  } catch { return "anon"; }
}

const btn: React.CSSProperties = {
  border: "1px solid #2a2820", borderRadius: 10, padding: "9px 13px", fontSize: 13,
  fontWeight: 700, cursor: "pointer", boxShadow: "0 3px 14px rgba(0,0,0,0.5)",
};

export default function ReportPanel({ pos }: { pos: { lat: number; lon: number } | null }) {
  const [sheet, setSheet] = useState(false);
  const [onDelivery, setOnDelivery] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const posRef = useRef(pos);
  useEffect(() => { posRef.current = pos; }, [pos]);

  // Keep the "on delivery" marker fresh while working; it auto-expires if we stop.
  useEffect(() => {
    if (!onDelivery) return;
    const id = clientId();
    const push = () => { const p = posRef.current; if (p) postPresence(id, p.lat, p.lon, true); };
    push();
    const iv = setInterval(push, 60000);
    return () => {
      clearInterval(iv);
      const p = posRef.current;
      postPresence(id, p?.lat ?? 0, p?.lon ?? 0, false); // clear the marker when they stop
    };
  }, [onDelivery]);

  const flash = (m: string) => { setToast(m); setTimeout(() => setToast(null), 2500); };
  const report = (kind: string, label: string) => {
    const p = posRef.current;
    if (!p) { flash("No GPS fix yet"); return; }
    postReport(kind, p.lat, p.lon);
    setSheet(false);
    flash("Reported: " + label);
  };

  return (
    <>
      <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", bottom: 150, zIndex: 27, display: "flex", gap: 8 }}>
        <button onClick={() => setSheet(true)} style={{ ...btn, background: "rgba(120,20,20,0.92)", color: "#ffd7d7" }}>
          {"\u{26A0}\u{FE0F}"} Report
        </button>
        <button
          onClick={() => setOnDelivery((v) => !v)}
          title="Show others you are a delivery driver, not a prowler"
          style={{ ...btn, background: onDelivery ? "rgba(20,50,80,0.95)" : "rgba(10,10,10,0.85)", color: onDelivery ? "#7fd1ff" : "#968f80", border: `1px solid ${onDelivery ? "#7fd1ff" : "#2a2820"}` }}
        >
          {"\u{1F69A}"} {onDelivery ? "On delivery" : "Mark delivery"}
        </button>
      </div>

      {toast && (
        <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", bottom: 200, zIndex: 28, background: "rgba(10,10,10,0.92)", color: "#e8e8e8", padding: "7px 14px", borderRadius: 9, fontSize: 12, fontWeight: 600, boxShadow: "0 4px 18px rgba(0,0,0,0.6)" }}>
          {toast}
        </div>
      )}

      {sheet && (
        <div onClick={() => setSheet(false)} style={{ position: "fixed", inset: 0, zIndex: 55, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "#111", border: "1px solid #2a2820", borderRadius: "16px 16px 0 0", padding: "18px 18px 28px", width: "100%", maxWidth: 460, boxShadow: "0 -6px 30px rgba(0,0,0,0.6)" }}>
            <div style={{ color: "#e8e8e8", fontSize: 15, fontWeight: 800, marginBottom: 12 }}>What did you see?</div>
            <div style={{ color: "#ff9b9b", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 6 }}>Reckless driver</div>
            <div style={{ display: "grid", gap: 6, marginBottom: 14 }}>
              {RECKLESS.map((r) => (
                <button key={r.kind} onClick={() => report(r.kind, r.label)} style={{ ...btn, background: "rgba(120,20,20,0.35)", color: "#ffd7d7", textAlign: "left", border: "1px solid #4a2020" }}>
                  {r.icon}  {r.label}
                </button>
              ))}
            </div>
            <div style={{ color: "#ffcf8f", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.6, marginBottom: 6 }}>Road hazard</div>
            <div style={{ display: "grid", gap: 6, marginBottom: 14 }}>
              {HAZARDS.map((r) => (
                <button key={r.kind} onClick={() => report(r.kind, r.label)} style={{ ...btn, background: "rgba(120,80,20,0.3)", color: "#ffe0b0", textAlign: "left", border: "1px solid #4a3820" }}>
                  {r.icon}  {r.label}
                </button>
              ))}
            </div>
            <button onClick={() => setSheet(false)} style={{ ...btn, background: "transparent", color: "#968f80", width: "100%", border: "1px solid #2a2820" }}>Cancel</button>
            <div style={{ fontSize: 9, color: "#6a655a", marginTop: 10, textAlign: "center" }}>Reports warn other drivers, not law enforcement. They fade automatically.</div>
          </div>
        </div>
      )}
    </>
  );
}
