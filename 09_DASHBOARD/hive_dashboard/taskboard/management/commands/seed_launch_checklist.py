"""
Seed the taskboard with Everlight Arcade launch and Stripe product setup tasks.
Human-friendly step-by-step instructions for each task.

Usage:
    python manage.py seed_launch_checklist
"""

from django.core.management.base import BaseCommand
from taskboard.models import TaskTemplate, TaskItem


BATCH_ID = "launch_checklist"


def ensure_template(name, category, description, icon, schema):
    obj, created = TaskTemplate.objects.get_or_create(
        name=name,
        defaults={
            "category": category,
            "description": description,
            "icon": icon,
            "schema": schema,
        },
    )
    return obj, created


TASKS = [
    # ── Task 1: Create 17 Stripe Products ────────────────────────
    {
        "template_name": "stripe_account",
        "template_defaults": None,  # already exists from seed_taskboard
        "title": "Create 17 Stripe products",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Go to dashboard.stripe.com and make sure TEST MODE is toggled ON (top-right toggle)\n"
            "   - You want to get everything perfect in test mode before touching real money\n"
            "2. Go to Products > + Add Product\n"
            "3. Create each product below. For each one:\n"
            "   - Enter the exact name\n"
            "   - Set the price as one-time payment\n"
            "   - After saving, click into the product and copy the Price ID (starts with price_...)\n"
            "   - Write down or paste each Price ID somewhere safe -- you will need all 17\n\n"
            "EBOOKS (one-time):\n"
            "   1.  Sam's First Superpower (Digital EPUB) -- $6.99\n"
            "   2.  Sam's Second Superpower (Digital EPUB) -- $6.99\n"
            "   3.  Sam's Third Superpower (Digital EPUB) -- $6.99\n"
            "   4.  Sam's Fourth Superpower (Digital EPUB) -- $6.99\n"
            "   5.  Sam's Fifth Superpower (Digital EPUB) -- $6.99\n"
            "   6.  Sam & Robo Complete Bundle (Digital) -- $29.99\n"
            "   7.  Beyond the Veil (Digital EPUB) -- $6.99\n\n"
            "ARCADE CREDITS (one-time):\n"
            "   8.  Arcade: 100 Gems -- $0.99\n"
            "   9.  Arcade: 500 Gems -- $3.99\n"
            "   10. Arcade: 1200 Gems -- $7.99\n"
            "   11. Arcade: Starter Pack -- $4.99\n"
            "   12. Arcade: Pro Pack -- $9.99\n\n"
            "ARCADE SUBSCRIPTIONS (recurring monthly):\n"
            "   13. Arcade: VIP Monthly -- $4.99/month\n"
            "   14. Arcade: VIP Annual -- $49.99/year\n\n"
            "SAAS PRODUCTS (recurring monthly):\n"
            "   15. Onyx POS Monthly -- $49/month\n"
            "   16. Hive Mind Starter -- $29/month\n"
            "   17. Hive Mind Pro -- $149/month\n\n"
            "TIPS:\n"
            "- For recurring products, pick 'Recurring' instead of 'One time' when setting price\n"
            "- You can add a description to each product if you want -- it shows on the Stripe receipt\n"
            "- Keep a spreadsheet or note with: Product Name | Price ID | Type (one-time/recurring)\n"
            "- You will paste these Price IDs into Supabase and Lovable later\n\n"
            "WHY ALL 17 NOW: It is way easier to create them all in one sitting than to come back "
            "and do it piecemeal. Once these exist in Stripe, every product page on your site can "
            "point to the right checkout with just a Price ID."
        ),
        "priority": 1,
    },

    # ── Task 2: Upload EPUBs to Supabase Storage ─────────────────
    {
        "template_name": "supabase_ebook_storage",
        "template_defaults": None,  # already exists from seed_ebook_store
        "title": "Upload EPUB files to Supabase Storage",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Log into your Supabase project (the one connected to your Lovable site)\n"
            "2. Go to Storage in the left sidebar\n"
            "3. Click 'New Bucket'\n"
            "   - Name: ebooks\n"
            "   - PRIVATE -- toggle public access OFF\n"
            "   - This is critical: if the bucket is public, anyone can download your books for free\n"
            "4. Inside the ebooks bucket, create subfolders and upload these files:\n\n"
            "   ebooks/sam-book-1/Sams_First_Superpower.epub\n"
            "   ebooks/sam-book-2/Sams_Second_Superpower.epub\n"
            "   ebooks/sam-book-3/Sams_Third_Superpower.epub\n"
            "   ebooks/sam-book-4/Sams_Fourth_Superpower.epub\n"
            "   ebooks/sam-book-5/Sams_Fifth_Superpower.epub\n"
            "   ebooks/beyond-the-veil/Beyond_The_Veil.epub\n"
            "   ebooks/sam-bundle/Sam_And_Robo_Complete.zip\n\n"
            "WHERE THE FILES LIVE ON YOUR PHONE:\n"
            "   /01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/"
            "ADVENTURES_WITH_SAM/Book1/Sams_First_Superpower.epub\n"
            "   /01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/"
            "ADVENTURES_WITH_SAM/Book 2/Sams_Second_Superpower.epub\n"
            "   /01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/"
            "ADVENTURES_WITH_SAM/book_3/Sams_Third_Superpower.epub\n"
            "   /01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/"
            "ADVENTURES_WITH_SAM/Book4/Sams_Fourth_Superpower.epub\n"
            "   /01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/"
            "ADVENTURES_WITH_SAM/Book5/Sams_Fifth_Superpower.epub\n"
            "   (Beyond the Veil and the bundle zip -- locate or create as needed)\n\n"
            "REMINDER: Private bucket means nobody downloads without paying. After checkout, "
            "Supabase generates a temporary signed URL that expires in 72 hours. "
            "Never make this bucket public."
        ),
        "priority": 1,
    },

    # ── Task 3: Create Supabase Edge Functions ────────────────────
    {
        "template_name": "supabase_edge_functions",
        "template_defaults": {
            "category": "general",
            "description": "Create Supabase Edge Functions for purchase verification and webhooks",
            "icon": "fa-solid fa-bolt",
            "schema": {"fields": [
                {"name": "verify_ebook", "label": "verify-ebook-purchase deployed?", "type": "checkbox",
                 "required": False},
                {"name": "verify_arcade", "label": "verify-arcade-purchase deployed?", "type": "checkbox",
                 "required": False},
                {"name": "verify_gems", "label": "verify-gem-purchase deployed?", "type": "checkbox",
                 "required": False},
                {"name": "stripe_webhook", "label": "stripe-webhook-handler deployed?", "type": "checkbox",
                 "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Create Supabase Edge Functions",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Open your Lovable project and paste this into the chat:\n\n"
            "   'Create four Supabase Edge Functions:\n"
            "   1. verify-ebook-purchase -- takes a Stripe session ID, confirms payment succeeded,\n"
            "      looks up the ebook in the ebook_files table, creates a purchase record with a\n"
            "      download token, and returns a signed download URL from the ebooks storage bucket.\n"
            "   2. verify-arcade-purchase -- takes a Stripe session ID, confirms payment, credits\n"
            "      the user's gem balance in a user_wallets table (create if needed).\n"
            "   3. verify-gem-purchase -- same as arcade but specifically for gem packs, maps the\n"
            "      Stripe price ID to the correct gem amount (100/500/1200).\n"
            "   4. stripe-webhook-handler -- receives Stripe webhook events (checkout.session.completed),\n"
            "      routes to the correct verify function based on product metadata, and sends a Slack\n"
            "      notification to SLACK_SALES_WEBHOOK_URL.\n"
            "   All functions should read secrets from Deno.env.get().'\n\n"
            "WHAT EACH FUNCTION DOES (plain English):\n\n"
            "- verify-ebook-purchase: Customer finishes checkout -> this function double-checks with\n"
            "  Stripe that they actually paid -> creates a time-limited download link -> hands it back\n"
            "  to the success page so the customer can download their book.\n\n"
            "- verify-arcade-purchase: Customer buys a starter/pro pack -> this function adds the\n"
            "  gems and any bonus items to their account.\n\n"
            "- verify-gem-purchase: Customer buys a gem pack (100/500/1200) -> this function looks up\n"
            "  how many gems that price ID maps to and adds them to the wallet.\n\n"
            "- stripe-webhook-handler: This is Stripe calling YOUR server. Every time a payment\n"
            "  completes, Stripe sends a POST to this function. It figures out what was bought and\n"
            "  routes to the right verify function. Also pings Slack so you know about every sale.\n\n"
            "WHY: These functions are the brains of your store. Without them, Stripe takes the money\n"
            "but nothing happens on your end. These connect payment to delivery."
        ),
        "priority": 2,
    },

    # ── Task 4: Add Supabase Secrets ──────────────────────────────
    {
        "template_name": "supabase_secrets_setup",
        "template_defaults": {
            "category": "api_credential",
            "description": "Store Stripe and Slack secrets in Supabase Edge Function secrets",
            "icon": "fa-solid fa-key",
            "schema": {"fields": [
                {"name": "stripe_key_stored", "label": "STRIPE_SECRET_KEY stored?", "type": "checkbox",
                 "required": False},
                {"name": "slack_webhook_stored", "label": "SLACK_SALES_WEBHOOK_URL stored?", "type": "checkbox",
                 "required": False},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Add Supabase secrets for Stripe and Slack",
        "description": (
            "HOW TO DO THIS:\n\n"
            "1. Go to your Supabase project\n"
            "2. Navigate to Settings > Edge Functions > Secrets\n"
            "   (Some versions: Project Settings > Edge Functions)\n"
            "3. Add these two secrets:\n\n"
            "   Secret #1:\n"
            "   - Name: STRIPE_SECRET_KEY\n"
            "   - Value: sk_test_... (your Stripe SECRET key from Task 1)\n"
            "   - Use the TEST key for now. You will swap to sk_live_... when you go live.\n\n"
            "   Secret #2:\n"
            "   - Name: SLACK_SALES_WEBHOOK_URL\n"
            "   - Value: https://hooks.slack.com/services/T.../B.../...\n"
            "   - This is the webhook URL from #ev-sales (if you set it up in the ebook store tasks)\n"
            "   - If you have not created the Slack webhook yet, do that first -- check the\n"
            "     ebook_store_launch tasks for the 'Set up Slack Incoming Webhook' task\n\n"
            "HOW TO FIND YOUR STRIPE SECRET KEY:\n"
            "   - Stripe Dashboard > Developers > API Keys\n"
            "   - Make sure Test Mode toggle is ON\n"
            "   - Copy the Secret Key (starts with sk_test_)\n"
            "   - NEVER put this in frontend code -- it goes in Supabase secrets only\n\n"
            "WHY: Your Edge Functions need these secrets to talk to Stripe and Slack. "
            "Supabase secrets are encrypted and only accessible from server-side Edge Functions, "
            "so your keys stay safe."
        ),
        "priority": 1,
    },

    # ── Task 5: Test Full Purchase Flow ───────────────────────────
    {
        "template_name": "purchase_flow_test",
        "template_defaults": {
            "category": "general",
            "description": "End-to-end test of the purchase flow in Stripe test mode",
            "icon": "fa-solid fa-vial",
            "schema": {"fields": [
                {"name": "ebook_test", "label": "Ebook purchase + download works?", "type": "checkbox",
                 "required": False},
                {"name": "arcade_test", "label": "Arcade credit purchase works?", "type": "checkbox",
                 "required": False},
                {"name": "slack_test", "label": "Slack notification fires?", "type": "checkbox",
                 "required": False},
                {"name": "supabase_records", "label": "Supabase tables have records?", "type": "checkbox",
                 "required": False},
                {"name": "notes", "label": "Notes / issues found", "type": "textarea", "required": False},
            ]},
        },
        "title": "Test full purchase flow in Stripe test mode",
        "description": (
            "HOW TO DO THIS:\n\n"
            "This is your dress rehearsal. Do not skip it.\n\n"
            "TEST AN EBOOK PURCHASE:\n"
            "1. Go to your live site (everlightventures.io/publishing or wherever ebooks are listed)\n"
            "2. Click 'Buy' on any Sam book\n"
            "3. On the Stripe Checkout page, use this test card:\n"
            "   - Card: 4242 4242 4242 4242\n"
            "   - Expiry: any future date (like 12/30)\n"
            "   - CVC: any 3 digits (like 123)\n"
            "   - Email: your real email (so you can check receipt delivery)\n"
            "4. Complete the purchase\n"
            "5. You should land on a success page with a download link\n"
            "6. Click the download link -- the EPUB should download\n"
            "7. Open the EPUB on your phone or Kindle app to make sure it is the right file\n\n"
            "TEST AN ARCADE PURCHASE:\n"
            "8. Go to the arcade section of your site\n"
            "9. Buy a gem pack (like 100 Gems for $0.99)\n"
            "10. Use the same test card: 4242 4242 4242 4242\n"
            "11. After checkout, verify your gem balance updated\n"
            "12. Try to play a game or unlock something with the gems\n\n"
            "CHECK THE BACKEND:\n"
            "13. Open Slack -- check #ev-sales for a notification about both purchases\n"
            "14. Open Supabase > Table Editor:\n"
            "    - Check the purchases table for the ebook record\n"
            "    - Check user_wallets (or equivalent) for the gem credit\n"
            "15. Open Stripe Dashboard > Payments -- both test payments should show up\n\n"
            "IF SOMETHING BREAKS:\n"
            "- Download link does not work? Check the ebooks bucket path matches ebook_files table\n"
            "- Gems did not credit? Check the Edge Function logs in Supabase\n"
            "- No Slack notification? Check SLACK_SALES_WEBHOOK_URL secret is set correctly\n"
            "- Stripe error? Check the webhook endpoint is registered in Stripe > Webhooks\n\n"
            "WHY: Better to find problems now with fake money than after a real customer pays. "
            "Test every path. Break things on purpose. This is the fun part."
        ),
        "priority": 2,
    },

    # ── Task 6: Switch Stripe to Live Mode ────────────────────────
    {
        "template_name": "ebook_store_go_live",
        "template_defaults": None,  # already exists from seed_ebook_store
        "title": "Switch Stripe to live mode",
        "description": (
            "HOW TO DO THIS:\n\n"
            "Only do this AFTER all test mode tasks above are passing.\n\n"
            "1. Go to Stripe Dashboard\n"
            "2. Toggle the 'Test mode' switch OFF (top-right corner)\n"
            "   - You are now looking at your live Stripe environment\n"
            "3. Go to Developers > API Keys and copy:\n"
            "   - pk_live_... (publishable key)\n"
            "   - sk_live_... (secret key)\n"
            "4. Go to Supabase > Settings > Edge Functions > Secrets\n"
            "   - Update STRIPE_SECRET_KEY to sk_live_...\n"
            "5. In your Lovable project, update the publishable key in your checkout code\n"
            "   - Search for pk_test_ and replace with pk_live_\n"
            "6. Verify your Stripe webhook endpoint is also set for live mode:\n"
            "   - Stripe > Developers > Webhooks > Add endpoint (if not already there for live)\n"
            "   - Point it to your stripe-webhook-handler Edge Function URL\n"
            "7. Buy one of your own books for real ($6.99)\n"
            "   - Use your actual credit card\n"
            "   - Confirm the download works\n"
            "   - Confirm Slack notification fires\n"
            "   - Confirm Supabase purchase record exists\n"
            "8. Refund yourself in Stripe if you want the $6.99 back:\n"
            "   - Stripe > Payments > click the payment > Refund\n\n"
            "AFTER THIS: Your store is live and accepting real payments. "
            "Share the links, post on social, and watch the sales roll in to #ev-sales."
        ),
        "priority": 3,
    },

    # ── Task 7: Apply for Google AdSense ──────────────────────────
    {
        "template_name": "google_adsense_setup",
        "template_defaults": {
            "category": "general",
            "description": "Apply for Google AdSense to monetize site traffic",
            "icon": "fa-solid fa-ad",
            "schema": {"fields": [
                {"name": "privacy_policy_live", "label": "Privacy policy page published?", "type": "checkbox",
                 "required": False},
                {"name": "adsense_applied", "label": "AdSense application submitted?", "type": "checkbox",
                 "required": False},
                {"name": "adsense_approved", "label": "AdSense approved?", "type": "checkbox",
                 "required": False},
                {"name": "publisher_id", "label": "Publisher ID (ca-pub-...)", "type": "text",
                 "required": False, "placeholder": "ca-pub-1234567890"},
                {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
            ]},
        },
        "title": "Apply for Google AdSense",
        "description": (
            "HOW TO DO THIS:\n\n"
            "BEFORE YOU APPLY -- you need a privacy policy page:\n"
            "1. In Lovable, create a /privacy page on everlightventures.io\n"
            "   - You can tell Lovable: 'Create a privacy policy page at /privacy that covers\n"
            "     data collection, cookies, third-party services (Stripe, Google Analytics,\n"
            "     Google AdSense), and contact info for Everlight Ventures.'\n"
            "   - Lovable will generate a solid privacy policy for you\n"
            "   - Make sure it is linked in the footer of your site\n\n"
            "APPLY FOR ADSENSE:\n"
            "2. Go to adsense.google.com\n"
            "3. Click 'Get Started'\n"
            "4. Enter your site URL: everlightventures.io\n"
            "5. Sign in with your Google account\n"
            "6. Fill in your payment info (address, tax info)\n"
            "7. Google will give you a snippet of code to add to your site's <head>\n"
            "   - In Lovable, tell it: 'Add this AdSense verification code to the <head> of every page:\n"
            "     [paste the code Google gives you]'\n"
            "8. Go back to AdSense and click 'Verify'\n"
            "9. Wait 1-3 business days for review\n\n"
            "WHAT HELPS YOU GET APPROVED:\n"
            "- Real content (your books, arcade, blog posts)\n"
            "- Privacy policy page (done in step 1)\n"
            "- Site has been live for at least a couple weeks\n"
            "- Navigation works, no broken links\n"
            "- Original content (not copy-pasted from elsewhere)\n\n"
            "WHY: AdSense is passive income. Once approved, you place ad blocks on pages with traffic "
            "and Google pays you per impression and click. It is not life-changing money at first, but "
            "it is free money that scales with traffic. Start the application now because the review "
            "takes time."
        ),
        "priority": 3,
    },
]


class Command(BaseCommand):
    help = "Seed taskboard with Everlight Arcade launch and Stripe product setup tasks"

    def handle(self, *args, **options):
        created_count = 0
        template_count = 0

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
                template_count += 1
                self.stdout.write(f"  [CREATED] Template: {tname}")
            elif template:
                self.stdout.write(f"  [EXISTS]  Template: {tname}")
            else:
                # template_defaults is None and template does not exist yet
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP]    No template found: {tname} -- run seed_taskboard or seed_ebook_store first"
                ))
                continue

            # Check if task already exists
            exists = TaskItem.objects.filter(
                batch_id=BATCH_ID,
                title=task_def["title"],
            ).exists()
            if exists:
                self.stdout.write(f"  [EXISTS]  Task: {task_def['title']}")
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
            self.stdout.write(f"  [CREATED] Task: {task_def['title']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nLaunch checklist seeded: {template_count} new templates, "
            f"{created_count} tasks in batch '{BATCH_ID}'"
        ))
