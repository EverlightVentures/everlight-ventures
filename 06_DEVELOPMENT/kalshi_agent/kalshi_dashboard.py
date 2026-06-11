#!/usr/bin/env python3
"""kalshi_dashboard.py -- the permanent gold-themed P&L dashboard (static HTML).

Pulls LIVE balance / positions / settlements straight from the Kalshi account,
rebuilds a per-bet ledger from the fills (the only honest source of what we
actually bought), marks open bets to market, computes the win/loss record + ROI,
and renders one self-contained, self-refreshing HTML page in the Everlight gold
theme. No JS framework, no build step -- just open the file.

Run on e5 (creds live there). Cron'd every 15 min right after auto_edge so the
numbers are never more than a quarter-hour stale.

  python3 -m kalshi_agent.kalshi_dashboard
"""
import json
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from kalshi_agent.execution import kalshi_exec as ke
from kalshi_agent.dataflows import kalshi_api as kapi

CREDS = "/home/ubuntu/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials"
HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
UPCOMING = HERE / "data" / "upcoming_edges.json"  # engine's gate-passing edges, queued to place
FUNDED_BASELINE = 116.26          # initial Kalshi deposit (memory: kalshi_live_funded)
PT = timezone(timedelta(hours=-7))  # Pacific (PDT in June)

# where to drop the HTML -- first writable path wins, all that exist get written
OUT_PATHS = [
    "/home/ubuntu/hive_reports/kalshi_dashboard.html",   # e5 served dir (tailnet)
    str(HERE / "kalshi_dashboard.html"),                  # next to the agent
]

SPORT_NAME = {"KXNBAGAME": "NBA", "KXMLBGAME": "MLB", "KXNHLGAME": "NHL",
              "KXWCGAME": "World Cup", "KXATPMATCH": "ATP", "KXWTAMATCH": "WTA",
              "KXBTC": "Bitcoin", "KXBTCD": "Bitcoin", "KXNBA": "NBA Champ"}


def pretty(ticker):
    """KXNBAGAME-26JUN10SASNYK-NYK -> ('NBA', 'NYK', 'Jun 10')."""
    parts = ticker.split("-")
    series = parts[0]
    sport = SPORT_NAME.get(series, series.replace("KX", "").replace("GAME", ""))
    pick = parts[-1] if len(parts) > 2 else ""
    date = ""
    if len(parts) > 1:
        mid = parts[1]
        # date token looks like 26JUN10... grab the leading YYMONDD
        for i in range(len(mid)):
            if mid[i:i + 3].isalpha():
                try:
                    yy, mon, dd = mid[i - 2:i], mid[i:i + 3], mid[i + 3:i + 5]
                    date = "%s %d" % (mon.title(), int(dd))
                except Exception:
                    pass
                break
    return sport, pick, date


