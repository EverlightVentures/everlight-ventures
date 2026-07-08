"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Marker, Source, Layer, Popup } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Incident, Aircraft, Train } from "@/lib/types";
import { THREAT_COLORS, THREAT_RANK } from "@/lib/types";
import LiveVideo from "@/components/LiveVideo";

// Grid-cluster pins when zoomed out so a dense area reads as one count bubble.
function clusterPins(items: Incident[], zoom: number) {
  if (zoom >= 11) return { clusters: [] as any[], singles: items };
  const cell = zoom < 8 ? 0.3 : zoom < 10 ? 0.09 : 0.035;
  const grid: Record<string, Incident[]> = {};
  for (const e of items) {
    const key = `${Math.round(e.lat! / cell)},${Math.round(e.lon! / cell)}`;
    (grid[key] ||= []).push(e);
  }
  const clusters: any[] = [];
  const singles: Incident[] = [];
  for (const k in grid) {
    const g = grid[k];
    if (g.length >= 3) {
      clusters.push({
        key: k,
        count: g.length,
        lat: g.reduce((s, e) => s + e.lat!, 0) / g.length,
        lon: g.reduce((s, e) => s + e.lon!, 0) / g.length,
        top: g.reduce((a, e) => (THREAT_RANK[e.threat_level] > THREAT_RANK[a] ? e.threat_level : a), "LOG"),
      });
    } else {
      singles.push(...g);
    }
  }
  return { clusters, singles };
}

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
    // OpenMapTiles vector schema (free) -- used only for 3D building footprints.
    omt: { type: "vector", url: "https://tiles.openfreemap.org/planet" },
  },
  layers: [
    { id: "sat", type: "raster", source: "sat" },
    { id: "ref", type: "raster", source: "ref", paint: { "raster-opacity": 0.85 } },
    // 3D building extrusion (appears when you zoom in + tilt).
    {
      id: "buildings3d",
      type: "fill-extrusion",
      source: "omt",
      "source-layer": "building",
      minzoom: 14,
      paint: {
        "fill-extrusion-color": "#2b2b33",
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], 6],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.72,
      },
    },
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

export type Layers = {
  evac?: any;
  danger?: any;
  safe?: any[];
  buses?: any[];
  route?: any;
  cams?: any[];
};

