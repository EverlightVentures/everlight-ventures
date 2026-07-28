# LUCREX Command Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained local dashboard at `127.0.0.1:2702` that wraps the real Claude terminal in a Flubber-green / Lucrex-gold skin with a crowned 3D mascot (Blubber) reacting to live session state.

**Architecture:** A single Python-stdlib server (`blubber_server.py`) serves static assets, read-only JSON probes (`probes.py`), and a hand-rolled WebSocket PTY bridge (`pty_bridge.py`) that runs Claude inside the page via `pty.fork()`. The front end is no-build vanilla JS with vendored `xterm.js` (terminal) and `three.min.js` (mascot). It replaces the dead placeholder that `serve_lucrex.sh` serves at `:2702`, inheriting the existing watchdog auto-heal and banner pill.

**Tech Stack:** Python 3 stdlib (`http.server`, `socketserver`, `pty`, `select`, `fcntl`, `termios`, `hashlib`, `base64`, `json`), vanilla HTML/CSS/JS, vendored xterm.js + three.js.

## Global Constraints

- **Local only.** All app code under `06_DEVELOPMENT/lucrex_command_deck/`. Never under `03_AUTOMATION_CORE/01_Scripts/` (Oracle auto-deploy cron) except the existing `serve_lucrex.sh` edit.
- **No `pip install`, no `npm install`.** Backend = Python stdlib only. Front end = vendored JS fetched once via `curl` into `web/vendor/`, never at runtime.
- **Bind `127.0.0.1`** by default; honor `EV_BIND` env var to expose.
- **No long dash anywhere.** Use two hyphens instead. A PreToolUse hook blocks the long-dash character in all generated content.
- **No hyphens-as-dashes in any user-facing copy** beyond two hyphens (per outbound-copy law); captions use plain words.
- **Real data only.** Token/session from `~/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/*.jsonl`; vitals from `/proc`; git from `git`. Label anything not live.
- **Port:** `2702`. **Palette:** gold `#D4AF37`, gold-hot `#ffcd3c`, dark `#0a0a0a`, card `#14140e`, turquoise `#00e5ff`, plus new Blubber-green `#39ff5a` / deep `#0c2a12`.
- **Python invocation:** `python3`. **Tests:** a stdlib `unittest` runner (`tests/run.py`) is provided so no pip dependency is required.

---

## File Structure

```
06_DEVELOPMENT/lucrex_command_deck/
  probes.py          # read-only collectors: vitals(), session(), git_state(), agents()
  pty_bridge.py      # WS handshake + frame codec + pty pump (the isolated risky part)
  blubber_server.py  # HTTP router: static + /api/* + /pty upgrade; CLI entrypoint
  web/
    index.html       # layout shell
    deck.css         # theme + responsive (fold/DeX)
    deck.js          # polls /api/*, mounts xterm, opens /pty WS, drives mood
    blubber.js       # crowned 3D mascot + blubberMood() state map
    vendor/          # xterm.js, xterm.css, three.min.js (curl'd once)
  tests/
    run.py                     # stdlib unittest runner (no pytest needed)
    test_probes.py
    test_pty_bridge.py
    fixtures/sample_transcript.jsonl
  README.md
```

Files edited outside the app dir:
- `03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh` (default `start` to Blubber; `start-next` opt-in)
- `/root/.zshrc` (`lucrex()` function + `alias lx`)
- `09_DASHBOARD/master_dashboard/templates/index.html` (one Lucrex tile)

---

### Task 1: `probes.py` -- session token parser + vitals (TDD)

**Files:**
- Create: `06_DEVELOPMENT/lucrex_command_deck/probes.py`
- Create: `06_DEVELOPMENT/lucrex_command_deck/tests/fixtures/sample_transcript.jsonl`
- Create: `06_DEVELOPMENT/lucrex_command_deck/tests/test_probes.py`
- Create: `06_DEVELOPMENT/lucrex_command_deck/tests/run.py`

