"""
Seed the taskboard with predefined templates and the current content engine todo list.

Usage:
    python manage.py seed_taskboard
    python manage.py seed_taskboard --templates-only
"""

from django.core.management.base import BaseCommand
from taskboard.models import TaskTemplate, TaskItem


TEMPLATES = [
    {
        "name": "elevenlabs_api",
        "category": "api_credential",
        "description": "ElevenLabs TTS API credentials for voice synthesis",
        "icon": "fa-solid fa-microphone",
        "schema": {"fields": [
            {"name": "api_key", "label": "API Key", "type": "secret", "required": True,
             "hint": "Found in ElevenLabs dashboard > Profile > API Key"},
            {"name": "voice_id_1", "label": "Voice ID #1 (Primary)", "type": "text", "required": True,
             "hint": "Copy from Voice Lab after cloning/selecting a voice"},
            {"name": "voice_id_2", "label": "Voice ID #2 (Secondary)", "type": "text", "required": False},
            {"name": "plan_tier", "label": "Plan Tier", "type": "select",
             "options": ["free", "starter", "creator", "pro"], "required": True},
        ]},
    },
    {
        "name": "smtp_credentials",
        "category": "email_account",
        "description": "SMTP service credentials for email nurture sequences",
        "icon": "fa-solid fa-envelope",
        "schema": {"fields": [
            {"name": "provider", "label": "SMTP Provider", "type": "select",
             "options": ["resend", "brevo", "proton", "other"], "required": True},
            {"name": "smtp_host", "label": "SMTP Host", "type": "text", "required": True,
             "placeholder": "smtp.resend.com"},
            {"name": "smtp_port", "label": "SMTP Port", "type": "text", "required": True,
             "placeholder": "465"},
            {"name": "smtp_user", "label": "SMTP Username", "type": "text", "required": True},
            {"name": "smtp_pass", "label": "SMTP Password", "type": "secret", "required": True},
            {"name": "from_email", "label": "From Email Address", "type": "email", "required": True,
             "placeholder": "hello@yourdomain.com"},
        ]},
    },
    {
        "name": "domain_registration",
        "category": "domain",
        "description": "Domain name registration details",
        "icon": "fa-solid fa-globe",
        "schema": {"fields": [
            {"name": "domain_name", "label": "Domain Name", "type": "text", "required": True,
             "placeholder": "onyxpos.io"},
            {"name": "registrar", "label": "Registrar", "type": "select",
             "options": ["Cloudflare", "Namecheap", "Google Domains", "Porkbun", "Other"], "required": True},
            {"name": "nameservers", "label": "Nameservers (if custom)", "type": "textarea", "required": False,
             "placeholder": "ns1.example.com\nns2.example.com"},
            {"name": "admin_url", "label": "Registrar Dashboard URL", "type": "url", "required": False},
            {"name": "login_email", "label": "Registrar Login Email", "type": "email", "required": False},
        ]},
    },
    {
        "name": "stripe_account",
        "category": "payment",
        "description": "Stripe payment processing credentials",
        "icon": "fa-solid fa-credit-card",
        "schema": {"fields": [
            {"name": "publishable_key", "label": "Publishable Key", "type": "text", "required": True,
             "placeholder": "pk_live_..."},
            {"name": "secret_key", "label": "Secret Key", "type": "secret", "required": True,
             "placeholder": "sk_live_..."},
            {"name": "webhook_secret", "label": "Webhook Signing Secret", "type": "secret", "required": False,
             "placeholder": "whsec_..."},
            {"name": "account_id", "label": "Account ID", "type": "text", "required": False,
             "placeholder": "acct_..."},
            {"name": "mode", "label": "Mode", "type": "select", "options": ["test", "live"], "required": True},
        ]},
    },
    {
        "name": "twitter_api",
        "category": "api_credential",
        "description": "X/Twitter developer API credentials for automated posting",
        "icon": "fa-brands fa-x-twitter",
        "schema": {"fields": [
            {"name": "api_key", "label": "API Key (Consumer Key)", "type": "secret", "required": True},
            {"name": "api_secret", "label": "API Secret (Consumer Secret)", "type": "secret", "required": True},
            {"name": "access_token", "label": "Access Token", "type": "secret", "required": True},
            {"name": "access_secret", "label": "Access Token Secret", "type": "secret", "required": True},
            {"name": "bearer_token", "label": "Bearer Token", "type": "secret", "required": False},
        ]},
    },
    {
        "name": "did_api",
        "category": "api_credential",
        "description": "D-ID API credentials for lip-sync avatar video generation",
        "icon": "fa-solid fa-face-smile",
        "schema": {"fields": [
            {"name": "api_key", "label": "API Key", "type": "secret", "required": True,
             "hint": "Found in D-ID Studio > Settings > API"},
            {"name": "plan_tier", "label": "Plan", "type": "select",
             "options": ["free_trial", "lite", "pro"], "required": True},
        ]},
    },
    {
        "name": "avatar_portraits",
        "category": "general",
        "description": "Generate and save avatar portrait images for video content",
        "icon": "fa-solid fa-image",
        "schema": {"fields": [
            {"name": "generator_used", "label": "Generator Used", "type": "select",
             "options": ["Midjourney", "DALL-E", "Stable Diffusion", "Free Generator", "Other"], "required": True},
            {"name": "portrait_count", "label": "Number of Portraits Generated", "type": "text", "required": True},
            {"name": "saved_to_path", "label": "Saved To Path", "type": "text", "required": True,
             "placeholder": "Avatar_Assets/base_portraits/"},
            {"name": "filenames", "label": "Filenames (one per line)", "type": "textarea", "required": True,
             "placeholder": "default.jpg\neli_founder.jpg\nsage_builder.jpg"},
            {"name": "style_notes", "label": "Style Notes", "type": "textarea", "required": False,
             "placeholder": "Professional headshot, dark background, etc."},
        ]},
    },
    {
        "name": "social_media_account",
        "category": "social_media",
        "description": "New social media account for a brand/product",
        "icon": "fa-solid fa-share-nodes",
        "schema": {"fields": [
            {"name": "platform", "label": "Platform", "type": "select",
             "options": ["Instagram", "TikTok", "Facebook", "LinkedIn", "YouTube", "Threads", "Other"], "required": True},
            {"name": "brand_name", "label": "Brand / Business Name", "type": "text", "required": True},
            {"name": "username", "label": "Username / Handle", "type": "text", "required": True, "placeholder": "@yourhandle"},
            {"name": "email_used", "label": "Email Used to Sign Up", "type": "email", "required": True},
            {"name": "password", "label": "Password", "type": "secret", "required": True},
            {"name": "phone_number", "label": "Phone Number (if required)", "type": "text", "required": False},
            {"name": "profile_url", "label": "Profile URL", "type": "url", "required": False},
            {"name": "bio", "label": "Bio / Description", "type": "textarea", "required": False},
            {"name": "two_factor", "label": "2FA Enabled", "type": "checkbox", "required": False},
        ]},
    },
    {
        "name": "ai_agent_credential",
        "category": "ai_agent",
        "description": "API credentials for a new AI service / agent",
        "icon": "fa-solid fa-robot",
        "schema": {"fields": [
            {"name": "service_name", "label": "Service Name", "type": "text", "required": True,
             "placeholder": "e.g. OpenAI, Anthropic, Google AI"},
            {"name": "api_key", "label": "API Key", "type": "secret", "required": True},
            {"name": "api_secret", "label": "API Secret (if applicable)", "type": "secret", "required": False},
            {"name": "organization_id", "label": "Organization / Project ID", "type": "text", "required": False},
            {"name": "endpoint_url", "label": "Custom Endpoint URL", "type": "url", "required": False},
            {"name": "model_id", "label": "Default Model ID", "type": "text", "required": False,
             "placeholder": "e.g. claude-opus-4-6"},
            {"name": "tier", "label": "Plan Tier", "type": "select",
             "options": ["free", "pay-as-you-go", "pro", "enterprise"], "required": False},
            {"name": "notes", "label": "Notes", "type": "textarea", "required": False},
        ]},
    },
    {
        "name": "email_account",
        "category": "email_account",
        "description": "New email account for a brand or business",
        "icon": "fa-solid fa-at",
        "schema": {"fields": [
            {"name": "provider", "label": "Provider", "type": "select",
             "options": ["Gmail", "Proton Mail", "Outlook", "Zoho", "Custom Domain", "Other"], "required": True},
            {"name": "email_address", "label": "Email Address", "type": "email", "required": True},
            {"name": "password", "label": "Password", "type": "secret", "required": True},
            {"name": "purpose", "label": "Purpose", "type": "text", "required": True,
             "placeholder": "e.g. Onyx POS support, Hive Mind notifications"},
            {"name": "recovery_email", "label": "Recovery Email", "type": "email", "required": False},
            {"name": "two_factor", "label": "2FA Enabled", "type": "checkbox", "required": False},
        ]},
    },
]


