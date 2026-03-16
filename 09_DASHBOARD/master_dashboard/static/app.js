const state = {
  selectedSet: new Set(),
  secondary: { rootId: null, path: "" },
  split: false,
  roots: [],
  rootId: null,
  path: "",
  selected: null,
  apps: [],
  mode: "files",
  mediaKind: null,
};

const rootsEl = document.getElementById("roots");
const gridEl = document.getElementById("grid");
const gridEl2 = document.getElementById("grid2");
const breadcrumbs2 = document.getElementById("breadcrumbs2");
const splitWrap = document.getElementById("splitWrap");
const splitModeBtn = document.getElementById("splitModeBtn");
const resetWindowsBtn = document.getElementById("resetWindowsBtn");
const breadcrumbsEl = document.getElementById("breadcrumbs");
const previewEl = document.getElementById("preview");
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const refreshBtn = document.getElementById("refreshBtn");
const openTabBtn = document.getElementById("openTabBtn");
const protonModal = document.getElementById("protonModal");
const closeProton = document.getElementById("closeProton");
const openProtonBtn = document.getElementById("openProtonBtn");
const recentList = document.getElementById("recentList");
const usageWidget = document.getElementById("usageWidget");
const appsGrid = document.getElementById("appsGrid");
const serviceStatus = document.getElementById("serviceStatus");
const serviceTimer = document.getElementById("serviceTimer");
const dock = document.getElementById("dock");
const cmdPalette = document.getElementById("commandPalette");
const cmdInput = document.getElementById("cmdInput");
const cmdList = document.getElementById("cmdList");
const notificationsEl = document.getElementById("notifications");
const workspaceTabs = document.getElementById("workspaceTabs");
const saveWorkspaceBtn = document.getElementById("saveWorkspaceBtn");
const saveLayoutBtn = document.getElementById("saveLayoutBtn");
const windowModeBtn = document.getElementById("windowModeBtn");
const contentSearchInput = document.getElementById("contentSearchInput");
const contentSearchBtn = document.getElementById("contentSearchBtn");
const contentResults = document.getElementById("contentResults");
const logsModal = document.getElementById("logsModal");
const logsContent = document.getElementById("logsContent");
const closeLogs = document.getElementById("closeLogs");
const snapLeftBtn = document.getElementById("snapLeftBtn");
const snapCenterBtn = document.getElementById("snapCenterBtn");
const snapRightBtn = document.getElementById("snapRightBtn");

const newFolderBtn = document.getElementById("newFolderBtn");
const newFileBtn = document.getElementById("newFileBtn");
const uploadBtn = document.getElementById("uploadBtn");
const uploadInput = document.getElementById("uploadInput");
const renameBtn = document.getElementById("renameBtn");
const moveBtn = document.getElementById("moveBtn");
const deleteBtn = document.getElementById("deleteBtn");
const copyPathBtn = document.getElementById("copyPathBtn");
const vimCmdBtn = document.getElementById("vimCmdBtn");
const terminalBtn = document.getElementById("terminalBtn");
const mediaAllBtn = document.getElementById("mediaAll");
const mediaImgBtn = document.getElementById("mediaImages");
const mediaVidBtn = document.getElementById("mediaVideo");
const mediaAudBtn = document.getElementById("mediaAudio");
const filesBtn = document.getElementById("filesMode");

const qs = (obj) =>
  Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

async function apiPost(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Request failed");
  }
  return res.json();
}

