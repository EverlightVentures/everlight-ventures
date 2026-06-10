# 🚀 Complete Content Distribution Workflow

## Your Use Case: AI Videos + Ebook Clips → Everywhere

You want to:
1. Create AI videos weekly (Sora)
2. Share clips from your ebook
3. Drop content once → distribute to email + Instagram + Facebook + TikTok

**This is now fully implemented and ready to use!**

---

## 🎯 Quick Start (3 Steps)

### Step 1: Connect Your Social Media Accounts

1. **Go to Settings:**
   ```
   http://localhost:3000/projects/demo-project/settings/social-media
   ```

2. **Connect Facebook:**
   - Click "Connect" on Facebook card
   - Authorize the app
   - System automatically detects your Instagram Business Account
   - Done! Both Facebook Page and Instagram are now connected

3. **TikTok (Coming Soon):**
   - TikTok requires API approval
   - For now, you can manually post to TikTok using the optimized caption

**Prerequisites:**
- Facebook App created at developers.facebook.com
- Instagram Business Account linked to Facebook Page
- Add to `.env`:
  ```bash
  FACEBOOK_APP_ID="your-app-id"
  FACEBOOK_APP_SECRET="your-app-secret"
  ```

---

### Step 2: Create Your First Multi-Channel Campaign

1. **Go to Create Campaign:**
   ```
   http://localhost:3000/projects/demo-project/campaigns/new
   ```

2. **Upload Your Content:**
   - Drag & drop your AI video (MP4) OR ebook image (JPG/PNG)
   - System automatically optimizes for each platform
   - Thumbnails generated instantly

3. **Write Your Content (Once):**
   - **Campaign Name:** "Week 1: AI Video Mini-Episode"
   - **Email Subject:** "🎬 New Episode: The Future of AI"
   - **Email Content:** HTML with your message + video embed/image
   - **Social Caption:** Auto-filled from subject (edit as needed)
   - **Hashtags:** "#AI #Video #Content #Marketing"

4. **Select Platforms:**
   - ☑ Instagram
   - ☑ Facebook
   - ☐ TikTok (coming soon)

5. **Click "🚀 Create & Distribute"**

---

### Step 3: Send & Watch It Go Everywhere

1. **Go to Campaign Details:**
   - View your draft campaign
   - Preview how it will look

2. **Click "Send":**
   - Emails sent to all subscribers ✅
   - Instagram post published ✅
   - Facebook post published ✅
   - All tracked and logged ✅

3. **Monitor Performance:**
   - Email analytics: Opens, clicks, unsubscribes
   - Social analytics: Coming in Streamlit dashboard
   - Activity log shows all posts

---

## 📹 Your Weekly Workflow

### Every Week (5 Minutes):

1. **Create Sora video** → Save as MP4
2. **Open app** → Create new campaign
3. **Drop video** → Uploads in seconds
4. **Write caption** → One caption for all platforms
5. **Add hashtags** → "#AI #Sora #Video #Weekly"
6. **Hit distribute** → Goes to:
   - ✉️ Email subscribers
   - 📱 Instagram followers
   - 👍 Facebook Page fans
   - 🎵 TikTok (manual for now)

**Done! You just distributed your content to all channels in under 5 minutes.**

---

## 📚 Ebook Clips Workflow

### Sharing Text + Image from Ebook:

1. **Create image:**
   - Screenshot quote from ebook
   - OR create graphic with quote + design

2. **Upload to campaign:**
   - Drop image in media uploader
   - System optimizes for each platform:
     - Instagram: 1080x1080 (square)
     - Facebook: 1200x1200
     - TikTok: 1080x1920 (vertical)

3. **Write caption:**
   ```
   "From my upcoming ebook on AI content creation:

   'The future of content isn't about replacing humans,
   it's about amplifying creativity.'

   Pre-order link in bio! #AI #Ebook #Writing"
   ```

4. **Distribute:**
   - Email: Full excerpt + image
   - Instagram: Quote image + caption + "Link in bio"
   - Facebook: Quote image + caption + clickable link
   - TikTok: Optimized vertical image

---

## 🎨 Content Adaptation (Automatic)

### What The System Does For You:

**For Instagram:**
- ✅ Resizes images to 1080x1080
- ✅ Compresses to under 8MB
- ✅ Adds "🔗 Link in bio" (links not clickable)
- ✅ Limits caption to 2,200 characters
- ✅ Optimizes hashtags (max 30)

**For Facebook:**
- ✅ Resizes images to 1200x1200
- ✅ Compresses to under 4MB
- ✅ Makes links clickable
- ✅ Generates link preview
- ✅ Higher character limit (63K)

**For TikTok (when API available):**
- ✅ Converts videos to 9:16 vertical
- ✅ Optimizes for max 10MB
- ✅ Limits caption to 2,200 characters
- ✅ Hashtag optimization

**For Email:**
- ✅ Injects tracking pixel (opens)
- ✅ Rewrites links for click tracking
- ✅ Adds UTM parameters for Google Analytics
- ✅ Handles unsubscribe link

