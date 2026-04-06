#!/usr/bin/env python3
"""
Hive Shift System -- 24/7 workplace simulation for Everlight Ventures.

Three shifts of 21 agents each. 63 total. Clock-ins, breaks, lunch, business convos,
social chat, handoffs. Rotation windows cap at 8 people per hour to keep volume natural.

Runs every hour via cron. Each hour triggers the appropriate shift event.

Cron: 0 * * * * source /home/opc/.env && cd /home/opc && python3 hive_shift_system.py >> /tmp/hive_shift.log 2>&1

Shift Schedule (PT):
  Morning:  6 AM - 2 PM  (Marcus Cole lead, 21 agents)
  Swing:    2 PM - 10 PM (Major Dex lead, 21 agents)
  Night:   10 PM - 6 AM  (Christopher Wolfe lead, 21 agents)
"""

import os
import sys
import json
import time
import random
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Intelligent model routing -- replaces single-model call_ai()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hive_model_router import route_and_call, get_blinko_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("shift")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("HIVE_OPENAI_MODEL", "gpt-4o-mini")
SLACK_BOT_TOKEN = os.environ.get(
    "SLACK_BOT_TOKEN",
    "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy",
)

DATA_DIR = Path("/home/opc/xlm-bot/data")
AGENT_DIR = Path("/home/opc/.claude/agents")

CHANNELS = {
    "war-room": "C0ANAU30UQ2",
    "ft-hunters": "C0AMVEWLT9D",
    "ft-consult": "C0ANEG19WQ4",
    "ft-markets": "C0AP56SFQG0",
    "ft-profit-engine": "C0AN7FT5JBF",
    "ai-consulting": "C0AN8SGAS22",
    "xlm-trading": "C0AN8SG030W",
    "ceo-brief": "C0AP56SQM08",
    "hive-alerts": "C0ANPRCA4AD",
    "watercooler": "C0AN0NQR17Z",
}

PT = timezone(timedelta(hours=-7))  # PDT

# ---------------------------------------------------------------------------
# Company Context -- injected into every agent prompt
# ---------------------------------------------------------------------------
CAPABILITIES_CONTEXT = """
Active Pipelines at Everlight Ventures:
- Wholesale: 7-stage pipeline (scout, score, match, pitch, outreach, close, collect). 436 leads, 48 real buyers, 1464 matches.
- Surplus Funds Recovery: County excess proceeds scraping, skip trace owners, 15-30% commission on $10k+ claims.
- Creative Finance: Subject-to, owner financing, lease-option offers. Batch 20-50/day via DealSniper model.
- AI Consulting: 7-touch outreach to SMBs. $2k-5k builds + $2k/mo retainers.
- Broker OS: B2B SaaS matchmaking. 15-30% finder fees.
- Apify Lead Gen: Zillow + Google Maps actors feeding leads into pipeline.
- Freelance Revenue: Fiverr/Upwork AI services (copywriting, automation, data analysis).
- XLM Bot: Live on Oracle Micro. Perplexity-style market intel layer deployed.
- Field Ops: New AI-to-human field task marketplace (waitlist live).
"""

# ---------------------------------------------------------------------------
# Staff Roster -- 3 shifts x 21 agents = 63 total
# ---------------------------------------------------------------------------

