const map = new maplibregl.Map({
  container: "map",
  style: "https://demotiles.maplibre.org/style.json",
  center: [-121.98, 38.25], // Solano
  zoom: 9,
});
map.addControl(new maplibregl.NavigationControl());
map.addControl(
  new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: true,
  })
); // "follow-me"

const THREAT_COLORS = {
  EXTREME: "#ff2d2d",
  HIGH: "#ff8c1a",
  MEDIUM: "#ffd21a",
  LOW: "#D4AF37",
  LOG: "#8a8a8a",
};
const POSTURE = ["LOG", "LOW", "MEDIUM", "HIGH", "EXTREME"];
const POSTURE_CLASS = { EXTREME: "red", HIGH: "orange", MEDIUM: "yellow", LOW: "green", LOG: "green" };

let markers = [];
let events = [];
let userLatLon = null; // [lon, lat] not set until GPS resolves

function clearMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
}

function tsMillis(ev) {
  return Date.parse(ev.last_seen) || 0;
}

function buildPopupNode(ev) {
  const wrap = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = ev.type || "Incident";
  const tl = document.createElement("span");
  const dist = ev.distance_mi != null ? ` · ${ev.distance_mi} mi` : "";
  tl.textContent = ` [${ev.threat_level}${dist}]`;
  tl.style.color = THREAT_COLORS[ev.threat_level] || "#888";
  const meta = document.createElement("small");
  meta.textContent = `${ev.geo_label || ""} · ${ev.log_time || ""}`;
  const body = document.createElement("div");
  body.className = "popup-body";
  body.textContent = ev.body || "";
  wrap.appendChild(title);
  wrap.appendChild(tl);
  wrap.appendChild(document.createElement("br"));
  wrap.appendChild(meta);
  wrap.appendChild(body);
  return wrap;
}

function updatePosture() {
  let top = "LOG";
  for (const ev of events) {
    if (POSTURE.indexOf(ev.threat_level) > POSTURE.indexOf(top)) top = ev.threat_level;
  }
  const el = document.getElementById("posture");
  el.textContent = top === "LOG" ? "GREEN" : top;
  el.className = "posture " + (POSTURE_CLASS[top] || "green");
}

function render(cutoffMillis) {
  clearMarkers();
  let shown = 0;
  for (const ev of events) {
    if (ev.lat == null || ev.lon == null) continue;
    if (cutoffMillis && tsMillis(ev) > cutoffMillis) continue;
    const color = THREAT_COLORS[ev.threat_level] || "#D4AF37";
    const el = document.createElement("div");
    el.textContent = "!";
    el.style.cssText =
      `background:${color};color:#0A0A0A;font-weight:700;border-radius:50%;` +
      "width:22px;height:22px;display:flex;align-items:center;justify-content:center;" +
      "border:2px solid #0A0A0A;cursor:pointer;";
    const popup = new maplibregl.Popup({ offset: 14 }).setDOMContent(buildPopupNode(ev));
    markers.push(
      new maplibregl.Marker({ element: el })
        .setLngLat([ev.lon, ev.lat])
        .setPopup(popup)
        .addTo(map)
    );
    shown++;
  }
  document.getElementById("count").textContent = shown + " incidents";
  updatePosture();
}

async function loadDays() {
  const sel = document.getElementById("day");
  const { days } = await (await fetch("/api/days")).json();
  sel.replaceChildren();
  for (const d of days.slice().reverse()) {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d.replace(/_/g, "-");
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
  if (!stamps.length) {
    clock.textContent = "live";
    return;
  }
  const min = Math.min(...stamps);
  const max = Math.max(...stamps);
  slider.oninput = () => {
    const frac = slider.value / 100;
    const cutoff = min + (max - min) * frac;
    clock.textContent =
      slider.value === "100"
        ? "live"
        : new Date(cutoff).toLocaleTimeString("en-US", {
            timeZone: "America/Los_Angeles",
            hour: "2-digit",
            minute: "2-digit",
          });
    render(slider.value === "100" ? null : cutoff);
  };
}

async function resolveCounty(lat, lon) {
  try {
    const c = await (await fetch(`/api/county?lat=${lat}&lon=${lon}`)).json();
    if (c.county) document.getElementById("county").textContent = `${c.county}, ${c.state}`;
  } catch (e) {
    /* leave placeholder */
  }
}

function locateUser() {
  if (!navigator.geolocation) {
    document.getElementById("county").textContent = "no GPS";
    return;
  }
  navigator.geolocation.watchPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      const first = !userLatLon;
      userLatLon = [longitude, latitude];
      if (first) resolveCounty(latitude, longitude);
      loadEvents(document.getElementById("day").value); // re-score against live GPS
    },
    () => {
      document.getElementById("county").textContent = "GPS denied";
    },
    { enableHighAccuracy: true, maximumAge: 30000 }
  );
}

map.on("load", () => {
  loadDays();
  locateUser();
});
setInterval(() => {
  const sel = document.getElementById("day");
  if (!sel.value || sel.selectedIndex === 0) loadEvents(sel.value);
}, 60000); // refresh the live day each minute
