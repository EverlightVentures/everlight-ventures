from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .geo_county import distance_mi
from .geo import decode_latlon

# Default bubble center (Fairfield / Solano) when the driver's GPS is unknown.
DEFAULT_CENTER: tuple[float, float] = (38.2494, -122.0400)

# Escape a bare '&' that is not already the start of an XML entity.
_BARE_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")


def _clean(text: str | None) -> str:
    if text is None:
        return ""
    return text.strip().strip('"').strip()


def _sanitize(xml_str: str) -> str:
    return _BARE_AMP.sub("&amp;", xml_str)


def _build_event(log: ET.Element, dispatch_id: str, lat: float | None, lon: float | None) -> dict:
    log_id = log.get("ID") or ""
    logtype = _clean(log.findtext("LogType"))
    location = _clean(log.findtext("Location"))
    location_desc = _clean(log.findtext("LocationDesc"))
    area = _clean(log.findtext("Area"))
    logtime = _clean(log.findtext("LogTime"))
    details: list[str] = []
    for d in log.findall("./LogDetails/details"):
        dt = _clean(d.findtext("DetailTime"))
        txt = _clean(d.findtext("IncidentDetail"))
        if txt:
            details.append(f"{dt}  {txt}".strip())
    title = f"{logtype} - {location}".strip(" -")
    return {
        "id": f"chp:{dispatch_id}:{log_id}",
        "source": "chp",
        "type": logtype,
        "title": title,
        "lat": lat,
        "lon": lon,
        "geo_label": location or location_desc,
        "log_time": logtime,
        "area": area,
        "body": "\n".join(details),
        "details": details,
    }


def parse_incidents(
    xml_str: str,
    center: tuple[float, float] | None = None,
    radius_mi: float = 75.0,
) -> list[dict]:
    """Parse CHP sa.xml into incidents inside a radius bubble around a center.

    The bubble replaces the old fixed-county filter: we read EVERY dispatch
    center statewide and keep any located incident within radius_mi of the
    center point (the driver's live GPS, or Fairfield by default). This is what
    makes the map cover the whole Bay Area and follow the operator anywhere.

    Tolerant by design: the live feed often ends mid-tag or carries a bare '&',
    so we read completed <Log> elements from an XMLPullParser and ignore the tail.
    """
    center = center or DEFAULT_CENTER
    parser = ET.XMLPullParser(events=("start", "end"))
    try:
        parser.feed(_sanitize(xml_str))
    except ET.ParseError:
        pass
    out: list[dict] = []
    dispatch_stack: list[str | None] = []
    for event, elem in parser.read_events():
        if elem.tag == "Dispatch":
            if event == "start":
                dispatch_stack.append(elem.get("ID"))
            elif dispatch_stack:
                dispatch_stack.pop()
        elif event == "end" and elem.tag == "Log":
            dispatch_id = dispatch_stack[-1] if dispatch_stack else "CHP"
            lat, lon = decode_latlon(_clean(elem.findtext("LATLON")))
            if lat is None or lon is None:
                continue  # unlocated incidents cannot be placed in the bubble
            if distance_mi(center, (lat, lon)) > radius_mi:
                continue
            out.append(_build_event(elem, dispatch_id, lat, lon))
    return out
