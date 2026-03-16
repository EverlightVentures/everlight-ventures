# Everlight Ventures -- Slack Support Bot Architecture

Version: 1.0
Author: Architect Agent
Date: 2026-03-06
Status: DESIGN (not yet implemented)

---

## 1. Overview

A unified Slack-based customer support system for all Everlight Ventures products. The bot
lives in the Everlight Ventures Slack workspace and serves two functions:

1. **Inbound support** -- AI-powered customer support across all product lines
2. **Outbound notifications** -- payment receipts, order confirmations, sales alerts

All webhook logic lives inside the existing Django project at
`/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard/` as a new Django app called `slackbot`.

---

## 2. System Diagram

```
                          CUSTOMERS
                             |
              +--------------+--------------+
              |              |              |
         Slack DM      Email (SMTP)    Website Form
              |              |              |
              v              v              v
     +--------+--------+    |         Lovable/Supabase
     |  Slack Events   |    |              |
     |  API (Socket)   |    |              |
     +--------+--------+    |              |
              |              |              |
              v              v              v
     +-------------------------------------------+
     |         DJANGO  (hive_dashboard)           |
     |                                            |
     |  slackbot/                                 |
     |    views.py       <-- Slack event handler  |
     |    webhooks.py    <-- Stripe/Supabase hooks|
     |    bot.py         <-- Claude AI responder  |
     |    router.py      <-- channel/product map  |
     |    knowledge.py   <-- product KB loader    |
     |    escalation.py  <-- escalation rules     |
     |    models.py      <-- SupportTicket model  |
     |    notifications.py <-- outbound Slack msgs|
     |                                            |
     |  Existing apps:                            |
     |    taskboard/     <-- ticket escalation    |
     |    funnel/        <-- lead tracking        |
     +--------+--+--+----------------------------+
              |  |  |
     +--------+  |  +--------+
     |           |            |
     v           v            v
  Claude API  Supabase    Stripe API
  (responses) (customer   (payments)
               data)

     Outbound flow (notifications):
     Stripe --> webhooks.py --> notifications.py --> Slack channel
     KDP API --> management command (cron) --> Slack channel
     Supabase edge function --> webhooks.py --> Slack channel
```

---

## 3. Slack Workspace Channel Structure

### Support Channels (bot monitors these)

| Channel               | Purpose                                      | Bot Behavior              |
|------------------------|----------------------------------------------|---------------------------|
| #support-onyx          | Onyx POS billing, features, setup            | Auto-respond, escalate    |
| #support-hivemind      | Hive Mind waitlist, onboarding               | Auto-respond, escalate    |
| #support-publishing    | Book orders, educator requests               | Auto-respond, escalate    |
| #support-alleykingz    | Game issues, NFT questions                   | Auto-respond, escalate    |
| #support-him-loadout   | Affiliate order tracking                     | Auto-respond, escalate    |
| #support-logistics     | Shipping quotes, tracking                    | Auto-respond, escalate    |
| #support-general       | Catch-all for unrouted inquiries             | Auto-respond, escalate    |

### Internal / Notification Channels

| Channel               | Purpose                                      | Bot Behavior              |
|------------------------|----------------------------------------------|---------------------------|
| #payments              | Stripe webhook receipts, subscription alerts | Post-only (no responses)  |
| #orders                | Order confirmations, shipping updates        | Post-only (no responses)  |
| #kdp-sales             | Daily Amazon KDP sales summary               | Post-only (cron)          |
| #escalations           | Tickets escalated to founder                 | Post + mention @founder   |
| #bot-logs              | Debug logs, error alerts                     | Post-only (diagnostics)   |

### Channel-to-Product Mapping (router.py)

```python
CHANNEL_PRODUCT_MAP = {
    "support-onyx": "onyx_pos",
    "support-hivemind": "hive_mind",
    "support-publishing": "publishing",
    "support-alleykingz": "alley_kingz",
    "support-him-loadout": "him_loadout",
    "support-logistics": "logistics",
    "support-general": "general",
}
```

---

## 4. Django App Structure

New app: `slackbot/` inside `hive_dashboard/`

