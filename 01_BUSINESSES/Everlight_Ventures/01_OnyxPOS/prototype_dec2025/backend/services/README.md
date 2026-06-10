# OnyxPOS Email Notification Service

Transactional email system using Resend API for reliable email delivery.

## Features

- ✅ **Welcome Emails** - Sent on user registration
- ✅ **Receipt Emails** - Sent after sales transactions
- ✅ **Low Stock Alerts** - Automated inventory alerts
- ✅ **Subscription Confirmations** - Billing notifications
- ✅ **Password Reset** - Secure password recovery
- ✅ **Beautiful HTML Templates** - Professional email design
- ✅ **Fallback Handling** - Graceful degradation if email fails

## Setup

### 1. Install Dependencies

```bash
pip install resend
```

### 2. Get Resend API Key

1. Sign up at [https://resend.com](https://resend.com)
2. Create an API key
3. Verify your sending domain (or use Resend's test domain)

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# Email Configuration
RESEND_API_KEY=re_your_api_key_here
FROM_EMAIL="OnyxPOS <onboarding@onyxpos.com>"
REPLY_TO_EMAIL="support@onyxpos.com"
```

## Usage

### Send Welcome Email

```python
from services.email_service import EmailService

EmailService.send_welcome_email(
    to="customer@example.com",
    business_name="Coffee Shop",
    user_name="John Doe"
)
```

### Send Receipt Email

```python
EmailService.send_receipt_email(
    to="customer@example.com",
    business_name="Coffee Shop",
    transaction_number="TXN-001",
    transaction_date=datetime.utcnow(),
    items=[
        {
            'name': 'Latte',
            'quantity': 2,
            'unit_price': 4.50,
            'line_total': 9.00
        }
    ],
    subtotal=9.00,
    tax=0.65,
    total=9.65,
    payment_method="card"
)
```

### Send Low Stock Alert

```python
EmailService.send_low_stock_alert(
    to="owner@business.com",
    business_name="Coffee Shop",
    low_stock_items=[
        {
            'name': 'Coffee Beans',
            'sku': 'BEANS-001',
            'stock': 5,
            'reorder_point': 20,
            'supplier': 'Acme Suppliers'
        }
    ]
)
```

### Send Subscription Confirmation

```python
EmailService.send_subscription_confirmation(
    to="owner@business.com",
    business_name="Coffee Shop",
    plan_name="Professional",
    amount=79.00,
    billing_date=datetime.utcnow() + timedelta(days=30)
)
```

### Send Password Reset

```python
EmailService.send_password_reset(
    to="user@example.com",
    reset_token="abc123xyz",
    business_name="Coffee Shop"
)
```

## Email Templates

All emails use responsive HTML templates with:
- **Mobile-first design** - Looks great on all devices
- **Brand consistency** - Uses OnyxPOS colors and styling
- **Clear CTAs** - Action buttons for important tasks
- **Professional layout** - Clean, modern design

## Testing

### Test in Development

During development, Resend provides a test mode that doesn't send real emails:

```python
# Set test mode
os.environ['RESEND_TEST_MODE'] = 'true'
```

### Preview Emails

Before sending to customers, test emails with your own address:

```python
EmailService.send_welcome_email(
    to="your-email@example.com",  # Your test email
    business_name="Test Business",
    user_name="Test User"
)
```

## Error Handling

The email service includes automatic error handling:

```python
# Emails are sent asynchronously and don't block the main flow
try:
    EmailService.send_welcome_email(...)
except Exception as e:
    # Error is logged but doesn't crash the application
    logger.error(f"Failed to send email: {e}")
```

## Production Deployment

### Domain Verification

For production, verify your domain in Resend:

1. Go to Resend Dashboard → Domains
2. Add your domain (e.g., `onyxpos.com`)
3. Add the provided DNS records to your domain
4. Wait for verification (usually a few minutes)

### Email Deliverability

To ensure high deliverability:

1. ✅ Verify your sending domain
2. ✅ Set up SPF, DKIM, and DMARC records
3. ✅ Use a professional `From` address
4. ✅ Include an unsubscribe link (for marketing emails)
5. ✅ Monitor bounce rates in Resend dashboard

### Rate Limits

Resend plans:
- **Free**: 100 emails/day
- **Starter**: 50,000 emails/month
- **Pro**: 100,000 emails/month

## Monitoring

Monitor email delivery in the Resend dashboard:

- **Sent**: Successfully delivered emails
- **Bounced**: Failed deliveries (invalid addresses)
- **Opened**: Track email opens (optional)
- **Clicked**: Track link clicks (optional)

## Custom Templates

To add new email templates:

1. Create a new method in `EmailService`:

```python
@classmethod
def send_custom_email(cls, to: str, custom_data: dict) -> bool:
    subject = "Your Subject"

    html = f"""
    <!DOCTYPE html>
    <html>
    ...your custom HTML...
    </html>
    """

    return cls.send_email(to, subject, html)
```

2. Use the new method in your API:

```python
EmailService.send_custom_email(
    to=user.email,
    custom_data={'key': 'value'}
)
```

## Troubleshooting

### "Resend not installed" warning

Install the Resend package:

```bash
pip install resend
```

### Emails not sending

Check:
1. ✅ RESEND_API_KEY is set in environment
2. ✅ API key is valid (check Resend dashboard)
3. ✅ Recipient email address is valid
4. ✅ Check Resend logs for delivery status

### Emails going to spam

Ensure:
1. ✅ Domain is verified
2. ✅ SPF/DKIM/DMARC records are correct
3. ✅ Not sending too many emails too quickly
4. ✅ Content doesn't trigger spam filters

## Alternative Email Providers

If you prefer a different provider, replace Resend with:

- **SendGrid** - Enterprise-grade email
- **Mailgun** - Developer-friendly API
- **AWS SES** - Cost-effective at scale
- **Postmark** - Transactional email specialist

Just update the `send_email()` method to use the new provider's API.

## Cost Estimation

For a typical OnyxPOS tenant:

- Welcome email: 1 per signup
- Receipt emails: 1-10 per day
- Low stock alerts: 5-10 per week
- Subscription emails: 1 per month

**Monthly estimate**: ~300-500 emails/tenant

**Recommended plan**: Resend Pro ($20/month for 100K emails)
- Supports ~200-300 active tenants
- $0.0002 per email after quota

## License

Proprietary - All rights reserved
