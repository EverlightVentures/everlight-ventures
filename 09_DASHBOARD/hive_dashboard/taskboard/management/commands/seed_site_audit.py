"""
Seed the taskboard with site audit fix tasks.
Two batches: manual tasks for the user, and Lovable prompts to paste.

Usage:
    python manage.py seed_site_audit
"""

from django.core.management.base import BaseCommand
from taskboard.models import TaskTemplate, TaskItem


def ensure_template(name, category, description, icon, schema):
    obj, _ = TaskTemplate.objects.get_or_create(
        name=name,
        defaults={
            "category": category,
            "description": description,
            "icon": icon,
            "schema": schema,
        },
    )
    return obj


CHECKBOX_SCHEMA = {"fields": [
    {"name": "done", "label": "Completed?", "type": "checkbox", "required": False},
    {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
]}

LOVABLE_SCHEMA = {"fields": [
    {"name": "prompt_pasted", "label": "Prompt pasted into Lovable?", "type": "checkbox", "required": False},
    {"name": "verified", "label": "Result verified?", "type": "checkbox", "required": False},
    {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
]}


# ═══════════════════════════════════════════════════════════════
# YOUR TODO LIST (manual tasks)
# ═══════════════════════════════════════════════════════════════
USER_TASKS = [
    {
        "title": "Regenerate GitHub PAT (old one is exposed in git config)",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Go to github.com > Settings > Developer Settings > Personal Access Tokens\n"
            "2. Delete the old token (the one starting with github_pat_11B6PGE3Q0...)\n"
            "3. Generate a new fine-grained token\n"
            "   - Scope it to just the EverlightVentures org\n"
            "   - Give it repo read/write permissions\n"
            "4. Update the remote URL:\n"
            "   git remote set-url origin https://x-access-token:NEW_TOKEN@github.com/EverlightVentures/everlight-ventures.git\n\n"
            "WHY: The old PAT is visible in the git config. Anyone with access to your repo can see it."
        ),
        "priority": 1,
    },
    {
        "title": "Upload book cover images to Lovable public assets",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. In Lovable, go to your project files\n"
            "2. Find or create a /public/images/books/ folder\n"
            "3. Upload these cover images from your phone:\n"
            "   - Book 1 cover: ADVENTURES_WITH_SAM/Book1/images/1_cover.jpg (or Sam's_Superpower_B1_1.jpg)\n"
            "   - Book 2 cover: ADVENTURES_WITH_SAM/Book 2/images/2_cover.jpg\n"
            "   - Book 3 cover: ADVENTURES_WITH_SAM/book_3/images/3_cover.jpg\n"
            "   - Book 4 cover: ADVENTURES_WITH_SAM/Book4/images/ (find the cover)\n"
            "   - Book 5 cover: ADVENTURES_WITH_SAM/Book5/images/ (find the cover)\n"
            "   - Beyond the Veil: you may need to generate a cover image\n\n"
            "WHY: The book pages need actual cover art to look professional. Right now they are probably placeholder or text-only."
        ),
        "priority": 2,
    },
    {
        "title": "Upload audio samples (Chapter 1 clips) to Lovable public assets",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Find your audiobook files:\n"
            "   - Sam & Robo audiobooks are in the book folders\n"
            "   - Beyond the Veil: BEYOND_THE_VEIL_HaileyPink_Book1/audiobook/\n"
            "2. For each book, extract or trim Chapter 1 to a 2-3 minute sample\n"
            "   - You can use a free tool like mp3cut.net or just upload the full Chapter 1 file\n"
            "3. Upload to Lovable: /public/audio/\n"
            "   - sam_book1_sample.mp3\n"
            "   - sam_book2_sample.mp3\n"
            "   - etc.\n"
            "   - btv_prologue_sample.mp3\n\n"
            "WHY: The site promises audio previews but there is nothing to play right now. "
            "A 2-minute sample is the best free marketing you have."
        ),
        "priority": 2,
    },
    {
        "title": "Upload HTML readers as preview-only versions to Lovable",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Your HTML readers are at:\n"
            "   - Book1/Sams_First_Superpower_reader.html\n"
            "   - Book 2/Sams_Second_Superpower_reader.html\n"
            "   - book_3/Sams_Third_Superpower_reader.html\n"
            "   - etc.\n"
            "2. For FREE PREVIEWS: upload a trimmed version (first 2-3 chapters only)\n"
            "   - Open each HTML file, find where Chapter 3 ends, delete everything after\n"
            "   - Save as sam_book1_preview.html, etc.\n"
            "3. Upload preview HTMLs to Lovable /public/previews/\n"
            "4. The FULL readers are the paid product -- do NOT upload those publicly\n\n"
            "WHY: Let people read the first few chapters free. They buy if they are hooked. "
            "This is how every bookstore works -- you browse before you buy."
        ),
        "priority": 2,
    },
    {
        "title": "Record or generate Beyond the Veil cover art",
        "description": (
            "HOW TO DO THIS:\n\n"
            "Use Midjourney, DALL-E, or your preferred image generator:\n\n"
            "Prompt idea: 'Book cover, female deputy in a duster coat standing at the "
            "boundary between a dusty western street and a luminous astral landscape "
            "with floating islands and cosmic ocean. Dual worlds. Cinematic lighting. "
            "Title: BEYOND THE VEIL. Author: Everlight Ventures Publishing. "
            "Dark moody color palette with amber and violet accents. "
            "Professional book cover composition, 1600x2560px'\n\n"
            "Save as beyond_the_veil_cover.jpg\n"
            "Upload to Lovable /public/images/books/\n\n"
            "WHY: This is your most ambitious book and it has no cover image. "
            "A strong cover is the single biggest factor in whether someone clicks to learn more."
        ),
        "priority": 2,
    },
]