**Interfaces:**
- Produces:
  - `session(transcript_dir=None) -> dict` with keys
    `{"tokens": {"input","output","cache_read","cache_creation","total"}, "turns": int, "model": str, "recent_output": int, "source": str, "error": str|None}`
  - `vitals() -> dict` with keys `{"uptime","load","mem_pct","disk_pct","error"}`
  - `git_state(root) -> dict` `{"branch","dirty","commits":[...],"deploy","error"}`
  - `agents(root) -> dict` `{"recent":[...],"source","error"}`

- [ ] **Step 1: Write the fixture transcript**

Create `tests/fixtures/sample_transcript.jsonl` with three lines (one user, two assistant with usage):

```json
{"type":"user","message":{"role":"user","content":"hi"}}
{"type":"assistant","message":{"model":"claude-opus-4-8","usage":{"input_tokens":100,"output_tokens":40,"cache_read_input_tokens":10,"cache_creation_input_tokens":5}}}
{"type":"assistant","message":{"model":"claude-opus-4-8","usage":{"input_tokens":200,"output_tokens":60,"cache_read_input_tokens":20,"cache_creation_input_tokens":0}}}
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_probes.py`:

```python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import probes

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

class TestSession(unittest.TestCase):
    def test_token_sums_and_turns(self):
        s = probes.session(transcript_dir=FIX)
        self.assertIsNone(s["error"])
        self.assertEqual(s["turns"], 2)
        self.assertEqual(s["model"], "claude-opus-4-8")
        self.assertEqual(s["tokens"]["input"], 300)
        self.assertEqual(s["tokens"]["output"], 100)
        self.assertEqual(s["tokens"]["cache_read"], 30)
        self.assertEqual(s["tokens"]["cache_creation"], 5)
        self.assertEqual(s["tokens"]["total"], 435)
        self.assertEqual(s["recent_output"], 100)  # last <=3 turns

    def test_missing_dir_is_soft_error(self):
        s = probes.session(transcript_dir="/no/such/dir")
        self.assertIsNotNone(s["error"])
        self.assertEqual(s["tokens"]["total"], 0)

if __name__ == "__main__":
    unittest.main()
```

Create `tests/run.py`:

```python
import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
loader = unittest.TestLoader()
suite = loader.discover(os.path.dirname(os.path.abspath(__file__)), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/lucrex_command_deck && python3 tests/run.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'probes'` or `AttributeError`.

- [ ] **Step 4: Implement `probes.py`**

