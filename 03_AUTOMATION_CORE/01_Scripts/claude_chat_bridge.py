"""Claude Chat Bridge -- HTTP server that wraps Claude Code CLI.

Runs on the phone (Termux). Accepts POST /ask with a message,
runs `claude --print` with full workspace context, returns the response.

This gives the React dashboard the same Claude Code brain that runs
in the terminal -- same CLAUDE.md, same memory, same MCP tools, same agents.

Usage:
    python3 claude_chat_bridge.py          # starts on port 8510
    python3 claude_chat_bridge.py --port 8511
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

WORKSPACE = "/mnt/sdcard/AA_MY_DRIVE"
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
PORT = int(sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else 8510)


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            self._json_response({"ok": True, "service": "claude_chat_bridge", "workspace": WORKSPACE})
            return
        self.send_error(404)

    def do_POST(self):
        if self.path == "/ask":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            question = str(body.get("message", body.get("question", ""))).strip()
            mode = str(body.get("mode", "review")).strip()

            if not question:
                self._json_response({"answer": "No message provided.", "engine": "claude-code"})
                return

            # Build claude command
            # --print = non-interactive, single response
            # Uses the workspace CLAUDE.md, memory, and all MCP tools
            cmd = [
                CLAUDE_BIN,
                "--print",
                question,
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=WORKSPACE,
                    env={
                        **os.environ,
                        "CLAUDE_CODE_ENTRY_POINT": "chat-bridge",
                    },
                )
                answer = (result.stdout or "").strip()
                if not answer and result.stderr:
                    answer = f"(stderr: {result.stderr.strip()[:300]})"
                if not answer:
                    answer = f"(No output, exit code {result.returncode})"
            except subprocess.TimeoutExpired:
                answer = "(Timed out after 60s -- try a shorter question)"
            except FileNotFoundError:
                answer = f"Claude CLI not found at: {CLAUDE_BIN}"
            except Exception as e:
                answer = f"Error: {str(e)[:300]}"

            self._json_response({
                "answer": answer,
                "engine": "claude-code",
                "mode": mode,
                "workspace": WORKSPACE,
            })
            return

        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Quiet logging
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {args[0] if args else ''}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ChatHandler)
    print(f"Claude Chat Bridge running on port {PORT}")
    print(f"Workspace: {WORKSPACE}")
    print(f"Claude CLI: {CLAUDE_BIN}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
