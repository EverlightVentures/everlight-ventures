"use client";
import { useMemo } from "react";
import Map, { Marker, Source, Layer } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Incident } from "@/lib/types";
import { THREAT_COLORS } from "@/lib/types";

// Satellite imagery + a place/road label overlay (free Esri tiles, no token).
const SAT_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    sat: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "Imagery: Esri, Maxar",
    },
    ref: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
    },
  },
  layers: [
    { id: "sat", type: "raster", source: "sat" },
    { id: "ref", type: "raster", source: "ref", paint: { "raster-opacity": 0.85 } },
  ],
};

export default function MapView({
  incidents,
  fused,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  fused: Incident[];
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
}) {
  const pins = useMemo(() => incidents.filter((e) => e.lat != null && e.lon != null), [incidents]);
  return (
    <Map
      initialViewState={{ longitude: -121.98, latitude: 38.25, zoom: 9, pitch: 45, bearing: 0 }}
      mapStyle={SAT_STYLE}
      maxPitch={75}
      attributionControl={false}
      style={{ position: "absolute", inset: 0 }}
    >
      {fused
        .filter((f) => f.lat != null)
        .map((f) => (
          <Marker key={f.id} longitude={f.lon!} latitude={f.lat!} onClick={(e) => { e.originalEvent.stopPropagation(); onSelect(f); }}>
            <div
              className={f.inferred ? "mk pulse" : "mk"}
              style={{
                background: "transparent",
                color: THREAT_COLORS[f.threat_level] || "#D4AF37",
                fontSize: (f.confidence ?? 0) >= 0.8 ? 26 : 20,
                border: "none",
                boxShadow: "none",
                textShadow: `0 0 8px ${THREAT_COLORS[f.threat_level] || "#D4AF37"}`,
              }}
            >
              &#9670;
            </div>
          </Marker>
        ))}
      {pins.map((ev) => (
        <Marker key={ev.id} longitude={ev.lon!} latitude={ev.lat!} onClick={(e) => { e.originalEvent.stopPropagation(); onSelect(ev); }}>
          <div
            className="mk"
            style={{
              background: THREAT_COLORS[ev.threat_level] || "#D4AF37",
              borderColor: ev.id === selectedId ? "#fff" : "rgba(0,0,0,0.6)",
            }}
          >
            !
          </div>
        </Marker>
      ))}
    </Map>
  );
}
