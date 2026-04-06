"""
Seed the taskboard with ebook store launch tasks.
Human-friendly step-by-step instructions for each task.

Usage:
    python manage.py seed_ebook_store
"""

from django.core.management.base import BaseCommand
from taskboard.models import TaskTemplate, TaskItem


BATCH_ID = "ebook_store_launch"


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


TASKS = [
    # ── Step 1: Slack Channels ──────────────────────────────────
    {
        "template_name": "slack_channel_setup",
        "template_defaults": {
            "category": "general",
            "description": "Create Slack channels for sales and support",
            "icon": "fa-brands fa-slack",
            "schema": {"fields": [
                {"name": "sales_channel_id", "label": "Sales Channel ID", "type": "text", "required": True,
                 "placeholder": "C0..."},
                {"name": "support_channel_id", "label": "Support Channel ID", "type": "text", "required": True,
                 "placeholder": "C0..."},
            ]},
        },
        "title": "Create Slack channels: #ev-sales and #ev-support",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Open Slack (everlightventures workspace)\n"
            "2. Click the '+' next to 'Channels' in the sidebar\n"
            "3. Create channel: ev-sales\n"
            "   - Purpose: 'Automated purchase notifications from the ebook store'\n"
            "   - Make it public so bots can post\n"
            "4. Create channel: ev-support\n"
            "   - Purpose: 'Customer support requests from everlightventures.io'\n"
            "   - Make it public\n"
            "5. Copy each channel ID (click the channel name at top, scroll down to the ID)\n"
            "6. Fill in the IDs below and mark complete\n\n"
            "WHY: Every time someone buys an ebook, you get a Slack notification. "
            "Every time someone needs help, it shows up in #ev-support instead of getting lost in email."
        ),
        "priority": 1,
    },

    # ── Step 2: Slack Incoming Webhook ──────────────────────────
    {
        "template_name": "slack_webhook_setup",
        "template_defaults": {
            "category": "api_credential",
            "description": "Slack incoming webhook for automated notifications",
            "icon": "fa-brands fa-slack",
            "schema": {"fields": [
                {"name": "webhook_url", "label": "Webhook URL", "type": "secret", "required": True,
                 "placeholder": "https://hooks.slack.com/services/..."},
            ]},
        },
        "title": "Set up Slack Incoming Webhook for #ev-sales",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Go to: api.slack.com/apps (in your browser)\n"
            "2. Click 'Create New App' > 'From scratch'\n"
            "   - Name: 'Everlight Store Bot'\n"
            "   - Workspace: everlightventures\n"
            "3. In the left sidebar, click 'Incoming Webhooks'\n"
            "4. Toggle it ON\n"
            "5. Click 'Add New Webhook to Workspace'\n"
            "6. Pick #ev-sales as the channel\n"
            "7. Copy the webhook URL -- it looks like https://hooks.slack.com/services/T.../B.../...\n"
            "8. Paste it below\n\n"
            "WHY: This webhook is what lets Supabase automatically post to Slack when a purchase happens. "
            "No code on your end -- Supabase calls this URL and Slack shows the message."
        ),
        "priority": 1,
    },

    # ── Step 3: Stripe Account ──────────────────────────────────
    {
        "template_name": "stripe_account",
        "template_defaults": None,  # already exists
        "title": "Set up Stripe and create 7 ebook products",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Go to stripe.com and sign up (or log in if you have one)\n"
            "2. Complete identity verification -- Stripe needs this before you can accept payments\n"
            "   - Takes 1-2 business days, but you can use TEST MODE right away\n"
            "3. In the Stripe Dashboard, go to Products > + Add Product\n"
            "4. Create these 7 products (use exact names for consistency):\n\n"
            "   a. Sam's First Superpower (Digital EPUB) -- $6.99, one-time\n"
            "   b. Sam's Second Superpower (Digital EPUB) -- $6.99, one-time\n"
            "   c. Sam's Third Superpower (Digital EPUB) -- $6.99, one-time\n"
            "   d. Sam's Fourth Superpower (Digital EPUB) -- $6.99, one-time\n"
            "   e. Sam's Fifth Superpower (Digital EPUB) -- $6.99, one-time\n"
            "   f. Sam & Robo Complete Bundle (Digital) -- $29.99, one-time\n"
            "   g. Beyond the Veil (Digital EPUB) -- $6.99, one-time\n\n"
            "5. For each product, copy the Price ID (starts with price_...)\n"
            "6. Copy your API keys from Developers > API Keys:\n"
            "   - Publishable key (pk_test_... for now)\n"
            "   - Secret key (sk_test_... for now)\n"
            "7. Fill in the keys below\n\n"
            "TIP: Start with TEST MODE keys (the toggle at the top of Stripe Dashboard). "
            "You can test purchases with card number 4242 4242 4242 4242. "
            "Switch to live keys once everything works."
        ),
        "priority": 1,
    },

    # ── Step 4: Supabase Storage ────────────────────────────────
    {
        "template_name": "supabase_ebook_storage",
        "template_defaults": {
            "category": "general",
            "description": "Upload EPUB files to Supabase private storage",
            "icon": "fa-solid fa-cloud-arrow-up",
            "schema": {"fields": [
                {"name": "bucket_created", "label": "Bucket 'ebooks' created?", "type": "checkbox", "required": False},
                {"name": "files_uploaded", "label": "How many files uploaded?", "type": "text", "required": True,
                 "placeholder": "7"},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Upload all EPUB files to Supabase Storage",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Log into your Supabase project (the one connected to Lovable)\n"
            "2. Go to Storage in the left sidebar\n"
            "3. Click 'New Bucket'\n"
            "   - Name: ebooks\n"
            "   - IMPORTANT: Make it PRIVATE (not public) -- buyers get temporary download links\n"
            "4. Inside the bucket, create folders and upload:\n\n"
            "   ebooks/sam-book-1/Sams_First_Superpower.epub\n"
            "   ebooks/sam-book-2/Sams_Second_Superpower.epub\n"
            "   ebooks/sam-book-3/Sams_Third_Superpower.epub\n"
            "   ebooks/sam-book-4/Sams_Fourth_Superpower.epub\n"
            "   ebooks/sam-book-5/Sams_Fifth_Superpower.epub\n"
            "   ebooks/beyond-the-veil/Beyond_The_Veil.epub\n\n"
            "   For the bundle, zip all 5 Sam books together and upload as:\n"
            "   ebooks/sam-bundle/Sam_And_Robo_Complete.zip\n\n"
            "Your EPUB files are at:\n"
            "   /ADVENTURES_WITH_SAM/Book1/Sams_First_Superpower.epub\n"
            "   /ADVENTURES_WITH_SAM/Book 2/Sams_Second_Superpower.epub\n"
            "   /ADVENTURES_WITH_SAM/book_3/Sams_Third_Superpower.epub\n"
            "   /ADVENTURES_WITH_SAM/Book4/Sams_Fourth_Superpower.epub\n"
            "   /ADVENTURES_WITH_SAM/Book5/Sams_Fifth_Superpower.epub\n\n"
            "WHY PRIVATE: Nobody can download your books without paying. "
            "After checkout, Supabase generates a temporary signed URL that expires in 72 hours."
        ),
        "priority": 2,
    },

    # ── Step 5: Supabase Tables ─────────────────────────────────
    {
        "template_name": "supabase_tables_setup",
        "template_defaults": {
            "category": "general",
            "description": "Create database tables for purchase tracking",
            "icon": "fa-solid fa-database",
            "schema": {"fields": [
                {"name": "tables_created", "label": "Tables created?", "type": "checkbox", "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Create Supabase tables for purchases and ebook files",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. In Supabase, go to SQL Editor (left sidebar)\n"
            "2. Click 'New Query'\n"
            "3. Paste this SQL and click 'Run':\n\n"
            "CREATE TABLE purchases (\n"
            "  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,\n"
            "  stripe_session_id TEXT UNIQUE NOT NULL,\n"
            "  stripe_customer_email TEXT NOT NULL,\n"
            "  product_slug TEXT NOT NULL,\n"
            "  amount_paid INTEGER NOT NULL,\n"
            "  download_token UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,\n"
            "  download_count INTEGER DEFAULT 0,\n"
            "  max_downloads INTEGER DEFAULT 3,\n"
            "  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '72 hours'),\n"
            "  created_at TIMESTAMPTZ DEFAULT NOW()\n"
            ");\n\n"
            "CREATE TABLE ebook_files (\n"
            "  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,\n"
            "  product_slug TEXT UNIQUE NOT NULL,\n"
            "  file_path TEXT NOT NULL,\n"
            "  file_name TEXT NOT NULL,\n"
            "  title TEXT NOT NULL,\n"
            "  author TEXT DEFAULT 'Everlight Ventures Publishing'\n"
            ");\n\n"
            "4. Then paste and run this to populate the ebook_files table:\n\n"
            "INSERT INTO ebook_files (product_slug, file_path, file_name, title) VALUES\n"
            "('sam-book-1', 'ebooks/sam-book-1/Sams_First_Superpower.epub', "
            "'Sams_First_Superpower.epub', 'Sam''s First Superpower'),\n"
            "('sam-book-2', 'ebooks/sam-book-2/Sams_Second_Superpower.epub', "
            "'Sams_Second_Superpower.epub', 'Sam''s Second Superpower'),\n"
            "('sam-book-3', 'ebooks/sam-book-3/Sams_Third_Superpower.epub', "
            "'Sams_Third_Superpower.epub', 'Sam''s Third Superpower'),\n"
            "('sam-book-4', 'ebooks/sam-book-4/Sams_Fourth_Superpower.epub', "
            "'Sams_Fourth_Superpower.epub', 'Sam''s Fourth Superpower'),\n"
            "('sam-book-5', 'ebooks/sam-book-5/Sams_Fifth_Superpower.epub', "
            "'Sams_Fifth_Superpower.epub', 'Sam''s Fifth Superpower'),\n"
            "('sam-bundle', 'ebooks/sam-bundle/Sam_And_Robo_Complete.zip', "
            "'Sam_And_Robo_Complete.zip', 'Sam & Robo Complete Bundle'),\n"
            "('beyond-the-veil', 'ebooks/beyond-the-veil/Beyond_The_Veil.epub', "
            "'Beyond_The_Veil.epub', 'Beyond the Veil');\n\n"
            "WHY: These tables track who bought what and control download access. "
            "The purchases table creates a 72-hour, 3-download link for each buyer."
        ),
        "priority": 2,
    },

    # ── Step 6: Connect Stripe to Lovable ───────────────────────
    {
        "template_name": "lovable_stripe_connect",
        "template_defaults": {
            "category": "payment",
            "description": "Connect Stripe to Lovable site",
            "icon": "fa-solid fa-plug",
            "schema": {"fields": [
                {"name": "connected", "label": "Stripe connected in Lovable?", "type": "checkbox", "required": False},
                {"name": "checkout_working", "label": "Test checkout working?", "type": "checkbox", "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Connect Stripe + Supabase in Lovable and build checkout",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Open your Lovable project for everlightventures.io\n"
            "2. Go to Settings (gear icon) > Integrations\n"
            "3. Connect Supabase:\n"
            "   - Paste your Supabase project URL and anon key\n"
            "   - (Find these in Supabase > Settings > API)\n"
            "4. For Stripe, paste this into the Lovable chat:\n\n"
            "   'Add a Buy Digital button to each book on /publishing/sam-and-robo.\n"
            "    Each button should open Stripe Checkout for $6.99.\n"
            "    After successful payment, redirect to /purchase/success?session_id={CHECKOUT_SESSION_ID}.\n"
            "    The success page should call a Supabase Edge Function called verify-purchase\n"
            "    that checks the Stripe session, creates a download token in the purchases table,\n"
            "    and returns a signed download URL from the ebooks storage bucket.\n"
            "    Show a download button and also send the link to the customer email.\n"
            "    Also do the same for Beyond the Veil on /publishing/beyond-the-veil.\n"
            "    Use Stripe test mode keys for now.\n"
            "    My Stripe publishable key is: [paste your pk_test_ key here]'\n\n"
            "5. Lovable will generate the checkout components and Edge Function\n"
            "6. Test with card: 4242 4242 4242 4242, any future date, any CVC\n"
            "7. Verify the download link works\n\n"
            "WHY: Lovable builds the checkout UI and Supabase function for you. "
            "You just need to provide the keys and tell it what you want. "
            "The prompt above is written to give Lovable everything it needs in one shot."
        ),
        "priority": 2,
    },

    # ── Step 7: Wire Slack Notifications ────────────────────────
    {
        "template_name": "slack_notification_wiring",
        "template_defaults": {
            "category": "general",
            "description": "Wire Slack notifications into the purchase flow",
            "icon": "fa-solid fa-bell",
            "schema": {"fields": [
                {"name": "webhook_stored", "label": "Webhook URL stored in Supabase secrets?", "type": "checkbox",
                 "required": False},
                {"name": "test_notification_sent", "label": "Test notification received in Slack?", "type": "checkbox",
                 "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Wire Slack notifications into the Edge Function",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. In Supabase, go to Settings > Edge Functions > Secrets\n"
            "   (or Project Settings > Vault)\n"
            "2. Add a new secret:\n"
            "   - Name: SLACK_SALES_WEBHOOK_URL\n"
            "   - Value: [paste the webhook URL from Step 2]\n"
            "3. In the Lovable chat, tell it:\n\n"
            "   'Update the verify-purchase Edge Function to also send a Slack notification.\n"
            "    After verifying the purchase, POST to the SLACK_SALES_WEBHOOK_URL secret with:\n"
            "    {\"text\": \"New sale: [book title] -- $[amount] -- [customer email]\"}\n"
            "    Use Deno.env.get(\"SLACK_SALES_WEBHOOK_URL\") to read the secret.'\n\n"
            "4. Make a test purchase (Stripe test mode)\n"
            "5. Check #ev-sales -- you should see the notification\n\n"
            "WHY: You get a real-time ping every time someone buys a book. "
            "No checking dashboards -- the sale comes to you."
        ),
        "priority": 3,
    },

    # ── Step 8: Go Live ─────────────────────────────────────────
    {
        "template_name": "ebook_store_go_live",
        "template_defaults": {
            "category": "general",
            "description": "Switch from test mode to live payments",
            "icon": "fa-solid fa-rocket",
            "schema": {"fields": [
                {"name": "stripe_live", "label": "Switched to Stripe live keys?", "type": "checkbox",
                 "required": False},
                {"name": "test_purchase_done", "label": "Real test purchase completed?", "type": "checkbox",
                 "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Go live -- switch Stripe to live mode and verify",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Make sure ALL test mode steps above are complete and working\n"
            "2. In Stripe Dashboard, toggle from 'Test' to 'Live' mode (top-right)\n"
            "3. Copy your LIVE keys:\n"
            "   - pk_live_... (publishable)\n"
            "   - sk_live_... (secret)\n"
            "4. Update keys in Lovable (Settings > Integrations > Stripe)\n"
            "   OR update them in your Supabase secrets if that is where they are stored\n"
            "5. Update the Edge Function secret for STRIPE_SECRET_KEY with the live key\n"
            "6. Buy one of your own books with a real card ($6.99 -- treat yourself)\n"
            "7. Confirm:\n"
            "   - Payment shows in Stripe Dashboard\n"
            "   - Download link works\n"
            "   - Slack notification fires in #ev-sales\n"
            "   - Refund yourself in Stripe if you want the $6.99 back\n\n"
            "AFTER THIS: Your ebook store is live. Share the links. "
            "Every book page on everlightventures.io now accepts real money."
        ),
        "priority": 3,
    },
]


class Command(BaseCommand):
    help = "Seed taskboard with ebook store launch tasks (human-friendly instructions)"

    def handle(self, *args, **options):
        created_count = 0

        for task_def in TASKS:
            tname = task_def["template_name"]
            tdefaults = task_def.get("template_defaults")

            # Get or create template
            template = TaskTemplate.objects.filter(name=tname).first()
            if not template and tdefaults:
                template = TaskTemplate.objects.create(
                    name=tname,
                    category=tdefaults["category"],
                    description=tdefaults["description"],
                    icon=tdefaults["icon"],
                    schema=tdefaults["schema"],
                )
                self.stdout.write(f"  [CREATED] Template: {tname}")
            elif not template:
                # Use existing template (like stripe_account)
                template = TaskTemplate.objects.filter(name=tname).first()
                if not template:
                    self.stdout.write(self.style.WARNING(f"  [SKIP] No template: {tname}"))
                    continue

            # Check if task already exists
            exists = TaskItem.objects.filter(
                batch_id=BATCH_ID,
                title=task_def["title"],
            ).exists()
            if exists:
                self.stdout.write(f"  [EXISTS] {task_def['title']}")
                continue

            TaskItem.objects.create(
                template=template,
                title=task_def["title"],
                description=task_def["description"],
                priority=task_def["priority"],
                source_agent="claude",
                target_agent="human",
                batch_id=BATCH_ID,
            )
            created_count += 1
            self.stdout.write(f"  [CREATED] {task_def['title']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nEbook store tasks seeded: {created_count} tasks in batch '{BATCH_ID}'"
        ))
