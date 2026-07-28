/* deck.js -- v4 orchestrator: always-on glow rail, status bar + footer,
   clickable top-commands, quick toolbar, glass terminal. DOM via textContent. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fmt(n) { n = n || 0; if (n >= 1e6) return (n / 1e6).toFixed(1) + "M"; if (n >= 1e3) return (n / 1e3).toFixed(1) + "k"; return String(n); }

  var QUOTES = ["The edge that never sleeps.", "Every move has a winner. We ARE that winner.",
    "Born in chaos. Most at home in chaos.", "The mind behind the money.", "Always prepared."];
  var sysHist = { mem: [], disk: [], load: [] };

  /* builders */
  function buildSys() {
    var host = $("#sys-rows"); if (!host) return; host.textContent = "";
    ["mem", "disk", "load"].forEach(function (k) {
      var row = el("div", "sys-row");
      row.appendChild(el("span", "lbl", k.toUpperCase()));
      var cv = document.createElement("canvas"); cv.id = "spark-" + k; row.appendChild(cv);
      row.appendChild(el("span", "val", "--"));
      host.appendChild(row);
    });
  }
  function buildQuick() {
    var host = $("#quickcmds"); if (!host) return;
    [{ l: "git status", c: "!git status\r" }, { l: "git log", c: "!git log --oneline -6\r" },
     { l: "disk", c: "!df -h /mnt/sdcard\r" }, { l: "clear", clear: true }].forEach(function (q) {
      var b = el("button", "qcmd", q.l);
      b.addEventListener("click", function () {
        if (q.clear && window.Deck) return window.Deck.clear();
        if (window.Deck) window.Deck.insert(q.c);
      });
      host.appendChild(b);
    });
  }

  /* renderers */
  function kv(host, pairs) { host.textContent = ""; pairs.forEach(function (p) { host.appendChild(el("span", "k", p[0])); host.appendChild(el("span", "v" + (p[2] ? " green" : ""), p[1])); }); }
  function renderTop(items) {
    var host = $("#top-cmds"); if (!host) return; host.textContent = "";
    var max = items.reduce(function (m, x) { return Math.max(m, x.count); }, 1);
    items.forEach(function (x) {
      var row = el("div", "rk"); row.title = "run !" + x.cmd;
      row.appendChild(el("span", "rk-cmd", x.cmd));
      var bar = el("span", "rk-bar"), fill = el("span", "rk-fill");
      fill.style.width = Math.max(6, x.count / max * 100) + "%"; bar.appendChild(fill); row.appendChild(bar);
      row.appendChild(el("span", "rk-n", String(x.count)));
      row.addEventListener("click", function () { if (window.Deck) window.Deck.insert("!" + x.cmd + " "); });
      host.appendChild(row);
    });
  }
  function renderActivity(events) {
    var host = $("#activity"); if (!host) return; host.textContent = "";
    events.slice().reverse().forEach(function (name) { var e = el("div", "a-ev"); e.appendChild(el("i")); e.appendChild(el("span", null, name)); host.appendChild(e); });
  }
  function pushSpark(k, v) {
    sysHist[k].push(v); if (sysHist[k].length > 30) sysHist[k].shift();
    var cv = document.getElementById("spark-" + k);
    if (cv && cv.clientWidth && window.Widgets) window.Widgets.spark(cv, sysHist[k]);
  }

  /* poll */
  async function poll() {
    try {
      var d = await fetch("/api/all").then(function (r) { return r.json(); });
      var v = d.vitals || {}, s = d.session || { tokens: {} }, ctx = d.context || {}, g = d.git || {};
      var tok = s.tokens || {};
      // topbar + footer
      $("#s-uptime").textContent = "up " + (v.uptime || "--");
      $("#s-load").textContent = "load " + (v.load || "--");
      $("#s-stream").hidden = !((s.recent_output || 0) > 200);
      $("#f-uptime").textContent = "up " + (v.uptime || "--");
      $("#f-turns").textContent = (s.turns || 0) + " turns";
      $("#f-model").textContent = s.model || "--";
      // gauge
      if (window.Widgets) window.Widgets.gauge($("#ctx-gauge"), ctx.pct || 0);
      $("#ctx-pct").textContent = (ctx.pct || 0) + "%";
      // burn
      if (window.Widgets) window.Widgets.bars($("#burn-chart"), (d.history || {}).series || []);
      $("#tok-total").textContent = fmt(tok.total || 0);
      // system sparklines
      pushSpark("mem", v.mem_pct || 0); pushSpark("disk", v.disk_pct || 0); pushSpark("load", parseFloat(v.load) || 0);
      var rows = $$("#sys-rows .sys-row");
      if (rows[0]) rows[0].querySelector(".val").textContent = (v.mem_pct || 0) + "%";
      if (rows[1]) rows[1].querySelector(".val").textContent = (v.disk_pct || 0) + "%";
      if (rows[2]) rows[2].querySelector(".val").textContent = (v.load || "--");
      // session
      kv($("#session-rows"), [["turns", String(s.turns || 0)], ["model", s.model || "--"],
        ["branch", g.branch || "--"], ["dirty", String(g.dirty || 0)],
        ["tokens", fmt(tok.total || 0), true], ["output", fmt(tok.output || 0), true]]);
      // activity
      renderActivity((d.activity || {}).events || []);
      // mascot
      var rv = s.recent_output || 0;
      if (window.Mascot) window.Mascot.setMood(rv > 1500 ? "heavy" : rv > 300 ? "thinking" : rv > 0 ? "idle" : "resting");
    } catch (e) { /* keep last render */ }
  }
  async function pollTop() { try { var d = await fetch("/api/top").then(function (r) { return r.json(); }); if (d.commands && d.commands.length) renderTop(d.commands); } catch (e) {} }

  /* terminal */
  function startTerm() {
    if (window.Mascot && window.Mascot.wake) window.Mascot.wake();
    var status = $("#term-status");
    var term = new Terminal({
      fontFamily: "JBMono, JetBrains Mono, ui-monospace, monospace", fontSize: 13,
      allowTransparency: true, cursorBlink: true,
      theme: { background: "rgba(8,8,10,0.22)", foreground: "#ece7d6", cursor: "#ffcd3c", green: "#39ff5a", brightGreen: "#8bffa0", yellow: "#d4af37", brightYellow: "#ffcd3c" }
    });
    term.open($("#terminal"));
    var proto = location.protocol === "https:" ? "wss" : "ws";
    var ws = new WebSocket(proto + "://" + location.host + "/pty");
    ws.binaryType = "arraybuffer";
    var enc = new TextEncoder();
    function sendResize() { var msg = "\x00" + JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }); if (ws.readyState === 1) ws.send(enc.encode(msg)); }
    ws.onopen = function () { status.textContent = "LIVE"; status.classList.remove("off"); sendResize(); term.focus(); };
    ws.onmessage = function (ev) { term.write(new Uint8Array(ev.data)); };
    ws.onclose = function () { status.textContent = "offline"; status.classList.add("off"); term.write("\r\n[ bridge offline -- reload to reconnect ]\r\n"); };
    term.onData(function (dd) { if (ws.readyState === 1) ws.send(enc.encode(dd)); });
    window.addEventListener("resize", sendResize);
    window.Deck = { insert: function (t) { if (ws.readyState === 1) ws.send(enc.encode(t)); term.focus(); }, clear: function () { term.clear(); } };
  }

  function boot() {
    buildSys(); buildQuick();
    var rf = $("#act-refresh"); if (rf) rf.addEventListener("click", function () { poll(); pollTop(); if (window.FileManager) window.FileManager.reload(); });
    var qi = 0; setInterval(function () { qi = (qi + 1) % QUOTES.length; var q = $("#f-quote"); if (q) q.textContent = QUOTES[qi]; }, 6000);
    setInterval(poll, 3000); poll();
    setInterval(pollTop, 30000); pollTop();
  }
  window.addEventListener("load", function () { boot(); startTerm(); });
})();
