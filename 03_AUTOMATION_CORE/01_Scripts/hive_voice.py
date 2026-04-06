#!/usr/bin/env python3
"""
Hive Voice System -- ElevenLabs Conversational AI Integration
Give each AI employee a unique human voice.

Usage:
    python3 hive_voice.py --create-agents     # Create ElevenLabs agents for all voiced employees
    python3 hive_voice.py --speak "text"       # Marcus Cole speaks text (TTS)
    python3 hive_voice.py --brief              # Generate audio CEO brief
    python3 hive_voice.py --list               # List all voice assignments
    python3 hive_voice.py --test               # Test TTS for all voiced agents
"""

import argparse
import json
import os
import sys
import yaml
import requests
from pathlib import Path

BASE = "/mnt/sdcard/AA_MY_DRIVE"
ROSTER_PATH = f"{BASE}/06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml"
ENV_PATH = f"{BASE}/03_AUTOMATION_CORE/03_Credentials/.env"
AGENT_IDS_PATH = f"{BASE}/06_DEVELOPMENT/everlight_os/hive_mind/voice_agents.json"
AUDIO_DIR = f"{BASE}/07_STAGING/tts_cache/hive_voices"
REPORT_DIR = f"{BASE}/09_DASHBOARD/reports"

API_BASE = "https://api.elevenlabs.io/v1"


def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def load_roster():
    with open(ROSTER_PATH) as f:
        return yaml.safe_load(f)


def get_voiced_employees(roster):
    """Get all employees with voice_id assigned."""
    voiced = []
    for mgr_key, mgr in roster.get("managers", {}).items():
        # Standard employees list
        employees = mgr.get("employees", [])
        for emp in employees:
            if isinstance(emp, dict) and emp.get("voice_id"):
                emp["department"] = mgr_key
                voiced.append(emp)
        # Perplexity uses research_beats instead of employees
        beats = mgr.get("research_beats", [])
        for beat in beats:
            if isinstance(beat, dict) and beat.get("voice_id"):
                beat["department"] = mgr_key
                # Normalize agent_name -> name for consistency
                if "agent_name" in beat and "name" not in beat:
                    beat["name"] = beat["agent_name"]
                voiced.append(beat)
    return voiced


def log(msg):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S PT")
    print(f"[{ts}] {msg}", flush=True)


def tts_speak(api_key, text, voice_id, model="eleven_flash_v2", output_path=None):
    """Generate speech from text using ElevenLabs TTS."""
    resp = requests.post(
        f"{API_BASE}/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "speed": 1.0},
        },
        timeout=30,
    )
    if resp.status_code == 200:
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
        return resp.content
    else:
        log(f"TTS failed: {resp.status_code} {resp.text[:200]}")
        return None


