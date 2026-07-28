#!/usr/bin/env python3
"""
Karma Pack dashboard -- local phone server on 127.0.0.1:2600.
On every page load it pulls the latest karma_pack.json from e5 over ssh and
renders the kit-style copy-button dashboard (alleykingz.online/bcardd/kit DNA).

Launched by hive_inner_startup (singleton via the port bind itself).
"""
import html
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 2600  # bind:127.0.0.1 -- phone-local dashboard, never exposed

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Karma Pack</title><style>
:root{--gold:#D4AF37;--gold-hi:#F0D060;--ink:#0A0A0A;--text:#E8E8E8;--dim:#8a8578}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--ink);color:var(--text);font-family:system-ui;padding:16px 12px 60px;max-width:640px;margin:0 auto}
h1{font-size:18px;color:var(--gold-hi)} .d{font-size:11px;color:var(--dim);margin-bottom:14px}
.card{border:1px solid rgba(212,175,55,.3);border-radius:12px;padding:12px;margin-bottom:12px;background:rgba(212,175,55,.04)}
.sub{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--gold)}
.t{font-size:13px;font-weight:600;margin:4px 0 8px}
a.open{display:inline-block;text-decoration:none;font-size:11px;font-weight:700;color:var(--ink);
background:linear-gradient(160deg,var(--gold-hi),var(--gold));border-radius:8px;padding:7px 14px;margin-right:8px}
button{cursor:pointer;border:none;border-radius:8px;padding:7px 14px;font-weight:700;font-size:11px;
color:var(--gold-hi);background:rgba(212,175,55,.12);border:1px solid rgba(212,175,55,.45)}
.p{font-size:12px;color:var(--text);line-height:1.5;margin:8px 0;border-left:3px solid var(--gold);
padding:6px 10px;background:rgba(212,175,55,.05);border-radius:0 8px 8px 0}
.note{font-size:10.5px;color:var(--dim);line-height:1.5}
</style></head><body>
<h1>🧠 Reddit Karma Pack</h1><div class="d">__DATE__ · tap OPEN, then COPY, paste, tweak a word, post. zero coin talk.</div>
__CARDS__
<p class="note">Fresh pack daily 9:05 AM. Pull-to-refresh re-fetches from e5. Karma goal: ~50-100 comment karma unlocks the meme-coin subs -- then the $BCARDD post launches.</p>
<script>
document.querySelectorAll('button').forEach(function(b){
  b.addEventListener('click',function(){
    navigator.clipboard.writeText(b.dataset.c).then(function(){
      b.textContent='✓ copied'; setTimeout(function(){b.textContent='COPY';},1200);
    });
  });
});
</script></body></html>"""


def get_pack():
    try:
        out = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=8", "e5", "cat ~/bcardi/automation/karma_pack.json"],
            capture_output=True, timeout=20).stdout
        return json.loads(out)
    except Exception as e:
        return {"date": "unreachable", "rows": [], "err": repr(e)[:80]}


def render():
    pack = get_pack()
    cards = []
    for r in pack.get("rows", []):
        paste = r.get("paste") or r.get("hint") or ""
        cards.append(
            '<div class="card"><span class="sub">r/{s}</span><div class="t">{t}</div>'
            '<a class="open" href="{l}" target="_blank">OPEN THREAD</a>'
            '<button data-c="{pc}">COPY</button>'
            '<div class="p">{p}</div></div>'.format(
                s=html.escape(r["sub"]), t=html.escape(r["title"]),
                l=html.escape(r["link"]), p=html.escape(paste),
                pc=html.escape(paste, quote=True)))
    if not cards:
        cards = ["<div class='card'><div class='t'>No pack loaded ({})</div></div>".format(
            html.escape(str(pack.get("err", "e5 empty"))))]
    return PAGE.replace("__DATE__", html.escape(pack.get("date", "?"))).replace(
        "__CARDS__", "\n".join(cards))


# operator-only pages (NEVER public -- served on 127.0.0.1 only)
OPS = "/mnt/sdcard/AA_MY_DRIVE/_state/bcardd_ops"
LOCAL_PAGES = {"/share": OPS + "/share.html", "/kit": OPS + "/kit.html", "/raid": OPS + "/raid_kit.html"}

OPS_INDEX = """<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>BCARDD Ops (private)</title><style>
body{background:#0A0A0A;color:#E8E8E8;font-family:system-ui;padding:24px;max-width:480px;margin:0 auto}
h1{color:#F0D060;font-size:20px}p{color:#8a8578;font-size:12px;margin-bottom:18px}
a{display:block;text-decoration:none;color:#0A0A0A;background:linear-gradient(160deg,#F0D060,#D4AF37);
border-radius:12px;padding:16px;margin-bottom:12px;font-weight:800;font-size:15px}
small{display:block;font-weight:600;opacity:.7;font-size:11px;margin-top:3px}</style></head><body>
<h1>&#128054; BCARDD Ops</h1><p>Private. This runs only on your phone (127.0.0.1). Never public.</p>
<a href="/share">&#10084;&#65039; Share Kit<small>heart ask + anonymous share messages</small></a>
<a href="/kit">&#128203; Submission Kit<small>copy-paste fields for listing forms</small></a>
<a href="/raid">&#128293; Raid Kit<small>where to drop the link + paste copy</small></a>
<a href="/karma">&#129504; Karma Pack<small>today's reddit comment missions</small></a>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path in ("/", "/ops"):
            body = OPS_INDEX
        elif path == "/karma":
            body = render()
        elif path in LOCAL_PAGES:
            try:
                with open(LOCAL_PAGES[path], encoding="utf-8") as f:
                    body = f.read()
            except OSError:
                body = "<h1>not found locally</h1>"
        else:
            body = OPS_INDEX
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
