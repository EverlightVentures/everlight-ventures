"""
everlight_themed_server.py -- single source of truth for the Everlight branded
HTTP server used by every local band on the phone.

Drop-in replacement for `python3 -m http.server`:
- Same file-serving behavior (HTML, JSON, etc.)
- Directory listings replaced with branded gold-on-dark cards
  (Playfair Display + Inter + JetBrains Mono, matches the master hub)
- No-cache headers everywhere
- Breadcrumb navigation
- File metadata (size, modified time)

CLI:
    python3 everlight_themed_server.py <port> [root_dir] [label]

Example (used by serve_local_reports.sh):
    python3 everlight_themed_server.py 2200 /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD "Reports Hub"
"""
from __future__ import annotations

import html
import http.server
import os
import socketserver
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

# Brand palette (matches content_tools/report_template.py + master hub at :2000)
PALETTE = {
    "gold":       "#d4a843",
    "gold_hot":   "#ffcd3c",
    "dark":       "#0a0a0a",
    "card":       "#14140e",
    "border":     "#2a2410",
    "text":       "#e8e8e8",
    "muted":      "#9b9788",
    "turquoise":  "#00e5ff",
}

PAGE_LABEL_DEFAULT = "Everlight Local"

# File type -> emoji + nice category label
FILE_TYPES = {
    ".html": ("📄", "html"),
    ".htm":  ("📄", "html"),
    ".md":   ("📝", "markdown"),
    ".pdf":  ("📕", "pdf"),
    ".json": ("⚙",  "json"),
    ".yaml": ("⚙",  "yaml"),
    ".yml":  ("⚙",  "yaml"),
    ".py":   ("🐍", "python"),
    ".sh":   ("⚡", "shell"),
    ".js":   ("◆",  "js"),
    ".jsx":  ("◆",  "jsx"),
    ".ts":   ("◆",  "ts"),
    ".tsx":  ("◆",  "tsx"),
    ".css":  ("🎨", "css"),
    ".png":  ("🖼",  "image"),
    ".jpg":  ("🖼",  "image"),
    ".jpeg": ("🖼",  "image"),
    ".webp": ("🖼",  "image"),
    ".gif":  ("🖼",  "image"),
    ".svg":  ("🖼",  "svg"),
    ".mp4":  ("🎬", "video"),
    ".mov":  ("🎬", "video"),
    ".mp3":  ("🎵", "audio"),
    ".wav":  ("🎵", "audio"),
    ".zip":  ("📦", "archive"),
    ".tar":  ("📦", "archive"),
    ".gz":   ("📦", "archive"),
    ".sqlite":("🗄", "db"),
    ".db":   ("🗄", "db"),
    ".csv":  ("📊", "csv"),
    ".txt":  ("📃", "text"),
    ".log":  ("📃", "log"),
}

PAGE_LABEL_ENV = os.environ.get("EV_PAGE_LABEL", PAGE_LABEL_DEFAULT)


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} PB"


def file_icon(name: str, is_dir: bool) -> tuple[str, str]:
    if is_dir:
        return ("📁", "dir")
    ext = Path(name).suffix.lower()
    return FILE_TYPES.get(ext, ("📄", "file"))


