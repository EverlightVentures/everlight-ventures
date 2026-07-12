"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Marker, Source, Layer, Popup } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Incident, Aircraft, Train } from "@/lib/types";
import { THREAT_COLORS, THREAT_RANK } from "@/lib/types";
import LiveVideo from "@/components/LiveVideo";
import { getFlight } from "@/lib/api";
import { ageOpacity, categoryGlyph } from "@/lib/util";

// Geodesic ring polygon (miles) around a point, for the proximity rings.
function ringGeo(lat: number, lon: number, miles: number) {
  const pts: [number, number][] = [];
  const R = 3958.8;
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * 2 * Math.PI;
    const dLat = ((miles / R) * Math.cos(a) * 180) / Math.PI;
    const dLon = ((miles / R) * Math.sin(a) * 180) / Math.PI / Math.cos((lat * Math.PI) / 180);
    pts.push([lon + dLon, lat + dLat]);
  }
  return { type: "Feature" as const, geometry: { type: "LineString" as const, coordinates: pts }, properties: {} };
}

const SAFE_ICON: Record<string, string> = {
  police: "\u{1F693}", hospital: "\u{1F3E5}", fire: "\u{1F692}",
  shelter: "\u{1F3E0}", pharmacy: "\u{1F48A}",
};

function Row({ k, v }: { k: string; v: any }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 12, color: "var(--text)" }}>
      <span style={{ color: "var(--muted)" }}>{k}</span>
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
      <div style={{ minWidth: 184, color: "var(--text)" }}>
        <div style={{ fontWeight: 700 }}>&#9992; {d.flight || d.id}{d.kind === "mil" ? " (military)" : ""}</div>
        <Row k="Altitude" v={d.alt ? `${d.alt.toLocaleString()} ft` : "?"} />
        <Row k="Speed" v={d.speed ? `${Math.round(d.speed)} kt` : "?"} />
        <Row k="Heading" v={d.track != null ? `${Math.round(d.track)}°` : "?"} />
        <Row k="Type" v={d.type || "?"} />
        {d.squawk ? <Row k="Squawk" v={d.squawk} /> : null}
        {d.emergency ? <div style={{ color: "#c00", fontWeight: 700, fontSize: 12 }}>EMERGENCY</div> : null}
        <div style={{ marginTop: 6, borderTop: "1px solid var(--line)", paddingTop: 4 }}>
          {!route ? (
            <div style={{ fontSize: 11, color: "var(--muted)" }}>looking up flight&hellip;</div>
          ) : (
            <>
              {route.airline ? <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>{route.airline}</div> : null}
              {route.origin || route.dest ? (
                <div style={{ fontWeight: 600 }}>
                  {route.origin?.city || route.origin?.code || "?"} &rarr; {route.dest?.city || route.dest?.code || "?"}
                </div>
              ) : (
                <div style={{ fontSize: 11, color: "var(--muted)" }}>route not published</div>
              )}
              {route.seats ? (
                <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                  &asymp;{route.est_pax} aboard of {route.seats} ({d.type}, est. ~83% load)
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    );
  }
  if (poi.kind === "train") {
    return (
      <div style={{ minWidth: 150, color: "var(--text)" }}>
        <div style={{ fontWeight: 700 }}>&#128646; {d.route || "Train"} {d.num || ""}</div>
        <Row k="Status" v={d.state || "?"} />
        <Row k="Speed" v={d.speed != null ? `${Math.round(d.speed)} mph` : "?"} />
        {d.distance_mi != null ? <Row k="Distance" v={`${d.distance_mi} mi`} /> : null}
      </div>
    );
  }
  if (poi.kind === "safe") {
    return (
      <div style={{ minWidth: 160, color: "var(--text)" }}>
        <div style={{ fontWeight: 700 }}>{SAFE_ICON[d.kind] || "\u{1F3E5}"} {d.name}</div>
        <Row k="Type" v={d.kind} />
        <Row k="Distance" v={`${d.distance_mi} mi`} />
        <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>safe haven &middot; open to the public</div>
      </div>
    );
  }
  if (poi.kind === "bus") {
    return (
      <div style={{ minWidth: 130, color: "var(--text)" }}>
        <div style={{ fontWeight: 700 }}>&#128652; {d.route || "Transit"}</div>
        {d.speed != null ? <Row k="Speed" v={`${Math.round(d.speed)} mph`} /> : null}
      </div>
    );
  }
  if (poi.kind === "social") {
    return (
      <div style={{ minWidth: 200, maxWidth: 260, color: "var(--text)" }}>
        <div style={{ fontWeight: 700 }}>&#128293; {d.city} &middot; {d.count} safety post{d.count !== 1 ? "s" : ""}</div>
        {(d.posts || []).slice(0, 4).map((p: any, i: number) => (
          <a key={i} href={p.url} target="_blank" rel="noreferrer" style={{ display: "block", fontSize: 11, marginTop: 4, color: "#7fd1ff", textDecoration: "none" }}>
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
  incidents, fused, aircraft, trains, layers, rankMap, userPos, showRings, linkFrom, linkTargets, escape, selectedId, onSelect,
}: {
  incidents: Incident[];
  fused: Incident[];
  aircraft: Aircraft[];
  trains: Train[];
  layers: Layers;
  rankMap: Record<string, number>;
  userPos: { lat: number; lon: number } | null;
  showRings: boolean;
  linkFrom: { lat: number; lon: number } | null;
  linkTargets: any[];
  escape?: { dest?: any; routes?: any[]; error?: string } | null;
  selectedId: string | null;
  onSelect: (ev: Incident) => void;
}) {
  const pins = useMemo(() => incidents.filter((e) => e.lat != null && e.lon != null), [incidents]);
  const planes = useGlide(aircraft).slice(0, 80); // cap for phone perf
  const [openCam, setOpenCam] = useState<any>(null);
  const [poi, setPoi] = useState<{ kind: string; data: any } | null>(null);
  const [zoom, setZoom] = useState(9);
  const [follow, setFollow] = useState(true);
  const mapRef = useRef<any>(null);
  const didCenter = useRef(false);
  const { clusters, singles } = useMemo(() => clusterPins(pins, zoom), [pins, zoom]);

  // Center on the operator: snap in on the first GPS fix, then track live while
  // "follow" is on (turned off the moment they pan the map by hand).
  useEffect(() => {
    if (!userPos || !mapRef.current) return;
    if (!follow && didCenter.current) return;
    mapRef.current.flyTo({
      center: [userPos.lon, userPos.lat],
      zoom: didCenter.current ? (mapRef.current.getZoom?.() ?? 13.5) : 13.5,
      duration: didCenter.current ? 700 : 1500,
      essential: true,
    });
    didCenter.current = true;
  }, [userPos, follow]);

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
    <>
    <Map
      ref={mapRef}
      initialViewState={{ longitude: userPos?.lon ?? -121.98, latitude: userPos?.lat ?? 38.25, zoom: userPos ? 13.5 : 9, pitch: 45, bearing: 0 }}
      mapStyle={SAT_STYLE}
      maxPitch={75}
      attributionControl={false}
      onMoveEnd={(e) => setZoom(e.viewState.zoom)}
      onDragStart={() => setFollow(false)}
      style={{ position: "absolute", inset: 0 }}
    >
      {linkFrom && linkTargets.length > 0 && (
        <Source
          id="links"
          type="geojson"
          data={{
            type: "FeatureCollection",
            features: linkTargets.filter((t) => t.lat != null && t.lon != null).map((t) => ({
              type: "Feature",
              geometry: { type: "LineString", coordinates: [[linkFrom.lon, linkFrom.lat], [t.lon, t.lat]] },
              properties: {},
            })),
          }}
        >
          <Layer id="links" type="line" paint={{ "line-color": "#8fe3a8", "line-width": 2, "line-dasharray": [1, 1.5], "line-opacity": 0.75 }} />
        </Source>
      )}
      {showRings && userPos && [5, 10, 25].map((mi) => (
        <Source key={"ring" + mi} id={"ring" + mi} type="geojson" data={ringGeo(userPos.lat, userPos.lon, mi)}>
          <Layer id={"ring" + mi} type="line" paint={{ "line-color": "#7fd1ff", "line-width": 1, "line-dasharray": [2, 3], "line-opacity": 0.5 }} />
        </Source>
      ))}
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
      {escape?.routes?.length ? (
        // Dispersed Egress: alternates first, recommended drawn last so it sits on top.
        [...escape.routes]
          .map((r, idx) => ({ r, idx }))
          .sort((a, b) => (a.r.recommended ? 1 : 0) - (b.r.recommended ? 1 : 0))
          .map(({ r, idx }) => (
            <Source key={"esc" + idx} id={"esc" + idx} type="geojson" data={{ type: "Feature", geometry: r.geometry, properties: {} }}>
              <Layer
                id={"esc" + idx}
                type="line"
                paint={{
                  "line-color": r.recommended ? "#39ff88" : r.blocked ? "#ff4d4d" : "#ffb454",
                  "line-width": r.recommended ? 6 : 3,
                  "line-opacity": r.recommended ? 0.95 : 0.6,
                  ...(r.recommended ? {} : { "line-dasharray": [2, 2] }),
                }}
              />
            </Source>
          ))
      ) : null}
      {escape?.dest && (
        <Marker longitude={escape.dest.lon} latitude={escape.dest.lat}>
          <div title={escape.dest.name} style={{ fontSize: 20, filter: "drop-shadow(0 0 4px #000)" }}>{"\u{1F3C1}"}</div>
        </Marker>
      )}
      {(layers.safe || []).map((s, i) => (
        <Marker key={"safe" + i} longitude={s.lon} latitude={s.lat} onClick={(e) => {
          e.originalEvent.stopPropagation();
          onSelect({
            id: "safe-" + (s.name || i), type: s.name || "Safe haven", source: "safe",
            threat_level: "LOG", lat: s.lat, lon: s.lon,
            geo_label: s.kind + (s.distance_mi != null ? " · " + s.distance_mi + " mi" : ""),
            last_seen: new Date().toISOString(), _kind: "safe", safeData: s,
          } as any);
        }}>
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
        const hot = h.hot ?? h.count >= 4;
        return (
          <Marker key={"hot" + i} longitude={h.lon} latitude={h.lat} onClick={(e) => {
            e.originalEvent.stopPropagation();
            // A hotspot IS an alert -> open the full drawer, not a popup.
            onSelect({
              id: "social-" + h.city, type: "Social hotspot: " + h.city, source: "reddit",
              threat_level: hot ? "HIGH" : "MEDIUM", severity: h.count, lat: h.lat, lon: h.lon,
              geo_label: h.city + " · " + h.count + " safety post" + (h.count !== 1 ? "s" : ""),
              last_seen: new Date().toISOString(), first_seen: new Date().toISOString(),
              posts: h.posts, _kind: "social",
            } as any);
          }}>
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
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>{openCam.name} {openCam.stream_url ? "· LIVE" : "· still"}</div>
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
        <Marker key={a.id} longitude={a.lon} latitude={a.lat} onClick={(e) => {
          e.originalEvent.stopPropagation();
          onSelect({
            id: "plane-" + (a.flight || a.id), type: "Flight " + (a.flight || a.id),
            source: "adsb", threat_level: a.emergency ? "HIGH" : "LOG", lat: a.lat, lon: a.lon,
            geo_label: (a.type || "aircraft") + (a.alt ? " · " + a.alt.toLocaleString() + " ft" : ""),
            last_seen: new Date().toISOString(), _kind: "plane", planeData: a,
          } as any);
        }}>
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
        const sel = ev.id === selectedId;
        const color = THREAT_COLORS[ev.threat_level] || "#D4AF37";
        const glyph = categoryGlyph(ev.type);
        const t = ev.last_seen ? new Date(ev.last_seen).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "";
        return (
          <Marker key={ev.id} longitude={ev.lon!} latitude={ev.lat!} onClick={(e) => { e.originalEvent.stopPropagation(); onSelect(ev); }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: sel ? 1 : ageOpacity(ev.last_seen) }}>
              <div
                style={{
                  width: sel ? 26 : 21, height: sel ? 26 : 21, borderRadius: "50%",
                  background: "rgba(9,9,12,0.82)",
                  border: `2px solid ${sel ? "#fff" : color}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: glyph ? 12 : 9, color, fontWeight: 700, cursor: "pointer",
                  boxShadow: `0 1px 4px rgba(0,0,0,0.55), 0 0 ${crit || sel ? 9 : 3}px ${color}`,
                  ...(crit && !sel ? { animation: "critglow 1.5s ease-in-out infinite", ["--gc" as any]: color } : {}),
                }}
              >
                {glyph || "●"}
              </div>
              {zoom >= 11 && (
                <div
                  style={{
                    marginTop: 2, fontSize: 9, lineHeight: 1.15, color: "#fff",
                    background: "rgba(0,0,0,0.6)", padding: "1px 5px", borderRadius: 4,
                    whiteSpace: "nowrap", maxWidth: 140, overflow: "hidden",
                    textOverflow: "ellipsis", textShadow: "0 0 2px #000",
                  }}
                >
                  #{rank} {(ev.type || "incident").slice(0, 16)} &middot; {t}
                </div>
              )}
            </div>
          </Marker>
        );
      })}
      {userPos && (
        <Marker longitude={userPos.lon} latitude={userPos.lat} anchor="center">
          <div style={{ position: "relative", width: 20, height: 20 }}>
            <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "#2f9bff", opacity: 0.35, animation: "ring 2s ease-out infinite" }} />
            <div style={{ position: "absolute", top: 5, left: 5, width: 10, height: 10, borderRadius: "50%", background: "#2f9bff", border: "2px solid #fff", boxShadow: "0 0 8px #2f9bff" }} />
          </div>
        </Marker>
      )}
    </Map>
      <button
        onClick={() => { setFollow(true); if (userPos && mapRef.current) mapRef.current.flyTo({ center: [userPos.lon, userPos.lat], zoom: 13.5, duration: 700, essential: true }); }}
        title={follow ? "following you" : "recenter on me"}
        className="glass"
        style={{
          position: "absolute", bottom: 118, right: 12, zIndex: 16, width: 40, height: 40,
          borderRadius: "50%", border: `1px solid ${follow ? "#2f9bff" : "var(--line)"}`,
          color: follow ? "#2f9bff" : "var(--text)", fontSize: 18, cursor: "pointer", lineHeight: 1,
        }}
      >
        {"◉"}
      </button>
    </>
  );
}
