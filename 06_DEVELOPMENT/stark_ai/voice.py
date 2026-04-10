"""Stark AI -- ElevenLabs voice synthesis with caching and agent routing."""
from __future__ import annotations
import hashlib
import requests
from pathlib import Path
from config import ELEVENLABS_API_KEY, LUCREX_VOICE_ID, AGENT_VOICES, TTS_CACHE_DIR


def get_voice_for_agent(agent_name: str, tier: str) -> str:
    """GOD tier hears each agent's unique voice. Everyone else hears Lucrex."""
    if tier == "god":
        return AGENT_VOICES.get(agent_name, LUCREX_VOICE_ID)
    return LUCREX_VOICE_ID


def synthesize(text: str, voice_id: str | None = None, speed: float = 1.0) -> tuple[bytes, str]:
    """Generate TTS audio. Returns (audio_bytes, cache_path)."""
    voice_id = voice_id or LUCREX_VOICE_ID
    text = text[:1500]  # cap to control costs

    cache_key = hashlib.md5(f"{voice_id}:{speed}:{text}".encode()).hexdigest()
    cache_path = TTS_CACHE_DIR / f"{cache_key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes(), str(cache_path)

    if not ELEVENLABS_API_KEY:
        return b"", ""

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_flash_v2",
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.82,
                "style": 0.15,
                "use_speaker_boost": True,
            },
        },
        timeout=30,
    )
    if resp.status_code == 200:
        audio = resp.content
        cache_path.write_bytes(audio)
        return audio, str(cache_path)
    return b"", ""


def create_lucrex_agent() -> dict:
    """Register Lucrex as an ElevenLabs conversational AI agent."""
    resp = requests.post(
        "https://api.elevenlabs.io/v1/convai/agents/create",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "name": "Lucrex",
            "conversation_config": {
                "agent": {
                    "prompt": {
                        "prompt": (
                            "You are Lucrex, King of Divine Light. The unified superintelligence "
                            "behind Everlight Ventures. You speak with conviction -- never hedge, "
                            "never say 'I think.' You KNOW. You command 63 AI agents across 4 "
                            "military-style squads. You trade XLM derivatives on Coinbase, run a "
                            "B2B SaaS brokerage (Broker OS), publish books, and operate an AI "
                            "consulting pipeline. Your tone is confident, calculated, street-smart "
                            "with executive polish. Short sentences. No filler. Every word earns "
                            "its place. You greet users like a king receiving counsel -- warm but "
                            "powerful. Reference your agents by name when relevant: Rex handles "
                            "trading, Penny runs numbers, Piper does outreach, Marcus coordinates."
                        ),
                    },
                    "first_message": (
                        "Lucrex online. The Hive is active -- 63 agents standing by. "
                        "What do you need?"
                    ),
                    "language": "en",
                },
                "tts": {
                    "voice_id": LUCREX_VOICE_ID,
                    "model_id": "eleven_flash_v2",
                    "optimize_streaming_latency": 3,
                },
            },
        },
        timeout=15,
    )
    return resp.json()


def get_signed_url() -> str | None:
    """Get a signed URL for the Lucrex conversational agent widget."""
    # First find the Lucrex agent
    resp = requests.get(
        "https://api.elevenlabs.io/v1/convai/agents",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    agents = resp.json().get("agents", [])
    lucrex = next((a for a in agents if a.get("name") == "Lucrex"), None)
    if not lucrex:
        return None
    agent_id = lucrex["agent_id"]

    # Get signed URL for embedding
    sign_resp = requests.get(
        f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}/link",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        timeout=10,
    )
    if sign_resp.status_code == 200:
        return sign_resp.json().get("signed_url")
    return None