const api = {
  async roots() {
    const res = await fetch("/api/roots");
    return res.json();
  },
  async list(rootId, path) {
    const res = await fetch(`/api/list?${qs({ root: rootId, path })}`);
    return res.json();
  },
  async search(rootId, q) {
    const res = await fetch(`/api/search?${qs({ root: rootId, q })}`);
    return res.json();
  },
  async stats(rootId, path) {
    const res = await fetch(`/api/stats?${qs({ root: rootId, path })}`);
    return res.json();
  },
  async recent(rootId) {
    const res = await fetch(`/api/recent?${qs({ root: rootId })}`);
    return res.json();
  },
  async usage(rootId) {
    const res = await fetch(`/api/usage?${qs({ root: rootId })}`);
    return res.json();
  },
  async apps() {
    const res = await fetch("/api/apps");
    return res.json();
  },
  async media(rootId, kind) {
    const res = await fetch(`/api/media?${qs({ root: rootId, kind })}`);
    return res.json();
  },
  async indexStatus(rootId) {
    const res = await fetch(`/api/index/status?${qs({ root: rootId })}`);
    return res.json();
  },
  async indexBuild(rootId) {
    const res = await fetch(`/api/index/build?${qs({ root: rootId })}`);
    return res.json();
  },
  async searchContent(rootId, q) {
    const res = await fetch(`/api/search_content?${qs({ root: rootId, q })}`);
    return res.json();
  },
  async smart(rootId, kind) {
    const res = await fetch(`/api/smart?${qs({ root: rootId, kind })}`);
    return res.json();
  },
};


const SERVICE_REFRESH = 30;
let serviceCountdown = SERVICE_REFRESH;


let servicesCache = null;
async function fetchServices() {
  const res = await fetch('/api/services/list');
  const data = await res.json();
  servicesCache = data.services || {};
  return servicesCache;
}

async function fetchServiceStatus() {
  const res = await fetch('/api/services/status');
  return res.json();
}