def build_ledger():
    cli = ke.from_creds(CREDS)
    bal = cli.get_balance()
    fills = cli._request("GET", "/portfolio/fills").get("fills", [])
    setls = {s["ticker"]: s for s in cli._request("GET", "/portfolio/settlements").get("settlements", [])}

    agg = defaultdict(lambda: {"contracts": 0.0, "cost": 0.0, "side": None})
    for f in fills:
        tk = f.get("ticker"); sd = f.get("side")
        c = float(f.get("count_fp") or 0)
        px = float(f.get("yes_price_dollars") or 0) if sd == "yes" else float(f.get("no_price_dollars") or 0)
        sgn = 1 if f.get("action") == "buy" else -1
        a = agg[tk]; a["contracts"] += sgn * c; a["cost"] += sgn * c * px
        if a["side"] is None:
            a["side"] = sd

    open_rows, settled_rows = [], []
    realized = wins = losses = 0.0
    staked_settled = 0.0
    for tk, a in agg.items():
        if abs(a["contracts"]) < 0.01:
            continue
        sport, pick, date = pretty(tk)
        if tk in setls:
            won = setls[tk].get("market_result") == a["side"]
            payout = a["contracts"] if won else 0.0
            pnl = payout - a["cost"]
            realized += pnl; staked_settled += a["cost"]
            wins += 1 if won else 0; losses += 0 if won else 1
            settled_rows.append({"sport": sport, "pick": pick, "date": date,
                                 "ct": a["contracts"], "cost": a["cost"],
                                 "won": won, "pnl": pnl,
                                 "when": setls[tk].get("settled_time", "")})
        else:
            try:
                yb, ya, nb, *_ = kapi.best_bbo(tk)
                mid = ((yb + ya) / 2) / 100.0 if yb and ya else None
            except Exception:
                mid = None
            mv = (mid * a["contracts"]) if mid else a["cost"]
            avg = a["cost"] / a["contracts"] if a["contracts"] else 0
            open_rows.append({"ticker": tk, "sport": sport, "pick": pick, "date": date,
                              "ct": a["contracts"], "cost": a["cost"], "avg": avg,
                              "mid": mid, "mv": mv,
                              "to_win": a["contracts"] - a["cost"]})

    open_mv = sum(r["mv"] for r in open_rows)
    equity = bal + open_mv
    rec = int(wins + losses)
    winrate = (wins / rec) if rec else 0.0
    roi = (realized / staked_settled) if staked_settled else 0.0

    # COMING UP = the engine's gate-PASSING edges (real, sharp-researched, cronned and
    # queued to be placed -- or already on). NOT the loose "watching" list. Sourced from
    # what auto_edge actually flagged this cycle.
    open_keys = {r["ticker"] for r in open_rows}
    upcoming, fresh = [], 0
    try:
        u = json.loads(UPCOMING.read_text())
        fresh = u.get("ts", 0)
        seen = set()
        for e in u.get("edges", []):
            tk = e.get("ticker")
            if not tk or tk in seen:
                continue
            seen.add(tk)
            sport, pick, date = pretty(tk)
            upcoming.append({"sport": sport, "pick": pick, "date": date,
                             "fair": e.get("fair"), "cents": e.get("our_cents"),
                             "net": e.get("net_pct"), "lane": e.get("lane", ""),
                             "placed": tk in open_keys})
    except Exception:
        pass

    # last-3 settled by time (the rolling log), full record kept separately
    recent3 = sorted(settled_rows, key=lambda r: r.get("when", ""), reverse=True)[:3]
    settled_rows.sort(key=lambda r: -r["pnl"])
    open_rows.sort(key=lambda r: -r["cost"])
    return {
        "balance": bal, "open_mv": open_mv, "equity": equity,
        "realized": realized, "total_pnl": equity - FUNDED_BASELINE,
        "wins": int(wins), "losses": int(losses), "winrate": winrate, "roi": roi,
        "open": open_rows, "settled": settled_rows, "recent3": recent3,
        "upcoming": upcoming, "upcoming_ts": fresh, "funded": FUNDED_BASELINE,
    }


def _stat(label, value, sub="", good=None):
    cls = "" if good is None else (" pos" if good else " neg")
    return ('<div class="stat%s"><div class="v">%s</div><div class="l">%s</div>'
            '<div class="s">%s</div></div>') % (cls, value, label, sub)


def _logrow(cls, state, title, meta, right, rcls=""):
    return ("<div class='log %s'><div class='dot'></div>"
            "<div class='lmain'><div class='lt'>%s</div><div class='lm'>%s</div></div>"
            "<div class='lend'><div class='lr %s'>%s</div><div class='ls'>%s</div></div></div>") % (
        cls, title, meta, rcls, right, state)


