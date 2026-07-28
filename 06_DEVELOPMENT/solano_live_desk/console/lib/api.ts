import type { Incident, SpaceWx } from "./types";

// The console is served at /console but the API stays at the site root, so all
// fetches use absolute /api paths (unaffected by basePath).
async function j<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

const q = (lat?: number, lon?: number) =>
  lat != null && lon != null ? `?lat=${lat}&lon=${lon}` : "";
const qd = (lat?: number, lon?: number, date?: string) => {
  const p = new URLSearchParams();
  if (lat != null && lon != null) { p.set("lat", String(lat)); p.set("lon", String(lon)); }
  if (date) p.set("date", date);
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const getEvents = (lat?: number, lon?: number, date?: string) =>
  j<{ events: Incident[] }>(`/api/events${qd(lat, lon, date)}`).then((d) => d.events);

export const getCorrelated = (lat?: number, lon?: number, date?: string) =>
  j<{ incidents: Incident[] }>(`/api/correlated${qd(lat, lon, date)}`).then((d) => d.incidents);

export const getEvac = (lat: number, lon: number) =>
  j<{ geojson: any }>(`/api/evac?lat=${lat}&lon=${lon}`).then((d) => d.geojson);
export const getSafePoints = (lat: number, lon: number) =>
  j<{ safe_points: any[] }>(`/api/safepoints?lat=${lat}&lon=${lon}`).then((d) => d.safe_points || []);
export const getBuses = (lat: number, lon: number) =>
  j<{ transit: any[] }>(`/api/transit?lat=${lat}&lon=${lon}`).then((d) => d.transit || []);
export const getDanger = () => j<any>("/api/danger");
export const getRoute = (lat: number, lon: number) => j<any>(`/api/route?lat=${lat}&lon=${lon}`);
export const getDays = () => j<{ days: string[] }>("/api/days").then((d) => d.days || []);
export const getMapCameras = (lat: number, lon: number) =>
  j<{ cameras: any[] }>(`/api/cameras?lat=${lat}&lon=${lon}&n=14`).then((d) => d.cameras || []);
export const getNews = (place: string) =>
  j<{ news: any[] }>(`/api/news?place=${encodeURIComponent(place)}`).then((d) => d.news || []);

export const getSpaceWx = () => j<SpaceWx>("/api/spacewx");

export const getEventTranscript = (lat: number, lon: number, id?: string) =>
  j<{ conversations: any[]; sources: number }>(
    `/api/event_transcript?lat=${lat}&lon=${lon}${id ? `&id=${encodeURIComponent(id)}` : ""}`
  );
export const getCamDvr = (lat: number, lon: number, t?: number) =>
  j<{ camera: any; frames: any[] }>(`/api/cam_dvr?lat=${lat}&lon=${lon}${t ? `&t=${t}` : ""}`);
export const getFlight = (callsign: string, type?: string) =>
  j<any>(`/api/flight?callsign=${encodeURIComponent(callsign)}${type ? `&type=${encodeURIComponent(type)}` : ""}`);
export const getStats = (date?: string) => j<any>(`/api/stats${date ? `?date=${date}` : ""}`);
export const getMesh = () => j<{ nodes: any[]; messages: any[]; updated: number }>("/api/mesh");
export const getIntel = (lat: number, lon: number) => j<any>(`/api/intel?lat=${lat}&lon=${lon}`);
export const getLinks = (id: string) => j<{ links: any[]; entities: any }>(`/api/links?id=${encodeURIComponent(id)}`);
export const getDecision = (lat: number, lon: number) => j<any>(`/api/decision?lat=${lat}&lon=${lon}`);
// Dispersed Egress: several ranked escape routes to safety (clearest way out first).
export const getEscape = (lat: number, lon: number) => j<any>(`/api/escape?lat=${lat}&lon=${lon}`);
// Personal SOS / crash alert -> max-priority push to a trusted phone.
export const sendSos = (lat: number, lon: number, kind: "crash" | "manual", where = "") =>
  fetch(`/api/sos?lat=${lat}&lon=${lon}&kind=${kind}${where ? `&where=${encodeURIComponent(where)}` : ""}`, { method: "POST" })
    .then((r) => r.json())
    .catch(() => ({ ok: false }));

// Community reports (reckless driver / hazard) + gig-driver "on delivery" presence.
export const postReport = (kind: string, lat: number, lon: number, detail = "") =>
  fetch(`/api/report?kind=${kind}&lat=${lat}&lon=${lon}${detail ? `&detail=${encodeURIComponent(detail)}` : ""}`, { method: "POST" })
    .then((r) => r.json()).catch(() => ({ ok: false }));
export const postPresence = (client: string, lat: number, lon: number, active: boolean) =>
  fetch(`/api/presence?client=${encodeURIComponent(client)}&lat=${lat}&lon=${lon}&active=${active}`, { method: "POST" })
    .then((r) => r.json()).catch(() => ({ ok: false }));
export const getReports = () => j<{ reports: any[] }>("/api/reports").then((d) => d.reports || []);

// EPIRB-style distress beacon (broadcasts position on repeat until cancelled).
export const postBeacon = (client: string, lat: number | null, lon: number | null, note: string, active: boolean) =>
  fetch(`/api/beacon?client=${encodeURIComponent(client)}${lat != null ? `&lat=${lat}` : ""}${lon != null ? `&lon=${lon}` : ""}${note ? `&note=${encodeURIComponent(note)}` : ""}&active=${active}`, { method: "POST" })
    .then((r) => r.json()).catch(() => ({ active: false }));
export const getBeacon = () => j<{ beacons: any[] }>("/api/beacon").then((d) => d.beacons || []);
export const getSocial = (place: string) => j<{ posts: any[] }>(`/api/social?place=${encodeURIComponent(place)}`);
export const getSocialHotspots = () => j<{ hotspots: any[]; updated: number }>("/api/social_hotspots");

export const getCameras = (lat: number, lon: number) =>
  j<{ cameras: any[] }>(`/api/cameras?lat=${lat}&lon=${lon}&n=3`).then((d) => d.cameras);

export const getCounty = (lat: number, lon: number) =>
  j<{ county: string; state: string }>(`/api/county?lat=${lat}&lon=${lon}`);

export const getAircraft = (lat: number, lon: number) =>
  j<{ aircraft: any[] }>(`/api/aircraft?lat=${lat}&lon=${lon}`).then((d) => d.aircraft || []);

export const getTrains = (lat: number, lon: number) =>
  j<{ trains: any[] }>(`/api/trains?lat=${lat}&lon=${lon}`).then((d) => d.trains || []);
