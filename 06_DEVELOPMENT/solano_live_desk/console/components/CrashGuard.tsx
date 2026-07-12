"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { sendSos } from "@/lib/api";

// Crash detection (Life360's flagship, rebuilt on free web sensors). A real crash
// is a brief, hard spike -- far above hard braking (~0.7g). We watch the phone's
// gravity-excluded acceleration and, on a spike, start a countdown the driver can
// cancel; if not, we fire the SOS. Foreground only in a browser (native app gets
// a background sensor) -- still useful with AroundMe open on a windshield mount.
const CRASH_MS2 = 29; // ~3g: a hard impact, not a pothole. Tunable.
const REARM_MS = 8000; // one crash = one trigger
const COUNTDOWN_S = 12;

type Phase = "idle" | "countdown" | "sent";

export default function CrashGuard({ pos }: { pos: { lat: number; lon: number } | null }) {
  const [armed, setArmed] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [count, setCount] = useState(COUNTDOWN_S);
  const [result, setResult] = useState<{ ok?: boolean; maps?: string; label?: string } | null>(null);
  const lastTrigger = useRef(0);
  const posRef = useRef(pos);
  useEffect(() => { posRef.current = pos; }, [pos]);

  const fire = useCallback(async (kind: "crash" | "manual") => {
    const p = posRef.current;
    let res: any = { ok: false, label: kind === "crash" ? "CRASH DETECTED" : "SOS" };
    if (p) res = await sendSos(p.lat, p.lon, kind);
    setResult(res);
    setPhase("sent");
  }, []);

  const trigger = useCallback((kind: "crash" | "manual") => {
    lastTrigger.current = Date.now();
    if (kind === "manual") { fire("manual"); return; }
    setCount(COUNTDOWN_S);
    setPhase("countdown");
  }, [fire]);

  // Accelerometer watch while armed.
  useEffect(() => {
    if (!armed) return;
    const onMotion = (e: DeviceMotionEvent) => {
      const a = e.acceleration;
      let mag: number;
      if (a && (a.x != null || a.y != null || a.z != null)) {
        mag = Math.hypot(a.x || 0, a.y || 0, a.z || 0); // gravity already excluded
      } else {
        const b = e.accelerationIncludingGravity;
        if (!b) return;
        mag = Math.abs(Math.hypot(b.x || 0, b.y || 0, b.z || 0) - 9.81);
      }
      if (mag >= CRASH_MS2 && Date.now() - lastTrigger.current > REARM_MS && phase === "idle") {
        trigger("crash");
      }
    };
    window.addEventListener("devicemotion", onMotion);
    return () => window.removeEventListener("devicemotion", onMotion);
  }, [armed, phase, trigger]);

  // Countdown -> auto-send.
  useEffect(() => {
    if (phase !== "countdown") return;
    if (count <= 0) { fire("crash"); return; }
    const id = setTimeout(() => setCount((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [phase, count, fire]);

  const arm = useCallback(async () => {
    // iOS 13+ requires an explicit motion-permission grant from a user gesture.
    const D: any = typeof DeviceMotionEvent !== "undefined" ? DeviceMotionEvent : null;
    if (D && typeof D.requestPermission === "function") {
      try {
        const p = await D.requestPermission();
        if (p !== "granted") return;
      } catch { return; }
    }
    setArmed(true);
  }, []);

  const dismiss = () => { setPhase("idle"); setCount(COUNTDOWN_S); setResult(null); };

  return (
    <>
      {/* arm toggle + manual SOS, bottom-right */}
      <div style={{ position: "absolute", right: 12, bottom: 96, zIndex: 27, display: "flex", gap: 6, alignItems: "center" }}>
        {armed && (
          <button
            onClick={() => trigger("manual")}
            style={{ background: "#c0392b", color: "#fff", border: "none", borderRadius: 10, padding: "8px 12px", fontWeight: 800, fontSize: 12, letterSpacing: 0.5, cursor: "pointer", boxShadow: "0 3px 14px rgba(0,0,0,0.5)" }}
          >
            SOS
          </button>
        )}
        <button
          onClick={() => (armed ? setArmed(false) : arm())}
          title={armed ? "Crash detection on" : "Turn on crash detection"}
          style={{
            background: armed ? "rgba(20,60,40,0.92)" : "rgba(10,10,10,0.85)",
            color: armed ? "#39ff88" : "#968f80", border: `1px solid ${armed ? "#39ff88" : "#2a2820"}`,
            borderRadius: 10, padding: "8px 11px", fontSize: 12, fontWeight: 700, cursor: "pointer", boxShadow: "0 3px 14px rgba(0,0,0,0.5)",
          }}
        >
          {"\u{1F6E1}"} {armed ? "Guard on" : "Guard off"}
        </button>
      </div>

      {/* crash countdown overlay */}
      {phase === "countdown" && (
        <div style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(120,0,0,0.94)", color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 24, textAlign: "center" }}>
          <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: 0.4 }}>Possible crash detected</div>
          <div style={{ fontSize: 72, fontWeight: 800, margin: "8px 0", fontVariantNumeric: "tabular-nums" }}>{count}</div>
          <div style={{ fontSize: 13, opacity: 0.9, maxWidth: 320 }}>Alerting your emergency contact and sharing your location. Tap below if you are OK.</div>
          <button onClick={dismiss} style={{ marginTop: 22, background: "#fff", color: "#7a0000", border: "none", borderRadius: 12, padding: "16px 40px", fontSize: 18, fontWeight: 800, cursor: "pointer" }}>
            I&apos;M OK
          </button>
          <button onClick={() => fire("crash")} style={{ marginTop: 12, background: "transparent", color: "#fff", border: "1px solid rgba(255,255,255,0.6)", borderRadius: 10, padding: "10px 24px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
            Send now
          </button>
        </div>
      )}

      {/* sent confirmation */}
      {phase === "sent" && (
        <div style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(10,10,10,0.95)", color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 24, textAlign: "center" }}>
          <div style={{ fontSize: 40 }}>{result?.ok ? "✅" : "⚠️"}</div>
          <div style={{ fontSize: 18, fontWeight: 800, margin: "8px 0" }}>
            {result?.ok ? `${result?.label || "SOS"} sent` : "Alert could not be pushed"}
          </div>
          <div style={{ fontSize: 13, opacity: 0.85, maxWidth: 320 }}>
            {result?.ok ? "Your emergency contact was alerted with your location." : "No push channel configured. Use the buttons below."}
          </div>
          <a href="tel:911" style={{ marginTop: 20, background: "#c0392b", color: "#fff", borderRadius: 12, padding: "16px 44px", fontSize: 18, fontWeight: 800, textDecoration: "none" }}>
            Call 911
          </a>
          {result?.maps ? (
            <a href={result.maps} target="_blank" rel="noreferrer" style={{ marginTop: 12, color: "#7fd1ff", fontSize: 13 }}>Open my location</a>
          ) : null}
          <button onClick={dismiss} style={{ marginTop: 16, background: "transparent", color: "#968f80", border: "none", fontSize: 13, cursor: "pointer" }}>Dismiss</button>
        </div>
      )}
    </>
  );
}