```python
"""probes.py -- read-only local state collectors for the Lucrex Command Deck.
Each function returns a plain dict and never raises; failures land in ["error"].
Python stdlib only."""
from __future__ import annotations
import glob, json, os, subprocess

DEFAULT_TRANSCRIPT_DIR = os.path.expanduser(
    "~/.claude/projects/-mnt-sdcard-AA-MY-DRIVE")

def _newest_jsonl(d):
    files = glob.glob(os.path.join(d, "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None

def session(transcript_dir=None):
    d = transcript_dir or DEFAULT_TRANSCRIPT_DIR
    out = {"tokens": {"input":0,"output":0,"cache_read":0,"cache_creation":0,"total":0},
           "turns":0, "model":"", "recent_output":0, "source":d, "error":None}
    try:
        path = _newest_jsonl(d)
        if not path:
            out["error"] = "no transcript found"; return out
        out["source"] = path
        recent = []
        with open(path, "r", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try: obj = json.loads(line)
                except ValueError: continue
                if obj.get("type") != "assistant": continue
                msg = obj.get("message") or {}
                u = msg.get("usage") or {}
                if not u: continue
                out["turns"] += 1
                if msg.get("model"): out["model"] = msg["model"]
                out["tokens"]["input"] += u.get("input_tokens",0)
                out["tokens"]["output"] += u.get("output_tokens",0)
                out["tokens"]["cache_read"] += u.get("cache_read_input_tokens",0)
                out["tokens"]["cache_creation"] += u.get("cache_creation_input_tokens",0)
                recent.append(u.get("output_tokens",0))
        t = out["tokens"]
        t["total"] = t["input"]+t["output"]+t["cache_read"]+t["cache_creation"]
        out["recent_output"] = sum(recent[-3:])
    except Exception as e:
        out["error"] = str(e)
    return out

def vitals():
    out = {"uptime":"","load":"","mem_pct":0,"disk_pct":0,"error":None}
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        out["uptime"] = f"{int(secs//3600)}h {int((secs%3600)//60)}m"
        out["load"] = f"{os.getloadavg()[0]:.2f}"
        with open("/proc/meminfo") as f:
            mi = {p.split(':')[0]: int(p.split()[1]) for p in f.read().splitlines() if ':' in p}
        total = mi.get("MemTotal",1); avail = mi.get("MemAvailable", mi.get("MemFree",0))
        out["mem_pct"] = round(100*(total-avail)/total)
        st = os.statvfs("/mnt/sdcard")
        out["disk_pct"] = round(100*(st.f_blocks-st.f_bfree)/max(st.f_blocks,1))
    except Exception as e:
        out["error"] = str(e)
    return out

def git_state(root):
    out = {"branch":"","dirty":0,"commits":[],"deploy":"","error":None}
    def g(args):
        return subprocess.run(["git","-C",root]+args, capture_output=True, text=True, timeout=8).stdout.strip()
    try:
        out["branch"] = g(["rev-parse","--abbrev-ref","HEAD"])
        st = g(["status","--porcelain"])
        out["dirty"] = len([l for l in st.splitlines() if l.strip()])
        out["commits"] = g(["log","--oneline","-3","--pretty=%s"]).splitlines()
    except Exception as e:
        out["error"] = str(e)
    return out

def agents(root):
    out = {"recent":[], "source":"AGENT_MAILBOX.md", "error":None}
    try:
        mb = os.path.join(root, "01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/AGENT_MAILBOX.md")
        if os.path.exists(mb):
            with open(mb, errors="ignore") as f:
                heads = [l.strip("# ").strip() for l in f if l.startswith("#")]
            out["recent"] = heads[-5:]
        else:
            out["error"] = "mailbox not found"
    except Exception as e:
        out["error"] = str(e)
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd 06_DEVELOPMENT/lucrex_command_deck && python3 tests/run.py`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/probes.py 06_DEVELOPMENT/lucrex_command_deck/tests/
git commit -m "feat(lucrex-deck): probes.py session/vitals/git/agents collectors + tests"
```

---

### Task 2: `pty_bridge.py` -- WebSocket frame codec (TDD) + PTY pump

**Files:**
- Create: `06_DEVELOPMENT/lucrex_command_deck/pty_bridge.py`
- Create: `06_DEVELOPMENT/lucrex_command_deck/tests/test_pty_bridge.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `accept_key(client_key: str) -> str` (Sec-WebSocket-Accept value)
  - `encode_frame(payload: bytes, opcode=0x1) -> bytes` (server to client, unmasked)
  - `decode_frames(buf: bytes) -> (list[(opcode, payload)], leftover_bytes)`
  - `mask_frame(payload: bytes, opcode=0x1) -> bytes` (test helper: a masked client frame)
  - `run_pty_session(sock, spawn, env) -> None` (blocking pump; used by server)

- [ ] **Step 1: Write the failing test**

Create `tests/test_pty_bridge.py`:

```python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pty_bridge as pb

class TestWS(unittest.TestCase):
    def test_accept_key_rfc_example(self):
        self.assertEqual(pb.accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
                         "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_roundtrip_masked_client_frame(self):
        payload = b"hello lucrex"
        frame = pb.mask_frame(payload, opcode=0x1)
        msgs, leftover = pb.decode_frames(frame)
        self.assertEqual(leftover, b"")
        self.assertEqual(msgs, [(0x1, payload)])

    def test_server_frame_is_unmasked(self):
        payload = b"x"*200  # forces 2-byte length path
        frame = pb.encode_frame(payload, opcode=0x2)
        self.assertEqual(frame[0] & 0x0f, 0x2)
        self.assertEqual(frame[1] & 0x80, 0)  # server never masks

    def test_partial_frame_returns_leftover(self):
        frame = pb.mask_frame(b"partial-data-here")
        msgs, leftover = pb.decode_frames(frame[:5])
        self.assertEqual(msgs, [])
        self.assertEqual(leftover, frame[:5])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/lucrex_command_deck && python3 tests/run.py`
