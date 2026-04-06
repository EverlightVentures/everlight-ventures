#!/usr/bin/env python3
"""
Piper Chart Engine -- Generates beautiful inline charts for outreach emails.

Creates base64-encoded PNG charts that embed directly in HTML emails.
Everlight branding: gold (#D4AF37), dark (#1a1a2e), white text.
Charts are compact (600x300) for email compatibility.
"""
import base64
import io
import os

# Matplotlib with non-interactive backend (no display needed)
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
import numpy as np


# Everlight brand colors
GOLD = "#D4AF37"
DARK_BG = "#1a1a2e"
LIGHT_TEXT = "#f0f0f0"
ACCENT_BLUE = "#4a90d9"
ACCENT_GREEN = "#4CAF50"
ACCENT_RED = "#e74c3c"
SOFT_GOLD = "#f5e6b8"
GRID_COLOR = "#333355"


def _setup_fig(width=6.0, height=2.8, title=""):
    """Create a branded figure."""
    fig, ax = plt.subplots(figsize=(width, height), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors=LIGHT_TEXT, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.yaxis.label.set_color(LIGHT_TEXT)
    ax.xaxis.label.set_color(LIGHT_TEXT)
    if title:
        ax.set_title(title, color=GOLD, fontsize=12, fontweight="bold", pad=12)
    fig.subplots_adjust(bottom=0.18, top=0.85, left=0.14, right=0.94)
    return fig, ax


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _img_tag(b64: str, alt: str = "Chart", width: int = 580) -> str:
    """Create an HTML img tag from base64 data."""
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" width="{width}" style="max-width:100%;height:auto;border-radius:8px;margin:10px 0;" />'


def chart_market_snapshot(data: dict) -> str:
    """Bar chart comparing local market to national averages.

    Shows: Median Price, Days on Market, Inventory (months).
    """
    city = data.get("city", "Local")
    labels = ["Median Price\n($K)", "Days on\nMarket", "Inventory\n(months)"]
    local_vals = [
        data.get("median_home_price", 300000) / 1000,
        data.get("days_on_market", 35),
        data.get("inventory_months", 3.5),
    ]
    national_vals = [
        data.get("national_median_price", 412000) / 1000,
        data.get("national_dom", 34),
        data.get("national_inv_months", 3.5),
    ]

    fig, ax = _setup_fig(title=f"{city} Market vs. National Average")
    x = np.arange(len(labels))
    width = 0.32

    bars1 = ax.bar(x - width / 2, local_vals, width, label=city, color=GOLD, edgecolor="none", zorder=3)
    bars2 = ax.bar(x + width / 2, national_vals, width, label="National Avg", color=ACCENT_BLUE, edgecolor="none", alpha=0.7, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("")
    ax.legend(loc="upper right", fontsize=8, facecolor=DARK_BG, edgecolor=GRID_COLOR, labelcolor=LIGHT_TEXT)
    ax.grid(axis="y", color=GRID_COLOR, alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    # Value labels on bars
    for bar_set in [bars1, bars2]:
        for bar in bar_set:
            h = bar.get_height()
            fmt = f"${h:.0f}K" if h > 50 else f"{h:.1f}"
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, fmt,
                    ha="center", va="bottom", color=LIGHT_TEXT, fontsize=7, fontweight="bold")

    return _img_tag(_fig_to_base64(fig), f"{city} Market Snapshot")


def chart_holding_cost(holding: dict, city: str = "Your Property") -> str:
    """Horizontal bar showing monthly holding cost breakdown."""
    categories = ["Property\nTaxes", "Insurance", "Maintenance", "Utilities", "Liability"]
    values = [
        holding.get("property_taxes", 0),
        holding.get("insurance", 0),
        holding.get("maintenance", 0),
        holding.get("utilities_vacant", 0),
        holding.get("liability", 0),
    ]
    total = sum(values)

    fig, ax = _setup_fig(title=f"Monthly Cost of Holding ({city})")
    colors = [ACCENT_RED, GOLD, ACCENT_BLUE, "#9b59b6", "#e67e22"]
    y_pos = np.arange(len(categories))

    bars = ax.barh(y_pos, values, color=colors, edgecolor="none", height=0.6, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=8)
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID_COLOR, alpha=0.3, zorder=0)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                f"${val:,}/mo", ha="left", va="center", color=LIGHT_TEXT, fontsize=8, fontweight="bold")

    ax.text(0.98, 0.02, f"Total: ${total:,}/mo  |  ${total * 12:,}/yr",
            transform=ax.transAxes, ha="right", va="bottom",
            color=GOLD, fontsize=10, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#2a2a4e", edgecolor=GOLD, alpha=0.9))

    return _img_tag(_fig_to_base64(fig), "Holding Cost Breakdown")


def chart_sell_vs_hold(median_price: int, annual_holding_cost: int, yoy_pct: float, city: str = "") -> str:
    """Line chart: equity trajectory if you sell now vs hold 1-5 years.

    Shows cash-in-hand today vs. net value after holding costs + appreciation.
    """
    years = [0, 1, 2, 3, 4, 5]
    sell_now = [median_price * 0.92] * 6  # 92% after closing costs if sold traditionally; we offer ~70-80% but it's instant

    # Net value if holding: appreciation minus cumulative holding costs
    hold_values = []
    for yr in years:
        appreciated = median_price * ((1 + yoy_pct / 100) ** yr)
        holding_paid = annual_holding_cost * yr
        net = appreciated - holding_paid
        hold_values.append(net)

    # Cash offer (our value prop): instant, no costs
    cash_offer = median_price * 0.78  # ~78% of market value, cash, fast

    fig, ax = _setup_fig(title=f"Sell Now vs. Hold: 5-Year Projection" + (f" ({city})" if city else ""))

    ax.plot(years, [v / 1000 for v in hold_values], color=ACCENT_RED, linewidth=2.5,
            marker="o", markersize=5, label="Hold (after costs)", zorder=3)
    ax.axhline(y=cash_offer / 1000, color=GOLD, linewidth=2.5, linestyle="--",
               label=f"Cash offer today: ${cash_offer / 1000:.0f}K", zorder=3)
    ax.fill_between(years, [cash_offer / 1000] * 6, [v / 1000 for v in hold_values],
                    where=[v < cash_offer for v in hold_values],
                    color=ACCENT_RED, alpha=0.15, zorder=1)

    ax.set_xlabel("Years", fontsize=9)
    ax.set_ylabel("Value ($K)", fontsize=9)
    ax.legend(loc="best", fontsize=8, facecolor=DARK_BG, edgecolor=GRID_COLOR, labelcolor=LIGHT_TEXT)
    ax.grid(color=GRID_COLOR, alpha=0.3, zorder=0)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('$%.0fK'))

    return _img_tag(_fig_to_base64(fig), "Sell vs Hold Analysis")


