const map = new maplibregl.Map({
  container: "map",
  style: "https://tiles.openfreemap.org/styles/liberty", // labeled: cities, streets, highways, POIs
  center: [-121.98, 38.25],
  zoom: 9,
  maxPitch: 75,
});
map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }));
map.addControl(
  new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: true,
  })
);

const THREAT_COLORS = {
  EXTREME: "#ff2d2d", HIGH: "#ff8c1a", MEDIUM: "#ffd21a", LOW: "#D4AF37", LOG: "#8a8a8a",
};
const POSTURE = ["LOG", "LOW", "MEDIUM", "HIGH", "EXTREME"];
const POSTURE_CLASS = { EXTREME: "red", HIGH: "orange", MEDIUM: "yellow", LOW: "green", LOG: "green" };

let markers = [];
let events = [];
let userLatLon = null; // [lon, lat]
let selectedId = null;

map.on("load", () => {
  // 3D terrain (free, no key)
  map.addSource("dem", {
    type: "raster-dem",
    tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
    encoding: "terrarium", tileSize: 256, maxzoom: 14,
    attribution: "Elevation: AWS Terrain Tiles",
  });
  map.setTerrain({ source: "dem", exaggeration: 1.3 });

  // Satellite "dive-in" layer (free, no token), hidden until toggled
  map.addSource("sat", {
    type: "raster", tileSize: 256, maxzoom: 19,
    tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
    attribution: "Imagery: Esri, Maxar, Earthstar Geographics",
  });
  map.addLayer({ id: "sat", type: "raster", source: "sat", layout: { visibility: "none" } });

  // County boundary lines (US counties = admin_level 6)
  try {
    map.addLayer({
      id: "county-lines", type: "line",
      source: "openmaptiles", "source-layer": "boundary",
      filter: ["==", ["get", "admin_level"], 6],
      paint: { "line-color": "#D4AF37", "line-width": 1, "line-dasharray": [2, 2], "line-opacity": 0.5 },
    });
  } catch (e) { /* source id differs; skip */ }

  loadDays();
  locateUser();
});

document.getElementById("sat-toggle").onclick = () => {
  const v = map.getLayoutProperty("sat", "visibility") === "visible" ? "none" : "visible";
  map.setLayoutProperty("sat", "visibility", v);
  document.getElementById("sat-toggle").style.background = v === "visible" ? "#D4AF37" : "#1a1a1a";
  if (v === "visible") map.easeTo({ pitch: 55 });
};
document.getElementById("detail-close").onclick = () => {
  document.getElementById("detail").classList.add("hidden");
  window.speechSynthesis && window.speechSynthesis.cancel();
  selectedId = null;
};

// "Listen to the report" -- read the panel aloud with the browser's own voice.
document.getElementById("d-listen").onclick = () => {
  if (!window.speechSynthesis) return;
  const text = [
    document.getElementById("d-title").textContent,
    document.getElementById("d-where").textContent,
    document.getElementById("d-story").textContent,
  ].filter(Boolean).join(". ");
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
};

function clearMarkers() { markers.forEach((m) => m.remove()); markers = []; }
function tsMillis(ev) { return Date.parse(ev.last_seen) || 0; }

function render(cutoffMillis) {
  clearMarkers();
  let shown = 0, top = "LOG";
  for (const ev of events) {
    if (POSTURE.indexOf(ev.threat_level) > POSTURE.indexOf(top)) top = ev.threat_level;
    if (ev.lat == null || ev.lon == null) continue;
    if (cutoffMillis && tsMillis(ev) > cutoffMillis) continue;
    const color = THREAT_COLORS[ev.threat_level] || "#D4AF37";
    const el = document.createElement("div");
    el.textContent = "!";
    el.style.cssText =
      `background:${color};color:#0A0A0A;font-weight:700;border-radius:50%;` +
      "width:24px;height:24px;display:flex;align-items:center;justify-content:center;" +
      `border:2px solid ${ev.id === selectedId ? "#fff" : "#0A0A0A"};cursor:pointer;`;
    el.onclick = () => openDetail(ev);
    markers.push(new maplibregl.Marker({ element: el }).setLngLat([ev.lon, ev.lat]).addTo(map));
    shown++;
  }
  document.getElementById("count").textContent = shown + " incidents";
  const pe = document.getElementById("posture");
  pe.textContent = top === "LOG" ? "GREEN" : top;
  pe.className = "posture " + (POSTURE_CLASS[top] || "green");
}

