const state = {
  roots: [],
  rootId: null,
  path: "",
  selected: null,
  apps: [],
};

const rootsEl = document.getElementById("roots");
const gridEl = document.getElementById("grid");
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

const qs = (obj) =>
  Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

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
};

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

function formatTime(iso) {
  const date = new Date(iso);
  return date.toLocaleString();
}

function openRawInTab(item) {
  const url = `/api/raw?${qs({ root: state.rootId, path: item.path })}`;
  window.open(url, "_blank");
}

function renderRoots() {
  rootsEl.innerHTML = "";
  state.roots.forEach((root) => {
    const div = document.createElement("div");
    div.className = "root-item" + (root.id === state.rootId ? " active" : "");
    div.textContent = root.name;
    div.addEventListener("click", () => {
      state.rootId = root.id;
      state.path = "";
      loadAll();
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
      loadList();
    });
    breadcrumbsEl.appendChild(span);
  });
}

function renderGrid(items) {
  gridEl.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
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
        state.path = item.path;
        loadList();
      } else {
        state.selected = item;
        renderPreview(item);
      }
    });
    card.addEventListener("dblclick", () => {
      if (!item.is_dir) openRawInTab(item);
    });
    gridEl.appendChild(card);
  });
}

function setPreviewHtml(html) {
  previewEl.innerHTML = html;
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
    row.addEventListener("dblclick", () => openRawInTab(item));
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
        loadList();
      }
    });
    appsGrid.appendChild(tile);
  });
}

async function loadList() {
  const data = await api.list(state.rootId, state.path);
  renderBreadcrumbs();
  renderGrid(data.items);
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
  await loadList();
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

function openProton(url) {
  window.open(url, "_blank");
}

function setupShortcuts() {
  document.querySelectorAll(".shortcuts button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const jump = btn.getAttribute("data-jump");
      state.path = jump.replace(/^\//, "");
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
  await loadAll();
  if (open) {
    const item = await api.stats(state.rootId, open);
    state.selected = item;
    renderPreview(item);
  }
}

searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});
refreshBtn.addEventListener("click", loadAll);
openTabBtn.addEventListener("click", openInNewTab);
openProtonBtn.addEventListener("click", () => protonModal.classList.remove("hidden"));
closeProton.addEventListener("click", () => protonModal.classList.add("hidden"));

setupShortcuts();
setupProtonButtons();
init();