def render(d):
    up = d["total_pnl"] >= 0
    g = lambda x: ("+$%.2f" % x) if x >= 0 else ("-$%.2f" % abs(x))
    hero = "".join([
        _stat("Account Value", "$%.2f" % d["equity"], "cash $%.2f + bets $%.2f" % (d["balance"], d["open_mv"])),
        _stat("All-Time P&L", g(d["total_pnl"]), "on $%.0f funded" % d["funded"], good=up),
        _stat("Win / Loss", "%d&ndash;%d" % (d["wins"], d["losses"]), "%.0f%% hit rate" % (d["winrate"] * 100), good=d["winrate"] >= 0.5),
        _stat("Return on Risk", "%+.0f%%" % (d["roi"] * 100), "on settled stake", good=d["roi"] >= 0),
    ])

    # COMING UP -- only real, gate-passing edges the engine will place (or just did)
    coming = "".join(
        _logrow("coming", "PLACED" if e["placed"] else "QUEUED",
                "%s &middot; %s" % (e["sport"], e["pick"]),
                "%s &middot; buy %s&cent; &middot; model %s%%" % (
                    e["date"] or "next", e["cents"],
                    ("%.0f" % (e["fair"] * 100)) if e.get("fair") else "?"),
                "+%.0f%% net" % ((e.get("net") or 0) * 100), "pos")
        for e in d["upcoming"][:3]) or "<div class='empty'>No edge clears the bar right now &mdash; the engine sits out until one does. (That is it working.)</div>"

    livenow = "".join(
        _logrow("now", "LIVE",
                "%s &middot; %s" % (r["sport"], r["pick"]),
                "%s &middot; %g @ %.0f&cent; &middot; $%.2f in" % (r["date"] or "today", r["ct"], r["avg"] * 100, r["cost"]),
                ("now %.0f&cent;" % (r["mid"] * 100)) if r["mid"] else "live", "")
        for r in d["open"]) or "<div class='empty'>No bets riding this second.</div>"

    justsettled = "".join(
        _logrow("won" if r["won"] else "lost", "WON" if r["won"] else "LOST",
                "%s &middot; %s" % (r["sport"], r["pick"]),
                "%s &middot; %g @ $%.2f" % (r["date"] or "settled", r["ct"], r["cost"]),
                g(r["pnl"]), "pos" if r["won"] else "neg")
        for r in d["recent3"]) or "<div class='empty'>Nothing settled yet.</div>"

    def srow(r):
        cls = "pos" if r["won"] else "neg"
        return ("<tr><td><span class='tag'>%s</span> %s</td><td>%s</td>"
                "<td>%g</td><td>$%.2f</td><td class='%s'>%s</td><td class='%s'>%s</td></tr>") % (
            r["sport"], r["pick"], r["date"], r["ct"], r["cost"], cls,
            "WON" if r["won"] else "lost", cls, g(r["pnl"]))

    settled_html = "".join(srow(r) for r in d["settled"][:40])
    stamp = datetime.now(PT).strftime("%b %-d, %Y &middot; %-I:%M %p PT")
    return TEMPLATE.format(hero=hero, coming=coming, livenow=livenow,
                           justsettled=justsettled, settled_html=settled_html,
                           stamp=stamp, realized=g(d["realized"]))