async function openDetail(ev) {
  selectedId = ev.id;
  const d = document.getElementById("detail");
  d.classList.remove("hidden");
  const tl = document.getElementById("d-threat");
  tl.textContent = `${ev.threat_level}${ev.distance_mi != null ? " · " + ev.distance_mi + " mi" : ""}`;
  tl.style.background = THREAT_COLORS[ev.threat_level] || "#888";
  tl.style.color = ["EXTREME", "HIGH", "LOG"].includes(ev.threat_level) ? "#fff" : "#0A0A0A";
  document.getElementById("d-title").textContent = ev.type || "Incident";
  document.getElementById("d-story").textContent =
    (ev.body || "(no dispatch detail yet)") + `\n\n${ev.geo_label || ""} · ${ev.log_time || ""}`;
  // Recorded scanner audio -> DVR replay right in the panel.
  const audio = document.getElementById("d-audio");
  if (ev.audio_url) {
    audio.src = ev.audio_url;
    audio.classList.remove("hidden");
  } else {
    audio.classList.add("hidden");
    audio.removeAttribute("src");
  }
  document.getElementById("d-where").textContent = "locating landmark...";
  document.getElementById("d-cams").textContent = ev.lat == null ? "no coordinates" : "loading...";
  document.getElementById("d-feeds").textContent = "loading...";
  map.flyTo({ center: [ev.lon, ev.lat], zoom: 14, pitch: 45 });
  render(null); // redraw so the selected marker gets a white ring

  if (ev.lat == null) return;
  fetch(`/api/where?lat=${ev.lat}&lon=${ev.lon}`)
    .then((r) => r.json())
    .then((w) => { if (selectedId === ev.id) document.getElementById("d-where").textContent = w.text; })
    .catch(() => {});
  fetch(`/api/cameras?lat=${ev.lat}&lon=${ev.lon}&n=3`)
    .then((r) => r.json())
    .then((c) => { if (selectedId === ev.id) renderCams(c.cameras || []); })
    .catch(() => { document.getElementById("d-cams").textContent = "cameras unavailable"; });
  fetch(`/api/feeds?lat=${ev.lat}&lon=${ev.lon}`)
    .then((r) => r.json())
    .then((f) => { if (selectedId === ev.id) renderFeeds(f.feeds || []); })
    .catch(() => {});
}

function renderCams(cams) {
  const box = document.getElementById("d-cams");
  box.replaceChildren();
  if (!cams.length) { box.textContent = "no cameras in range"; return; }
  for (const c of cams) {
    const div = document.createElement("div");
    div.className = "cam";
    if (c.image_url) {
      const img = document.createElement("img");
      img.src = c.image_url + (c.image_url.includes("?") ? "&" : "?") + "t=" + Date.now();
      img.loading = "lazy";
      div.appendChild(img);
    }
    const cap = document.createElement("small");
    cap.textContent = `${c.name || "camera"} · ${c.distance_mi} mi` + (c.stream_url ? " (live)" : "");
    div.appendChild(cap);
    if (c.stream_url) {
      div.style.cursor = "pointer";
      div.onclick = () => window.open(c.stream_url, "_blank");
    }
    box.appendChild(div);
  }
}

