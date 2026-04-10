"""Stark AI -- Configuration loaded from .env credentials."""
import os
from pathlib import Path

# Load credentials
_env_path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
if not _env_path.exists():
    _env_path = Path("/home/opc/03_Credentials/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_ANON_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww",
)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
LUCREX_VOICE_ID = "f6pM8mPp5ODaRZDE6oTq"  # Jeremy -- the voice of Lucrex

# Agent voice map (GOD mode hears each agent's unique voice)
AGENT_VOICES = {
    "Marcus Cole": "onwK4e9ZLuTAKqWW03F9",
    "Rex Thornton": "GBv7mTt0atIp3Br8iCZE",
    "Rex Blackwell": "ODq5zmih8GrVes37Dizd",
    "Piper Reeves": "XrExE9yKIg1WjnnlVkGX",
    "Penny Vance": "21m00Tcm4TlvDq8ikWAM",
    "Filter Banks": "iP95p4xoKVk53GoZ742B",
    "Harrison Knox": "29vD33N1CtxCmqQRPOHJ",
    "Justine Park": "Xb7hH8MSUJpSbSDYk0k2",
    "Major Dex": "pqHfZKP75CvOlQylNhV4",
    "Scout Navarro": "bVMeCyTHy58xNoL34h3p",
    "Ace Morgan": "ErXwobaYiN019PkySvjV",
    "Forge Steele": "pNInz6obpgDQGcFmaJgB",
    "Cipher Wolfe": "CYw3kZ02Hs0563khs1Fj",
}

# Tier permission matrix
TIER_PERMISSIONS = {
    "god": [
        "trading", "dispatch", "email", "deals", "infrastructure",
        "voice-switch", "reports", "dashboards", "questions", "history",
    ],
    "client": ["reports", "dashboards", "questions", "history"],
    "public": ["demo", "about"],
}

# Command category -> agent routing
AGENT_ROUTING = {
    "trading":        ["Rex Thornton", "Penny Vance", "Cipher Wolfe"],
    "dispatch":       ["Marcus Cole"],
    "email":          ["Piper Reeves", "Marcus Cole"],
    "deals":          ["Rex Blackwell", "Filter Banks", "Harrison Knox", "Piper Reeves"],
    "infrastructure": ["Forge Steele", "Major Dex"],
    "reports":        ["Penny Vance", "Marcus Cole"],
    "dashboards":     ["Marcus Cole"],
    "questions":      ["Marcus Cole"],
    "demo":           ["Marcus Cole"],
    "about":          ["Marcus Cole"],
}

# Server
PORT = int(os.getenv("STARK_PORT", "8511"))
WORKSPACE = os.getenv("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE")
ORACLE_DASHBOARD_URL = "http://129.159.38.250:8502"
TTS_CACHE_DIR = Path(os.getenv("TTS_CACHE", "/mnt/sdcard/AA_MY_DRIVE/07_STAGING/tts_cache/stark"))
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
