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

export const getEvents = (lat?: number, lon?: number) =>
  j<{ events: Incident[] }>(`/api/events${q(lat, lon)}`).then((d) => d.events);

export const getCorrelated = (lat?: number, lon?: number) =>
  j<{ incidents: Incident[] }>(`/api/correlated${q(lat, lon)}`).then((d) => d.incidents);

export const getSpaceWx = () => j<SpaceWx>("/api/spacewx");

export const getEventTranscript = (lat: number, lon: number) =>
  j<{ segments: any[]; sources: number }>(`/api/event_transcript?lat=${lat}&lon=${lon}`);

export const getCameras = (lat: number, lon: number) =>
  j<{ cameras: any[] }>(`/api/cameras?lat=${lat}&lon=${lon}&n=3`).then((d) => d.cameras);

export const getCounty = (lat: number, lon: number) =>
  j<{ county: string; state: string }>(`/api/county?lat=${lat}&lon=${lon}`);

export const getAircraft = (lat: number, lon: number) =>
  j<{ aircraft: any[] }>(`/api/aircraft?lat=${lat}&lon=${lon}`).then((d) => d.aircraft || []);

export const getTrains = (lat: number, lon: number) =>
  j<{ trains: any[] }>(`/api/trains?lat=${lat}&lon=${lon}`).then((d) => d.trains || []);
