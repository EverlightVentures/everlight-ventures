#!/usr/bin/env python3
"""
SOLANO COUNTY -- Data Center Impact, made local and relatable.
Builds Solano-specific charts + a self-contained HTML page structured as a
relatability ladder: ONE PERSON -> A FAMILY -> THE CITY -> THE COMMUNITY.

Static artifact, base64-embedded charts, opens in any browser (no server).
Every figure traces to SOURCES_SOLANO.md. Estimates are labeled.

Run:  python3 generate_solano.py
Out:  charts/solano_*.png  +  solano_fairfield_impact.html
"""
from __future__ import annotations
import base64
import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

GOLD = "#D4A843"
DARK = "#0A0A0A"
PANEL = "#141414"
LIGHT = "#E8E8E8"
MUTED = "#9A9A9A"
RED = "#C0504D"
GREEN = "#6Fae6f"
BLUE = "#5B8DB8"
TEAL = "#4FA89B"
PURPLE = "#9A7FBE"

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"
CHARTS.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": DARK, "axes.facecolor": PANEL, "savefig.facecolor": DARK,
    "text.color": LIGHT, "axes.labelcolor": LIGHT, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#333333", "axes.titlecolor": GOLD, "font.family": "DejaVu Sans",
    "axes.titlesize": 13, "axes.titleweight": "bold",
})