async function renderServices() {
  if (!serviceStatus) return;
  const services = await fetchServices();
  const status = await fetchServiceStatus();
  serviceStatus.innerHTML = "";
  Object.keys(services).forEach((key) => {
    const svc = services[key];
    const st = status.status?.[key] || { running: false };
    const card = document.createElement('div');
    card.className = 'service-card ' + (st.running ? 'online' : 'offline');
    card.innerHTML = `
      <div class="dot"></div>
      <div class="name">${svc.name}</div>
      <div class="service-actions">
        <button class="btn ghost" data-action="start">Start</button>
        <button class="btn ghost" data-action="stop">Stop</button>
        <button class="btn ghost" data-action="logs">Logs</button>
        ${svc.logic_path ? '<button class="btn ghost" data-action="logic">Logic</button>' : ''}
        <a href="${svc.url}" target="_blank">Open</a>
      </div>
    `;
    card.querySelectorAll('button').forEach((b) => {
      b.addEventListener('click', async () => {
        const action = b.getAttribute('data-action');
        if (action === 'start') await fetch('/api/services/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
        if (action === 'stop') await fetch('/api/services/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
        if (action === 'logs') {
          const lr = await fetch(`/api/services/logs?key=${key}`);
          const ld = await lr.json();
          logsContent.textContent = ld.logs || '';
          logsModal.classList.remove('hidden');
        }
        if (action === 'logic' && svc.logic_path) {
          const url = `/edit?${qs({ root: state.rootId, path: svc.logic_path.replace(servicesCache.dashboard?.root || '/mnt/sdcard/AA_MY_DRIVE','') })}`;
          window.open(url, '_blank');
        }
        renderServices();
      });
    });
    serviceStatus.appendChild(card);
  });
}

const services = [
  { name: "Master Dashboard", url: "http://localhost:8765", health: "/health" },
  { name: "Analytics", url: "http://localhost:8777", health: "/_stcore/health" },
  { name: "Crypto Bot", url: "http://localhost:8501", health: "/_stcore/health" },
  { name: "XLM Bot", url: "http://localhost:8502", health: "/_stcore/health" },
];

async function checkService(svc) {
  try {
    const res = await fetch(svc.url + svc.health, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}


function startServiceTimer() {
  if (!serviceTimer) return;
  serviceTimer.textContent = String(serviceCountdown);
  setInterval(() => {
    serviceCountdown -= 1;
    if (serviceCountdown <= 0) {
      serviceCountdown = SERVICE_REFRESH;
      renderServices();
    }
    serviceTimer.textContent = String(serviceCountdown);
  }, 1000);
}

async function renderServices() {
  if (!serviceStatus) return;
  const statuses = await Promise.all(services.map(checkService));
  serviceStatus.innerHTML = "";
  services.forEach((svc, i) => {
    const card = document.createElement("div");
    card.className = "service-card " + (statuses[i] ? "online" : "offline");
    card.innerHTML = `
      <div class="dot"></div>
      <div class="name">${svc.name}</div>
      <a href="${svc.url}" target="_blank">Open</a>
    `;
    serviceStatus.appendChild(card);
  });
}


const notifications = [];
function notify(msg) {
  if (!notificationsEl) return;
  const entry = { msg, ts: new Date().toLocaleTimeString() };
  notifications.unshift(entry);
  if (notifications.length > 20) notifications.pop();
  notificationsEl.innerHTML = notifications.map(n => `<div class="notification">${n.ts} · ${n.msg}</div>`).join("");
}



function captureLayout() {
  const panels = document.querySelectorAll(".panel");
  const layout = {};
  panels.forEach((p) => {
    const cls = Array.from(p.classList).find(c => ["left","center","right"].includes(c));
    if (!cls) return;
    layout[cls] = {
      left: p.style.left || "",
      top: p.style.top || "",
      right: p.style.right || "",
      width: p.style.width || "",
      height: p.style.height || "",
    };
  });
  return layout;
}

function applyLayout(layout) {
  if (!layout) return;
  Object.keys(layout).forEach((k) => {
    const p = document.querySelector(`.panel.${k}`);
    if (!p) return;
    const l = layout[k];
    p.style.left = l.left || "";
    p.style.top = l.top || "";
    p.style.right = l.right || "";
    p.style.width = l.width || "";
    p.style.height = l.height || "";
  });
}


function saveLastWorkspace(idx) {
  localStorage.setItem("aa_last_workspace", String(idx));
}

function loadLastWorkspaceIndex() {
  const v = localStorage.getItem("aa_last_workspace");
  return v ? parseInt(v, 10) : 0;
}

function loadWorkspaces() {
  const raw = localStorage.getItem("aa_workspaces");
  return raw ? JSON.parse(raw) : [];
}

function saveWorkspaces(list) {
  localStorage.setItem("aa_workspaces", JSON.stringify(list));
}

function renderWorkspaces() {
  if (!workspaceTabs) return;
  const workspaces = loadWorkspaces();
  workspaceTabs.innerHTML = "";
  const activeIdx = loadLastWorkspaceIndex();
  workspaces.forEach((w, idx) => {
    const el = document.createElement("div");
    el.className = "workspace-tab" + (idx === activeIdx ? " active" : "");
    el.textContent = w.name;
    el.addEventListener("click", () => {
      state.rootId = w.rootId;
      state.path = w.path;
      state.mode = w.mode || "files";
      state.mediaKind = w.mediaKind || null;
      saveLastWorkspace(idx);
      if (w.layout) {
        document.body.classList.add("window-mode");
        applyLayout(w.layout);
      }
      loadAll();
    });
    workspaceTabs.appendChild(el);
  });
}

function saveCurrentWorkspace() {
  const name = prompt("Workspace name?");
  if (!name) return;
  const workspaces = loadWorkspaces();
  workspaces.unshift({ name, rootId: state.rootId, path: state.path, mode: state.mode, mediaKind: state.mediaKind, layout: captureLayout() });
  saveWorkspaces(workspaces.slice(0, 10));
  renderWorkspaces();
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = bytes;
  let i = -1;
  do {
    size /= 1024;
    i += 1;
  } while (size >= 1024 && i < units.length - 1);
  return `${size.toFixed(1)} ${units[i]}`;
}


function renderDock() {
  if (!dock) return;
  dock.innerHTML = [
    { label: "Files", action: () => { state.mode = "files"; loadAll(); } },
    { label: "Media", action: () => { state.mode = "media"; state.mediaKind = null; loadAll(); } },
    { label: "Images", action: () => { state.mode = "media"; state.mediaKind = "image"; loadAll(); } },
    { label: "Audio", action: () => { state.mode = "media"; state.mediaKind = "audio"; loadAll(); } },
    { label: "Analytics", action: () => window.open("http://localhost:8777", "_blank") },
  ].map((item) => {
    const el = document.createElement("div");
    el.className = "dock-item";
    el.textContent = item.label;
    el.addEventListener("click", item.action);
    return el;
  }).reduce((frag, el) => { frag.appendChild(el); return frag; }, document.createDocumentFragment());
}

function formatTime(iso) {
  const date = new Date(iso);
  return date.toLocaleString();
}

function openFilePage(item) {
  const url = `/file?${qs({ root: state.rootId, path: item.path })}`;
  window.open(url, "_blank");
}

function renderRoots() {
  rootsEl.innerHTML = "";
  state.roots.forEach((root) => {
    const div = document.createElement("div");
    div.className = "root-item" + (root.id === state.rootId ? " active" : "");
    div.textContent = root.name;
    div.addEventListener("click", async () => {
      state.rootId = root.id;
      state.path = "";
      await ensureIndex();
      await loadAll();
      renderRoots();
    });
    rootsEl.appendChild(div);
  });
}

function renderBreadcrumbs() {
  breadcrumbsEl.innerHTML = "";
  const parts = state.path ? state.path.split("/") : [];
  const all = ["", ...parts];
  let acc = "";
  all.forEach((part, idx) => {
    if (idx === 0) {
      part = "root";
      acc = "";
    } else {
      acc = acc ? `${acc}/${part}` : part;
    }
    const span = document.createElement("span");
    span.textContent = part || "root";
    span.addEventListener("click", () => {
      state.path = acc;
      state.mode = "files";
      loadList();
    });
    breadcrumbsEl.appendChild(span);
  });
}


function renderBreadcrumbs2() {
  if (!breadcrumbs2) return;
  breadcrumbs2.innerHTML = "";
  const parts = state.secondary.path ? state.secondary.path.split("/") : [];
  const all = ["", ...parts];
  let acc = "";
  all.forEach((part, idx) => {
    if (idx === 0) {
      part = "root";
      acc = "";
    } else {
      acc = acc ? `${acc}/${part}` : part;
    }
    const span = document.createElement("span");
    span.textContent = part || "root";
    span.addEventListener("click", () => {
      state.secondary.path = acc;
      loadListSecondary();
    });
    breadcrumbs2.appendChild(span);
  });
}

function renderGrid2(items) {
  if (!gridEl2) return;
  gridEl2.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.path = item.path;
    card.dataset.isdir = String(!!item.is_dir);
    const title = document.createElement("div");
    title.className = "name";
    title.textContent = item.name;
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = item.is_dir ? "folder" : formatSize(item.size);
    card.appendChild(title);
    card.appendChild(meta);
    card.addEventListener("click", () => {
      if (item.is_dir) {
        state.secondary.path = item.path;
        loadListSecondary();
      } else {
        state.selected = item;
        renderPreview(item);
      }
    });
    card.setAttribute("draggable", true);
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", item.path);
    });
    card.addEventListener("dblclick", () => {
      if (!item.is_dir) openFilePage(item);
    });
    gridEl2.appendChild(card);
  });
}

