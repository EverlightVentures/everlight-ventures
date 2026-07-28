"""blubber_server.py -- Lucrex Command Deck server (Python stdlib only).

Serves the deck front-end, read-only JSON probes, and a WebSocket PTY that runs
Claude inside the page. Binds 127.0.0.1 by default (EV_BIND to expose), per the
Network Binding Doctrine.

    python3 blubber_server.py [port]     # default 2702
"""
from __future__ import annotations
import json, os, socketserver, sys, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probes
import pty_bridge

ROOT = "/mnt/sdcard/AA_MY_DRIVE"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(APP_DIR, "web")
BIND = os.environ.get("EV_BIND", "127.0.0.1")

CTYPE = {".html": "text/html", ".css": "text/css", ".js": "text/javascript",
         ".json": "application/json", ".svg": "image/svg+xml",
         ".ico": "image/x-icon", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
         ".mp4": "video/mp4", ".woff2": "font/woff2", ".woff": "font/woff"}


def _spawn_cmd():
    # Launch claude directly so the zsh auto-chain re-exec loop cannot fire.
    return [os.environ.get("SHELL_CLAUDE", "claude")]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/pty":
            return self._upgrade_ws()
        if path.startswith("/api/"):
            name = path[5:]
            q = parse_qs(parsed.query)
            if name == "all":      return self._json({
                "vitals": probes.vitals(), "session": probes.session(),
                "history": probes.token_history(), "context": probes.context_window(),
                "activity": probes.activity(), "git": probes.git_state(ROOT)})
            if name == "vitals":   return self._json(probes.vitals())
            if name == "session":  return self._json(probes.session())
            if name == "git":      return self._json(probes.git_state(ROOT))
            if name == "agents":   return self._json(probes.agents(ROOT))
            if name == "history":  return self._json(probes.token_history())
            if name == "context":  return self._json(probes.context_window())
            if name == "activity": return self._json(probes.activity())
            if name == "top":      return self._json(probes.top_commands())
            if name == "fs":       return self._json(probes.fs(q.get("path", [None])[0]))
            return self._send(404, b'{"error":"unknown endpoint"}')
        # static assets out of web/
        rel = "index.html" if path == "/" else path.lstrip("/")
        if rel.startswith("web/"):
            rel = rel[4:]
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        with open(full, "rb") as f:
            body = f.read()
        return self._send(200, body,
                          CTYPE.get(os.path.splitext(full)[1], "application/octet-stream"))

    def _upgrade_ws(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return self._send(400, b"missing Sec-WebSocket-Key", "text/plain")
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", pty_bridge.accept_key(key))
        self.end_headers()
        self.wfile.flush()               # flush headers before hijacking the socket
        self.close_connection = True     # do not let the handler loop reuse it
        env = dict(os.environ)
        env["EV_RAW"] = "1"              # prevent the zsh auto-chain double-launch
        env["EV_CLAUDE_LAUNCHED"] = "1"
        env["TERM"] = "xterm-256color"
        try:
            pty_bridge.run_pty_session(self.connection, _spawn_cmd(), env)
        except Exception:
            pass
        try:
            self.connection.close()
        except Exception:
            pass


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 2702
    probes._DECK_STARTED = time.time()   # prefer the session this deck spawns
    with Server((BIND, port), Handler) as httpd:
        print(f"Lucrex Command Deck on http://{BIND}:{port}/", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
