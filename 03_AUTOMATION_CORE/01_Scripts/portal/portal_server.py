#!/usr/bin/env python3
"""
Everlight Ventures -- Organizational Portal Server
Numbered category/subcategory/file addressing scheme.

Bind: 127.0.0.1 (loopback only -- network-binding doctrine, private by default)
Port: env PORTAL_PORT, default 8800

Addressing:
  /                        -> branded master index (from registry.yaml)
  /NN/                     -> category index listing subcategories
  /NN/subcat/              -> subcategory listing
  /NN/subcat/file          -> static file (portal_root tree OR source_files from registry)

sdcard symlink note:
  Android sdcard is typically formatted as FAT32 or exFAT, which does NOT support
  POSIX symlinks. Rather than copying files (which go stale), this server reads
  source_files entries from registry.yaml and streams them directly at request time.
  Files defined in source_files are served from their original locations; no copy needed.
  Files placed directly in portal_root/NN/subcat/ are served normally.
"""

import http.server
import os
import mimetypes
import urllib.parse
import json
from pathlib import Path

# -- try yaml, fall back to a tiny inline parser for stdlib-only env --
try:
    import yaml
    def _load_yaml(path):
        with open(path, "r") as f:
            return yaml.safe_load(f)
except ImportError:
    # Minimal YAML-ish parser: only used if PyYAML not present.
    # Relies on json for data that's already JSON-shaped; for the registry we use
    # a simple key:value line scanner that handles the flat fields we need.
    # NOTE: this is a last-resort fallback; PyYAML is stdlib on most distros.
    def _load_yaml(path):
        raise ImportError(
            "PyYAML is not available. Install with: pip3 install pyyaml\n"
            "Or run: python3 -c \"import yaml\" to check."
        )

PORTAL_DIR = Path(__file__).parent.resolve()
PORTAL_ROOT = PORTAL_DIR / "portal_root"
REGISTRY_PATH = PORTAL_DIR / "registry.yaml"

PORT = int(os.environ.get("PORTAL_PORT", "8800"))

# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

def load_registry():
    """Load and return the parsed registry.yaml as a list of category dicts."""
    data = _load_yaml(str(REGISTRY_PATH))
    return data.get("categories", [])


def build_source_index(categories):
    """
    Build a lookup dict:
      source_index[(NN, subcat, filename)] -> source_path (str)
    Used to serve files from registry source_files entries.
    """
    idx = {}
    for cat in categories:
        nn = cat.get("number", "").zfill(2)
        for subcat, files in (cat.get("source_files") or {}).items():
            for fentry in (files or []):
                key = (nn, subcat, fentry["filename"])
                idx[key] = fentry["source_path"]
    return idx


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

_GOOGLE_FONTS = "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600&display=swap"

_CSS = """
  :root {
    --gold: #D4AF37;
    --dark: #0A0A0A;
    --card: #111111;
    --border: #2a2a2a;
    --text: #E8E8E8;
    --muted: #888888;
    --link: #D4AF37;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--dark);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.6;
    padding: 0 0 60px;
  }
  header {
    background: #0d0d0d;
    border-bottom: 1px solid var(--gold);
    padding: 22px 40px;
    display: flex;
    align-items: baseline;
    gap: 16px;
  }
  header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 1.9rem;
    color: var(--gold);
    letter-spacing: 0.02em;
  }
  header span {
    color: var(--muted);
    font-size: 0.85rem;
  }
  nav.breadcrumb {
    padding: 12px 40px;
    font-size: 0.82rem;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }
  nav.breadcrumb a { color: var(--gold); text-decoration: none; }
  nav.breadcrumb a:hover { text-decoration: underline; }
  .container { max-width: 1100px; margin: 0 auto; padding: 30px 40px; }
  .section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: var(--gold);
    margin: 32px 0 14px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }
  .category-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 18px 20px;
    transition: border-color 0.15s;
  }
  .card:hover { border-color: var(--gold); }
  .card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .cat-num {
    background: var(--gold);
    color: var(--dark);
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 2px 8px;
    border-radius: 3px;
    white-space: nowrap;
  }
  .cat-name {
    font-weight: 600;
    font-size: 1rem;
    color: var(--text);
  }
  .cat-desc {
    font-size: 0.82rem;
    color: var(--muted);
    margin-bottom: 12px;
  }
  .subcat-list {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
  }
  .subcat-list li a {
    display: inline-block;
    background: #1a1a1a;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.78rem;
    color: var(--text);
    text-decoration: none;
    transition: background 0.12s, border-color 0.12s;
  }
  .subcat-list li a:hover {
    background: #222;
    border-color: var(--gold);
    color: var(--gold);
  }
  .ext-links { margin-top: 8px; }
  .ext-link {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.78rem;
    color: var(--gold);
    text-decoration: none;
    margin-right: 10px;
    margin-top: 4px;
  }
  .ext-link:hover { text-decoration: underline; }
  .ext-badge {
    font-size: 0.65rem;
    background: #1d1700;
    border: 1px solid var(--gold);
    color: var(--gold);
    border-radius: 3px;
    padding: 1px 5px;
    vertical-align: middle;
  }
  .file-list { list-style: none; }
  .file-list li {
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.88rem;
  }
  .file-list li:last-child { border-bottom: none; }
  .file-list a { color: var(--gold); text-decoration: none; }
  .file-list a:hover { text-decoration: underline; }
  .file-meta { color: var(--muted); font-size: 0.75rem; margin-left: 8px; }
  .badge-source {
    font-size: 0.65rem;
    background: #0a1700;
    border: 1px solid #3a5a00;
    color: #8fba30;
    border-radius: 3px;
    padding: 1px 5px;
    margin-left: 6px;
    vertical-align: middle;
  }
  .empty-state {
    color: var(--muted);
    font-size: 0.85rem;
    padding: 20px 0;
    font-style: italic;
  }
  footer {
    text-align: center;
    padding: 30px 40px 10px;
    color: var(--muted);
    font-size: 0.75rem;
    border-top: 1px solid var(--border);
    margin-top: 40px;
  }
  footer span { color: var(--gold); }
"""