```
hive_dashboard/
  slackbot/
    __init__.py
    apps.py
    models.py           # SupportTicket, SupportMessage
    views.py            # Slack event endpoint, interactive components
    webhooks.py         # Stripe, Supabase, KDP webhook receivers
    bot.py              # Claude API integration -- generates responses
    router.py           # Maps channels to products, selects KB
    knowledge.py        # Loads product-specific knowledge bases
    escalation.py       # Rules for when to escalate to human
    notifications.py    # Sends formatted messages to Slack channels
    email_bridge.py     # Processes forwarded emails from support@ address
    prompts/
      base.py           # Shared system prompt components
      onyx_pos.py       # Onyx POS product knowledge + prompt
      hive_mind.py      # Hive Mind product knowledge + prompt
      publishing.py     # Publishing product knowledge + prompt
      alley_kingz.py    # Alley Kingz product knowledge + prompt
      him_loadout.py    # HIM Loadout product knowledge + prompt
      logistics.py      # Everlight Logistics product knowledge + prompt
    management/
      commands/
        kdp_daily_summary.py   # Cron job: pull KDP sales, post to Slack
        sync_supabase_customers.py  # Sync customer data from Supabase
    templates/
      slackbot/
        ticket_detail.html      # Admin view of ticket in Django
    urls.py
    admin.py
```

### URL Registration

In `hive_dashboard/urls.py`, add:

```python
path('slack/', include('slackbot.urls')),
```

### slackbot/urls.py

```python
from django.urls import path
from . import views, webhooks

app_name = "slackbot"

urlpatterns = [
    # Slack Events API endpoint (receives all Slack events)
    path("events/", views.slack_events, name="slack_events"),

    # Slack interactive components (button clicks, modals)
    path("interactive/", views.slack_interactive, name="slack_interactive"),

    # Stripe webhook receiver
    path("webhook/stripe/", webhooks.stripe_webhook, name="stripe_webhook"),

    # Supabase webhook receiver (new signups, form submissions)
    path("webhook/supabase/", webhooks.supabase_webhook, name="supabase_webhook"),

    # KDP sales webhook (or manual trigger)
    path("webhook/kdp/", webhooks.kdp_sales_webhook, name="kdp_webhook"),

    # Health check
    path("health/", views.health_check, name="health"),
]
```

---

## 5. Data Models

### slackbot/models.py

```python
from django.db import models
from django.utils import timezone


class SupportTicket(models.Model):
    PRODUCT_CHOICES = [
        ("onyx_pos", "Onyx POS"),
        ("hive_mind", "Hive Mind"),
        ("publishing", "Publishing"),
        ("alley_kingz", "Alley Kingz"),
        ("him_loadout", "HIM Loadout"),
        ("logistics", "Everlight Logistics"),
        ("general", "General"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("ai_handled", "AI Handled"),
        ("escalated", "Escalated to Human"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    SOURCE_CHOICES = [
        ("slack", "Slack"),
        ("email", "Email"),
        ("web", "Website Form"),
    ]

    ticket_id = models.CharField(max_length=20, unique=True, db_index=True)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="slack")

    # Customer info
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    slack_user_id = models.CharField(max_length=50, blank=True)
    slack_channel_id = models.CharField(max_length=50, blank=True)
    slack_thread_ts = models.CharField(max_length=50, blank=True)

    # Content
    subject = models.CharField(max_length=500)
    initial_message = models.TextField()

    # AI handling
    ai_response_count = models.IntegerField(default=0)
    ai_confidence = models.FloatField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True)

    # Linkage to existing taskboard (for escalated tickets)
    taskboard_item = models.ForeignKey(
        "taskboard.TaskItem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
    )

    # Supabase customer ID (if matched)
    supabase_customer_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "status"]),
            models.Index(fields=["customer_email"]),
        ]

    def __str__(self):
        return f"[{self.ticket_id}] {self.subject} ({self.get_status_display()})"

    def generate_ticket_id(self):
        """Generate ticket ID like EV-2026-0001."""
        year = timezone.now().year
        last = SupportTicket.objects.filter(
            ticket_id__startswith=f"EV-{year}-"
        ).count()
        self.ticket_id = f"EV-{year}-{last + 1:04d}"

    def escalate(self, reason):
        self.status = "escalated"
        self.escalation_reason = reason
        self.save()


class SupportMessage(models.Model):
    """Individual message in a support conversation."""
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("ai", "AI Bot"),
        ("human", "Human Agent"),
    ]

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    slack_ts = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class PaymentEvent(models.Model):
    """Log of Stripe webhook events processed."""
    stripe_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    customer_email = models.EmailField(blank=True)
    product = models.CharField(max_length=50, blank=True)
    amount_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default="usd")
    metadata = models.JSONField(default=dict)
    slack_message_ts = models.CharField(max_length=50, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type}: ${self.amount_cents / 100:.2f} ({self.customer_email})"
```