---

## 📊 Analytics & Tracking

### Email Analytics (Available Now)

**View at:** `http://localhost:3000/projects/demo-project/campaigns/[id]`

**Metrics:**
- Opens (unique + total)
- Clicks (unique + total)
- Open rate %
- Click rate %
- Unsubscribes
- Link performance

### Social Media Analytics (Streamlit - Coming Soon)

**Will show:**
- Likes per post
- Comments per post
- Shares (Facebook)
- Reach & impressions
- Cross-channel comparison (Email vs Social)
- Best performing content
- Engagement trends

### Google Analytics (Via UTM)

**Add UTM parameters:**
- Source: `newsletter`
- Medium: `email` or `social`
- Campaign: `week-1-ai-video`
- Content: `main-cta`

**View in GA4:**
- Reports → Acquisition → Traffic Acquisition
- Filter by Medium = "email" or "social"
- See conversions, revenue, behavior

---

## 💡 Pro Tips

### Content Strategy

**1. Repurpose Like a Pro:**
- Long AI video → Email embed
- Short clip → Instagram Reel
- Still frame → Facebook post
- Quote card → All platforms

**2. Platform-Specific Optimization:**
- Instagram: Focus on visuals + story
- Facebook: Add clickable links + longer text
- TikTok: Vertical video + trending sounds
- Email: In-depth content + CTA

**3. Hashtag Strategy:**
```
Broad: #AI #Content #Marketing
Niche: #AIVideo #SoraAI #ContentCreation
Branded: #YourBrand #YourSeries
```

### Posting Schedule

**Best Times to Send:**
- Email: Tuesday-Thursday, 10am-2pm
- Instagram: Mon-Fri, 11am-1pm, 7pm-9pm
- Facebook: Wed-Fri, 1pm-4pm
- TikTok: Tue-Thu, 7pm-11pm

**Frequency:**
- Weekly AI videos → Consistent schedule (every Monday)
- Ebook quotes → 2-3x per week
- Mix in other content to keep feed active

### Engagement Boosting

**Email:**
- Clear subject lines (no clickbait)
- Personalized greeting
- Single clear CTA
- Mobile-optimized

**Social:**
- First 3 seconds matter (video hook)
- Ask questions in captions
- Use stories/reels for reach
- Engage with comments quickly

---

## 🔧 Technical Details

### Media Processing

**Images:**
- Accepted formats: JPEG, PNG, WebP
- Max size: 100MB (automatically compressed)
- Output formats:
  - Original URL
  - Optimized URL (web quality)
  - Thumbnail URL (300x300)

**Videos:**
- Accepted formats: MP4, MOV, WebM
- Max size: 100MB
- Requirements:
  - Instagram: 60 sec max, MP4, H.264
  - Facebook: 240 min max, MP4, H.264
  - TikTok: 10 min max, 9:16 aspect ratio

### Storage

**Development:**
- Files stored in `/public/uploads/social-media/`
- Accessible via `/uploads/social-media/filename.jpg`

**Production (Recommended):**
- Use Cloudflare R2 (zero egress fees)
- Or AWS S3/DigitalOcean Spaces
- Configure in `.env`:
  ```bash
  R2_ENDPOINT="https://your-account.r2.cloudflarestorage.com"
  R2_ACCESS_KEY_ID="key"
  R2_SECRET_ACCESS_KEY="secret"
  R2_BUCKET_NAME="everlight-media"
  R2_PUBLIC_URL="https://cdn.yoursite.com"
  ```

### Publishing Flow

```
1. Upload media → Optimization → Thumbnails generated
2. Write content → Auto-adapt per platform
3. Create campaign → Saves as DRAFT
4. Click "Send" → Email sending starts
5. Emails sent → Social posting triggered (non-blocking)
6. For each platform:
   - Create SocialMediaPost record (status: PUBLISHING)
   - Call platform API (with retry logic)
   - Update status: PUBLISHED or FAILED
   - Log activity
7. Done! All channels updated
```

**Retry Logic:**
- 3 attempts with exponential backoff
- Handles rate limits (429 errors)
- Logs failures without blocking email send
- Manual retry option in UI (coming soon)

---

## 🛠️ Troubleshooting

### "Upload Failed" Error

**Problem:** File too large or wrong format

**Solution:**
- Check file size (max 100MB)
- Use supported formats: JPG, PNG, WebP, MP4, MOV, WebM
- Try compressing file before upload

### "Social Post Failed" in Logs

**Problem:** Platform API error

**Solution:**
1. Check social media settings page
2. Verify account status is "Connected"
3. If "Token Expired" → Disconnect and reconnect
4. Check activity log for specific error message

### "Instagram Link Not Clickable"

**This is normal!** Instagram doesn't support clickable links in captions.

**Workaround:**
- Use "Link in bio" strategy
- Add URL to Instagram bio
- Mention "Link in bio" in caption
- Use Instagram Stories for swipe-up (if eligible)

