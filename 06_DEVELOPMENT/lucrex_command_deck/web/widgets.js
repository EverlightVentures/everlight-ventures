/* widgets.js -- tiny canvas data-viz (gauge, bars, sparkline). No chart lib.
   window.Widgets.{gauge,bars,spark}. All DPR-aware and theme-colored. */
(function () {
  "use strict";
  var GOLD = "#d4af37", GOLD_HOT = "#ffcd3c", GREEN = "#39ff5a",
      GOLD_DIM = "#4a3f16", MUTED = "#8f8a76", TRACK = "#161510";

  function setup(canvas) {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = canvas.clientWidth || canvas.width || 200;
    var h = canvas.clientHeight || canvas.height || 100;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h };
  }

  // ring gauge: pct 0..100 with centered label
  function gauge(canvas, pct) {
    var s = setup(canvas), ctx = s.ctx;
    var cx = s.w / 2, cy = s.h / 2 + 2, r = Math.min(s.w, s.h) / 2 - 12;
    var lw = Math.max(7, r * 0.16);
    pct = Math.max(0, Math.min(100, pct || 0));
    // track
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = TRACK; ctx.lineWidth = lw; ctx.stroke();
    // value arc
    var start = -Math.PI / 2, end = start + Math.PI * 2 * (pct / 100);
    var grad = ctx.createLinearGradient(0, 0, s.w, s.h);
    grad.addColorStop(0, GREEN); grad.addColorStop(1, GOLD_HOT);
    ctx.beginPath(); ctx.arc(cx, cy, r, start, end);
    ctx.strokeStyle = grad; ctx.lineWidth = lw; ctx.lineCap = "round";
    ctx.shadowColor = "rgba(57,255,90,.6)"; ctx.shadowBlur = 12; ctx.stroke();
    ctx.shadowBlur = 0;
    // label
    ctx.fillStyle = GREEN; ctx.font = "700 " + Math.round(r * 0.55) + "px JBMono, monospace";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(Math.round(pct) + "%", cx, cy);
  }

  // vertical bar chart from a numeric series
  function bars(canvas, series) {
    var s = setup(canvas), ctx = s.ctx;
    series = series || [];
    if (!series.length) return;
    var max = Math.max.apply(null, series) || 1;
    var pad = 4, n = series.length;
    var bw = (s.w - pad * 2) / n;
    var grad = ctx.createLinearGradient(0, s.h, 0, 0);
    grad.addColorStop(0, GOLD_DIM); grad.addColorStop(.6, GREEN); grad.addColorStop(1, GOLD_HOT);
    for (var i = 0; i < n; i++) {
      var bh = Math.max(2, (series[i] / max) * (s.h - 6));
      var x = pad + i * bw, y = s.h - bh;
      ctx.fillStyle = grad;
      ctx.shadowColor = "rgba(57,255,90,.35)"; ctx.shadowBlur = 6;
      ctx.fillRect(x + 1, y, Math.max(1, bw - 2), bh);
    }
    ctx.shadowBlur = 0;
  }

  // sparkline with soft fill
  function spark(canvas, series, color) {
    var s = setup(canvas), ctx = s.ctx;
    series = series || [];
    if (series.length < 2) { series = series.concat(series); if (series.length < 2) return; }
    color = color || GREEN;
    var max = Math.max.apply(null, series), min = Math.min.apply(null, series);
    var span = (max - min) || 1, n = series.length, pad = 2;
    function X(i) { return pad + i * (s.w - pad * 2) / (n - 1); }
    function Y(v) { return s.h - pad - ((v - min) / span) * (s.h - pad * 2); }
    // fill
    ctx.beginPath(); ctx.moveTo(X(0), s.h);
    for (var i = 0; i < n; i++) ctx.lineTo(X(i), Y(series[i]));
    ctx.lineTo(X(n - 1), s.h); ctx.closePath();
    var g = ctx.createLinearGradient(0, 0, 0, s.h);
    g.addColorStop(0, "rgba(57,255,90,.28)"); g.addColorStop(1, "rgba(57,255,90,0)");
    ctx.fillStyle = g; ctx.fill();
    // line
    ctx.beginPath();
    for (var j = 0; j < n; j++) { var fn = j ? "lineTo" : "moveTo"; ctx[fn](X(j), Y(series[j])); }
    ctx.strokeStyle = color; ctx.lineWidth = 1.6; ctx.lineJoin = "round";
    ctx.shadowColor = color; ctx.shadowBlur = 6; ctx.stroke(); ctx.shadowBlur = 0;
  }

  window.Widgets = { gauge: gauge, bars: bars, spark: spark };
})();
