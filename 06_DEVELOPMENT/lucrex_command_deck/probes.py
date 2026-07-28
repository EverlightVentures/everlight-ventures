"""probes.py -- read-only local state collectors for the Lucrex Command Deck.

Each function returns a plain dict and never raises; any failure lands in the
["error"] key so a single broken probe can never white-screen the deck.
Python stdlib only (no pip).
"""
from __future__ import annotations
import glob, json, os, subprocess, time
from collections import Counter

WORKSPACE = "/mnt/sdcard/AA_MY_DRIVE"
MODEL_CTX = {"claude-opus-4-8": 1000000, "claude-sonnet-5": 1000000,
             "claude-haiku-4-5": 200000, "default": 200000}

DEFAULT_TRANSCRIPT_DIR = os.path.expanduser(
    "~/.claude/projects/-mnt-sdcard-AA-MY-DRIVE")


_DECK_STARTED = 0.0  # epoch set by the server at launch; prefer sessions born after it


def _newest_jsonl(d):
    """Pick the transcript this deck represents.

    Priority: DECK_TRANSCRIPT env override -> the newest transcript created after
    the deck server started (i.e. the session the deck's own terminal spawned) ->
    the globally newest transcript. This stops the display from flickering to an
    unrelated concurrent session (e.g. a long autonomous run in the same dir).
    """
    override = os.environ.get("DECK_TRANSCRIPT")
    if override and os.path.isfile(override):
        return override
    files = glob.glob(os.path.join(d, "*.jsonl"))
    if not files:
        return None
    if _DECK_STARTED:
        fresh = [f for f in files if os.path.getctime(f) >= _DECK_STARTED]
        if fresh:
            return max(fresh, key=os.path.getmtime)
    return max(files, key=os.path.getmtime)


