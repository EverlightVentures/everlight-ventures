"""
personality_synth -- the psychological layer.

Takes the raw findings from every investigator and extracts:
  - interests   (cars, fitness, religion, art, gaming, etc.)
  - life_events (recent divorce, new baby, move, retirement, death in family)
  - profession  (job title + employer if found)
  - comm_style  (formal vs casual; signals to match register)
  - financial   (multi-property owner, bankruptcy, foreclosure, business filings)
  - red_flags   (lawsuits, complaints, criminal records)
  - signals_for_pitch  (compact dict the pitch generator consumes)

Per Operator Truth: every tag has a SOURCE -- which finding produced it.
No "the AI guesses" without a citable extractor.
"""
from __future__ import annotations

import re
from typing import Any

# Interest taxonomy -- keyword -> category. Easily extended.
# Each keyword is matched with word boundaries against the lowercased finding text.
INTEREST_KEYWORDS = {
    # Vehicles
    "Cars / Vehicles":     ["car", "cars", "auto", "vehicle", "mustang", "tesla", "truck", "harley",
                              "motorcycle", "bike", "garage", "engine", "mechanic", "classiccar",
                              "carshow", "racing", "porsche", "ferrari", "lamborghini", "supercar",
                              "rv", "camper", "boat", "yacht", "atv"],
    # Sports / Fitness
    "Sports & Fitness":    ["gym", "fitness", "marathon", "yoga", "crossfit", "lifting", "boxing",
                              "mma", "basketball", "football", "soccer", "tennis", "golf", "surfing",
                              "running", "cycling", "outdoor", "hiking", "climbing", "kayak", "ski",
                              "snowboard", "skateboard", "powerlifting"],
    # Faith / Community
    "Faith / Community":   ["church", "pastor", "ministry", "missionary", "faith", "christ", "jesus",
                              "synagogue", "rabbi", "mosque", "imam", "buddhist", "meditation",
                              "volunteer", "rotary", "lions club", "kiwanis", "elk", "mason",
                              "freemason", "scout", "scouts"],
    # Family
    "Family / Parenting":  ["mom", "dad", "father", "mother", "kids", "children", "son", "daughter",
                              "family", "married", "wife", "husband", "grandparent", "baby",
                              "toddler", "newborn", "homeschool"],
    # Career / Business
    "Entrepreneurship":    ["founder", "ceo", "entrepreneur", "startup", "business owner", "smallbiz",
                              "self-employed", "consultant", "freelance", "investor", "angel"],
    "Tech / Engineering":  ["developer", "engineer", "software", "coding", "python", "javascript",
                              "github", "open source", "ml", "ai engineer", "devops", "kubernetes",
                              "rust", "golang", "react", "fullstack"],
    # Arts
    "Art / Music":         ["artist", "music", "musician", "guitar", "piano", "vinyl", "concert",
                              "studio", "painting", "photography", "creative", "vinyl records",
                              "jazz", "blues", "hip hop", "hip-hop", "edm", "classical music"],
    # === FOOD / DIET (NEW, EXPANDED) ===
    "Foodie / Restaurants": ["foodie", "restaurant", "chef", "cuisine", "tasting menu",
                               "michelin", "yelp elite", "dinner club", "supper club"],
    "Diet / Lifestyle":    ["vegan", "vegetarian", "plant-based", "keto", "paleo", "carnivore",
                              "gluten-free", "celiac", "halal", "kosher", "intermittent fasting",
                              "whole30", "mediterranean diet", "carnivore diet"],
    "Drinks / Beverage":   ["coffee", "espresso", "barista", "wine", "sommelier", "winery",
                              "brewery", "craft beer", "ipa", "whiskey", "bourbon", "scotch",
                              "tequila", "mezcal", "cocktail", "mixologist"],
    # === TRAVEL (NEW) ===
    "Travel / Adventure":  ["travel", "wanderlust", "passport", "expat", "digital nomad",
                              "backpacking", "cruise", "european trip", "africa", "asia tour",
                              "south america", "bucket list"],
    # === HEALTH / WELLNESS (expanded, careful with sensitivity) ===
    "Health / Wellness":   ["wellness", "nutrition", "diet", "biohacking", "longevity",
                              "supplement", "mental health", "therapy", "anxiety", "depression",
                              "meditation app", "mindfulness", "self-care"],
    "Recovery / Sobriety": ["sober", "sobriety", "in recovery", "12 step", "12-step", "alcoholic",
                              "addict in recovery", "narcotics anonymous", "alcoholics anonymous",
                              "smart recovery", "sober living"],
    "Medical / Patient":   ["diabetic", "diabetes", "cancer survivor", "stage iv", "stage 4",
                              "stage iii", "rheumatoid", "lupus", "chronic illness", "ms warrior",
                              "fibromyalgia", "caregiver"],
    # === POLITICS / CAUSES (expanded) ===
    "Causes / Politics":   ["activist", "vote", "campaign", "veterans", "vfw", "rotary", "civic",
                              "nonprofit", "501c3", "foundation", "donor", "philanthrop",
                              "fundraiser", "advocacy"],
    "Politics / Left":     ["democrat", "progressive", "blue wave", "actblue", "biden", "obama"],
    "Politics / Right":    ["republican", "maga", "conservative", "trump", "gop", "winred"],
    # === HOBBIES (NEW) ===
    "Gaming":              ["gamer", "gaming", "twitch", "esports", "ps5", "xbox", "nintendo",
                              "steam", "league of legends", "fortnite", "warzone", "valorant"],
    "Reading / Books":     ["reader", "bookworm", "goodreads", "kindle", "audible", "book club",
                              "literary"],
    "Film / TV":           ["cinephile", "letterboxd", "imdb top", "criterion", "movie buff",
                              "binge watch", "netflix", "hbo", "marvel fan", "star wars fan"],
    "Crafts / DIY":        ["diy", "woodworking", "knitting", "crochet", "sewing", "quilting",
                              "ceramic", "pottery", "metalwork", "etsy seller"],
    "Hunting / Fishing":   ["hunting", "hunter", "deer season", "elk hunt", "fishing", "angler",
                              "fly fishing", "bass fishing", "ducks unlimited"],
    "Gardening":           ["gardener", "garden", "permaculture", "heirloom", "homestead",
                              "homesteading", "chickens", "honeybee"],
    # Real Estate
    "Real Estate":         ["realtor", "investor", "landlord", "tenant", "property", "rental",
                              "rehab", "flipper", "broker"],
    # Pets
    "Pets / Animals":      ["dog", "dogs", "cat", "cats", "puppy", "kitten", "pet", "rescue",
                              "vet", "horse", "equestrian", "rabbit"],
    # === CONSUMPTION PATTERNS (NEW) ===
    "Luxury / Fashion":    ["gucci", "louis vuitton", "prada", "rolex", "patek", "supreme",
                              "designer", "high fashion", "couture", "fashion week"],
    "Frugal / Budget":     ["thrift", "thrifting", "couponing", "frugal", "fire movement",
                              "financial independence", "early retirement", "dave ramsey",
                              "ramit"],
    # === EDUCATION / CREDENTIALS (NEW) ===
    "Higher Education":    ["phd", "doctorate", "professor", "academic", "researcher",
                              "ivy league", "harvard", "stanford", "mit"],
    "Veteran / Military":  ["veteran", "active duty", "served in", "us army", "navy", "marines",
                              "air force", "coast guard", "national guard", "deployed"],
}

