"""
Email Notification Service using Resend
Install: pip install resend jinja2
"""
import os
from datetime import datetime
from typing import Optional, List, Dict
import logging

# Try to import resend, fallback to mock if not installed
try:
    import resend
    resend.api_key = os.getenv("RESEND_API_KEY")
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logging.warning("Resend not installed. Email sending disabled. Install with: pip install resend")

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service"""

    FROM_EMAIL = os.getenv("FROM_EMAIL", "OnyxPOS <onboarding@onyxpos.com>")
    REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "support@onyxpos.com")

    @classmethod
    def send_email(
        cls,
        to: str | List[str],
        subject: str,
        html: str,
        text: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """Send email using Resend"""
        if not RESEND_AVAILABLE:
            logger.warning(f"Email not sent (Resend unavailable): {subject} to {to}")
            return False

        try:
            if isinstance(to, str):
                to = [to]

            params = {
                "from": cls.FROM_EMAIL,
                "to": to,
                "subject": subject,
                "html": html,
                "reply_to": cls.REPLY_TO_EMAIL,
            }

            if text:
                params["text"] = text

            if attachments:
                params["attachments"] = attachments

            email = resend.Emails.send(params)
            logger.info(f"Email sent successfully: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    @classmethod
    def send_welcome_email(cls, to: str, business_name: str, user_name: str) -> bool:
        """Send welcome email to new user"""
        subject = f"Welcome to OnyxPOS, {business_name}!"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to OnyxPOS! 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Congratulations on starting your journey with OnyxPOS for <strong>{business_name}</strong>!</p>

                    <p>You now have access to a powerful, next-generation point of sale system with:</p>
                    <ul>
                        <li>✅ Real-time sales tracking</li>
                        <li>✅ Advanced inventory management</li>
                        <li>✅ Cryptocurrency payment support</li>
                        <li>✅ Comprehensive analytics</li>
                        <li>✅ Multi-location support</li>
                    </ul>

                    <p>Your <strong>14-day free trial</strong> starts now! No credit card required.</p>

                    <p style="text-align: center;">
                        <a href="https://app.onyxpos.com/login" class="button">Get Started →</a>
                    </p>

                    <h3>What's Next?</h3>
                    <ol>
                        <li>Add your products to inventory</li>
                        <li>Configure your payment methods</li>
                        <li>Make your first sale</li>
                        <li>Invite team members</li>
                    </ol>

                    <p>Need help? Our support team is here for you 24/7.</p>
                </div>
                <div class="footer">
                    <p>Questions? Contact us at <a href="mailto:support@onyxpos.com">support@onyxpos.com</a></p>
                    <p>&copy; {datetime.now().year} OnyxPOS. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)

    @classmethod
    def send_receipt_email(
        cls,
        to: str,
        business_name: str,
        transaction_number: str,
        transaction_date: datetime,
        items: List[Dict],
        subtotal: float,
        tax: float,
        total: float,
        payment_method: str
    ) -> bool:
        """Send receipt email after purchase"""
        subject = f"Receipt #{transaction_number} from {business_name}"

        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item['name']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item['quantity']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">${item['unit_price']:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: bold;">${item['line_total']:.2f}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0a0a0a; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e5e7eb; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .totals {{ margin-top: 20px; padding-top: 20px; border-top: 2px solid #3b82f6; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{business_name}</h1>
                    <p>Receipt #{transaction_number}</p>
                </div>
                <div class="content">
                    <p><strong>Date:</strong> {transaction_date.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p><strong>Payment Method:</strong> {payment_method.title()}</p>

                    <table>
                        <thead>
                            <tr style="background: #f9fafb;">
                                <th style="padding: 10px; text-align: left;">Item</th>
                                <th style="padding: 10px; text-align: center;">Qty</th>
                                <th style="padding: 10px; text-align: right;">Price</th>
                                <th style="padding: 10px; text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>

                    <div class="totals">
                        <table style="margin: 0;">
                            <tr>
                                <td style="padding: 5px; text-align: right;"><strong>Subtotal:</strong></td>
                                <td style="padding: 5px; text-align: right; width: 120px;">${subtotal:.2f}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px; text-align: right;"><strong>Tax:</strong></td>
                                <td style="padding: 5px; text-align: right;">${tax:.2f}</td>
                            </tr>
                            <tr style="font-size: 18px; color: #3b82f6;">
                                <td style="padding: 10px 5px; text-align: right;"><strong>Total:</strong></td>
                                <td style="padding: 10px 5px; text-align: right;"><strong>${total:.2f}</strong></td>
                            </tr>
                        </table>
                    </div>

                    <p style="margin-top: 30px; text-align: center; color: #666;">
                        Thank you for your business!
                    </p>
                </div>
                <div class="footer">
                    <p>Powered by <strong>OnyxPOS</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)

    @classmethod
    def send_low_stock_alert(
        cls,
        to: str,
        business_name: str,
        low_stock_items: List[Dict]
    ) -> bool:
        """Send low stock alert to business owner"""
        subject = f"⚠️ Low Stock Alert - {business_name}"

        items_html = ""
        for item in low_stock_items:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item['name']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item['sku']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: center; color: #ef4444; font-weight: bold;">{item['stock']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item['reorder_point']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item.get('supplier', 'N/A')}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .alert {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin-bottom: 20px; border-radius: 6px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="alert">
                    <h2>⚠️ Low Stock Alert</h2>
                    <p><strong>{len(low_stock_items)}</strong> items are running low in your inventory.</p>
                </div>

                <p>The following products need to be reordered:</p>

                <table>
                    <thead>
                        <tr style="background: #f9fafb;">
                            <th style="padding: 10px; text-align: left;">Product</th>
                            <th style="padding: 10px; text-align: left;">SKU</th>
                            <th style="padding: 10px; text-align: center;">Current Stock</th>
                            <th style="padding: 10px; text-align: center;">Reorder Point</th>
                            <th style="padding: 10px; text-align: left;">Supplier</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <p style="text-align: center;">
                    <a href="https://app.onyxpos.com/inventory" class="button">Manage Inventory →</a>
                </p>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)

    @classmethod
    def send_subscription_confirmation(
        cls,
        to: str,
        business_name: str,
        plan_name: str,
        amount: float,
        billing_date: datetime
    ) -> bool:
        """Send subscription confirmation email"""
        subject = f"Subscription Confirmed - {plan_name} Plan"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .success {{ background: #f0fdf4; border-left: 4px solid #10b981; padding: 20px; margin-bottom: 20px; border-radius: 6px; }}
                .plan-details {{ background: #fff; border: 2px solid #3b82f6; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">
                    <h2>✅ Subscription Activated!</h2>
                </div>

                <p>Hi {business_name},</p>
                <p>Your subscription to OnyxPOS has been successfully activated!</p>

                <div class="plan-details">
                    <h3 style="margin-top: 0; color: #3b82f6;">{plan_name} Plan</h3>
                    <p><strong>Monthly Cost:</strong> ${amount:.2f}</p>
                    <p><strong>Next Billing Date:</strong> {billing_date.strftime('%B %d, %Y')}</p>
                </div>

                <h3>What's Included:</h3>
                <ul>
                    <li>✅ Unlimited transactions</li>
                    <li>✅ Advanced analytics & reporting</li>
                    <li>✅ Cryptocurrency payment support</li>
                    <li>✅ Multi-location management</li>
                    <li>✅ Priority customer support</li>
                    <li>✅ Regular feature updates</li>
                </ul>

                <p style="text-align: center;">
                    <a href="https://app.onyxpos.com/billing" class="button">View Billing Details →</a>
                </p>

                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    You can manage your subscription, update payment methods, or cancel anytime from your billing dashboard.
                </p>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)

    @classmethod
    def send_password_reset(
        cls,
        to: str,
        reset_token: str,
        business_name: str
    ) -> bool:
        """Send password reset email"""
        subject = "Reset Your OnyxPOS Password"
        reset_url = f"https://app.onyxpos.com/reset-password?token={reset_token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .warning {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hi,</p>
                <p>We received a request to reset your password for <strong>{business_name}</strong> on OnyxPOS.</p>

                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password →</a>
                </p>

                <p>Or copy and paste this link into your browser:</p>
                <p style="background: #f9fafb; padding: 10px; border-radius: 6px; word-break: break-all; font-family: monospace; font-size: 12px;">
                    {reset_url}
                </p>

                <div class="warning">
                    <p style="margin: 0;"><strong>⚠️ Security Notice:</strong></p>
                    <p style="margin: 5px 0 0 0;">This link will expire in 1 hour. If you didn't request this reset, please ignore this email and your password will remain unchanged.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)

    @classmethod
    def send_weekly_digest(
        cls,
        to: str,
        business_name: str,
        digest_data: Dict
    ) -> bool:
        """Send weekly owner intelligence digest email"""
        subject = f"Weekly Business Digest - {business_name}"

        # Extract data
        summary = digest_data.get('summary', {})
        top_items = digest_data.get('top_items', {})
        labor = digest_data.get('labor', {})
        inventory = digest_data.get('inventory', {})

        today_data = summary.get('today', {})
        week_data = summary.get('this_week', {})
        action_items = summary.get('action_items', [])

        # Build action items HTML
        action_items_html = ""
        for item in action_items[:5]:
            priority_color = {
                'high': '#ef4444',
                'medium': '#f59e0b',
                'low': '#3b82f6'
            }.get(item['priority'], '#6b7280')

            action_items_html += f"""
            <div style="background: #fff; border-left: 4px solid {priority_color}; padding: 15px; margin: 10px 0; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: {priority_color}; text-transform: uppercase; font-size: 11px;">{item['priority']} PRIORITY</strong>
                        <p style="margin: 5px 0; font-size: 14px; font-weight: bold;">{item['message']}</p>
                        <p style="margin: 5px 0; color: #666; font-size: 13px;">→ {item['action']}</p>
                    </div>
                </div>
            </div>
            """

        if not action_items:
            action_items_html = "<p style='color: #10b981; font-weight: bold;'>✅ All systems operating optimally!</p>"

        # Build top performers HTML
        top_performers_html = ""
        for item in top_items.get('top_performers', [])[:5]:
            top_performers_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item['name']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">${item['revenue']:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">${item['profit']:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; color: #10b981; font-weight: bold;">{item['margin_percent']:.1f}%</td>
            </tr>
            """

        # Build dead stock HTML
        dead_stock_html = ""
        dead_stock_items = inventory.get('dead_stock_items', [])[:5]
        if dead_stock_items:
            for item in dead_stock_items:
                dead_stock_html += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{item['name']}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item['quantity']}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; color: #ef4444;">${item['value']:.2f}</td>
                </tr>
                """
        else:
            dead_stock_html = "<tr><td colspan='3' style='padding: 20px; text-align: center; color: #10b981;'>No dead stock - excellent inventory management!</td></tr>"

        # Labor status color
        labor_status_color = {
            'excellent': '#10b981',
            'good': '#3b82f6',
            'warning': '#f59e0b',
            'critical': '#ef4444'
        }.get(labor.get('status', 'good'), '#3b82f6')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background: #f3f4f6; margin: 0; padding: 0; }}
                .container {{ max-width: 700px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #0a0a0a 0%, #1f1f1f 100%); color: white; padding: 40px 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 14px; }}
                .content {{ padding: 30px; }}
                .metric-card {{ background: #f9fafb; border-radius: 8px; padding: 20px; margin: 15px 0; border: 1px solid #e5e7eb; }}
                .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
                .metric-box {{ background: white; border: 2px solid #e5e7eb; border-radius: 8px; padding: 20px; text-align: center; }}
                .metric-value {{ font-size: 32px; font-weight: bold; color: #0a0a0a; margin: 10px 0; }}
                .metric-label {{ font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
                .metric-change {{ font-size: 14px; margin-top: 5px; }}
                .positive {{ color: #10b981; }}
                .negative {{ color: #ef4444; }}
                .section-title {{ font-size: 20px; font-weight: bold; margin: 30px 0 15px 0; color: #0a0a0a; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; background: white; }}
                th {{ background: #f9fafb; padding: 12px; text-align: left; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
                .footer {{ background: #f9fafb; padding: 30px; text-align: center; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb; }}
                .button {{ display: inline-block; background: #0a0a0a; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Weekly Business Digest</h1>
                    <p>{business_name} • Week of {datetime.now().strftime('%B %d, %Y')}</p>
                </div>

                <div class="content">
                    <!-- Key Metrics -->
                    <div class="metric-grid">
                        <div class="metric-box">
                            <div class="metric-label">Today's Revenue</div>
                            <div class="metric-value">${today_data.get('revenue', 0):,.2f}</div>
                            <div class="metric-change {'positive' if today_data.get('vs_yesterday', 0) >= 0 else 'negative'}">
                                {'▲' if today_data.get('vs_yesterday', 0) >= 0 else '▼'} ${abs(today_data.get('vs_yesterday', 0)):,.2f} vs yesterday
                            </div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Weekly Profit</div>
                            <div class="metric-value">${week_data.get('profit', 0):,.2f}</div>
                            <div class="metric-change" style="color: #6b7280;">
                                {week_data.get('margin_percent', 0):.1f}% margin
                            </div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Labor Cost %</div>
                            <div class="metric-value" style="color: {labor_status_color};">{labor.get('cost_percent', 0):.1f}%</div>
                            <div class="metric-change" style="color: {labor_status_color};">
                                {labor.get('status', 'good').title()}
                            </div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Inventory Value</div>
                            <div class="metric-value">${inventory.get('total_value', 0):,.2f}</div>
                            <div class="metric-change" style="color: #6b7280;">
                                {inventory.get('unique_items', 0)} items
                            </div>
                        </div>
                    </div>

                    <!-- Action Items -->
                    <h2 class="section-title">🎯 Action Items</h2>
                    {action_items_html}

                    <!-- Top Performers -->
                    <h2 class="section-title">🏆 Top Performing Items</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: right;">Revenue</th>
                                <th style="text-align: right;">Profit</th>
                                <th style="text-align: right;">Margin</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top_performers_html}
                        </tbody>
                    </table>

                    <!-- Dead Stock Alert -->
                    {f'''<h2 class="section-title">⚠️ Dead Stock Alert ({inventory.get('dead_stock_count', 0)} items)</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: right;">Quantity</th>
                                <th style="text-align: right;">Value at Risk</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dead_stock_html}
                        </tbody>
                    </table>''' if inventory.get('dead_stock_count', 0) > 0 else ''}

                    <!-- Weekly Summary -->
                    <div class="metric-card">
                        <h3 style="margin-top: 0;">📈 This Week's Summary</h3>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li><strong>${week_data.get('revenue', 0):,.2f}</strong> total revenue from <strong>{week_data.get('transaction_count', 0)}</strong> transactions</li>
                            <li><strong>${week_data.get('profit', 0):,.2f}</strong> gross profit at <strong>{week_data.get('margin_percent', 0):.1f}%</strong> margin</li>
                            <li><strong>${labor.get('total_cost', 0):,.2f}</strong> labor costs ({labor.get('cost_percent', 0):.1f}% of revenue)</li>
                            <li><strong>{inventory.get('total_quantity', 0)}</strong> units in inventory worth <strong>${inventory.get('total_value', 0):,.2f}</strong></li>
                        </ul>
                    </div>

                    <p style="text-align: center;">
                        <a href="https://app.onyxpos.com/dashboard" class="button">View Full Dashboard →</a>
                    </p>
                </div>

                <div class="footer">
                    <p><strong>OnyxOS Intelligence Digest</strong></p>
                    <p>Delivered weekly to help you make data-driven decisions</p>
                    <p style="margin-top: 20px;">
                        Questions? <a href="mailto:support@onyxpos.com" style="color: #3b82f6;">Contact Support</a>
                    </p>
                    <p>&copy; {datetime.now().year} OnyxPOS. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return cls.send_email(to, subject, html)
