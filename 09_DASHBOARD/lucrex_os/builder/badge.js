// Flips the freshness badge based on data-generated vs now + data-refresh.
(function () {
  var body = document.body;
  var el = document.getElementById("lx-freshness");
  if (!el) return;
  var iso = body.getAttribute("data-generated");
  var refresh = parseInt(body.getAttribute("data-refresh") || "0", 10);
  function fmtPT(d) {
    return d.toLocaleTimeString("en-US", { timeZone: "America/Los_Angeles", hour: "2-digit", minute: "2-digit" });
  }
  function paint() {
    if (!iso) { el.textContent = "no timestamp"; el.className = "lx-badge stale"; return; }
    var gen = new Date(iso), now = new Date();
    if (isNaN(gen)) { el.textContent = "no timestamp"; el.className = "lx-badge stale"; return; }
    var ageSec = (now - gen) / 1000;
    var window = refresh > 0 ? refresh * 2 : 3600;
    if (ageSec <= window) { el.textContent = "live " + fmtPT(gen) + " PT"; el.className = "lx-badge live"; }
    else { el.textContent = "STALE as of " + fmtPT(gen) + " PT"; el.className = "lx-badge stale"; }
  }
  paint();
  document.addEventListener("visibilitychange", function () { if (!document.hidden) paint(); });
})();