async function loadListSecondary() {
  if (!state.split) return;
  if (state.secondary.rootId === null) state.secondary.rootId = state.rootId;
  const data = await api.list(state.secondary.rootId, state.secondary.path);
  renderBreadcrumbs2();
  renderGrid2(data.items);
}


async function handleDropMove(targetCard, dataPath) {
  if (!targetCard || !dataPath) return;
  if (targetCard.dataset.isdir !== 'true') return;
  const dest = targetCard.dataset.path;
  await apiPost('/api/move', { root: state.rootId, path: dataPath, dest });
  notify(`Moved to ${dest}`);
  await loadAll();
}

function renderGrid(items) {
  gridEl.innerHTML = "";
  state.selectedSet.clear();
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.path = item.path;
    card.dataset.isdir = String(!!item.is_dir);
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "select-box";
    card.appendChild(checkbox);
    const title = document.createElement("div");
    title.className = "name";
    title.textContent = item.name;

    if (item.group === "image") {
      const thumb = document.createElement("img");
      thumb.className = "thumb";
      thumb.src = `/api/thumb?${qs({ root: state.rootId, path: item.path })}`;
      card.appendChild(thumb);
    }
    const meta = document.createElement("div");
    meta.className = "meta";
    if (!item.is_dir) {
      meta.innerHTML = `${formatSize(item.size)} · <a class="open-link" href="/file?${qs({ root: state.rootId, path: item.path })}" target="_blank">Open</a> · <a class="open-link" href="/edit?${qs({ root: state.rootId, path: item.path })}" target="_blank">Edit</a>`;
    } else {
      meta.textContent = "folder";
    }
    card.appendChild(title);
    card.appendChild(meta);
    card.addEventListener("click", (e) => {
      if (e.shiftKey) {
        checkbox.checked = !checkbox.checked;
        if (checkbox.checked) state.selectedSet.add(item); else state.selectedSet.delete(item);
        return;
      }
      if (item.is_dir) {
        state.path = item.path;
        state.mode = "files";
        loadList();
      } else {
        state.selected = item;
        renderPreview(item);
      }
    });
    card.setAttribute("draggable", true);
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", item.path);
    });
    card.addEventListener("dblclick", () => {
      if (!item.is_dir) openFilePage(item);
    });
    gridEl.appendChild(card);
  });
}

