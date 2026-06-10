# Resend Email Integration Setup

This guide walks you through setting up Resend for email delivery in Everlight Ventures.

## What's Been Integrated

Resend has been integrated for:
1. **Magic Link Authentication** - Passwordless login emails
2. **Newsletter Campaigns** - Bulk email sending to contacts

## Setup Steps

### 1. Create a Resend Account

1. Go to [resend.com](https://resend.com)
2. Sign up for a free account
3. Verify your email address

### 2. Get Your API Key

1. Log into your Resend dashboard
2. Navigate to **API Keys** in the sidebar
3. Click **Create API Key**
4. Give it a name (e.g., "Everlight Ventures Production")
5. Select permissions: **Sending access**
6. Click **Create** and copy your API key (starts with `re_`)

### 3. Configure Your Domain (Production Only)

For production use, you need to verify your domain:

1. In Resend dashboard, go to **Domains**
2. Click **Add Domain**
3. Enter your domain (e.g., `everlight.dev`)
4. Add the provided DNS records to your domain registrar
5. Wait for verification (usually takes a few minutes)

**Note:** For development, you can skip this step. Resend allows sending to your own email without domain verification.

### 4. Update Environment Variables

Copy your `.env.example` to `.env` if you haven't already:

```bash
cp .env.example .env
```

Edit `.env` and add your Resend API key:

```env
# Email (Resend)
RESEND_API_KEY="re_your_actual_api_key_here"
EMAIL_FROM="noreply@yourdomain.com"
```

**Important:**
- Replace `re_your_actual_api_key_here` with your actual Resend API key
- Update `EMAIL_FROM` to match your verified domain (or use your personal email for testing)

### 5. Test the Integration

#### Test Magic Links (Development Mode)

In development (`NODE_ENV=development`), magic links are logged to console instead of sent:

```bash
npm run dev
```

Then try signing in with magic link - check your console for the link.

#### Test Magic Links (Production Mode)

Set `NODE_ENV=production` in your `.env`:

```env
NODE_ENV="production"
```

Now magic link emails will be sent via Resend to the email address you enter.

#### Test Campaign Sending

1. Create a project
2. Import or add contacts
3. Create a campaign
4. Click "Send Campaign"

In development mode, it will log to console. In production mode, emails will be sent via Resend.

## Email Behavior by Environment

### Development Mode (`NODE_ENV=development`)

- **Magic Links**: Logged to console only
- **Campaigns**: Logged to console only
- No actual emails are sent
- Useful for local development without using API credits

### Production Mode (`NODE_ENV=production`)

- **Magic Links**: Sent via Resend
- **Campaigns**: Sent via Resend
- Requires valid `RESEND_API_KEY`
- Counts against your Resend quota

## Resend Pricing

- **Free Tier**: 100 emails/day, 3,000 emails/month
- **Pro**: $20/month - 50,000 emails/month
- **Enterprise**: Custom pricing

For development and testing, the free tier is sufficient.

## Email Templates

### Magic Link Email

The magic link email includes:
- Professional HTML template with button
- Plain text fallback
- 24-hour expiration notice

To customize, edit: `apps/web/src/lib/auth.ts` (lines 68-91)

### Campaign Emails

Campaigns use the content you create:
- HTML content from your campaign editor
- Automatic plain text fallback (strips HTML tags)

## Troubleshooting

### "API key not found" error

- Make sure `RESEND_API_KEY` is set in your `.env` file
- Verify the key starts with `re_`
- Restart your dev server after changing `.env`

### Emails not being sent

- Check that `NODE_ENV=production` in your `.env`
- Verify your Resend API key is valid
- Check your Resend dashboard for error logs
- Ensure `EMAIL_FROM` matches your verified domain (or use your personal email for testing)

### Domain verification issues

- DNS changes can take 24-48 hours to propagate
- Use `dig` or online DNS checkers to verify your records
- For testing, use your personal email address as `EMAIL_FROM`

### Rate limiting

- Free tier: 100 emails/day
- If you hit limits, upgrade your Resend plan
- Use development mode for testing to avoid consuming credits

## Migration from Other Services

If you want to switch to a different email service (SendGrid, Postmark, etc.), update these files:

1. `apps/web/src/lib/auth.ts` - Magic link sending
2. `apps/web/src/app/api/projects/[slug]/campaigns/[id]/send/route.ts` - Campaign sending

Both files have clean integration points that make swapping services straightforward.

## Support

- **Resend Documentation**: [resend.com/docs](https://resend.com/docs)
- **Resend Support**: [resend.com/support](https://resend.com/support)
- **GitHub Issues**: Report issues with the integration in your repository

## Next Steps

After setting up Resend, you may want to:

1. Customize email templates to match your brand
2. Set up email analytics tracking
3. Configure email bounce handling
4. Add unsubscribe links to campaign emails
5. Implement email scheduling for campaigns