def _html_shell(title, breadcrumb_html, body_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} -- Everlight Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="{_GOOGLE_FONTS}" rel="stylesheet">
  <style>{_CSS}</style>
</head>
<body>
<header>
  <h1>EVERLIGHT VENTURES</h1>
  <span>Organizational Portal -- :8800</span>
</header>
{breadcrumb_html}
<div class="container">
{body_html}
</div>
<footer>
  <span>EVERLIGHT VENTURES</span> -- Portal v1 -- 127.0.0.1:8800 -- private (loopback)
</footer>
</body>
</html>"""


def render_master_index(categories):
    """Render the root index listing all categories."""
    breadcrumb = '<nav class="breadcrumb"><a href="/">Portal</a></nav>'
    cards_html = []
    for cat in categories:
        nn = cat.get("number", "??").zfill(2)
        name = cat.get("name", "")
        desc = cat.get("description", "")
        subcats = cat.get("subcategories", [])
        ext_links = cat.get("external_links", [])

        subcat_items = "".join(
            f'<li><a href="/{nn}/{sc}/">{sc}</a></li>'
            for sc in subcats
        )
        ext_items = "".join(
            f'<a class="ext-link" href="{lnk["url"]}" target="_blank" rel="noopener">'
            f'<span class="ext-badge">LIVE</span> {lnk["label"]}</a>'
            for lnk in ext_links
        )

        card = f"""<div class="card">
  <div class="card-header">
    <span class="cat-num">{nn}</span>
    <a href="/{nn}/" style="text-decoration:none"><span class="cat-name">{name}</span></a>
  </div>
  <p class="cat-desc">{desc}</p>
  <ul class="subcat-list">{subcat_items}</ul>
  {"<div class='ext-links'>" + ext_items + "</div>" if ext_items else ""}
</div>"""
        cards_html.append(card)

    body = f"""<p class="section-title">Categories (01 -- {len(categories):02d})</p>
<div class="category-grid">
{"".join(cards_html)}
</div>"""
    return _html_shell("Master Index", breadcrumb, body)


def render_category_index(cat):
    """Render the NN/ index for one category."""
    nn = cat.get("number", "??").zfill(2)
    name = cat.get("name", "")
    desc = cat.get("description", "")
    subcats = cat.get("subcategories", [])
    ext_links = cat.get("external_links", [])

    breadcrumb = f'<nav class="breadcrumb"><a href="/">Portal</a> / <a href="/{nn}/">{nn} {name}</a></nav>'

    subcat_items = "".join(
        f'<li><a href="/{nn}/{sc}/">{sc}</a></li>'
        for sc in subcats
    )
    ext_items = "".join(
        f'<p><a class="ext-link" href="{lnk["url"]}" target="_blank" rel="noopener">'
        f'<span class="ext-badge">LIVE</span> {lnk["label"]}</a></p>'
        for lnk in ext_links
    )

    body = f"""<p class="section-title">{nn} -- {name}</p>
