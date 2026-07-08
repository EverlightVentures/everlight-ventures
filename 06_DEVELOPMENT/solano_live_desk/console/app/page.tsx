"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { Incident, SpaceWx, Aircraft, Train } from "@/lib/types";
import type { Layers } from "@/components/MapView";
import type { ToggleKey } from "@/components/Toolbar";
import {
  getEvents, getCorrelated, getSpaceWx, getCounty, getAircraft, getTrains,
  getEvac, getSafePoints, getBuses, getDanger, getRoute, getDays,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import AlarmQueue from "@/components/AlarmQueue";
import DetailDrawer from "@/components/DetailDrawer";
import Toolbar from "@/components/Toolbar";

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
    danger: false, evac: false, safe: false, buses: false, route: false,
  });
  const [layerData, setLayerData] = useState<Layers>({});
  const [day, setDay] = useState(""); // "" = today/live; else an archived day
  const [days, setDays] = useState<string[]>([]);
  const [alarmOpen, setAlarmOpen] = useState(true);
  const dayRef = useRef("");
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

  return (
    <main style={{ position: "fixed", inset: 0 }}>
      <MapView
        incidents={incidents}
        fused={fused}
        aircraft={aircraft}
        trains={trains}
        layers={layerData}
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
      />
      <StatusBar incidents={incidents} spacewx={spacewx} county={county} live={live && !day} />
      <AlarmQueue
        incidents={incidents}
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
        open={alarmOpen}
        onToggle={() => setAlarmOpen((v) => !v)}
      />
      <Toolbar active={layerOn} onToggle={toggleLayer} days={days} day={day} onDay={setDay} />
      <DetailDrawer ev={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
