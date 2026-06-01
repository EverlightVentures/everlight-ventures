from everlense.models import MediaItem, Label

_TIER1_THRESHOLD = 0.5

def classify_screenshot(item: MediaItem, categories: dict, ocr: str) -> Label:
    text = (ocr or "").lower()
    best, best_hits = None, 0
    for name, spec in categories.items():
        hits = sum(1 for kw in (spec.get("keywords") or []) if kw.lower() in text)
        if hits > best_hits:
            best, best_hits = name, hits
    if best and best_hits > 0:
        conf = min(0.5 + 0.15 * best_hits, 0.95)
        return Label(category=f"Screenshots/{best}", confidence=conf, tier=0,
                     signals=[f"keyword x{best_hits} -> {best}"])
    return Label(category="Screenshots/_Inbox", confidence=0.2, tier=0, signals=["no keyword match"])

def classify_camera(item: MediaItem, ocr: str) -> Label:
    # Tier-0 cannot know the project of an old photo. Route to a holding bucket; Tier-1/operator decides.
    text = (ocr or "").lower()
    if any(k in text for k in ("receipt", "invoice", "total")):
        return Label(category="Business/Receipts_Docs", confidence=0.6, tier=0, signals=["receipt text"])
    return Label(category="Business/_Inbox", confidence=0.3, tier=0, signals=["camera default"])

def needs_tier1(label: Label) -> bool:
    return label.confidence < _TIER1_THRESHOLD

def classify(item: MediaItem, categories: dict, ocr_fn, ai=None) -> Label:
    text = ocr_fn(item.path) if item.source == "screenshot" else ""
    if item.source == "screenshot":
        label = classify_screenshot(item, categories, text)
    else:
        label = classify_camera(item, text)
    if ai is not None and needs_tier1(label):
        upgraded = ai(item, categories, text)
        if upgraded is not None:
            return upgraded
    return label