function setPreviewHtml(html) {
  previewEl.innerHTML = html;
}

function renderPlaylist(items) {
  if (!items.length) return;
  const list = items.slice(0, 50);
  const html = list.map(i => `<div class="playlist-item" data-path="${i.path}">${i.name}</div>`).join("");
  previewEl.innerHTML = `<div class="playlist">${html}</div>`;
  previewEl.querySelectorAll(".playlist-item").forEach(el => {
    el.addEventListener("click", () => {
      const path = el.getAttribute("data-path");
      renderPreview({ path, mime: "audio/mpeg", name: el.textContent });
    });
  });
}

function renderPreview(item) {
  const url = `/api/raw?${qs({ root: state.rootId, path: item.path })}`;
  const mime = item.mime || "";
  if (mime.startsWith("image/")) {
    setPreviewHtml(`<img src="${url}" alt="${item.name}" />`);
  } else if (mime.startsWith("video/")) {
    setPreviewHtml(`<video controls src="${url}"></video>`);
  } else if (mime.startsWith("audio/")) {
    setPreviewHtml(`<audio controls src="${url}"></audio>`);
  } else if (mime === "application/pdf") {
    setPreviewHtml(`<iframe src="${url}" height="100%"></iframe>`);
  } else {
    fetch(url)
      .then((res) => res.text())
      .then((text) => {
        const snippet = text.length > 200000 ? text.slice(0, 200000) + "\n..." : text;
        setPreviewHtml(`<pre>${escapeHtml(snippet)}</pre>`);
      })
      .catch(() => setPreviewHtml(`<div class="preview-empty">Preview failed.</div>`));
  }
}

function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

function renderUsage(data) {
  const pct = data.percent || 0;
  usageWidget.innerHTML = `
    <div>Total: ${formatSize(data.total)}</div>
    <div>Used: ${formatSize(data.used)}</div>
    <div>Free: ${formatSize(data.free)}</div>
    <div class="usage-bar"><div class="usage-fill" style="width:${pct}%"></div></div>
  `;
}

function renderRecent(items) {
  recentList.innerHTML = "";
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "recent-item";
    row.innerHTML = `<div>${item.name}</div><span>${formatTime(item.mtime_iso)}</span>`;
    row.addEventListener("click", () => {
      state.selected = item;
      renderPreview(item);
    });
    row.addEventListener("dblclick", () => openFilePage(item));
    recentList.appendChild(row);
  });
}

