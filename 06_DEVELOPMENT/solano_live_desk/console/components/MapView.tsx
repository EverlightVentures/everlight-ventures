"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Marker } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Incident, Aircraft, Train } from "@/lib/types";
import { THREAT_COLORS } from "@/lib/types";

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

// Dead-reckon aircraft between polls: advance each along its heading/speed so it
// glides smoothly instead of jumping. Throttled to ~7fps to stay light on phones.
function useGlide(aircraft: Aircraft[]): Aircraft[] {
  const [frame, setFrame] = useState<Aircraft[]>(aircraft);
  const truth = useRef<{ list: Aircraft[]; t: number }>({ list: aircraft, t: 0 });
  useEffect(() => {
    truth.current = { list: aircraft, t: performance.now() };
    setFrame(aircraft);
  }, [aircraft]);
  useEffect(() => {
    let raf = 0;
    let last = 0;
    const tick = (now: number) => {
      if (now - last > 150) {
        last = now;
        const dt = (now - truth.current.t) / 1000; // seconds since last truth
        setFrame(
          truth.current.list.map((a) => {
            if (a.speed == null || a.track == null) return a;
            const distDeg = ((a.speed * dt) / 3600) / 60; // knots*s -> nm -> deg
            const rad = (a.track * Math.PI) / 180;
            return {
              ...a,
              lat: a.lat + distDeg * Math.cos(rad),
              lon: a.lon + (distDeg * Math.sin(rad)) / Math.cos((a.lat * Math.PI) / 180),
            };
          })
        );
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return frame;
}

export default function MapView({
  incidents, fused, aircraft, trains, selectedId, onSelect,
}: {
  incidents: Incident[];
  fused: Incident[];
  aircraft: Aircraft[];
  trains: Train[];
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
}) {
  const pins = useMemo(() => incidents.filter((e) => e.lat != null && e.lon != null), [incidents]);
  const planes = useGlide(aircraft).slice(0, 80); // cap for phone perf

  return (
    <Map
      initialViewState={{ longitude: -121.98, latitude: 38.25, zoom: 9, pitch: 45, bearing: 0 }}
      mapStyle={SAT_STYLE}
      maxPitch={75}
      attributionControl={false}
      style={{ position: "absolute", inset: 0 }}
    >
      {trains.map((t) => (
        <Marker key={t.id} longitude={t.lon} latitude={t.lat}>
          <div title={`${t.route || "train"} ${t.num || ""}`} style={{ fontSize: 16, filter: "drop-shadow(0 0 3px #000)" }}>
            &#128646;
          </div>
        </Marker>
      ))}
      {planes.map((a) => (
        <Marker key={a.id} longitude={a.lon} latitude={a.lat}>
          <div
            title={`${a.flight || a.id} ${a.alt ? a.alt + "ft" : ""}`}
            style={{
              color: a.emergency ? "#ff2d2d" : a.kind === "mil" ? "#ffd21a" : "#8fe3ff",
              fontSize: 13,
              transform: `rotate(${(a.track ?? 0)}deg)`,
              textShadow: "0 0 4px #000",
            }}
          >
            &#9650;
          </div>
        </Marker>
      ))}
      {fused
        .filter((f) => f.lat != null)
        .map((f) => (
          <Marker key={f.id} longitude={f.lon!} latitude={f.lat!} onClick={(e) => { e.originalEvent.stopPropagation(); onSelect(f); }}>
            <div
              className={f.inferred ? "pulse" : undefined}
              style={{
                color: THREAT_COLORS[f.threat_level] || "#D4AF37",
                fontSize: (f.confidence ?? 0) >= 0.8 ? 26 : 20,
                cursor: "pointer",
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
