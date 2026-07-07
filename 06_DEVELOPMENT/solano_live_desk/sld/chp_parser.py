from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .geo import decode_latlon, in_solano_bbox

# Escape a bare '&' that is not already the start of an XML entity.
_BARE_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)")


def _clean(text: str | None) -> str:
    if text is None:
        return ""
    return text.strip().strip('"').strip()


def _sanitize(xml_str: str) -> str:
    return _BARE_AMP.sub("&amp;", xml_str)


def is_solano(area: str, lat: float | None = None, lon: float | None = None) -> bool:
    """Decide Solano membership by CHP's own area-office label first.

    CHP assigns every incident to an area office (Solano = office #365). Trust
    that label: include when it is "Solano", reject when it names another office
    (I-80/I-680 run through all 9 Bay Area counties, so road names are not proof).
    Only when CHP leaves the area blank do we fall back to the coordinate box.
    """
    a = _clean(area).lower()
    if a == "solano":
        return True
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


def parse_incidents(xml_str: str, dispatch_id: str = "GGCC") -> list[dict]:
    """Parse CHP sa.xml into normalized Solano incident dicts.

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
            if not is_solano(area, lat, lon):
                continue
            out.append(_build_event(elem, dispatch_id, lat, lon))
    return out