Expected: FAIL (`No module named 'pty_bridge'`).

- [ ] **Step 3: Implement `pty_bridge.py`**

```python
"""pty_bridge.py -- minimal stdlib WebSocket + PTY pump for the Lucrex deck.
Runs a real shell/Claude inside a pty and streams it over one WebSocket.
No third-party deps."""
from __future__ import annotations
import base64, fcntl, hashlib, json, os, pty, select, signal, struct, termios

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def accept_key(client_key):
    h = hashlib.sha1((client_key + WS_GUID).encode()).digest()
    return base64.b64encode(h).decode()

def encode_frame(payload, opcode=0x1):
    b0 = 0x80 | (opcode & 0x0f); n = len(payload)
    if n < 126:            header = struct.pack("!BB", b0, n)
    elif n < (1 << 16):    header = struct.pack("!BBH", b0, 126, n)
    else:                  header = struct.pack("!BBQ", b0, 127, n)
    return header + payload

def mask_frame(payload, opcode=0x1):
    b0 = 0x80 | (opcode & 0x0f); n = len(payload); mask = b"\xa1\xb2\xc3\xd4"
    if n < 126:            header = struct.pack("!BB", b0, 0x80 | n)
    elif n < (1 << 16):    header = struct.pack("!BBH", b0, 0x80 | 126, n)
    else:                  header = struct.pack("!BBQ", b0, 0x80 | 127, n)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return header + mask + masked

def decode_frames(buf):
    msgs = []; i = 0; L = len(buf)
    while True:
        if L - i < 2: break
        b0, b1 = buf[i], buf[i+1]
        opcode = b0 & 0x0f; masked = b1 & 0x80; ln = b1 & 0x7f; j = i + 2
        if ln == 126:
            if L - j < 2: break
            ln = struct.unpack("!H", buf[j:j+2])[0]; j += 2
        elif ln == 127:
            if L - j < 8: break
            ln = struct.unpack("!Q", buf[j:j+8])[0]; j += 8
        mask = b""
        if masked:
            if L - j < 4: break
            mask = buf[j:j+4]; j += 4
        if L - j < ln: break
        data = buf[j:j+ln]; j += ln
        if masked:
            data = bytes(b ^ mask[k % 4] for k, b in enumerate(data))
        msgs.append((opcode, data)); i = j
    return msgs, buf[i:]

def _set_winsize(fd, rows, cols):
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except Exception:
        pass

def run_pty_session(sock, spawn, env):
    """Blocking pump. Forks a pty, execs `spawn`, bridges sock<->pty until either closes."""
    pid, master = pty.fork()
    if pid == 0:  # child
        os.environ.update(env)
        try: os.execvp(spawn[0], spawn)
        except Exception: os._exit(1)
    buf = b""
    try:
        while True:
            r, _, _ = select.select([sock, master], [], [], 60)
            if master in r:
                try: data = os.read(master, 65536)
                except OSError: data = b""
                if not data:
                    sock.sendall(encode_frame(b"\r\n[ session ended -- tap to reconnect ]\r\n"))
                    break
                sock.sendall(encode_frame(data, opcode=0x2))
            if sock in r:
                chunk = sock.recv(65536)
                if not chunk: break
                buf += chunk
                frames, buf = decode_frames(buf)
                for opcode, payload in frames:
                    if opcode == 0x8:  # close
                        return
                    if opcode in (0x1, 0x2):
                        if payload[:1] == b"\x00":   # control JSON (resize), 0x00 sentinel
                            try:
                                ctl = json.loads(payload[1:].decode())
                                if ctl.get("type") == "resize":
                                    _set_winsize(master, int(ctl["rows"]), int(ctl["cols"]))
                            except Exception:
                                pass
                        else:
                            os.write(master, payload)
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except Exception: pass
        try: os.waitpid(pid, 0)
        except Exception: pass
        try: os.close(master)
        except Exception: pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd 06_DEVELOPMENT/lucrex_command_deck && python3 tests/run.py`
Expected: PASS (all probe + ws tests).

