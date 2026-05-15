// Moltbook -- vanilla JS, fetch + render the panes every N seconds.
// No framework. Uses DOM methods (createElement + textContent) so user-supplied
// content from Blinko / mailbox / activity_feed cannot inject HTML.

(function () {
  "use strict";

  let cfg = { refresh_seconds: 30, title: "Moltbook", subtitle: "Lucrex Notebook" };

  // ---- helpers ----
  const $ = (sel) => document.querySelector(sel);
  const fmt = (n) => String(n).padStart(2, "0");

  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === "class") e.className = attrs[k];
        else if (k === "text") e.textContent = attrs[k];
        else e.setAttribute(k, attrs[k]);
      }
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach((c) => {
        if (c == null) return;
        if (typeof c === "string") e.appendChild(document.createTextNode(c));
        else e.appendChild(c);
      });
    }
    return e;
  }

  function replaceChildren(parent, ...nodes) {
    while (parent.firstChild) parent.removeChild(parent.firstChild);
    nodes.forEach((n) => n && parent.appendChild(n));
  }

  async function fetchJson(path) {
    try {
      const r = await fetch(path, { cache: "no-store" });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) {
      return null;
    }
  }

  // ---- clock + hero meta ----
  function tickClock() {
    const d = new Date();
    const clock = $("#clock");
    if (clock) clock.textContent = `${fmt(d.getHours())}:${fmt(d.getMinutes())}:${fmt(d.getSeconds())}`;
    const heroDate = $("#hero-date");
    if (heroDate) {
      heroDate.textContent = d.toLocaleDateString("en-US",
        { weekday: "long", month: "long", day: "numeric", year: "numeric" });
    }
    const heroRefresh = $("#hero-refresh");
    if (heroRefresh) heroRefresh.textContent = `refresh: ${cfg.refresh_seconds}s`;
  }

  // ---- memory pane ----
  async function renderMemory() {
    const data = await fetchJson("/api/memory");
    const pill = $("#memory-pill");
    const card = $("#memory-card");
    if (!data) {
      if (pill) { pill.className = "pill pill-unknown"; pill.textContent = "memory: ?"; }
      if (card) replaceChildren(card, el("div", { class: "skeleton", text: "memory probe failed" }));
      return;
    }
    const state = data.state || "UNKNOWN";
    if (pill) {
      pill.textContent = `memory: ${state.toLowerCase()}`;
      pill.className = "pill " + (
        state === "CONNECTED" ? "pill-ok"
        : state === "DEGRADED" ? "pill-warn"
        : state === "OFFLINE" ? "pill-bad"
        : "pill-unknown"
      );
    }
    if (!card) return;

    const stateLine = el("div", { class: "mem-state-line" },
      el("span", { class: `mem-state s-${state}`, text: state }));

    let detail;
    if (state === "CONNECTED") {
      detail = el("div", { class: "mem-detail" }, [
        document.createTextNode("source: "),
        el("b", { text: data.source_url || "" }),
        el("br"),
        document.createTextNode("notes: "),
        el("b", { text: String(data.notes_count) }),
        el("br"),
        document.createTextNode(`latest update: ${data.latest_update || ""}`),
        el("br"),
        document.createTextNode(`probe time: ${data.probe_ms || 0} ms`),
      ]);
    } else if (state === "DEGRADED") {
      detail = el("div", { class: "mem-detail" }, [
        document.createTextNode("source: "),
        el("b", { text: "local fallback" }),
        el("br"),
        document.createTextNode(`path: ${data.source_path || ""}`),
        el("br"),
        document.createTextNode("notes: "),
        el("b", { text: String(data.notes_count) }),
        el("br"),
        document.createTextNode(`last synced: ${data.latest_update || "?"}`),
        el("br"),
        el("span", {
          style: "color: var(--gold)",
          text: "Heads up: anything written after the last sync isn't on this fallback."
        }),
      ]);
    } else if (state === "OFFLINE") {
      detail = el("div", { class: "mem-detail" }, [
        "No remote Blinko, no local fallback. ",
        el("br"),
        "Operating without persistent memory this session.",
      ]);
    } else {
      detail = el("div", { class: "mem-detail", text: `state: ${state}` });
    }

    replaceChildren(card, stateLine, detail);
  }

  // ---- family pane ----
  async function renderFamily() {
    const data = await fetchJson("/api/family");
    const grid = $("#family-grid");
    if (!grid) return;
    if (!data || !data.devices) {
      replaceChildren(grid, el("div", { class: "skeleton", text: "family registry unavailable" }));
      return;
    }
    const cards = data.devices.map((d) => {
      const name = d.name || "?";
      // crude online inference -- caller can refine later
      let status = "warn";
      if (name.includes("e5-mother") || name.includes("acemagician")) status = "online";
      else if (name.includes("latitude") || name.includes("dell")) status = "offline";
      else if (name.includes("z-fold") || name.includes("phone")) status = "warn";

      return el("div", { class: `card glass device status-${status}` }, [
        el("div", { class: "device-head" }, [
          el("span", { class: "device-status-dot" }),
          el("span", { text: name }),
        ]),
        el("div", { class: "device-ip", text: d.tailnet_ip || "" }),
        el("div", { class: "device-role", text: d.role || "" }),
      ]);
    });
    replaceChildren(grid, ...cards);
  }

  // ---- audit pane (clickable cards, grouped by date, classification-aware) ----
  let classificationCache = null;
  async function getClassification() {
    if (classificationCache) return classificationCache;
    classificationCache = await fetchJson("/api/audit/classification") || { codes: {}, threads: {}, sessions: {} };
    return classificationCache;
  }

  function dayKey(iso) {
    return (iso || "").slice(0, 10); // YYYY-MM-DD
  }
  function prettyDayLabel(yyyy_mm_dd) {
    if (!yyyy_mm_dd) return "—";
    try {
      const d = new Date(yyyy_mm_dd + "T12:00:00");
      if (isNaN(d)) return yyyy_mm_dd;
      return d.toLocaleDateString("en-US",
        { weekday: "long", month: "long", day: "numeric", year: "numeric" });
    } catch (_) { return yyyy_mm_dd; }
  }
  function timeOfDay(iso) {
    try {
      const d = new Date(iso);
      if (isNaN(d)) return "";
      return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    } catch (_) { return ""; }
  }

  async function renderAudit() {
    const data = await fetchJson("/api/audit");
    const list = $("#audit-list");
    if (!list) return;
    const entries = data && Array.isArray(data.entries) ? data.entries : [];
    if (!entries.length) {
      replaceChildren(list, el("div", { class: "skeleton", text: "no audit entries yet" }));
      return;
    }
    const cls = await getClassification();
    const codeName = (code) => (code && cls.codes && cls.codes[code]) || "";

    // Group by date (newest first)
    const groups = new Map(); // dayKey -> [entries]
    entries.forEach((e) => {
      const k = dayKey(e.date);
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(e);
    });
    const sortedDays = [...groups.keys()].sort().reverse();

    const fragments = [];
    sortedDays.forEach((day) => {
      const dayEntries = groups.get(day).slice().sort((a, b) =>
        (b.date || "").localeCompare(a.date || ""));
      // group header
      fragments.push(el("div", { class: "audit-day-header" }, [
        el("span", { class: "audit-day-label", text: prettyDayLabel(day) }),
        el("span", { class: "audit-day-count", text: `${dayEntries.length} entr${dayEntries.length === 1 ? "y" : "ies"}` }),
      ]));
      // cards for this day
      dayEntries.forEach((e) => {
        const card = el("div", { class: "audit-card", role: "button", tabindex: "0",
                                  "data-entry-id": e.id || "" });
        card.appendChild(el("span", { class: "audit-card-arrow", text: "↗" }));

        // classification code badge in the head row
        const head = el("div", { class: "audit-card-head" }, [
          el("div", { class: "audit-card-title-wrap" }, [
            e.category ? el("span", {
              class: "audit-code",
              title: codeName(e.category) || "category",
              text: e.category,
            }) : null,
            el("span", { class: "audit-card-title", text: e.title || e.id || "(untitled)" }),
          ]),
          el("div", { class: "audit-card-date", text: timeOfDay(e.date) }),
        ]);
        card.appendChild(head);

        if (e.summary) {
          card.appendChild(el("div", { class: "audit-card-summary", text: e.summary }));
        }

        const meta = el("div", { class: "audit-card-meta" });
        if (e.category) {
          meta.appendChild(el("span", {
            class: "audit-tag t-category",
            title: codeName(e.category),
            text: codeName(e.category) ? `${e.category} · ${codeName(e.category).split(" — ")[0]}` : e.category,
          }));
        }
        if (e.thread)  meta.appendChild(el("span", { class: "audit-tag t-thread", text: `thread: ${e.thread}` }));
        if (e.session) meta.appendChild(el("span", { class: "audit-tag t-session", text: e.session }));
        if (e.status)  meta.appendChild(el("span", { class: `audit-tag t-status-${e.status}`, text: e.status }));
        card.appendChild(meta);

        const open = () => openAuditEntry(e.id);
        card.addEventListener("click", open);
        card.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); }
        });
        fragments.push(card);
      });
    });
    replaceChildren(list, ...fragments);
  }

  function shortDate(iso) {
    if (!iso) return "";
    // ISO 8601 with optional offset -- show "Mon May 14, 4:00 PM" style
    try {
      const d = new Date(iso);
      if (isNaN(d)) return iso.slice(0, 10);
      return d.toLocaleDateString("en-US",
        { weekday: "short", month: "short", day: "numeric" })
        + " · " + d.toLocaleTimeString("en-US",
        { hour: "numeric", minute: "2-digit" });
    } catch (_) { return iso.slice(0, 10); }
  }

  // ---- safe HTML insertion (DOMParser + strip dangerous nodes/attrs) ----
  function safeSetHtml(target, htmlString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString || "", "text/html");
    // strip dangerous elements
    doc.querySelectorAll("script, iframe, object, embed, link, meta, style").forEach((n) => n.remove());
    // strip event handlers + javascript: URLs
    doc.querySelectorAll("*").forEach((n) => {
      [...n.attributes].forEach((a) => {
        if (a.name.toLowerCase().startsWith("on")) n.removeAttribute(a.name);
        const val = String(a.value || "").trim().toLowerCase();
        if ((a.name === "href" || a.name === "src") &&
            (val.startsWith("javascript:") || val.startsWith("data:text/html"))) {
          n.removeAttribute(a.name);
        }
      });
    });
    while (target.firstChild) target.removeChild(target.firstChild);
    [...doc.body.childNodes].forEach((c) => target.appendChild(c.cloneNode(true)));
  }

  async function openAuditEntry(id) {
    if (!id) return;
    const modal = $("#audit-modal");
    if (!modal) return;
    document.body.classList.add("modal-open");
    modal.hidden = false;
    $("#modal-eyebrow").textContent = "audit entry";
    $("#modal-title").textContent = "loading…";
    $("#modal-meta").textContent = "";
    $("#modal-summary").textContent = "";
    replaceChildren($("#modal-body"),
      el("div", { class: "skeleton", text: "loading…" }));

    const entry = await fetchJson(`/api/audit/${encodeURIComponent(id)}`);
    if (!entry || entry.error) {
      $("#modal-title").textContent = "Entry not found";
      replaceChildren($("#modal-body"),
        el("div", { class: "skeleton", text: entry?.error || "could not load entry" }));
      return;
    }
    $("#modal-eyebrow").textContent = `audit · ${entry.id}`;
    $("#modal-title").textContent = entry.title || entry.id;

    const meta = $("#modal-meta");
    replaceChildren(meta);
    if (entry.date)   meta.appendChild(el("span", { class: "audit-tag", text: shortDate(entry.date) }));
    if (entry.phase)  meta.appendChild(el("span", { class: "audit-tag t-phase", text: `phase ${entry.phase}` }));
    if (entry.status) meta.appendChild(el("span", { class: `audit-tag t-status-${entry.status}`, text: entry.status }));
    if (entry.agent)  meta.appendChild(el("span", { class: "audit-tag", text: entry.agent }));
    (entry.tags || []).forEach((t) =>
      meta.appendChild(el("span", { class: "audit-tag", text: t })));

    $("#modal-summary").textContent = entry.summary || "";
    // body: server-rendered HTML from our own markdown -> still sanitize defensively
    safeSetHtml($("#modal-body"), entry.html || "");
  }

  function closeAuditModal() {
    const modal = $("#audit-modal");
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
  }

  function wireModalDismiss() {
    const modal = $("#audit-modal");
    if (!modal) return;
    modal.querySelectorAll("[data-close]").forEach((b) =>
      b.addEventListener("click", closeAuditModal));
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !modal.hidden) closeAuditModal();
    });
  }

  // ---- notes pane ----
  async function renderNotes() {
    const data = await fetchJson("/api/notes");
    const list = $("#notes-list");
    if (!list) return;
    if (!data || !Array.isArray(data.items) || data.items.length === 0) {
      replaceChildren(list, el("div", { class: "skeleton", text: "no recent notes" }));
      return;
    }
    const items = data.items.map((n) => el("div", { class: "note" }, [
      el("div", { class: "note-ts", text: n.created_at || "" }),
      el("div", { class: "note-preview", text: n.preview || "" }),
    ]));
    replaceChildren(list, ...items);
  }

  // ---- footer ----
  async function renderFooter() {
    const h = await fetchJson("/api/health");
    const el_ = $("#footer-status");
    if (!el_) return;
    el_.textContent = h ? `server ok · pid ${h.pid} · uptime ${h.uptime_s}s` : "server unreachable";
  }

  // ---- refresh cycle ----
  async function refreshAll() {
    tickClock();
    await Promise.all([
      renderMemory(),
      renderFamily(),
      renderAudit(),
      renderNotes(),
      renderFooter(),
    ]);
  }

  async function bootstrap() {
    const c = await fetchJson("/api/config");
    if (c) cfg = Object.assign(cfg, c);
    wireModalDismiss();
    refreshAll();
    setInterval(tickClock, 1000);
    setInterval(refreshAll, Math.max(5, cfg.refresh_seconds) * 1000);
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