### Video Upload Slow

**Problem:** Large video file

**Solution:**
- Compress video before upload:
  - Use HandBrake or ffmpeg
  - Target: H.264, 1080p, 5-10 Mbps
  - Should reduce to 20-50MB for 1-3 min video
- Upload on faster connection

---

## 🎯 Next Steps

### This Week

1. ✅ Set up Facebook App (developers.facebook.com)
2. ✅ Add credentials to `.env`
3. ✅ Connect Facebook + Instagram accounts
4. ✅ Create your first campaign
5. ✅ Send to all channels!

### Next Month

1. Build content library (10-20 videos/images)
2. Establish posting schedule (e.g., every Monday)
3. Monitor analytics → Optimize content
4. Grow subscriber/follower count
5. Track conversions in Google Analytics

### Long Term

1. **TikTok Integration** (when API approved)
2. **Streamlit Analytics** (social metrics + charts)
3. **Scheduled Posts** (set future publish times)
4. **A/B Testing** (test different captions/images)
5. **Automation** (recurring campaigns)

---

## 📝 Example Campaign Templates

### Template 1: Weekly AI Video

**Name:** Week [X]: [Topic]
**Email Subject:** 🎬 New Episode: [Topic]
**Email Content:**
```html
<h1>This Week's AI Video</h1>
<p>Hey [First Name],</p>
<p>This week I'm exploring [topic]...</p>
<video src="[video-url]" controls></video>
<a href="[website]?utm_source=newsletter&utm_medium=email&utm_campaign=week-[X]">Watch on Website</a>
<p>{{unsubscribe_link}}</p>
```

**Social Caption:**
```
New episode is live! 🎬

This week: [Brief description]

[2-3 sentence summary]

Watch the full video → Link in bio

#AI #Video #ContentCreation #[Topic]
```

**Hashtags:** #AI #Video #Sora #ContentCreation #[YourNiche]

---

### Template 2: Ebook Quote + Image

**Name:** Ebook Quote: [Theme]
**Email Subject:** 💡 Quote from upcoming ebook
**Email Content:**
```html
<h1>Wisdom from the Book</h1>
<p>Here's an excerpt from my upcoming ebook:</p>
<img src="[quote-image]" alt="Quote" />
<blockquote>"[Full quote]"</blockquote>
<p>Pre-order link: [link with UTM]</p>
<p>{{unsubscribe_link}}</p>
```

**Social Caption:**
```
From my upcoming ebook 📚

"[Quote]"

Pre-order link in bio!

#Ebook #Writing #[Topic] #ContentMarketing
```

**Hashtags:** #Ebook #Writing #Quotes #[YourNiche]

---

### Template 3: Multi-Content Roundup

**Name:** Weekly Roundup: [Date]
**Email Subject:** 📬 This Week's Content Roundup
**Email Content:**
```html
<h1>This Week's Highlights</h1>

<h2>🎬 New Video</h2>
<p>[Video description]</p>
<a href="[video]">Watch Now</a>

<h2>📚 Ebook Update</h2>
<p>[Progress update]</p>
<img src="[preview-image]" />

<h2>💡 Quote of the Week</h2>
<blockquote>"[Quote]"</blockquote>

<p>{{unsubscribe_link}}</p>
```

**Social Caption:**
```
This week's highlights 🌟

✅ New AI video episode
✅ Ebook progress update
✅ Quote of the week

Check them all out → Link in bio

#WeeklyRoundup #Content #AI #Ebook
```

---

## ✅ Success Checklist

Before your first campaign:
- [ ] PostgreSQL running (`docker ps`)
- [ ] Facebook App credentials in `.env`
- [ ] Facebook + Instagram accounts connected
- [ ] At least 1 subscriber contact added
- [ ] Test email address working (or Resend API key)
- [ ] App running (`npm run dev`)

For each campaign:
- [ ] Video/image uploaded and optimized
- [ ] Email content written with {{unsubscribe_link}}
- [ ] Social caption crafted (max 2,200 chars)
- [ ] Hashtags added (max 30)
- [ ] Platforms selected
- [ ] Preview checked
- [ ] Send button clicked!

After sending:
- [ ] Check email inbox (test recipient)
- [ ] Check Instagram feed
- [ ] Check Facebook page
- [ ] Verify tracking pixel loads (email HTML source)
- [ ] Monitor activity log
- [ ] Review analytics after 24-48 hours

---

## 🎉 You're All Set!

You now have a complete content distribution machine:

**Input:** AI video or ebook image
**Process:** One upload → auto-optimized → distributed
**Output:** Email + Instagram + Facebook + (TikTok soon)

**Time Saved:** 30+ minutes per post
**Reach:** All your channels at once
**Analytics:** Unified tracking across platforms

Start creating and distributing your content today! 🚀

Questions? Check `SOCIAL_MEDIA_INTEGRATION_GUIDE.md` for technical details.