function renderApps(apps) {
  appsGrid.innerHTML = "";
  apps.forEach((app) => {
    const tile = document.createElement("div");
    tile.className = "app-tile";
    tile.innerHTML = `<div>${app.name}</div><div class="tag">${app.tag || "app"}</div>`;
    tile.addEventListener("click", () => {
      if (app.url) {
        window.open(app.url, "_blank");
      } else if (app.path) {
        state.path = app.path.replace(/^\//, "");
        state.mode = "files";
        loadList();
      }
    });
    appsGrid.appendChild(tile);
  });
}

async function ensureIndex() {
  const status = await api.indexStatus(state.rootId);
  if (!status.ok) {
    await api.indexBuild(state.rootId);
  }
}

async function loadList() {
  const data = await api.list(state.rootId, state.path);
  renderBreadcrumbs();
  renderGrid(data.items);
}

async function loadMedia(kind = null) {
  const data = await api.media(state.rootId, kind);
  renderBreadcrumbs();
  renderGrid(data.results || []);
  if (kind === "audio") {
    renderPlaylist(data.results || []);
  }
}

async function loadWidgets() {
  const [usage, recent, apps] = await Promise.all([
    api.usage(state.rootId),
    api.recent(state.rootId),
    api.apps(),
  ]);
  renderUsage(usage);
  renderRecent(recent.results || []);
  renderApps(apps.apps || []);
}

async function loadAll() {
  if (state.mode === "media") {
    await loadMedia(state.mediaKind);
  } else if (state.mode === "smart") {
    const data = await api.smart(state.rootId, null);
    renderGrid(data.results || []);
  } else {
    await loadList();
  }
  await loadWidgets();
}

async function doSearch() {
  const q = searchInput.value.trim();
  if (!q) return;
  const data = await api.search(state.rootId, q);
  renderGrid(data.results);
  if (data.truncated) {
    setPreviewHtml(`<div class="preview-empty">Search truncated. Refine query.</div>`);
  }
}


const commands = [
  { label: "New Folder", run: () => newFolderBtn.click() },
  { label: "New File", run: () => newFileBtn.click() },
  { label: "Upload", run: () => uploadBtn.click() },
  { label: "Rename", run: () => renameBtn.click() },
  { label: "Move", run: () => moveBtn.click() },
  { label: "Delete", run: () => deleteBtn.click() },
  { label: "Open Selected", run: () => state.selected && openFilePage(state.selected) },
  { label: "Edit Selected", run: () => state.selected && window.open(`/edit?${qs({ root: state.rootId, path: state.selected.path })}`, "_blank") },
  { label: "Files Mode", run: () => { state.mode = "files"; loadAll(); } },
  { label: "Media Mode", run: () => { state.mode = "media"; state.mediaKind = null; loadAll(); } },
  { label: "Images", run: () => { state.mode = "media"; state.mediaKind = "image"; loadAll(); } },
  { label: "Video", run: () => { state.mode = "media"; state.mediaKind = "video"; loadAll(); } },
  { label: "Audio", run: () => { state.mode = "media"; state.mediaKind = "audio"; loadAll(); } },
  { label: "Analytics", run: () => window.open("http://localhost:8777", "_blank") },
];

function openPalette() {
  if (!cmdPalette) return;
  cmdPalette.classList.remove("hidden");
  cmdInput.value = "";
  renderCmdList("");
  cmdInput.focus();
}

function closePalette() {
  cmdPalette.classList.add("hidden");
}

function renderCmdList(filter) {
  const items = commands.filter(c => c.label.toLowerCase().includes(filter.toLowerCase()));
  cmdList.innerHTML = "";
  items.forEach((c, idx) => {
    const el = document.createElement("div");
    el.className = "cmd-item" + (idx === 0 ? " active" : "");
    el.textContent = c.label;
    el.addEventListener("click", () => { c.run(); closePalette(); });
    cmdList.appendChild(el);
  });
}


async function runContentSearch() {
  const q = contentSearchInput.value.trim();
  if (!q) return;
  const data = await api.searchContent(state.rootId, q);
  renderContentResults(data.results || []);
}

function renderContentResults(results) {
  if (!contentResults) return;
  contentResults.innerHTML = "";
  results.slice(0, 50).forEach((r) => {
    const el = document.createElement("div");
    el.className = "content-result";
    el.textContent = r;
    el.addEventListener("click", () => {
      const parts = r.split(":");
      const relPath = parts.slice(0, -2).join(":");
      if (!relPath) return;
      const url = `/file?${qs({ root: state.rootId, path: relPath })}`;
      window.open(url, "_blank");
    });
    contentResults.appendChild(el);
  });
}


function toggleWindowMode() {
  document.body.classList.toggle("window-mode");
}

function makeDraggable(panel) {
  const handle = document.createElement("div");
  handle.className = "drag-handle";
  handle.textContent = "drag";
  panel.insertBefore(handle, panel.firstChild);
  let offsetX = 0, offsetY = 0, dragging = false;
  handle.addEventListener("mousedown", (e) => {
    dragging = true;
    const rect = panel.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    panel.style.left = `${e.clientX - offsetX}px`;
    panel.style.top = `${e.clientY - offsetY}px`;
  });
  window.addEventListener("mouseup", () => { dragging = false; });
}


function toggleSplit() {
  state.split = !state.split;
  if (splitWrap) splitWrap.classList.toggle("enabled", state.split);
  if (state.split) loadListSecondary();
}

function openProton(url) {
  window.open(url, "_blank");
}

function setupShortcuts() {
  document.querySelectorAll(".shortcuts button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const jump = btn.getAttribute("data-jump");
      state.path = jump.replace(/^\//, "");
      state.mode = "files";
      loadList();
    });
  });
}