def _save(fig, name):
    fig.tight_layout()
    p = CHARTS / name
    fig.savefig(p, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  ok {name}")
    return p


def _commas(x, _p):
    return f"{x:,.0f}"


# S1 -- the relatability ladder (water per day, log scale) --------------------
def s1_ladder():
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    labels = ["One person", "A family (2.86)", "Suisun City\n(~30k people)",
              "Fairfield\n(~124k people)", "Solano County\n(~452k people)"]
    vals = [150, 450, 4_500_000, 18_600_000, 67_800_000]
    colors = [BLUE, TEAL, GOLD, "#C9962F", PURPLE]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.62)
    ax.set_xscale("log")
    ax.set_xlabel("Water used per day (gallons, log scale)")
    ax.set_title("The relatability ladder: who uses how much water in Solano")
    for b, v in zip(bars, vals[::-1]):
        ax.text(v * 1.15, b.get_y() + b.get_height() / 2, f"{v:,}", va="center",
                color=LIGHT, fontsize=9, fontweight="bold")
    ax.axvline(5_000_000, color=RED, lw=2, ls="--")
    ax.text(6_200_000, 3.55, "ONE large data center\n= 5,000,000 gal/day\n(~ all of Suisun City)",
            color=RED, fontsize=8.6, fontweight="bold", ha="left", va="center",
            bbox=dict(facecolor="#1a0a0a", edgecolor=RED, boxstyle="round,pad=0.4"))
    ax.text(0.5, -0.20, "Per-person figure is an estimate (~150 gal/day total residential). "
            "City/county figures scale that by population.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "solano_01_ladder.png")


# S2 -- power: one data center vs every home in the county --------------------
def s2_power():
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    labels = ["EVERY home in\nSolano County\n(~158k households)",
              "ONE large data\ncenter (~300 MW)",
              "California Forever's\nstated plan (2 GW)"]
    vals = [948_000, 2_628_000, 17_520_000]  # MWh/year
    bars = ax.bar(labels, vals, color=[BLUE, RED, "#8a2a28"], width=0.55)
    ax.set_ylabel("Electricity per year (MWh)")
    ax.set_title("Power: one data center can outdraw the whole county's homes")
    ax.yaxis.set_major_formatter(FuncFormatter(_commas))
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 300_000, f"{v/1e6:.1f}M", ha="center",
                color=LIGHT, fontsize=10, fontweight="bold")
    ax.annotate("one center alone =\n~2.8x all county homes", xy=(1, 2_628_000),
                xytext=(0.3, 9_000_000), color=GOLD, fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.text(0.5, -0.22, "MWh/year. Homes est. at ~6 MWh/yr (California average, lower than US). "
            "2 GW = California Forever's own stated power plan for the Solano Foundry.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "solano_02_power.png")


# S3 -- where the local tap water comes from ----------------------------------
def s3_sources():
    fig, ax = plt.subplots(figsize=(6.6, 5))
    sizes = [40, 26, 34]
    labels = ["Lake Berryessa\n(Solano Project /\nPutah Creek) ~40%",
              "State Water Project /\nNorth Bay Aqueduct\n(the Delta) ~26%",
              "Groundwater\n(local wells) ~34%"]
    wedges, _ = ax.pie(sizes, colors=[BLUE, TEAL, GOLD], startangle=90,
                       wedgeprops=dict(width=0.42, edgecolor=DARK, linewidth=2))
    ax.legend(wedges, labels, loc="center", bbox_to_anchor=(0.5, -0.08),
              facecolor=PANEL, edgecolor="#333", labelcolor=LIGHT, fontsize=9)
    ax.set_title("Where your tap water comes from (Vacaville mix shown)")
    ax.text(0, 0, "SOLANO\nWATER", ha="center", va="center", color=GOLD, fontsize=11, fontweight="bold")
    return _save(fig, "solano_03_sources.png")


# S4 -- Solano Project allocations + the data-center wedge ---------------------
def s4_allocations():
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    labels = ["Agriculture\n(Solano ID)", "Maine Prairie\n(ag)", "Vallejo", "Fairfield",
              "Vacaville", "Suisun City"]
    vals = [141_000, 15_000, 14_750, 9_200, 5_600, 1_600]  # acre-feet/year
    colors = [GREEN, GREEN, BLUE, BLUE, RED, BLUE]
    bars = ax.bar(labels, vals, color=colors, width=0.62)
    ax.set_ylabel("Lake Berryessa allocation (acre-feet/year)")
    ax.set_title("Who drinks Lake Berryessa -- and what a data center would take")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2500, f"{v:,}", ha="center",
                color=LIGHT, fontsize=8.5, fontweight="bold")
    ax.axhline(5_601, color=GOLD, lw=2, ls="--")
    ax.text(5.4, 9_000, "ONE large data center\n= ~5,601 AF/yr\n= Vacaville's ENTIRE share",
            color=GOLD, fontsize=8.6, fontweight="bold", ha="right")
    ax.text(0.5, -0.24, "5M gal/day x 365 = 1.83 billion gal/yr = ~5,601 acre-feet -- almost exactly "
            "Vacaville's whole Lake Berryessa allocation (5,600 AF).",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "solano_04_allocations.png")


# S5 -- Lake Berryessa status (full now, thin snowpack) -----------------------
def s5_berryessa():
    fig, ax = plt.subplots(figsize=(8.4, 2.8))
    cats = ["Lake Berryessa\nstorage (May 2026)", "Sierra snowpack\n(the summer buffer)"]
    vals = [98, 59]
    colors = [GREEN, RED]
    bars = ax.barh(cats, vals, color=colors, height=0.5)
    ax.barh(cats, [100 - v for v in vals], left=vals, color="#2a2a2a", height=0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percent of capacity / of average")
    ax.set_title("Your reservoir is full -- but the snowpack that refills it is not")
    for b, v in zip(bars, vals):
        ax.text(v - 3, b.get_y() + b.get_height() / 2, f"{v}%", va="center", ha="right",
                color="#0A0A0A", fontsize=11, fontweight="bold")
    ax.text(0.5, -0.45, "Berryessa ~98% full (USBR, May 2026); Sierra snowpack ~59% of average. "
            "Full reservoir, weak buffer -- supplies swing hard year to year.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "solano_05_berryessa.png")


def b64(p):
    return base64.b64encode(p.read_bytes()).decode("ascii")


def build():
    print("Building Solano charts...")
    s1 = s1_ladder(); s2 = s2_power(); s3 = s3_sources(); s4 = s4_allocations(); s5 = s5_berryessa()
    today = dt.date.today().isoformat()

    def img(p):
        return f'<img src="data:image/png;base64,{b64(p)}" style="width:100%;height:auto;border-radius:8px;display:block;margin:10px 0;"/>'

    species = [
        ("Salt marsh harvest mouse", "Federal + State ENDANGERED", "Lives only in these salt marshes; under 25% of its historic range left."),
        ("Delta smelt", "Federal Threatened / State Endangered", "Functionally collapsed in the wild; survives via captive breeding. Killed by reduced freshwater flow."),
        ("Longfin smelt (Bay-Delta)", "Federal ENDANGERED (listed 2024)", "Under 1% of its 1970s population."),
        ("California Ridgway's rail", "Federal + State ENDANGERED", "Marsh bird of the SF Bay / Suisun complex."),
        ("Suisun song sparrow", "CA Species of Special Concern", "Near-endemic to Suisun Marsh; range-restricted."),
    ]
    sp_cards = "\n".join(
        f'<div class="sp"><b>{n}</b><span class="tag">{s}</span><p>{d}</p></div>' for n, s, d in species
    )

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Data Centers and Solano County -- What It Means Here</title>
<style>
  :root{{--gold:{GOLD};--dark:{DARK};--panel:{PANEL};--light:{LIGHT};--muted:{MUTED};}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--dark);color:var(--light);line-height:1.6;
       font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}}
  header{{padding:32px 20px 22px;border-bottom:2px solid var(--gold);
          background:linear-gradient(180deg,#161616,#0A0A0A);}}
  .wm{{color:var(--gold);letter-spacing:3px;font-size:11px;font-weight:700;}}
  h1{{font-family:Georgia,serif;font-size:27px;margin:8px 0 6px;color:#fff;}}
  .sub{{color:var(--muted);font-size:13.5px;}}
  .wrap{{max-width:920px;margin:0 auto;padding:20px;}}
  .level{{border-radius:12px;padding:18px 18px 8px;margin:22px 0;border:1px solid #2a2a2a;background:var(--panel);}}
  .level .step{{display:inline-block;font-size:11px;font-weight:700;letter-spacing:2px;padding:4px 10px;border-radius:20px;color:#0A0A0A;}}
  .lv1 .step{{background:{BLUE};}} .lv2 .step{{background:{TEAL};}}
  .lv3 .step{{background:{GOLD};}} .lv4 .step{{background:{PURPLE};}}
  .level h2{{font-family:Georgia,serif;font-size:21px;margin:10px 0 4px;color:#fff;}}
  .impact{{background:#1a1408;border-left:3px solid var(--gold);border-radius:6px;
           padding:11px 13px;margin:12px 0;font-size:14px;color:#e8d9a8;}}
  .impact b{{color:var(--gold);}}
  .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:14px 0;}}
  .kpi{{background:#101010;border:1px solid #2a2a2a;border-left:3px solid var(--gold);border-radius:8px;padding:12px;}}
  .kpi b{{display:block;color:var(--gold);font-size:19px;font-family:Georgia,serif;}}
  .kpi span{{color:var(--muted);font-size:11.5px;}}
  .sp{{background:#101010;border:1px solid #2a2a2a;border-radius:8px;padding:11px;margin:8px 0;}}
  .sp b{{color:#fff;}} .sp .tag{{display:inline-block;margin-left:8px;font-size:10.5px;font-weight:700;color:{RED};}}
  .sp p{{margin:5px 0 0;color:var(--muted);font-size:12.5px;}}
  .watch{{background:#241010;border:1px solid #4a2020;border-radius:10px;padding:16px;margin:22px 0;}}
  .watch h2{{color:#e8a8a8;font-family:Georgia,serif;margin-top:0;}}
  footer{{color:var(--muted);font-size:12px;padding:22px;border-top:1px solid #222;text-align:center;}}
  a{{color:var(--gold);}}
</style></head><body>
<header>
  <div class="wm">EVERLIGHT VENTURES &middot; INTEL CENTER &middot; LOCAL DOSSIER</div>
  <h1>Data Centers and Solano County</h1>
  <div class="sub">Fairfield &middot; Vacaville &middot; Suisun City &middot; the whole county.
  What the AI build-out would actually mean HERE, scaled from one person up to the
  whole community. Compiled {today}. Figures sourced in SOURCES_SOLANO.md; estimates labeled.</div>
</header>
<div class="wrap">

  <div class="impact"><b>The bottom line:</b> Solano has NO data center today, and the county
  already restricted big battery-storage projects to industrial zones. You are EARLY, which is
  the strongest position to be in. The one live thread to watch is the
  <b>California Forever / Suisun Expansion</b> plan, which reportedly permits data centers
  "by-right" across ~85% of its 13,410 acres (the developer denies it intends one and promises
  binding power/water caps). See the red box at the bottom.</div>

  <div class="level lv1">
    <span class="step">LEVEL 1 &middot; ONE PERSON</span>
    <h2>You, individually</h2>
    <div class="kpis">
      <div class="kpi"><b>~150 gal</b><span>water you use per day (est.)</span></div>
      <div class="kpi"><b>~6 MWh</b><span>electricity per year (CA home avg)</span></div>
      <div class="kpi"><b>~$54/mo</b><span>Fairfield water bill (+8%/yr through 2030)</span></div>
      <div class="kpi"><b>~32&cent;/kWh</b><span>PG&amp;E power, among the highest in the US</span></div>
    </div>
    <p>Your tap water comes from <b>Lake Berryessa</b> (down the Putah South Canal) and the
    <b>Delta</b> (the North Bay Aqueduct). You do <b>not</b> get to use a data center -- it
    serves remote corporate clients. You would get the side effects, not the service.</p>
    <div class="impact">A single large data center uses as much water in <b>one day</b> as you
    use in about <b>91 years</b>. Its electricity for one year would run your home for
    <b>centuries</b>.</div>
  </div>

  <div class="level lv2">
    <span class="step">LEVEL 2 &middot; A FAMILY</span>
    <h2>Your household (~2.86 people)</h2>
    <div class="kpis">
      <div class="kpi"><b>~450 gal</b><span>water per day, per household</span></div>
      <div class="kpi"><b>8% / 19.3%</b><span>water-rate hikes: Fairfield (yr) / Vacaville (2025)</span></div>
      <div class="kpi"><b>+$24/mo</b><span>new PG&amp;E base charge starting March 2026</span></div>
    </div>
    {img(s1)}
    <div class="impact">One large data center's daily water (<b>5 million gallons</b>) equals the
    daily use of about <b>11,000 Solano families</b>. And when a big new power load lands on the
    grid, the upgrade costs can show up on <b>your family's bill</b>, whether or not you ever
    touch the service.</div>
  </div>

  <div class="level lv3">
    <span class="step">LEVEL 3 &middot; THE CITY</span>
    <h2>Fairfield, Vacaville, Suisun City</h2>
    {img(s4)}
    <div class="impact">A single 5-million-gallon-a-day data center would draw about
    <b>5,601 acre-feet a year -- almost exactly Vacaville's ENTIRE Lake Berryessa allocation</b>
    (5,600 AF). Put another way, it would drink roughly as much water in a day as the whole
    <b>city of Suisun City</b> (~30,000 people).</div>
    {img(s2)}
    <div class="impact">On power, one hyperscale center (~300 MW) could use <b>more electricity
    than every home in Solano County combined -- about 2 to 3 times over</b>. California Forever's
    own stated plan calls for <b>2 gigawatts</b>, roughly the power of ~2.9 million homes.</div>
    <div class="kpis">
      <div class="kpi"><b>32 MGD</b><span>Fairfield's peak water capacity (a center = ~16% of it)</span></div>
      <div class="kpi"><b>~13%</b><span>of Fairfield's total water supply, for one center</span></div>
    </div>
  </div>

  <div class="level lv4">
    <span class="step">LEVEL 4 &middot; THE COMMUNITY</span>
    <h2>The county, the marsh, the farms, the air</h2>
    {img(s3)}
    <p><b>The water is already spoken for.</b> Lake Berryessa supplies the cities AND the
    minimum flows that keep Putah Creek's restored wild salmon run alive (a real comeback,
    confirmed by UC Davis in 2025). The Delta water feeds the cities AND the Suisun Marsh. Any
    big new industrial draw competes with all of it at once.</p>
    {img(s5)}
    <p><b>Suisun Marsh</b> is the largest contiguous brackish marsh on the West Coast (~116,000
    acres, in Fairfield's and Suisun City's backyard). It is already stressed: in 2021 upstream
    users consumed ~84% of the watershed's runoff. A data center's consumptive water use tightens
    the freshwater flow these species depend on:</p>
    {sp_cards}
    <div class="kpis">
      <div class="kpi"><b>$438M</b><span>Solano County farm output (2024) competing for the same water</span></div>
      <div class="kpi"><b>~520 MW</b><span>Solano wind power EXPORTED today (Montezuma Hills)</span></div>
      <div class="kpi"><b>Ozone</b><span>Fairfield/Suisun already in nonattainment; PM2.5 next</span></div>
    </div>
    <div class="impact"><b>Two compounding harms at the community level:</b> (1) Solano currently
    EXPORTS clean wind power to the Bay Area -- one data center would flip it into a net power
    sink, and a flat 24/7 load pulls in gas turbines/batteries. (2) Fairfield and Suisun are
    already in ozone nonattainment and headed for PM2.5 nonattainment; backup-generator exhaust
    would add NOx and PM2.5 to an airshed that is already over the line -- worst in summer, exactly
    when heat, wildfire risk, and water stress all peak together.</div>
  </div>

  <div class="watch">
    <h2>THE ONE THING TO WATCH</h2>
    <p><b>California Forever / Suisun Expansion.</b> The formal application was filed Oct 14, 2025.
    Rio Vista's city manager alleges the Specific Plan allows data centers by-right across ~85.2%
    of the 13,410-acre area; the developer calls that "inaccurate" and says binding power and water
    caps will make it "fundamentally incompatible" with data centers. Suisun City conceded data
    centers ARE listed in the zoning ("zoning is broad intentionally").</p>
    <p><b>The marketing does not decide this -- the documents do.</b> Watch whether those binding
    power/water limits actually get written into the EIR and Development Agreement, which go before
    the Suisun City Planning Commission later in 2026. That is the public-comment pressure point.
    Solano County also runs the Travis AFB land-use overlay and LAFCO annexation review -- more
    leverage points.</p>
    <p><b>Your move:</b> show up to Suisun City Planning Commission + Solano County Water Agency
    meetings, and push for the binding caps + cost-causation (the developer pays for its own
    grid/water) + recycled-water requirements to be in writing BEFORE anything is approved.</p>
  </div>

</div>
<footer>EVERLIGHT VENTURES -- Intel Center &middot; Local decision-support, not legal/financial advice.<br/>
Figures in SOURCES_SOLANO.md. Data-center impacts here are projected mechanisms applied to the
documented local baseline -- there is no operating data center in Solano today.</footer>
</body></html>"""
    out = HERE / "solano_fairfield_impact.html"
    out.write_text(html, encoding="utf-8")
    print(f"  ok {out.name}  ({out.stat().st_size//1024} KB)")
    return out


if __name__ == "__main__":
    build()
    print("Done.")
