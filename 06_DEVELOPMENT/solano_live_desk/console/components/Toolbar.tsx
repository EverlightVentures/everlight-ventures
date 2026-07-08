"use client";

export type ToggleKey = "danger" | "evac" | "safe" | "buses" | "route";

const CHIPS: { k: ToggleKey; label: string }[] = [
  { k: "danger", label: "\u{1F534} Danger" },
  { k: "evac", label: "\u{1F6D1} Evac" },
  { k: "safe", label: "\u{1F3E5} Safe" },
  { k: "buses", label: "\u{1F68C} Bus" },
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
  active, onToggle, days, day, onDay,
}: {
  active: Record<ToggleKey, boolean>;
  onToggle: (k: ToggleKey) => void;
  days: string[];
  day: string;
  onDay: (d: string) => void;
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
