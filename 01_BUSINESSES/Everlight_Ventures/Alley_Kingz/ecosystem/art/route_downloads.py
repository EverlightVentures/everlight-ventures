#!/usr/bin/env python3
# Route the operator's manually-made Seedance art from /mnt/sdcard/Download into the game's
# asset folders, matching each file to the game's EXISTING expected filename (case-insensitive,
# extension-agnostic -- browsers content-sniff, so PNG content under a .jpg name renders fine).
# Top-level Download only (skips OneDrive/NoteGPT). Reports every move + flags anything unmatched.
import os, shutil
DL   = "/mnt/sdcard/Download"
GAME = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game"
SUBS = ["assets/ui", "assets/spells", "assets/specials", "assets/cards", "assets/units"]
IMG  = (".png", ".jpg", ".jpeg", ".webp")

def norm(name):
    b = os.path.splitext(name)[0]
    # collapse double extensions like cur_gems.jpg.png -> cur_gems
    for e in (".jpg", ".jpeg", ".png", ".webp"):
        if b.lower().endswith(e): b = b[:-len(e)]
    return b.lower()

# map of game-asset basename -> its real path (ui wins ties)
dests = {}
for sub in SUBS:
    d = os.path.join(GAME, sub)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith(IMG):
                dests.setdefault(norm(f), os.path.join(d, f))

routed, unmapped = [], []
for f in sorted(os.listdir(DL)):
    p = os.path.join(DL, f)
    if not os.path.isfile(p) or not f.lower().endswith(IMG): continue
    if f[:1].isdigit() and len(f) > 12: continue          # skip camera-roll numeric dumps
    if f.lower().startswith(("screenshot", "img_", "media-")): unmapped.append(f); continue
    k = norm(f)
    if k in dests:
        try: shutil.copy(p, dests[k]); routed.append((f, os.path.relpath(dests[k], GAME)))
        except Exception as e: unmapped.append(f + " (copy err: %s)" % str(e)[:40])
    else:
        unmapped.append(f)

print("=== ROUTED %d ===" % len(routed))
for a, b in routed: print("  %-26s -> %s" % (a, b))
print("=== UNMAPPED %d (no exact game-asset name match -- need your call) ===" % len(unmapped))
for u in unmapped: print("  " + u)