# ═══════════════════════════════════════════════════════════════
# LOVABLE TODO LIST (paste these prompts into Lovable chat)
# ═══════════════════════════════════════════════════════════════
LOVABLE_TASKS = [
    {
        "title": "LOVABLE: Fix SEO -- unique meta titles and descriptions per page",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'Every page on my site has the same meta title and description. "
            "Please give each route its own unique <title> and <meta name=\"description\">:\n\n"
            "/ -- title: Everlight Ventures | Build Different. Build in the Light. "
            "desc: A venture studio building across commerce, publishing, software, and finance.\n"
            "/publishing -- title: Everlight Publishing | Books That Last "
            "desc: Independent publisher of children's fiction, literary thrillers, and interactive learning.\n"
            "/publishing/sam-and-robo -- title: Adventures with Sam & Robo | 5 Books, Ages 3-8 "
            "desc: Phonics-based children's books with interactive coloring pages, audiobooks, and digital editions.\n"
            "/publishing/beyond-the-veil -- title: Beyond the Veil | A Quantum Western Thriller "
            "desc: A 100,000-word novel about a deputy who escapes reality through astral projection.\n"
            "/alley-kingz -- title: Alley Kingz | Real-Time PvP Card Battler "
            "desc: 41 characters, 10 city factions, Three.js 3D. Play the demo now.\n"
            "/onyx -- title: Onyx POS | $49/mo Flat Rate Point of Sale "
            "desc: No percentage fees. Inventory, employees, analytics, mobile checkout.\n"
            "/hivemind -- title: Hive Mind | AI Team Orchestration "
            "desc: Coordinate Claude, Gemini, Codex, and Perplexity as a unified AI team.\n"
            "/him-loadout -- title: HIM Loadout | Curated Gear for Men "
            "desc: Tech, EDC, fitness, grooming, outdoor, and style picks worth buying.\n"
            "/logistics -- title: Everlight Logistics | Fulfillment and Supply Chain "
            "desc: E-commerce fulfillment, last-mile delivery, and supply chain consulting.\n"
            "/dashboard -- title: XLM Bot | Live Algorithmic Trading Dashboard "
            "desc: Real-time performance metrics for our XLM perpetuals trading bot.\n\n"
            "Also update the og:title, og:description, twitter:title, and twitter:description "
            "meta tags to match each page.'"
        ),
        "priority": 1,
    },
    {
        "title": "LOVABLE: Add sitemap.xml and robots.txt for Google indexing",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'Add a sitemap.xml and robots.txt to my site.\n\n"
            "robots.txt should allow all crawlers and point to the sitemap:\n"
            "User-agent: *\n"
            "Allow: /\n"
            "Sitemap: https://everlightventures.io/sitemap.xml\n\n"
            "sitemap.xml should list all 10 routes with today as lastmod:\n"
            "/, /publishing, /publishing/sam-and-robo, /publishing/beyond-the-veil, "
            "/alley-kingz, /onyx, /hivemind, /him-loadout, /logistics, /dashboard\n\n"
            "Make sure both files are served as static files at the root.'"
        ),
        "priority": 1,
    },
    {
        "title": "LOVABLE: Add ebook preview readers (first 2 chapters, embedded iframe)",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'On /publishing/sam-and-robo, add a \"Read a Free Sample\" section. "
            "Embed an iframe that loads /previews/sam_book1_preview.html "
            "(I will upload this file). Style the iframe with a dark border, "
            "max-height 500px, scrollable, with a frosted glass overlay at the bottom "
            "that says \"Continue reading -- $6.99\" with a Buy button.\n\n"
            "Do the same on /publishing/beyond-the-veil with /previews/btv_preview.html. "
            "The overlay should say \"Continue reading -- $6.99\" with a Buy Digital button.\n\n"
            "The preview gives them the first 2 chapters free. The buy button "
            "will eventually open Stripe Checkout.'"
        ),
        "priority": 2,
    },
    {
        "title": "LOVABLE: Add audio preview players for each book",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'Add an audio player section to /publishing/sam-and-robo and "
            "/publishing/beyond-the-veil.\n\n"
            "For Sam & Robo: show a simple audio player with the label "
            "\"Listen to Chapter 1\" and load /audio/sam_book1_sample.mp3. "
            "Style it minimal -- dark background, gold accent on the progress bar, "
            "play/pause button. Add players for books 1-5.\n\n"
            "For Beyond the Veil: audio player labeled \"Listen to the Prologue\" "
            "loading /audio/btv_prologue_sample.mp3.\n\n"
            "Use the native HTML5 audio element styled to match the site theme. "
            "Do NOT autoplay. Show duration.'"
        ),
        "priority": 2,
    },
    {
        "title": "LOVABLE: Replace Amazon links with $6.99 Buy Digital buttons",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'On /publishing/sam-and-robo, replace all \"Buy on Amazon\" buttons with "
            "\"Buy Digital -- $6.99\" buttons. These should be the primary CTA for each book, "
            "styled with the gold accent color (#D4AF37), solid fill, white text.\n\n"
            "Add a secondary smaller link under each that says "
            "\"Also available on Amazon\" but make it a muted text link (not a button) "
            "that goes to # for now (I will add the Amazon URLs later).\n\n"
            "Also add a \"Complete Series Bundle -- $29.99 (save $5)\" card "
            "after the individual books with a larger CTA button.\n\n"
            "Do the same on /publishing/beyond-the-veil -- "
            "primary button is \"Buy Digital -- $6.99\", "
            "secondary is \"Join Print Waitlist\" as a text link.\n\n"
            "For now the buy buttons can just show an alert saying "
            "\"Store coming soon!\" -- I will wire Stripe later.'"
        ),
        "priority": 2,
    },
    {
        "title": "LOVABLE: Protect ebook content -- no right-click, no copy, watermark",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'For the ebook preview iframes and any reader content on the site:\n\n"
            "1. Disable right-click context menu on the preview iframes\n"
            "2. Disable text selection (user-select: none) on book content\n"
            "3. Disable Ctrl+S / Cmd+S save shortcut\n"
            "4. Add a subtle diagonal watermark overlay that says "
            "\"PREVIEW -- everlightventures.io\" in very light opacity (0.08) "
            "repeating across the iframe content\n"
            "5. The preview HTML files should not be directly linkable -- "
            "wrap them so the iframe source is a Supabase function that "
            "checks a session token before serving content\n\n"
            "This is for the free previews. The paid full readers will be "
            "delivered as downloadable EPUBs after Stripe payment, not hosted on the site.\n\n"
            "Note: this will not stop determined pirates, but it stops casual copying "
            "and makes it clear this is proprietary content.'"
        ),
        "priority": 3,
    },
    {
        "title": "LOVABLE: Add per-page OG images for social sharing",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'Update the og:image meta tag to be unique per page:\n\n"
            "/ -- keep the current default Everlight Ventures image\n"
            "/publishing/sam-and-robo -- use /images/books/sam_book1_cover.jpg\n"
            "/publishing/beyond-the-veil -- use /images/books/beyond_the_veil_cover.jpg\n"
            "/alley-kingz -- use a screenshot of the game demo if available\n"
            "/onyx -- use the Onyx POS logo or a dashboard screenshot\n\n"
            "For any pages without a custom image, fall back to the default.\n"
            "This makes social media shares look professional instead of generic.'"
        ),
        "priority": 3,
    },
    {
        "title": "LOVABLE: Add contact/support form wired to Slack #ev-support",
        "description": (
            "PASTE THIS INTO LOVABLE:\n\n"
            "'Add a simple contact/support form in the footer or on a /support page.\n"
            "Fields: Name, Email, Subject (dropdown: Book Support, General Question, "
            "Business Inquiry, Bug Report), Message.\n\n"
            "On submit, store the message in a Supabase \"support_requests\" table "
            "and POST to a Slack webhook (I will provide the URL) with:\n"
            "{\"text\": \"Support request from [name] ([email]): [subject] -- [message]\"}\n\n"
            "Show a confirmation message: \"Got it. We will get back to you within 24 hours.\"\n"
            "Style the form to match the site dark theme.'"
        ),
        "priority": 3,
    },
]


