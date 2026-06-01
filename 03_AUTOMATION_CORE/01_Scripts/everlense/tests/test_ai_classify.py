import os
from everlense import ai_classify
from everlense.models import MediaItem, Label

def _item(source="screenshot"):
    return MediaItem("/x/a.png", "h1", source, None, None, 1080, 2400)

def test_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ai_classify.ai_label(_item(), {"AI": {"keywords": []}}, "claude prompt") is None

def test_parses_model_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(ai_classify, "_raw_call",
        lambda *a, **k: '{"category":"Screenshots/AI","confidence":0.9}')
    lbl = ai_classify.ai_label(_item(), {"AI": {"keywords": []}}, "claude prompt")
    assert isinstance(lbl, Label) and lbl.category == "Screenshots/AI" and lbl.tier == 1