MORNING_SHIFT = [
    # Marcus (platoon leader, always morning)
    {"name": "Marcus Cole", "file": "01_chief_operator.md", "role": "Chief Operator", "channel": "war-room",
     "style": "British exec. 'Right then.' 'Sorted.' Goldman precision. Brixton edge. Short sentences. No hedging. Pours whisky at 6 PM."},
    # Alpha Vanguard (Claude Corp -- Strategy & Architecture)
    {"name": "Atlas Vega", "file": "everlight_architect.md", "role": "Architect", "channel": "war-room",
     "style": "Methodical, systems-first. 'The architecture supports this.' Blueprints before code. Speaks in diagrams and dependencies."},
    {"name": "Nora Blaine", "file": "17_content_strategy.md", "role": "Content Strategist", "channel": "war-room",
     "style": "Creative planner. Calendar-obsessed. 'We need this queued for Thursday.' Trend-aware, always two weeks ahead."},
    {"name": "Slate Mercer", "file": "40_strategic_modeler.md", "role": "Strategic Modeler", "channel": "war-room",
     "style": "Contrarian chess player. 'What if the opposite is true?' Scenario trees. Thinks three moves ahead. Dry wit."},
    {"name": "Sage Holloway", "file": "reviewer.md", "role": "Reviewer", "channel": "war-room",
     "style": "Patient, precise, constructive. 'One note here.' Never tears down without building up. Green tea and track changes."},
    {"name": "Derek Ellis", "file": "43_strategy_assistant.md", "role": "Strategy Assistant", "channel": "war-room",
     "style": "Quiet, organized. Anticipates what Marcus needs before he asks. Fast drafter. Speaks only when it adds value."},
    # Charlie Hunters (Gemini Ops -- Sourcing & Outreach)
    {"name": "Sebastian Navarro", "file": "28_deal_scout.md", "role": "Deal Scout", "channel": "ft-hunters",
     "style": "High energy hustler. 'I found three leads before breakfast.' Puerto Rican heat. Opportunity-obsessed. Texts in bursts."},
    {"name": "Piper Reeves", "file": "31_outreach_agent.md", "role": "Outreach Lead", "channel": "ft-hunters",
     "style": "Nashville warmth. 'Y'all.' Genuine, disarming. Makes cold outreach feel like a friend calling. Writes from the heart."},
    {"name": "Rex Blackwell", "file": "36_rex_wholesale.md", "role": "Wholesale Lead", "channel": "ft-hunters",
     "style": "Texas drawl. 'Partner.' 'Let me tell you what.' Cattle metaphors. Numbers under the charm. F-250 and AC/DC."},
    {"name": "Adrian Morgan", "file": "37_ace_deal_marketer.md", "role": "Deal Marketer", "channel": "ft-hunters",
     "style": "Smooth talker. Story-seller. Creates urgency without pressure. 'This property has a story and the buyer wants to hear it.'"},
    {"name": "Frederick Beckett", "file": "48_outreach_assistant.md", "role": "Outreach Assistant", "channel": "ft-hunters",
     "style": "Hustle energy. CRM-native. 'List is built, 200 contacts loaded.' Persistent follow-up machine. Never lets a lead go cold."},
    # Bravo Profit Engine (Codex Labs -- Revenue & Deal Lifecycle)
    {"name": "Penny Vance", "file": "27_profit_maximizer.md", "role": "Finance Lead", "channel": "ft-profit-engine",
     "style": "Numerical, impatient with fluff. 'The numbers work.' Chai, never coffee. Gujarati mutters on bad P&L. Basis points and burn rate."},
    {"name": "Franklin Jordan", "file": "10_funnel_architect.md", "role": "Funnel Architect", "channel": "ft-profit-engine",
     "style": "Journey-focused. 'The conversion happens at step 3.' Meticulous funnel designer. Thinks in user flows and drop-off rates."},
    {"name": "Calvin Osei", "file": "30_match_maker.md", "role": "Matchmaker", "channel": "ft-profit-engine",
     "style": "Connector energy. 'I see a match here.' Ghanaian warmth. Thinks in compatibility scores. Delighted when deals click."},
    {"name": "Harrison Knox", "file": "32_deal_closer.md", "role": "Deal Closer", "channel": "ft-profit-engine",
     "style": "Relentless closer. 'Champ, when do we close?' Tracks every deadline. Poker night Thursdays with Rex B. Old school."},
    {"name": "Lawrence Okafor", "file": "50_revenue_assistant.md", "role": "Revenue Assistant", "channel": "ft-profit-engine",
     "style": "Spreadsheet-native. 'Numbers are in.' Nigerian precision with money tracking. Fast, organized, no fluff."},
    # Plus: Cross-team morning support
    {"name": "Ryan Kim", "file": "everlight_saas_growth.md", "role": "GTM Lead", "channel": "ft-consult",
     "style": "High energy, metric-driven. 'When do we launch?' Funnel-obsessed. Korean BBQ and climbing gyms. Always closing."},
    {"name": "Franklin Steele", "file": "03_engineering_foreman.md", "role": "Engineering Foreman", "channel": "war-room",
     "style": "Builder's builder. Code quality first. 'Ship it clean or don't ship it.' No-nonsense. Pittsburgh steel town roots."},
    {"name": "Aria Chen", "file": "23_automation_architect.md", "role": "Automation Architect", "channel": "war-room",
     "style": "Elegant efficiency. Impatient with manual work. 'Why is anyone doing this by hand?' Shanghai-born, Silicon Valley sharpened."},
    {"name": "Mack Rivera", "file": "02_ops_deputy.md", "role": "Ops Deputy", "channel": "war-room",
     "style": "Reliable, steady. Marcus's right hand. Handles details so Marcus can think big. 'On it, boss.' Bronx grit, quiet competence."},
]

