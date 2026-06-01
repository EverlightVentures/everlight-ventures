import os
import json
import base64
from everlense.models import MediaItem, Label

_MODEL = "claude-haiku-4-5"

def _raw_call(system: str, content: list) -> str:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=_MODEL, max_tokens=200,
        system=system, messages=[{"role": "user", "content": content}])
    return msg.content[0].text

def _parse(text: str) -> Label | None:
    try:
        start = text.index("{"); end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        return Label(category=data["category"], project=data.get("project"),
                     confidence=float(data.get("confidence", 0.7)), tier=1,
                     signals=["haiku"], proposed_category=data.get("proposed_category"))
    except Exception:
        return None

def ai_label(item: MediaItem, categories: dict, ocr: str) -> Label | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    cat_names = list(categories.keys())
    if item.source == "screenshot":
        system = ("You classify a phone screenshot into exactly one topic. "
                  f"Choose from: {cat_names}. If none fit, set proposed_category to a new short name. "
                  'Reply ONLY JSON: {"category":"Screenshots/<Topic>","confidence":0-1,"proposed_category":null}')
        content = [{"type": "text", "text": f"OCR text:\n{ocr[:1500]}"}]
    else:
        try:
            with open(item.path, "rb") as fh:
                b64 = base64.standard_b64encode(fh.read()).decode()
        except Exception:
            return None
        system = ('You classify a phone photo. Reply ONLY JSON: '
                  '{"category":"Personal" or "Business/_Inbox" or "Business/Receipts_Docs","confidence":0-1}')
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}]
    return _parse(_raw_call(system, content))
