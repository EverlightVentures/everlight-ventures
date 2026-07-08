"use client";
import Map, { Marker } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";

const MINI_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    sat: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
    },
  },
  layers: [{ id: "sat", type: "raster", source: "sat" }],
};

// PiP "you are here" inset. Non-interactive + low weight; re-centers when the
// operator moves a meaningful distance (keyed on 3-decimal coords ~ a block).
export default function MiniMap({ lat, lon }: { lat: number; lon: number }) {
  return (
    <div
      className="glass"
      style={{
        position: "absolute", bottom: 120, right: 12, width: 148, height: 148,
        borderRadius: 12, overflow: "hidden", zIndex: 16, border: "1px solid var(--line)",
      }}
    >
      <Map
        key={`${lat.toFixed(3)},${lon.toFixed(3)}`}
        initialViewState={{ longitude: lon, latitude: lat, zoom: 14 }}
        mapStyle={MINI_STYLE}
        interactive={false}
        attributionControl={false}
        style={{ width: "100%", height: "100%" }}
      >
        <Marker longitude={lon} latitude={lat}>
          <div
            style={{
              width: 14, height: 14, borderRadius: "50%", background: "#2ecc71",
              border: "2px solid #fff", boxShadow: "0 0 8px #2ecc71",
            }}
          />
        </Marker>
      </Map>
      <div style={{ position: "absolute", top: 4, left: 7, fontSize: 10, color: "#fff", textShadow: "0 0 3px #000", fontWeight: 700, letterSpacing: 0.5 }}>
        YOU
      </div>
    </div>
  );
}