INITIAL_TASKS = [
    {
        "template": "elevenlabs_api",
        "title": "ElevenLabs: Sign up free tier, get API key + voice IDs",
        "description": "Needed for TTS audio in the avatar content pipeline. Free tier gives 10,000 chars/month.",
        "priority": 2,
        "source_agent": "claude",
        "target_agent": "avatar_orchestrator",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "smtp_credentials",
        "title": "SMTP: Pick a service (Resend/Brevo/Proton), get credentials",
        "description": "Required for funnel email nurture sequences. Resend free tier = 3,000 emails/month. Brevo = 300/day.",
        "priority": 2,
        "source_agent": "claude",
        "target_agent": "funnel_nurture",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "domain_registration",
        "title": "Domain: Register onyxpos.io or similar ($12/yr)",
        "description": "Landing pages need a real domain. Cloudflare Registrar has cheapest renewal prices.",
        "priority": 3,
        "source_agent": "claude",
        "target_agent": "funnel_orchestrator",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "stripe_account",
        "title": "Stripe: Set up account for payment processing",
        "description": "Required for Onyx POS trial-to-paid conversion. Start with test mode keys.",
        "priority": 3,
        "source_agent": "claude",
        "target_agent": "funnel_orchestrator",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "twitter_api",
        "title": "X/Twitter: Apply for developer API access (free v2)",
        "description": "Needed for automated social posting via social_poster.py. Free v2 tier allows tweet creation.",
        "priority": 3,
        "source_agent": "claude",
        "target_agent": "social_poster",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "did_api",
        "title": "(Optional) D-ID: Sign up if you want lip-sync later",
        "description": "Free tier = 5 minutes of video. Only needed if you want talking-head animation instead of Ken Burns slideshow.",
        "priority": 5,
        "source_agent": "claude",
        "target_agent": "avatar_orchestrator",
        "batch_id": "content_engine_setup",
    },
    {
        "template": "avatar_portraits",
        "title": "Generate 3-5 avatar portrait images",
        "description": "Use Midjourney, DALL-E, or a free generator. Need professional-looking headshots for video content. Save to Avatar_Assets/base_portraits/.",
        "priority": 2,
        "source_agent": "claude",
        "target_agent": "avatar_orchestrator",
        "batch_id": "content_engine_setup",
    },
]