# Life events -- keyword -> event tag. Pulled from news/obits/court mentions.
LIFE_EVENT_PATTERNS = [
    ("recently_divorced",     r"\b(divorce|divorced|filed for divorce|separated)\b"),
    ("recently_widowed",      r"\b(widow|widower|widowed|passed away|deceased)\b"),
    ("recent_birth_in_family", r"\b(welcomes? .{0,15} baby|new baby|gave birth|grand(child|son|daughter))\b"),
    ("recent_marriage",       r"\b(wedding|married|engaged|engagement)\b"),
    ("recent_move",           r"\b(moved to|relocated|new home|just moved)\b"),
    ("recent_retirement",     r"\b(retir(ed|ing|ement)|step down|stepped down)\b"),
    ("recent_job_change",     r"\b(new role|new position|started|hired|joined|laid off|let go)\b"),
    ("recent_death_in_family", r"\b(loss of|in memory of|in memoriam|memorial service)\b"),
    ("foreclosure",           r"\b(foreclos|notice of default|lis pendens|trustee sale)\b"),
    ("bankruptcy",            r"\b(bankruptcy|chapter 7|chapter 13|chapter 11)\b"),
    ("lawsuit",               r"\b(lawsuit|sued|plaintiff|defendant|civil suit)\b"),
    ("award_recognition",     r"\b(award|recognized|honored|featured|spotlight)\b"),
]