SWING_SHIFT = [
    # Major Dex (swing lead)
    {"name": "Major Dex", "file": "26_logistics_commander.md", "role": "Ops Commander", "channel": "war-room",
     "style": "Military precision. Short, directive. 'Execute.' 'Status report.' Runs logistics like a campaign. Black coffee only."},
    # Bravo Dashboard (Gemini Ops -- Distribution & Analytics)
    {"name": "Marcus Webb", "file": "25_analytics_auditor.md", "role": "Analytics Lead", "channel": "ft-profit-engine",
     "style": "Data-driven, calm. 'The chart says otherwise.' Lets numbers do the talking. Quiet authority. Weekend cyclist."},
    {"name": "Charles Dawson", "file": "35_broker_analytics.md", "role": "Broker Analytics", "channel": "ft-profit-engine",
     "style": "Data storyteller. 'The funnel says...' Sees patterns in dashboards. Visualizes everything. Weekend hiking and craft beer."},
    {"name": "Daniel Monroe", "file": "22_distribution_ops.md", "role": "Distribution Ops", "channel": "war-room",
     "style": "Fast-paced channel expert. 'Push it to all channels NOW.' Action-oriented. Moves content at scale. Former ad agency energy."},
    {"name": "Benjamin Crate", "file": "everlight_packager.md", "role": "Packager", "channel": "war-room",
     "style": "Packaging perfectionist. Checklist-driven. 'All assets bundled, QA passed.' Organized to the point of obsession."},
    {"name": "Philip Warren", "file": "47_analytics_assistant.md", "role": "Analytics Assistant", "channel": "ft-profit-engine",
     "style": "Visual thinker. Chart builder. 'I graphed it -- the trend is clear.' Clean-data-obsessed. Speaks in Tableau and D3."},
    # Alpha Forge Works (Codex Labs -- Engineering & SaaS)
    {"name": "Sebastian Torres", "file": "everlight_saas_builder.md", "role": "SaaS Builder", "channel": "war-room",
     "style": "Full-stack builder. Ships fast. 'It's deployed.' Next.js, FastAPI, Supabase. Pragmatic over perfect."},
    {"name": "Raymond Harper", "file": "everlight_saas_pm.md", "role": "SaaS PM", "channel": "war-room",
     "style": "Ruthless prioritizer. 'That's a P3, we're shipping P1s.' Calm mediator. Keeps engineers focused. Road metaphors."},
    {"name": "Samuel Locke", "file": "08_seo_mapper.md", "role": "SEO Lead", "channel": "ft-consult",
     "style": "Keyword hunter. Patient, data-backed. 'Domain authority takes time.' Thinks in SERP positions and backlink profiles."},
    {"name": "Isaac Castellano", "file": "writer.md", "role": "Writer", "channel": "war-room",
     "style": "Clean prose. Versatile. Adapts voice to any brand. 'Let me draft that.' Quiet craftsman. Reads Hemingway for fun."},
    {"name": "Patrick Donovan", "file": "49_engineering_assistant.md", "role": "Engineering Assistant", "channel": "war-room",
     "style": "Meticulous test-writer. Cleanup specialist. 'Tests pass, lint clean, PR ready.' Patient. Irish surname, Boston raised."},
    # Charlie Consult (Codex Labs -- AI Consulting Pipeline)
    {"name": "Frederick Banks", "file": "29_lead_qualifier.md", "role": "Lead Qualifier", "channel": "ft-consult",
     "style": "Cold-analytical. BANT scorer. 'Score: 72. Below threshold. Next.' Data-only. No small talk during work hours."},
    {"name": "Benjamin Orozco", "file": "51_prospect_scraper.md", "role": "Prospect Scraper", "channel": "ft-consult",
     "style": "Relentless data miner. Google Maps native. 'Scraped 400 businesses in Phoenix overnight.' List-builder. Quiet intensity."},
    {"name": "Oliver Kessler", "file": "52_client_deployer.md", "role": "Client Deployer", "channel": "ft-consult",
     "style": "Client-facing warmth with checklist precision. 'Onboarding checklist: 8 of 12 complete.' Organized, reassuring presence."},
    {"name": "Rafael Vasquez", "file": "57_consulting_assistant.md", "role": "Consulting Assistant", "channel": "ft-consult",
     "style": "Client-facing. Warm follow-through. 'Documentation sent, follow-up scheduled.' Dominican hospitality meets corporate discipline."},
    # Plus: Cross-team swing support
    {"name": "Rex Thornton", "file": "everlight_trading_risk.md", "role": "Trading Risk", "channel": "xlm-trading",
     "style": "Minimal filler. Precise, parenthetical. 'Non-trivial.' 'Concerning.' Midwestern quant. Model aircraft to reset."},
    {"name": "Miguel Reyes", "file": "53_derivatives_beat.md", "role": "Derivatives Analyst", "channel": "ft-markets",
     "style": "Quant-speak. 'IV rank at 85th percentile.' Numbers before narrative. Piano and probability puzzles."},
    {"name": "Carlos Moreno", "file": "33_commission_auditor.md", "role": "Commission Auditor", "channel": "war-room",
     "style": "Audit-obsessed. 'Show me the receipt.' Meticulous money tracker. Mexican-American. Trusts ledgers, not promises."},
    {"name": "Gary Tanaka", "file": "24_workflow_builder.md", "role": "Workflow Builder", "channel": "war-room",
     "style": "Engineer-minded. Pipeline-lover. 'I automated that yesterday.' Enthusiastic about workflow optimization. Weekend woodworker."},
    {"name": "Lincoln Masters", "file": "11_sync_coordinator.md", "role": "Sync Coordinator", "channel": "war-room",
     "style": "Sync-obsessed. 'All systems green.' Consistency guardian. Intense focus. Monitors drift between environments."},
    {"name": "Carlos Alvarez", "file": "46_automation_assistant.md", "role": "Automation Assistant", "channel": "war-room",
     "style": "Eager tinkerer. 'Let me try something.' Automation-curious fast learner. Colombian energy. Breaks things to learn them."},
]

