"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { Incident, SpaceWx, Aircraft, Train } from "@/lib/types";
import type { Layers } from "@/components/MapView";
import type { ToggleKey } from "@/components/Toolbar";
import {
  getEvents, getCorrelated, getSpaceWx, getCounty, getAircraft, getTrains,
  getEvac, getSafePoints, getBuses, getDanger, getRoute, getDays, getMapCameras, getNews,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import AlarmQueue from "@/components/AlarmQueue";
import DetailDrawer from "@/components/DetailDrawer";
import Toolbar from "@/components/Toolbar";
import Scrubber from "@/components/Scrubber";
import NewsPanel from "@/components/NewsPanel";
import MiniMap from "@/components/MiniMap";

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
    danger: false, evac: false, safe: false, buses: false, route: false, cams: false,
  });
  const [layerData, setLayerData] = useState<Layers>({});
  const [day, setDay] = useState(""); // "" = today/live; else an archived day
  const [days, setDays] = useState<string[]>([]);
  const [alarmOpen, setAlarmOpen] = useState(true);
  const [newsOpen, setNewsOpen] = useState(false);
  const [news, setNews] = useState<any[]>([]);
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

  // Time-scrubber: replay the day up to a cutoff (100 = live/all).
  const times = incidents.map((e) => Date.parse(e.last_seen || "") || 0).filter(Boolean);
  const tmin = times.length ? Math.min(...times) : 0;
  const tmax = times.length ? Math.max(...times) : 0;
  const cutoff = scrubT >= 100 ? Infinity : tmin + (scrubT / 100) * (tmax - tmin);
  const shown = scrubT >= 100 ? incidents : incidents.filter((e) => (Date.parse(e.last_seen || "") || 0) <= cutoff);
  const shownFused = scrubT >= 100 ? fused : fused.filter((e) => (Date.parse(e.last_seen || "") || 0) <= cutoff);
  const scrubLabel = scrubT >= 100 || !tmax ? "" : new Date(cutoff).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  // One shared recency ranking: newest = #1. Map pin #N === alarm-queue #N.
  const rankMap: Record<string, number> = {};
  [...shown]
    .sort((a, b) => (Date.parse(b.last_seen || "") || 0) - (Date.parse(a.last_seen || "") || 0))
    .forEach((e, i) => { rankMap[e.id] = i + 1; });

  return (
    <main style={{ position: "fixed", inset: 0 }}>
      <MapView
        incidents={shown}
        fused={shownFused}
        aircraft={aircraft}
        trains={trains}
        layers={layerData}
        rankMap={rankMap}
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
      />
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
      <Scrubber value={scrubT} onChange={setScrubT} label={scrubLabel} live={scrubT >= 100} />
      <Toolbar
        active={layerOn}
        onToggle={toggleLayer}
        days={days}
        day={day}
        onDay={setDay}
        newsOpen={newsOpen}
        onNews={() => setNewsOpen((v) => !v)}
        muted={muted}
        onMute={() => setMuted((v) => !v)}
      />
      <NewsPanel open={newsOpen} news={news} place={county} onClose={() => setNewsOpen(false)} />
      {pos && <MiniMap lat={pos.lat} lon={pos.lon} />}
      <DetailDrawer ev={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
