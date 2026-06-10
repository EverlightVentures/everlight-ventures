# Seedance PoC -- $BCARDD animated unit (walk + fire)
**Goal:** one 4-5s clip that proves the animated-unit pipeline + nails $BCARDD as the real white Dogo Argentino. ~$0.50 on Seedance 2.0.

## Run it (Seedance 2.0, IMAGE-TO-VIDEO)
- **Reference image (REQUIRED):** `01_BUSINESSES/Everlight_Ventures/Everlight_Crypto/Copy of Official $BCARDD.png` -- this locks the character to your actual dog (white Dogo Argentino / Argentine Mastiff). Upload it as the reference/init image so Seedance animates THAT dog, not a guess.
- **Length:** 4-5s. **Loopable.** **No camera move** (locked side view).
- **Background:** PLAIN FLAT SOLID mid-grey, no scenery -- so e5 can cut it out cleanly into a transparent sprite sheet.

## Prompt (paste)
```
Using the reference image as the exact character: a pure white Dogo Argentino
(Argentine Mastiff) warlord, scarred, thin gold crown, matte-black combat harness
with gold trim -- the same dog as the reference. Animate a clean SIDE-VIEW game
sprite loop, full body in frame, centered: the dog pilots a crowned matte-black
armored war-rig with gold trim (the Crownbreaker) moving left-to-right at a steady
charge. The wheels/tires visibly spin, the suspension bobs, the dog leans and
steers, and a roof cannon fires a missile with a muzzle-flash and recoil. Steady
forward motion, looping seamlessly. PLAIN SOLID mid-grey studio background, even
lighting, hyper-real PBR, crisp edges. No text, no watermark, no UI, no camera
movement, no rum bottle.
```

## What happens after you generate it
1. You send me the MP4 (drop it in `ecosystem/art/seedance_poc/`).
2. On **e5-mother** (the phone cannot ffmpeg): extract ~12 frames -> remove the grey background per frame -> assemble a transparent **sprite sheet** PNG.
3. I wire the game to FLIPBOOK that sheet for $BCARDD (cycle frames as he moves) -> he actually walks + fires on the board, performantly. Fallback stays the static portrait, then the shape.
4. You judge it. If it looks good -> we fund one full faction (12) the same way. If not -> we tune the prompt/pipeline before spending more.

## Notes
- Side-view + solid bg are the two things that make a clip turn into a clean game sprite. Cinematic/3-4 angle + scenery = hard to cut out.
- This is the proof. Do NOT batch a category until this one looks right in-game.
