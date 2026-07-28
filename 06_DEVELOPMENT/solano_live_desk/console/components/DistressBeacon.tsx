"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { postBeacon, getBeacon } from "@/lib/api";

function clientId(): string {
  try {
    let id = localStorage.getItem("aroundme_client");
    if (!id) { id = "c" + Math.random().toString(36).slice(2, 10); localStorage.setItem("aroundme_client", id); }
    return id;
  } catch { return "anon"; }
}
const mmss = (s: number) => `${Math.floor(s / 60)}m ${s % 60}s`;

// EPIRB-style distress beacon. NOT a certified 406 MHz EPIRB: it pulses your
// position to your contact + the local mesh on repeat until cancelled.
export default function DistressBeacon({ pos }: { pos: { lat: number; lon: number } | null }) {
  const [confirm, setConfirm] = useState(false);
  const [active, setActive] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const posRef = useRef(pos);
  useEffect(() => { posRef.current = pos; }, [pos]);

  // Poll the server so the banner survives a reload and reflects the true state.
  useEffect(() => {
    const id = clientId();
    const f = () => getBeacon().then((list) => {
      const mine = (list || []).find((b: any) => b.client === id);
      setActive(!!mine);
      if (mine) setElapsed(mine.elapsed_s);
    }).catch(() => {});
    f();
    const iv = setInterval(f, 15000);
    return () => clearInterval(iv);
  }, []);

  // Tick the elapsed clock locally while active.
  useEffect(() => {
    if (!active) return;
    const iv = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(iv);
  }, [active]);

  const activate = useCallback(async () => {
    const p = posRef.current;
    await postBeacon(clientId(), p?.lat ?? null, p?.lon ?? null, "", true);
    setActive(true); setElapsed(0); setConfirm(false);
  }, []);

  const cancel = useCallback(async () => {
    await postBeacon(clientId(), 0, 0, "", false);
    setActive(false); setElapsed(0);
  }, []);

  return (
    <>
      {!active && (
        <button
          onClick={() => setConfirm(true)}
          title="EPIRB-style distress beacon"
          style={{ position: "absolute", right: 12, bottom: 150, zIndex: 27, background: "rgba(90,10,10,0.9)", color: "#ffb0b0", border: "1px solid #ff5b5b55", borderRadius: 10, padding: "8px 11px", fontSize: 12, fontWeight: 800, letterSpacing: 0.4, cursor: "pointer", boxShadow: "0 3px 14px rgba(0,0,0,0.5)" }}
        >
          {"\u{1F198}"} EPIRB
        </button>
      )}

      {active && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 58, background: "#b3120f", color: "#fff", padding: "10px 14px", display: "flex", alignItems: "center", gap: 12, boxShadow: "0 4px 20px rgba(0,0,0,0.6)" }}>
          <span style={{ fontSize: 20 }}>{"\u{1F198}"}</span>
          <div style={{ flex: 1, lineHeight: 1.2 }}>
            <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: 0.4 }}>DISTRESS BEACON ACTIVE</div>
            <div style={{ fontSize: 11, opacity: 0.92 }}>Broadcasting your position on repeat &middot; {mmss(elapsed)}</div>
          </div>
          <button onClick={cancel} style={{ background: "#fff", color: "#b3120f", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: 12, fontWeight: 800, cursor: "pointer" }}>
            Cancel
          </button>
        </div>
      )}

      {confirm && (
        <div onClick={() => setConfirm(false)} style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(0,0,0,0.66)", display: "flex", alignItems: "center", justifyContent: "center", padding: 22 }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "#141310", border: "1px solid #4a2020", borderRadius: 16, padding: "24px 22px", maxWidth: 380, textAlign: "center", boxShadow: "0 10px 40px rgba(0,0,0,0.6)" }}>
            <div style={{ fontSize: 34 }}>{"\u{1F198}"}</div>
            <div style={{ color: "#fff", fontSize: 18, fontWeight: 800, margin: "8px 0 6px" }}>Activate distress beacon?</div>
            <div style={{ color: "#e8e8e8", fontSize: 13, lineHeight: 1.5 }}>
              This broadcasts your position on repeat until you cancel: a max-priority alert to your contact and the local mesh.
            </div>
            <div style={{ color: "#968f80", fontSize: 11, lineHeight: 1.5, margin: "12px 0 0" }}>
              This is NOT a certified 406 MHz EPIRB and does not reach Coast Guard or SARSAT. On open water or in true wilderness, carry a real EPIRB or PLB.
            </div>
            <button onClick={activate} style={{ marginTop: 18, width: "100%", background: "#b3120f", color: "#fff", border: "none", borderRadius: 12, padding: "16px", fontSize: 16, fontWeight: 800, cursor: "pointer" }}>
              ACTIVATE DISTRESS BEACON
            </button>
            <button onClick={() => setConfirm(false)} style={{ marginTop: 10, background: "transparent", color: "#968f80", border: "none", fontSize: 13, cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}
