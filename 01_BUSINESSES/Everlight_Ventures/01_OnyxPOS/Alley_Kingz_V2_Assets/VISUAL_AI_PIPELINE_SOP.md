# ALLEY KINGZ VISUAL AI PIPELINE -- SOP v1.0
*2026-03-01 | Automation Architect + Chief Operator*

---

## OVERVIEW

This SOP governs the end-to-end process for generating, reviewing, and deploying
hyper-real visual assets for Alley Kingz using the Gemini Vision AI pipeline.

**Pipeline stages:**
```
Reference Image  ->  Gemini Vision  ->  Refined Prompt  ->  AI Generation  ->  Art Review  ->  Performance Check  ->  Repo
```

---

## STAGE 1: REFERENCE GATHERING

**Owned by:** Chief Operator (you) / Art Director

1. Drop reference screenshots into: `07_Reference_Images/`
   - Good references: Clash Royale cards, Brawl Stars characters, NBA TopShot moments,
     Street Fighter 6 character renders, Uncharted 4 environmental screenshots
   - Minimum 10 references before first generation run
2. Organize by asset type subfolder: `characters/`, `cards/`, `environments/`, `shop_ui/`
3. Name files descriptively: `clash_royale_legendary_card_example.png`

---

## STAGE 2: GEMINI IMAGE-TO-PROMPT EXTRACTION

**Owned by:** Workflow Builder / Automation

**Run the pipeline script:**
```bash
# Single image
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/art_generator_v2.py \
  --image 07_Reference_Images/clash_royale_legendary_card_example.png \
  --style legendary_card

# Batch directory
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/art_generator_v2.py \
  --input 07_Reference_Images/characters/ \
  --style character

# Test run (no API call)
python3 art_generator_v2.py --image test.png --style character --dry-run
```

**Requires:**
```bash
export GEMINI_API_KEY=your_key_here
pip install google-generativeai
```

**Output:** Prompts saved to `06_AI_Prompts/Generated/` + entry in `content_pack.json`

---

## STAGE 3: AI GENERATION

**Owned by:** Chief Operator / Outsource Lead

Take the approved prompts from `06_AI_Prompts/Reviewed/` and run them in one of:

**Option A: Midjourney (recommended for quality)**
- Paste prompt into Discord Midjourney bot
- Append negative prompt: `low quality, blurry, 2D sprite, pixel art, flat shading, cartoon, anime, oversaturated, watermark, text, signature`
- Use `--ar 2:3` for card/character art, `--ar 16:9` for map art
- Use `--q 2` for final quality, `--q 1` for drafts

**Option B: SDXL via ComfyUI**
- Load prompt into ComfyUI positive node
- Negative: same as above
- Sampler: DPM++ 2M Karras, steps 30-40, CFG 7.0
- Checkpoint: Realistic Vision V6 or Juggernaut XL

**Option C: Outsource Studio Brief**
- Export Prompt Bible section + Art Bible + reference images
- Package to `08_Outsource_Briefs/` as ZIP
- Studios: Kevuru Games, RocketBrush Studio
- Budget: $5K-$10K Phase 1

**Output:** Raw generated images saved to appropriate asset subfolder with filename format:
`YYYY-MM-DD_AssetType_Name_HyperReal_V1.png`
Example: `2026-03-05_Character_AlleyKing_HyperReal_V1.png`

---

## STAGE 4: ART REVIEW GATE

**Owned by:** Chief Operator

Review each generated asset against ART_BIBLE.md. Check:

| Check | Pass Criteria |
|-------|--------------|
| Color palette | Contains at least 2 of the 5 primary colors |
| Lighting | Key + fill + rim visible; not flat |
| Proportions | Heroic scale; readable at thumbnail |
| Cultural authenticity | Streetwear-accurate; not generic |
| PBR appearance | Materials look physical: leather creases, skin SSS |
| Silhouette | Instantly readable at 200x300px |
| Rarity cues | Border/glow matches rarity tier system |

**Decision:**
- PASS -> Move to `06_AI_Prompts/Reviewed/`, update `content_pack.json` status to `art_review`
- FAIL -> Return to Stage 3 with refined prompt; log failure reason in content_pack.json

**Escalation:** If 3 consecutive AI generations fail for the same asset, escalate to outsource brief.

---

## STAGE 5: PERFORMANCE CHECK

**Owned by:** Engineering / Automation

Before any asset enters the game:

1. **Texture compression**
   - iOS: ASTC 6x6 compression
   - Android: ETC2 compression
   - Max 2K for cards/characters, 1K for UI
2. **Poly count verification**
   - Card character: max 45K
   - In-game character: max 20K
   - Map scene: max 50K total
3. **Device benchmark**
   - Test on Snapdragon 665 device (or emulator profile)
   - Must maintain 60FPS during card reveal animation
4. **Update manifest**
   - Update `content_pack.json` status to `approved`
   - Add `pbr_maps` and `lod_levels` fields

---

## STAGE 6: REPO + DEPLOYMENT

1. Move final compressed asset to appropriate folder:
   - Characters: `01_Characters/HyperReal/`
   - Cards: `02_Cards/{rarity}/`
   - Maps: `03_Areas_Maps/`
   - Shop: `04_Shop_UI/`
   - Marketing: `05_Marketing/`
2. File naming: `YYYY-MM-DD_AssetType_Name_HyperReal_V{N}.{ext}`
3. Update `content_pack.json` with final asset path
4. For in-game deployment: Unity Addressables bundle (see engineering handoff)
5. For marketing assets: upload to `05_Marketing/AppStore_Screenshots/` + social folders

---

## SPRINT CADENCE

- **Art Review sprint:** Every Tuesday
- **Generation batch:** Wednesdays (batch 10 prompts minimum)
- **Performance checks:** Fridays before deployment

---

## RISK LOG

| Risk | Mitigation |
|------|-----------|
| AI assets look incoherent | Art Bible review gate mandatory; reject without it |
| OOM crashes from large textures | ASTC/ETC2 mandatory; no raw 4K in game builds |
| Outsource delivers wrong aesthetic | Share Art Bible + Prompt Bible + references in brief |
| App store update lag | Unity Addressables for in-game; store screenshots updated separately |
| "AI slop" -- uncanny or generic | 3 fail = escalate to outsource, not retry loop |

---

*SOP v1.0 -- Review quarterly or when Art Bible is updated.*