function setupProtonButtons() {
  document.querySelectorAll(".proton-btn").forEach((btn) => {
    btn.addEventListener("click", () => openProton(btn.dataset.url));
  });
}

function parseUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const root = params.get("root");
  const path = params.get("path");
  const open = params.get("open");
  if (root !== null) state.rootId = parseInt(root, 10);
  if (path) state.path = path;
  return open;
}

function openInNewTab() {
  const open = state.selected ? state.selected.path : "";
  const url = `/view?${qs({ root: state.rootId, path: state.path, open })}`;
  window.open(url, "_blank");
}

async function init() {
  const rootData = await api.roots();
  state.roots = rootData.roots;
  if (state.rootId === null) {
    state.rootId = rootData.default ?? 0;
  }
  renderRoots();
  const open = parseUrlParams();
  await ensureIndex();
  await loadAll();
  if (open) {
    const item = await api.stats(state.rootId, open);
    state.selected = item;
    renderPreview(item);
  }
}

filesBtn.addEventListener("click", async () => {
  state.mode = "files";
  await loadAll();
});
mediaAllBtn.addEventListener("click", async () => {
  state.mode = "media";
  state.mediaKind = null;
  await loadAll();
});
mediaImgBtn.addEventListener("click", async () => {
  state.mode = "media";
  state.mediaKind = "image";
  await loadAll();
});
mediaVidBtn.addEventListener("click", async () => {
  state.mode = "media";
  state.mediaKind = "video";
  await loadAll();
});
mediaAudBtn.addEventListener("click", async () => {
  state.mode = "media";
  state.mediaKind = "audio";
  await loadAll();
});

searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});
refreshBtn.addEventListener("click", loadAll);
openTabBtn.addEventListener("click", openInNewTab);
openProtonBtn.addEventListener("click", () => protonModal.classList.remove("hidden"));
closeProton.addEventListener("click", () => protonModal.classList.add("hidden"));
closeLogs.addEventListener("click", () => logsModal.classList.add("hidden"));


newFolderBtn.addEventListener("click", async () => {
  const name = prompt("Folder name?");
  if (!name) return;
  await apiPost("/api/mkdir", { root: state.rootId, path: state.path, name });
  await loadAll();
});

newFileBtn.addEventListener("click", async () => {
  const name = prompt("File name?");
  if (!name) return;
  await apiPost("/api/touch", { root: state.rootId, path: state.path, name });
  await loadAll();
});

uploadBtn.addEventListener("click", () => uploadInput.click());

