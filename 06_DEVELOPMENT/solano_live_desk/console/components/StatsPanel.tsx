"use client";
import { motion, AnimatePresence } from "framer-motion";

const COLORS = ["#D4AF37", "#ff8c1a", "#7fd1ff", "#8fe3a8", "#ff5b5b", "#d59bff", "#ffd21a", "#9bffe0"];

function Pie({ data }: { data: [string, number][] }) {
  const total = data.reduce((s, [, v]) => s + v, 0) || 1;
  let acc = 0;
  const cx = 58, cy = 58, r = 50;
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <svg width="116" height="116" viewBox="0 0 116 116">
        {data.map(([, v], i) => {
          const frac = v / total;
          const a0 = acc * 2 * Math.PI - Math.PI / 2;
          acc += frac;
          const a1 = acc * 2 * Math.PI - Math.PI / 2;
          const large = frac > 0.5 ? 1 : 0;
          if (frac >= 0.999) return <circle key={i} cx={cx} cy={cy} r={r} fill={COLORS[i % COLORS.length]} />;
          return (
            <path key={i} fill={COLORS[i % COLORS.length]}
              d={`M${cx},${cy} L${cx + r * Math.cos(a0)},${cy + r * Math.sin(a0)} A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(a1)},${cy + r * Math.sin(a1)} Z`} />
          );
        })}
      </svg>
      <div style={{ fontSize: 11, flex: 1, minWidth: 130 }}>
        {data.map(([label, v], i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
            <span style={{ width: 9, height: 9, background: COLORS[i % COLORS.length], borderRadius: 2, flex: "0 0 auto" }} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
            <span style={{ color: "var(--muted)", marginLeft: "auto" }}>{Math.round((v / total) * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Bars({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 1, height: 58 }}>
        {values.map((v, h) => (
          <div key={h} title={`${h}:00 (${v})`} style={{ flex: 1, background: "#D4AF37", height: `${(v / max) * 100}%`, minHeight: v ? 2 : 0, borderRadius: 1, opacity: 0.85 }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--muted)", marginTop: 2 }}>
        <span>12a</span><span>6a</span><span>12p</span><span>6p</span><span>11p</span>
      </div>
    </div>
  );
}

function HBars({ data, color = "#7fd1ff" }: { data: [string, number][]; color?: string }) {
  const max = Math.max(...data.map(([, v]) => v), 1);
  return (
    <div>
      {data.map(([label, v], i) => (
        <div key={i} style={{ marginBottom: 5 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 1 }}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "80%" }}>{label}</span>
            <span style={{ color: "var(--muted)" }}>{v}</span>
          </div>
          <div style={{ height: 5, background: "#222", borderRadius: 3 }}>
            <div style={{ width: `${(v / max) * 100}%`, height: "100%", background: color, borderRadius: 3 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--muted)", marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: any }) {
  return (
    <div className="glass" style={{ flex: 1, borderRadius: 10, padding: "8px 10px" }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: "var(--gold)" }}>{value}</div>
      <div style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
    </div>
  );
}

export default function StatsPanel({ open, stats, onClose }: { open: boolean; stats: any; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="glass scroll-thin"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          style={{
            position: "absolute", top: 76, left: "50%", transform: "translateX(-50%)",
            width: "min(460px, 94vw)", maxHeight: "72vh", overflowY: "auto",
            borderRadius: 14, padding: 16, zIndex: 26,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 4 }}>
            <span className="display" style={{ color: "var(--gold)", fontSize: 17 }}>
              Analytics {stats?.date ? `· ${String(stats.date).replace(/_/g, "-")}` : ""}
            </span>
            <button onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text)", fontSize: 20, cursor: "pointer" }}>
              &times;
            </button>
          </div>
          {!stats ? (
            <div style={{ color: "var(--muted)", fontSize: 13 }}>loading&hellip;</div>
          ) : (
            <div>
              <div style={{ display: "flex", gap: 8 }}>
                <Tile label="Incidents today" value={stats.total} />
                <Tile label="Avg active" value={`${stats.avg_active_min} min`} />
              </div>
              <Section title="Busy hours (incidents by time of day)">
                <Bars values={stats.by_hour || []} />
              </Section>
              {stats.by_type?.length ? (
                <Section title="Incident type mix">
                  <Pie data={stats.by_type} />
                </Section>
              ) : null}
              {stats.by_area?.length ? (
                <Section title="Hotspots (by location)">
                  <HBars data={stats.by_area} />
                </Section>
              ) : null}
              {stats.by_severity ? (
                <Section title="Severity">
                  <HBars data={Object.entries(stats.by_severity) as [string, number][]} color="#ff8c1a" />
                </Section>
              ) : null}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
