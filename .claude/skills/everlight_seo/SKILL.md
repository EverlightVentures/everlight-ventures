---
name: everlight_seo
description: SEO pass for any public-facing Everlight content (everlightventures.io, blog, book listings, landing pages). Wraps the everlight_seo_formatter agent. Micro tie-in -- public-site discoverability gates inbound for Deal 1 and SaaS.
---

When to use:
- Any content destined for everlightventures.io (React/Vite site at 06_DEVELOPMENT/everlightventures/), the blog, KDP/book listings, or a landing page.
- Before publishing a Google Doc report that will also be posted publicly.

NOT for:
- Internal reports, Slack posts, seller/buyer outreach email (those use voice registers, not SEO).
- Anything behind 127.0.0.1 (private dashboards are not indexed by design).

Procedure:
1. Hand the draft to the everlight_seo_formatter agent for the structural pass.
2. Title + meta description: one primary keyword, under 60 chars title / 155 chars meta.
3. Headings: one H1, keyword in first H2, scannable subheads.
4. Schema: add JSON-LD (Article, Product, or FAQ) matching content type.
5. Internal links: at least two links to other Everlight pages; reads from Supabase content table, never hardcoded URLs.
6. Image alt text on every asset. Open Graph + Twitter card tags present.
7. Output: write to the site repo content path or 02_CONTENT_FACTORY/01_Queue/, never the root.

Brand: gold #D4A843 accents, Playfair/Inter, EVERLIGHT VENTURES wordmark inherited from report_template.py. Never hardcode brand colors.

Register in roster.yaml under skills: owner = everlight_seo_formatter, buddy = everlight_content_director.
