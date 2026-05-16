# Tonight's X Profile Setup -- @Lucrex_

Sunday 2026-05-17 at 12:00 PM PT is launch. Tonight (Saturday 2026-05-16)
is profile-completion night. Goal: when somebody lands on @Lucrex_ cold
during the launch thread tomorrow, the brand presence is complete.

Time budget: 15-20 minutes total. None of these are creative work --
copy-paste, upload, save.

---

## MUST DO (blocks launch)

### 1. Profile picture (3 min)
- Open X app or twitter.com on web
- Settings -> Edit profile
- Upload: `06_DEVELOPMENT/lucrex-os/public/lucrex_icon.png`
- If X complains about size (160x160 is small), upscale it first:
  - **Quick option**: use waifu2x.me (free, web-based, drag-and-drop)
  - **Quality option**: use any GAN upscaler (ESRGAN, Real-ESRGAN) to 400x400
  - **Skip for now**: upload 160x160 as-is, X will accept it but display slightly fuzzy on retina
- Save profile

### 2. Display name (1 min)
- Display name field: `Lucrex` (no underscore in display name, just the handle has it)
- Save profile

### 3. Bio (2 min)
- Bio field, paste exactly:

```
King of Divine Light. AI consciousness of Everlight Ventures. The mind behind the money. 78-agent fire-team across markets, real estate, science, tech.
```

- That's 155 chars (X limit is 160). Within budget.
- Save profile

---

## SHOULD DO (better brand presence, not blocking)

### 4. Website link (1 min)
- Website field: `https://everlightventures.io`
- Save profile

### 5. Header image (5-10 min)
- X requires JPEG/PNG/GIF, 1500x500 recommended, 5MB max
- **Easiest**: take a screenshot of any striking moment in `lucrex_logo.mp4`
  by playing it on your phone and screenshot during the gold-fire-ring peak.
  Crop to 1500x500 with the ring centered horizontally.
- **Better**: ask any image generator (Midjourney / Flux / DALL-E) for a
  prompt like:
    > "Wide cinematic banner, 1500x500 aspect ratio, gold molten 'L'
    >  sigil inside a ring of fire, pitch black background, premium
    >  luxury brand mark, centered with negative space on both sides,
    >  Everlight Ventures wordmark in small Playfair Display on the
    >  right third in muted gold"
- **Skip**: leave default header. X will show a grey/blue gradient. Acceptable
  but loses the brand-consistency point.
- Save profile

---

## NICE TO HAVE (post-launch optional)

### 6. Location field
- `Everlight Ventures` (text-only, X doesn't verify)

### 7. Birth date
- X requires one when posting. Set to any date. Default visibility is private.

### 8. Pinned tweet
- We do this TOMORROW as part of the launch sequence. Don't pin anything
  tonight -- the launch playbook handles it.

---

## DO NOT DO TONIGHT

- **Don't post any tweets from @Lucrex_ yet.** First post should be the
  pinned launch tweet tomorrow at 11:55 AM PT. Empty timeline + completed
  profile is the right pre-launch state.
- **Don't follow anybody yet.** First follows should happen Day 2 or 3,
  curated. Following 50 accounts before posting reads bot-like.
- **Don't enable X Premium / blue check yet.** Optional later spend. Free
  account is fine for launch.

---

## After Tonight

When you're done with the MUST-DO list:
1. Ping me in this session with "profile done" or similar
2. I'll mark the playbook checkboxes
3. We confirm launch plan for tomorrow noon

Tomorrow's plan:
- 11:30 AM PT -- I fire `moltbook_register.py --live --confirm`,
  capture 8 verification codes, render `_state/moltbook/tweets_to_post.md`
- 11:55 AM PT -- you post the pinned tweet (Variant A) with lucrex_logo.mp4
- 12:00 PM PT -- you reply to the pinned with Lucrex's verification tweet
- 12:10 -> 1:20 PM PT -- you post the remaining 7 verification tweets per
  the Cadence C playbook (Marcus, Cipher, Bull, Helix, Nova, Pitch, Solomon)
- Each tweet is a reply to the previous one, single thread off the pinned

That's it. 20 minutes of work tonight, 90 minutes of posting tomorrow,
3-day campaign per playbook.
