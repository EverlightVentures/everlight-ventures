# Solano Live Desk -- Key Setup (what to get, where, what to give me)

All of these are FREE unless marked. None are required for what already works
(map, incidents, threat alerts, air, rail, earthquakes, cameras). They ADD layers.
When you have a key, paste it to me and I wire the layer + verify it live.

---

## 1. 511.org token -- buses, BART, Amtrak real-time (FREE, ~2 min)
Adds live public-transit vehicle positions across the 9-county Bay Area.
1. Go to: https://511.org/open-data/token
2. Fill the short form (name, email; project = "personal situational awareness").
3. Token arrives by email instantly.
4. Give me: the token string.
-> I set SLD_511_TOKEN and add a Transit toggle (buses/BART) to the map.

## 2. Windy Webcams API key -- public webcams anywhere (FREE, ~3 min)
The legal "look around" layer (fills gaps where highway cams don't reach).
1. Go to: https://api.windy.com/keys  (make a free Windy account if needed)
2. Create a key of type "Webcams API" (free tier).
3. Give me: the key string.
-> I set SLD_WINDY_KEY and show nearby public webcams in the detail panel + map.

## 3. NASA FIRMS map key -- wildfire hotspots (FREE, instant)
Satellite fire detections; pairs with CAL FIRE perimeters (no key).
1. Go to: https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. Enter your email -> key emailed instantly.
3. Give me: the MAP_KEY string.
-> I set SLD_FIRMS_KEY and add wildfire hotspots to the hazard layer.

## 4. Broadcastify Premium -- the audio -> transcription bridge (PAID ~$30/yr)
This is the CHEAP consumer tier, NOT the $2,500/mo enterprise API. It unlocks the
Solano "Calls" archive (per-call audio + metadata) that we transcribe with Whisper
on e5 -> live scanner incidents drop on your map. Personal use only (no republishing).
1. Go to: https://www.broadcastify.com/premium/
2. Buy Premium ($15 / 6 months, or $30 / year).
3. Confirm the Solano Calls node is in your account:
   https://www.broadcastify.com/calls/playlists/?uuid=678e43aa-0f3c-11f1-bb32-0ef97433b5f9
4. Tell me it's active (we set up the Calls pull together; I do NOT need your password
   in chat -- we store it in the vault).
-> I build the Whisper transcription + geocode pipeline (Phase 4).
FREE-FOREVER ALTERNATIVE: a standalone RTL-SDR node (~$40 one-time) you never carry
-- fully legal own-receiver recording. Your call, not needed until Phase 4.

## 5. Cloudflare AI token -- custom map icons (you said I already have it)
Optional polish: real police/fire/plane/train/hazard icons instead of emoji.
-> I generate them with the CF AI worker when we do a visual polish pass. Emoji is
fine for now, so this is low priority.

---

## Summary: what to hand me (in any order, whenever)
- [ ] 511 token (free)
- [ ] Windy Webcams key (free)
- [ ] NASA FIRMS map key (free)
- [ ] Broadcastify Premium purchased + "it's active" (optional, ~$30/yr)
- CF AI token: already available -> I use it for icons at polish time.
