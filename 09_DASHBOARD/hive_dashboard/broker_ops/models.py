"""
Broker OS - Models

Pure middleman matchmaking engine:
- OfferListing: what sellers have (AI SaaS, services, tools)
- LeadProfile:  what buyers need (startups, SMBs, CTOs)
- BrokerMatch:  AI-scored pairing
- Deal:         closed/active deal
- CommissionRecord: immutable ledger, audit-ready
"""
import uuid

from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# SELLER SIDE: what's being offered
# ---------------------------------------------------------------------------

class OfferListing(models.Model):
    CATEGORY_CHOICES = [
        ("ai_saas",      "AI / SaaS Tool"),
        ("dev_service",  "Dev / Implementation Service"),
        ("fintech",      "Fintech / Compliance"),
        ("healthtech",   "Healthtech / Privacy"),
        ("marketing",    "Marketing / Growth"),
        ("logistics",    "Logistics / Operations"),
        ("other",        "Other"),
    ]
    STATUS_CHOICES = [
        ("active",    "Active"),
        ("paused",    "Paused"),
        ("closed",    "Closed"),
        ("draft",     "Draft"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller_name   = models.CharField(max_length=200)
    seller_email  = models.EmailField()
    seller_url    = models.URLField(blank=True)

    title         = models.CharField(max_length=300)
    category      = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="ai_saas", db_index=True)
    description   = models.TextField()
    keywords      = models.JSONField(default=list, help_text="List of matching keywords")

    # Pricing
    price_min     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_max     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pricing_model = models.CharField(
        max_length=20,
        choices=[("one_time","One-time"),("monthly","Monthly"),("annual","Annual"),("revenue_share","Rev Share")],
        default="monthly"
    )
    commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.00,
                                          help_text="% commission we take on each deal")

    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    source        = models.CharField(max_length=100, blank=True, help_text="product_hunt, indiehackers, direct, email")
    source_url    = models.URLField(blank=True)

    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    notes         = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Offer Listing"

    def __str__(self):
        return f"{self.title} ({self.seller_name})"

    @property
    def commission_min(self):
        return float(self.price_min) * float(self.commission_pct) / 100

    @property
    def commission_max(self):
        return float(self.price_max) * float(self.commission_pct) / 100


# ---------------------------------------------------------------------------
# BUYER SIDE: what's being sought
# ---------------------------------------------------------------------------