function renderFeeds(feeds) {
  const box = document.getElementById("d-feeds");
  box.replaceChildren();
  if (!feeds.length) { box.textContent = "no scanner feeds for this county"; return; }
  for (const f of feeds) {
    const a = document.createElement("a");
    a.href = f.url; a.target = "_blank"; a.textContent = "🔊 " + f.name;
    box.appendChild(a);
  }
}

async function loadDays() {
  const sel = document.getElementById("day");
  const { days } = await (await fetch("/api/days")).json();
  sel.replaceChildren();
  for (const d of days.slice().reverse()) {
    const o = document.createElement("option");
    o.value = d; o.textContent = d.replace(/_/g, "-");
    sel.appendChild(o);
  }
  sel.onchange = () => loadEvents(sel.value);
  await loadEvents(sel.value);
}

async function loadEvents(date) {
  let url = date ? `/api/events?date=${date}` : "/api/events";
  if (userLatLon) url += `${url.includes("?") ? "&" : "?"}lat=${userLatLon[1]}&lon=${userLatLon[0]}`;
  const data = await (await fetch(url)).json();
  events = data.events || [];
  const withGeo = events.filter((e) => e.lat != null);
  if (withGeo.length && !map.__fitted) {
    const b = new maplibregl.LngLatBounds();
    withGeo.forEach((e) => b.extend([e.lon, e.lat]));
    if (!b.isEmpty()) map.fitBounds(b, { padding: 60, maxZoom: 12 });
    map.__fitted = true;
  }
  wireSlider();
  render(null);
}

function wireSlider() {
  const slider = document.getElementById("time");
  const clock = document.getElementById("clock");
  const stamps = events.map(tsMillis).filter(Boolean);
  if (!stamps.length) { clock.textContent = "live"; return; }
  const min = Math.min(...stamps), max = Math.max(...stamps);
  slider.oninput = () => {
    const cutoff = min + (max - min) * (slider.value / 100);
    clock.textContent = slider.value === "100" ? "live"
      : new Date(cutoff).toLocaleTimeString("en-US", { timeZone: "America/Los_Angeles", hour: "2-digit", minute: "2-digit" });
    render(slider.value === "100" ? null : cutoff);
  };
}

async function resolveCounty(lat, lon) {
  try {
    const c = await (await fetch(`/api/county?lat=${lat}&lon=${lon}`)).json();
    if (c.county) document.getElementById("county").textContent = `${c.county}, ${c.state}`;
  } catch (e) { /* keep placeholder */ }
}

function locateUser() {
  if (!navigator.geolocation) { document.getElementById("county").textContent = "no GPS"; return; }
  navigator.geolocation.watchPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      const first = !userLatLon;
      userLatLon = [longitude, latitude];
      if (first) resolveCounty(latitude, longitude);
      fetch(`/api/location?lat=${latitude}&lon=${longitude}`, { method: "POST" }).catch(() => {});
      loadEvents(document.getElementById("day").value);
    },
    () => { document.getElementById("county").textContent = "GPS denied"; },
    { enableHighAccuracy: true, maximumAge: 30000 }
  );
}

setInterval(() => {
  const sel = document.getElementById("day");
  if (!sel.value || sel.selectedIndex === 0) loadEvents(sel.value);
}, 60000);

/* ---- Live transportation layer: aircraft + trains ---- */
const AIR_COLORS = { military: "#ff2d2d", commercial: "#7fd1ff", ga: "#cccccc" };
let airMarkers = new Map();   // hex -> marker (reused so planes glide, not flicker)
let trainMarkers = [];
let airOn = false, railOn = false;

function center() {
  return userLatLon || [map.getCenter().lng, map.getCenter().lat];
}