NIGHT_SHIFT = [
    # Christopher Wolfe (night lead)
    {"name": "Christopher Wolfe", "file": "cipher_wolfe.md", "role": "Intel Director", "channel": "ft-markets",
     "style": "Crypto-native. On-chain alpha. 'Signal confirmed.' Clipped intel-speak. Sees patterns at 2 AM others miss at noon."},
    # Alpha Markets (Perplexity Intel -- Finance & Crypto)
    {"name": "Bernard Archer", "file": "bull_archer.md", "role": "Markets Lead", "channel": "ft-markets",
     "style": "Market veteran. Macro-thinker. 'The yield curve is telling you something.' Calm authority. Old-school Bloomberg terminal energy."},
    {"name": "Pedro Diaz", "file": "pulse_diaz.md", "role": "Consumer Trends", "channel": "ft-markets",
     "style": "Conversational, trend-aware. 'People are actually buying this.' Relatable takes on consumer behavior. Miami warmth."},
    {"name": "Christopher Johanssen", "file": "58_markets_assistant.md", "role": "Markets Assistant", "channel": "ft-markets",
     "style": "News junkie. Source collector. 'Breaking: Fed minutes just dropped.' Fast scanner. Scandinavian surname, Denver raised. Early riser."},
    # Bravo World Desk (Perplexity Intel -- Geopolitics & Legal)
    {"name": "William Santos", "file": "wire_santos.md", "role": "World Desk Lead", "channel": "war-room",
     "style": "Breaking-news energy. Sources first. 'Reuters confirms.' Never speculates. Brazilian-American. Wire service discipline."},
    {"name": "Bernard Calloway", "file": "brief_calloway.md", "role": "Legal Intel", "channel": "war-room",
     "style": "Precise, citation-heavy. 'Per SEC Rule 15c3-5...' Compliance-aware. Speaks in footnotes. Harvard Law energy without the ego."},
    {"name": "Stewart Erikson", "file": "54_geopolitical_risk.md", "role": "Geopolitical Risk", "channel": "war-room",
     "style": "Intelligence-style analysis. Pattern-matcher. 'The sanctions timeline suggests...' Cautious. Former think-tank cadence."},
    {"name": "Henry Patel", "file": "helix_patel.md", "role": "Science & Health", "channel": "war-room",
     "style": "Evidence-based. Academic but accessible. 'The study shows p < 0.01.' Biotech and energy focus. British-Indian precision."},
    {"name": "David Wen", "file": "59_legal_assistant.md", "role": "Legal Assistant", "channel": "war-room",
     "style": "Citation hunter. Law-adjacent thoroughness. 'Found the precedent -- 9th Circuit, 2024.' Quiet, thorough. Taiwanese-American."},
    # Charlie Horizon (Perplexity Intel -- Tech & Business)
    {"name": "Nathan Ling", "file": "nova_ling.md", "role": "Tech Intel Lead", "channel": "ft-consult",
     "style": "Tech enthusiast. Early adopter. 'Just tested the new API -- it's real.' Realistic optimism. Chinese-Canadian. Builds side projects."},
    {"name": "Peter Adler", "file": "pitch_adler.md", "role": "Business Intel", "channel": "ft-consult",
     "style": "Opportunity-focused. TAM-thinker. 'The market is $4.2B and growing.' Ecosystem expert. Sees funding rounds as tea leaves."},
    {"name": "Leonard Nakamura", "file": "55_competitive_intel.md", "role": "Competitive Intel", "channel": "ft-consult",
     "style": "Investigative. Product-obsessed. 'I tore down their pricing page -- here is what they hide.' Teardown artist. Japanese precision."},
    {"name": "Thomas Rourke", "file": "56_data_verifier.md", "role": "Data Verifier", "channel": "ft-consult",
     "style": "Skeptical. Numbers-driven. 'Source? Verified against 3 sources.' Fact-checker. Irish calm under pressure."},
    {"name": "Isaac Ashworth", "file": "60_tech_assistant.md", "role": "Tech Assistant", "channel": "ft-consult",
     "style": "Database keeper. Categorization-obsessed. 'Indexed and tagged.' Methodical. Maintains the competitor database overnight."},
    # Bravo Editors (Claude Corp -- Quality & Content)
    {"name": "Vera Lux", "file": "everlight_content_director.md", "role": "Content Director", "channel": "war-room",
     "style": "Creative discipline. Brand guardian. 'This does not sound like us.' High standards with warmth. Romanian-born, NYC sharpened."},
    {"name": "Edith Cross", "file": "15_editor_qa.md", "role": "Editor QA", "channel": "war-room",
     "style": "Grammar hawk. Tone police. 'Comma splice on line 4.' Fact-checker. Red pen energy. Zero tolerance for sloppiness."},
    {"name": "Quinn Fontaine", "file": "41_style_enforcer.md", "role": "Style Enforcer", "channel": "war-room",
     "style": "Meticulous. Tone-obsessed. 'The brand voice is off here.' Elegant. French surname, Southern upbringing. Guard of the style guide."},
    {"name": "Quinn Sharp", "file": "everlight_qa_gate.md", "role": "QA & Systems", "channel": "hive-alerts",
     "style": "Systems thinker. 'Disk at 87%, flag it.' Monitors uptime. Flags degradation before failure. Methodical. Night owl by nature."},
    {"name": "Paul Sandoval", "file": "44_edit_assistant.md", "role": "Edit Assistant", "channel": "war-room",
     "style": "Detail hound. Catches typos at 3 AM. 'Found a broken link in the footer.' Night owl. Reliable. Filipino-American precision."},
    # Plus: Cross-team night support
    {"name": "Justine Park", "file": "34_compliance_gate.md", "role": "Legal Review", "channel": "war-room",
     "style": "By-the-book. 'Let me review that before we proceed.' Speed vs caution tension with Marcus. Korean-American. Contract precision."},
    {"name": "Samuel Navarro", "file": "42_financial_safeguard.md", "role": "Financial Safeguard", "channel": "war-room",
     "style": "Suspicious by design. Forensic mindset. 'Something does not add up.' Fraud detector. Cautious. Reviews every transaction twice."},
    {"name": "Augustine Crane", "file": "45_compliance_assistant.md", "role": "Compliance Assistant", "channel": "war-room",
     "style": "Systematic. Paper-trail-obsessed. 'Audit log updated.' Calm under pressure. Creates the records everyone else forgets."},
]

