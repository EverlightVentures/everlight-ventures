"""
Broker OS - Models

Multi-vertical matchmaking engine:
- OfferListing: what sellers have (SaaS, services, tools, real estate)
- LeadProfile:  what buyers need (startups, SMBs, CTOs, investors)
- PropertyLead: real estate wholesale pipeline (distressed properties)
- InvestorBuyer: cash buyer list for wholesale assignments
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
        ("ai_saas",          "AI / SaaS Tool"),
        ("computer_vision",  "Computer Vision / Image AI"),
        ("dev_service",      "Dev / Implementation Service"),
        ("fintech",          "Fintech / Compliance"),
        ("healthtech",       "Healthtech / Privacy"),
        ("marketing",        "Marketing / Growth"),
        ("logistics",        "Logistics / Operations"),
        ("real_estate",      "Real Estate / Property"),
        ("website",          "Website / Domain"),
        ("other",            "Other"),
    ]
    STATUS_CHOICES = [
        ("active",    "Active"),
        ("paused",    "Paused"),
        ("closed",    "Closed"),
        ("draft",     "Draft"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller_name   = models.CharField(max_length=200)
    seller_email  = models.EmailField(blank=True, default="")
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
        ("intro",          "Intro Made"),
        ("negotiating",    "Negotiating"),
        ("contracted",     "Contracted"),
        ("legal_review",   "Legal Review (Justine)"),
        ("signing",        "Awaiting Signatures"),
        ("title_engaged",  "Title Company Engaged"),
        ("closing",        "Closing in Progress"),
        ("active",         "Active / In Progress"),
        ("closed_won",     "Closed Won"),
        ("closed_lost",    "Closed Lost"),
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

    # ── EMD tracking (audit-required for title-company files) ──
    earnest_money_deposit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Buyer EMD held with title/attorney. 0 = none on file yet.")
    emd_status = models.CharField(
        max_length=20, blank=True,
        choices=[("pending", "Pending receipt"), ("held", "Held by title"),
                 ("refunded", "Refunded to buyer"), ("forfeited", "Forfeited to seller"),
                 ("applied_to_close", "Applied to closing")],
        help_text="Lifecycle state of the earnest money")
    emd_received_at = models.DateTimeField(null=True, blank=True)
    emd_held_by = models.CharField(max_length=200, blank=True,
                                    help_text="Name of title company / attorney holding EMD")

    # ── Close type (audit-required: assignment vs double-close) ──
    close_type = models.CharField(
        max_length=20, default="assignment",
        choices=[("assignment", "Contract assignment"),
                 ("double_close", "A->B then B->C double close"),
                 ("subject_to", "Subject-to existing financing"),
                 ("direct_purchase", "We buy and hold")],
        help_text="How the deal will close. Drives template + funding requirements.")
    funder_name = models.CharField(max_length=200, blank=True,
                                    help_text="Transactional funder for double closes")

    # ── Inspection / due diligence ──
    inspection_status = models.CharField(
        max_length=20, default="not_started",
        choices=[("not_started", "Not started"), ("scheduled", "Scheduled"),
                 ("complete", "Complete"), ("waived", "Waived"),
                 ("failed", "Failed -- terminated")])
    inspection_due_date = models.DateField(null=True, blank=True)
    inspection_notes = models.TextField(blank=True)

    # ── Title status ──
    title_company = models.CharField(max_length=200, blank=True)
    title_search_ordered_at = models.DateTimeField(null=True, blank=True)
    title_clear = models.BooleanField(default=False,
                                       help_text="Title returned clear and marketable")

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


# ---------------------------------------------------------------------------
# REAL ESTATE WHOLESALE: property leads + investor buyers
# ---------------------------------------------------------------------------

class PropertyLead(models.Model):
    """Distressed or motivated-seller property for wholesale assignment."""
    LEAD_TYPE_CHOICES = [
        ("pre_foreclosure", "Pre-Foreclosure"),
        ("tax_lien",        "Tax Lien / Delinquent"),
        ("probate",         "Probate / Estate"),
        ("absentee",        "Absentee Owner"),
        ("divorce",         "Divorce"),
        ("code_violation",  "Code Violation"),
        ("high_equity",     "High Equity / Tired Landlord"),
        ("vacant",          "Vacant Property"),
        ("fsbo",            "For Sale By Owner"),
        ("expired_listing", "Expired MLS Listing"),
        ("zillow",          "Zillow / Public Listing"),
        ("other",           "Other"),
    ]
    STATUS_CHOICES = [
        ("new",          "New Lead"),
        ("contacted",    "Contacted"),
        ("negotiating",  "Negotiating"),
        ("under_contract", "Under Contract"),
        ("assigned",     "Assigned to Buyer"),
        ("closed",       "Closed"),
        ("dead",         "Dead / No Deal"),
    ]
    PROPERTY_TYPE_CHOICES = [
        ("sfr",         "Single Family"),
        ("multi",       "Multi-Family (2-4)"),
        ("apartment",   "Apartment (5+)"),
        ("condo",       "Condo / Townhouse"),
        ("land",        "Vacant Land"),
        ("commercial",  "Commercial"),
        ("mobile",      "Mobile Home"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Property info
    address         = models.CharField(max_length=300)
    city            = models.CharField(max_length=100)
    state           = models.CharField(max_length=2)
    zip_code        = models.CharField(max_length=10)
    county          = models.CharField(max_length=100, blank=True)
    property_type   = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES, default="sfr")
    bedrooms        = models.IntegerField(default=0)
    bathrooms       = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    sqft            = models.IntegerField(default=0)
    lot_sqft        = models.IntegerField(default=0)
    year_built      = models.IntegerField(default=0)

    # Owner info
    owner_name      = models.CharField(max_length=200, blank=True)
    owner_phone     = models.CharField(max_length=20, blank=True)
    owner_email     = models.EmailField(blank=True)
    owner_mailing   = models.CharField(max_length=300, blank=True, help_text="If different from property address")
    is_absentee     = models.BooleanField(default=False)

    # Deal numbers
    asking_price    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_arv   = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                           help_text="After Repair Value")
    estimated_repair = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                            help_text="Estimated repair costs")
    max_offer       = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                           help_text="70% ARV - repairs - assignment fee")
    assignment_fee  = models.DecimalField(max_digits=12, decimal_places=2, default=10000,
                                           help_text="Our wholesale fee (typically $5k-$25k)")

    # Scoring
    lead_type       = models.CharField(max_length=20, choices=LEAD_TYPE_CHOICES, default="other")
    motivation_score = models.IntegerField(default=0, help_text="0-100, how motivated is the seller")
    equity_pct      = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                           help_text="Estimated equity percentage")
    days_on_market  = models.IntegerField(default=0)

    # Status
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new", db_index=True)
    source          = models.CharField(max_length=100, blank=True, help_text="zillow, propstream, tax_records, driving_for_dollars")
    source_url      = models.URLField(blank=True)
    zillow_url      = models.URLField(blank=True)

    # Outreach
    last_contacted  = models.DateTimeField(null=True, blank=True)
    contact_count   = models.IntegerField(default=0)
    contact_method  = models.CharField(max_length=30, blank=True, help_text="sms, cold_call, direct_mail, email")

    # Linked deal (if assigned)
    deal            = models.ForeignKey(Deal, on_delete=models.SET_NULL, null=True, blank=True, related_name="properties")

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    notes           = models.TextField(blank=True)
    raw_data        = models.JSONField(default=dict, help_text="Original scraped data")

    class Meta:
        ordering = ["-motivation_score", "-created_at"]
        verbose_name = "Property Lead"

    def __str__(self):
        return f"{self.address}, {self.city} {self.state} | {self.lead_type} | {self.status}"

    @property
    def spread(self):
        """Profit spread: ARV - repair - asking price."""
        return float(self.estimated_arv) - float(self.estimated_repair) - float(self.asking_price)

    @property
    def mao(self):
        """Maximum Allowable Offer = 70% ARV - repairs - assignment fee."""
        return float(self.estimated_arv) * 0.70 - float(self.estimated_repair) - float(self.assignment_fee)

    def save(self, *args, **kwargs):
        if self.estimated_arv and not self.max_offer:
            self.max_offer = self.mao
        super().save(*args, **kwargs)


class InvestorBuyer(models.Model):
    """Cash buyer / investor for wholesale property assignments."""
    BUYER_TYPE_CHOICES = [
        ("fix_flip",    "Fix & Flip"),
        ("buy_hold",    "Buy & Hold / Rental"),
        ("developer",   "Developer / New Construction"),
        ("landlord",    "Landlord Portfolio"),
        ("fund",        "Investment Fund / REIT"),
        ("owner_occ",   "Owner Occupant"),
        ("other",       "Other"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200)
    company         = models.CharField(max_length=200, blank=True)
    email           = models.EmailField()
    phone           = models.CharField(max_length=20, blank=True)

    buyer_type      = models.CharField(max_length=20, choices=BUYER_TYPE_CHOICES, default="fix_flip")
    markets         = models.JSONField(default=list, help_text="List of city/state or zip codes they buy in")
    property_types  = models.JSONField(default=list, help_text="sfr, multi, land, etc.")
    budget_min      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_max      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    can_close_days  = models.IntegerField(default=14, help_text="How fast they can close (days)")
    cash_buyer      = models.BooleanField(default=True)
    proof_of_funds  = models.BooleanField(default=False, help_text="Has provided POF")

    deals_closed    = models.IntegerField(default=0, help_text="Total deals closed with us")
    total_volume    = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    avg_response_hrs = models.FloatField(default=0, help_text="Avg hours to respond to a deal")

    is_active       = models.BooleanField(default=True)
    last_deal_at    = models.DateTimeField(null=True, blank=True)
    source          = models.CharField(max_length=100, blank=True, help_text="reia, facebook, direct, referral")

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    notes           = models.TextField(blank=True)

    class Meta:
        ordering = ["-deals_closed", "-created_at"]
        verbose_name = "Investor Buyer"

    def __str__(self):
        return f"{self.name} | {self.buyer_type} | ${self.budget_min}-${self.budget_max} | {self.can_close_days}d close"


# ---------------------------------------------------------------------------
# CLIENT FILES: A-to-Z deal lifecycle document management
# ---------------------------------------------------------------------------

class ClientFile(models.Model):
    """Per-deal client folder tracking the full document lifecycle."""
    STATUS_CHOICES = [
        ("active",         "Active"),
        ("under_contract", "Under Contract"),
        ("closing",        "Closing"),
        ("closed",         "Closed"),
        ("dead",           "Dead"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_lead   = models.OneToOneField(PropertyLead, on_delete=models.CASCADE,
                                            related_name="client_file", null=True, blank=True)
    deal            = models.OneToOneField(Deal, on_delete=models.SET_NULL,
                                            null=True, blank=True, related_name="client_file")

    # Denormalized for quick display
    client_name     = models.CharField(max_length=200, help_text="Seller / property owner name")
    property_address = models.CharField(max_length=300)
    city            = models.CharField(max_length=100, blank=True)
    state           = models.CharField(max_length=2, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)

    # Deal numbers (snapshot)
    contract_price  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    assignment_fee  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    buyer_price     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_arv   = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Matched buyer (once assigned)
    buyer           = models.ForeignKey(InvestorBuyer, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="client_files")
    title_company   = models.CharField(max_length=200, blank=True)
    title_contact   = models.CharField(max_length=200, blank=True)
    title_email     = models.EmailField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    closed_at       = models.DateTimeField(null=True, blank=True)
    notes           = models.TextField(blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Client File"

    def __str__(self):
        return f"{self.property_address} | {self.client_name} | {self.status}"

    @property
    def document_count(self):
        return self.documents.count()

    @property
    def latest_document(self):
        return self.documents.order_by("-created_at").first()


class ClientDocument(models.Model):
    """Individual document in a client file timeline."""
    DOC_TYPE_CHOICES = [
        ("seller_outreach",    "Seller Outreach Email"),
        ("deal_sheet",         "Deal Sheet / Investor Presentation"),
        ("assignment_contract", "Assignment Contract"),
        ("buyer_pitch",        "Buyer Pitch Email"),
        ("title_engagement",   "Title Company Engagement"),
        ("signed_contract",    "Signed Contract"),
        ("closing_statement",  "Closing Statement"),
        ("payment_receipt",    "Payment Receipt"),
        ("addendum",           "Addendum / Amendment"),
        ("note",               "Internal Note"),
        ("other",              "Other"),
    ]
    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("sent",     "Sent"),
        ("signed",   "Signed"),
        ("final",    "Final"),
        ("voided",   "Voided"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_file     = models.ForeignKey(ClientFile, on_delete=models.CASCADE, related_name="documents")

    doc_type        = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES, db_index=True)
    title           = models.CharField(max_length=300)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Content - stored as branded HTML
    html_content    = models.TextField(blank=True, help_text="Branded HTML document content")
    plain_text      = models.TextField(blank=True, help_text="Plain text fallback")

    # Email tracking (for outreach docs)
    to_email        = models.EmailField(blank=True)
    sent_at         = models.DateTimeField(null=True, blank=True)
    opened_at       = models.DateTimeField(null=True, blank=True)

    # Metadata
    generated_by    = models.CharField(max_length=50, blank=True, help_text="Agent name: piper, rex, ace, hammer")
    slack_message_id = models.CharField(max_length=100, blank=True)
    supabase_id     = models.CharField(max_length=100, blank=True, help_text="Synced Supabase record ID")

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Client Document"

    def __str__(self):
        return f"{self.get_doc_type_display()} | {self.title} | {self.status}"

    @property
    def step_number(self):
        """Position in the deal timeline (1-based)."""
        order = [c[0] for c in self.DOC_TYPE_CHOICES]
        try:
            return order.index(self.doc_type) + 1
        except ValueError:
            return 99


# ---------------------------------------------------------------------------
# DEAL EVENTS: full timeline / audit trail for every deal action
# ---------------------------------------------------------------------------

class DealEvent(models.Model):
    """Immutable timeline entry for deal lifecycle tracking."""
    EVENT_TYPE_CHOICES = [
        ("stage_change",      "Stage Change"),
        ("contract_generated", "Contract Generated"),
        ("legal_review",      "Legal Review"),
        ("legal_approved",    "Legal Approved"),
        ("legal_flagged",     "Legal Issue Flagged"),
        ("doc_sent",          "Document Sent"),
        ("doc_signed",        "Document Signed"),
        ("title_engaged",     "Title Company Engaged"),
        ("emd_deposited",     "EMD Deposited"),
        ("emd_released",      "EMD Released"),
        ("invoice_created",   "Invoice Created"),
        ("invoice_paid",      "Invoice Paid"),
        ("call_logged",       "Call Logged"),
        ("email_sent",        "Email Sent"),
        ("email_received",    "Email Received"),
        ("note",              "Internal Note"),
        ("closing_scheduled", "Closing Scheduled"),
        ("funds_disbursed",   "Funds Disbursed"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal        = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="events")
    event_type  = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True)
    title       = models.CharField(max_length=300)
    detail      = models.TextField(blank=True)
    agent_name  = models.CharField(max_length=50, blank=True, help_text="Hive agent who performed action")
    metadata    = models.JSONField(default=dict, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Deal Event"

    def __str__(self):
        return f"{self.event_type} | {self.title} | {self.created_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# CALL LOG: mid-call tools, notes, outcomes, follow-ups
# ---------------------------------------------------------------------------

class CallLog(models.Model):
    """Track every phone/video call with sellers, buyers, title companies."""
    CALL_TYPE_CHOICES = [
        ("seller_intro",   "Seller Introduction"),
        ("seller_followup", "Seller Follow-up"),
        ("negotiation",    "Negotiation Call"),
        ("buyer_pitch",    "Buyer Pitch"),
        ("buyer_followup", "Buyer Follow-up"),
        ("title_company",  "Title Company"),
        ("legal_review",   "Legal / Compliance"),
        ("closing_call",   "Closing Coordination"),
        ("other",          "Other"),
    ]
    OUTCOME_CHOICES = [
        ("connected",     "Connected - Positive"),
        ("connected_neg", "Connected - Negative / Not Interested"),
        ("voicemail",     "Left Voicemail"),
        ("no_answer",     "No Answer"),
        ("callback",      "Callback Scheduled"),
        ("deal_advanced", "Deal Advanced to Next Stage"),
        ("dead",          "Lead Dead"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal            = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="calls",
                                         null=True, blank=True)
    property_lead   = models.ForeignKey(PropertyLead, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="calls")
    investor_buyer  = models.ForeignKey(InvestorBuyer, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="calls")

    call_type       = models.CharField(max_length=20, choices=CALL_TYPE_CHOICES)
    outcome         = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True)
    direction       = models.CharField(max_length=10,
                                        choices=[("outbound", "Outbound"), ("inbound", "Inbound")],
                                        default="outbound")

    # Who was on the call
    caller_agent    = models.CharField(max_length=50, help_text="Hive agent: piper, hammer, harrison")
    contact_name    = models.CharField(max_length=200, blank=True)
    contact_phone   = models.CharField(max_length=20, blank=True)
    contact_email   = models.EmailField(blank=True)

    # Timing
    started_at      = models.DateTimeField(default=timezone.now)
    duration_secs   = models.IntegerField(default=0)

    # Mid-call notes (agent fills these DURING the call)
    notes           = models.TextField(blank=True, help_text="Free-form notes during call")
    seller_mood     = models.CharField(max_length=20, blank=True,
                                        choices=[("motivated", "Motivated"), ("neutral", "Neutral"),
                                                 ("resistant", "Resistant"), ("hostile", "Hostile")])
    price_discussed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           help_text="Price mentioned on call")
    objections      = models.JSONField(default=list, blank=True,
                                        help_text="List of objections raised")
    commitments     = models.JSONField(default=list, blank=True,
                                        help_text="List of commitments/next steps agreed")

    # Follow-up
    followup_date   = models.DateTimeField(null=True, blank=True)
    followup_action = models.CharField(max_length=300, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Call Log"

    def __str__(self):
        return f"{self.call_type} | {self.contact_name} | {self.outcome} | {self.started_at:%Y-%m-%d}"


class CallbackTask(models.Model):
    """Phone callback task auto-created from inbound email replies.

    The wholesalers that close 1+/week answer replies on the PHONE within
    24 hours, not via email. Justine's IMAP monitor flags any inbound that
    looks motivated and creates a CallbackTask so the human (or VA) sees a
    queue with talking points pre-loaded by Hammer Knox.
    """
    PRIORITY_CHOICES = [
        ("urgent", "Urgent (call within 2h)"),
        ("high", "High (call within 24h)"),
        ("normal", "Normal (call within 48h)"),
        ("low", "Low (when convenient)"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In progress"),
        ("done", "Done"),
        ("voicemail", "Voicemail left"),
        ("no_answer", "No answer"),
        ("invalid", "Bad number"),
        ("snoozed", "Snoozed"),
    ]

    lead_id = models.CharField(max_length=64, blank=True, db_index=True,
                               help_text="UUID/ID of the related PropertyLead or LeadProfile")
    buyer_id = models.CharField(max_length=64, blank=True, db_index=True,
                                help_text="UUID of the related InvestorBuyer")
    contact_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    reason = models.TextField(blank=True)
    talking_points = models.TextField(blank=True)
    disposition_notes = models.TextField(blank=True)
    source = models.CharField(max_length=50, default="manual")
    assigned_to = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["status", "priority", "-created_at"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return f"[{self.priority}] {self.contact_name or self.phone or self.lead_id or 'unknown'} -- {self.status}"


class POFRequest(models.Model):
    """Proof-of-Funds collection from a cash buyer. Audit-required to
    prevent dispatching deals to buyers who cannot actually close."""
    STATUS_CHOICES = [
        ("invited", "Invited (link sent)"),
        ("submitted", "POF submitted, pending review"),
        ("approved", "Approved -- buyer can receive deals"),
        ("rejected", "Rejected (insufficient or expired)"),
        ("expired", "POF older than 90 days; resubmit"),
    ]
    buyer = models.ForeignKey("InvestorBuyer", on_delete=models.CASCADE,
                               related_name="pof_requests")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="invited",
                              db_index=True)
    pof_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                      help_text="Amount documented on the POF letter")
    pof_letter_url = models.CharField(max_length=1024, blank=True,
                                       help_text="Path to uploaded POF document")
    pof_letter_dated = models.DateField(null=True, blank=True,
                                         help_text="Date on the POF letter (must be < 90d old at deal time)")
    requested_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"POF[{self.status}] {self.buyer.name} ${self.pof_amount}"


class ConsentLedger(models.Model):
    """Immutable Prior Express Written Consent (PEWC) record.

    Required by 47 CFR 64.1200(f)(9) for any marketing autodialed,
    prerecorded, or AI-voice call. Once a contact signs the consent form,
    THIS row becomes the legal proof. Never edited, never deleted -- new
    revocations create separate `revoked=True` rows that supersede.

    What this row is proof of
    -------------------------
    1. The contact saw the disclosure (we store the exact text shown).
    2. The contact agreed (signature_text + signature_ip + timestamp).
    3. The contact authorized specific channels (channels JSON array).
    4. The number being called (phone, normalized).
    5. The seller name (Everlight Ventures, baked into disclosure_text).

    On any TCPA dispute, this row + Django's `auto_now_add` audit trail is
    what we hand to the lawyer.
    """
    CONTACT_TYPE_CHOICES = [
        ("seller", "Seller"),
        ("buyer", "Cash Buyer / Investor"),
        ("wholesaler", "JV Wholesaler"),
        ("title_company", "Title Company"),
        ("other", "Other"),
    ]
    CHANNEL_CHOICES = [
        ("ai_call", "AI Voice Call"),
        ("autodialed_call", "Autodialed Call"),
        ("prerecorded_voicemail", "Prerecorded Voicemail Drop"),
        ("sms_marketing", "Marketing SMS"),
        ("email_marketing", "Marketing Email"),
    ]

    # Who consented
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, db_index=True)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True, db_index=True)
    contact_phone = models.CharField(max_length=20, blank=True, db_index=True,
                                     help_text="Normalized 10-digit US number")

    # What they consented to
    channels = models.JSONField(default=list,
                                help_text="List of authorized channel codes from CHANNEL_CHOICES")
    disclosure_text = models.TextField(
        help_text="Exact disclosure text shown to the contact at consent time. NEVER edit retroactively.")

    # Proof of agreement
    signature_text = models.CharField(max_length=200,
                                       help_text="What the contact typed/checked as their signature")
    signature_ip = models.GenericIPAddressField(null=True, blank=True)
    signature_user_agent = models.TextField(blank=True)
    consent_token = models.CharField(max_length=64, unique=True, db_index=True,
                                      help_text="Random token in the consent URL")

    # Lifecycle
    revoked = models.BooleanField(default=False, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=200, blank=True)
    revoked_via = models.CharField(max_length=50, blank=True,
                                    help_text="STOP_sms | unsubscribe_email | revoke_form | request_phone")

    # ── Forensic anchors for legal defense (TCPA / FTSA / state DNC) ──
    # Outbound = the disclosure WE sent them (proves they saw it)
    outbound_twilio_sid = models.CharField(max_length=64, blank=True, db_index=True,
        help_text="Twilio SID of outbound disclosure SMS (subpoena anchor)")
    outbound_sent_at = models.DateTimeField(null=True, blank=True,
        help_text="Server-side timestamp when disclosure was sent")
    # Inbound = their reply that constitutes the signature (E-SIGN Act)
    inbound_twilio_sid = models.CharField(max_length=64, blank=True, db_index=True,
        help_text="Twilio SID of inbound consent reply (subpoena anchor)")
    inbound_body_verbatim = models.TextField(blank=True,
        help_text="Exact reply body from contact -- their consent signature")
    inbound_received_at = models.DateTimeField(null=True, blank=True,
        help_text="Twilio server-side timestamp when reply landed")
    # Strong tie-back to the property lead so legal proof links to the deal
    property_lead_id = models.CharField(max_length=100, blank=True, db_index=True,
        help_text="PropertyLead.id this consent belongs to (string for UUID compat)")
    # Raw evidence payloads (kept verbatim for forensic completeness)
    evidence_payload_json = models.TextField(blank=True,
        help_text="Raw Twilio webhook/API payloads for outbound + inbound (audit-only)")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["contact_phone", "revoked", "-created_at"]),
            models.Index(fields=["contact_email", "revoked", "-created_at"]),
            models.Index(fields=["outbound_twilio_sid"]),
            models.Index(fields=["inbound_twilio_sid"]),
            models.Index(fields=["property_lead_id"]),
        ]

    def __str__(self):
        status = "revoked" if self.revoked else "active"
        return f"[{self.contact_type}] {self.contact_name} ({self.contact_phone or self.contact_email}) -- {status}"

    def has_channel(self, channel: str) -> bool:
        return not self.revoked and channel in (self.channels or [])

    def is_legally_defensible(self) -> bool:
        """True only if we have the full forensic chain for this consent.

        Used by the audit + by the consent-proof-pack view. Defensibility
        requires: outbound disclosure SID + inbound reply SID + verbatim body.
        """
        return bool(
            self.outbound_twilio_sid
            and self.inbound_twilio_sid
            and self.inbound_body_verbatim
            and self.channels
            and not self.revoked
        )


class BankReconciliation(models.Model):
    """Monthly bank reconciliation record. Audit-required (Section 1: Financial)."""
    period_year = models.IntegerField(db_index=True)
    period_month = models.IntegerField(db_index=True, help_text="1-12")
    bank_account_label = models.CharField(max_length=100, default="primary_checking")
    statement_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    book_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reconciled_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    in_transit_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_checks = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discrepancies_count = models.IntegerField(default=0)
    discrepancies_notes = models.TextField(blank=True)
    statement_pdf_url = models.CharField(max_length=1024, blank=True)
    reconciled = models.BooleanField(default=False, db_index=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.CharField(max_length=100, blank=True, help_text="Rich / CPA name")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_year", "-period_month"]
        unique_together = [("period_year", "period_month", "bank_account_label")]

    def __str__(self):
        return f"BankRec {self.period_year}-{self.period_month:02d} {self.bank_account_label} {'OK' if self.reconciled else 'PENDING'}"


class RESPAAuditLog(models.Model):
    """Tracks any payment that could be construed as a referral or kickback
    under RESPA Section 8. The audit module looks for unaccounted-for entries.
    """
    PAYMENT_TYPE_CHOICES = [
        ("referral", "Referral fee"),
        ("birddog", "Bird-dog finder fee"),
        ("commission_split", "Commission split (JV)"),
        ("vendor_kickback_check", "Vendor kickback check"),
        ("other", "Other"),
    ]
    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPE_CHOICES, db_index=True)
    payee_name = models.CharField(max_length=200)
    payee_role = models.CharField(max_length=100, blank=True,
                                   help_text="Title agent / lender / inspector / contractor / other")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deal = models.ForeignKey("Deal", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="respa_payments")
    written_disclosure_present = models.BooleanField(default=False,
                                                      help_text="RESPA-compliant disclosure on file?")
    disclosure_url = models.CharField(max_length=1024, blank=True)
    paid_at = models.DateField()
    reviewed_by_attorney = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"RESPA {self.payment_type} ${self.amount} -> {self.payee_name}"


class InsurancePolicy(models.Model):
    """E&O, GL, and other coverage tracking. Audit-required (Section 5: Risk)."""
    POLICY_TYPE_CHOICES = [
        ("eo", "Errors & Omissions"),
        ("gl", "General Liability"),
        ("cyber", "Cyber Liability"),
        ("auto", "Commercial Auto"),
        ("workers_comp", "Workers Comp"),
        ("umbrella", "Umbrella"),
    ]
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPE_CHOICES, db_index=True)
    carrier = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100)
    coverage_limit = models.DecimalField(max_digits=12, decimal_places=2)
    deductible = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    annual_premium = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    expiration_date = models.DateField(db_index=True)
    certificate_url = models.CharField(max_length=1024, blank=True,
                                        help_text="Certificate of Insurance PDF")
    states_covered = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"{self.get_policy_type_display()} {self.carrier} ${self.coverage_limit} until {self.expiration_date}"


class GBPListing(models.Model):
    """Google Business Profile tracking. Audit-required (Section 6: Reputation)."""
    name = models.CharField(max_length=200, default="Everlight Ventures")
    primary_market = models.CharField(max_length=100, default="Atlanta, GA")
    phone = models.CharField(max_length=20, default="+14048004380")
    website = models.URLField(default="https://everlightventures.io")
    google_place_id = models.CharField(max_length=200, blank=True)
    verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    review_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    last_post_at = models.DateTimeField(null=True, blank=True,
                                         help_text="Last GBP post (for SEO refresh cadence)")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"GBP[{self.primary_market}] {'verified' if self.verified else 'unverified'} ({self.review_count} reviews)"


class AgentRoster(models.Model):
    """Formal team / AI-agent roster. Audit-required (Section 7: Team)."""
    AGENT_TYPE_CHOICES = [
        ("human", "Human team member"),
        ("va", "Virtual Assistant (contractor)"),
        ("ai", "AI agent (Hive Mind)"),
        ("vendor", "External vendor (CPA / attorney / title)"),
    ]
    name = models.CharField(max_length=200)
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPE_CHOICES, db_index=True)
    role = models.CharField(max_length=200, help_text="e.g. Acquisitions, Disposition, Compliance")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    employment_start = models.DateField(null=True, blank=True)
    code_of_conduct_signed = models.BooleanField(default=False,
                                                  help_text="For human/VA: signed code of conduct?")
    code_of_conduct_signed_at = models.DateTimeField(null=True, blank=True)
    background_check_complete = models.BooleanField(default=False)
    mfa_enrolled = models.BooleanField(default=False,
                                        help_text="Django MFA TOTP device enrolled (if has admin access)?")
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_active", "agent_type", "name"]

    def __str__(self):
        return f"[{self.agent_type}] {self.name} ({self.role}){' INACTIVE' if not self.is_active else ''}"


class TestimonialCollection(models.Model):
    """Closed-deal testimonials. Audit-required (Section 6: Reputation).
    FTC-compliant: must reflect typical experience; not cherry-picked highest-money."""
    deal = models.ForeignKey("Deal", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="testimonials")
    contact_name = models.CharField(max_length=200)
    contact_role = models.CharField(max_length=50,
                                     choices=[("seller", "Seller"), ("buyer", "Buyer"),
                                              ("title", "Title Co"), ("attorney", "Attorney")])
    quote_text = models.TextField()
    publication_permission = models.CharField(max_length=30,
                                                choices=[("full_name", "Full name + market OK"),
                                                         ("first_name", "First name + market OK"),
                                                         ("anonymous", "Anonymous only"),
                                                         ("no_publish", "Internal use only")])
    market_city = models.CharField(max_length=100, blank=True)
    deal_assignment_fee_range = models.CharField(max_length=50, blank=True,
                                                   help_text="e.g. '$5K-$10K' for FTC typicality context")
    received_at = models.DateField()
    published_at = models.DateField(null=True, blank=True,
                                     help_text="When published to landing page / GBP / etc.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"[{self.contact_role}] {self.contact_name} -- {self.quote_text[:60]}..."