---

## 6. Claude API Prompt Architecture

### 6.1 Base System Prompt (prompts/base.py)

```python
BASE_SYSTEM_PROMPT = """
You are the Everlight Ventures customer support assistant. You represent
all Everlight Ventures products with professionalism and clarity.

Rules:
- Be helpful, concise, and friendly
- Never make up information -- if you do not know, say so and offer to escalate
- Never share internal pricing, margins, or business strategy
- For billing disputes or refund requests, always escalate to a human
- Include the ticket ID in every response: [Ticket: {ticket_id}]
- If the customer seems frustrated, acknowledge their frustration first
- For technical issues, ask for specific error messages or screenshots
- Sign off as "Everlight Support" (never use a personal name)

You have access to the following product knowledge base for this conversation:
{product_kb}

Customer info (if available):
- Name: {customer_name}
- Email: {customer_email}
- Product: {product_name}
- Previous tickets: {previous_ticket_count}
"""
```

### 6.2 Product-Specific Knowledge (one file per product)

**prompts/onyx_pos.py**

```python
ONYX_POS_KB = """
PRODUCT: Onyx POS
TYPE: Point-of-sale system for small businesses

FEATURES:
- Inventory management
- Sales tracking and reporting
- Customer management
- Receipt printing
- Multi-location support

PRICING:
- Starter: $29/month (1 register, basic reports)
- Growth: $79/month (3 registers, advanced analytics)
- Enterprise: Custom pricing

COMMON ISSUES:
- Setup: Walk through initial configuration, printer setup
- Billing: Explain plan differences, direct refund requests to human
- Features: Explain what is available on their plan
- Integration: POS integrates with Stripe for payments

ESCALATION TRIGGERS:
- Hardware/printer issues beyond basic troubleshooting
- Refund or billing dispute
- Data loss or sync errors
- Account security concerns
"""
```

**prompts/hive_mind.py**

```python
HIVE_MIND_KB = """
PRODUCT: Hive Mind
TYPE: AI-powered SaaS platform (currently in waitlist phase)

STATUS: Pre-launch. Accepting waitlist signups.

COMMON QUESTIONS:
- Waitlist position: We process in order, no specific dates yet
- Pricing: Will be announced at launch
- Features: AI workspace orchestration, multi-agent collaboration
- Beta access: Selected users will be invited in waves

ESCALATION TRIGGERS:
- Partnership or integration inquiries
- Press or media requests
- Enterprise/bulk waitlist requests
"""
```

**prompts/publishing.py**

```python
PUBLISHING_KB = """
PRODUCT: Everlight Publishing
TYPE: Book publishing (Amazon KDP, direct sales)

OFFERINGS:
- Children's books
- Educational materials
- Activity books

COMMON QUESTIONS:
- Book orders: Direct to Amazon listing or website
- Educator/bulk pricing: Escalate to human for custom quotes
- Author inquiries: Escalate to human
- Shipping: Standard Amazon shipping applies for KDP orders
- Direct orders: Fulfilled via Everlight Logistics

ESCALATION TRIGGERS:
- Bulk/educator order requests (10+ copies)
- Author collaboration proposals
- Print quality complaints
- Missing or damaged orders
"""
```

**prompts/alley_kingz.py**

```python
ALLEY_KINGZ_KB = """
PRODUCT: Alley Kingz
TYPE: Web3 game / NFT project

COMMON QUESTIONS:
- Gameplay: Explain game mechanics, how to start
- NFT minting: Wallet setup, mint process, gas fees
- NFT utility: In-game benefits of holding NFTs
- Technical: Browser requirements, wallet compatibility

ESCALATION TRIGGERS:
- Lost NFT or failed transaction (need tx hash)
- Smart contract issues
- Account recovery
- Marketplace listing problems
"""
```

**prompts/him_loadout.py**

```python
HIM_LOADOUT_KB = """
PRODUCT: HIM Loadout
TYPE: Affiliate/curated product drops

COMMON QUESTIONS:
- Order status: Check tracking via order ID or email
- Returns: 30-day return policy, must be unused
- Product authenticity: All items sourced from verified suppliers
- Affiliate program: Explain commission structure

ESCALATION TRIGGERS:
- Refund requests
- Product defect claims
- Affiliate payout disputes
- Order not received after 14 days
"""
```