export default function MapView({
  incidents, fused, aircraft, trains, layers, selectedId, onSelect,
}: {
  incidents: Incident[];
  fused: Incident[];
  aircraft: Aircraft[];
  trains: Train[];
  layers: Layers;
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
}) {
  const pins = useMemo(() => incidents.filter((e) => e.lat != null && e.lon != null), [incidents]);
  const planes = useGlide(aircraft).slice(0, 80); // cap for phone perf
  const [openCam, setOpenCam] = useState<any>(null);
  const [zoom, setZoom] = useState(9);
  const mapRef = useRef<any>(null);
  const { clusters, singles } = useMemo(() => clusterPins(pins, zoom), [pins, zoom]);
  // Rank pins by recency: newest incident is #1.
  const rankMap = useMemo(() => {
    const m: Record<string, number> = {};
    [...pins]
      .sort((a, b) => (Date.parse(b.last_seen || "") || 0) - (Date.parse(a.last_seen || "") || 0))
      .forEach((e, i) => { m[e.id] = i + 1; });
    return m;
  }, [pins]);

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: -121.98, latitude: 38.25, zoom: 9, pitch: 45, bearing: 0 }}
      mapStyle={SAT_STYLE}
      maxPitch={75}
      attributionControl={false}
      onMoveEnd={(e) => setZoom(e.viewState.zoom)}
      style={{ position: "absolute", inset: 0 }}
    >
      {layers.evac && (
        <Source id="evac" type="geojson" data={layers.evac}>
          <Layer id="evac-fill" type="fill" paint={{ "fill-color": "#ff8c1a", "fill-opacity": 0.16 }} />
          <Layer id="evac-line" type="line" paint={{ "line-color": "#ff8c1a", "line-width": 1.5 }} />
        </Source>
      )}
      {layers.danger && (
        <Source id="danger" type="geojson" data={layers.danger}>
          <Layer id="danger-fill" type="fill" filter={["==", "$type", "Polygon"]} paint={{ "fill-color": "#ff2d2d", "fill-opacity": 0.22 }} />
          <Layer id="danger-pt" type="circle" filter={["==", "$type", "Point"]} paint={{ "circle-radius": 6, "circle-color": "#ff2d2d", "circle-opacity": 0.5 }} />
        </Source>
      )}
      {layers.route?.route && (
        <Source id="route" type="geojson" data={{ type: "Feature", geometry: layers.route.route, properties: {} }}>
          <Layer id="route-line" type="line" paint={{ "line-color": "#2ecc71", "line-width": 5, "line-opacity": 0.9 }} />
        </Source>
      )}
      {(layers.safe || []).map((s, i) => (
        <Marker key={"safe" + i} longitude={s.lon} latitude={s.lat}>
          <div title={`${s.name || "safe"} (${s.kind || ""})`} style={{ fontSize: 15, filter: "drop-shadow(0 0 3px #000)" }}>&#127973;</div>
        </Marker>
      ))}
      {(layers.buses || []).map((b, i) => (
        <Marker key={"bus" + i} longitude={b.lon} latitude={b.lat}>
          <div title={b.route || "bus"} style={{ fontSize: 12, filter: "drop-shadow(0 0 2px #000)" }}>&#128652;</div>
        </Marker>
      ))}
      {(layers.cams || []).map((cm, i) => (
        <Marker key={"cam" + i} longitude={cm.lon} latitude={cm.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setOpenCam(cm); }}>
          <div title={cm.name || "camera"} style={{ fontSize: 14, cursor: "pointer", filter: "drop-shadow(0 0 2px #000)" }}>&#128247;</div>
        </Marker>
      ))}
      {openCam && (
        <Popup longitude={openCam.lon} latitude={openCam.lat} anchor="bottom" maxWidth="300px" onClose={() => setOpenCam(null)} closeOnClick={false}>
          <div style={{ width: 260 }}>
            {openCam.stream_url ? (
              <LiveVideo src={openCam.stream_url} />
            ) : openCam.image_url ? (
              <img src={`${openCam.image_url}${openCam.image_url.includes("?") ? "&" : "?"}t=${Date.now()}`} alt="" style={{ width: "100%", borderRadius: 6 }} />
            ) : (
              <div style={{ fontSize: 12 }}>no feed</div>
            )}
            <div style={{ fontSize: 11, color: "#333", marginTop: 4 }}>{openCam.name} {openCam.stream_url ? "· LIVE" : "· still"}</div>
          </div>
        </Popup>
      )}
      {layers.route?.dest && (
        <Marker longitude={layers.route.dest.lon} latitude={layers.route.dest.lat}>
          <div title={layers.route.dest.name} style={{ fontSize: 18 }}>&#128205;</div>
        </Marker>
      )}
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
      {clusters.map((c) => (
        <Marker
          key={"cl" + c.key}
          longitude={c.lon}
          latitude={c.lat}
          onClick={(e) => { e.originalEvent.stopPropagation(); mapRef.current?.flyTo({ center: [c.lon, c.lat], zoom: Math.min(zoom + 3, 13) }); }}
        >
          <div
            style={{
              background: THREAT_COLORS[c.top] || "#D4AF37", color: "#08080a", fontWeight: 700,
              borderRadius: "50%", width: 34, height: 34, display: "flex", alignItems: "center",
              justifyContent: "center", border: "2px solid #08080a", cursor: "pointer", fontSize: 13,
              boxShadow: "0 0 0 3px rgba(212,175,55,0.35)",
            }}
          >
            {c.count}
          </div>
        </Marker>
      ))}
      {singles.map((ev) => {
        const crit = ev.threat_level === "EXTREME" || ev.threat_level === "HIGH";
        const rank = rankMap[ev.id];
        const t = ev.last_seen ? new Date(ev.last_seen).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "";
        return (
          <Marker key={ev.id} longitude={ev.lon!} latitude={ev.lat!} onClick={(e) => { e.originalEvent.stopPropagation(); onSelect(ev); }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                className="mk"
                style={{
                  background: THREAT_COLORS[ev.threat_level] || "#D4AF37",
                  borderColor: ev.id === selectedId ? "#fff" : "rgba(0,0,0,0.6)",
                  fontSize: rank > 99 ? 9 : 11,
                  ...(crit
                    ? { animation: "critglow 1.4s ease-in-out infinite", ["--gc" as any]: THREAT_COLORS[ev.threat_level] }
                    : {}),
                }}
              >
                {rank}
              </div>
              {zoom >= 11 && (
                <div
                  style={{
                    marginTop: 2, fontSize: 9, lineHeight: 1.15, color: "#fff",
                    background: "rgba(0,0,0,0.62)", padding: "1px 4px", borderRadius: 3,
                    whiteSpace: "nowrap", maxWidth: 132, overflow: "hidden",
                    textOverflow: "ellipsis", textShadow: "0 0 2px #000",
                  }}
                >
                  {(ev.type || "incident").slice(0, 20)} &middot; {t}
                </div>
              )}
            </div>
          </Marker>
        );
      })}
    </Map>
  );
}
