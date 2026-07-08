"use client";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Incident } from "@/lib/types";
import { THREAT_COLORS } from "@/lib/types";
import { getEventTranscript, getCameras } from "@/lib/api";

const TABS = ["Feed", "Transcript", "Audio", "Cameras", "Sources"] as const;
type Tab = (typeof TABS)[number];

// Distinct colors so each Officer reads as a different voice; Dispatcher is gold.
const OFFICER_COLORS = ["#7fd1ff", "#8fe3a8", "#ffb454", "#d59bff", "#ff9bb0", "#9bffe0"];
function speakerColor(speaker: string) {
  if (speaker === "Dispatcher") return "#d4af37";
  const n = parseInt(speaker.replace(/\D/g, ""), 10) || 1;
  return OFFICER_COLORS[(n - 1) % OFFICER_COLORS.length];
}

function LiveVideo({ src }: { src: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    let hls: any;
    (async () => {
      if (v.canPlayType("application/vnd.apple.mpegurl")) {
        v.src = src; // Safari native HLS
      } else {
        const Hls = (await import("hls.js")).default;
        if (Hls.isSupported()) {
          hls = new Hls({ liveDurationInfinity: true });
          hls.loadSource(src);
          hls.attachMedia(v);
        } else {
          v.src = src;
        }
      }
    })();
    return () => hls && hls.destroy();
  }, [src]);
  return <video ref={ref} controls muted playsInline autoPlay style={{ width: "100%", borderRadius: 8, background: "#000" }} />;
}

function Transcripts({ data }: { data: { segments: any[]; sources: number } | null }) {
  if (data === null) return <Muted>loading radio traffic...</Muted>;
  if (!data.segments.length) return <Muted>no radio traffic matched to this event yet</Muted>;
  const audio = data.segments.find((s) => s.audio_url)?.audio_url;
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>
        {data.sources} matched call{data.sources !== 1 ? "s" : ""} near this event &middot; who said what
      </div>
      {audio && <audio controls preload="none" src={audio} style={{ width: "100%", height: 32, marginBottom: 10 }} />}
      {data.segments.map((s, i) => (
        <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <span style={{ flex: "0 0 auto", width: 72, fontSize: 11, fontWeight: 700, color: speakerColor(s.speaker) }}>
            {s.speaker}
          </span>
          <div style={{ fontSize: 13, lineHeight: 1.45 }}>
            {s.time && <span style={{ color: "var(--muted)", fontSize: 11, marginRight: 6 }}>{s.time}</span>}
            {s.text}
            {s.codes?.length ? (
              <span style={{ color: "#ff8c1a", fontSize: 11, marginLeft: 6 }}>{s.codes.join(", ")}</span>
            ) : null}
          </div>
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
  const [transcripts, setTranscripts] = useState<{ segments: any[]; sources: number } | null>(null);
  const [cams, setCams] = useState<any[] | null>(null);

  useEffect(() => { setTab("Feed"); setTranscripts(null); setCams(null); }, [ev?.id]);
  useEffect(() => {
    if (!ev) return;
    if (tab === "Transcript" && transcripts === null) {
      if (ev.lat != null) getEventTranscript(ev.lat, ev.lon!).then(setTranscripts).catch(() => setTranscripts({ segments: [], sources: 0 }));
      else setTranscripts({ segments: [], sources: 0 });
    }
    if (tab === "Cameras" && cams === null && ev.lat != null)
      getCameras(ev.lat, ev.lon!).then(setCams).catch(() => setCams([]));
  }, [tab, ev, transcripts, cams]);

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
          {tab === "Cameras" && <Cams data={cams} />}
          {tab === "Sources" && <Sources ev={ev} />}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
