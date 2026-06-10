#!/usr/bin/env python3
"""
Data Center Impact 360 -- analytics + environmental graphs generator.

Builds the chart set and a self-contained HTML dashboard (charts embedded as
base64 so the file opens anywhere, including the phone, with no broken images).

Every number here traces to a cited source in SOURCES.md. Where a figure is a
projection, a range, or methodology-dependent, the caption says so -- we do not
launder forecasts as facts.

Run:  python3 generate_assets.py
Out:  charts/*.png  +  data_center_360_dashboard.html
"""
from __future__ import annotations
import base64
import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless / phone-safe
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ---- Everlight brand palette (single source of truth: report_template.py) ----
GOLD = "#D4A843"
DARK = "#0A0A0A"
PANEL = "#141414"
LIGHT = "#E8E8E8"
MUTED = "#9A9A9A"
RED = "#C0504D"      # cost / harm
GREEN = "#6Fae6f"    # benefit / clean
BLUE = "#5B8DB8"     # neutral data
PURPLE = "#9A7FBE"   # intel

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": DARK,
    "axes.facecolor": PANEL,
    "savefig.facecolor": DARK,
    "text.color": LIGHT,
    "axes.labelcolor": LIGHT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": "#333333",
    "axes.titlecolor": GOLD,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.titleweight": "bold",
})


def _save(fig, name: str):
    path = CHARTS / name
    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def _thousands(x, _pos):
    return f"{x:,.0f}"