- [ ] **Step 5: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/pty_bridge.py 06_DEVELOPMENT/lucrex_command_deck/tests/test_pty_bridge.py
git commit -m "feat(lucrex-deck): stdlib WebSocket frame codec + pty pump + tests"
```

---

### Task 3: `blubber_server.py` -- HTTP router + /api + /pty upgrade

**Files:**
- Create: `06_DEVELOPMENT/lucrex_command_deck/blubber_server.py`

**Interfaces:**
- Consumes: `probes.session/vitals/git_state/agents`, `pty_bridge.accept_key/run_pty_session`.
- Produces: runnable server. CLI `python3 blubber_server.py [port]` (default 2702). Endpoints:
  `GET /` (index.html), static under `web/`, `GET /api/{vitals,session,git,agents}`, `GET /pty` (WS upgrade).

- [ ] **Step 1: Implement the server**

```python
"""blubber_server.py -- Lucrex Command Deck server (stdlib only).
Serves the deck, read-only JSON probes, and a WebSocket PTY that runs Claude."""
from __future__ import annotations
import json, os, socketserver, sys
from http.server import BaseHTTPRequestHandler
import probes, pty_bridge

ROOT = "/mnt/sdcard/AA_MY_DRIVE"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(APP_DIR, "web")
BIND = os.environ.get("EV_BIND", "127.0.0.1")

CTYPE = {".html":"text/html",".css":"text/css",".js":"text/javascript",
         ".json":"application/json",".svg":"image/svg+xml",".ico":"image/x-icon"}