async function refreshAircraft() {
  if (!airOn) return;
  const [lon, lat] = center();
  let data;
  try { data = await (await fetch(`/api/aircraft?lat=${lat}&lon=${lon}&dist=120`)).json(); }
  catch (e) { return; }
  const seen = new Set();
  for (const a of data.aircraft || []) {
    seen.add(a.id);
    let m = airMarkers.get(a.id);
    const color = a.emergency ? "#ff00d4" : AIR_COLORS[a.kind] || "#ccc";
    if (!m) {
      const el = document.createElement("div");
      el.className = "plane";
      const glyph = document.createElement("span");
      glyph.textContent = "✈";
      glyph.style.display = "inline-block";
      el.appendChild(glyph);
      el.onclick = () => openAir(a);
      m = new maplibregl.Marker({ element: el, rotationAlignment: "map" });
      airMarkers.set(a.id, m);
      m.setLngLat([a.lon, a.lat]).addTo(map);
    }
    m.setLngLat([a.lon, a.lat]);
    m.setRotation((a.track || 0) - 45); // the glyph points NE at 0deg
    const s = m.getElement().firstElementChild;
    s.style.color = color;
    s.style.fontSize = a.kind === "military" ? "20px" : "15px";
    m.getElement().title = `${a.flight} ${a.type || ""} ${a.alt || "?"}ft ${a.kind}${a.emergency ? " EMERGENCY" : ""}`;
  }
  for (const [id, m] of airMarkers) if (!seen.has(id)) { m.remove(); airMarkers.delete(id); }
}

async function refreshTrains() {
  trainMarkers.forEach((m) => m.remove());
  trainMarkers = [];
  if (!railOn) return;
  const [lon, lat] = center();
  let data;
  try { data = await (await fetch(`/api/trains?lat=${lat}&lon=${lon}&radius=80`)).json(); }
  catch (e) { return; }
  for (const t of data.trains || []) {
    const el = document.createElement("div");
    el.className = "train";
    el.textContent = "🚆";
    el.title = `${t.route} #${t.num} ${t.speed || 0}mph ${t.state || ""}`;
    el.onclick = () => openTrain(t);
    trainMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([t.lon, t.lat]).addTo(map));
  }
}

function openAir(a) {
  map.flyTo({ center: [a.lon, a.lat], zoom: 10, pitch: 30 });
  const d = document.getElementById("detail");
  d.classList.remove("hidden");
  const tl = document.getElementById("d-threat");
  tl.textContent = a.emergency ? "AIRCRAFT EMERGENCY" : a.kind.toUpperCase() + " AIRCRAFT";
  tl.style.background = a.emergency ? "#ff00d4" : AIR_COLORS[a.kind];
  tl.style.color = "#0A0A0A";
  document.getElementById("d-title").textContent = a.flight;
  document.getElementById("d-where").textContent = `${a.type || "unknown type"} · reg ${a.reg || "?"}`;
  document.getElementById("d-story").textContent =
    `Altitude: ${a.alt || "?"} ft\nGround speed: ${a.speed || "?"} kt\nHeading: ${Math.round(a.track || 0)}°\nSquawk: ${a.squawk || "?"}` +
    (a.emergency ? "\n\n*** EMERGENCY SQUAWK ***" : "");
  document.getElementById("d-cams").textContent = "n/a for aircraft";
  document.getElementById("d-feeds").textContent = "n/a";
}

function openTrain(t) {
  map.flyTo({ center: [t.lon, t.lat], zoom: 11 });
  const d = document.getElementById("detail");
  d.classList.remove("hidden");
  const tl = document.getElementById("d-threat");
  tl.textContent = "RAIL"; tl.style.background = "#8a8a8a"; tl.style.color = "#fff";
  document.getElementById("d-title").textContent = `${t.route} #${t.num}`;
  document.getElementById("d-where").textContent = `${t.distance_mi} mi away · ${t.state || ""}`;
  document.getElementById("d-story").textContent =
    `Speed: ${t.speed || 0} mph\nHeading: ${t.heading || "?"}\nState: ${t.state || "?"}`;
  document.getElementById("d-cams").textContent = "n/a";
  document.getElementById("d-feeds").textContent = "n/a";
}