# Communication style cues
FORMAL_CUES = ["dr.", "esq", "mba", "phd", "professor", "attorney", "ceo", "founder", "president"]
CASUAL_CUES = ["lol", "lmao", "bro", "vibes", "fam", "literally", "fire", "🔥", "yo"]


def _normalize_text(s: str) -> str:
    return (s or "").lower()


def synthesize_personality(findings_all: list[dict]) -> dict:
    """
    findings_all: every finding across every investigator (the orchestrator's
    full `results` list, flattened).
    Returns a structured personality profile keyed by source citations.
    """
    interests: dict[str, list[dict]] = {}  # category -> [{keyword, source_label, source_url}]
    life_events: dict[str, list[dict]] = {}  # event_tag -> citations
    profession_hits: list[dict] = []
    financial: list[dict] = []
    red_flags: list[dict] = []
    formal_score = 0
    casual_score = 0
    sources_consulted: set = set()

    for inv in findings_all or []:
        if not isinstance(inv, dict): continue
        inv_id = inv.get("investigator_id", "")
        inv_name = inv.get("investigator", inv_id)
        for f in inv.get("findings", []):
            text = _normalize_text(f.get("value", "") + " " + f.get("label", ""))
            url = f.get("url", "")
            label = f.get("label", "")
            sources_consulted.add(inv_id)

            # Interest tagging
            for cat, keywords in INTEREST_KEYWORDS.items():
                for kw in keywords:
                    if re.search(rf"\b{re.escape(kw.lower())}\b", text):
                        interests.setdefault(cat, []).append({
                            "keyword": kw,
                            "source": inv_name,
                            "source_label": label,
                            "source_url": url,
                        })
                        break  # one hit per category per finding

            # Life events
            for tag, pat in LIFE_EVENT_PATTERNS:
                if re.search(pat, text, re.I):
                    life_events.setdefault(tag, []).append({
                        "source": inv_name,
                        "source_label": label,
                        "source_url": url,
                        "snippet": f.get("value", "")[:140],
                    })

            # Profession (job_title from social_bio_scraper / sec_edgar / opencorporates)
            if any(k in label.lower() for k in ("role", "officer", "title", "ceo", "founder")):
                profession_hits.append({
                    "value": f.get("value", ""),
                    "source": inv_name,
                    "url": url,
                })

            # Financial
            if any(k in text for k in ("bankruptcy", "foreclos", "tax lien", "judgment")):
                financial.append({
                    "kind": "distress_signal",
                    "snippet": f.get("value", "")[:160],
                    "source": inv_name, "url": url,
                })
            elif any(k in text for k in ("multi-property", "second home", "investment property",
                                            "rental property", "llc owner")):
                financial.append({
                    "kind": "multi_property_signal",
                    "snippet": f.get("value", "")[:160],
                    "source": inv_name, "url": url,
                })

            # Red flags
            if any(k in text for k in ("indictment", "convicted", "arrested", "lawsuit", "fraud",
                                          "scam", "complaint")):
                red_flags.append({
                    "snippet": f.get("value", "")[:160],
                    "source": inv_name, "url": url,
                })

            # Comm style
            for cue in FORMAL_CUES:
                if cue in text: formal_score += 1
            for cue in CASUAL_CUES:
                if cue in text: casual_score += 1

    # Dedupe interests -- one citation per category, top hit wins
    interests_final = {}
    for cat, hits in interests.items():
        seen = set(); uniq = []
        for h in hits:
            k = (h["keyword"], h["source_url"])
            if k in seen: continue
            seen.add(k); uniq.append(h)
        interests_final[cat] = uniq[:5]

    # Comm style verdict
    if formal_score >= 2 and formal_score > casual_score:
        comm_style = "formal"
    elif casual_score >= 2 and casual_score > formal_score:
        comm_style = "casual"
    else:
        comm_style = "neutral"

    return {
        "interests": interests_final,
        "life_events": life_events,
        "profession": profession_hits[:3],
        "financial_signals": financial[:5],
        "red_flags": red_flags[:5],
        "communication_style": comm_style,
        "communication_evidence": {"formal_score": formal_score, "casual_score": casual_score},
        "sources_consulted": sorted(sources_consulted),
    }