class Command(BaseCommand):
    help = "Seed taskboard with site audit fix tasks (user manual + Lovable prompts)"

    def handle(self, *args, **options):
        # Ensure templates
        user_template = ensure_template(
            "site_audit_manual", "general",
            "Manual task from site audit", "fa-solid fa-wrench", CHECKBOX_SCHEMA,
        )
        lovable_template = ensure_template(
            "lovable_prompt", "general",
            "Prompt to paste into Lovable chat", "fa-solid fa-wand-magic-sparkles", LOVABLE_SCHEMA,
        )

        created = 0

        for task_def in USER_TASKS:
            exists = TaskItem.objects.filter(
                batch_id="site_audit_fixes", title=task_def["title"]
            ).exists()
            if exists:
                self.stdout.write(f"  [EXISTS] {task_def['title']}")
                continue
            TaskItem.objects.create(
                template=user_template,
                title=task_def["title"],
                description=task_def["description"],
                priority=task_def["priority"],
                source_agent="claude",
                target_agent="human",
                batch_id="site_audit_fixes",
            )
            created += 1
            self.stdout.write(f"  [CREATED] {task_def['title']}")

        for task_def in LOVABLE_TASKS:
            exists = TaskItem.objects.filter(
                batch_id="site_audit_lovable", title=task_def["title"]
            ).exists()
            if exists:
                self.stdout.write(f"  [EXISTS] {task_def['title']}")
                continue
            TaskItem.objects.create(
                template=lovable_template,
                title=task_def["title"],
                description=task_def["description"],
                priority=task_def["priority"],
                source_agent="claude",
                target_agent="lovable",
                batch_id="site_audit_lovable",
            )
            created += 1
            self.stdout.write(f"  [CREATED] {task_def['title']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nSite audit tasks seeded: {created} tasks across 'site_audit_fixes' and 'site_audit_lovable' batches"
        ))