**prompts/logistics.py**

```python
LOGISTICS_KB = """
PRODUCT: Everlight Logistics
TYPE: Shipping and fulfillment service

SERVICES:
- Domestic shipping (USPS, UPS, FedEx)
- Package tracking
- Shipping quotes
- Fulfillment for Everlight products

COMMON QUESTIONS:
- Shipping quotes: Collect weight, dimensions, origin, destination
- Tracking: Look up by tracking number
- Delivery times: Standard 3-7 days, Express 1-3 days
- International: Currently US domestic only

ESCALATION TRIGGERS:
- Lost packages (no scan in 7+ days)
- Damaged shipments (need photos)
- Commercial/bulk shipping contracts
- International shipping requests
"""
```

### 6.3 Claude API Call Structure (bot.py)

```python
import anthropic
from django.conf import settings

def generate_support_response(ticket, customer_message, product_kb):
    """
    Call Claude API to generate a support response.
    Returns: dict with 'response', 'confidence', 'should_escalate', 'escalation_reason'
    """
    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    system_prompt = BASE_SYSTEM_PROMPT.format(
        ticket_id=ticket.ticket_id,
        product_kb=product_kb,
        customer_name=ticket.customer_name or "Unknown",
        customer_email=ticket.customer_email or "Not provided",
        product_name=ticket.get_product_display(),
        previous_ticket_count=SupportTicket.objects.filter(
            customer_email=ticket.customer_email
        ).exclude(pk=ticket.pk).count(),
    )

    # Build conversation history from ticket messages
    messages = []
    for msg in ticket.messages.all():
        role = "user" if msg.role == "customer" else "assistant"
        messages.append({"role": role, "content": msg.content})

    # Add current message
    messages.append({"role": "user", "content": customer_message})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    reply_text = response.content[0].text

    # Check for escalation signals in the response
    should_escalate = any(phrase in reply_text.lower() for phrase in [
        "let me connect you with",
        "i'll escalate this",
        "a team member will",
    ])

    return {
        "response": reply_text,
        "confidence": 0.85,  # TODO: implement confidence scoring
        "should_escalate": should_escalate,
        "escalation_reason": "",
    }
```

---

## 7. Escalation Rules (escalation.py)

```python
ESCALATION_RULES = {
    # --- Always escalate ---
    "always_escalate_keywords": [
        "refund",
        "cancel my subscription",
        "billing dispute",
        "charged incorrectly",
        "speak to a human",
        "talk to someone",
        "lawyer",
        "legal",
        "sue",
        "BBB",
        "attorney general",
    ],

    # --- Escalate after N AI responses with no resolution ---
    "max_ai_responses_before_escalation": 3,

    # --- Escalate if customer sends ALL CAPS (likely frustrated) ---
    "caps_ratio_threshold": 0.7,  # >70% uppercase chars = escalate

    # --- Product-specific escalation triggers ---
    "product_triggers": {
        "onyx_pos": ["data loss", "sync error", "hardware", "printer not working"],
        "publishing": ["bulk order", "educator", "damaged", "missing order"],
        "alley_kingz": ["lost nft", "failed transaction", "smart contract"],
        "him_loadout": ["refund", "defect", "payout"],
        "logistics": ["lost package", "damaged shipment", "international"],
    },
}


def should_escalate(ticket, message_text):
    """
    Returns (bool, str) -- (should_escalate, reason)
    """
    text_lower = message_text.lower()

    # Check always-escalate keywords
    for keyword in ESCALATION_RULES["always_escalate_keywords"]:
        if keyword in text_lower:
            return True, f"Keyword trigger: '{keyword}'"

    # Check AI response count
    if ticket.ai_response_count >= ESCALATION_RULES["max_ai_responses_before_escalation"]:
        return True, f"AI response limit reached ({ticket.ai_response_count} responses)"

    # Check frustration (caps ratio)
    alpha_chars = [c for c in message_text if c.isalpha()]
    if alpha_chars:
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if caps_ratio >= ESCALATION_RULES["caps_ratio_threshold"]:
            return True, "Customer appears frustrated (high caps ratio)"

    # Check product-specific triggers
    triggers = ESCALATION_RULES["product_triggers"].get(ticket.product, [])
    for trigger in triggers:
        if trigger in text_lower:
            return True, f"Product-specific trigger: '{trigger}'"

    return False, ""
```