document.getElementById("air-toggle").onclick = () => {
  airOn = !airOn;
  document.getElementById("air-toggle").style.background = airOn ? "#D4AF37" : "#1a1a1a";
  if (airOn) refreshAircraft();
  else { airMarkers.forEach((m) => m.remove()); airMarkers.clear(); }
};
document.getElementById("rail-toggle").onclick = () => {
  railOn = !railOn;
  document.getElementById("rail-toggle").style.background = railOn ? "#D4AF37" : "#1a1a1a";
  refreshTrains();
};
setInterval(refreshAircraft, 12000);  // planes glide every 12s
setInterval(refreshTrains, 30000);

/* ---- Evacuation zones + safe points (the "where do I go" layer) ---- */
let safeMarkers = [];
const SAFE_ICON = { hospital: "🏥", police: "🚓", fire_station: "🚒", shelter: "🏠", assembly_point: "🟢" };

async function refreshEvac(on) {
  if (map.getLayer("evac-fill")) map.removeLayer("evac-fill");
  if (map.getLayer("evac-line")) map.removeLayer("evac-line");
  if (map.getSource("evac")) map.removeSource("evac");
  if (!on) return;
  let gj;
  try { gj = (await (await fetch("/api/evac")).json()).geojson; } catch (e) { return; }
  const n = (gj.features || []).length;
  if (!n) { alert("No active evacuation zones in California right now (blue sky)."); return; }
  map.addSource("evac", { type: "geojson", data: gj });
  map.addLayer({
    id: "evac-fill", type: "fill", source: "evac",
    paint: {
      "fill-color": ["match", ["get", "STATUS"],
        "Evacuation Order", "#ff2d2d", "Evacuation Warning", "#ff8c1a",
        "Shelter in Place", "#7fd1ff", "#ffd21a"],
      "fill-opacity": 0.35,
    },
  });
  map.addLayer({
    id: "evac-line", type: "line", source: "evac",
    paint: { "line-color": "#fff", "line-width": 1 },
  });
}

async function refreshSafe(on) {
  safeMarkers.forEach((m) => m.remove());
  safeMarkers = [];
  if (!on) return;
  const [lon, lat] = center();
  let pts;
  try { pts = (await (await fetch(`/api/safepoints?lat=${lat}&lon=${lon}`)).json()).safe_points; }
  catch (e) { return; }
  for (const p of pts || []) {
    const el = document.createElement("div");
    el.textContent = SAFE_ICON[p.kind] || "➕";
    el.style.fontSize = "18px";
    el.style.cursor = "pointer";
    el.title = `${p.name} (${p.kind}) · ${p.distance_mi} mi`;
    safeMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).addTo(map));
  }
}

document.getElementById("evac-toggle").onclick = (e) => {
  const on = e.target.style.background !== "rgb(212, 175, 55)";
  e.target.style.background = on ? "#D4AF37" : "#1a1a1a";
  refreshEvac(on);
};
document.getElementById("safe-toggle").onclick = (e) => {
  const on = e.target.style.background !== "rgb(212, 175, 55)";
  e.target.style.background = on ? "#D4AF37" : "#1a1a1a";
  refreshSafe(on);
};

/* ---- Buses (511 transit) + public webcams ---- */
let busMarkers = [];
let camMarkers = [];
let busOn = false, camOn = false;

