"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Marker, Source, Layer, Popup } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Incident, Aircraft, Train } from "@/lib/types";
import { THREAT_COLORS, THREAT_RANK } from "@/lib/types";
import LiveVideo from "@/components/LiveVideo";
import { getFlight } from "@/lib/api";

const SAFE_ICON: Record<string, string> = {
  police: "\u{1F693}", hospital: "\u{1F3E5}", fire: "\u{1F692}",
  shelter: "\u{1F3E0}", pharmacy: "\u{1F48A}",
};

function Row({ k, v }: { k: string; v: any }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 12, color: "#333" }}>
      <span style={{ color: "#777" }}>{k}</span>
      <span style={{ fontWeight: 600 }}>{v}</span>
    </div>
  );
}

// One detail card for any non-incident marker; planes get live route lookup.
function PoiCard({ poi }: { poi: { kind: string; data: any } }) {
  const [route, setRoute] = useState<any>(null);
  useEffect(() => {
    setRoute(null);
    if (poi.kind === "plane" && poi.data.flight) getFlight(poi.data.flight, poi.data.type).then(setRoute).catch(() => {});
  }, [poi]);
  const d = poi.data;
  if (poi.kind === "plane") {
    return (
      <div style={{ minWidth: 184, color: "#111" }}>
        <div style={{ fontWeight: 700 }}>&#9992; {d.flight || d.id}{d.kind === "mil" ? " (military)" : ""}</div>
        <Row k="Altitude" v={d.alt ? `${d.alt.toLocaleString()} ft` : "?"} />
        <Row k="Speed" v={d.speed ? `${Math.round(d.speed)} kt` : "?"} />
        <Row k="Heading" v={d.track != null ? `${Math.round(d.track)}°` : "?"} />
        <Row k="Type" v={d.type || "?"} />
        {d.squawk ? <Row k="Squawk" v={d.squawk} /> : null}
        {d.emergency ? <div style={{ color: "#c00", fontWeight: 700, fontSize: 12 }}>EMERGENCY</div> : null}
        <div style={{ marginTop: 6, borderTop: "1px solid #ddd", paddingTop: 4 }}>
          {!route ? (
            <div style={{ fontSize: 11, color: "#888" }}>looking up flight&hellip;</div>
          ) : (
            <>
              {route.airline ? <div style={{ fontSize: 11, color: "#666", fontWeight: 600 }}>{route.airline}</div> : null}
              {route.origin || route.dest ? (
                <div style={{ fontWeight: 600 }}>
                  {route.origin?.city || route.origin?.code || "?"} &rarr; {route.dest?.city || route.dest?.code || "?"}
                </div>
              ) : (
                <div style={{ fontSize: 11, color: "#888" }}>route not published</div>
              )}
              {route.seats ? (
                <div style={{ fontSize: 11, color: "#555", marginTop: 2 }}>~{route.seats} seats ({d.type}) &middot; live occupancy not broadcast</div>
              ) : null}
            </>
          )}
        </div>
      </div>
    );
  }
  if (poi.kind === "train") {
    return (
      <div style={{ minWidth: 150, color: "#111" }}>
        <div style={{ fontWeight: 700 }}>&#128646; {d.route || "Train"} {d.num || ""}</div>
        <Row k="Status" v={d.state || "?"} />
        <Row k="Speed" v={d.speed != null ? `${Math.round(d.speed)} mph` : "?"} />
        {d.distance_mi != null ? <Row k="Distance" v={`${d.distance_mi} mi`} /> : null}
      </div>
    );
  }
  if (poi.kind === "safe") {
    return (
      <div style={{ minWidth: 160, color: "#111" }}>
        <div style={{ fontWeight: 700 }}>{SAFE_ICON[d.kind] || "\u{1F3E5}"} {d.name}</div>
        <Row k="Type" v={d.kind} />
        <Row k="Distance" v={`${d.distance_mi} mi`} />
        <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>safe haven &middot; open to the public</div>
      </div>
    );
  }
  if (poi.kind === "bus") {
    return (
      <div style={{ minWidth: 130, color: "#111" }}>
        <div style={{ fontWeight: 700 }}>&#128652; {d.route || "Transit"}</div>
        {d.speed != null ? <Row k="Speed" v={`${Math.round(d.speed)} mph`} /> : null}
      </div>
    );
  }
  if (poi.kind === "social") {
    return (
      <div style={{ minWidth: 200, maxWidth: 260, color: "#111" }}>
        <div style={{ fontWeight: 700 }}>&#128293; {d.city} &middot; {d.count} safety post{d.count !== 1 ? "s" : ""}</div>
        {(d.posts || []).slice(0, 4).map((p: any, i: number) => (
          <a key={i} href={p.url} target="_blank" rel="noreferrer" style={{ display: "block", fontSize: 11, marginTop: 4, color: "#1a4b8c", textDecoration: "none" }}>
            {(p.title || "").slice(0, 82)}
          </a>
        ))}
      </div>
    );
  }
  return null;
}

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
  socialHot?: any[];
};