def _spawn_cmd():
    # Launch claude directly so the zsh auto-chain re-exec loop cannot fire.
    return [os.environ.get("SHELL_CLAUDE", "claude")]

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

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
        path = self.path.split("?",1)[0]
        if path == "/pty":
            return self._upgrade_ws()
        if path.startswith("/api/"):
            name = path[5:]
            if name == "vitals":  return self._json(probes.vitals())
            if name == "session": return self._json(probes.session())
            if name == "git":     return self._json(probes.git_state(ROOT))
            if name == "agents":  return self._json(probes.agents(ROOT))
            return self._send(404, b'{"error":"unknown"}')
        rel = "index.html" if path == "/" else path.lstrip("/")
        if rel.startswith("web/"): rel = rel[4:]
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        with open(full, "rb") as f: body = f.read()
        return self._send(200, body, CTYPE.get(os.path.splitext(full)[1], "application/octet-stream"))

    def _upgrade_ws(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return self._send(400, b"missing key", "text/plain")
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", pty_bridge.accept_key(key))
        self.end_headers()
        env = dict(os.environ)
        env["EV_RAW"] = "1"            # prevent zsh auto-chain double-launch
        env["TERM"] = "xterm-256color"
        try:
            pty_bridge.run_pty_session(self.connection, _spawn_cmd(), env)
        except Exception:
            pass
        try: self.connection.close()
        except Exception: pass

class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 2702
    with Server((BIND, port), Handler) as httpd:
        print(f"Lucrex Command Deck on http://{BIND}:{port}/", flush=True)
        httpd.serve_forever()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test the API endpoints**

Run:
```bash
cd 06_DEVELOPMENT/lucrex_command_deck && (python3 blubber_server.py 2702 & echo $! > /tmp/deck.pid); sleep 1
curl -s http://127.0.0.1:2702/api/vitals | head -c 200; echo
curl -s http://127.0.0.1:2702/api/session | head -c 200; echo
kill "$(cat /tmp/deck.pid)"
```
Expected: two JSON blobs; `session` shows nonzero `tokens.total` (this live session).

- [ ] **Step 3: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/blubber_server.py
git commit -m "feat(lucrex-deck): stdlib HTTP router with /api probes + /pty websocket upgrade"
```

---

### Task 4: Vendor libs + front-end shell (index.html, deck.css, deck.js)

**Files:**
- Create: `web/vendor/xterm.js`, `web/vendor/xterm.css`, `web/vendor/three.min.js`
- Create: `web/index.html`, `web/deck.css`, `web/deck.js`

**Interfaces:**
- Consumes: `/api/*`, `/pty` from Task 3; `window.Blubber.setMood(state)` from Task 5.
- Produces: working terminal + panels in the browser.

- [ ] **Step 1: Vendor the libraries (one-time curl, no npm)**

```bash
cd 06_DEVELOPMENT/lucrex_command_deck/web/vendor
curl -fsSL https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.js -o xterm.js
curl -fsSL https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.css -o xterm.css
curl -fsSL https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js -o three.min.js
ls -la  # confirm all three are non-empty
```
Expected: three non-empty files. (If a mirror fails, retry with `https://unpkg.com/@xterm/xterm@5.5.0/lib/xterm.js` etc.)

- [ ] **Step 2: Write `index.html`**

Layout shell with these regions (exact ids): top bar `#topbar` (crown glyph + "LUCREX" wordmark + `#uptime`), left rail `#rail` (`<canvas id="blubber">` + `#mood` caption + `#tokgauge` + `#agentcount`), center `#terminal`, bottom `#panels` with `#p-session`, `#p-git`, `#p-vitals`. Load order in `<head>`: `vendor/xterm.css`, `deck.css`; before `</body>`: `vendor/three.min.js`, `vendor/xterm.js`, `blubber.js`, `deck.js`. Include `<meta name="viewport" content="width=device-width, initial-scale=1">`.

- [ ] **Step 3: Write `deck.css`**

Theme with the Global-Constraints palette. Requirements: CSS grid `#app` (rail / main); glassmorphism panels (`background: rgba(20,20,14,.7); backdrop-filter: blur(10px); border:1px solid #2a2410`); gold headings (`Georgia, serif` fallback, no external font fetch, offline-safe); mono body (`"JetBrains Mono", ui-monospace, monospace`); Blubber-green glow accents (`box-shadow: 0 0 24px #39ff5a55`). Responsive: `@media (max-width: 820px)` stacks to one column and turns `#panels` into a horizontal scroll row (folded phone); `@media (min-width: 1400px)` widens the terminal (DeX/unfolded).

- [ ] **Step 4: Write `deck.js`**

```javascript
// deck.js -- polls probes, mounts xterm, opens /pty, drives Blubber's mood.
const $ = (s) => document.querySelector(s);
function fmt(n){ return n>=1000 ? (n/1000).toFixed(1)+"k" : String(n); }

async function poll(){
  try {
    const [v,s,g] = await Promise.all([
      fetch("/api/vitals").then(r=>r.json()),
      fetch("/api/session").then(r=>r.json()),
      fetch("/api/git").then(r=>r.json()),
    ]);
    $("#uptime").textContent = `up ${v.uptime||"--"} - load ${v.load||"--"}`;
    $("#p-vitals").innerHTML = `<h3>VITALS</h3>mem ${v.mem_pct}% - disk ${v.disk_pct}%`;
    $("#p-session").innerHTML =
      `<h3>SESSION</h3>${s.turns} turns - ${s.model||"--"}<br>tokens ${fmt(s.tokens.total)}`;
    $("#p-git").innerHTML =
      `<h3>GIT</h3>${g.branch||"--"} - ${g.dirty} dirty<br>${(g.commits||[])[0]||""}`;
    $("#tokgauge").textContent = fmt(s.tokens.total)+" tok";
    const rv = s.recent_output||0;
    const mood = rv>1500 ? "heavy" : rv>300 ? "thinking" : "idle";
    if (window.Blubber) window.Blubber.setMood(mood);
  } catch(e){ /* soft-fail; keep last render */ }
}
setInterval(poll, 3000); poll();

function startTerm(){
  const term = new Terminal({fontFamily:"JetBrains Mono, monospace", fontSize:13,
    theme:{background:"#0a0a0a", foreground:"#e8e8e8", green:"#39ff5a"}, cursorBlink:true});
  term.open($("#terminal"));
  const proto = location.protocol==="https:"?"wss":"ws";
  const ws = new WebSocket(`${proto}://${location.host}/pty`);
  ws.binaryType = "arraybuffer";
  const enc = new TextEncoder();
  function sendResize(){
    const msg = "\x00"+JSON.stringify({type:"resize", cols:term.cols, rows:term.rows});
    if (ws.readyState===1) ws.send(enc.encode(msg));
  }
  ws.onopen = () => { sendResize(); term.focus(); };
  ws.onmessage = (ev) => term.write(new Uint8Array(ev.data));
  ws.onclose = () => term.write("\r\n[ bridge offline -- reload to reconnect ]\r\n");
  term.onData((d) => { if (ws.readyState===1) ws.send(enc.encode(d)); });
  window.addEventListener("resize", sendResize);
}
window.addEventListener("load", startTerm);
```

- [ ] **Step 5: Manual browser check**

Run the server, open `http://127.0.0.1:2702/` via `termux-open-url`. Confirm: panels populate, terminal connects, typing `ls` shows output. (Blubber may be a plain dot until Task 5.)

