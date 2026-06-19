#!/usr/bin/env python3
"""watchdog.py -- the self-healing watchdog for the Kalshi engine.

Rich's ask (2026-06-15): "I don't want to always find it myself. I want a service
that tracks win/lose, figures out WHY we started losing, and patches it -- then
tells me what it fixed and why, in a little CEO memo on a dashboard."

DESIGN PRINCIPLE (revised per Rich 2026-06-15: "if the logic supports it, it should be
able to place a BIGGER bet -- be adaptive in a good way too, don't limit yourself").
The watchdog is ADAPTIVE BOTH WAYS: it leans OUT of weak/blind/bleeding segments AND
leans IN on segments with proven, well-covered, high-conviction edge. The ONE thing it
can never touch is the absolute risk ceiling + the balance floor -- the ruin-prevention
governor (the XLM lesson). Inside that governor, gas AND brakes, driven by evidence not
feelings. It earns the keys with the same paper->live discipline as the rest of the system.

  v1 (THIS FILE) = DIAGNOSE + MEMO, read-only. Watches the settled record, detects a
    regime shift (was winning -> now losing), pins the culprit segment (sport / lane /
    coverage), checks if we're betting blind, and writes a plain-English CEO memo +
    Slack + a dashboard feed. It RECOMMENDS the patch; it does not apply it yet.
  v2 (next, gated on v1 proving correct) = brakes-only AUTO-PATCH: writes
    watchdog_state.json (quarantined sports/lanes + expiry) that auto_edge reads and
    obeys. Reversible, time-boxed, always memo'd.

Run (e5):  PYTHONPATH=/home/ubuntu/AA_MY_DRIVE/06_DEVELOPMENT python3 -m kalshi_agent.watchdog
"""
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
LEDGER = HERE / "data" / "auto_edge_ledger.jsonl"
MEMOS = HERE / "data" / "watchdog_memos.jsonl"
STATE = HERE / "data" / "watchdog_state.json"   # v2 brakes+gas the engine obeys
CONFIG = HERE / "auto_edge_config.json"
# write the HTML where it exists so the dashboard can serve it (e5), else next to us
HTML_DIRS = ["/home/ubuntu/hive_reports", str(HERE)]

# how the watchdog reads the tape
RECENT_N = 10          # the "now" window of settled bets
PRIOR_N = 10           # the "before" window we compare against
MIN_SEG_VOL = 3        # a segment needs this many bets before we blame it
DROP_ALERT = 0.15      # a >=15pt win-rate drop recent-vs-prior = regime shift
TARGET = 0.75          # the win-rate we steer to (mirrors auto_edge target_win_rate)
STREAK_N = 3           # N consecutive losses in a sport -> quarantine it (Rich's "bad streak -> switch sport")

# Kalshi ticker prefix -> sport, and sport -> Odds-API key (for the coverage check)
SPORT_PREFIX = [("KXNBA", "nba"), ("KXMLB", "mlb"), ("KXNHL", "nhl"),
                ("KXWC", "wc"), ("KXUFC", "ufc"), ("KXNFL", "nfl"), ("KXWNBA", "wnba"),
                ("KXKBO", "kbo"), ("KXNPB", "npb")]


def _client(creds):
    from kalshi_agent.execution.kalshi_exec import from_creds
    return from_creds(creds) if creds else from_creds()


def sport_of(ticker):
    t = (ticker or "").upper()
    for pre, sp in SPORT_PREFIX:
        if t.startswith(pre):
            return sp
    return "other"


def _lane_map():
    """ticker -> lane, from the engine's own ledger (so we can blame a LANE, not just a sport)."""
    out = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ticker") and r.get("lane"):
                out.setdefault(r["ticker"], r["lane"])
    return out