class Command(BaseCommand):
    help = "Seed taskboard with templates and initial content engine todo list"

    def add_arguments(self, parser):
        parser.add_argument("--templates-only", action="store_true", help="Only create templates, no tasks")

    def handle(self, *args, **options):
        # Create templates
        for t in TEMPLATES:
            obj, created = TaskTemplate.objects.get_or_create(
                name=t["name"],
                defaults={
                    "category": t["category"],
                    "description": t["description"],
                    "icon": t["icon"],
                    "schema": t["schema"],
                },
            )
            status = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{status}] Template: {obj.name}")

        if options["templates_only"]:
            self.stdout.write(self.style.SUCCESS("Templates seeded. Skipping tasks."))
            return

        # Create initial tasks
        for td in INITIAL_TASKS:
            template = TaskTemplate.objects.get(name=td["template"])
            existing = TaskItem.objects.filter(
                template=template,
                batch_id=td.get("batch_id", ""),
                title=td["title"],
            ).exists()
            if existing:
                self.stdout.write(f"  [EXISTS] Task: {td['title']}")
                continue

            TaskItem.objects.create(
                template=template,
                title=td["title"],
                description=td.get("description", ""),
                priority=td.get("priority", 3),
                source_agent=td.get("source_agent", ""),
                target_agent=td.get("target_agent", ""),
                batch_id=td.get("batch_id", ""),
            )
            self.stdout.write(f"  [CREATED] Task: {td['title']}")

        self.stdout.write(self.style.SUCCESS(f"\nTaskboard seeded: {len(TEMPLATES)} templates, {len(INITIAL_TASKS)} tasks."))