### Escalation Flow

```
Customer message arrives
    |
    v
should_escalate() check
    |
    +-- YES --> 1. Set ticket.status = "escalated"
    |           2. Create TaskItem in taskboard (linked to ticket)
    |           3. Post to #escalations with @founder mention
    |           4. Reply to customer: "I'm connecting you with a team member..."
    |
    +-- NO  --> 1. Call Claude API for response
                2. Post AI response in thread
                3. Increment ai_response_count
                4. Log SupportMessage
```

---

## 8. Webhook Data Flows

### 8.1 Stripe Payment --> Slack Notification

```
Stripe (checkout.session.completed, invoice.paid, etc.)
    |
    v
POST /slack/webhook/stripe/
    |
    v
webhooks.py:stripe_webhook()
    1. Verify Stripe signature (STRIPE_WEBHOOK_SECRET)
    2. Parse event type
    3. Create PaymentEvent record
    4. Format Slack message block
    5. Post to #payments channel via Slack Web API
    6. If subscription event --> also post to #support-{product}
    7. Trigger email confirmation (via Django send_mail or Resend API)
```

**Stripe events to handle:**

| Stripe Event                          | Slack Channel  | Action                          |
|----------------------------------------|----------------|---------------------------------|
| checkout.session.completed             | #payments      | New sale notification           |
| invoice.paid                           | #payments      | Subscription renewal            |
| invoice.payment_failed                 | #payments      | Failed payment alert            |
| customer.subscription.deleted          | #payments      | Cancellation alert              |
| customer.subscription.updated          | #payments      | Plan change notification        |

**Slack message format for payments:**

```
---------------------------------------------
NEW PAYMENT RECEIVED
Product: Onyx POS (Growth Plan)
Customer: jane@example.com
Amount: $79.00 USD
Type: Subscription renewal
Stripe ID: pi_xxxxxxxxxxxxx
---------------------------------------------
```

### 8.2 Email --> Slack Bridge

```
Customer sends email to support@everlightventures.io
    |
    v
Email forwarding rule (Proton Mail / Google Workspace)
    --> Forward to Slack channel via Slack email integration
    OR
    --> Forward to POST /slack/webhook/email/ (custom endpoint)
    |
    v
email_bridge.py:process_inbound_email()
    1. Parse sender, subject, body
    2. Route to correct #support-{product} channel based on subject/keywords
    3. Create SupportTicket (source="email")
    4. Post to Slack channel as new thread
    5. Bot responds in thread (same Claude AI flow)
    6. If customer replies to email --> new message in same Slack thread
```

**Email routing keywords:**

| Keyword in Subject/Body      | Routes to            |
|-------------------------------|----------------------|
| POS, register, onyx          | #support-onyx        |
| hive mind, waitlist, saas    | #support-hivemind    |
| book, publish, order, ISBN   | #support-publishing  |
| alley kingz, NFT, game      | #support-alleykingz  |
| loadout, affiliate           | #support-him-loadout |
| shipping, tracking, delivery | #support-logistics   |
| (no match)                   | #support-general     |

### 8.3 Amazon KDP Sales --> Slack Daily Summary

```
Cron job (daily at 8:00 AM PT)
    |
    v
python manage.py kdp_daily_summary
    1. Pull sales data from KDP Reports API (or scrape)
    2. Aggregate: units sold, revenue, by title
    3. Format summary
    4. Post to #kdp-sales channel
```

**KDP summary format:**

```
---------------------------------------------
KDP DAILY SALES REPORT -- 2026-03-05

Total Units: 12
Total Revenue: $47.82

By Title:
  "ABC Adventures" -- 5 units ($19.95)
  "123 Fun Book" -- 4 units ($15.96)
  "Color My World" -- 3 units ($11.91)

MTD: 87 units / $341.22
---------------------------------------------
```

### 8.4 Supabase --> Slack (New Signups, Form Submissions)

```
Supabase Edge Function (triggered on INSERT to signups/contacts table)
    |
    v
POST /slack/webhook/supabase/
    1. Verify Supabase webhook secret
    2. Parse event (new_signup, contact_form, waitlist_join)
    3. Create Lead in funnel app (or update existing)
    4. Post notification to appropriate channel
    5. If contact form --> create SupportTicket, route to support channel
```

---

## 9. Slack App Configuration

### 9.1 Required Slack App Scopes (Bot Token)

