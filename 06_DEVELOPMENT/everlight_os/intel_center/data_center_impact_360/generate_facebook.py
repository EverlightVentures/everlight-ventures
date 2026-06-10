#!/usr/bin/env python3
"""
Facebook share assets for the Solano data-center briefing.
Builds a portrait infographic (1080x1500) optimized for mobile FB feed,
plus the existing charts are available as a carousel.

Run:  python3 generate_facebook.py
Out:  facebook/solano_share.png
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

GOLD = "#D4A843"
DARK = "#0A0A0A"
PANEL = "#161616"
LIGHT = "#E8E8E8"
MUTED = "#9A9A9A"
RED = "#C0504D"
GREEN = "#6Fae6f"

HERE = Path(__file__).resolve().parent
FB = HERE / "facebook"
FB.mkdir(exist_ok=True)


def infographic():
    # 1080x1500 px at 100 dpi = 10.8 x 15.0 inches
    fig = plt.figure(figsize=(10.8, 15.0), facecolor=DARK)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, fc, ec=None, lw=0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                     facecolor=fc, edgecolor=ec or fc, linewidth=lw, mutation_aspect=1))

    # header band
    box(0, 90.5, 100, 9.5, "#161616")
    ax.plot([4, 96], [90.3, 90.3], color=GOLD, lw=2)
    ax.text(6, 96.6, "EVERLIGHT VENTURES  ·  LOCAL INTEL", color=GOLD, fontsize=13,
            fontweight="bold", family="DejaVu Sans")
    ax.text(6, 92.4, "What a data center would mean for", color=LIGHT, fontsize=20,
            family="DejaVu Serif")
    ax.text(6, 90.9, "SOLANO COUNTY", color="#fff", fontsize=33, fontweight="bold",
            family="DejaVu Serif")

    # subhead
    ax.text(50, 87.8, "Fairfield  ·  Vacaville  ·  Suisun City", color=MUTED, fontsize=15,
            ha="center")

    # big stat cards
    def stat(y, big, small, color=GOLD):
        box(5, y, 90, 8.2, PANEL, ec="#2a2a2a", lw=1)
        ax.plot([6.5, 6.5], [y + 0.8, y + 7.4], color=color, lw=4)
        ax.text(9, y + 5.0, big, color=color, fontsize=23, fontweight="bold", va="center")
        ax.text(9, y + 2.0, small, color=LIGHT, fontsize=13.5, va="center")

    stat(77.5, "1 data center = 5,601 acre-ft / year",
         "Almost exactly VACAVILLE'S ENTIRE Lake Berryessa allocation.")
    stat(68.3, "= a whole CITY of water, every day",
         "5 million gallons/day -- about all of Suisun City (~30,000 people).", color="#C9962F")
    stat(59.1, "> EVERY home in the county, on power",
         "One ~300 MW center can outdraw all Solano homes 2-3x over.", color=RED)
    stat(49.9, "We EXPORT clean power today",
         "~520 MW of Solano wind. A data center flips us to a power sink.", color=GREEN)

    # the local environment line
    box(5, 38.5, 90, 9.6, "#14100a", ec="#3a2f10", lw=1)
    ax.text(50, 46.3, "AND THE WATER IS ALREADY SPOKEN FOR", color=GOLD, fontsize=15,
            fontweight="bold", ha="center")
    ax.text(50, 43.4, "The same Lake Berryessa feeds our cities, our $438M of farms,",
            color=LIGHT, fontsize=12.8, ha="center")
    ax.text(50, 41.6, "and the flows keeping Putah Creek's wild salmon alive.", color=LIGHT,
            fontsize=12.8, ha="center")
    ax.text(50, 39.6, "Suisun Marsh -- 5 endangered species -- needs that freshwater too.",
            color=MUTED, fontsize=12, ha="center")

    # the watch box
    box(5, 24.5, 90, 12.5, "#1a0d0d", ec="#4a2020", lw=1.5)
    ax.text(50, 34.6, "THE ONE THING TO WATCH", color="#e8a8a8", fontsize=16,
            fontweight="bold", ha="center")
    ax.text(50, 31.8, "California Forever's Suisun Expansion reportedly allows", color=LIGHT,
            fontsize=13, ha="center")
    ax.text(50, 30.0, "data centers across ~85% of its 13,410 acres.", color=LIGHT,
            fontsize=13, ha="center")
    ax.text(50, 27.7, "The developer denies it and promises binding water/power caps.", color=MUTED,
            fontsize=11.8, ha="center")
    ax.text(50, 25.9, "The EIR + Development Agreement decide -- not the marketing.", color=GOLD,
            fontsize=12.5, fontweight="bold", ha="center")

    # CTA
    box(5, 12.5, 90, 10.5, PANEL, ec=GOLD, lw=1.5)
    ax.text(50, 20.6, "WE ARE EARLY -- THAT IS OUR LEVERAGE", color=GOLD, fontsize=16,
            fontweight="bold", ha="center")
    ax.text(50, 17.7, "Show up to the Suisun City Planning Commission +", color=LIGHT,
            fontsize=13, ha="center")
    ax.text(50, 15.9, "Solano County Water Agency meetings.", color=LIGHT, fontsize=13, ha="center")
    ax.text(50, 13.9, "Demand the water + power caps be in writing BEFORE any approval.",
            color=MUTED, fontsize=11.8, ha="center")

    # footer
    ax.text(50, 8.0, "Sources: USBR, SCWA, CalMatters, Press Democrat, UC Davis, USFWS, LBNL.",
            color=MUTED, fontsize=9.5, ha="center")
    ax.text(50, 6.2, "No data center exists in Solano today. These are projected impacts on a",
            color=MUTED, fontsize=9.5, ha="center")
    ax.text(50, 4.8, "documented local baseline. Decision-support, not legal/financial advice.",
            color=MUTED, fontsize=9.5, ha="center")
    ax.text(50, 2.2, "E V E R L I G H T   V E N T U R E S", color=GOLD, fontsize=12,
            fontweight="bold", ha="center")

    out = FB / "solano_share.png"
    fig.savefig(out, dpi=100, facecolor=DARK)
    plt.close(fig)
    print(f"  ok {out.relative_to(HERE)}  ({out.stat().st_size//1024} KB)")
    return out


if __name__ == "__main__":
    print("Building Facebook infographic...")
    infographic()
    print("Done.")
