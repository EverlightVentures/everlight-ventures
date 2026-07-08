export type Incident = {
  id: string;
  source: string;
  type?: string;
  title?: string;
  body?: string;
  lat?: number | null;
  lon?: number | null;
  geo_label?: string;
  severity?: string;
  threat_level: string;
  distance_mi?: number | null;
  status?: string;
  last_seen?: string;
  first_seen?: string;
  audio_url?: string;
  confidence?: number;
  tier?: string;
  sources?: string[];
  units?: string[];
  inferred?: boolean;
};

export type SpaceWx = { kp: number | null; level: string; gps: string; alert: boolean };

export type Aircraft = {
  id: string; flight?: string; lat: number; lon: number; alt?: number;
  speed?: number; track?: number; type?: string; kind?: string; emergency?: boolean;
};

export type Train = {
  id: string; num?: string; route?: string; lat: number; lon: number;
  heading?: number; speed?: number; state?: string; distance_mi?: number;
};

export const THREAT_COLORS: Record<string, string> = {
  EXTREME: "#ff2d2d",
  HIGH: "#ff8c1a",
  MEDIUM: "#ffd21a",
  LOW: "#D4AF37",
  LOG: "#8a8a8a",
};

export const THREAT_RANK: Record<string, number> = {
  EXTREME: 4, HIGH: 3, MEDIUM: 2, LOW: 1, LOG: 0,
};
