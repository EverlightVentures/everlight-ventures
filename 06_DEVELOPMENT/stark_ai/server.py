"""
STARK AI -- Voice-First Command Center for Everlight Ventures
FastAPI backend: auth, command routing, TTS, agent dispatch.
Port 8511 | Supabase auth | ElevenLabs TTS | Claude CLI dispatch
"""
from __future__ import annotations
import uuid
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import io

from config import PORT, TTS_CACHE_DIR, LUCREX_VOICE_ID
import auth as stark_auth
import voice as stark_voice
import commands as stark_cmd


# ── Pydantic models ──────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None

class CommandRequest(BaseModel):
    text: str
    voice: bool = False           # return TTS audio URL
    session_id: str | None = None

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    voice_enabled: bool | None = None
    preferred_voice: str | None = None
    voice_speed: float | None = None
    theme: str | None = None

class SpeakRequest(BaseModel):
    text: str
    voice_id: str | None = None
    speed: float = 1.0


# ── App ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="Stark AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Dependency: authenticated user ───────────────────────────────────

async def get_current_user(request: Request) -> dict:
    return await stark_auth.verify_token(request)


# ── Auth endpoints ───────────────────────────────────────────────────

@app.post("/api/stark/auth/signup")
async def signup(req: AuthRequest):
    data = await stark_auth.signup(req.email, req.password, req.display_name)
    return {"ok": True, "user": data.get("user"), "session": data.get("session")}


@app.post("/api/stark/auth/login")
async def login(req: AuthRequest):
    data = await stark_auth.login(req.email, req.password)
    return {
        "ok": True,
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "user": data.get("user"),
        "stark_profile": data.get("stark_profile"),
    }


