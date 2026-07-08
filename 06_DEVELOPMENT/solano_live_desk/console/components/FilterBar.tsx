"use client";
import type { Filters } from "@/lib/util";

const SEVS = ["EXTREME", "HIGH", "MEDIUM", "LOW"];
const SEV_COLORS: Record<string, string> = {
  EXTREME: "#ff2d2d", HIGH: "#ff8c1a", MEDIUM: "#ffd21a", LOW: "#D4AF37",
};

function nActive(f: Filters) {
  return (f.q.trim() ? 1 : 0) + (f.src ? 1 : 0) + (Object.values(f.sev).some(Boolean) ? 1 : 0);
}

export default function FilterBar({
  filters, onChange, sources, count, open, onToggle,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  sources: string[];
  count: number;
  open: boolean;
  onToggle: () => void;
}) {
  const active = nActive(filters);
  if (!open) {
    return (
      <button
        onClick={onToggle}
        className="glass"
        style={{
          position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)", zIndex: 21,
          borderRadius: 10, padding: "6px 11px", color: "var(--gold)", border: "1px solid var(--line)",
          cursor: "pointer", fontSize: 12, fontWeight: 600, display: "flex", alignItems: "center", gap: 5,
        }}
      >
        {"\u{1F50D}"} Filter
        {active > 0 && (
          <span style={{ background: "var(--gold)", color: "#08080a", fontSize: 10, fontWeight: 700, borderRadius: 999, padding: "1px 6px" }}>
            {active}
          </span>
        )}
      </button>
    );
  }
  return (
    <div
      className="glass scroll-thin"
      style={{
        position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)", zIndex: 23,
        borderRadius: 12, padding: "8px 10px", display: "flex", gap: 6, alignItems: "center",
        maxWidth: "94vw", overflowX: "auto",
      }}
    >
      <input
        value={filters.q}
        onChange={(e) => onChange({ ...filters, q: e.target.value })}
        placeholder="search..."
        style={{ background: "rgba(0,0,0,0.35)", border: "1px solid var(--line)", borderRadius: 8, color: "var(--text)", padding: "5px 9px", fontSize: 12, width: 120 }}
      />
      {SEVS.map((s) => (
        <button
          key={s}
          onClick={() => onChange({ ...filters, sev: { ...filters.sev, [s]: !filters.sev[s] } })}
          title={s}
          style={{
            background: filters.sev[s] ? SEV_COLORS[s] : "transparent",
            color: filters.sev[s] ? "#08080a" : "var(--text)",
            border: `1px solid ${SEV_COLORS[s]}`, borderRadius: 6, padding: "4px 7px",
            fontSize: 10, fontWeight: 700, cursor: "pointer",
          }}
        >
          {s[0]}
        </button>
      ))}
      <select
        value={filters.src}
        onChange={(e) => onChange({ ...filters, src: e.target.value })}
        style={{ background: "transparent", color: filters.src ? "var(--gold)" : "var(--text)", border: "1px solid var(--line)", borderRadius: 8, padding: "4px 6px", fontSize: 11 }}
      >
        <option value="" style={{ color: "#000" }}>all</option>
        {sources.map((s) => <option key={s} value={s} style={{ color: "#000" }}>{s}</option>)}
      </select>
      <span style={{ fontSize: 11, color: "var(--muted)", flex: "0 0 auto" }}>{count}</span>
      {active ? (
        <button onClick={() => onChange({ q: "", sev: {}, src: "" })} title="clear filters" style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 15 }}>
          &times;
        </button>
      ) : null}
      <button onClick={onToggle} title="hide" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--line)", color: "var(--text)", cursor: "pointer", fontSize: 13, borderRadius: 6, padding: "3px 8px" }}>
        &and;
      </button>
    </div>
  );
}