def render_html(path: Path, url_path: str, entries: list[dict], label: str) -> str:
    p = PALETTE
    breadcrumb_parts = [b for b in url_path.strip("/").split("/") if b]
    crumbs_html = '<a href="/">root</a>'
    accumulator = ""
    for i, part in enumerate(breadcrumb_parts):
        accumulator += "/" + part
        crumbs_html += f' <span class="sep">›</span> <a href="{html.escape(accumulator)}/">{html.escape(part)}</a>'

    rows = []
    if url_path.strip("/"):
        rows.append({
            "name": "..",
            "href": "../",
            "icon": "↩",
            "category": "parent",
            "size": "",
            "modified": "",
            "is_dir": True,
            "_sort": (-1, ""),
        })

    for e in entries:
        ico, cat = file_icon(e["name"], e["is_dir"])
        rows.append({
            "name": e["name"],
            "href": e["href"],
            "icon": ico,
            "category": cat,
            "size": "" if e["is_dir"] else fmt_size(e["size"]),
            "modified": e["mtime"].strftime("%Y-%m-%d %H:%M"),
            "is_dir": e["is_dir"],
            "_sort": (0 if e["is_dir"] else 1, -e["mtime"].timestamp()),
        })

    rows.sort(key=lambda r: r["_sort"])

    def row_html(r):
        size_cell = f'<span class="size mono">{r["size"]}</span>' if r["size"] else '<span class="size mono dim">—</span>'
        cat_class = f'cat-{r["category"]}'
        mtime_cell = f'<span class="mtime mono">{html.escape(r["modified"])}</span>' if r["modified"] else ''
        return (
            f'<a href="{html.escape(r["href"])}" class="row">'
            f'<span class="icon">{r["icon"]}</span>'
            f'<span class="name">{html.escape(r["name"])}</span>'
            f'<span class="pill mono {cat_class}">{html.escape(r["category"])}</span>'
            f'<span class="meta">{size_cell}{mtime_cell}</span>'
            f'</a>'
        )

    rows_html = "\n".join(row_html(r) for r in rows)
    n_dirs = sum(1 for r in rows if r["is_dir"] and r["name"] != "..")
    n_files = sum(1 for r in rows if not r["is_dir"])
    page_title_text = url_path.strip("/").split("/")[-1] if url_path.strip("/") else "root"

    title = f"{label} · {url_path}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --gold: {p['gold']};
    --gold-hot: {p['gold_hot']};
    --gold-deep: #b8902f;
    --dark: {p['dark']};
    --dark-2: #0f0f0a;
    --card: #15140d;
    --card-hi: #1d1b12;
    --border: #322a14;
    --border-hi: #4a3d1c;
    --text: #f4eedb;
    --text-dim: #b5af9b;
    --muted: #7a7560;
    --turquoise: #00e5ff;
    --rose: #ff7a8a;
    --green: #5cffb1;
    --violet: #c79bff;
    --silver: #d4d4dc;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    background:
      radial-gradient(ellipse 800px 400px at 20% -10%, rgba(212,168,67,.18) 0%, transparent 70%),
      radial-gradient(ellipse 600px 300px at 100% 100%, rgba(0,229,255,.06) 0%, transparent 70%),
      linear-gradient(180deg, #050402 0%, var(--dark) 40%, #08080a 100%);
    background-attachment: fixed;
    color: var(--text);
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-weight: 400;
    min-height: 100vh;
    line-height: 1.55;
    padding: 1.75rem 1rem 4rem;
    -webkit-font-smoothing: antialiased;
  }}
  .display {{ font-family: 'Playfair Display', Georgia, serif; }}
  .mono     {{ font-family: 'JetBrains Mono', ui-monospace, 'Courier New', monospace; }}
  .dim      {{ color: var(--muted); }}
  a {{ color: inherit; text-decoration: none; }}

  .wrap {{ max-width: 1140px; margin: 0 auto; }}

  /* HEADER */
  header {{
    margin-bottom: 1.75rem;
    padding: 1.25rem 1.5rem 1.25rem;
    background: linear-gradient(135deg, rgba(212,168,67,.06) 0%, rgba(0,0,0,0) 65%);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 14px;
    position: relative;
    overflow: hidden;
  }}
  header::before {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, var(--gold) 0%, transparent 50%);
  }}
  .brand {{
    color: var(--gold);
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .25em;
    text-transform: uppercase;
    margin-bottom: .35rem;
  }}
  .brand .sep {{ color: var(--gold-deep); margin: 0 .65em; opacity: .65; }}
  h1 {{
    font-family: 'Playfair Display', Georgia, serif;
    color: var(--gold-hot);
    margin: 0 0 .35rem;
    font-size: clamp(1.85rem, 4.5vw, 2.65rem);
    font-weight: 900;
    letter-spacing: -.01em;
    line-height: 1.05;
    text-shadow: 0 0 24px rgba(255,205,60,.25);
  }}
  h1 .path-italic {{ font-style: italic; font-weight: 700; color: var(--gold); }}
  .crumbs {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .82rem;
    color: var(--text-dim);
    margin-top: .25rem;
  }}
  .crumbs a {{
    color: var(--gold);
    border-bottom: 1px dotted transparent;
    transition: border-color .15s ease, color .15s ease;
  }}
  .crumbs a:hover {{ color: var(--gold-hot); border-bottom-color: var(--gold-hot); }}
  .crumbs .sep {{ color: var(--gold-deep); margin: 0 .35em; }}
  .summary {{
    display: flex; gap: 1.25rem; flex-wrap: wrap;
    margin-top: .85rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--muted);
  }}
  .summary span {{ display: inline-flex; align-items: baseline; gap: .35em; }}
  .summary strong {{
    color: var(--gold-hot);
    font-weight: 700;
    font-size: .95rem;
    letter-spacing: 0;
  }}

  /* LIST */
  .list {{
    background: linear-gradient(180deg, var(--card) 0%, var(--dark-2) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: .35rem .55rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.55), inset 0 1px 0 rgba(212,168,67,.05);
  }}
  .row {{
    display: grid;
    grid-template-columns: 32px 1fr auto auto;
    align-items: center; gap: .85rem;
    padding: .65rem .85rem;
    border-radius: 9px;
    border-left: 2px solid transparent;
    transition: background .15s ease, border-color .15s ease, transform .12s ease;
  }}
  .row:hover {{
    background: linear-gradient(90deg, rgba(212,168,67,.10) 0%, rgba(212,168,67,.02) 100%);
    border-left-color: var(--gold-hot);
    transform: translateX(2px);
  }}
  .row + .row {{ border-top: 1px solid rgba(122,117,96,.10); }}
  .icon {{ font-size: 1.15rem; line-height: 1; opacity: .9; }}
  .row:hover .icon {{ opacity: 1; }}
  .name {{
    font-size: .98rem;
    font-weight: 500;
    color: var(--text);
    word-break: break-all;
    letter-spacing: .005em;
  }}
  .row:hover .name {{ color: var(--gold-hot); }}

  /* CATEGORY PILLS -- per-type colors */
  .pill {{
    font-size: .62rem;
    font-weight: 700;
    padding: 2px 9px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: .12em;
    border: 1px solid transparent;
    line-height: 1.4;
  }}
  .cat-dir       {{ background: rgba(212,168,67,.14); color: var(--gold-hot); border-color: rgba(212,168,67,.35); }}
  .cat-parent    {{ background: rgba(122,117,96,.14); color: var(--text-dim); border-color: rgba(122,117,96,.3); }}
  .cat-html      {{ background: rgba(0,229,255,.10); color: var(--turquoise); border-color: rgba(0,229,255,.32); }}
  .cat-markdown  {{ background: rgba(212,212,220,.10); color: var(--silver); border-color: rgba(212,212,220,.28); }}
  .cat-pdf       {{ background: rgba(255,122,138,.10); color: var(--rose); border-color: rgba(255,122,138,.32); }}
  .cat-json,
  .cat-yaml      {{ background: rgba(199,155,255,.10); color: var(--violet); border-color: rgba(199,155,255,.32); }}
  .cat-python    {{ background: rgba(92,255,177,.08); color: var(--green); border-color: rgba(92,255,177,.28); }}
  .cat-shell     {{ background: rgba(255,205,60,.10); color: var(--gold-hot); border-color: rgba(255,205,60,.32); }}
  .cat-js,
  .cat-jsx,
  .cat-ts,
  .cat-tsx       {{ background: rgba(255,205,60,.08); color: var(--gold); border-color: rgba(255,205,60,.25); }}
  .cat-css       {{ background: rgba(0,229,255,.08); color: var(--turquoise); border-color: rgba(0,229,255,.22); }}
  .cat-image,
  .cat-svg       {{ background: rgba(92,255,177,.08); color: var(--green); border-color: rgba(92,255,177,.25); }}
  .cat-video,
  .cat-audio     {{ background: rgba(199,155,255,.08); color: var(--violet); border-color: rgba(199,155,255,.25); }}
  .cat-archive   {{ background: rgba(255,122,138,.08); color: var(--rose); border-color: rgba(255,122,138,.25); }}
  .cat-db,
  .cat-csv       {{ background: rgba(0,229,255,.08); color: var(--turquoise); border-color: rgba(0,229,255,.22); }}
  .cat-text,
  .cat-log       {{ background: rgba(122,117,96,.10); color: var(--text-dim); border-color: rgba(122,117,96,.28); }}
  .cat-file      {{ background: rgba(212,168,67,.06); color: var(--text-dim); border-color: rgba(212,168,67,.18); }}

  /* META (size + mtime) */
  .meta {{
    display: flex; gap: 1.1rem; align-items: center;
    font-size: .76rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
  }}
  .size  {{ min-width: 70px; text-align: right; color: var(--text-dim); }}
  .mtime {{ min-width: 124px; text-align: right; color: var(--turquoise); opacity: .82; }}
  .row:hover .mtime {{ opacity: 1; }}

  /* FOOTER */
  footer {{
    margin-top: 2rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--border);
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem;
    color: var(--muted);
    display: flex; justify-content: space-between;
    flex-wrap: wrap; gap: .5rem;
    letter-spacing: .08em;
    text-transform: uppercase;
  }}
  footer a {{ color: var(--gold); border-bottom: 1px dotted var(--gold-deep); }}
  footer a:hover {{ color: var(--gold-hot); border-bottom-color: var(--gold-hot); }}
  footer .sep {{ color: var(--gold-deep); margin: 0 .65em; opacity: .65; }}

  @media (max-width: 720px) {{
    body {{ padding: 1rem .65rem 3rem; }}
    .row {{ grid-template-columns: 26px 1fr; gap: .55rem; padding: .55rem .65rem; }}
    .pill, .meta {{ grid-column: 2 / -1; padding-left: 0; justify-self: start; }}
    .meta {{ font-size: .7rem; gap: .65rem; margin-top: .15rem; }}
    .size, .mtime {{ min-width: auto; text-align: left; }}
    h1 {{ font-size: 1.85rem; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">Everlight Ventures<span class="sep">◆</span>{html.escape(label)}</div>
    <h1 class="display">{html.escape(page_title_text)}<span class="path-italic"> {html.escape(url_path or '/')}</span></h1>
    <div class="crumbs">{crumbs_html}</div>
    <div class="summary">
      <span><strong>{n_dirs}</strong> dirs</span>
      <span><strong>{n_files}</strong> files</span>
      <span class="dim">sorted ▸ dirs first, newest below</span>
    </div>
  </header>

  <main class="list">
    {rows_html}
  </main>

  <footer>
    <span>Everlight Ventures<span class="sep">◆</span>Local Hub<span class="sep">◆</span><a href="http://127.0.0.1:2000/">return to hub</a></span>
    <span>{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
  </footer>
</div>
</body>
</html>
"""


class EverlightHandler(http.server.SimpleHTTPRequestHandler):
    label = PAGE_LABEL_ENV

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        msg = fmt % args
        if " 200 " in msg or " 304 " in msg:
            return
        super().log_message(fmt, *args)

    def list_directory(self, path):
        try:
            names = os.listdir(path)
        except OSError:
            self.send_error(404, "Cannot list directory")
            return None

        entries = []
        for name in names:
            if name.startswith("."):
                continue
            full = Path(path) / name
            try:
                st = full.stat()
            except OSError:
                continue
            entries.append({
                "name": name,
                "href": urllib.parse.quote(name) + ("/" if full.is_dir() else ""),
                "is_dir": full.is_dir(),
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime),
            })

        url_path = urllib.parse.unquote(self.path)
        body = render_html(Path(path), url_path, entries, self.label).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return self._make_buffer(body)

    @staticmethod
    def _make_buffer(body: bytes):
        import io
        return io.BytesIO(body)


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    root = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) > 2 else Path.cwd()
    label = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("EV_PAGE_LABEL", PAGE_LABEL_DEFAULT)

    EverlightHandler.label = label
    os.chdir(root)

    bind = os.environ.get("EV_BIND", "127.0.0.1")
    print(f"[everlight_themed_server] http://{bind}:{port}/  root={root}  label={label!r}",
          file=sys.stderr, flush=True)

    with socketserver.ThreadingTCPServer((bind, port), EverlightHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