class LeadProfile(models.Model):
    INTENT_CHOICES = [
        ("hot",   "Hot - ready to buy"),
        ("warm",  "Warm - evaluating"),
        ("cold",  "Cold - researching"),
    ]
    LEAD_SOURCE_CHOICES = [
        ("inbound_email",  "Inbound Email"),
        ("product_hunt",   "Product Hunt"),
        ("linkedin",       "LinkedIn"),
        ("twitter_x",      "Twitter/X"),
        ("referral",       "Referral"),
        ("direct",         "Direct / Manual"),
        ("newsletter",     "Newsletter"),
        ("reddit",         "Reddit"),
        ("hacker_news",    "Hacker News"),
        ("github",         "GitHub"),
        ("other",          "Other"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200)
    email           = models.EmailField(blank=True)
    company         = models.CharField(max_length=200, blank=True)
    role            = models.CharField(max_length=100, blank=True, help_text="CTO, Founder, etc.")
    company_size    = models.CharField(
        max_length=20,
        choices=[("1_10","1-10"),("11_50","11-50"),("51_200","51-200"),("200_plus","200+")],
        blank=True
    )

    need_description  = models.TextField(help_text="What they're looking for")
    categories_needed = models.JSONField(default=list, help_text="List of category keys they need")
    budget_min        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    budget_max        = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    intent          = models.CharField(max_length=10, choices=INTENT_CHOICES, default="warm")
    lead_source     = models.CharField(max_length=30, choices=LEAD_SOURCE_CHOICES, default="other", db_index=True)
    source_url      = models.URLField(blank=True)

    # Outreach tracking
    last_contacted  = models.DateTimeField(null=True, blank=True)
    contact_count   = models.IntegerField(default=0)
    unsubscribed    = models.BooleanField(default=False)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    notes           = models.TextField(blank=True)
    raw_data        = models.JSONField(default=dict, help_text="Original scraped/imported payload")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead Profile"

    def __str__(self):
        return f"{self.name} @ {self.company or 'Unknown'} ({self.intent})"


# ---------------------------------------------------------------------------
# MATCHING: AI-scored pairings
# ---------------------------------------------------------------------------

class BrokerMatch(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending Review"),
        ("approved",  "Approved - Outreach Sent"),
        ("declined",  "Declined"),
        ("converted", "Converted to Deal"),
        ("expired",   "Expired"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer       = models.ForeignKey(OfferListing, on_delete=models.CASCADE, related_name="matches")
    lead        = models.ForeignKey(LeadProfile, on_delete=models.CASCADE, related_name="matches")

    # AI scoring
    match_score     = models.FloatField(default=0.0, help_text="0-100, AI-generated", db_index=True)
    match_reasoning = models.TextField(blank=True, help_text="Why this pair was matched")
    matched_by      = models.CharField(max_length=50, default="auto", help_text="auto, manual, claude")

    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)

    outreach_sent_at  = models.DateTimeField(null=True, blank=True)
    outreach_channel  = models.CharField(max_length=50, blank=True, help_text="email, slack, dm")
    outreach_template = models.CharField(max_length=100, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at  = models.DateTimeField(auto_now=True)
    notes       = models.TextField(blank=True)

    class Meta:
        unique_together = [("offer", "lead")]
        ordering = ["-match_score", "-created_at"]
        verbose_name = "Broker Match"

    def __str__(self):
        return f"Match {self.match_score:.0f}% | {self.offer.title[:30]} <-> {self.lead.name}"


# ---------------------------------------------------------------------------
# DEALS: closed/active
# ---------------------------------------------------------------------------

class Deal(models.Model):
    STAGE_CHOICES = [
        ("intro",       "Intro Made"),
        ("negotiating", "Negotiating"),
        ("contracted",  "Contracted"),
        ("active",      "Active / In Progress"),
        ("closed_won",  "Closed Won"),
        ("closed_lost", "Closed Lost"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match       = models.OneToOneField(BrokerMatch, on_delete=models.CASCADE, related_name="deal",
                                        null=True, blank=True)
    offer       = models.ForeignKey(OfferListing, on_delete=models.SET_NULL, null=True, related_name="deals")
    lead        = models.ForeignKey(LeadProfile, on_delete=models.SET_NULL, null=True, related_name="deals")

    stage       = models.CharField(max_length=20, choices=STAGE_CHOICES, default="intro")
    deal_value  = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                       help_text="Total value of the deal (seller-buyer contract)")
    commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    commission_due = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          help_text="Our cut = deal_value * commission_pct / 100")

    agreement_url     = models.URLField(blank=True, help_text="Link to signed finder agreement")
    stripe_invoice_id = models.CharField(max_length=200, blank=True)

    started_at   = models.DateTimeField(default=timezone.now)
    closed_at    = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.commission_due = self.deal_value * self.commission_pct / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deal ${self.deal_value} | {self.stage} | {self.offer}"


# ---------------------------------------------------------------------------
# COMMISSION LEDGER: immutable audit trail
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# OUTREACH SEQUENCES: multi-step email tracking
# ---------------------------------------------------------------------------

class OutreachSequence(models.Model):
    STEP_CHOICES = [
        ("buyer_intro",  "Buyer Intro"),
        ("seller_intro", "Seller Intro"),
        ("followup_1",   "Follow-up 1"),
        ("followup_2",   "Follow-up 2"),
        ("breakup",      "Breakup / Final"),
    ]
    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("sent",     "Sent"),
        ("opened",   "Opened"),
        ("replied",  "Replied"),
        ("bounced",  "Bounced"),
        ("skipped",  "Skipped"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match       = models.ForeignKey(BrokerMatch, on_delete=models.CASCADE, related_name="outreach_steps")
    step        = models.CharField(max_length=20, choices=STEP_CHOICES)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    subject     = models.CharField(max_length=300, blank=True)
    body        = models.TextField(blank=True)
    to_email    = models.EmailField()

    scheduled_at = models.DateTimeField(help_text="When this email should be sent")
    sent_at      = models.DateTimeField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_at"]
        unique_together = [("match", "step")]
        verbose_name = "Outreach Sequence Step"

    def __str__(self):
        return f"{self.step} -> {self.to_email} ({self.status})"


class CommissionRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ("earned",    "Earned"),
        ("paid",      "Paid Out"),
        ("adjusted",  "Adjusted"),
        ("reversed",  "Reversed"),
        ("pending",   "Pending"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal        = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="commissions")
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES)

    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    currency    = models.CharField(max_length=10, default="USD")
    description = models.CharField(max_length=500, blank=True)

    stripe_payout_id  = models.CharField(max_length=200, blank=True)
    stripe_invoice_id = models.CharField(max_length=200, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    reference   = models.CharField(max_length=200, blank=True, help_text="External reference / invoice #")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Commission Record"

    def __str__(self):
        return f"{self.record_type} ${self.amount} | Deal {str(self.deal_id)[:8]}"
