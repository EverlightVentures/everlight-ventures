from __future__ import annotations

# Broadcastify live-listen feeds by county FIPS. Listen-only embeds (ToS: no
# scraping/restream). Extend as new counties are added to the follow-me tray.
COUNTY_FEEDS = {
    "06095": [  # Solano
        {"id": "4881", "name": "Fairfield / Vacaville / Suisun PD, Fire & EMS"},
        {"id": "28814", "name": "CHP Solano (I-80 / I-680)"},
        {"id": "20773", "name": "Solano Sheriff, Rio Vista & Dixon PD"},
        {"id": "45005", "name": "Solano CAL FIRE"},
        {"id": "820", "name": "Vallejo Fire (PD priority encrypted)"},
    ],
}


def feeds_for_county(fips: str | None) -> list[dict]:
    """Broadcastify live-listen feeds for a county, each with a listen URL."""
    out = []
    for f in COUNTY_FEEDS.get(fips or "", []):
        out.append({**f, "url": f"https://www.broadcastify.com/listen/feed/{f['id']}"})
    return out