def session(transcript_dir=None):
    """Parse the newest Claude Code transcript and sum real token usage."""
    d = transcript_dir or DEFAULT_TRANSCRIPT_DIR
    out = {"tokens": {"input": 0, "output": 0, "cache_read": 0,
                      "cache_creation": 0, "total": 0},
           "turns": 0, "model": "", "recent_output": 0,
           "source": d, "error": None}
    try:
        path = _newest_jsonl(d)
        if not path:
            out["error"] = "no transcript found"
            return out
        out["source"] = path
        recent = []
        with open(path, "r", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message") or {}
                u = msg.get("usage") or {}
                if not u:
                    continue
                out["turns"] += 1
                if msg.get("model") and msg["model"] != "<synthetic>":
                    out["model"] = msg["model"]
                out["tokens"]["input"] += u.get("input_tokens", 0)
                out["tokens"]["output"] += u.get("output_tokens", 0)
                out["tokens"]["cache_read"] += u.get("cache_read_input_tokens", 0)
                out["tokens"]["cache_creation"] += u.get("cache_creation_input_tokens", 0)
                recent.append(u.get("output_tokens", 0))
        t = out["tokens"]
        t["total"] = t["input"] + t["output"] + t["cache_read"] + t["cache_creation"]
        out["recent_output"] = sum(recent[-3:])
    except Exception as e:
        out["error"] = str(e)
    return out


def vitals():
    """Uptime, load, memory %, disk % from /proc and statvfs."""
    out = {"uptime": "", "load": "", "mem_pct": 0, "disk_pct": 0, "error": None}
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        out["uptime"] = f"{int(secs // 3600)}h {int((secs % 3600) // 60)}m"
        out["load"] = f"{os.getloadavg()[0]:.2f}"
        with open("/proc/meminfo") as f:
            mi = {p.split(':')[0]: int(p.split()[1])
                  for p in f.read().splitlines() if ':' in p}
        total = mi.get("MemTotal", 1)
        avail = mi.get("MemAvailable", mi.get("MemFree", 0))
        out["mem_pct"] = round(100 * (total - avail) / total)
        st = os.statvfs("/mnt/sdcard")
        out["disk_pct"] = round(100 * (st.f_blocks - st.f_bfree) / max(st.f_blocks, 1))
    except Exception as e:
        out["error"] = str(e)
    return out


_git_cache = {"t": 0.0, "data": None}


def git_state(root, ttl=12):
    """Current branch, dirty (tracked) count, and last 3 commit subjects.

    Cached for `ttl` seconds because the deck polls every few seconds and
    `git status` on a large, very dirty sdcard repo is slow. Untracked files
    are skipped (--untracked-files=no) to keep status fast on big trees.
    """
    now = time.time()
    if _git_cache["data"] is not None and now - _git_cache["t"] < ttl:
        return _git_cache["data"]
    out = {"branch": "", "dirty": 0, "commits": [], "deploy": "", "error": None}

    def g(args, timeout=5):
        return subprocess.run(["git", "-C", root] + args,
                              capture_output=True, text=True, timeout=timeout).stdout.strip()
    try:
        out["branch"] = g(["rev-parse", "--abbrev-ref", "HEAD"])
        st = g(["status", "--porcelain", "--untracked-files=no"])
        out["dirty"] = len([l for l in st.splitlines() if l.strip()])
        out["commits"] = g(["log", "--oneline", "-3", "--pretty=%s"]).splitlines()
    except Exception as e:
        out["error"] = str(e)
    _git_cache["t"] = now
    _git_cache["data"] = out
    return out


def agents(root):
    """Recent Hive activity parsed from the AGENT_MAILBOX headings (labeled source)."""
    out = {"recent": [], "source": "AGENT_MAILBOX.md", "error": None}
    try:
        mb = os.path.join(
            root,
            "01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/AGENT_MAILBOX.md")
        if os.path.exists(mb):
            with open(mb, errors="ignore") as f:
                heads = [l.strip("# ").strip() for l in f if l.startswith("#")]
            out["recent"] = heads[-5:]
        else:
            out["error"] = "mailbox not found"
    except Exception as e:
        out["error"] = str(e)
    return out


def _iter_assistant(path):
    """Yield (message, usage) for each assistant turn in a transcript."""
    with open(path, "r", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("type") != "assistant":
                continue
            msg = obj.get("message") or {}
            yield msg, (msg.get("usage") or {})


def token_history(n=24, transcript_dir=None):
    """Per-turn output-token series (last n turns) for the burn chart."""
    d = transcript_dir or DEFAULT_TRANSCRIPT_DIR
    out = {"series": [], "error": None}
    try:
        path = _newest_jsonl(d)
        if not path:
            out["error"] = "no transcript"
            return out
        vals = [u.get("output_tokens", 0) for _, u in _iter_assistant(path) if u]
        out["series"] = vals[-n:]
    except Exception as e:
        out["error"] = str(e)
    return out


def context_window(transcript_dir=None):
    """Latest turn's context occupancy vs the model's window (for the gauge)."""
    d = transcript_dir or DEFAULT_TRANSCRIPT_DIR
    out = {"used": 0, "max": 200000, "pct": 0, "model": "", "error": None}
    try:
        path = _newest_jsonl(d)
        if not path:
            out["error"] = "no transcript"
            return out
        last, model = None, ""
        for msg, u in _iter_assistant(path):
            if not u or msg.get("model") == "<synthetic>":
                continue
            used = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                    + u.get("cache_creation_input_tokens", 0))
            if used > 0:
                last = u
                model = msg.get("model", model)
        if last:
            used = (last.get("input_tokens", 0) + last.get("cache_read_input_tokens", 0)
                    + last.get("cache_creation_input_tokens", 0))
            mx = MODEL_CTX.get(model, MODEL_CTX["default"])
            out.update(model=model, max=mx, used=used,
                       pct=round(100 * used / mx) if mx else 0)
    except Exception as e:
        out["error"] = str(e)
    return out


def activity(n=8, transcript_dir=None):
    """Recent tool_use names from the transcript (the live activity ticker)."""
    d = transcript_dir or DEFAULT_TRANSCRIPT_DIR
    out = {"events": [], "error": None}
    try:
        path = _newest_jsonl(d)
        if not path:
            out["error"] = "no transcript"
            return out
        ev = []
        for msg, _ in _iter_assistant(path):
            content = msg.get("content")
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        ev.append(b.get("name", "tool"))
        out["events"] = ev[-n:]
    except Exception as e:
        out["error"] = str(e)
    return out


def top_commands(n=6):
    """Most-used shell commands from ~/.zsh_history (ranked list widget)."""
    out = {"commands": [], "source": "~/.zsh_history", "error": None}
    try:
        hp = os.path.expanduser("~/.zsh_history")
        if not os.path.exists(hp):
            out["error"] = "no history"
            return out
        c = Counter()
        with open(hp, errors="ignore") as f:
            for line in f:
                line = line.strip()
                cmd = line.split(";", 1)[1] if (line.startswith(":") and ";" in line) else line
                w = cmd.strip().split()
                # count real command tokens only (skip continuation junk: \, --, dates)
                if w and w[0][:1].isalpha() and 1 < len(w[0]) <= 20:
                    c[w[0]] += 1
        out["commands"] = [{"cmd": k, "count": v} for k, v in c.most_common(n)]
    except Exception as e:
        out["error"] = str(e)
    return out


def fs(path=None):
    """Sandboxed read-only directory listing (folders first) for the file manager."""
    root = WORKSPACE
    p = os.path.realpath(path or root)
    out = {"cwd": p, "parent": os.path.dirname(p), "root": root, "entries": [], "error": None}
    if not (p == root or p.startswith(root + os.sep)):
        p = root
        out.update(cwd=root, parent=os.path.dirname(root), error="outside workspace")
    try:
        items = []
        with os.scandir(p) as it:
            for e in it:
                try:
                    isdir = e.is_dir()
                    items.append({"name": e.name, "type": "dir" if isdir else "file",
                                  "size": 0 if isdir else e.stat().st_size})
                except OSError:
                    continue
        items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
        out["entries"] = items[:800]
    except Exception as ex:
        out["error"] = str(ex)
    return out


if __name__ == "__main__":
    print(json.dumps({"vitals": vitals(),
                      "session": {k: v for k, v in session().items() if k != "source"},
                      "git": git_state("/mnt/sdcard/AA_MY_DRIVE")}, indent=2))
