"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { Incident, SpaceWx, Aircraft, Train } from "@/lib/types";
import type { Layers } from "@/components/MapView";
import type { ToggleKey } from "@/components/Toolbar";
import {
  getEvents, getCorrelated, getSpaceWx, getCounty, getAircraft, getTrains,
  getEvac, getSafePoints, getBuses, getDanger, getRoute, getDays, getMapCameras, getNews, getStats,
  getSocialHotspots, getLinks,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import AlarmQueue from "@/components/AlarmQueue";
import DetailDrawer from "@/components/DetailDrawer";
import Toolbar from "@/components/Toolbar";
import Scrubber from "@/components/Scrubber";
import NewsPanel from "@/components/NewsPanel";
import StatsPanel from "@/components/StatsPanel";
import MiniMap from "@/components/MiniMap";
import FilterBar from "@/components/FilterBar";
import Legend from "@/components/Legend";
import { filterIncidents, EMPTY_FILTERS } from "@/lib/util";
import type { Filters } from "@/lib/util";

// Short alert tone on a brand-new critical incident (WebAudio, no asset).
function playBeep() {
  try {
    const Ctx = (window.AudioContext || (window as any).webkitAudioContext);
    const ctx = new Ctx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "sine";
    g.gain.value = 0.14;
    o.connect(g);
    g.connect(ctx.destination);
    o.frequency.setValueAtTime(880, ctx.currentTime);
    o.frequency.setValueAtTime(620, ctx.currentTime + 0.14);
    o.start();
    o.stop(ctx.currentTime + 0.3);
    setTimeout(() => ctx.close(), 500);
  } catch {
    /* autoplay may be blocked until first interaction */
  }
}

// MapLibre is browser-only -- never render it on the server.
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function Home() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [fused, setFused] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [spacewx, setSpacewx] = useState<SpaceWx | null>(null);
  const [county, setCounty] = useState("");
  const [live, setLive] = useState(false);
  const [pos, setPos] = useState<{ lat: number; lon: number } | null>(null);
  const [aircraft, setAircraft] = useState<Aircraft[]>([]);
  const [trains, setTrains] = useState<Train[]>([]);
  const [layerOn, setLayerOn] = useState<Record<ToggleKey, boolean>>({
    danger: false, evac: false, safe: false, buses: false, route: false, cams: false, social: false, rings: false,
  });
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [filterOpen, setFilterOpen] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [linkTargets, setLinkTargets] = useState<any[]>([]);

  // Fetch link analysis when an incident is selected -> draw connection lines.
  useEffect(() => {
    if (!selected?.id) { setLinkTargets([]); return; }
    getLinks(selected.id)
      .then((d) => setLinkTargets((d.links || []).filter((l: any) => l.lat != null)))
      .catch(() => setLinkTargets([]));
  }, [selected?.id]);
  const [layerData, setLayerData] = useState<Layers>({});
  const [day, setDay] = useState(""); // "" = today/live; else an archived day
  const [days, setDays] = useState<string[]>([]);
  const [alarmOpen, setAlarmOpen] = useState(true);
  const [newsOpen, setNewsOpen] = useState(false);
  const [news, setNews] = useState<any[]>([]);
  const [statsOpen, setStatsOpen] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [muted, setMuted] = useState(false);
  const [scrubT, setScrubT] = useState(100); // 100 = live; lower = replay earlier
  const dayRef = useRef("");
  const seenCrit = useRef<Set<string>>(new Set());
  const firstLoad = useRef(true);
  useEffect(() => { dayRef.current = day; }, [day]);

  const refreshFused = useCallback(() => {
    getCorrelated(pos?.lat, pos?.lon, day || undefined).then(setFused).catch(() => {});
  }, [pos, day]);

  // Today (live) or an archived past day -- yesterday never bleeds into today.
  useEffect(() => {
    getEvents(pos?.lat, pos?.lon, day || undefined).then(setIncidents).catch(() => {});
    refreshFused();
    getSpaceWx().then(setSpacewx).catch(() => {});
  }, [pos, day, refreshFused]);

  useEffect(() => { getDays().then((d) => setDays(d.filter((x) => x !== ""))).catch(() => {}); }, []);

  const toggleLayer = (k: ToggleKey) => {
    const on = !layerOn[k];
    setLayerOn((p) => ({ ...p, [k]: on }));
    if (!on) { setLayerData((d) => ({ ...d, [k]: undefined })); return; }
    const c = pos ?? { lat: 38.25, lon: -122.04 };
    if (k === "evac") getEvac(c.lat, c.lon).then((g) => setLayerData((d) => ({ ...d, evac: g }))).catch(() => {});
    if (k === "danger") getDanger().then((g) => setLayerData((d) => ({ ...d, danger: g }))).catch(() => {});
    if (k === "safe") getSafePoints(c.lat, c.lon).then((s) => setLayerData((d) => ({ ...d, safe: s }))).catch(() => {});
    if (k === "buses") getBuses(c.lat, c.lon).then((b) => setLayerData((d) => ({ ...d, buses: b }))).catch(() => {});
    if (k === "route") getRoute(c.lat, c.lon).then((r) => setLayerData((d) => ({ ...d, route: r }))).catch(() => {});
    if (k === "cams") getMapCameras(c.lat, c.lon).then((cams) => setLayerData((d) => ({ ...d, cams }))).catch(() => {});
  };

  // Buses move -- refresh them while the layer is on.
  useEffect(() => {
    if (!layerOn.buses) return;
    const c = pos ?? { lat: 38.25, lon: -122.04 };
    const id = setInterval(() => getBuses(c.lat, c.lon).then((b) => setLayerData((d) => ({ ...d, buses: b }))).catch(() => {}), 15000);
    return () => clearInterval(id);
  }, [layerOn.buses, pos]);

  // Follow-me GPS: post it so the server threat-scores against my location.
  useEffect(() => {
    if (!navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (p) => {
        const lat = p.coords.latitude, lon = p.coords.longitude;
        setPos({ lat, lon });
        fetch("/api/location", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat, lon }),
        }).catch(() => {});
        getCounty(lat, lon).then((c) => setCounty(`${c.county}, ${c.state}`)).catch(() => {});
      },
      () => {},
      { enableHighAccuracy: true }
    );
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  // Live push over the existing /ws bus.
  useEffect(() => {
    let ws: WebSocket | null = null;
    let stop = false;
    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws`);
      ws.onopen = () => setLive(true);
      ws.onmessage = (m) => {
        if (dayRef.current) return; // reviewing an archived day -- ignore live push
        try {
          const msg = JSON.parse(m.data);
          if (msg.t === "snapshot") setIncidents(msg.events || []);
          else if (msg.t === "delta")
            setIncidents((prev) => {
              const byId: Record<string, Incident> = Object.fromEntries(prev.map((e) => [e.id, e]));
              for (const e of msg.events || []) byId[e.id] = e;
              return Object.values(byId);
            });
        } catch {}
      };
      ws.onclose = () => { setLive(false); if (!stop) setTimeout(connect, 5000); };
      ws.onerror = () => ws && ws.close();
    };
    connect();
    return () => { stop = true; ws && ws.close(); };
  }, []);

  // Correlation isn't pushed over ws yet -- refresh the fused layer on a timer.
  useEffect(() => {
    const id = setInterval(refreshFused, 20000);
    return () => clearInterval(id);
  }, [refreshFused]);

  // Transportation: planes every 6s (they glide between polls), trains every 15s.
  useEffect(() => {
    const c = pos ?? { lat: 38.25, lon: -122.04 };
    const planes = () => getAircraft(c.lat, c.lon).then(setAircraft).catch(() => {});
    const rail = () => getTrains(c.lat, c.lon).then(setTrains).catch(() => {});
    planes(); rail();
    const a = setInterval(planes, 6000);
    const t = setInterval(rail, 15000);
    return () => { clearInterval(a); clearInterval(t); };
  }, [pos]);

  // Local news headlines when the panel is open.
  useEffect(() => {
    if (newsOpen && county) getNews(county).then(setNews).catch(() => setNews([]));
  }, [newsOpen, county]);

  // Analytics when the panel opens (and for the selected archived day).
  useEffect(() => {
    if (statsOpen) getStats(day || undefined).then(setStats).catch(() => setStats(null));
  }, [statsOpen, day]);

  // Social hotspots (safety-chatter heat) -- refresh every 5 min for the map + alert.
  useEffect(() => {
    const f = () => getSocialHotspots().then((d) => setHotspots(d.hotspots || [])).catch(() => {});
    f();
    const id = setInterval(f, 300000);
    return () => clearInterval(id);
  }, []);

  // Playback: advance the scrubber while playing, at the chosen speed.
  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setScrubT((v) => {
        const next = v + speed * 0.6;
        if (next >= 100) { setPlaying(false); return 100; }
        return next;
      });
    }, 220);
    return () => clearInterval(id);
  }, [playing, speed]);

  // Sound alert on a brand-new EXTREME incident (skips the initial load).
  useEffect(() => {
    let fresh = false;
    for (const e of incidents) {
      if (e.threat_level === "EXTREME" && !seenCrit.current.has(e.id)) {
        seenCrit.current.add(e.id);
        if (!firstLoad.current) fresh = true;
      }
    }
    firstLoad.current = false;
    if (fresh && !muted) playBeep();
  }, [incidents, muted]);

  // Search + severity + source filter, then the time-scrubber cutoff.
  const filtered = filterIncidents(incidents, filters);
  const sources = Array.from(new Set(incidents.map((e) => e.source).filter(Boolean))).sort();
  const times = incidents.map((e) => Date.parse(e.last_seen || "") || 0).filter(Boolean);
  const tmin = times.length ? Math.min(...times) : 0;
  const tmax = times.length ? Math.max(...times) : 0;
  const cutoff = scrubT >= 100 ? Infinity : tmin + (scrubT / 100) * (tmax - tmin);
  const shown = scrubT >= 100 ? filtered : filtered.filter((e) => (Date.parse(e.last_seen || "") || 0) <= cutoff);
  const shownFused = scrubT >= 100 ? fused : fused.filter((e) => (Date.parse(e.last_seen || "") || 0) <= cutoff);
  const scrubLabel = scrubT >= 100 || !tmax ? "" : new Date(cutoff).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  // Chronological numbering: first event = #1, latest = highest number.
  // Map pin #N === alarm-queue #N (the queue still lists newest-first).
  const rankMap: Record<string, number> = {};
  [...shown]
    .sort((a, b) => (Date.parse(a.last_seen || "") || 0) - (Date.parse(b.last_seen || "") || 0))
    .forEach((e, i) => { rankMap[e.id] = i + 1; });

  return (
    <main style={{ position: "fixed", inset: 0 }}>
      <MapView
        incidents={shown}
        fused={shownFused}
        aircraft={aircraft}
        trains={trains}
        layers={{ ...layerData, socialHot: layerOn.social ? hotspots : undefined }}
        rankMap={rankMap}
        userPos={pos}
        showRings={layerOn.rings}
        linkFrom={selected && selected.lat != null && selected.lon != null ? { lat: selected.lat, lon: selected.lon } : null}
        linkTargets={linkTargets}
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
      />
      {(() => {
        // Per-city auto-tuned "hot" flag (spike above the city's own baseline).
        const hot = hotspots.filter((h) => (h.hot ?? h.count >= 4));
        if (!hot.length) return null;
        // Prefer the hotspot NEAREST me (proximity beats raw count); highest count if no GPS.
        const rank = (h: any) => (pos ? (h.lat - pos.lat) ** 2 + (h.lon - pos.lon) ** 2 : -h.count);
        const h = [...hot].sort((a, b) => rank(a) - rank(b))[0];
        return (
          <div
            style={{
              position: "absolute", top: 56, left: "50%", transform: "translateX(-50%)", zIndex: 30,
              background: "rgba(200,0,0,0.92)", color: "#fff", padding: "6px 14px", borderRadius: 10,
              fontSize: 13, fontWeight: 700, boxShadow: "0 4px 20px rgba(0,0,0,0.5)", cursor: "pointer",
            }}
            onClick={() => setLayerOn((p) => ({ ...p, social: true }))}
          >
            {"\u{1F525}"} {h.city} heating up: {h.count} safety posts
          </div>
        );
      })()}
      <div className="radar-sweep" />
      <div className="scanlines" />
      <StatusBar incidents={incidents} spacewx={spacewx} county={county} live={live && !day && scrubT >= 100} />
      <AlarmQueue
        incidents={shown}
        rankMap={rankMap}
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
        open={alarmOpen}
        onToggle={() => setAlarmOpen((v) => !v)}
      />
      <Scrubber
        value={scrubT}
        onChange={(v) => { setScrubT(v); if (v >= 100) setPlaying(false); }}
        label={scrubLabel}
        live={scrubT >= 100}
        playing={playing}
        onPlay={() => setPlaying((p) => !p)}
        speed={speed}
        onSpeed={() => setSpeed((s) => (s === 1 ? 4 : s === 4 ? 20 : 1))}
        onLive={() => { setPlaying(false); setScrubT(100); }}
      />
      <FilterBar
        filters={filters}
        onChange={setFilters}
        sources={sources}
        count={shown.length}
        open={filterOpen}
        onToggle={() => setFilterOpen((v) => !v)}
      />
      <Legend />
      <Toolbar
        active={layerOn}
        onToggle={toggleLayer}
        days={days}
        day={day}
        onDay={setDay}
        newsOpen={newsOpen}
        onNews={() => setNewsOpen((v) => !v)}
        statsOpen={statsOpen}
        onStats={() => setStatsOpen((v) => !v)}
        muted={muted}
        onMute={() => setMuted((v) => !v)}
      />
      <NewsPanel open={newsOpen} news={news} place={county} onClose={() => setNewsOpen(false)} />
      <StatsPanel open={statsOpen} stats={stats} onClose={() => setStatsOpen(false)} />
      {pos && <MiniMap lat={pos.lat} lon={pos.lon} />}
      <DetailDrawer ev={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