- [ ] **Step 6: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/web/index.html 06_DEVELOPMENT/lucrex_command_deck/web/deck.css 06_DEVELOPMENT/lucrex_command_deck/web/deck.js 06_DEVELOPMENT/lucrex_command_deck/web/vendor
git commit -m "feat(lucrex-deck): vendored xterm/three + deck shell, panels, embedded terminal"
```

---

### Task 5: `blubber.js` -- crowned 3D mascot + mood state map

**Files:**
- Create: `06_DEVELOPMENT/lucrex_command_deck/web/blubber.js`

**Interfaces:**
- Consumes: `THREE` global, `<canvas id="blubber">`, `#mood` element.
- Produces: `window.Blubber = { setMood(state) }`. States: `idle|listening|thinking|working|heavy|done|resting`.

- [ ] **Step 1: Implement the mascot with CSS fallback**

Requirements:
- If `window.THREE` is undefined, apply a CSS-animated green blob to `#blubber`'s parent and still expose `window.Blubber.setMood` (updates only the caption). Blubber always shows.
- With THREE: a `SphereGeometry` (translucent green `MeshStandardMaterial`, emissive `#39ff5a`) displaced per-frame by sine-noise for the gooey wobble; a low-poly gold "crown" group parented above it; one point light; `requestAnimationFrame` loop.
- `blubberMood(state)` controls wobble amplitude, wobble speed, emissive intensity, crown spin, and caption. Exact map (Lucrex voice, two-hyphen only):

```javascript
const MOODS = {
  idle:      {amp:0.06, spd:0.6, glow:0.5, crown:0.2, lines:["The edge that never sleeps.","Always prepared."]},
  listening: {amp:0.08, spd:0.9, glow:0.7, crown:0.4, lines:["I am listening.","Talk to me."]},
  thinking:  {amp:0.14, spd:1.8, glow:1.0, crown:0.8, lines:["Running the play.","Reading the tape."]},
  working:   {amp:0.18, spd:2.2, glow:1.3, crown:1.6, lines:["42 minds, one move.","Dispatched."]},
  heavy:     {amp:0.24, spd:3.0, glow:1.7, crown:2.0, lines:["Cooking.","This is where I live."]},
  done:      {amp:0.08, spd:0.7, glow:1.2, crown:0.6, lines:["Handled.","Clean."]},
  resting:   {amp:0.04, spd:0.4, glow:0.3, crown:0.1, lines:["Even kings wait."]},
};
```
- Rotate the caption every ~5s from the current mood's `lines`, writing to `#mood`.

- [ ] **Step 2: Manual visual check**

Reload the deck. Confirm: crowned green blob renders and wobbles; force moods from the console (`Blubber.setMood('heavy')`) and confirm it intensifies + caption changes; rename `three.min.js` and confirm the CSS fallback blob still appears.

- [ ] **Step 3: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/web/blubber.js
git commit -m "feat(lucrex-deck): crowned Blubber 3D mascot with Lucrex mood state map + CSS fallback"
```

---

### Task 6: Wire into the machine -- serve_lucrex.sh, .zshrc, hub tile

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh`
- Modify: `/root/.zshrc`
- Modify: `09_DASHBOARD/master_dashboard/templates/index.html`

**Interfaces:**
- Consumes: `blubber_server.py` from Task 3.
- Produces: `serve_lucrex.sh start` runs the deck; `lucrex`/`lx` shell commands; a hub tile.

- [ ] **Step 1: Repoint `serve_lucrex.sh`**

