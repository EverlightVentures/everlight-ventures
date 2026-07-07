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
  selectedId = null;
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