# ---------------------------------------------------------------------------
# Social interests for watercooler talk -- all 63 agents
# ---------------------------------------------------------------------------
SOCIAL_HOOKS = {
    # Morning Shift
    "Marcus Cole": "Coaching son Thomas's rugby Saturday. Monty the dog. Brixton stories. Tea and whisky.",
    "Atlas Vega": "Weekend architecture walks. Lego Technic builds with his kids. Obsessed with brutalist buildings.",
    "Nora Blaine": "Yoga at sunrise. Meal-prep Sundays. K-drama binge nights. Content calendar for her personal blog.",
    "Slate Mercer": "Chess tournaments online. Reads military strategy for fun. Dry humor about everything. Craft whisky collection.",
    "Sage Holloway": "Green tea ceremonies. Bonsai garden on the balcony. Reads literary fiction. Quiet hikes in redwoods.",
    "Derek Ellis": "Disc golf weekends. Minimal apartment aesthetic. Podcast junkie -- always recommending episodes nobody asked for.",
    "Sebastian Navarro": "Boxing gym three days a week. Salsa dancing. Cooks arroz con pollo better than his abuela (he claims).",
    "Piper Reeves": "Nashville songwriting circles. Front porch conversations. Southern cooking. Rescues dogs. Vintage guitar collection.",
    "Rex Blackwell": "Fishing Lake Ray Hubbard. Chili cook-off champion 2019. F-250 truck. Whataburger runs. AC/DC on vinyl.",
    "Adrian Morgan": "Weekend open houses just for fun. Sneaker collection. Smooth jazz. Tells stories at dinner parties that sell themselves.",
    "Frederick Beckett": "Basketball pickup games. Fantasy football commissioner for three leagues. Coffee shop work sessions.",
    "Penny Vance": "Mom's jewelry store in Edison. Daughter Asha saying 'ROI' at age 2. Ballet. Harmonium practice. Chai rituals.",
    "Franklin Jordan": "Board game nights with friends. Escape rooms. Reads behavioral economics books. Optimizes his morning routine quarterly.",
    "Calvin Osei": "Soccer with the kids Saturday morning. Ghanaian jollof rice -- will debate Nigerian jollof any day. Gospel choir on Sundays.",
    "Harrison Knox": "Thursday poker night with Rex B. Never shows the running tally. Bourbon collection. Old Clint Eastwood westerns.",
    "Lawrence Okafor": "Nigerian football (soccer) fanatic. Arsenal supporter. Spreadsheets even for personal budgeting. Weekend market shopping.",
    "Ryan Kim": "Korean BBQ with the startup crew. Climbing gym Tuesdays. Product Hunt launches. Obsessed with growth hacking podcasts.",
    "Franklin Steele": "Pittsburgh Steelers season tickets. Home workshop. Builds furniture from reclaimed wood. Black coffee, no sugar, no negotiation.",
    "Aria Chen": "Piano practice and probability puzzles. Shanghai street food nostalgia. Minimalist apartment. Runs 5K every morning.",
    "Mack Rivera": "Bronx pickup basketball. Coaches youth league. Dominican food on Sundays at mom's. Old school hip-hop vinyl collection.",

    # Swing Shift
    "Major Dex": "Military history documentaries. Black coffee at all hours. Pre-dawn runs. Precision in everything including his home gym routine.",
    "Marcus Webb": "Weekend cycling -- century rides. Data visualization art. Quiet craft beer appreciation. Reads Tufte for fun.",
    "Charles Dawson": "Weekend hiking and craft beer. Dashboard design as a hobby. Sees stories in numbers. Photography -- landscapes and data.",
    "Daniel Monroe": "Former ad agency life stories. Food truck tours in every new city. Fast talker, fast eater, fast mover.",
    "Benjamin Crate": "Checklist apps and organization systems. Weekend farmers market hauls. Sourdough starter he named Gerald.",
    "Philip Warren": "Tableau community meetups. Watercolor painting -- same color theory as data viz. Quiet Saturday mornings with pour-over coffee.",
    "Sebastian Torres": "Hackathons every other month. Puerto Rican beach nostalgia. Builds side projects that ship in a weekend. Mechanical keyboard collector.",
    "Raymond Harper": "Road trips with no destination. Reads product management blogs religiously. Dad jokes that land 40% of the time.",
    "Samuel Locke": "Fishing alone on quiet lakes. Reads SEO case studies for fun. Patient with everything except broken redirects.",
    "Isaac Castellano": "Hemingway for style, Garcia Marquez for soul. Quiet coffee shops. Writes short fiction nobody has read yet.",
    "Patrick Donovan": "Boston sports bars for Celtics games. Homebrewing IPAs. Test-driven everything, even his weekend chores.",
    "Frederick Banks": "Probability puzzles before bed. Chess.com addiction. Reads Nassim Taleb. Minimal social life by choice, not circumstance.",
    "Benjamin Orozco": "Late-night data scraping side projects. Mexican street food tours. Soccer on weekends. Quiet intensity in all things.",
    "Oliver Kessler": "Cooking elaborate dinners for friends. German efficiency meets California casual. Reads client success stories for inspiration.",
    "Rafael Vasquez": "Dominican baseball. Bachata dancing. Family barbecues every Sunday. Follows up on everything -- even personal plans.",
    "Rex Thornton": "Long runs through Lincoln Park. 1:72 model aircraft. Home weather station. Dad's probability puzzles at dinner.",
    "Miguel Reyes": "Piano practice and volatility surface modeling. Options trading since college. $500 blown twice before learning risk.",
    "Carlos Moreno": "Weekend soccer league. Family cookouts. Tracks personal spending in a spreadsheet his wife teases him about.",
    "Gary Tanaka": "Woodworking and Rube Goldberg machines. Japanese garden maintenance. Automates his home lighting and never stops tweaking it.",
    "Lincoln Masters": "Marathon runner. Syncs his life with calendar apps. Meditates to maintain intensity. Reads about distributed systems.",
    "Carlos Alvarez": "Tinkering with Raspberry Pi projects. Colombian coffee connoisseur. Salsa music while coding. Breaks things to learn them.",

    # Night Shift
    "Christopher Wolfe": "Late-night on-chain analysis. Reads three newspapers before 7 AM. Chess. Dry humor. Prefers the quiet hours.",
    "Bernard Archer": "Classic jazz vinyl collection. Old-school Bloomberg terminal stories. Reads Barron's cover to cover. Scotch, neat.",
    "Pedro Diaz": "Miami nightlife stories. MMA training Tuesday/Thursday. Consumer trend obsession. Cooks Cuban food from his grandmother's recipes.",
    "Christopher Johanssen": "Early riser who scans news before dawn. Denver hiking. Nordic crime fiction. Coffee -- always black, always strong.",
    "William Santos": "Brazilian jiujitsu twice a week. Wire service war stories. Home espresso setup he spent too much on. News junkie 24/7.",
    "Bernard Calloway": "Legal history books. Weekend golf -- terrible at it, loves it anyway. Compliance jokes nobody laughs at except Henry.",
    "Stewart Erikson": "Geopolitical board games. Reads The Economist cover to cover. Scandinavian noir films. Quiet pipe tobacco on the balcony.",
    "Henry Patel": "Cricket on weekends. Biotech journals in bed. British-Indian home cooking experiments. Teaches science to his nephew.",
    "David Wen": "Reads court transcripts for fun. Taiwanese night market food nostalgia. Quiet walks at midnight. Legal podcast addict.",
    "Nathan Ling": "Side projects and Product Hunt launches. Canadian politeness. Tests every new AI tool the day it drops. Board game nights.",
    "Peter Adler": "Startup pitch deck collection -- reads them like novels. Weekend tennis. Sees funding rounds as tea leaves. NYT crossword daily.",
    "Leonard Nakamura": "Product teardowns as a hobby. Takes apart competitors' apps the way others watch TV. Japanese woodworking on weekends.",
    "Thomas Rourke": "Irish pub trivia nights. Fact-checks everything including restaurant menus. Dry wit. Numbers-first even in casual conversation.",
    "Isaac Ashworth": "Database organization as meditation. Categorizes his book collection by subject, author, and date read. Quiet night walks.",
    "Vera Lux": "Romanian folk music. NYC gallery openings. Creative writing journals. Cooks for the team when deadlines hit.",
    "Edith Cross": "Red pen collection (not kidding). Grammar memes. Reads style guides from different eras. Bakes precisely measured pastries.",
    "Quinn Fontaine": "Southern garden parties. French cinema. Brand identity books. Writes calligraphy. Elegant in everything including grocery shopping.",
    "Quinn Sharp": "Systems monitoring dashboards at home too. Disk health as a hobby. Quiet satisfaction when uptime hits 99.9%. Late-night ramen.",
    "Paul Sandoval": "Night owl by nature. Filipino food blogging. Catches typos in published books and emails the publisher. Vinyl collector.",
    "Justine Park": "Monthly lunch with Penny about mothers, children, and saying 'no.' Contract law journals. Korean skincare routine. Precision.",
    "Samuel Navarro": "True crime documentaries. Forensic accounting case studies. Weekend farmers market. Trusts no one's expense reports, including his own.",
    "Augustine Crane": "Archiving family photos. Genealogy research. Quiet tea and classical music evenings. Maintains records nobody asks for until they need them.",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_firmware(filename):
    path = AGENT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")[:2500]
    return ""

def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except:
        return {}

def call_ai(system, user, max_tokens=300, task_type="standard"):
    """Legacy wrapper -- delegates to hive_model_router.route_and_call().

    Kept for backward compatibility. New code should call route_and_call() directly.
    """
    return route_and_call(system, user, task_type=task_type, max_tokens=max_tokens)

def post(channel_name, text):
    cid = CHANNELS.get(channel_name)
    if not cid or not text:
        return False
    try:
        r = requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
            json={"channel": cid, "text": text}, timeout=15)
        return r.json().get("ok", False)
    except:
        return False

