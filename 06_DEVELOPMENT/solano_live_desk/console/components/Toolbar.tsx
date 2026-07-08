"use client";

export type ToggleKey = "danger" | "evac" | "safe" | "buses" | "route" | "cams" | "social";

const CHIPS: { k: ToggleKey; label: string }[] = [
  { k: "danger", label: "\u{1F534} Danger" },
  { k: "social", label: "\u{1F525} Hotspots" },
  { k: "evac", label: "\u{1F6D1} Evac" },
  { k: "safe", label: "\u{1F3E5} Safe" },
  { k: "buses", label: "\u{1F68C} Bus" },
  { k: "cams", label: "\u{1F4F7} Cams" },
  { k: "route", label: "\u{1F9ED} Route out" },
];

function chipStyle(on: boolean): React.CSSProperties {
  return {
    background: on ? "var(--gold)" : "transparent",
    color: on ? "#08080a" : "var(--text)",
    border: "1px solid var(--line)",
    borderRadius: 8,
    padding: "6px 10px",
    fontSize: 12,
    fontWeight: on ? 700 : 400,
    cursor: "pointer",
    whiteSpace: "nowrap",
  };
}

export default function Toolbar({
  active, onToggle, days, day, onDay, newsOpen, onNews, statsOpen, onStats, muted, onMute,
}: {
  active: Record<ToggleKey, boolean>;
  onToggle: (k: ToggleKey) => void;
  days: string[];
  day: string;
  onDay: (d: string) => void;
  newsOpen: boolean;
  onNews: () => void;
  statsOpen: boolean;
  onStats: () => void;
  muted: boolean;
  onMute: () => void;
}) {
  return (
    <div
      className="glass scroll-thin"
      style={{
        position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)",
        borderRadius: 12, padding: "7px 10px", zIndex: 18, display: "flex", gap: 6,
        alignItems: "center", maxWidth: "94vw", overflowX: "auto",
      }}
    >
      {CHIPS.map((c) => (
        <button key={c.k} onClick={() => onToggle(c.k)} style={chipStyle(active[c.k])}>
          {c.label}
        </button>
      ))}
      <button onClick={onNews} style={chipStyle(newsOpen)}>{"\u{1F4F0}"} News</button>
      <button onClick={onStats} style={chipStyle(statsOpen)}>{"\u{1F4CA}"} Stats</button>
      <button onClick={onMute} style={chipStyle(!muted)} title="sound alerts on new critical incidents">
        {muted ? "\u{1F507}" : "\u{1F514}"}
      </button>
      <div style={{ width: 1, height: 22, background: "var(--line)" }} />
      <select
        value={day}
        onChange={(e) => onDay(e.target.value)}
        title="review a past day (archived)"
        style={{
          background: "transparent", color: day ? "var(--gold)" : "var(--text)",
          border: "1px solid var(--line)", borderRadius: 8, padding: "6px 8px",
          fontSize: 12, cursor: "pointer",
        }}
      >
        <option value="" style={{ color: "#000" }}>Today (live)</option>
        {days.map((d) => (
          <option key={d} value={d} style={{ color: "#000" }}>
            {d.replace(/_/g, "-")}
          </option>
        ))}
      </select>
    </div>
  );
}
