"""
Email Service
Handles all transactional emails via SendGrid
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@onyxpos.com')
FROM_NAME = 'OnyxPOS'


def send_email(to_email, subject, html_content, text_content=None):
    """
    Send email via SendGrid

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text fallback (optional)

    Returns:
        dict: {'success': bool, 'error': str}
    """
    if not SENDGRID_API_KEY:
        print("⚠️ SendGrid API key not configured, email not sent")
        return {'success': False, 'error': 'SendGrid not configured'}

    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )

        if text_content:
            message.add_content(Content("text/plain", text_content))

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        return {
            'success': True,
            'status_code': response.status_code
        }

    except Exception as e:
        print(f"❌ Email send error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def send_payment_failed_email(tenant, invoice_amount):
    """Send payment failed notification"""
    subject = "Payment Failed - Action Required"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ef4444;">Payment Failed</h2>
            <p>Hi {tenant.business_name},</p>
            <p>We were unable to process your payment of <strong>${invoice_amount:.2f}</strong> for your OnyxPOS subscription.</p>
            <p><strong>What you need to do:</strong></p>
            <ul>
                <li>Update your payment method in your billing settings</li>
                <li>Ensure your card has sufficient funds</li>
            </ul>
            <p>You have <strong>10 days</strong> before your account is suspended.</p>
            <a href="https://billing.stripe.com/p/login/..." style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                Update Payment Method
            </a>
            <p style="color: #666; font-size: 14px;">If you believe this is an error, please contact support.</p>
            <p>Best,<br>The OnyxPOS Team</p>
        </body>
    </html>
    """

    return send_email(tenant.owner_email, subject, html_content)


def send_trial_expiring_email(tenant, days_remaining):
    """Send trial expiring notification"""
    subject = f"Your OnyxPOS Trial Ends in {days_remaining} Days"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #6366f1;">Your Trial is Ending Soon</h2>
            <p>Hi {tenant.business_name},</p>
            <p>Your 14-day free trial of OnyxPOS ends in <strong>{days_remaining} days</strong>.</p>
            <p><strong>Continue using OnyxPOS:</strong></p>
            <ul>
                <li>Subscribe starting at just $39/mo + 0.15% GMV (capped at $149)</li>
                <li>Max total cost: $188/mo</li>
                <li>Keep all your data and settings</li>
                <li>No interruption to your business</li>
            </ul>
            <a href="https://app.onyxpos.com/billing" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                Choose Your Plan
            </a>
            <p style="color: #666; font-size: 14px;">Questions? Reply to this email or visit our help center.</p>
            <p>Best,<br>The OnyxPOS Team</p>
        </body>
    </html>
    """

    return send_email(tenant.owner_email, subject, html_content)


def send_account_suspended_email(tenant):
    """Send account suspended notification"""
    subject = "OnyxPOS Account Suspended"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ef4444;">Account Suspended</h2>
            <p>Hi {tenant.business_name},</p>
            <p>Your OnyxPOS account has been suspended due to payment failure.</p>
            <p><strong>To restore access:</strong></p>
            <ol>
                <li>Update your payment method</li>
                <li>Your account will be automatically reactivated</li>
                <li>No data has been lost</li>
            </ol>
            <a href="https://billing.stripe.com/p/login/..." style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                Reactivate Account
            </a>
            <p style="color: #666; font-size: 14px;">Need help? Contact support at support@onyxpos.com</p>
            <p>Best,<br>The OnyxPOS Team</p>
        </body>
    </html>
    """

    return send_email(tenant.owner_email, subject, html_content)


def send_payment_succeeded_email(tenant, invoice_amount):
    """Send payment success confirmation"""
    subject = "Payment Received - Thank You"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Payment Received</h2>
            <p>Hi {tenant.business_name},</p>
            <p>Thank you! We've successfully processed your payment of <strong>${invoice_amount:.2f}</strong>.</p>
            <p><strong>Subscription Details:</strong></p>
            <ul>
                <li>Plan: {tenant.plan_tier.title()}</li>
                <li>Status: Active</li>
                <li>Next billing date: {tenant.current_period_end.strftime('%B %d, %Y') if tenant.current_period_end else 'N/A'}</li>
            </ul>
            <a href="https://app.onyxpos.com/billing" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                View Billing Details
            </a>
            <p style="color: #666; font-size: 14px;">Receipt attached or available in your billing portal.</p>
            <p>Best,<br>The OnyxPOS Team</p>
        </body>
    </html>
    """

    return send_email(tenant.owner_email, subject, html_content)


def send_welcome_email(tenant):
    """Send welcome email to new users"""
    subject = "Welcome to OnyxPOS!"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #6366f1;">Welcome to OnyxPOS! 🎉</h2>
            <p>Hi {tenant.business_name},</p>
            <p>Thank you for choosing OnyxPOS for your point of sale needs!</p>
            <p><strong>Get started in 3 easy steps:</strong></p>
            <ol>
                <li><strong>Add your first product</strong> - Build your inventory</li>
                <li><strong>Make a test sale</strong> - Try the sales terminal</li>
                <li><strong>Invite your team</strong> - Add employees and set permissions</li>
            </ol>
            <a href="https://app.onyxpos.com" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
                Open OnyxPOS
            </a>
            <p><strong>Your trial includes:</strong></p>
            <ul>
                <li>14 days free access to all features</li>
                <li>No credit card required during trial</li>
                <li>Full mobile app access</li>
                <li>Unlimited transactions</li>
            </ul>
            <p style="color: #666; font-size: 14px;">Need help? Check out our <a href="https://docs.onyxpos.com">documentation</a> or reply to this email.</p>
            <p>Best,<br>The OnyxPOS Team</p>
        </body>
    </html>
    """

    return send_email(tenant.owner_email, subject, html_content)
