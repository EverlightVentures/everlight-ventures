# Everlight Ventures - Marketing Analytics Dashboard

Advanced Streamlit dashboard for analyzing email campaign performance, subscriber engagement, and marketing ROI.

## Features

### 📊 Overview Metrics
- Total campaigns sent
- Email delivery statistics
- Average open & click rates
- Real-time engagement tracking

### 📧 Campaign Performance
- Detailed campaign-by-campaign breakdown
- Performance comparison charts
- UTM parameter tracking
- Export campaign data to CSV

### 🔗 Link Analytics
- Top performing links
- Click-through rates
- Unique vs. total clicks
- Link performance across campaigns

### 👥 Subscriber Engagement
- Engagement level classification
- Most engaged subscribers
- Inactive subscriber identification
- Engagement score calculation

### ⏱️ Activity Timeline
- Hourly activity breakdown
- Peak engagement times
- Activity type distribution
- Real-time event tracking

### 🔬 Advanced Analytics
- Unsubscribe reason analysis
- Email client statistics
- Hourly engagement patterns
- Downloadable reports

## Quick Start

### 1. Install Dependencies

```bash
cd analytics-dashboard
pip install -r requirements.txt
```

Or create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database Connection

```bash
cp .env.example .env
nano .env  # Edit with your database credentials
```

Update `.env`:
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/everlight_dev"
```

### 3. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open automatically at: http://localhost:8501

## Dashboard Sections

### Overview Metrics
Top-level KPIs showing:
- Total campaigns sent
- Total emails delivered
- Total opens (unique + total)
- Total clicks with CTR

### Campaign Performance Table
Interactive table with:
- Campaign name & subject
- Send date
- Recipients count
- Opens & clicks
- Open rate %
- Click rate %
- Unsubscribes

### Performance Comparison Chart
Bar chart comparing open rates and click rates across campaigns.

### Top Performing Links
- Bar chart of most clicked links
- Detailed table with URL, clicks, and unique clickers
- Identify which content drives engagement

### Subscriber Engagement
- Pie chart showing engagement distribution:
  - Highly Engaged (>10 points)
  - Engaged (3-10 points)
  - Low Engagement (1-3 points)
  - Inactive (0 points)
- Table of most engaged subscribers

### Activity Timeline
- Line chart showing opens/clicks/unsubscribes over time
- Activity type breakdown
- Peak activity hours visualization

### Advanced Analytics Tabs

**Unsubscribe Analysis:**
- Reasons for unsubscribing
- Unsubscribe rate by campaign
- Trends over time

**Email Client Stats:**
- Distribution of email clients (Gmail, Outlook, etc.)
- Mobile vs. desktop usage
- Optimize emails for popular clients

**Export Data:**
- Download campaign performance (CSV)
- Download engagement data (CSV)
- Download link analytics (CSV)

## Filters & Controls

### Sidebar Filters
- **Project Slug:** Select which project to analyze
- **Date Range:** Choose start and end dates
- **Campaign Status:** Filter by DRAFT, SENDING, SENT, FAILED
- **Refresh Button:** Reload data from database

## Metrics Explained

### Engagement Score
Calculated as: `(Opens × 1) + (Clicks × 2)`

Higher weight for clicks shows deeper engagement.

### Engagement Levels
- **Highly Engaged:** Score > 10 (power users)
- **Engaged:** Score 3-10 (active subscribers)
- **Low Engagement:** Score 1-3 (occasional readers)
- **Inactive:** Score 0 (never opened)

### Open Rate
`(Unique Opens / Total Recipients) × 100`

### Click Rate (CTR)
`(Unique Clickers / Total Recipients) × 100`

### Unsubscribe Rate
`(Unsubscribes / Total Recipients) × 100`

## Use Cases

### 1. Campaign Optimization
- Identify best-performing subject lines
- Compare send times for optimal engagement
- A/B test different content approaches

### 2. Subscriber Segmentation
- Target highly engaged users for premium offers
- Re-engagement campaigns for inactive users
- Remove completely inactive subscribers

### 3. Content Strategy
- See which links get the most clicks
- Identify popular topics/products
- Optimize call-to-action placement

### 4. ROI Tracking
- UTM parameters show traffic in Google Analytics
- Connect email campaigns to conversions
- Calculate revenue per campaign

### 5. Deliverability Insights
- Email client stats help optimize rendering
- Peak hours show best send times
- Unsubscribe analysis improves content quality

## Tips for Best Results

### Data Collection
- Send at least 3-5 campaigns before analyzing trends
- Wait 24-48 hours after sending for accurate open rates
- Email clients may delay tracking pixel loading

### Dashboard Usage
- Use date ranges to compare time periods
- Export data regularly for historical analysis
- Monitor engagement trends weekly

### Performance Benchmarks
- **Good Open Rate:** 15-25%
- **Good Click Rate:** 2-5%
- **Acceptable Unsubscribe Rate:** <0.5%
- **Highly Engaged %:** Aim for 20-30%

## Troubleshooting

### Dashboard Won't Start
```bash
# Check if Streamlit is installed
streamlit --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Database Connection Error
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Check if PostgreSQL is running
sudo docker ps | grep postgres

# Verify .env file exists and is correct
cat .env
```

### No Data Showing
- Ensure campaigns have been sent (status = SENT)
- Check date range includes sent campaigns
- Verify project slug matches your database

### Slow Performance
- Add database indexes (already included in schema)
- Reduce date range for large datasets
- Use filters to narrow down data

## Advanced Customization

### Add Custom Metrics

Edit `database.py` to add new queries:

```python
def get_custom_metric(project_slug, start_date, end_date):
    query = text("""
        SELECT ... FROM ...
    """)
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn, params={...})
```

Then use in `app.py`:
```python
custom_data = get_custom_metric(project_filter, date_range[0], date_range[1])
st.plotly_chart(...)
```

### Change Color Schemes

Modify Plotly color scales in `app.py`:
```python
color_continuous_scale='Viridis'  # Try: Blues, Reds, Greens, Viridis, etc.
```

### Add More Filters

In `app.py` sidebar:
```python
tag_filter = st.sidebar.multiselect("Tags", options=[...])
```

## Integration with Google Analytics

All UTM parameters are automatically tracked:
- `utm_source`: Newsletter source
- `utm_medium`: Email
- `utm_campaign`: Campaign identifier
- `utm_content`: Specific link/CTA

View in GA4:
1. Go to Reports → Acquisition → Traffic acquisition
2. Filter by Medium = "email"
3. See campaigns, conversions, revenue

## Deployment Options

### Option 1: Local (Current Setup)
Run on your machine for private analysis.

### Option 2: Streamlit Cloud (Free)
1. Push code to GitHub
2. Connect at share.streamlit.io
3. Add DATABASE_URL secret
4. Deploy (free for public dashboards)

### Option 3: Docker
```bash
docker build -t analytics-dashboard .
docker run -p 8501:8501 --env-file .env analytics-dashboard
```

### Option 4: Self-Hosted Server
Deploy on VPS with nginx reverse proxy for team access.

## Security Notes

- Never commit `.env` to version control
- Use read-only database user for dashboard
- Enable authentication for production deployments
- Restrict database access to necessary IPs only

## Support & Updates

This dashboard connects directly to your PostgreSQL database and automatically reflects new data as campaigns are sent and tracked.

For issues or feature requests, check the main Everlight Ventures documentation.