def settled_rows(k):
    """Every settled bet as (settled_time, ticker, sport, lane, won, pnl) -- rebuilt from
    FILLS (the honest source; /positions reports 0) joined to settlements. Chronological."""
    fills = k._request("GET", "/portfolio/fills").get("fills", [])
    setls = {s["ticker"]: s for s in k._request("GET", "/portfolio/settlements").get("settlements", [])}
    lanes = _lane_map()
    agg = defaultdict(lambda: {"contracts": 0.0, "cost": 0.0, "side": None})
    for f in fills:
        tk, sd = f.get("ticker"), f.get("side")
        c = float(f.get("count_fp") or 0)
        px = float(f.get("yes_price_dollars") or 0) if sd == "yes" else float(f.get("no_price_dollars") or 0)
        sgn = 1 if f.get("action") == "buy" else -1
        a = agg[tk]; a["contracts"] += sgn * c; a["cost"] += sgn * c * px
        if a["side"] is None:
            a["side"] = sd
    rows = []
    for tk, a in agg.items():
        if tk in setls and abs(a["contracts"]) >= 0.01:
            s = setls[tk]
            won = s.get("market_result") == a["side"]
            pnl = (a["contracts"] if won else 0.0) - a["cost"]
            rows.append((s.get("settled_time", ""), tk, sport_of(tk), lanes.get(tk, "?"), won, pnl))
    rows.sort()
    return rows


def _wr(rows):
    if not rows:
        return None
    return sum(1 for r in rows if r[4]) / len(rows)


def _seg_stats(rows, idx):
    """Win-rate / count / pnl grouped by field `idx` (2=sport, 3=lane)."""
    g = defaultdict(lambda: {"w": 0, "n": 0, "pnl": 0.0})
    for r in rows:
        key = r[idx]
        g[key]["n"] += 1
        g[key]["w"] += 1 if r[4] else 0
        g[key]["pnl"] += r[5]
    return {k: {"wr": v["w"] / v["n"], "n": v["n"], "pnl": v["pnl"]} for k, v in g.items()}


def coverage_blind(sport):
    """True if the odds service currently has NO multi-book coverage for this sport
    (so the engine would be betting blind on a single book -- the soccer trap)."""
    try:
        from kalshi_agent.dataflows import odds_api
        key = odds_api.SPORT_KEYS.get(sport)
        if not key:
            return None                       # we don't expect book coverage for this one (e.g. ufc)
        games = odds_api.consensus(key)
        if not games:
            return True
        return max((g.get("books", 0) for g in games), default=0) < 2
    except Exception:
        return None


def _streaks(rows):
    """Per-sport TRAILING consecutive-loss count (chronological). The 'bad streak' signal."""
    seqs = defaultdict(list)
    for r in rows:
        seqs[r[2]].append(r[4])           # sport -> [won, won, ...] in time order
    out = {}
    for sp, seq in seqs.items():
        n = 0
        for won in reversed(seq):
            if won:
                break
            n += 1
        out[sp] = n
    return out


