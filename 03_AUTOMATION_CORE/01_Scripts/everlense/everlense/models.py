from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MediaItem:
    path: str
    sha256: str
    source: str            # "camera" | "screenshot" | "social"
    taken_at: Optional[str]
    gps: Optional[dict]    # {"lat": float, "lon": float, "from": "exif"} or None
    width: int
    height: int

@dataclass
class Label:
    category: str          # "Personal" | "Business/Properties" | "Screenshots/Linux" ...
    project: Optional[str] = None
    confidence: float = 0.0
    tier: int = 0          # 0 = heuristic, 1 = AI
    signals: list = field(default_factory=list)
    proposed_category: Optional[str] = None

@dataclass
class PhotoRecord:
    sha256: str
    dest_path: str
    source: str
    category: str
    project: Optional[str]
    taken_at: Optional[str]
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    address: Optional[str]
    ocr_text: Optional[str]
    tags: list
    stamped: bool
    filed_at: str