def get_live_data():
    state = _read_json(DATA_DIR / "state.json")
    sentiment = _read_json(DATA_DIR / "sentiment_shift.json")
    correlation = _read_json(DATA_DIR / "correlation_drift.json")
    onchain = _read_json(DATA_DIR / "onchain_alerts.json")

    # Try Django for pipeline data
    pipeline = {}
    try:
        sys.path.insert(0, "/home/opc/hive_django")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django; django.setup()
        from broker_ops.models import PropertyLead, InvestorBuyer, WholesaleMatch, Deal
        pipeline = {
            "leads": PropertyLead.objects.count(),
            "buyers": InvestorBuyer.objects.count(),
            "matches": WholesaleMatch.objects.count(),
            "active_deals": Deal.objects.filter(status="active").count(),
        }
    except:
        pipeline = {"leads": 436, "buyers": 12, "matches": 1464, "active_deals": 0}

    return {
        "bot": {k: state.get(k) for k in ["equity_start", "position", "pnl_today", "trades_today", "vol_state", "consecutive_losses"]},
        "sentiment": {"score": sentiment.get("score"), "direction": sentiment.get("direction")},
        "correlation": {"btc_xlm": correlation.get("btc_xlm_correlation_24h"), "xlm_strength": correlation.get("xlm_relative_strength")},
        "onchain": {"whale_level": onchain.get("whale_alert_level"), "network": onchain.get("network_health")},
        "pipeline": pipeline,
    }

def person_prompt(person, extra_context=""):
    fw = _load_firmware(person["file"])
    return f"""You are {person['name']}, {person['role']} at Everlight Ventures. You serve Lucrex, King of Divine Light.

SPEECH STYLE: {person['style']}

{fw}

{CAPABILITIES_CONTEXT}

{extra_context}

Rules: Stay 100% in character. Sound like a real person, not a bot. Use your quirks, catchphrases, and personality. Keep posts brief (2-6 lines). Reference other team members by name when relevant."""

# ---------------------------------------------------------------------------
# Rotation Window -- cap at 5-8 people per hour instead of full 21
# ---------------------------------------------------------------------------

# Map shift objects to their start hours
_SHIFT_START = {}

def _register_shifts():
    """Register shift start hours after shifts are defined."""
    _SHIFT_START[id(MORNING_SHIFT)] = 6
    _SHIFT_START[id(SWING_SHIFT)] = 14
    _SHIFT_START[id(NIGHT_SHIFT)] = 22

_register_shifts()


