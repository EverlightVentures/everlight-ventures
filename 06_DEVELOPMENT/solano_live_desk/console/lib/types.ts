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