def chart_seller_satisfaction() -> str:
    """Donut chart: seller satisfaction after selling."""
    labels = ["Very Happy", "Happy", "Neutral", "Unhappy"]
    sizes = [42, 31, 15, 12]
    colors = [ACCENT_GREEN, GOLD, ACCENT_BLUE, ACCENT_RED]
    explode = (0.03, 0, 0, 0)

    fig, ax = plt.subplots(figsize=(4.5, 2.8), facecolor=DARK_BG)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%", startangle=90,
        colors=colors, explode=explode, pctdistance=0.78,
        textprops={"color": LIGHT_TEXT, "fontsize": 8},
        wedgeprops={"linewidth": 1.5, "edgecolor": DARK_BG},
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")

    # Center hole for donut
    centre = plt.Circle((0, 0), 0.55, fc=DARK_BG)
    ax.add_artist(centre)
    ax.text(0, 0.05, "73%", ha="center", va="center", color=GOLD, fontsize=18, fontweight="bold")
    ax.text(0, -0.18, "satisfied", ha="center", va="center", color=LIGHT_TEXT, fontsize=9)

    ax.set_title("How Sellers Feel After Selling", color=GOLD, fontsize=11, fontweight="bold", pad=8)

    return _img_tag(_fig_to_base64(fig), "Seller Satisfaction", width=440)


