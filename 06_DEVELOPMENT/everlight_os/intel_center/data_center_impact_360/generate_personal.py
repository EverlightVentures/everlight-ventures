#!/usr/bin/env python3
"""
Personal AI footprint charts -- one person using AI to run a business, vs
everyday things, vs the aggregate. Honest ranges (water spans ~2 orders of
magnitude by accounting scope). Sources in SOURCES_PERSONAL.md.

Run:  python3 generate_personal.py
Out:  charts/personal_*.png
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GOLD = "#D4A843"; DARK = "#0A0A0A"; PANEL = "#141414"; LIGHT = "#E8E8E8"
MUTED = "#9A9A9A"; RED = "#C0504D"; GREEN = "#6Fae6f"; BLUE = "#5B8DB8"

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"; CHARTS.mkdir(exist_ok=True)
plt.rcParams.update({
    "figure.facecolor": DARK, "axes.facecolor": PANEL, "savefig.facecolor": DARK,
    "text.color": LIGHT, "axes.labelcolor": LIGHT, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": "#333333", "axes.titlecolor": GOLD, "font.family": "DejaVu Sans",
    "axes.titlesize": 13, "axes.titleweight": "bold",
})


def _save(fig, name):
    fig.tight_layout(); p = CHARTS / name
    fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)
    print(f"  ok {name}"); return p


# P1 -- energy: a heavy AI day vs everyday things (kWh/day, log) ---------------
def p1_energy():
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    labels = ["1 phone charge", "100 AI text\nprompts", "YOUR heavy AI\nday (est.)",
              "Driving 1 mile\n(gas car)", "Fridge, 1 day", "Your household,\n1 day"]
    vals = [0.012, 0.03, 0.30, 1.35, 1.5, 29.0]
    colors = [BLUE, BLUE, GOLD, MUTED, MUTED, RED]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.62)
    ax.set_xscale("log")
    ax.set_xlabel("Electricity per day (kWh, log scale)")
    ax.set_title("Your AI energy vs. everyday life: it's a rounding error")
    for b, v in zip(bars, vals[::-1]):
        ax.text(v * 1.15, b.get_y() + b.get_height() / 2, f"{v} kWh", va="center",
                color=LIGHT, fontsize=9, fontweight="bold")
    ax.text(0.5, -0.20, "Your heavy AI day (~0.3 kWh, range 0.1-0.5) is ~1% of your household's "
            "electricity and less than running your fridge for ~5 hours.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "personal_01_energy.png")


# P2 -- water: a heavy AI day vs everyday things (liters/day, log) -------------
def p2_water():
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    labels = ["YOUR AI day\n(low estimate)", "YOUR AI day\n(high estimate)", "1 almond",
              "8-min shower", "Your household\nwater, 1 day", "1 quarter-lb\nburger"]
    vals = [0.026, 2.5, 3.8, 136.0, 1703.0, 1703.0]
    colors = [GOLD, "#C9962F", GREEN, BLUE, BLUE, RED]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.62)
    ax.set_xscale("log")
    ax.set_xlabel("Water per day (liters, log scale)")
    ax.set_title("Your AI water: between a few teaspoons and one almond")
    for b, v in zip(bars, vals[::-1]):
        txt = f"{v} L" if v >= 1 else f"{int(v*1000)} mL"
        ax.text(v * 1.18, b.get_y() + b.get_height() / 2, txt, va="center",
                color=LIGHT, fontsize=9, fontweight="bold")
    ax.text(0.5, -0.20, "Water estimates span ~2 orders of magnitude by accounting scope (on-site "
            "vs. + power-plant). Even the HIGH end is less than growing one almond; a burger is ~700x more.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "personal_02_water.png")


# P3 -- the real story is aggregate scale, not you ----------------------------
def p3_scale():
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    years = ["You, 1 year\nof heavy AI", "All generative AI\n(2025)", "All generative AI\n(2030 proj.)"]
    vals = [0.00011, 15.0, 347.0]  # TWh/year
    colors = [GOLD, BLUE, RED]
    bars = ax.bar(years, vals, color=colors, width=0.55)
    ax.set_yscale("log")
    ax.set_ylabel("Electricity per year (TWh, log scale)")
    ax.set_title("The real story isn't your prompts -- it's the aggregate")
    labels = ["0.0001 TWh\n(~110 kWh)", "15 TWh", "347 TWh"]
    for b, v, t in zip(bars, vals, labels):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.4, t, ha="center",
                color=LIGHT, fontsize=9.5, fontweight="bold")
    ax.text(0.5, -0.22, "700M+ users x explosive growth (~23x by 2030, Schneider Electric) + training "
            "+ speculative overbuild -- THAT is the footprint problem, not one person's use.",
            transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
    return _save(fig, "personal_03_scale.png")


if __name__ == "__main__":
    print("Building personal-footprint charts...")
    p1_energy(); p2_water(); p3_scale()
    print("Done.")