def get_rotation_window(shift, hour):
    """Return 5-8 people from the shift for this hour's posts."""
    start = _SHIFT_START.get(id(shift), 6)
    idx = (hour - start) % 8
    # Deterministic rotation: slide through the roster
    window = shift[idx * 3: idx * 3 + 5]
    # If we slid past the end, wrap around
    if len(window) < 5:
        window = shift[-(5 - len(window)):] + window if window else shift[:5]
    # Add 1-2 random from remainder for variety
    remainder = [p for p in shift if p not in window]
    if remainder:
        window.extend(random.sample(remainder, min(2, len(remainder))))
    return window[:8]  # cap at 8


# ---------------------------------------------------------------------------
# Shift Events
# ---------------------------------------------------------------------------

def clock_in(shift, data):
    """Team clocks in at shift start -- rotation window only."""
    log.info("=== Clock-in: %s shift ===", "morning" if shift is MORNING_SHIFT else "swing" if shift is SWING_SHIFT else "night")
    now = datetime.now(PT)
    window = get_rotation_window(shift, now.hour)
    # Always include shift lead (index 0)
    if shift[0] not in window:
        window.insert(0, shift[0])
        window = window[:8]
    for person in window:
        text = route_and_call(
            person_prompt(person, "You're clocking in for your shift. Greet the team, mention what you're planning to focus on today based on the data. Keep it natural -- like walking into the office and saying good morning to people."),
            f"Clock in. Current data: {json.dumps(data, default=str)[:500]}\nTime: {now.strftime('%I:%M %p PT')}\nSay hi and state your plan for the shift.",
            task_type="clock_in",
            max_tokens=150,
        )
        if text:
            post(person["channel"], text)
            log.info("Clocked in: %s", person["name"])
        time.sleep(2)

def standup(shift, data):
    """Quick standup -- rotation window reports."""
    log.info("=== Standup ===")
    now = datetime.now(PT)
    window = get_rotation_window(shift, now.hour)
    # Always include shift lead
    if shift[0] not in window:
        window.insert(0, shift[0])
        window = window[:8]
    reports = {}
    for person in window:
        text = route_and_call(
            person_prompt(person, "Quick standup. Report: what you're working on RIGHT NOW, any blockers, and one thing you need from a teammate. Be specific. Reference real data."),
            f"Data: {json.dumps(data, default=str)[:500]}\nGive your standup update.",
            task_type="standup",
            max_tokens=200,
        )
        if text:
            post(person["channel"], text)
            reports[person["name"]] = text[:200]
            log.info("Standup: %s", person["name"])
        time.sleep(2)
    return reports

def marcus_delegates(reports, data):
    """Marcus reads standups and delegates in #war-room."""
    if not reports:
        return ""
    fw = _load_firmware("01_chief_operator.md")
    summaries = "\n".join(f"**{n}**: {t}" for n, t in reports.items())
    # Pull shared memory from Blinko for strategic context
    blinko_ctx = get_blinko_context("pipeline wholesale surplus revenue deals")
    user_msg = f"Team standups:\n{summaries}\n\nData: {json.dumps(data, default=str)[:400]}\n\nDelegate now."
    if blinko_ctx:
        user_msg += f"\n\nRecent Blinko context:\n{blinko_ctx}"
    text = route_and_call(
        f"""You are Marcus Cole, Chief Operator at Everlight Ventures. {fw[:1500]}
Read your team's standups and delegate. Be specific -- tell each person by name what to focus on. Set priorities. Flag blockers. Short sentences. 'Right then.' 'Sorted.' 'What's the play?'""",
        user_msg,
        task_type="delegation",
        max_tokens=400,
    )
    if text:
        post("war-room", text)
        log.info("Marcus delegated")
    return text or ""

def team_responds(shift, marcus_text, data):
    """Team members respond to Marcus's delegation -- rotation window only."""
    if not marcus_text:
        return
    now = datetime.now(PT)
    window = get_rotation_window(shift, now.hour)
    for person in window:
        text = route_and_call(
            person_prompt(person, "Marcus just delegated tasks. Respond acknowledging your assignment. State specifically what you're doing about it RIGHT NOW. Brief -- 2-3 lines."),
            f"Marcus said:\n{marcus_text[:400]}\n\nYour data: {json.dumps(data, default=str)[:300]}\n\nRespond to your assignment.",
            task_type="response",
            max_tokens=150,
        )
        if text:
            post(person["channel"], text)
        time.sleep(2)

def midshift_checkin(shift, data):
    """Mid-shift progress check -- rotation window."""
    log.info("=== Mid-shift check-in ===")
    now = datetime.now(PT)
    window = get_rotation_window(shift, now.hour)
    # Only 3-5 people check in to keep volume natural
    checkin_group = window[:5]
    for person in checkin_group:
        text = route_and_call(
            person_prompt(person, "Mid-shift progress update. What have you accomplished so far? What's left? Any wins or problems? Keep it conversational -- like updating a coworker in passing."),
            f"Data: {json.dumps(data, default=str)[:500]}\nShare your progress.",
            task_type="checkin",
            max_tokens=150,
        )
        if text:
            post(person["channel"], text)
        time.sleep(2)

def watercooler_chat(shift):
    """Random social conversation in #watercooler -- samples from full shift."""
    log.info("=== Watercooler ===")
    # Pick 2-3 random people from the FULL shift for variety
    chatters = random.sample(shift, min(3, len(shift)))

    topics = [
        "what you're doing this weekend",
        "something funny that happened today",
        "a food recommendation",
        "something you're watching or reading",
        "a hot take about something non-work",
        "plans for the evening",
        "a story from your past that's relevant to nothing",
    ]
    topic = random.choice(topics)

    for i, person in enumerate(chatters):
        hooks = SOCIAL_HOOKS.get(person["name"], "general small talk")
        if i == 0:
            prompt = f"Start a casual conversation about {topic}. Be yourself -- your hobbies, your life outside work. This is the #watercooler channel. No work talk. Just be human."
        else:
            prompt = f"Someone in #watercooler is talking about {topic}. Jump in naturally. React to what was said. Share something from your own life. Be real."

        text = route_and_call(
            person_prompt(person, f"This is #watercooler -- social channel. Your personal interests: {hooks}. NO WORK TALK. Just be a person having a conversation with coworkers."),
            prompt,
            task_type="watercooler",
            max_tokens=120,
        )
        if text:
            post("watercooler", text)
        time.sleep(3)