def analyze(rows):
    recent = rows[-RECENT_N:]
    prior = rows[-(RECENT_N + PRIOR_N):-RECENT_N]
    r_wr, p_wr = _wr(recent), _wr(prior)
    sports = _seg_stats(recent, 2)
    lanes = _seg_stats(recent, 3)
    # the culprit = the segment dragging us down: worst win-rate with enough volume, and
    # actually losing money. Prefer a sport (Rich thinks in sports), fall back to lane.
    # Culprit = the segment dragging the WIN RATE (what Rich watches), not the P&L. A lane
    # can be win-rate-poor yet green on money because one outlier propped it up (World Cup:
    # 40% wins but +$32 off the lucky Australia longshot) -- that is the trap, so we judge on
    # win-rate with enough volume, and note separately whether an outlier is masking it.
    BAD_WR = TARGET - DROP_ALERT          # 0.55 -- below this, a segment is bleeding the record
    cands = [(k, v) for k, v in sports.items() if v["n"] >= MIN_SEG_VOL and v["wr"] < BAD_WR]
    cands.sort(key=lambda kv: kv[1]["wr"])
    culprit = cands[0] if cands else None
    # ADAPTIVE BOTH WAYS (Rich): also surface the segment worth LEANING INTO -- best
    # win-rate, real volume, actually making money. The size-up half of the gas pedal.
    hot = [(k, v) for k, v in sports.items() if v["n"] >= MIN_SEG_VOL and v["pnl"] > 0 and v["wr"] >= TARGET]
    hot.sort(key=lambda kv: -kv[1]["wr"])
    # BAD-STREAK detector (Rich: "bad streak in a sport -> bet a different sport"). Trailing
    # consecutive losses per sport over the full record; quarantine fires off this even when
    # the windowed win-rate hasn't dropped below BAD_WR yet -- faster than the window.
    streaks = _streaks(rows)
    cold = sorted([(sp, n) for sp, n in streaks.items() if n >= STREAK_N], key=lambda x: -x[1])
    regime_shift = bool(r_wr is not None and (
        (p_wr is not None and r_wr <= p_wr - DROP_ALERT) or r_wr <= TARGET - DROP_ALERT))
    return {"recent_wr": r_wr, "prior_wr": p_wr, "recent_n": len(recent), "prior_n": len(prior),
            "sports": sports, "lanes": lanes, "culprit": culprit, "hot": hot[0] if hot else None,
            "cold_streak": cold[0] if cold else None, "streaks": streaks,
            "regime_shift": regime_shift, "all_time_wr": _wr(rows), "all_time_n": len(rows)}


def _cfg():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def _load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"quarantine": {}, "lean_in": {}}


def _write_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def decide_actions(a, cfg, blind_fn, now):
    """PURE decision (no IO/network -- blind_fn injected so it's testable). Returns
    (quarantine_updates, lean_in_updates, action_strings). BRAKES quarantine a bleeding
    COVERED segment (a BLIND bleeder needs none -- the no-coverage gate already skips it).
    GAS leans into a proven hot COVERED segment, bounded + time-boxed."""
    hours = cfg.get("watchdog_quarantine_hours", 24)
    mult = cfg.get("watchdog_lean_in_mult", 1.25)
    cool = int(hours * 3600)
    q, li, actions = {}, {}, []
    if a["culprit"]:
        sp, sv = a["culprit"]
        if blind_fn(sp) is True:
            actions.append("%s is bleeding but BLIND -- the no-coverage gate already sits it out; no quarantine needed." % sp.upper())
        else:
            q[sp] = {"until": now + cool, "reason": "%.0f%% win-rate over %d bets" % (sv["wr"] * 100, sv["n"]),
                     "wr": sv["wr"], "n": sv["n"]}
            actions.append("BRAKES: quarantined %s for %dh (%.0f%% win-rate over %d) -- auto-lifts when it recovers." % (
                sp.upper(), hours, sv["wr"] * 100, sv["n"]))
    # BAD-STREAK brake (Rich: "bad streak in a sport -> bet a different sport"). Fires off a
    # raw consecutive-loss streak, faster than the windowed win-rate. Quarantine = rotate away.
    if a.get("cold_streak"):
        sp, n = a["cold_streak"]
        if sp not in q:
            if blind_fn(sp) is True:
                actions.append("%s on a %d-loss streak but BLIND -- the gate already sits it out." % (sp.upper(), n))
            else:
                q[sp] = {"until": now + cool, "reason": "%d losses in a row" % n, "streak": n}
                actions.append("BRAKES: quarantined %s for %dh (%d-loss streak) -- rotating to other sports." % (
                    sp.upper(), hours, n))
    if a.get("hot"):
        hs, hv = a["hot"]
        if blind_fn(hs) is not True:
            li[hs] = {"until": now + cool, "mult": mult, "reason": "%.0f%% win-rate over %d bets" % (hv["wr"] * 100, hv["n"]),
                      "wr": hv["wr"], "n": hv["n"]}
            actions.append("GAS: lean-in on %s x%.2f for %dh (%.0f%% win-rate over %d) -- bigger stakes while the edge holds, still under the ceiling." % (
                hs.upper(), mult, hours, hv["wr"] * 100, hv["n"]))
    return q, li, actions