<p class="cat-desc" style="margin-bottom:20px">{desc}</p>
<p class="section-title">Subcategories</p>
<ul class="subcat-list">{subcat_items}</ul>
{"<p class='section-title'>Live External Apps</p>" + ext_items if ext_items else ""}"""
    return _html_shell(f"{nn} {name}", breadcrumb, body)


def render_subcat_index(cat, subcat, portal_root, source_index):
    """Render the NN/subcat/ listing of files."""
    nn = cat.get("number", "??").zfill(2)
    name = cat.get("name", "")
    breadcrumb = (
        f'<nav class="breadcrumb">'
        f'<a href="/">Portal</a> / '
        f'<a href="/{nn}/">{nn} {name}</a> / '
        f'<a href="/{nn}/{subcat}/">{subcat}</a></nav>'
    )

    # Collect files: from portal_root tree + from source_index
    items = []
    subcat_dir = portal_root / nn / subcat
    if subcat_dir.is_dir():
        for f in sorted(subcat_dir.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                size = f.stat().st_size
                items.append({
                    "name": f.name,
                    "url": f"/{nn}/{subcat}/{f.name}",
                    "size": _human_size(size),
                    "source": "local",
                })

    # Add source_files entries not already in local dir
    existing_names = {i["name"] for i in items}
    for (snn, ssc, fname), spath in source_index.items():
        if snn == nn and ssc == subcat and fname not in existing_names:
            sp = Path(spath)
            size_str = _human_size(sp.stat().st_size) if sp.exists() else "?"
            items.append({
                "name": fname,
                "url": f"/{nn}/{subcat}/{fname}",
                "size": size_str,
                "source": "registry",
            })

    if items:
        li_html = "".join(
            f'<li><a href="{it["url"]}">{it["name"]}</a>'
            f'{"<span class=badge-source>registry src</span>" if it["source"] == "registry" else ""}'
            f'<span class="file-meta">{it["size"]}</span></li>'
            for it in items
        )
        file_block = f'<ul class="file-list">{li_html}</ul>'
    else:
        file_block = '<p class="empty-state">No files here yet. Drop files into portal_root/{nn}/{subcat}/ or add source_files entries to registry.yaml.</p>'.replace("{nn}", nn).replace("{subcat}", subcat)

    body = f'<p class="section-title">{nn} / {subcat}</p>{file_block}'
    return _html_shell(f"{nn}/{subcat}", breadcrumb, body)


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class PortalHandler(http.server.BaseHTTPRequestHandler):

    # Class-level shared state, set once before server starts
    categories = []
    source_index = {}

    def log_message(self, fmt, *args):
        # Compact one-line log with timestamp
        print(f"[portal] {self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        # Strip trailing slash for matching, but remember if it was there
        clean = path.rstrip("/")
        parts = [p for p in clean.split("/") if p]

        # ------------------------------------------------------------------ /
        if len(parts) == 0:
            html = render_master_index(self.categories)
            self._send_html(html)
            return

        # ------------------------------------------------------------------ /NN or /NN/
        if len(parts) == 1:
            nn = parts[0].zfill(2)
            cat = self._find_cat(nn)
            if cat is None:
                self._send_404(f"Category {nn!r} not found in registry.")
                return
            html = render_category_index(cat)
            self._send_html(html)
            return

        # ------------------------------------------------------------------ /NN/subcat or /NN/subcat/
        if len(parts) == 2:
            nn, subcat = parts[0].zfill(2), parts[1]
            cat = self._find_cat(nn)
            if cat is None:
                self._send_404(f"Category {nn!r} not found.")
                return
            html = render_subcat_index(cat, subcat, PORTAL_ROOT, self.source_index)
            self._send_html(html)
            return

        # ------------------------------------------------------------------ /NN/subcat/file
        if len(parts) == 3:
            nn, subcat, filename = parts[0].zfill(2), parts[1], parts[2]

            # 1. Check portal_root first
            local_path = PORTAL_ROOT / nn / subcat / filename
            if local_path.is_file():
                self._serve_file(local_path)
                return

            # 2. Check source_index (registry source_files)
            src_path = self.source_index.get((nn, subcat, filename))
            if src_path:
                sp = Path(src_path)
                if sp.is_file():
                    self._serve_file(sp)
                    return
                else:
                    self._send_404(f"Source file not found at: {src_path}")
                    return

            self._send_404(f"File {filename!r} not found in {nn}/{subcat}/")
            return

        # Deeper paths not supported
        self._send_404("Path depth > 3 not supported.")

    def _find_cat(self, nn):
        nn_padded = nn.zfill(2)
        for c in self.categories:
            if str(c.get("number", "")).zfill(2) == nn_padded:
                return c
        return None

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path):
        mime, _ = mimetypes.guess_type(str(path))
        if mime is None:
            mime = "application/octet-stream"
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except PermissionError:
            self._send_error(403, f"Permission denied reading {path.name}")
        except OSError as e:
            self._send_error(500, str(e))

    def _send_404(self, msg="Not found."):
        body = _html_shell(
            "404 Not Found",
            '<nav class="breadcrumb"><a href="/">Portal</a> / 404</nav>',
            f'<p class="section-title">404 -- Not Found</p>'
            f'<p style="color:var(--muted);margin-top:12px">{msg}</p>'
            f'<p style="margin-top:20px"><a href="/" style="color:var(--gold)">Back to Index</a></p>',
        )
        data = body.encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, code, msg):
        data = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    try:
        cats = load_registry()
    except ImportError as e:
        print(f"[portal] ERROR: {e}")
        raise SystemExit(1)
    except FileNotFoundError:
        print(f"[portal] ERROR: registry.yaml not found at {REGISTRY_PATH}")
        raise SystemExit(1)

    PortalHandler.categories = cats
    PortalHandler.source_index = build_source_index(cats)

    bind_addr = ("127.0.0.1", PORT)
    server = http.server.HTTPServer(bind_addr, PortalHandler)
    print(f"[portal] Everlight Portal running at http://127.0.0.1:{PORT}/")
    print(f"[portal] Registry: {len(cats)} categories loaded from {REGISTRY_PATH}")
    print(f"[portal] portal_root: {PORTAL_ROOT}")
    print("[portal] Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[portal] Stopped.")


if __name__ == "__main__":
    main()