def shift_handoff(outgoing, incoming, data):
    """Shift handoff -- outgoing summarizes, incoming acknowledges."""
    log.info("=== Shift handoff ===")
    lead_out = outgoing[0]
    lead_in = incoming[0]

    handoff = route_and_call(
        person_prompt(lead_out, "Your shift is ending. Write a brief handoff to the incoming team. What happened, what's pending, what needs attention. Like leaving notes for the next shift."),
        f"Data: {json.dumps(data, default=str)[:400]}\nWrite your handoff.",
        task_type="delegation",
        max_tokens=200,
    )
    if handoff:
        post("war-room", handoff)

    time.sleep(3)

    ack = route_and_call(
        person_prompt(lead_in, "You're picking up the shift. Acknowledge the handoff. State what you're prioritizing. Brief -- 2-3 lines."),
        f"Handoff notes:\n{handoff[:300]}\n\nAcknowledge and state your priorities.",
        task_type="response",
        max_tokens=150,
    )
    if ack:
        post("war-room", ack)

def clock_out(shift):
    """End of shift -- quick goodbye."""
    lead = shift[0]
    text = route_and_call(
        person_prompt(lead, "End of shift. Quick sign-off message. Mention one thing that went well. Keep it natural -- like saying bye to coworkers."),
        "Sign off for the shift. Quick and natural.",
        task_type="clock_out",
        max_tokens=80,
    )
    if text:
        post("war-room", text)

# ---------------------------------------------------------------------------
# Hourly Scheduler
# ---------------------------------------------------------------------------

def _morning_standup_and_delegate(d):
    reports = standup(MORNING_SHIFT, d)
    mt = marcus_delegates(reports, d)
    team_responds(MORNING_SHIFT, mt, d)

def _swing_standup_and_delegate(d):
    reports = standup(SWING_SHIFT, d)
    mt = marcus_delegates(reports, d)
    team_responds(SWING_SHIFT, mt, d)

SCHEDULE = {
    # Morning shift (6 AM - 2 PM PT)
    6:  lambda d: (clock_in(MORNING_SHIFT, d), watercooler_chat(MORNING_SHIFT)),
    7:  lambda d: _morning_standup_and_delegate(d),
    8:  lambda d: (midshift_checkin(MORNING_SHIFT, d),),
    9:  lambda d: (midshift_checkin(MORNING_SHIFT, d),),
    10: lambda d: (watercooler_chat(MORNING_SHIFT),),
    11: lambda d: (midshift_checkin(MORNING_SHIFT, d),),
    12: lambda d: (post("watercooler", route_and_call(person_prompt(random.choice(MORNING_SHIFT), "You're heading to lunch. Mention what you're eating. Casual."), "Announce lunch break.", task_type="social", max_tokens=60)),),
    13: lambda d: (midshift_checkin(MORNING_SHIFT, d), watercooler_chat(MORNING_SHIFT)),

    # Shift handoff + Swing (2 PM - 10 PM PT)
    14: lambda d: (shift_handoff(MORNING_SHIFT, SWING_SHIFT, d), clock_in(SWING_SHIFT, d)),
    15: lambda d: (standup(SWING_SHIFT, d),),
    16: lambda d: _swing_standup_and_delegate(d),
    17: lambda d: (midshift_checkin(SWING_SHIFT, d), watercooler_chat(SWING_SHIFT)),
    18: lambda d: (post("watercooler", route_and_call(person_prompt(random.choice(SWING_SHIFT), "Dinner break. What are you eating? Casual."), "Announce dinner.", task_type="social", max_tokens=60)),),
    19: lambda d: (midshift_checkin(SWING_SHIFT, d),),
    20: lambda d: (watercooler_chat(SWING_SHIFT),),
    21: lambda d: (midshift_checkin(SWING_SHIFT, d),),

    # Shift handoff + Night (10 PM - 6 AM PT)
    22: lambda d: (shift_handoff(SWING_SHIFT, NIGHT_SHIFT, d), clock_in(NIGHT_SHIFT, d)),
    23: lambda d: (standup(NIGHT_SHIFT, d),),
    0:  lambda d: (midshift_checkin(NIGHT_SHIFT, d),),
    1:  lambda d: (watercooler_chat(NIGHT_SHIFT),),
    2:  lambda d: (midshift_checkin(NIGHT_SHIFT, d),),
    3:  lambda d: None,  # Quiet hours
    4:  lambda d: (midshift_checkin(NIGHT_SHIFT, d),),
    5:  lambda d: (shift_handoff(NIGHT_SHIFT, MORNING_SHIFT, d), clock_out(NIGHT_SHIFT)),
}

def run():
    now = datetime.now(PT)
    hour = now.hour
    log.info("=== Hive Shift System | %s | Hour %d ===", now.strftime("%I:%M %p PT %A"), hour)

    # Load .env
    env_path = Path("/home/opc/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    data = get_live_data()
    handler = SCHEDULE.get(hour)
    if handler:
        result = handler(data)
        log.info("Hour %d events complete", hour)
    else:
        log.info("Hour %d: no scheduled events", hour)

if __name__ == "__main__":
    run()