def apply_state(a):
    """v2: write the brakes+gas the engine reads. Returns (state, actions) or (None, []) if
    auto-patch is off. Expired entries drop on every pass = auto-release."""
    cfg = _cfg()
    if not cfg.get("watchdog_autopatch", False):
        return None, []
    now = int(time.time())
    st = _load_state()
    st = {"ts": now,
          "quarantine": {k: v for k, v in st.get("quarantine", {}).items() if v.get("until", 0) > now},
          "lean_in": {k: v for k, v in st.get("lean_in", {}).items() if v.get("until", 0) > now}}
    q, li, actions = decide_actions(a, cfg, coverage_blind, now)
    st["quarantine"].update(q)
    st["lean_in"].update(li)
    _write_state(st)
    return st, actions


def build_memo(a, actions=None):
    pct = lambda x: ("%.0f%%" % (x * 100)) if x is not None else "n/a"
    alert = a["regime_shift"]
    title = "Win-rate watchdog: %s" % ("RECORD SLIPPING -- action recommended" if alert else "holding steady")
    what = "Last %d settled bets: %s wins (the %d before: %s). All-time %s over %d bets." % (
        a["recent_n"], pct(a["recent_wr"]), a["prior_n"], pct(a["prior_wr"]),
        pct(a["all_time_wr"]), a["all_time_n"])
    why, rec, blind = "No single segment is dragging us down right now.", \
        "Hold -- the controller is steering the win-prob floor on its own.", None
    if a["culprit"]:
        sp, st = a["culprit"]
        blind = coverage_blind(sp)
        mask = " (green only on one outlier -- the win rate is the real signal)" if (st["pnl"] > 0 and st["wr"] < 0.5) else ""
        why = "The bleed is concentrated in %s: %s win-rate over %d bets, %s$%.2f%s. %s" % (
            sp.upper(), pct(st["wr"]), st["n"],
            "-" if st["pnl"] < 0 else "+", abs(st["pnl"]), mask,
            ("We have NO multi-book coverage for %s right now -- those were single-book bets = betting blind." % sp.upper())
            if blind else "Coverage looks OK, so this reads as variance or a soft model on this sport.")
        if blind:
            rec = ("Already auto-handled: the no-coverage guard (require_consensus_books) now sits %s out "
                   "until the odds service covers it again. No further action needed." % sp.upper())
        else:
            rec = "QUARANTINE %s for 24h until its record recovers (auto-applied below)." % sp.upper()
    # the gas-pedal half: if a segment is proven hot AND covered, recommend leaning in.
    if a.get("hot"):
        hs, hv = a["hot"]
        if coverage_blind(hs) is not True:
            rec += ("  LEAN IN: %s is running %.0f%% over %d bets (+$%.2f) -- conviction sizing "
                    "will stake these bigger while the edge holds." % (hs.upper(), hv["wr"] * 100, hv["n"], hv["pnl"]))
    taken = ("Auto-patch OFF -- recommend only." if actions is None
             else ("; ".join(actions) if actions
                   else "No auto-action needed -- nothing covered is bleeding and no hot segment to lean into."))
    return {"ts": int(time.time()), "alert": alert, "title": title, "what_changed": what,
            "why": why, "recommendation": rec, "action_taken": taken,
            "culprit": (a["culprit"][0] if a["culprit"] else None),
            "blind": blind, "stats": {"recent_wr": a["recent_wr"], "all_time_wr": a["all_time_wr"],
                                      "sports": a["sports"], "lanes": a["lanes"]}}