@app.get("/api/stark/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"ok": True, "user": user}


@app.patch("/api/stark/auth/profile")
async def update_profile(updates: ProfileUpdate, user: dict = Depends(get_current_user)):
    patch = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(400, "Nothing to update")
    result = await stark_auth.update_profile(user["id"], patch)
    return {"ok": True, "profile": result}


# ── Command endpoint ─────────────────────────────────────────────────

@app.post("/api/stark/command")
async def handle_command(req: CommandRequest, user: dict = Depends(get_current_user)):
    """Process a text/voice command through the Stark AI engine."""
    result = await stark_cmd.process_command(req.text, user)
    result["tier"] = user["tier"]

    # Generate TTS if requested
    audio_url = None
    voice_id = None
    if req.voice and not result.get("denied"):
        voice_id = stark_voice.get_voice_for_agent(result["agent"], user["tier"])
        audio_bytes, cache_path = stark_voice.synthesize(result["text"], voice_id)
        if audio_bytes:
            # Return audio as a URL that can be fetched
            fname = Path(cache_path).name if cache_path else f"{uuid.uuid4().hex}.mp3"
            audio_url = f"/api/stark/audio/{fname}"

    # Log to Supabase (fire and forget)
    cmd_id = await stark_cmd.log_command(
        user_id=user["id"],
        session_id=req.session_id,
        input_text=req.text,
        response=result,
        voice_id=voice_id,
    )

    return {
        "ok": True,
        "id": cmd_id,
        "text": result["text"],
        "agent": result["agent"],
        "category": result["category"],
        "agents_used": result["agents_used"],
        "audio_url": audio_url,
        "voice_id": voice_id,
        "latency_ms": result["latency_ms"],
    }


# ── Public command (no auth, limited) ────────────────────────────────

@app.post("/api/stark/demo")
async def demo_command(req: CommandRequest):
    """Public demo endpoint -- limited responses, no dispatch."""
    demo_user = {"id": "demo", "tier": "public", "display_name": "Guest"}
    category = stark_cmd.classify(req.text)
    if category not in ("demo", "about", "questions"):
        return {
            "ok": True,
            "text": (
                "Lucrex here. That command requires authentication. "
                "Sign up to unlock the full Hive Mind experience -- "
                "63 agents, voice control, real-time trading intel."
            ),
            "agent": "Lucrex",
            "category": category,
            "agents_used": [],
            "denied": True,
        }
    result = await stark_cmd.process_command(req.text, demo_user)
    return {"ok": True, **result}


# ── Voice endpoints ──────────────────────────────────────────────────

@app.post("/api/stark/speak")
async def speak(req: SpeakRequest, user: dict = Depends(get_current_user)):
    """Generate TTS audio and return as streaming MP3."""
    voice_id = req.voice_id or LUCREX_VOICE_ID
    audio_bytes, _ = stark_voice.synthesize(req.text, voice_id, req.speed)
    if not audio_bytes:
        raise HTTPException(500, "TTS generation failed")
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/stark/audio/{filename}")
async def serve_audio(filename: str):
    """Serve cached TTS audio file."""
    path = TTS_CACHE_DIR / filename
    if not path.exists() or not path.suffix == ".mp3":
        raise HTTPException(404, "Audio not found")
    return StreamingResponse(
        io.BytesIO(path.read_bytes()),
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/stark/voice/widget-url")
async def widget_url(user: dict = Depends(get_current_user)):
    """Get ElevenLabs conversational widget URL for direct voice chat."""
    url = stark_voice.get_signed_url()
    if not url:
        raise HTTPException(404, "Lucrex voice agent not found. Create it first.")
    return {"ok": True, "url": url}


# ── Agent roster ─────────────────────────────────────────────────────

@app.get("/api/stark/agents")
async def list_agents(user: dict = Depends(get_current_user)):
    """Return available agents with their voice status."""
    from config import AGENT_VOICES, AGENT_ROUTING
    agents = []
    seen = set()
    for cat, names in AGENT_ROUTING.items():
        for name in names:
            if name not in seen:
                seen.add(name)
                agents.append({
                    "name": name,
                    "voice_id": AGENT_VOICES.get(name),
                    "has_voice": name in AGENT_VOICES,
                    "categories": [c for c, ns in AGENT_ROUTING.items() if name in ns],
                    "status": "online",
                })
    return {"ok": True, "agents": agents, "total": len(agents)}


# ── Command history ──────────────────────────────────────────────────

@app.get("/api/stark/history")
async def command_history(limit: int = 50, user: dict = Depends(get_current_user)):
    """Fetch user's command history from Supabase."""
    from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
    import requests as req
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    resp = req.get(
        f"{SUPABASE_URL}/rest/v1/stark_commands"
        f"?user_id=eq.{user['id']}&select=*&order=created_at.desc&limit={limit}",
        headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {key}"},
        timeout=10,
    )
    rows = resp.json() if resp.status_code == 200 else []
    return {"ok": True, "commands": rows}


# ── Session management ───────────────────────────────────────────────

@app.post("/api/stark/session")
async def create_session(user: dict = Depends(get_current_user)):
    """Create a new Stark session."""
    from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
    import requests as req
    session_id = str(uuid.uuid4())
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    req.post(
        f"{SUPABASE_URL}/rest/v1/stark_sessions",
        json={"id": session_id, "user_id": user["id"], "mode": "mixed"},
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    return {"ok": True, "session_id": session_id}


# ── Admin: create Lucrex agent ───────────────────────────────────────

@app.post("/api/stark/admin/create-lucrex")
async def create_lucrex_agent(user: dict = Depends(get_current_user)):
    """Create the Lucrex ElevenLabs conversational agent. GOD tier only."""
    if user["tier"] != "god":
        raise HTTPException(403, "GOD tier required")
    result = stark_voice.create_lucrex_agent()
    return {"ok": True, "agent": result}


# ── Health ───────────────────────────────────────────────────────────

@app.get("/api/stark/health")
async def health():
    return {
        "ok": True,
        "service": "stark-ai",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import uvicorn
    # Bind policy: 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
    uvicorn.run(app, host=os.environ.get("EV_BIND", "127.0.0.1"), port=PORT)
