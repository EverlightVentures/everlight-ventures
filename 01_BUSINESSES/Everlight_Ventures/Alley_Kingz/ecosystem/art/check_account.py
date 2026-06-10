#!/usr/bin/env python3
"""
ELEVENLABS ACCOUNT INSPECTOR (read-only, pure stdlib)
=====================================================
Prints the subscription tier, credit balance, and key identity so we can
confirm what this key touches. Used to verify Alley Kingz key isolation.
Pure stdlib. No writes. RUN: python3 check_account.py  (uses ELEVENLABS_API_KEY)
"""
import os, json, urllib.request, urllib.error

KEY = (os.environ.get("ALLEY_KINGZ_ELEVENLABS_API_KEY")
       or os.environ.get("AK_ELEVENLABS_API_KEY")
       or os.environ.get("ELEVENLABS_API_KEY"))
BASE = "https://api.elevenlabs.io/v1"


def get(path):
    req = urllib.request.Request(BASE + path, method="GET")
    req.add_header("xi-api-key", KEY)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"_error": type(e).__name__, "_msg": str(e)[:200]}


def main():
    if not KEY:
        print("No ELEVENLABS_API_KEY in env."); return 0
    print("KEY tail:", "..." + KEY[-6:])

    sub = get("/user/subscription")
    print("\n== SUBSCRIPTION ==")
    for k in ("tier", "character_count", "character_limit", "status",
              "can_extend_character_limit", "allowed_to_extend_character_limit",
              "next_character_count_reset_unix", "currency"):
        if k in sub:
            print("  %s: %s" % (k, sub[k]))
    if "character_limit" in sub and "character_count" in sub:
        print("  characters_remaining:", sub["character_limit"] - sub["character_count"])
    if "_http_error" in sub:
        print("  ERROR:", sub)

    user = get("/user")
    print("\n== USER ==")
    if isinstance(user, dict):
        for k in ("user_id", "is_new_user", "xi_api_key"):
            if k in user:
                v = user[k]
                if k == "xi_api_key" and isinstance(v, str):
                    v = "..." + v[-6:]
                print("  %s: %s" % (k, v))

    voices = get("/voices")
    print("\n== VOICES VISIBLE TO THIS KEY ==")
    if isinstance(voices, dict) and "voices" in voices:
        for v in voices["voices"]:
            print("  - %-28s cat=%-10s id=%s" %
                  (v.get("name"), v.get("category"), v.get("voice_id")))
        print("  total:", len(voices["voices"]))
    else:
        print("  ", voices)


if __name__ == "__main__":
    raise SystemExit(main())