uploadInput.addEventListener("change", async (e) => {
  const files = Array.from(e.target.files || []);
  for (const file of files) {
    const form = new FormData();
    form.append("root", state.rootId);
    form.append("path", state.path);
    form.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error("Upload failed");
  }
  uploadInput.value = "";
  await loadAll();
});

renameBtn.addEventListener("click", async () => {
  if (!state.selected) return alert("Select a file first");
  const name = prompt("New name?", state.selected.name);
  if (!name) return;
  await apiPost("/api/rename", { root: state.rootId, path: state.selected.path, name });
  await loadAll();
});

moveBtn.addEventListener("click", async () => {
  const targets = state.selectedSet.size ? Array.from(state.selectedSet) : (state.selected ? [state.selected] : []);
  if (!targets.length) return alert("Select files first");
  const dest = prompt("Move to folder (path from root):", "");
  if (dest === null) return;
  for (const t of targets) {
    await apiPost("/api/move", { root: state.rootId, path: t.path, dest });
  }
  await loadAll();
});

deleteBtn.addEventListener("click", async () => {
  const targets = state.selectedSet.size ? Array.from(state.selectedSet) : (state.selected ? [state.selected] : []);
  if (!targets.length) return alert("Select files first");
  if (!confirm(`Delete ${targets.length} item(s)?`)) return;
  for (const t of targets) {
    await apiPost("/api/delete", { root: state.rootId, path: t.path });
  }
  state.selected = null;
  state.selectedSet.clear();
  await loadAll();
});

copyPathBtn.addEventListener("click", async () => {
  if (!state.selected) return alert("Select a file first");
  const fullPath = `${state.roots[state.rootId].path}/${state.selected.path}`.replace(/\/\/+/, "/");
  await navigator.clipboard.writeText(fullPath);
});

vimCmdBtn.addEventListener("click", async () => {
  if (!state.selected) return alert("Select a file first");
  const fullPath = `${state.roots[state.rootId].path}/${state.selected.path}`.replace(/\/\/+/, "/");
  await navigator.clipboard.writeText(`vim "${fullPath}"`);
  alert("Vim command copied to clipboard");
});

terminalBtn.addEventListener("click", async () => {
  const res = await fetch("/api/terminal/start", { method: "POST" });
  if (res.ok) {
    const data = await res.json();
    window.open(data.url, "_blank");
  } else {
    alert("ttyd not installed. Install ttyd to enable web terminal.");
  }
});

setupShortcuts();
setupProtonButtons();


// Drag & drop upload
gridEl.addEventListener("dragover", (e) => {
  e.preventDefault();
  gridEl.classList.add("dragging");
});
gridEl.addEventListener("dragleave", () => {
  gridEl.classList.remove("dragging");
});
gridEl.addEventListener("drop", async (e) => {
  e.preventDefault();
  gridEl.classList.remove("dragging");
  const files = Array.from(e.dataTransfer.files || []);
  for (const file of files) {
    const form = new FormData();
    form.append("root", state.rootId);
    form.append("path", state.path);
    form.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error("Upload failed");
  }
  await loadAll();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/sw.js");
}

// Drop to move into secondary pane directory
if (gridEl2) {
  gridEl2.addEventListener("dragover", (e) => e.preventDefault());
  gridEl2.addEventListener("drop", async (e) => {
    e.preventDefault();
    const path = e.dataTransfer.getData("text/plain");
    if (!path) return;
    await apiPost('/api/move', { root: state.rootId, path, dest: state.secondary.path });
    notify(`Moved to ${state.secondary.path || '/'}`);
    await loadAll();
  });
}

if (gridEl) {
  gridEl.addEventListener("dragover", (e) => e.preventDefault());
  gridEl.addEventListener("drop", async (e) => {
    e.preventDefault();
    const path = e.dataTransfer.getData("text/plain");
    if (!path) return;
    await apiPost('/api/move', { root: state.rootId, path, dest: state.path });
    notify(`Moved to ${state.path || '/'}`);
    await loadAll();
  });
}

init();