async function refreshBuses() {
  busMarkers.forEach((m) => m.remove());
  busMarkers = [];
  if (!busOn) return;
  const [lon, lat] = center();
  let data;
  try { data = await (await fetch(`/api/transit?lat=${lat}&lon=${lon}&radius=40`)).json(); }
  catch (e) { return; }
  for (const v of data.transit || []) {
    const el = document.createElement("div");
    el.textContent = "🚌";
    el.style.fontSize = "15px";
    el.style.cursor = "pointer";
    el.title = `Route ${v.route || v.label || "?"} · ${v.distance_mi} mi`;
    el.onclick = () => {
      map.flyTo({ center: [v.lon, v.lat], zoom: 13 });
      const d = document.getElementById("detail");
      d.classList.remove("hidden");
      document.getElementById("d-threat").textContent = "TRANSIT";
      document.getElementById("d-threat").style.background = "#8a8a8a";
      document.getElementById("d-threat").style.color = "#fff";
      document.getElementById("d-title").textContent = `Bus / Route ${v.route || v.label || "?"}`;
      document.getElementById("d-where").textContent = `${v.distance_mi} mi away`;
      document.getElementById("d-story").textContent = `Route: ${v.route || "?"}\nVehicle: ${v.label || v.id}`;
      document.getElementById("d-cams").textContent = "n/a";
      document.getElementById("d-feeds").textContent = "n/a";
    };
    busMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([v.lon, v.lat]).addTo(map));
  }
}

async function refreshCams() {
  camMarkers.forEach((m) => m.remove());
  camMarkers = [];
  if (!camOn) return;
  const [lon, lat] = center();
  let data;
  try { data = await (await fetch(`/api/webcams?lat=${lat}&lon=${lon}&radius_km=60`)).json(); }
  catch (e) { return; }
  for (const c of data.webcams || []) {
    const el = document.createElement("div");
    el.textContent = "📷";
    el.style.fontSize = "15px";
    el.style.cursor = "pointer";
    el.title = c.name;
    el.onclick = () => {
      map.flyTo({ center: [c.lon, c.lat], zoom: 13 });
      const d = document.getElementById("detail");
      d.classList.remove("hidden");
      document.getElementById("d-threat").textContent = "WEBCAM";
      document.getElementById("d-threat").style.background = "#7fd1ff";
      document.getElementById("d-threat").style.color = "#0A0A0A";
      document.getElementById("d-title").textContent = c.name;
      document.getElementById("d-where").textContent = "public webcam";
      document.getElementById("d-story").textContent = "";
      const box = document.getElementById("d-cams");
      box.replaceChildren();
      if (c.image) { const img = document.createElement("img"); img.src = c.image; box.appendChild(img); }
      document.getElementById("d-feeds").textContent = "";
    };
    camMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([c.lon, c.lat]).addTo(map));
  }
}

document.getElementById("bus-toggle").onclick = (e) => {
  busOn = !busOn;
  e.target.style.background = busOn ? "#D4AF37" : "#1a1a1a";
  refreshBuses();
};

document.getElementById("news-toggle").onclick = async () => {
  const countyText = document.getElementById("county").textContent;
  const place = /[A-Za-z]/.test(countyText) ? countyText.split(",")[0] : "Solano County";
  const d = document.getElementById("detail");
  d.classList.remove("hidden");
  document.getElementById("d-threat").textContent = "NEWS";
  document.getElementById("d-threat").style.background = "#a77fff";
  document.getElementById("d-threat").style.color = "#0A0A0A";
  document.getElementById("d-title").textContent = `Local news: ${place}`;
  document.getElementById("d-where").textContent = "what is driving events around you";
  document.getElementById("d-story").textContent = "loading...";
  document.getElementById("d-cams").textContent = "";
  const feeds = document.getElementById("d-feeds");
  feeds.replaceChildren();
  try {
    const data = await (await fetch(`/api/news?place=${encodeURIComponent(place)}`)).json();
    document.getElementById("d-story").textContent = (data.news || []).length ? "" : "no recent news found";
    for (const a of data.news || []) {
      const link = document.createElement("a");
      link.href = a.url; link.target = "_blank";
      link.textContent = `📰 ${a.title || a.domain}`;
      feeds.appendChild(link);
    }
  } catch (e) {
    document.getElementById("d-story").textContent = "news unavailable";
  }
};
document.getElementById("cam-toggle").onclick = (e) => {
  camOn = !camOn;
  e.target.style.background = camOn ? "#D4AF37" : "#1a1a1a";
  refreshCams();
};
setInterval(refreshBuses, 20000);  // buses move every 20s