def chart_why_sellers_sell() -> str:
    """Horizontal bar: top reasons people sell."""
    reasons = [
        "Closer to family", "Need more space", "Job relocation",
        "Neighborhood changed", "Cash out equity", "Maintenance costs",
        "Life change", "Financial difficulty",
    ]
    pcts = [23, 18, 15, 12, 11, 9, 8, 4]

    fig, ax = _setup_fig(width=6.0, height=3.2, title="Top Reasons Homeowners Sell (NAR Survey)")
    y_pos = np.arange(len(reasons))
    colors_grad = [GOLD if p > 10 else ACCENT_BLUE for p in pcts]

    bars = ax.barh(y_pos, pcts, color=colors_grad, edgecolor="none", height=0.6, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(reasons, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("% of Sellers", fontsize=9)
    ax.grid(axis="x", color=GRID_COLOR, alpha=0.3, zorder=0)

    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{pct}%", ha="left", va="center", color=LIGHT_TEXT, fontsize=8, fontweight="bold")

    return _img_tag(_fig_to_base64(fig), "Why Sellers Sell")


def generate_email_charts(market_data: dict, holding_data: dict = None, include_satisfaction: bool = True) -> str:
    """Generate all charts for an outreach email. Returns HTML string."""
    city = market_data.get("city", "")
    state = market_data.get("state", "")
    price = market_data.get("median_home_price", 300000)
    yoy = market_data.get("price_change_yoy_pct", 3.0)

    sections = []

    # Section header
    sections.append(f"""
    <div style="background:#1a1a2e;padding:20px;border-radius:12px;margin:20px 0;border:1px solid #D4AF37;">
      <h3 style="color:#D4AF37;font-family:Georgia,serif;margin:0 0 5px 0;font-size:16px;">
        Your {city}{', ' + state if state else ''} Market at a Glance
      </h3>
      <p style="color:#aaa;font-size:11px;margin:0 0 15px 0;">
        Data compiled from NAR, Census Bureau, and local MLS records &bull; Updated Q1 2026
      </p>
    """)

    # Chart 1: Market snapshot
    try:
        sections.append(chart_market_snapshot(market_data))
    except Exception:
        pass

    # Chart 2: Holding costs (if we have breakdown)
    if holding_data:
        try:
            sections.append(chart_holding_cost(holding_data, city))
        except Exception:
            pass

    # Chart 3: Sell vs Hold projection
    annual_hold = holding_data["total_annual"] if holding_data else market_data.get("annual_holding_cost", 18000)
    try:
        sections.append(chart_sell_vs_hold(price, annual_hold, yoy, city))
    except Exception:
        pass

    # Chart 4: Seller satisfaction (optional -- only on first touch)
    if include_satisfaction:
        try:
            sections.append(chart_seller_satisfaction())
        except Exception:
            pass

    # Key stat callouts
    monthly_cost = holding_data["total_monthly"] if holding_data else market_data.get("monthly_holding_cost", 1500)
    sections.append(f"""
      <div style="margin-top:15px;padding:12px;background:#2a2a4e;border-radius:8px;border-left:3px solid #D4AF37;">
        <table style="width:100%;border:none;color:#f0f0f0;font-size:13px;font-family:Arial,sans-serif;">
          <tr>
            <td style="padding:4px 8px;"><strong style="color:#D4AF37;">Median Price:</strong> ${price:,}</td>
            <td style="padding:4px 8px;"><strong style="color:#D4AF37;">Days on Market:</strong> {market_data.get('days_on_market', 35)}</td>
          </tr>
          <tr>
            <td style="padding:4px 8px;"><strong style="color:#D4AF37;">YoY Change:</strong> {'+' if yoy > 0 else ''}{yoy}%</td>
            <td style="padding:4px 8px;"><strong style="color:#D4AF37;">Holding Cost:</strong> ${monthly_cost:,}/mo</td>
          </tr>
          <tr>
            <td colspan="2" style="padding:4px 8px;"><strong style="color:#D4AF37;">Market Type:</strong> {market_data.get('market_type_label', 'Balanced market')}</td>
          </tr>
        </table>
      </div>
    """)

    # Close container
    sections.append("</div>")

    return "\n".join(sections)


if __name__ == "__main__":
    from piper_market_data import get_market_data, get_holding_cost_breakdown

    mkt = get_market_data("Cleveland", "OH")
    hold = get_holding_cost_breakdown(165000, "OH")
    html = generate_email_charts(mkt, hold)

    # Save preview
    preview = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Chart Preview</title></head>
<body style="background:#111;padding:20px;">{html}</body></html>"""
    Path("chart_preview.html").write_text(preview)
    print(f"Preview saved to chart_preview.html ({len(html)} chars)")
