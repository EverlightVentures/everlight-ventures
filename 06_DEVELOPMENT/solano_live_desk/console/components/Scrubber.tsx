"use client";

const btn: React.CSSProperties = {
  background: "rgba(255,255,255,0.06)", border: "1px solid var(--line)", color: "var(--text)",
  borderRadius: 7, padding: "4px 8px", fontSize: 12, cursor: "pointer", flex: "0 0 auto", lineHeight: 1,
};

export default function Scrubber({
  value, onChange, label, live, playing, onPlay, speed, onSpeed, onLive,
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
  live: boolean;
  playing: boolean;
  onPlay: () => void;
  speed: number;
  onSpeed: () => void;
  onLive: () => void;
}) {
  return (
    <div
      className="glass"
      style={{
        position: "absolute", bottom: 66, left: "50%", transform: "translateX(-50%)",
        borderRadius: 10, padding: "6px 10px", zIndex: 17, display: "flex",
        alignItems: "center", gap: 7, width: "min(560px, 94vw)",
      }}
    >
      <button onClick={onPlay} title={playing ? "pause" : "play back the day"} style={btn}>
        {playing ? "⏸" : "▶"}
      </button>
      <button onClick={onSpeed} title="playback speed" style={btn}>{speed}x</button>
      <span style={{ fontSize: 11, color: live ? "#2ecc71" : "var(--gold)", fontWeight: 700, minWidth: 58, textAlign: "center" }}>
        {live ? "● LIVE" : label}
      </span>
      <input
        type="range" min={0} max={100} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, accentColor: "#D4AF37" }}
      />
      <button onClick={onLive} title="jump to now" style={{ ...btn, color: live ? "var(--muted)" : "#2ecc71" }}>
        Now
      </button>
    </div>
  );
}
