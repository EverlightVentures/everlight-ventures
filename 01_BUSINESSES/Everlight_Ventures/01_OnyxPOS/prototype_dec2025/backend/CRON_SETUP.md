# OnyxPOS Scheduled Tasks Setup

## Weekly Digest Email

The weekly digest sends business intelligence summaries to all tenant owners every Monday morning.

### Endpoints

1. **Preview Digest** (Owner-only)
   ```
   GET /api/v1/scheduled/digest/preview
   Authorization: Bearer {jwt_token}
   ```
   Shows what would be sent in the digest email

2. **Send to Current Owner** (Owner-only)
   ```
   POST /api/v1/scheduled/digest/send
   Authorization: Bearer {jwt_token}
   ```
   Manually trigger digest for logged-in owner

3. **Send to All Tenants** (Cron job)
   ```
   POST /api/v1/scheduled/digest/send-all
   ```
   Sends digests to all active tenants (no auth required)

4. **Test Email Service** (Owner-only)
   ```
   POST /api/v1/scheduled/digest/test-email
   Authorization: Bearer {jwt_token}
   ```
   Sends test digest with sample data

### Cron Job Setup

#### Linux/Ubuntu with crontab

1. Open crontab editor:
   ```bash
   crontab -e
   ```

2. Add weekly digest job (runs every Monday at 8 AM):
   ```cron
   0 8 * * 1 curl -X POST http://localhost:5000/api/v1/scheduled/digest/send-all
   ```

3. For production with HTTPS:
   ```cron
   0 8 * * 1 curl -X POST https://api.onyxpos.com/api/v1/scheduled/digest/send-all
   ```

#### Production Deployment (systemd timer)

1. Create service file `/etc/systemd/system/onyxpos-digest.service`:
   ```ini
   [Unit]
   Description=OnyxPOS Weekly Digest Email Service

   [Service]
   Type=oneshot
   User=www-data
   ExecStart=/usr/bin/curl -X POST http://localhost:5000/api/v1/scheduled/digest/send-all
   ```

2. Create timer file `/etc/systemd/system/onyxpos-digest.timer`:
   ```ini
   [Unit]
   Description=OnyxPOS Weekly Digest Timer

   [Timer]
   OnCalendar=Mon *-*-* 08:00:00
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

3. Enable and start:
   ```bash
   sudo systemctl enable onyxpos-digest.timer
   sudo systemctl start onyxpos-digest.timer
   ```

4. Check status:
   ```bash
   sudo systemctl status onyxpos-digest.timer
   sudo systemctl list-timers
   ```

#### Using GitHub Actions (Cloud-based)

Create `.github/workflows/weekly-digest.yml`:
```yaml
name: Weekly Digest Email

on:
  schedule:
    - cron: '0 8 * * 1'  # Every Monday at 8 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  send-digests:
    runs-on: ubuntu-latest
    steps:
      - name: Send Weekly Digests
        run: |
          curl -X POST https://api.onyxpos.com/api/v1/scheduled/digest/send-all
```

### Email Service Configuration

The digest requires Resend API for email delivery.

1. Sign up at https://resend.com
2. Get your API key
3. Set environment variable:
   ```bash
   export RESEND_API_KEY="re_123456789"
   export FROM_EMAIL="OnyxPOS <digests@onyxpos.com>"
   ```

4. Test email service:
   ```bash
   # Login and get JWT token
   curl -X POST http://localhost:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"owner@example.com","password":"password"}'

   # Test email
   curl -X POST http://localhost:5000/api/v1/scheduled/digest/test-email \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

### Digest Content

Each weekly digest includes:
- **Today vs Yesterday Revenue** - Daily comparison
- **Weekly Profit Analysis** - Revenue, COGS, margin %
- **Labor Cost Percentage** - With industry benchmark status
- **Inventory Valuation** - Total value and dead stock alerts
- **Action Items** - Prioritized recommendations
- **Top Performing Items** - By profit margin
- **Dead Stock Alert** - Items with no sales in 90 days

### Security Notes

**IMPORTANT for Production:**

The `/send-all` endpoint currently has no authentication to allow cron job access. For production:

1. **Option A: IP Whitelist**
   Add middleware to only allow calls from localhost/trusted IPs

2. **Option B: API Key Authentication**
   Create a `CRON_API_KEY` environment variable and require it in header

3. **Option C: Internal Network Only**
   Keep endpoint on internal network, not exposed to public internet

Example IP whitelist implementation:
```python
@scheduled_bp.before_request
def restrict_cron_endpoints():
    if request.endpoint == 'scheduled.send_all_digests':
        allowed_ips = ['127.0.0.1', '::1']  # localhost only
        if request.remote_addr not in allowed_ips:
            return jsonify({'error': 'Unauthorized'}), 403
```

### Monitoring

Check logs for digest status:
```bash
# Check cron execution
grep CRON /var/log/syslog

# Check application logs
tail -f /var/log/onyxpos/app.log

# View digest results
curl -X POST http://localhost:5000/api/v1/scheduled/digest/send-all | jq
```

### Troubleshooting

**Emails not sending:**
1. Check `RESEND_API_KEY` is set correctly
2. Verify `FROM_EMAIL` is using a verified domain in Resend
3. Check logs for error messages
4. Test with `/digest/test-email` endpoint first

**Cron not running:**
1. Verify crontab syntax: `crontab -l`
2. Check cron service: `systemctl status cron`
3. Review cron logs: `grep CRON /var/log/syslog`

**No data in digest:**
1. Ensure tenants have transaction data
2. Check database connection
3. Verify tenant subscriptions are active
