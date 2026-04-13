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