export default function MapView({
  incidents, fused, aircraft, trains, layers, rankMap, selectedId, onSelect,
}: {
  incidents: Incident[];
  fused: Incident[];
  aircraft: Aircraft[];
  trains: Train[];
  layers: Layers;
  rankMap: Record<string, number>;
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
}) {
  const pins = useMemo(() => incidents.filter((e) => e.lat != null && e.lon != null), [incidents]);
  const planes = useGlide(aircraft).slice(0, 80); // cap for phone perf
  const [openCam, setOpenCam] = useState<any>(null);
  const [poi, setPoi] = useState<{ kind: string; data: any } | null>(null);
  const [zoom, setZoom] = useState(9);
  const mapRef = useRef<any>(null);
  const { clusters, singles } = useMemo(() => clusterPins(pins, zoom), [pins, zoom]);

  // Selecting an incident (from the alarm queue or the map) sweeps the map to it.
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const ev = incidents.find((e) => e.id === selectedId);
    if (ev && ev.lat != null && ev.lon != null) {
      mapRef.current.flyTo({
        center: [ev.lon, ev.lat],
        zoom: Math.max(13, mapRef.current.getZoom?.() ?? 13),
        duration: 1400,
        essential: true,
      });
    }
  }, [selectedId, incidents]);

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
        <Marker key={"safe" + i} longitude={s.lon} latitude={s.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setPoi({ kind: "safe", data: s }); }}>
          <div title={`${s.name || "safe"} (${s.kind || ""})`} style={{ fontSize: 15, cursor: "pointer", filter: "drop-shadow(0 0 3px #000)" }}>
            {SAFE_ICON[s.kind] || "\u{1F3E5}"}
          </div>
        </Marker>
      ))}
      {(layers.buses || []).map((b, i) => (
        <Marker key={"bus" + i} longitude={b.lon} latitude={b.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setPoi({ kind: "bus", data: b }); }}>
          <div title={b.route || "bus"} style={{ fontSize: 12, cursor: "pointer", filter: "drop-shadow(0 0 2px #000)" }}>&#128652;</div>
        </Marker>
      ))}
      {(layers.cams || []).map((cm, i) => (
        <Marker key={"cam" + i} longitude={cm.lon} latitude={cm.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setOpenCam(cm); }}>
          <div title={cm.name || "camera"} style={{ fontSize: 14, cursor: "pointer", filter: "drop-shadow(0 0 2px #000)" }}>&#128247;</div>
        </Marker>
      ))}
      {(layers.socialHot || []).map((h, i) => {
        const sz = 22 + Math.min(h.count * 4, 22);
        const hot = h.count >= 3;
        return (
          <Marker key={"hot" + i} longitude={h.lon} latitude={h.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setPoi({ kind: "social", data: h }); }}>
            <div
              title={`${h.city}: ${h.count} safety posts`}
              style={{
                background: hot ? "rgba(255,45,45,0.85)" : "rgba(255,140,26,0.82)", color: "#fff", fontWeight: 700,
                borderRadius: "50%", width: sz, height: sz, display: "flex", alignItems: "center",
                justifyContent: "center", fontSize: 12, border: "2px solid #fff", cursor: "pointer",
                ...(hot ? { animation: "critglow 1.2s ease-in-out infinite", ["--gc" as any]: "#ff2d2d" } : {}),
              }}
            >
              {h.count}
            </div>
          </Marker>
        );
      })}
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
      {poi && poi.data.lat != null && (
        <Popup longitude={poi.data.lon} latitude={poi.data.lat} anchor="bottom" onClose={() => setPoi(null)} closeOnClick={false} maxWidth="264px">
          <PoiCard poi={poi} />
        </Popup>
      )}
      {layers.route?.dest && (
        <Marker longitude={layers.route.dest.lon} latitude={layers.route.dest.lat}>
          <div title={layers.route.dest.name} style={{ fontSize: 18 }}>&#128205;</div>
        </Marker>
      )}
      {trains.map((t) => (
        <Marker key={t.id} longitude={t.lon} latitude={t.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setPoi({ kind: "train", data: t }); }}>
          <div title={`${t.route || "train"} ${t.num || ""}`} style={{ fontSize: 16, cursor: "pointer", filter: "drop-shadow(0 0 3px #000)" }}>
            &#128646;
          </div>
        </Marker>
      ))}
      {planes.map((a) => (
        <Marker key={a.id} longitude={a.lon} latitude={a.lat} onClick={(e) => { e.originalEvent.stopPropagation(); setPoi({ kind: "plane", data: a }); }}>
          <div
            title={`${a.flight || a.id} ${a.alt ? a.alt + "ft" : ""}`}
            style={{
              color: a.emergency ? "#ff2d2d" : a.kind === "mil" ? "#ffd21a" : "#8fe3ff",
              fontSize: 13, cursor: "pointer",
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
                  ...(ev.id === selectedId
                    ? { animation: "critglow 1s ease-in-out infinite", ["--gc" as any]: "#ffffff" }
                    : crit
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