def _html(memos):
    G, DK, LT = "#D4AF37", "#0A0A0A", "#E8E8E8"
    rows = []
    for m in memos[:30]:
        when = time.strftime("%Y-%m-%d %H:%M PT", time.localtime(m["ts"] - 8 * 3600))
        bar = "#c0392b" if m.get("alert") else G
        rows.append(
            "<div style='border-left:4px solid %s;background:#141414;margin:14px 0;padding:14px 18px;border-radius:8px'>"
            "<div style='color:%s;font-weight:700;font-size:15px'>%s</div>"
            "<div style='color:#888;font-size:12px;margin:2px 0 10px'>%s</div>"
            "<div style='margin:6px 0'><b style='color:%s'>What changed:</b> %s</div>"
            "<div style='margin:6px 0'><b style='color:%s'>Why:</b> %s</div>"
            "<div style='margin:6px 0'><b style='color:%s'>Recommendation:</b> %s</div>"
            "<div style='margin:6px 0;color:#888'><b>Action taken:</b> %s</div></div>" % (
                bar, bar, m["title"], when, G, m["what_changed"], G, m["why"], G, m["recommendation"], m["action_taken"]))
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='120'><title>Kalshi Watchdog -- CEO Memos</title></head>"
            "<body style='background:%s;color:%s;font-family:Inter,system-ui,sans-serif;max-width:820px;margin:0 auto;padding:28px'>"
            "<h1 style='font-family:\"Playfair Display\",Georgia,serif;color:%s;margin-bottom:2px'>Kalshi Watchdog</h1>"
            "<div style='color:#888;margin-bottom:18px'>Self-healing engine -- what changed, why, and what was done. Auto-refresh 120s.</div>"
            "%s</body></html>" % (DK, LT, G, "".join(rows) or "<i>No memos yet.</i>"))


def write_outputs(memo):
    MEMOS.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMOS, "a") as f:
        f.write(json.dumps(memo) + "\n")
    memos = [json.loads(l) for l in MEMOS.read_text().splitlines() if l.strip()][::-1]
    html = _html(memos)
    for d in HTML_DIRS:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            (Path(d) / "watchdog.html").write_text(html)
            break
        except Exception:
            continue
    # Slack courtesy ping (never blocks)
    try:
        from content_tools import branded_slack
        sev = "warn" if memo["alert"] else "info"
        branded_slack.post_branded_alert("kalshi-watchdog",
                                         "%s\n%s\n%s" % (memo["what_changed"], memo["why"], memo["recommendation"]),
                                         severity=sev)
    except Exception:
        pass


def _sig(m):
    """What makes a memo 'the same news' -- so a 30-min cron doesn't flood the log/Slack."""
    return (m.get("alert"), m.get("culprit"), m.get("blind"), m.get("action_taken"))


def _unchanged(memo):
    if not MEMOS.exists():
        return False
    lines = [l for l in MEMOS.read_text().splitlines() if l.strip()]
    if not lines:
        return False
    try:
        return _sig(json.loads(lines[-1])) == _sig(memo)
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creds", default="/home/ubuntu/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials")
    ap.add_argument("--force", action="store_true", help="write a memo even if nothing changed")
    args = ap.parse_args()
    k = _client(args.creds)
    rows = settled_rows(k)
    if not rows:
        print("watchdog: no settled bets yet.")
        return 0
    a = analyze(rows)
    state, actions = apply_state(a)                       # v2: act (brakes+gas) if autopatch is on
    memo = build_memo(a, actions if state is not None else None)
    if _unchanged(memo) and not args.force:
        print("watchdog: no change since last memo (%s) -- staying quiet." % memo["title"])
        return 0
    write_outputs(memo)
    print("=" * 64)
    print("  KALSHI WATCHDOG --", memo["title"])
    print("=" * 64)
    print("  WHAT CHANGED:", memo["what_changed"])
    print("  WHY:", memo["why"])
    print("  RECOMMENDATION:", memo["recommendation"])
    print("  ACTION TAKEN:", memo["action_taken"])
    print("  by sport (last %d):" % a["recent_n"],
          ", ".join("%s %.0f%%/%d/%s$%.0f" % (s, v["wr"] * 100, v["n"], "-" if v["pnl"] < 0 else "+", abs(v["pnl"]))
                    for s, v in sorted(a["sports"].items(), key=lambda kv: kv[1]["wr"])))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