Add a `launch_blubber()` that runs `nohup python3 06_DEVELOPMENT/lucrex_command_deck/blubber_server.py "$PORT" > "$LOGFILE" 2>&1 &` (writing `$PIDFILE`), make `start` call it, and rename the existing node path to a `start-next` case so it stays reachable but is no longer default. Keep `stop/status/logs` working (they already use `$PIDFILE`). Preserve the `127.0.0.1`/`EV_BIND` binding.

- [ ] **Step 2: Verify the launcher**

```bash
bash 03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh restart
sleep 1; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:2702/   # expect 200
bash 03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh status
```
Expected: `200` and a running status.

- [ ] **Step 3: Add the `lucrex()` shell command**

Append to `/root/.zshrc` (near the `kalshi`/`seedance` aliases):

```zsh
# Lucrex Command Deck (King of Divine Light) -- 2700 band :2702
lucrex() {
  case "${1:-}" in
    start) bash $EL_HOME/03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh start ;;
    stop)  bash $EL_HOME/03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh stop ;;
    logs)  bash $EL_HOME/03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh logs ;;
    *)     termux-open-url "http://127.0.0.1:2702/" 2>/dev/null || echo "open http://127.0.0.1:2702/" ;;
  esac
}
alias lx='lucrex'
```

- [ ] **Step 4: Add the hub tile**

In `09_DASHBOARD/master_dashboard/templates/index.html`, copy an existing tile block and point it at `http://127.0.0.1:2702/` with label "LUCREX Command Deck" and a crown glyph, matching the surrounding markup exactly.

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh 09_DASHBOARD/master_dashboard/templates/index.html
git commit -m "feat(lucrex-deck): serve_lucrex default to Blubber deck + hub tile"
```
(Note: `.zshrc` lives outside the repo; it is edited in place, not committed.)

---

### Task 7: End-to-end verification + README + Verification Receipt

**Files:**
- Create: `06_DEVELOPMENT/lucrex_command_deck/README.md`

- [ ] **Step 1: Full unit run**

Run: `cd 06_DEVELOPMENT/lucrex_command_deck && python3 tests/run.py`
Expected: all tests PASS.

- [ ] **Step 2: Live end-to-end drive**

```bash
bash 03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh restart; sleep 1
for e in vitals session git agents; do
  printf "%s -> " "$e"; curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:2702/api/$e"
done
curl -s -o /dev/null -w "index %{http_code}\n" http://127.0.0.1:2702/
bash 03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --status | grep 2702
```
Expected: all `200`; watchdog shows `:2702` alive. Then open in browser, type `ls` in the embedded terminal, confirm output; toggle a mood.

- [ ] **Step 3: Write `README.md`**

Document: what it is, `lucrex`/`lx` usage, ports, how to rebuild vendor libs, the `start-next` opt-in, and the phone-safety constraints. Link back to the design spec.

- [ ] **Step 4: Produce the Verification Receipt**

Paste the actual command outputs from Step 2 (HTTP codes, watchdog line, a note that the terminal echoed `ls`) into the final report so it is proven-real, not simulated.

- [ ] **Step 5: Commit**

```bash
git add 06_DEVELOPMENT/lucrex_command_deck/README.md
git commit -m "docs(lucrex-deck): README + verification receipt"
```

---

## Self-Review

**Spec coverage:** every section maps to a task -- probes/session (T1), pty+ws (T2), server/api (T3), front end + terminal (T4), Blubber + moods (T5), wiring/alias/hub (T6; banner pill already present so no edit), verification (T7). No gaps.

**Placeholder scan:** code steps carry real code; the static-asset files (index.html, deck.css) are specified by exact ids + requirements rather than full listings because they carry no testable logic, and their acceptance is the manual browser check in T4/T5. No "TODO/TBD" left.

**Type consistency:** `session()` returns `recent_output` (used by deck.js mood calc and T5 thresholds); `encode_frame/decode_frames/mask_frame/accept_key/run_pty_session` names match across T2 tests, T2 impl, and T3 server; `window.Blubber.setMood(state)` name matches T4 consumer and T5 producer; mood strings (`idle/thinking/heavy/...`) match deck.js and the MOODS map.
