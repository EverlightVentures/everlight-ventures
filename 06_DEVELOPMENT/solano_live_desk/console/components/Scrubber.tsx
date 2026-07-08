"use client";

export default function Scrubber({
  value, onChange, label, live,
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
  live: boolean;
}) {
  return (
    <div
      className="glass"
      style={{
        position: "absolute", bottom: 66, left: "50%", transform: "translateX(-50%)",
        borderRadius: 10, padding: "6px 12px", zIndex: 17, display: "flex",
        alignItems: "center", gap: 10, width: "min(520px, 92vw)",
      }}
    >
      <span style={{ fontSize: 11, color: live ? "#2ecc71" : "var(--gold)", fontWeight: 700, minWidth: 62 }}>
        {live ? "● LIVE" : label}
      </span>
      <input
        type="range" min={0} max={100} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, accentColor: "#D4AF37" }}
      />
    </div>
  );
}