TEMPLATE = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta http-equiv=refresh content=90>
<title>Kalshi &middot; Everlight Trading Desk</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;800&family=Inter:wght@400;500;600&display=swap" rel=stylesheet>
<style>
:root{{--gold:#D4AF37;--dark:#0A0A0A;--card:#141414;--line:#262626;--txt:#E8E8E8;--mut:#8a8a8a;--pos:#43d692;--neg:#fb4c2f}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--dark);color:var(--txt);font-family:Inter,system-ui,sans-serif;padding:20px;max-width:920px;margin:0 auto}}
h1{{font-family:'Playfair Display',serif;font-weight:800;font-size:30px;letter-spacing:.3px}}
.wm{{color:var(--gold);font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:2px}}
.sub{{color:var(--mut);font-size:12px;margin-top:4px}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:20px 0}}
@media(min-width:680px){{.grid{{grid-template-columns:repeat(4,1fr)}}}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}}
.stat .v{{font-family:'Playfair Display',serif;font-size:26px;font-weight:700}}
.stat .l{{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-top:6px}}
.stat .s{{color:var(--mut);font-size:11px;margin-top:3px}}
.stat.pos{{border-color:rgba(67,214,146,.35)}} .stat.pos .v{{color:var(--pos)}}
.stat.neg{{border-color:rgba(251,76,47,.35)}} .stat.neg .v{{color:var(--neg)}}
h2{{font-family:'Playfair Display',serif;font-size:17px;margin:24px 0 9px;border-left:3px solid var(--gold);padding-left:10px}}
h2 small{{color:var(--mut);font-family:Inter;font-size:11px;font-weight:400;letter-spacing:.3px}}
.log-wrap{{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
.log{{display:flex;align-items:center;gap:11px;padding:12px 14px;border-bottom:1px solid var(--line)}}
.log:last-child{{border-bottom:none}}
.log .dot{{width:9px;height:9px;border-radius:50%;flex:0 0 auto;background:var(--mut)}}
.log.coming .dot{{background:var(--gold)}}
.log.now .dot{{background:var(--pos);animation:p 1.6s infinite}}
.log.won .dot{{background:var(--pos)}} .log.lost .dot{{background:var(--neg)}}
.lmain{{flex:1;min-width:0}}
.lt{{font-weight:600;font-size:14px}}
.lm{{color:var(--mut);font-size:11px;margin-top:2px}}
.lend{{text-align:right;flex:0 0 auto;padding-left:8px}}
.lr{{font-weight:700;font-size:14px;font-family:'Playfair Display',serif}}
.ls{{font-size:9px;letter-spacing:1.5px;color:var(--mut);text-transform:uppercase;margin-top:3px}}
.empty{{padding:14px;color:var(--mut);font-size:12px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13px}}
th{{text-align:left;color:var(--mut);font-size:10px;text-transform:uppercase;letter-spacing:1px;padding:10px 12px;border-bottom:1px solid var(--line)}}
td{{padding:10px 12px;border-bottom:1px solid var(--line)}}
tr:last-child td{{border-bottom:none}}
.tag{{background:rgba(212,175,55,.14);color:var(--gold);font-size:10px;font-weight:600;padding:2px 7px;border-radius:6px;letter-spacing:.5px}}
.pos{{color:var(--pos);font-weight:600}} .neg{{color:var(--neg);font-weight:600}} .mut{{color:var(--mut)}}
details{{margin-top:10px}} summary{{color:var(--mut);font-size:12px;cursor:pointer;padding:6px 0}}
.foot{{color:var(--mut);font-size:11px;margin-top:24px;text-align:center;line-height:1.7}}
.live{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--pos);margin-right:5px;animation:p 2s infinite}}
@keyframes p{{50%{{opacity:.3}}}}
</style></head><body>
<div class=wm>Everlight Ventures &middot; Trading Desk</div>
<h1>Kalshi Edge Engine</h1>
<div class=sub><span class=live></span>Live &middot; autonomous &middot; updated {stamp}</div>
<div class=grid>{hero}</div>
<h2>Coming Up <small>&mdash; researched, queued, auto-placed by the cron</small></h2>
<div class=log-wrap>{coming}</div>
<h2>Live Now <small>&mdash; riding this second</small></h2>
<div class=log-wrap>{livenow}</div>
<h2>Just Settled <small>&mdash; last 3 &middot; {realized} realized</small></h2>
<div class=log-wrap>{justsettled}</div>
<details><summary>Full record &middot; every settled bet</summary>
<table><tr><th>Market</th><th>Date</th><th>Ct</th><th>Cost</th><th>Result</th><th>P&amp;L</th></tr>{settled_html}</table>
</details>
<div class=foot>Built by the Everlight Kalshi edge engine &middot; refreshes every 90s &middot; the math, not the gut.<br>King of Divine Light &middot; the mind behind the money.</div>
</body></html>"""


def main():
    d = build_ledger()
    html = render(d)
    written = []
    for p in OUT_PATHS:
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            Path(p).write_text(html)
            written.append(p)
        except Exception as e:
            print("skip", p, e)
    print("Dashboard written:", ", ".join(written))
    print("  equity $%.2f | all-time %s | record %d-%d (%.0f%%) | realized $%.2f" % (
        d["equity"], ("+$%.2f" % d["total_pnl"]) if d["total_pnl"] >= 0 else ("-$%.2f" % abs(d["total_pnl"])),
        d["wins"], d["losses"], d["winrate"] * 100, d["realized"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
