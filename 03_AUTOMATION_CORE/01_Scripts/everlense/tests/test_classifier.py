from everlense import classifier
from everlense.models import MediaItem
from everlense import config

def _item(source="screenshot", w=1080, h=2400):
    return MediaItem("/x/a.png", "h1", source, "2026-05-31T10:00:00", None, w, h)

def test_screenshot_keyword_match(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    lbl = classifier.classify_screenshot(_item(), cats, ocr="user@box:~$ sudo apt update")
    assert lbl.category == "Screenshots/Linux" and lbl.tier == 0 and lbl.confidence >= 0.5

def test_screenshot_low_confidence_when_no_keyword(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    lbl = classifier.classify_screenshot(_item(), cats, ocr="a pretty sunset photo")
    assert lbl.confidence < 0.5      # falls through to Tier-1 later

def test_camera_heuristic_defaults_to_business_inbox(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    lbl = classifier.classify_camera(_item(source="camera", w=4000, h=3000), ocr="")
    assert lbl.category in ("Business/_Inbox", "Personal") and lbl.tier == 0
