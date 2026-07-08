"use client";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Incident } from "@/lib/types";
import { THREAT_COLORS } from "@/lib/types";
import { getEventTranscript, getCameras, getCamDvr } from "@/lib/api";
import LiveVideo from "@/components/LiveVideo";

const TABS = ["Feed", "Transcript", "Audio", "Cameras", "Sources"] as const;
type Tab = (typeof TABS)[number];

// Distinct colors so each Officer reads as a different voice; Dispatcher is gold.
const OFFICER_COLORS = ["#7fd1ff", "#8fe3a8", "#ffb454", "#d59bff", "#ff9bb0", "#9bffe0"];
function speakerColor(speaker: string) {
  if (speaker === "Dispatcher") return "#d4af37";
  const n = parseInt(speaker.replace(/\D/g, ""), 10) || 1;
  return OFFICER_COLORS[(n - 1) % OFFICER_COLORS.length];
}

const SERVICE_COLORS: Record<string, string> = {
  EMS: "#ff5b5b", Fire: "#ff8c1a", CHP: "#7fd1ff", Police: "#d4af37", Dispatch: "#8fe3a8",
};

function Transcripts({ data }: { data: { conversations: any[]; sources: number } | null }) {
  const [svc, setSvc] = useState<string | null>(null);
  if (data === null) return <Muted>loading radio traffic...</Muted>;
  const convos = data.conversations || [];
  if (!convos.length) return <Muted>no radio traffic matched to this event yet</Muted>;
  const services = Array.from(new Set(convos.map((c) => c.service)));
  const active = svc && services.includes(svc) ? svc : services[0];
  const shown = convos.filter((c) => c.service === active);
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>
        {data.sources} call{data.sources !== 1 ? "s" : ""} near this event &middot; pick a service
      </div>
      <div style={{ display: "flex", gap: 4, marginBottom: 10, flexWrap: "wrap" }}>
        {services.map((s) => (
          <button
            key={s}
            onClick={() => setSvc(s)}
            style={{
              background: active === s ? SERVICE_COLORS[s] || "#888" : "transparent",
              color: active === s ? "#08080a" : "var(--text)",
              border: `1px solid ${SERVICE_COLORS[s] || "var(--line)"}`,
              borderRadius: 6, padding: "3px 9px", fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}
          >
            {s} ({convos.filter((c) => c.service === s).length})
          </button>
        ))}
      </div>
      {shown.map((c, i) => (
        <div key={i} style={{ borderTop: i ? "1px solid var(--line)" : "none", paddingTop: i ? 10 : 0, marginTop: i ? 10 : 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: SERVICE_COLORS[c.service] || "var(--gold)" }}>
            {c.service} &middot; {c.call}
            <span style={{ color: "var(--muted)", fontWeight: 400 }}> &middot; started {c.start}</span>
          </div>
          {c.audio_url && <audio controls preload="none" src={c.audio_url} style={{ width: "100%", height: 32, margin: "6px 0" }} />}
          {c.segments.map((s: any, j: number) => (
            <div key={j} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
              <span style={{ flex: "0 0 auto", width: 72, fontSize: 11, fontWeight: 700, color: speakerColor(s.speaker) }}>
                {s.speaker}
              </span>
              <div style={{ fontSize: 13, lineHeight: 1.4 }}>
                {s.time && <span style={{ color: "var(--muted)", fontSize: 11, marginRight: 6 }}>{s.time}</span>}
                {s.text}
                {s.codes?.length ? <span style={{ color: "#ff8c1a", fontSize: 11, marginLeft: 6 }}>{s.codes.join(", ")}</span> : null}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function Cams({ data }: { data: any[] | null }) {
  if (data === null) return <Muted>loading cameras...</Muted>;
  if (!data.length) return <Muted>no cameras in range</Muted>;
  return (
    <div>
      {data.map((c, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          {c.stream_url ? <LiveVideo src={c.stream_url} /> : c.image_url ? (
            <img src={`${c.image_url}${c.image_url.includes("?") ? "&" : "?"}t=${Date.now()}`} alt="" style={{ width: "100%", borderRadius: 8, background: "#222" }} />
          ) : null}
          <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3 }}>
            {c.name || "camera"} &middot; {c.distance_mi} mi &middot; {c.stream_url ? "LIVE" : "still"}
          </div>
        </div>
      ))}
    </div>
  );
}

function DvrPlayer({ data, eventTs }: { data: { camera: any; frames: any[] } | null; eventTs: number }) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (data?.frames?.length) {
      let best = 0, bd = 1e12;
      data.frames.forEach((f, i) => { const d = Math.abs(f.ts - eventTs); if (d < bd) { bd = d; best = i; } });
      setIdx(best);
    }
  }, [data, eventTs]);
  if (data === null) return <Muted>loading footage...</Muted>;
  if (!data.frames.length) return <Muted>no recorded footage near this event yet (the DVR records cameras near you from now on)</Muted>;
  const f = data.frames[Math.min(idx, data.frames.length - 1)];
  const rel = Math.round((f.ts - eventTs) / 60);
  const label = rel === 0 ? "at event time" : rel < 0 ? `${-rel} min before` : `${rel} min after`;
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>
        {data.camera?.name} &middot; {data.camera?.distance_mi} mi &middot; {data.frames.length} frames
      </div>
      <img src={f.url} alt="" style={{ width: "100%", borderRadius: 8, background: "#000" }} />
      <div style={{ fontSize: 12, color: "var(--gold)", textAlign: "center", margin: "5px 0", fontWeight: 600 }}>{label}</div>
      <input type="range" min={0} max={data.frames.length - 1} value={idx} onChange={(e) => setIdx(Number(e.target.value))} style={{ width: "100%", accentColor: "#D4AF37" }} />
    </div>
  );
}

function Sources({ ev }: { ev: Incident }) {
  const rows = [
    ["Source", ev.source], ["Type", ev.type], ["Location", ev.geo_label],
    ["First seen", ev.first_seen], ["Last seen", ev.last_seen],
    ["Threat", `${ev.threat_level}${ev.status ? " · " + ev.status : ""}`],
  ];
  if (ev.confidence != null) rows.push(["Confidence", `${Math.round(ev.confidence * 100)}% (${ev.tier})`]);
  if (ev.sources) rows.push(["Corroborating", ev.sources.join(", ")]);
  if (ev.units?.length) rows.push(["Units", ev.units.join(", ")]);
  return (
    <div style={{ fontSize: 13, lineHeight: 1.7 }}>
      {rows.filter((r) => r[1]).map((r, i) => (
        <div key={i}>
          <span style={{ color: "var(--muted)" }}>{r[0]}: </span>
          {String(r[1])}
        </div>
      ))}
    </div>
  );
}

const preStyle: React.CSSProperties = { whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.5, fontFamily: "inherit", margin: 0 };
const Muted = ({ children }: { children: React.ReactNode }) => (
  <div style={{ color: "var(--muted)", fontSize: 13 }}>{children}</div>
);

export default function DetailDrawer({ ev, onClose }: { ev: Incident | null; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("Feed");
  const [transcripts, setTranscripts] = useState<{ conversations: any[]; sources: number } | null>(null);
  const [cams, setCams] = useState<any[] | null>(null);
  const [dvr, setDvr] = useState<{ camera: any; frames: any[] } | null>(null);
  const eventTs = ev ? Math.round((Date.parse(ev.last_seen || "") || Date.now()) / 1000) : 0;

  useEffect(() => { setTab("Feed"); setTranscripts(null); setCams(null); setDvr(null); }, [ev?.id]);
  useEffect(() => {
    if (!ev) return;
    if (tab === "Transcript" && transcripts === null) {
      if (ev.lat != null) getEventTranscript(ev.lat, ev.lon!, ev.id).then(setTranscripts).catch(() => setTranscripts({ conversations: [], sources: 0 }));
      else setTranscripts({ conversations: [], sources: 0 });
    }
    if (tab === "Cameras" && cams === null && ev.lat != null)
      getCameras(ev.lat, ev.lon!).then(setCams).catch(() => setCams([]));
    if (tab === "Cameras" && dvr === null && ev.lat != null)
      getCamDvr(ev.lat, ev.lon!, eventTs).then(setDvr).catch(() => setDvr({ camera: null, frames: [] }));
  }, [tab, ev, transcripts, cams, dvr, eventTs]);

  return (
    <AnimatePresence>
      {ev && (
        <motion.aside
          className="glass scroll-thin"
          initial={{ x: 400, opacity: 0.5 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: "spring", damping: 26, stiffness: 240 }}
          style={{
            position: "absolute", top: 76, right: 12, bottom: 12, width: 384, maxWidth: "92vw",
            borderRadius: 14, padding: 16, overflowY: "auto", zIndex: 25,
          }}
        >
          <button
            onClick={onClose}
            style={{ position: "absolute", top: 10, right: 12, background: "none", border: "none", color: "var(--text)", fontSize: 22, cursor: "pointer", lineHeight: 1 }}
          >
            &times;
          </button>
          <span
            style={{
              background: ev.inferred ? "#ff00d4" : THREAT_COLORS[ev.threat_level] || "#888",
              color: "#fff", fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 6,
            }}
          >
            {ev.threat_level}
            {ev.tier ? ` · ${ev.tier}` : ""}
            {ev.confidence != null ? ` ${Math.round(ev.confidence * 100)}%` : ""}
            {ev.status ? ` · ${ev.status}` : ""}
          </span>
          <h2 className="display" style={{ fontSize: 20, margin: "10px 0 3px", color: "var(--gold)" }}>
            {ev.type || "Incident"}
          </h2>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            {ev.geo_label}
            {ev.distance_mi != null ? ` · ${ev.distance_mi} mi` : ""}
          </div>
          <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--line)", marginBottom: 12, overflowX: "auto" }}>
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  background: "none", border: "none", cursor: "pointer", padding: "6px 9px",
                  fontSize: 12, whiteSpace: "nowrap",
                  color: tab === t ? "var(--gold)" : "var(--muted)",
                  borderBottom: `2px solid ${tab === t ? "var(--gold)" : "transparent"}`,
                }}
              >
                {t}
              </button>
            ))}
          </div>
          {tab === "Feed" && <pre style={preStyle}>{ev.body || "(no dispatch detail yet)"}</pre>}
          {tab === "Transcript" && <Transcripts data={transcripts} />}
          {tab === "Audio" && (ev.audio_url
            ? <audio controls preload="none" src={ev.audio_url} style={{ width: "100%" }} />
            : <Muted>no recorded audio for this incident</Muted>)}
          {tab === "Cameras" && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--gold)", marginBottom: 6 }}>
                Event footage (5 min before &rarr; after)
              </div>
              <DvrPlayer data={dvr} eventTs={eventTs} />
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--gold)", margin: "14px 0 6px" }}>
                Live cameras nearby
              </div>
              <Cams data={cams} />
            </div>
          )}
          {tab === "Sources" && <Sources ev={ev} />}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