```
channels:history       -- Read messages in public channels
channels:join          -- Join public channels
chat:write             -- Send messages
commands               -- Slash commands (future)
groups:history         -- Read messages in private channels
im:history             -- Read DMs to the bot
im:write               -- Send DMs
reactions:write        -- Add reactions to messages
users:read             -- Look up user info
users:read.email       -- Get user email addresses
files:read             -- Read uploaded files (screenshots, etc.)
```

### 9.2 Event Subscriptions

Subscribe to these Slack events (sent to `/slack/events/`):

```
message.channels       -- Messages in public channels bot is in
message.groups         -- Messages in private channels bot is in
message.im             -- Direct messages to the bot
app_mention            -- When someone @mentions the bot
member_joined_channel  -- Track when customers join support channels
```

### 9.3 Environment Variables

Add to Django settings or `.env`:

```
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-xxxxxxxxxxxx       # For Socket Mode (optional)
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxxxxxxxxxx
SUPABASE_WEBHOOK_SECRET=xxxxxxxxxxxx
SLACK_FOUNDER_USER_ID=U0XXXXXXXX        # For @mention on escalation
```

---

## 10. Django Settings Changes

Add to `hive_dashboard/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'slackbot',
]

# -- Slack Support Bot --
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_FOUNDER_USER_ID = os.environ.get("SLACK_FOUNDER_USER_ID", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
```

---

## 11. Request Verification (Security)

### Slack Request Verification (views.py)

All incoming Slack requests must be verified using the signing secret:

```python
import hashlib
import hmac
import time
from django.conf import settings

def verify_slack_request(request):
    """Verify that the request actually came from Slack."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Reject requests older than 5 minutes (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{request.body.decode()}"
    my_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)
```

### Stripe Webhook Verification

```python
import stripe

def verify_stripe_webhook(request):
    """Verify Stripe webhook signature."""
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", "")
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
    return event
```

---

## 12. Full Message Handling Flow

```
1. Slack sends event to POST /slack/events/
2. views.py:slack_events() receives it
3. Verify Slack signature
4. If event.type == "url_verification" --> return challenge (Slack setup)
5. If event.type == "event_callback":
    a. Extract channel, user, text, thread_ts
    b. Ignore bot's own messages (check bot_id)
    c. router.py: determine product from channel name
    d. Look up or create SupportTicket (by thread_ts or new)
    e. Save customer message as SupportMessage
    f. escalation.py: check if should escalate
    g. If escalate:
        - Update ticket status
        - Create TaskItem in taskboard
        - Post escalation notice to #escalations
        - Reply in thread: "Connecting you with a team member..."
    h. If not escalate:
        - knowledge.py: load product KB
        - bot.py: call Claude API with conversation history + KB
        - Post AI response in Slack thread
        - Save AI response as SupportMessage
        - Increment ai_response_count
6. Return 200 OK to Slack (must respond within 3 seconds)
```

### Async Processing Note

Slack requires a 200 response within 3 seconds. The Claude API call will take
longer than that. Two options:

**Option A -- Background thread (simpler, good for low volume):**

```python
import threading

def slack_events(request):
    # ... verify, parse ...
    threading.Thread(target=handle_support_message, args=(event_data,)).start()
    return JsonResponse({"ok": True})
```

**Option B -- Django-Q or Celery task queue (better for scale):**

```python
from django_q.tasks import async_task

def slack_events(request):
    # ... verify, parse ...
    async_task("slackbot.bot.handle_support_message", event_data)
    return JsonResponse({"ok": True})
```

Recommendation: Start with Option A. Move to Option B if volume exceeds ~50
tickets/day.

---

## 13. Integration with Existing Apps

### Taskboard Integration (escalated tickets)

When a ticket escalates, create a TaskItem:

```python
from taskboard.models import TaskTemplate, TaskItem

def create_escalation_task(ticket):
    template, _ = TaskTemplate.objects.get_or_create(
        name="Support Escalation",
        defaults={
            "category": "general",
            "description": "Customer support ticket escalated to human",
            "schema": {"fields": [
                {"name": "resolution", "label": "Resolution", "type": "textarea", "required": True},
                {"name": "follow_up", "label": "Follow-up needed?", "type": "checkbox", "required": False},
            ]},
        },
    )
    task = TaskItem.objects.create(
        template=template,
        title=f"[{ticket.ticket_id}] {ticket.subject}",
        description=(
            f"Product: {ticket.get_product_display()}\n"
            f"Customer: {ticket.customer_email}\n"
            f"Escalation reason: {ticket.escalation_reason}\n"
            f"AI responses given: {ticket.ai_response_count}\n"
            f"Source: {ticket.get_source_display()}"
        ),
        status="pending",
        priority=2,  # High
        source_agent="slackbot",
        batch_id=f"support-{ticket.ticket_id}",
    )
    ticket.taskboard_item = task
    ticket.save()
    return task
```

