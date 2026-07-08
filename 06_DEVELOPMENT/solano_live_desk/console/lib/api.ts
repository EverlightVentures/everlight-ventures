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
export const getFlight = (callsign: string) =>
  j<any>(`/api/flight?callsign=${encodeURIComponent(callsign)}`);
export const getStats = (date?: string) => j<any>(`/api/stats${date ? `?date=${date}` : ""}`);
export const getMesh = () => j<{ nodes: any[]; messages: any[]; updated: number }>("/api/mesh");

export const getCameras = (lat: number, lon: number) =>
  j<{ cameras: any[] }>(`/api/cameras?lat=${lat}&lon=${lon}&n=3`).then((d) => d.cameras);

export const getCounty = (lat: number, lon: number) =>
  j<{ county: string; state: string }>(`/api/county?lat=${lat}&lon=${lon}`);

export const getAircraft = (lat: number, lon: number) =>
  j<{ aircraft: any[] }>(`/api/aircraft?lat=${lat}&lon=${lon}`).then((d) => d.aircraft || []);

export const getTrains = (lat: number, lon: number) =>
  j<{ trains: any[] }>(`/api/trains?lat=${lat}&lon=${lon}`).then((d) => d.trains || []);