def create_conversational_agent(api_key, name, voice_id, personality, first_message, model="eleven_flash_v2"):
    """Create an ElevenLabs conversational AI agent."""
    resp = requests.post(
        f"{API_BASE}/convai/agents/create",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "name": name,
            "tags": ["everlight", "hive-mind"],
            "conversation_config": {
                "tts": {
                    "voice_id": voice_id,
                    "model_id": model,
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                },
                "agent": {
                    "first_message": first_message,
                    "language": "en",
                    "prompt": {
                        "prompt": personality,
                        "llm": "gemini-2.5-flash",
                        "temperature": 0.7,
                    },
                },
            },
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data.get("agent_id")
    else:
        log(f"Agent creation failed for {name}: {resp.status_code} {resp.text[:300]}")
        return None


def cmd_list(roster):
    """List all voice assignments."""
    voiced = get_voiced_employees(roster)
    log(f"\nVoiced Employees: {len(voiced)}\n")
    for emp in voiced:
        name = emp.get("name", emp.get("agent_name", "?"))
        vid = emp.get("voice_id", "?")
        vdesc = emp.get("voice_description", "")
        dept = emp.get("department", "?")
        log(f"  {name:20s} | {dept:12s} | {vid} | {vdesc}")


def cmd_create_agents(roster, api_key):
    """Create ElevenLabs conversational agents for all voiced employees."""
    voiced = get_voiced_employees(roster)
    agent_ids = {}

    if os.path.exists(AGENT_IDS_PATH):
        with open(AGENT_IDS_PATH) as f:
            agent_ids = json.load(f)

    log(f"Creating {len(voiced)} conversational agents...\n")
    for emp in voiced:
        emp_id = emp.get("id", emp.get("name", "unknown"))
        name = emp.get("name", emp.get("agent_name", "?"))
        voice_id = emp.get("voice_id", "")
        personality_tags = emp.get("personality", [])
        email = emp.get("email", "")
        dept = emp.get("department", "")

        if emp_id in agent_ids:
            log(f"  SKIP {name} -- already created (agent_id: {agent_ids[emp_id]})")
            continue

        personality = (
            f"You are {name}, an AI employee at Everlight Ventures. "
            f"Your email is {email}. You work in the {dept} department. "
            f"Your personality traits: {', '.join(personality_tags)}. "
            f"Keep responses concise and professional. You are part of a 42-person AI team called the Hive Mind."
        )
        first_msg = f"Hi, this is {name} from Everlight Ventures. How can I help you today?"

        agent_id = create_conversational_agent(api_key, name, voice_id, personality, first_msg)
        if agent_id:
            agent_ids[emp_id] = agent_id
            log(f"  OK   {name:20s} -> agent_id: {agent_id}")
        else:
            log(f"  FAIL {name}")

    # Save agent IDs
    os.makedirs(os.path.dirname(AGENT_IDS_PATH), exist_ok=True)
    with open(AGENT_IDS_PATH, "w") as f:
        json.dump(agent_ids, f, indent=2)
    log(f"\nAgent IDs saved to {AGENT_IDS_PATH}")


def cmd_speak(api_key, text, roster, voice_name=None):
    """Marcus Cole speaks the given text."""
    voice_cfg = roster.get("voice", {})
    voice_id = voice_cfg.get("ceo_brief_voice", voice_cfg.get("default_voice_id", "pNInz6obpgDQGcFmaJgB"))

    os.makedirs(AUDIO_DIR, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = f"{AUDIO_DIR}/marcus_speaks_{ts}.mp3"

    log(f"Marcus Cole speaking ({len(text)} chars)...")
    result = tts_speak(api_key, text, voice_id, output_path=output)
    if result:
        log(f"Audio saved: {result}")
    else:
        log("TTS failed")


def cmd_brief(api_key, roster):
    """Generate audio version of latest CEO brief."""
    from datetime import datetime
    brief_path = f"{REPORT_DIR}/ceo_brief_{datetime.now().strftime('%Y-%m-%d')}.md"
    if not os.path.exists(brief_path):
        log(f"No CEO brief found at {brief_path}")
        return

    with open(brief_path) as f:
        brief_text = f.read()

    # Strip markdown formatting for speech
    import re
    clean = re.sub(r'[*_#|`\[\]]', '', brief_text)
    clean = re.sub(r'---+', '', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    clean = clean.strip()

    if len(clean) > 5000:
        clean = clean[:5000] + "... That's the summary for today."

    cmd_speak(api_key, clean, roster)


def cmd_test(api_key, roster):
    """Test TTS for all voiced agents with a short phrase."""
    voiced = get_voiced_employees(roster)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    for emp in voiced:
        name = emp.get("name", emp.get("agent_name", "?"))
        voice_id = emp.get("voice_id", "")
        emp_id = emp.get("id", emp.get("name", "unknown"))
        test_text = f"Hi, this is {name} from Everlight Ventures. The Hive is operational and all systems are green."
        output = f"{AUDIO_DIR}/test_{emp_id}.mp3"

        log(f"  Testing {name}...")
        result = tts_speak(api_key, test_text, voice_id, output_path=output)
        if result:
            log(f"    OK -> {output}")
        else:
            log(f"    FAIL")


def main():
    parser = argparse.ArgumentParser(description="Hive Voice System")
    parser.add_argument("--create-agents", action="store_true", help="Create ElevenLabs conversational agents")
    parser.add_argument("--speak", type=str, help="Marcus Cole speaks this text")
    parser.add_argument("--brief", action="store_true", help="Generate audio CEO brief")
    parser.add_argument("--list", action="store_true", help="List voice assignments")
    parser.add_argument("--test", action="store_true", help="Test TTS for all voices")
    args = parser.parse_args()

    env = load_env()
    roster = load_roster()
    api_key = env.get("ELEVENLABS_API_KEY", "")

    if args.list:
        cmd_list(roster)
        return

    if not api_key and not args.list:
        log("ERROR: ELEVENLABS_API_KEY not found in .env")
        log("Get your key at elevenlabs.io -> Profile -> API Key")
        sys.exit(1)

    if args.create_agents:
        cmd_create_agents(roster, api_key)
    elif args.speak:
        cmd_speak(api_key, args.speak, roster)
    elif args.brief:
        cmd_brief(api_key, roster)
    elif args.test:
        cmd_test(api_key, roster)
    else:
        cmd_list(roster)


if __name__ == "__main__":
    main()
