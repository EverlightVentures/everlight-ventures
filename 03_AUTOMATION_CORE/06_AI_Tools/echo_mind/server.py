#!/usr/bin/env python3
"""Echo Mind — API + static server on port 8503."""
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8503
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
NOTES_FILE = DATA_DIR / "notes.json"


def _load_notes():
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except Exception:
            return []
    return []


def _save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def _extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def _fetch_youtube_transcript(url):
    """Fetch transcript from YouTube video."""
    video_id = _extract_video_id(url)
    if not video_id:
        return None, "Could not extract video ID from URL"
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        lines = []
        for entry in transcript:
            lines.append(entry.text)
        full_text = " ".join(lines)
        return full_text, None
    except Exception as e:
        return None, f"Failed to fetch transcript: {e}"


def _summarize_text(text, max_sentences=8):
    """Simple extractive summary — pick most information-dense sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= max_sentences:
        return text
    scored = []
    words_all = set(text.lower().split())
    for s in sentences:
        words = s.lower().split()
        unique = len(set(words))
        length_score = min(len(words) / 20, 1.0)
        scored.append((s, unique * length_score))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:max_sentences]
    # Restore original order
    ordered = sorted(top, key=lambda x: text.index(x[0]))
    return " ".join(s for s, _ in ordered)


def _extract_key_points(text, max_points=6):
    """Extract key phrases/concepts from text."""
    # Simple TF approach — find most frequent meaningful phrases
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stop = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they',
            'their', 'about', 'would', 'could', 'should', 'which', 'there',
            'these', 'those', 'then', 'than', 'what', 'when', 'where', 'will',
            'just', 'also', 'very', 'more', 'some', 'only', 'into', 'over',
            'such', 'after', 'before', 'other', 'like', 'because', 'going',
            'really', 'know', 'think', 'want', 'need', 'make', 'much'}
    freq = {}
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:max_points]
    return [w for w, _ in top]


class EchoMindHandler(SimpleHTTPRequestHandler):
    """Handle API routes + static files."""

    def log_message(self, format, *args):
        if len(args) >= 2 and str(args[1]) != '200':
            super().log_message(format, *args)

    def end_headers(self):
        # Prevent browser caching of HTML so code changes take effect immediately
        if hasattr(self, '_path_is_html') and self._path_is_html:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/notes":
            notes = _load_notes()
            # Return without full text for list view
            slim = [{k: v for k, v in n.items() if k != "text"} for n in notes]
            self._json_response(slim)

        elif self.path.startswith("/api/note/"):
            nid = self.path.split("/api/note/")[1]
            notes = _load_notes()
            note = next((n for n in notes if n["id"] == nid), None)
            if note:
                self._json_response(note)
            else:
                self._json_response({"error": "not found"}, 404)

        elif self.path.startswith("/api/export/"):
            nid = self.path.split("/api/export/")[1]
            notes = _load_notes()
            note = next((n for n in notes if n["id"] == nid), None)
            if not note:
                self._json_response({"error": "not found"}, 404)
                return
            md = f"# Echo Mind — {note.get('mode', 'note').title()}\n"
            md += f"_{note.get('createdAt', '')}_\n\n---\n\n{note.get('text', '')}\n"
            if note.get("summary"):
                md += f"\n---\n\n## Summary\n\n{note['summary']}\n"
            if note.get("keyPoints"):
                md += f"\n## Key Concepts\n\n"
                for kp in note["keyPoints"]:
                    md += f"- {kp}\n"
            body = md.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="echomind_{nid}.md"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            # Serve static files — mark HTML for no-cache
            self._path_is_html = self.path.endswith('.html') or self.path in ('/', '')
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/save":
            try:
                body = self._read_body()
                text = body.get("text", "").strip()
                if not text:
                    self._json_response({"error": "empty text"}, 400)
                    return
                notes = _load_notes()
                note = {
                    "id": body.get("id") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                          + hex(id(text))[-4:],
                    "mode": body.get("mode", "note"),
                    "text": text,
                    "title": body.get("title", ""),
                    "source": body.get("source", "voice"),
                    "sourceUrl": body.get("sourceUrl", ""),
                    "wordCount": len(text.split()),
                    "duration": body.get("duration", 0),
                    "summary": _summarize_text(text) if len(text.split()) > 30 else text,
                    "keyPoints": _extract_key_points(text),
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                notes.insert(0, note)
                _save_notes(notes)
                self._json_response(note)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        elif self.path == "/api/youtube":
            try:
                body = self._read_body()
                url = body.get("url", "").strip()
                if not url:
                    self._json_response({"error": "no URL"}, 400)
                    return
                text, err = _fetch_youtube_transcript(url)
                if err:
                    self._json_response({"error": err}, 400)
                    return
                summary = _summarize_text(text)
                key_points = _extract_key_points(text)
                # Auto-save as a note
                notes = _load_notes()
                note = {
                    "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                          + hex(abs(hash(url)))[-4:],
                    "mode": "note",
                    "text": text,
                    "title": f"YouTube: {url}",
                    "source": "youtube",
                    "sourceUrl": url,
                    "wordCount": len(text.split()),
                    "duration": 0,
                    "summary": summary,
                    "keyPoints": key_points,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                notes.insert(0, note)
                _save_notes(notes)
                self._json_response({
                    "note": note,
                    "transcript": text,
                    "summary": summary,
                    "keyPoints": key_points,
                })
            except Exception as e:
                traceback.print_exc()
                self._json_response({"error": str(e)}, 500)

        elif self.path == "/api/summarize":
            try:
                body = self._read_body()
                text = body.get("text", "")
                self._json_response({
                    "summary": _summarize_text(text),
                    "keyPoints": _extract_key_points(text),
                })
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        else:
            self._json_response({"error": "not found"}, 404)

    def do_DELETE(self):
        if self.path.startswith("/api/note/"):
            nid = self.path.split("/api/note/")[1]
            notes = _load_notes()
            before = len(notes)
            notes = [n for n in notes if n["id"] != nid]
            if len(notes) < before:
                _save_notes(notes)
                self._json_response({"ok": True})
            else:
                self._json_response({"error": "not found"}, 404)
        else:
            self._json_response({"error": "not found"}, 404)


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def main():
    os.chdir(str(ROOT))
    server = ReusableHTTPServer(("0.0.0.0", PORT), EchoMindHandler)
    print(f"Echo Mind serving on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
