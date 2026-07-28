/* filemanager.js -- VS Code-style workspace tree.
   Folders expand/collapse in place (lazy-loaded). Click a file to inject its
   path into the Claude prompt; drag a file onto the terminal. Read-only,
   sandboxed to the workspace. */
(function () {
  "use strict";
  var ROOT = "/mnt/sdcard/AA_MY_DRIVE";
  var treeEl;

  function q(p) { return /\s/.test(p) ? "'" + p.replace(/'/g, "'\\''") + "'" : p; }
  function human(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(1) + "G";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
    return n + "B";
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function insert(p) { if (window.Deck && window.Deck.insert) window.Deck.insert(q(p) + " "); }

  function fetchDir(path) {
    return fetch("/api/fs?path=" + encodeURIComponent(path)).then(function (r) { return r.json(); });
  }

  function makeRow(entry, path, depth) {
    var isdir = entry.type === "dir";
    var row = el("div", "tw-row " + (isdir ? "dir" : "file"));
    row.style.paddingLeft = (10 + depth * 14) + "px";
    row.appendChild(el("span", "tw-chev", isdir ? "▸" : ""));
    row.appendChild(el("span", "tw-ic", isdir ? "■" : "·"));
    row.appendChild(el("span", "tw-name", entry.name));
    if (!isdir) row.appendChild(el("span", "tw-size", human(entry.size)));

    if (isdir) {
      var kids = null;
      row.addEventListener("click", function () {
        if (kids) { // toggle
          var open = row.classList.toggle("open");
          kids.style.display = open ? "" : "none";
          return;
        }
        row.classList.add("open");
        kids = el("div", "tw-children");
        row.after(kids);
        fetchDir(path).then(function (d) {
          (d.entries || []).forEach(function (c) {
            kids.appendChild(makeRow(c, d.cwd + "/" + c.name, depth + 1));
          });
          if (!d.entries || !d.entries.length) {
            var empty = el("div", "tw-row file", "empty"); empty.style.paddingLeft = (10 + (depth + 1) * 14) + "px";
            kids.appendChild(empty);
          }
        });
      });
    } else {
      row.addEventListener("click", function () { insert(path); flash(row); });
      row.draggable = true;
      row.addEventListener("dragstart", function (ev) {
        ev.dataTransfer.setData("text/plain", q(path) + " ");
      });
    }
    return row;
  }

  function flash(row) {
    row.style.background = "rgba(57,255,90,.16)";
    setTimeout(function () { row.style.background = ""; }, 200);
  }

  function load() {
    treeEl.textContent = "";
    fetchDir(ROOT).then(function (d) {
      (d.entries || []).forEach(function (c) {
        treeEl.appendChild(makeRow(c, ROOT + "/" + c.name, 0));
      });
    }).catch(function () {
      treeEl.appendChild(el("div", "tw-row file", "could not read workspace"));
    });
  }

  function init() {
    treeEl = document.getElementById("tree");
    if (!treeEl) return;
    var term = document.getElementById("terminal");
    if (term) {
      term.addEventListener("dragover", function (e) { e.preventDefault(); });
      term.addEventListener("drop", function (e) {
        e.preventDefault();
        var t = e.dataTransfer.getData("text/plain");
        if (t && window.Deck && window.Deck.insert) window.Deck.insert(t);
      });
    }
    window.FileManager = { open: load, reload: load };
    load();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