# 1 ---------------------------------------------------------------------------
def chart_water_vs_people():
    """One large data center's daily water vs. one person's. Log scale."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = ["One person\n(home use/day)", "One large/hyperscale\ndata center (peak/day)"]
    vals = [100, 5_000_000]  # gal/day
    bars = ax.bar(labels, vals, color=[BLUE, GOLD], width=0.55)
    ax.set_yscale("log")
    ax.set_ylabel("Gallons of water per day (log scale)")
    ax.set_title("A single big data center drinks like a town of ~50,000 people")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.3, f"{v:,} gal", ha="center",
                color=LIGHT, fontsize=10, fontweight="bold")
    ax.annotate("approx 50,000x\na person", xy=(1, 5_000_000), xytext=(0.45, 400_000),
                color=GOLD, fontsize=11, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.text(0.5, -0.30, "Peak figure for a very large facility on a hot day; not a fleet average. "
            "Average U.S. home use is 82-100 gal/person/day.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "01_water_vs_people.png")


# 2 ---------------------------------------------------------------------------
def chart_wue():
    """Water Usage Effectiveness: lower = better. The 'rogue vs good citizen' metric."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = ["Legacy industry\navg (evaporative)", "Google\n(on-site, ~2023)",
              "Microsoft\nFY25", "AWS\n(air-cool mix)", "Air-cooled /\nzero-water design"]
    vals = [1.85, 1.10, 0.27, 0.18, 0.02]
    colors = [RED, GOLD, GREEN, GREEN, GREEN]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.6)
    ax.set_xlabel("Water Usage Effectiveness -- liters of water per kWh (lower is better)")
    ax.set_title("WUE: the one number that separates 'rogue' from 'good-citizen'")
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.03, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center",
                color=LIGHT, fontsize=10, fontweight="bold")
    ax.text(0.5, -0.22, "Hyperscalers' own reports now run far below the legacy ~1.8 average -- "
            "design choice, not magic. Closed-loop and air cooling trade water for more electricity.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "02_wue_comparison.png")


# 3 ---------------------------------------------------------------------------
def chart_us_demand():
    """US data-center electricity demand growth (LBNL 2024)."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    years = [2014, 2023, 2028]
    ax.plot(years[:2], [58, 176], "-o", color=GOLD, lw=2.5, label="Actual (LBNL)")
    ax.plot([2023, 2028], [176, 325], "--o", color=GREEN, lw=2, label="2028 low scenario")
    ax.plot([2023, 2028], [176, 580], "--o", color=RED, lw=2, label="2028 high scenario")
    ax.fill_between([2023, 2028], [176, 325], [176, 580], color=GOLD, alpha=0.12)
    ax.set_ylabel("Terawatt-hours / year")
    ax.set_title("U.S. data-center electricity use is set to double -- or worse -- by 2028")
    for x, y in [(2014, 58), (2023, 176)]:
        ax.text(x, y + 18, f"{y} TWh", color=LIGHT, fontsize=9, fontweight="bold", ha="center")
    ax.text(2028, 325 - 35, "325 TWh\n(6.7% of US)", color=GREEN, fontsize=9, ha="center")
    ax.text(2028, 580 + 8, "580 TWh\n(up to 12% of US)", color=RED, fontsize=9, ha="center")
    ax.text(2014, 58 - 30, "1.9% of US grid", color=MUTED, fontsize=8, ha="center")
    ax.text(2023, 176 + 40, "4.4% of US grid", color=MUTED, fontsize=8, ha="center")
    ax.set_xticks(years)
    ax.legend(facecolor=PANEL, edgecolor="#333", labelcolor=LIGHT, fontsize=8, loc="upper left")
    ax.margins(x=0.08, y=0.18)
    return _save(fig, "03_us_electricity_demand.png")


# 4 ---------------------------------------------------------------------------
def chart_water_fate():
    """Where the withdrawn water goes (evaporative-tower design)."""
    fig, ax = plt.subplots(figsize=(6.4, 5))
    sizes = [82, 18]
    labels = ["~80-85% EVAPORATES\n(gone to the sky,\nnot returned to supply)",
              "~15-20% DISCHARGED\n(warm 'blowdown' --\ntreated, salty, chemical)"]
    colors = [RED, BLUE]
    wedges, _ = ax.pie(sizes, colors=colors, startangle=90,
                       wedgeprops=dict(width=0.42, edgecolor=DARK, linewidth=2))
    ax.legend(wedges, labels, loc="center", bbox_to_anchor=(0.5, -0.08),
              facecolor=PANEL, edgecolor="#333", labelcolor=LIGHT, fontsize=9, ncol=1)
    ax.set_title("What happens to a data center's cooling water")
    ax.text(0, 0, "EVAPORATIVE\nCOOLING", ha="center", va="center", color=GOLD,
            fontsize=11, fontweight="bold")
    return _save(fig, "04_water_fate.png")


# 5 ---------------------------------------------------------------------------
def chart_texas_water():
    """Texas data-center water projection (HARC)."""
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    years = ["2024\n(actual)", "2025\n(est.)", "2030\n(projected)"]
    vals = [50, 49, 399]
    bars = ax.bar(years, vals, color=[BLUE, GOLD, RED], width=0.55)
    ax.set_ylabel("Billion gallons / year")
    ax.set_title("Texas data-center water use: a ~8x jump by 2030 (HARC projection)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 6, f"{v}B", ha="center",
                color=LIGHT, fontsize=11, fontweight="bold")
    ax.annotate("approx 6.6% of ALL Texas water\napprox Lake Mead down 16 ft/yr",
                xy=(2, 399), xytext=(0.55, 300), color=GOLD, fontsize=9.5, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.text(0.5, -0.24, "Projection by the Houston Advanced Research Center, during ongoing drought. "
            "No Texas law currently caps data-center water use.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "05_texas_water_projection.png")


# 6 ---------------------------------------------------------------------------
def chart_bill_impact():
    """Monthly residential bill increases tied to data-center capacity costs."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = ["Washington DC\n(Pepco)", "Western\nMaryland", "Ohio", "Virginia\n(proj. by 2040)"]
    lows = [21, 18, 16, 14]
    highs = [21, 18, 16, 37]
    x = range(len(labels))
    ax.bar(x, lows, color=GOLD, width=0.5, label="Now / low")
    ax.bar(x, [h - l for h, l in zip(highs, lows)], bottom=lows, color=RED, width=0.5,
           label="VA upper range (2040)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Added residential bill ($/month)")
    ax.set_title("What data-center power demand adds to YOUR monthly bill")
    for i, (l, h) in enumerate(zip(lows, highs)):
        txt = f"+${l}" if l == h else f"+${l}-${h}"
        ax.text(i, h + 0.8, txt, ha="center", color=LIGHT, fontsize=10, fontweight="bold")
    ax.legend(facecolor=PANEL, edgecolor="#333", labelcolor=LIGHT, fontsize=8, loc="upper left")
    ax.text(0.5, -0.24, "DC/MD/OH are realized 2025-26 increases from PJM capacity prices "
            "(data centers = 63% / ~$9.3B of the increase). Virginia is the JLARC 2040 projection.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "06_household_bill_impact.png")


# 7 ---------------------------------------------------------------------------
def chart_states():
    """Data centers by state (top 3 + rest of US)."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = ["Virginia", "Texas", "California", "Rest of U.S."]
    vals = [665, 413, 321, 3601]
    colors = [GOLD, "#C9962F", BLUE, "#3A3A3A"]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.6)
    ax.set_xlabel("Number of data centers")
    ax.set_title("Where they are: ~5,000 U.S. data centers, heavily clustered")
    ax.xaxis.set_major_formatter(FuncFormatter(_thousands))
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 40, b.get_y() + b.get_height() / 2, f"{v:,}", va="center",
                color=LIGHT, fontsize=10, fontweight="bold")
    ax.text(0.5, -0.24, "Virginia's Loudoun County ('Data Center Alley') is the densest cluster on Earth. "
            "Counts vary by source/definition (~4,300-5,400 total).",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "07_states_data_centers.png")


# 8 ---------------------------------------------------------------------------
def chart_jobs():
    """Construction vs permanent jobs per 100 MW."""
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    labels = ["Construction jobs\n(TEMPORARY)", "Permanent jobs\n(after build)"]
    vals = [135, 25]
    bars = ax.bar(labels, vals, color=[BLUE, RED], width=0.5)
    ax.set_ylabel("Workers per 100 MW of capacity")
    ax.set_title("The jobs promise vs. reality: temporary boom, skeleton crew after")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center",
                color=LIGHT, fontsize=12, fontweight="bold")
    ax.text(0.5, -0.22, "Large hyperscale campuses often run on 20-50 permanent staff; "
            "most facilities employ fewer than ~150. Construction jobs vanish at ribbon-cutting.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "08_jobs_reality.png")


# 9 ---------------------------------------------------------------------------
def chart_water_price():
    """Mesa AZ: Google pays less per gallon than residents."""
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels = ["Google\n(data center)", "Local residents\n(households)"]
    vals = [6.08, 10.80]
    bars = ax.bar(labels, vals, color=[RED, GOLD], width=0.5)
    ax.set_ylabel("Price per 1,000 gallons ($)")
    ax.set_title("Mesa, Arizona: the biggest water user pays the LOWEST rate")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.2, f"${v:.2f}", ha="center",
                color=LIGHT, fontsize=12, fontweight="bold")
    ax.annotate("residents pay ~44% MORE\nper gallon than the data center",
                xy=(1, 10.8), xytext=(0.15, 8.6), color=GOLD, fontsize=9.5, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.text(0.5, -0.22, "Municipal water is priced on average cost + volume discounts -- not scarcity. "
            "The largest, most price-insensitive user gets the cheapest rate, in a desert.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "09_water_price_disparity.png")


# 10 --------------------------------------------------------------------------
def chart_resource_parity():
    """The user's thesis chart: one data center = how many humans' worth of resources."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = ["WATER\n(vs 1 person/day)", "ELECTRICITY\n(vs 1 person, via homes)"]
    vals = [50_000, 250_000]
    bars = ax.bar(labels, vals, color=[BLUE, GOLD], width=0.5)
    ax.set_ylabel("Equivalent number of humans")
    ax.set_title("The parity question: one hyperscale center = a small CITY of people", pad=14)
    ax.set_ylim(0, 300_000)
    ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 6000, f"{v:,}\npeople", ha="center",
                color=LIGHT, fontsize=11, fontweight="bold")
    ax.text(0.5, -0.22, "Water: 5M gal/day / 100 gal per person = approx 50,000. Power: ~100,000 homes x ~2.5 "
            "people/home = approx 250,000. The machine's footprint already dwarfs the individual's.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "10_resource_parity.png")


CHART_BUILDERS = [
    ("01_water_vs_people.png", chart_water_vs_people,
     "One large data center can use as much water in a day as a town of ~50,000 people."),
    ("02_wue_comparison.png", chart_wue,
     "Water Usage Effectiveness (WUE) is the accountability metric. Good operators run 10-90x lower than legacy."),
    ("03_us_electricity_demand.png", chart_us_demand,
     "U.S. data-center power use: 58 to 176 TWh (2014-2023), heading to 325-580 TWh by 2028 (LBNL)."),
    ("04_water_fate.png", chart_water_fate,
     "In evaporative cooling, ~80-85% of withdrawn water evaporates and never returns to the supply."),
    ("05_texas_water_projection.png", chart_texas_water,
     "Texas data-center water use is projected to jump ~8x to 399 billion gallons by 2030."),
    ("06_household_bill_impact.png", chart_bill_impact,
     "Real, realized monthly bill increases on households -- driven by data-center capacity demand."),
    ("07_states_data_centers.png", chart_states,
     "~5,000 U.S. data centers, clustered hard in Virginia, Texas, and California."),
    ("08_jobs_reality.png", chart_jobs,
     "Construction jobs are temporary; permanent staffing is tiny. The jobs promise rarely lands."),
    ("09_water_price_disparity.png", chart_water_price,
     "In Mesa AZ, Google pays ~44% LESS per gallon than residents -- water priced on volume, not scarcity."),
    ("10_resource_parity.png", chart_resource_parity,
     "The parity thesis: one hyperscale center already consumes the resources of a small CITY of people."),
]


def build_all_charts():
    out = []
    for _, fn, caption in CHART_BUILDERS:
        path = fn()
        out.append((path, caption))
        print(f"  ok {path.name}")
    return out


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_dashboard(chart_results):
    today = dt.date.today().isoformat()
    cards = []
    for (path, caption) in chart_results:
        cards.append(f"""
      <figure class="card">
        <img src="data:image/png;base64,{b64(path)}" alt="{caption}"/>
        <figcaption>{caption}</figcaption>
      </figure>""")
    cards_html = "\n".join(cards)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Data Center Impact 360 -- Everlight Intel</title>
<style>
  :root {{ --gold:{GOLD}; --dark:{DARK}; --panel:{PANEL}; --light:{LIGHT}; --muted:{MUTED}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--dark); color:var(--light);
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; line-height:1.55; }}
  header {{ padding:34px 22px 22px; border-bottom:2px solid var(--gold);
            background:linear-gradient(180deg,#161616,#0A0A0A); }}
  .wordmark {{ color:var(--gold); letter-spacing:3px; font-size:12px; font-weight:700; }}
  h1 {{ font-family:Georgia,'Times New Roman',serif; font-size:30px; margin:8px 0 6px; color:#fff; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:22px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:18px 0 6px; }}
  .kpi {{ background:var(--panel); border:1px solid #2a2a2a; border-left:3px solid var(--gold);
          border-radius:8px; padding:14px; }}
  .kpi b {{ display:block; color:var(--gold); font-size:22px; font-family:Georgia,serif; }}
  .kpi span {{ color:var(--muted); font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:18px; margin-top:10px; }}
  .card {{ background:var(--panel); border:1px solid #2a2a2a; border-radius:10px; padding:12px; margin:0; }}
  .card img {{ width:100%; height:auto; border-radius:6px; display:block; }}
  .card figcaption {{ color:var(--muted); font-size:12.5px; margin-top:8px; }}
  h2 {{ font-family:Georgia,serif; color:var(--gold); border-bottom:1px solid #2a2a2a; padding-bottom:6px; margin-top:34px; }}
  .note {{ background:#1a1408; border:1px solid #3a2f10; border-radius:8px; padding:12px 14px; font-size:13px; color:#e8d9a8; }}
  footer {{ color:var(--muted); font-size:12px; padding:24px 22px; border-top:1px solid #222; text-align:center; }}
  a {{ color:var(--gold); }}
</style></head>
<body>
<header>
  <div class="wordmark">EVERLIGHT VENTURES &middot; INTEL CENTER</div>
  <h1>Data Center Impact 360</h1>
  <div class="sub">The water, power, money, and health story behind the AI build-out -- verified, cited, and made local.<br/>
  Compiled {today} &middot; 6-agent Hive fan-out + cross-check &middot; figures sourced in SOURCES.md</div>
</header>
<div class="wrap">

  <div class="kpis">
    <div class="kpi"><b>5M</b><span>gallons/day -- a big data center, approx a town of 50,000 people</span></div>
    <div class="kpi"><b>~80%</b><span>of cooling water evaporates -- gone, not recycled</span></div>
    <div class="kpi"><b>176 to 580</b><span>TWh -- U.S. data-center power, 2023 to 2028 high case</span></div>
    <div class="kpi"><b>$9.3B</b><span>data-center share of one PJM grid-cost cycle, paid by ratepayers</span></div>
    <div class="kpi"><b>&lt;150</b><span>permanent jobs at most large centers (often 20-50)</span></div>
    <div class="kpi"><b>$725B</b><span>Big Tech's planned 2026 AI build spend</span></div>
  </div>

  <div class="note"><b>Read me first.</b> Three widely-shared "facts" did <b>not</b> survive sourcing and are corrected here:
  the diesel "200-600x NOx" claim (real approx 6-20x), the "$5.4B health cost" (the study says ~$20B/yr and ~1,300 deaths/yr by 2030),
  and the "80% NO2 rise in Boxtown" (it was +79% at the fence-line, +9% in Boxtown, with a competing study finding little change).
  Projections are labeled as projections.</div>

  <h2>The Environmental Graphs</h2>
  <div class="grid">
  {cards_html}
  </div>

  <h2>How to read this</h2>
  <p>Energy is the <b>uniform national</b> strain -- measured, monitor-attributed, already on bills.
  Water is the <b>sharper local</b> strain -- driven by cooling type and whether the source is a stressed
  aquifer or drought basin, and largely <b>invisible</b> because there's no market price and weak disclosure.
  The benefits flow to a handful of corporate balance sheets; many of the costs are socialized onto ratepayers,
  taxpayers, and the air and water of the host community. That asymmetry -- privatized gains, socialized inputs --
  is the moral of the story.</p>

</div>
<footer>
  EVERLIGHT VENTURES -- Intel Center &middot; This dashboard is decision-support, not legal/financial advice.<br/>
  Every figure is traceable in <code>SOURCES.md</code>. Contested or projected numbers are flagged in the reports.
</footer>
</body></html>"""
    out = HERE / "data_center_360_dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"  ok {out.name}  ({out.stat().st_size//1024} KB)")
    return out


if __name__ == "__main__":
    print("Building charts...")
    results = build_all_charts()
    print("Building dashboard...")
    build_dashboard(results)
    print("Done.")
