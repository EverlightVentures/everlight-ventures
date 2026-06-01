def ocr_text(path: str) -> str:
    """Return OCR text for an image, or '' on any failure. Isolated so tests can monkeypatch it."""
    try:
        import pytesseract
        from PIL import Image
        with Image.open(path) as im:
            return pytesseract.image_to_string(im) or ""
    except Exception:
        return ""