### Funnel Integration (lead tracking)

When a new customer contacts support, check if they exist as a Lead:

```python
from funnel.models import Lead, FunnelEvent

def track_support_contact(ticket):
    if not ticket.customer_email:
        return
    lead = Lead.objects.filter(email=ticket.customer_email).first()
    if lead:
        FunnelEvent.objects.create(
            lead=lead,
            event_type="support_contact",
            metadata={
                "ticket_id": ticket.ticket_id,
                "product": ticket.product,
                "source": ticket.source,
            },
        )
```

---

## 14. Deployment Requirements

### Python Dependencies (add to requirements.txt)

```
slack-sdk>=3.27.0
slack-bolt>=1.18.0       # Optional: if using Bolt framework
anthropic>=0.25.0
stripe>=8.0.0
supabase>=2.0.0          # For Supabase client queries
```

### Cron Jobs

```cron
# KDP daily sales summary -- 8:00 AM PT
0 8 * * * cd /path/to/hive_dashboard && python manage.py kdp_daily_summary

# Sync Supabase customers -- every 6 hours
0 */6 * * * cd /path/to/hive_dashboard && python manage.py sync_supabase_customers
```

### Nginx / Reverse Proxy

The Slack Events API and webhooks need to be publicly accessible. Add to nginx:

```nginx
location /slack/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Alternatively, use ngrok during development:

```bash
ngrok http 8000
# Then set Slack Events URL to: https://xxxxx.ngrok.io/slack/events/
```

---

## 15. Implementation Order

| Phase | Task                                            | Priority |
|-------|-------------------------------------------------|----------|
| 1     | Create `slackbot` Django app skeleton           | Critical |
| 2     | Slack app setup (Slack API dashboard)           | Critical |
| 3     | Event handler + signature verification          | Critical |
| 4     | SupportTicket + SupportMessage models           | Critical |
| 5     | Claude API integration (bot.py)                 | Critical |
| 6     | Product knowledge bases (prompts/)              | Critical |
| 7     | Escalation rules + taskboard integration        | High     |
| 8     | Stripe webhook handler                          | High     |
| 9     | Payment notification formatting                 | High     |
| 10    | Email bridge (support@ forwarding)              | Medium   |
| 11    | Supabase webhook handler                        | Medium   |
| 12    | KDP daily summary cron job                      | Medium   |
| 13    | Funnel/Lead integration                         | Low      |
| 14    | Slash commands (/ticket, /status)               | Low      |
| 15    | Analytics dashboard for support metrics         | Low      |

---

## 16. Cost Estimates

| Service          | Expected Cost         | Notes                                    |
|-------------------|-----------------------|------------------------------------------|
| Slack             | Free (Pro if needed)  | Free tier supports bot + channels        |
| Claude API        | ~$5-20/month          | Depends on ticket volume, using Sonnet   |
| Stripe webhooks   | Free                  | Included with Stripe account             |
| Supabase          | Free tier             | Already in use for Lovable site          |
| ngrok (dev only)  | Free                  | For local development testing            |
| Oracle VM         | Free tier             | Already deployed for XLM bot             |

---

## 17. File Locations Summary

| File                                                     | Purpose                        |
|-----------------------------------------------------------|--------------------------------|
| `09_DASHBOARD/hive_dashboard/slackbot/`                  | New Django app (all bot code)  |
| `09_DASHBOARD/hive_dashboard/hive_dashboard/settings.py` | Add slackbot to INSTALLED_APPS |
| `09_DASHBOARD/hive_dashboard/hive_dashboard/urls.py`     | Add slack/ URL prefix          |
| `03_AUTOMATION_CORE/02_Config/slack_bot.env`             | Environment variables          |
| `03_AUTOMATION_CORE/04_Logs/slackbot/`                   | Runtime logs                   |
| `01_BUSINESSES/Customer_Support/`                        | KB source documents            |
