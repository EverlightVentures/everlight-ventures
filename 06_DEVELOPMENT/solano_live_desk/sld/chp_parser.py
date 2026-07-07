from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .geo import decode_latlon, in_corridor_bbox, in_solano_bbox

# Escape a bare '&' that is not already the start of an XML entity.
_BARE_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")


def _clean(text: str | None) -> str:
    if text is None:
        return ""
    return text.strip().strip('"').strip()


def _sanitize(xml_str: str) -> str:
    return _BARE_AMP.sub("&amp;", xml_str)


def is_solano(
    area: str,
    lat: float | None = None,
    lon: float | None = None,
    scope: str = "corridor",
) -> bool:
    """Decide whether an incident belongs on the feed.

    CHP assigns every incident to an area office (Solano = office #365), so an
    area of "Solano" is always included. Beyond that the two scopes differ:

    - scope="corridor" (default): include anything inside the driving-corridor
      box regardless of which county office CHP assigned it to, so Benicia-Bridge
      and I-80/I-680 approach incidents (which CHP labels a neighbor county) show.
      Road names are never used, so far-south freeway calls (San Jose) stay out.
    - scope="county": trust CHP's label. Reject any non-blank, non-Solano office;
      use the strict Solano box only when CHP left the area blank.
    """
    a = _clean(area).lower()
    if a == "solano":
        return True
    if scope == "corridor":
        return in_corridor_bbox(lat, lon)
    if a:
        return False
    return in_solano_bbox(lat, lon)


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
    xml_str: str, dispatch_id: str = "GGCC", scope: str = "corridor"
) -> list[dict]:
    """Parse CHP sa.xml into normalized incident dicts for the given scope.

    Tolerant by design: the live CHP feed frequently ends mid-tag or carries
    an unescaped '&'. We feed an XMLPullParser and read only the <Log> elements
    that completed, so a broken tail cannot discard the good records before it.
    """
    parser = ET.XMLPullParser(events=("start", "end"))
    try:
        parser.feed(_sanitize(xml_str))
    except ET.ParseError:
        pass  # keep whatever completed before the malformed point
    out: list[dict] = []
    dispatch_stack: list[str | None] = []
    for event, elem in parser.read_events():
        if elem.tag == "Dispatch":
            if event == "start":
                dispatch_stack.append(elem.get("ID"))
            elif dispatch_stack:
                dispatch_stack.pop()
        elif event == "end" and elem.tag == "Log":
            current = dispatch_stack[-1] if dispatch_stack else None
            if current != dispatch_id:
                continue
            area = _clean(elem.findtext("Area"))
            lat, lon = decode_latlon(_clean(elem.findtext("LATLON")))
            if not is_solano(area, lat, lon, scope=scope):
                continue
            out.append(_build_event(elem, dispatch_id, lat, lon))
    return out
