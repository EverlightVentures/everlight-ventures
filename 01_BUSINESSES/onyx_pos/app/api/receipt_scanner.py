"""
Onyx POS -- Receipt Scanner Module
Built by SaaS Factory: Leo Marchetti (AI/CV Lead)

OpenCV preprocessing pipeline + Tesseract OCR for receipt digitization.
Extracts: vendor, date, line items, subtotal, tax, total from receipt photos.

Pipeline: grayscale → blur → edge detect → contour → perspective correct → threshold → OCR → parse
"""
import cv2
import numpy as np
import re
from datetime import datetime
from typing import Optional
import io
import json


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 corner points: top-left, top-right, bottom-right, bottom-left.

    Uses sum/diff trick: TL has smallest sum, BR has largest sum,
    TR has smallest diff, BL has largest diff.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left

    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply perspective transform to flatten a document/receipt.

    Takes 4 corner points, computes the target rectangle dimensions,
    and warps the image to a top-down view.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Compute width: max of top edge and bottom edge
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    # Compute height: max of left edge and right edge
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    # Destination points for the top-down view
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))

    return warped


def preprocess_receipt(image_bytes: bytes) -> np.ndarray:
    """Full preprocessing pipeline for a receipt image.

    1. Decode image from bytes
    2. Resize to manageable dimensions (max 1500px on longest side)
    3. Convert to grayscale
    4. Apply Gaussian blur to reduce noise
    5. Detect edges with Canny
    6. Find receipt contour (largest 4-sided contour)
    7. Apply perspective correction if receipt found
    8. Apply adaptive thresholding for clean OCR input

    Returns: preprocessed binary image ready for OCR
    """
    # Decode
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not decode image")

    # Resize if too large (keeps aspect ratio)
    h, w = image.shape[:2]
    max_dim = 1500
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    original = image.copy()

    # Grayscale + blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edged = cv2.Canny(blurred, 50, 200)

    # Dilate to close gaps in edges
    kernel = np.ones((5, 5), np.uint8)
    edged = cv2.dilate(edged, kernel, iterations=1)

    # Find contours -- look for the receipt boundary
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    receipt_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # A receipt is roughly rectangular (4 corners)
        if len(approx) == 4:
            receipt_contour = approx
            break

    # Apply perspective correction if we found the receipt
    if receipt_contour is not None:
        warped = four_point_transform(
            cv2.cvtColor(original, cv2.COLOR_BGR2GRAY),
            receipt_contour.reshape(4, 2)
        )
    else:
        # No clear receipt boundary -- use the whole grayscale image
        warped = gray

    # Adaptive thresholding for clean OCR
    thresh = cv2.adaptiveThreshold(
        warped, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21, 10
    )

    return thresh


def ocr_image(preprocessed: np.ndarray) -> str:
    """Run Tesseract OCR on a preprocessed image.

    Falls back to returning empty string if Tesseract is not installed.
    """
    try:
        import pytesseract
        text = pytesseract.image_to_string(preprocessed, config="--psm 6")
        return text.strip()
    except ImportError:
        # Tesseract not installed -- return raw text placeholder
        return "[OCR_UNAVAILABLE: install pytesseract and tesseract-ocr]"
    except Exception as e:
        return f"[OCR_ERROR: {str(e)}]"


def parse_receipt_text(raw_text: str) -> dict:
    """Parse raw OCR text into structured receipt data.

    Extracts:
    - vendor: first non-empty line (usually the store name)
    - date: first date-like pattern found
    - items: lines that look like "item_name ... $price"
    - subtotal, tax, total: common receipt keywords

    Returns dict with extracted fields + confidence estimate.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    if not lines:
        return {
            "vendor": None,
            "date": None,
            "items": [],
            "subtotal": None,
            "tax": None,
            "total": None,
            "raw_text": raw_text,
            "confidence": 0.0,
        }

    # Vendor: first substantive line
    vendor = lines[0] if lines else None

    # Date patterns
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',           # 04/12/2026
        r'\d{1,2}-\d{1,2}-\d{2,4}',            # 04-12-2026
        r'\d{4}-\d{2}-\d{2}',                    # 2026-04-12
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s*\d{4}',  # Apr 12, 2026
    ]
    receipt_date = None
    for pattern in date_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            receipt_date = match.group()
            break

    # Price pattern: captures dollar amounts
    price_pattern = r'\$?\d+\.\d{2}'

    # Line items: lines containing a price
    items = []
    for line in lines:
        prices = re.findall(price_pattern, line)
        if prices and not any(kw in line.upper() for kw in ["SUBTOTAL", "SUB TOTAL", "TAX", "TOTAL", "CHANGE", "CASH", "CARD", "CREDIT", "DEBIT", "BALANCE"]):
            # Clean up item name (everything before the price)
            price_str = prices[-1]  # Last price on the line is usually the line total
            name_part = line[:line.rfind(price_str)].strip()
            name_part = re.sub(r'[.\s]+$', '', name_part)  # Remove trailing dots/spaces
            if name_part:
                price_val = float(price_str.replace("$", ""))
                items.append({"name": name_part, "price": price_val})

    # Totals
    def find_amount(keywords: list[str]) -> Optional[float]:
        for line in lines:
            upper = line.upper()
            if any(kw in upper for kw in keywords):
                prices = re.findall(price_pattern, line)
                if prices:
                    return float(prices[-1].replace("$", ""))
        return None

    subtotal = find_amount(["SUBTOTAL", "SUB TOTAL", "SUB-TOTAL"])
    tax = find_amount(["TAX"])
    total = find_amount(["TOTAL"])

    # If total wasn't found but subtotal and tax were, compute it
    if total is None and subtotal is not None and tax is not None:
        total = round(subtotal + tax, 2)

    # Confidence: rough estimate based on how much we extracted
    confidence_score = 0.0
    if vendor:
        confidence_score += 0.15
    if receipt_date:
        confidence_score += 0.15
    if items:
        confidence_score += min(0.3, len(items) * 0.05)
    if subtotal is not None:
        confidence_score += 0.15
    if tax is not None:
        confidence_score += 0.10
    if total is not None:
        confidence_score += 0.15

    return {
        "vendor": vendor,
        "date": receipt_date,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "raw_text": raw_text,
        "confidence": round(confidence_score, 2),
    }


def scan_receipt(image_bytes: bytes) -> dict:
    """Full receipt scanning pipeline.

    Takes raw image bytes, preprocesses with OpenCV, runs OCR,
    parses into structured data.

    Returns:
        dict with vendor, date, items, subtotal, tax, total,
        raw_text, confidence, scanned_at
    """
    # Step 1: OpenCV preprocessing
    preprocessed = preprocess_receipt(image_bytes)

    # Step 2: OCR
    raw_text = ocr_image(preprocessed)

    # Step 3: Parse
    result = parse_receipt_text(raw_text)
    result["scanned_at"] = datetime.utcnow().isoformat()

    return result
