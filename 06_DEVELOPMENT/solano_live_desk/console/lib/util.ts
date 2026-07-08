import type { Incident } from "./types";

// "2m ago" style relative age.
export function ageLabel(iso?: string): string {
  if (!iso) return "";
  const s = (Date.now() - (Date.parse(iso) || 0)) / 1000;
  if (s < 0) return "now";
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// Temporal decay: fresh = 1.0, fades to 0.25 by 6h old.
export function ageOpacity(iso?: string): number {
  if (!iso) return 1;
  const h = (Date.now() - (Date.parse(iso) || Date.now())) / 3600000;
  if (h <= 0.5) return 1;
  if (h >= 6) return 0.25;
  return 1 - ((h - 0.5) / 5.5) * 0.75;
}

// Source reliability tier (verified dispatch > scanner > sensor > social).
const SOURCE_META: Record<string, { label: string; tier: string; color: string }> = {
  chp: { label: "CHP", tier: "Verified", color: "#8fe3a8" },
  roads: { label: "511", tier: "Verified", color: "#8fe3a8" },
  scanner: { label: "Scanner", tier: "Reported", color: "#ffb454" },
  correlated: { label: "Fused", tier: "Correlated", color: "#d4af37" },
  firms: { label: "Satellite", tier: "Sensor", color: "#ff8c1a" },
  quakes: { label: "USGS", tier: "Sensor", color: "#7fd1ff" },
  nws: { label: "NWS", tier: "Sensor", color: "#7fd1ff" },
  reddit: { label: "Social", tier: "Unverified", color: "#d59bff" },
};
export function sourceMeta(source?: string) {
  return SOURCE_META[source || ""] || { label: source || "?", tier: "Unverified", color: "#8a8a90" };
}

// Category glyph from the incident type (fire / medical-traffic / crime / quake).
const GLYPH: [RegExp, string][] = [
  [/fire|smoke|arson|hazmat|explos|wildfire/i, "\u{1F525}"],
  [/robber|211|459|415|assault|242|240|suspect|pursuit|shot|shooting|187|homicide|weapon|gun/i, "\u{1F6A8}"],
  [/construction|roadwork|road work|closure|closed|cone/i, "\u{1F6A7}"],
  [/quake|earthquake/i, "\u{1F30A}"],
  [/flood|storm|wind|weather|heat/i, "\u{26A0}"],
  [/medical|ems|injur|gsw|collision|crash|1179|1181|traffic|hazard|debris|vehicle|dui/i, "\u{1F697}"],
];
export function categoryGlyph(type?: string): string {
  for (const [re, g] of GLYPH) if (re.test(type || "")) return g;
  return "";
}

// Client-side incident filter (text + severity toggles + source).
export type Filters = { q: string; sev: Record<string, boolean>; src: string };
export const EMPTY_FILTERS: Filters = { q: "", sev: {}, src: "" };
export function filterIncidents(list: Incident[], f: Filters): Incident[] {
  const q = f.q.trim().toLowerCase();
  const anySev = Object.values(f.sev).some(Boolean);
  return list.filter((e) => {
    if (q && !`${e.type || ""} ${e.geo_label || ""} ${e.source || ""}`.toLowerCase().includes(q)) return false;
    if (anySev && !f.sev[e.threat_level]) return false;
    if (f.src && e.source !== f.src) return false;
    return true;
  });
}
