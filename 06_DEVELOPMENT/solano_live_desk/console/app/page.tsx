"use client";
import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { Incident, SpaceWx, Aircraft, Train } from "@/lib/types";
import { getEvents, getCorrelated, getSpaceWx, getCounty, getAircraft, getTrains } from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import AlarmQueue from "@/components/AlarmQueue";
import DetailDrawer from "@/components/DetailDrawer";

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

  const refreshFused = useCallback(() => {
    getCorrelated(pos?.lat, pos?.lon).then(setFused).catch(() => {});
  }, [pos]);

  useEffect(() => {
    getEvents(pos?.lat, pos?.lon).then(setIncidents).catch(() => {});
    refreshFused();
    getSpaceWx().then(setSpacewx).catch(() => {});
  }, [pos, refreshFused]);

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
        selectedId={selected?.id ?? null}
        onSelect={setSelected}
      />
      <StatusBar incidents={incidents} spacewx={spacewx} county={county} live={live} />
      <AlarmQueue incidents={incidents} selectedId={selected?.id ?? null} onSelect={setSelected} />
      <DetailDrawer ev={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
