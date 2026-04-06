# LOVABLE PROMPT: Hive Mind Product Page + Private Dashboard

Paste everything below into Lovable. This replaces the current /hivemind page with a full product page that sells Hive Mind as a downloadable local AI environment, with subscriptions via Stripe. The private /hivemind/dashboard route remains for the owner's war room view.

**Supabase URL:** `https://jdqqmsmwmbsnlnstyavl.supabase.co`
**Anon Key:** (already connected -- use the existing Supabase integration)

---

## ROUTE STRUCTURE

- `/hivemind` -- Public product page (visible to everyone, no auth required)
- `/hivemind/dashboard` -- Private war room (auth-gated, owner only)

---

## PAGE: /hivemind (PUBLIC PRODUCT PAGE)

### Design System

- Background: #0A0A0A (Void Black)
- Cards: #1A1A1A with border #2A2A2A
- Primary accent: #7C3AED (Violet)
- Secondary accent: #D4AF37 (Everlight Gold)
- Text: #E5E5E5 (Platinum), muted: #8A8A8A (Smoke)
- Heading font: Inter 700
- Body font: Inter 400

---

### SECTION 1: HERO

**Headline:** Your Own AI War Room. On Your Phone.

**Subhead:** Four AI systems. Full file access. Runs locally. No cloud middleman.

**Supporting text (1-2 lines below subhead, muted color):**
"This is not another chat window. Hive Mind installs directly on your device and gives AI agents full read, write, and execute access to your actual files. It does not summarize -- it builds, edits, deploys, and operates."

**Background:** Dark (#0A0A0A) with an animated neural network visualization -- nodes and connecting lines in violet (#7C3AED) and gold (#D4AF37), slow-pulsing, low opacity (15-20%). The nodes should drift gently, with occasional pulses traveling along the connections. Think constellation map, not a screensaver. Canvas-based or CSS animation -- keep it lightweight.

**Two CTA buttons side by side:**
- Primary (filled, gold #D4AF37, black text): "Download Free Trial"
- Secondary (outlined, violet border, white text): "Watch Setup Video"

"Download Free Trial" scrolls to the pricing section.
"Watch Setup Video" opens a modal with an embedded YouTube video (placeholder: use a 16:9 dark frame with centered play button and text "Setup Video Coming Soon" until video is ready).

Below the buttons, small muted text: "14-day free trial. 5 queries/day. No credit card required."

---

### SECTION 2: HOW IT WORKS (3-step visual)

Section heading: "Install It. Open It. Use It."

Three cards in a horizontal row (stack vertically on mobile). Each card has a large step number (1, 2, 3) in violet, an icon, a title, and a short description.

**Step 1: Download the Installer**
Icon: Download/arrow-down
"One script sets up everything -- Termux, Ubuntu, Python, Claude CLI, the dashboard, and all four AI agents. No manual config. Run it and walk away."

**Step 2: Open Your War Room**
Icon: Terminal/monitor
"Launch the dashboard on localhost:8504. Claude, Gemini, Codex, and Perplexity are all running locally on your device, ready to take orders."

**Step 3: Work With Your Files**
Icon: Folder with gear/wrench
"The AI agents can read, write, edit, and execute code on YOUR machine. Not a sandbox. Not a playground. Your actual workspace -- your projects, your repos, your data."

Visual connector lines between the three cards (animated on scroll -- a line draws from step 1 to step 2 to step 3). On mobile, use a vertical dotted line instead.

---

### SECTION 3: KEY DIFFERENTIATOR

Section heading: "This Is Not Another Chat Window"

**Subhead (muted):** "Online chatbots can only talk. Hive Mind can do."

Display a comparison table with clean styling -- dark rows, alternating subtle backgrounds (#1A1A1A / #151515), violet highlight on the Hive Mind column header.

| Feature | ChatGPT / Gemini Online | Hive Mind |
|---|---|---|
| File access | No -- copy/paste only | Full read / write / execute |
| Multiple AI agents | One at a time | 4 running in parallel |
| Code execution | Sandbox only | Your real environment |
| Customization | None | Your agents, your rules |
| Offline capable | No | Yes (except AI API calls) |
| Data privacy | Sent to cloud servers | Stays on your device |
| Workspace integration | Zero | Full access to your files, repos, and tools |

Use checkmark icons (green) for Hive Mind advantages and X icons (red/muted) for the online chatbot limitations. Make the contrast obvious.

---

### SECTION 4: AGENT PROFILES

Section heading: "Meet the Team"

Four cards, one per agent, in a 2x2 grid (stack on mobile). Each card has the agent's color as a subtle top border glow.

**Claude -- Chief Operator**
Color: Purple (#8B5CF6)
"Strategy, architecture, risk assessment, and long-form synthesis. Claude sees the whole board and plans the moves. Runs locally via the official Claude Code CLI."

**Gemini -- Logistics Commander**
Color: Blue (#3B82F6)
"Workflow automation, distribution, multi-tool orchestration. Gemini takes the plan and builds the pipeline."

**Codex -- Engineering Foreman**
Color: Green (#10B981)
"Code generation, SaaS architecture, funnel building, ROI analysis. Codex writes the software and runs the numbers."

**Perplexity -- Intelligence Anchor**
Color: Orange (#F59E0B)
"Real-time research across 8 beats: crypto, finance, tech, business, science, legal, news, and local intel. Perplexity always runs first so every agent starts with fresh data."

Each card should have a subtle animated pulse on the status dot (like a heartbeat) when the page loads.

---

### SECTION 5: WHAT'S INCLUDED

Section heading: "Everything in the Box"

Eight items in a 2x4 grid (single column on mobile). Each item has a small icon, a bold title, and a one-line description.

**Termux + Ubuntu Environment**
"Auto-installed. Full Linux environment running natively on your device. No root required."

**Claude Code CLI**
"Anthropic's official command-line tool. Direct access to Claude with full file system permissions."

**Hive Mind Dashboard**
"Web UI on localhost:8504. War room view, session history, agent status, analytics -- all in your browser."

**Smart Query Routing**
"The router reads your prompt and auto-picks the right agents. Trading questions get Claude + Codex + Perplexity. Content tasks get Claude + Gemini. You never pay for agents you do not need."

**War Room View**
"See each agent's individual reasoning side by side. Compare perspectives, spot disagreements, make better calls."

**Session History + Analytics**
"Every session stored and searchable. Filter by date, category, or agent. Your past decisions build a knowledge base that improves future answers."

**Supabase Cloud Sync**
"Your session data backs up to Supabase automatically. Access your history from any device. Your local files stay local."

**Parallel Execution**
"All selected agents run at the same time. A 4-agent session takes as long as the slowest agent -- not the sum of all four."

---

### SECTION 6: FEATURES GRID

Section heading: "What Sets It Apart"

Four cards in a 2x2 grid (single column on mobile). Each card has an icon, a title, and a 1-2 sentence description.

**Full File System Access**
Icon: Folder/open
"Agents can read your code, edit your configs, write new files, and run scripts. This is not a chat -- it is an operating environment."

**Runs on Your Hardware**
Icon: Phone/device
"Everything executes on your device. Your data never leaves your machine unless you explicitly sync it. No cloud processing of your files."

**Works Offline (Mostly)**
Icon: Wifi-off
"The local environment, dashboard, and file tools all work without internet. Only the AI API calls need a connection."

**API Access (Enterprise)**
Icon: Code brackets
"Build on top of the platform. POST a prompt, GET a synthesized result. Use the same orchestration engine in your own tools and automations."

---

### SECTION 7: PRICING TABLE

Section heading: "Pick Your Tier"
Subheading: "All plans include a 14-day free trial at 5 queries/day. No credit card required to start."

Three pricing cards side by side. The middle card (Hive) should be visually highlighted -- slightly larger, gold border, "Most Popular" badge.

**Spark -- $49/mo**
- 5 queries per day
- 2 agents: Claude + Perplexity
- Dashboard access (localhost:8504)
- Session history (30-day window)
- Email support
- CTA button: "Download Free Trial"

**Hive -- $129/mo** (highlighted, "Most Popular" badge in gold)
- 100 queries per day
- All 4 agents: Claude, Gemini, Codex, Perplexity
- Full dashboard + war room view
- Full RAG memory (1-year window)
- Priority support
- CTA button: "Download Free Trial"

**Enterprise -- $399/mo**
- Unlimited queries
- All 4 agents with custom agent configs
- Full dashboard + war room + analytics
- Unlimited RAG memory
- API access
- Team deployment (multi-device install)
- Priority support (4h response)
- CTA button: "Download Free Trial"

**Stripe Integration:**

Each "Download Free Trial" button calls a Supabase Edge Function named `create-checkout` that creates a Stripe Checkout Session.

The edge function should accept a `slug` parameter and map it to a Stripe Price ID:
- `hivemind-spark` -> Stripe price for $49/mo recurring
- `hivemind-hive` -> Stripe price for $129/mo recurring
- `hivemind-enterprise` -> Stripe price for $399/mo recurring

All checkout sessions should have:
- `mode: 'subscription'`
- `subscription_data.trial_period_days: 14`
- `success_url: https://everlightventures.io/hivemind?success=true`
- `cancel_url: https://everlightventures.io/hivemind?canceled=true`

Create the Stripe products in the Stripe Dashboard first:
- Product: "Hive Mind Spark" -- $49/mo recurring
- Product: "Hive Mind Hive" -- $129/mo recurring
- Product: "Hive Mind Enterprise" -- $399/mo recurring

Below the pricing cards, centered muted text: "All plans billed monthly. Cancel anytime from your dashboard. Founding members get their rate locked for life."

---

### SECTION 8: REQUIREMENTS

Section heading: "What You Need"

A single card or clean list with a subtle border. Four items, each with a checkmark icon:

- **Android phone with Termux** (or any Linux device)
- **2GB+ free storage** (for the full environment)
- **Internet connection** (for AI API calls -- local tools work offline)
- **Also works on:** Linux, WSL on Windows, macOS terminal

Small muted note below: "The installer handles all dependencies. You do not need to know Linux."

---

### SECTION 9: USE CASES

Section heading: "How People Use It"

Three use case cards in a row. Each card shows a sample prompt in a code-like monospace block, then an arrow, then a list of which agents engaged and what they produced.

**Use Case 1:**
Prompt: "Audit my trading bot config and flag anything risky"
Agents engaged: Claude (risk assessment) + Codex (code review) + Perplexity (market data)
Result preview: "Claude read the config file directly, flagged overlapping entry conditions. Codex found an uncapped position size in the loop logic and wrote a fix. Perplexity pulled current volatility data to validate the stop-loss thresholds. Patched config committed to the repo."

**Use Case 2:**
Prompt: "Write a Q2 content strategy and save it to my content folder"
Agents engaged: Claude (strategy) + Gemini (distribution plan) + Perplexity (competitor research)
Result preview: "Perplexity found 3 direct competitors and their posting cadences. Claude built a 12-week editorial calendar. Gemini mapped distribution channels and wrote a scheduling script. Strategy doc saved directly to /content/Q2_strategy.md -- no copy-paste needed."

**Use Case 3:**
Prompt: "Review the checkout code, fix the webhook bug, and deploy"
Agents engaged: Codex (code review + fix) + Perplexity (dependency audit)
Result preview: "Codex read the diff, found a missing null check in the webhook handler, wrote the fix, and committed it. Perplexity checked updated packages for known vulnerabilities. Deployment script ran from the terminal. Done in one session."

---

### SECTION 10: SOCIAL PROOF

Section heading: "What Early Users Say"

Three testimonial cards with placeholder content. Each card has a quote, a name, and a role. Use quotation marks, not italic styling.

Card 1:
"I was paying for ChatGPT, Claude, and Perplexity separately and none of them could touch my files. This replaced all three and actually does real work on my machine."
-- J.M., Solo SaaS Founder

Card 2:
"The fact that it runs locally sold me. I pointed it at my codebase and it just... worked. Read the files, made edits, ran tests. No copy-pasting into a browser."
-- R.K., Full-Stack Developer

Card 3:
"I use it on my phone. Four AI agents with full access to my project files, running from Termux. It sounds fake until you try it."
-- A.T., Mobile-First Operator

Muted text below: "Testimonials from early access beta program."

---

### SECTION 11: FAQ

Section heading: "Questions"

Accordion-style FAQ. Click to expand, click again to collapse. Only one open at a time.

**Q: What exactly gets installed on my device?**
A: A Termux terminal environment, an Ubuntu layer inside it, Python, the Claude Code CLI, and the Hive Mind dashboard + orchestration scripts. The installer handles everything -- you run one command and it sets up the full environment.

**Q: Do I need to root my phone?**
A: No. Termux runs in userspace. No root, no unlocked bootloader, no voided warranty.

**Q: What AI models does Hive Mind use?**
A: Claude (Anthropic) for strategy and synthesis, Gemini (Google) for workflow and logistics, Codex (OpenAI) for code and engineering, and Perplexity for real-time research. The router picks which agents engage based on your prompt.

**Q: Do I need my own API keys?**
A: No. All AI API access is included in your subscription. You do not need accounts with Anthropic, Google, OpenAI, or Perplexity.

**Q: Does it work without internet?**
A: The local environment, file tools, and dashboard all work offline. The AI agents need an internet connection to call their APIs. So you can browse your session history and files offline, but new queries need a connection.

**Q: Is my data private?**
A: Your files never leave your device. The AI agents run API calls to process your prompts, but your local filesystem stays local. Session metadata syncs to Supabase (encrypted), but your actual project files are never uploaded anywhere.

**Q: What does "RAG memory" mean?**
A: The system remembers your past sessions and uses them as context for future queries. If you told the hive last month that you run a SaaS company targeting SMBs, it remembers that without you repeating it. Spark keeps 30 days. Hive keeps 1 year. Enterprise keeps everything.

**Q: Can I cancel anytime?**
A: Yes. Cancel from your dashboard. Your subscription ends at the end of the billing period. No contracts, no cancellation fees, no hoops. The local environment stays on your device -- you just lose API access.

**Q: Does it work on desktop?**
A: Yes. Anything that runs a Linux terminal works -- native Linux, WSL on Windows, macOS terminal. The phone setup uses Termux, but the same scripts run on any POSIX environment.

**Q: Is there an API?**
A: API access is included in the Enterprise plan. POST a prompt, GET a synthesized result with individual agent reports. Full REST API documentation provided on activation.

---

### SECTION 12: FOOTER CTA

Dark section with violet gradient background (subtle, not flashy).

Headline: "Ready to run your own war room?"

Subhead: "Download it. Install it. Own it."

Email capture field + "Download Free Trial" button (gold, same style as hero CTA).

The email capture should insert into a Supabase table:

```sql
create table if not exists hivemind_leads (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  source text default 'footer_cta',
  created_at timestamptz default now()
);
alter table hivemind_leads enable row level security;
create policy "Service can insert leads" on hivemind_leads for insert with check (true);
create policy "Owner can read leads" on hivemind_leads for select using (
  (select role from user_profiles where id = auth.uid()) = 'owner'
);
```

After submission, show a success message: "You are in. Check your email for download instructions."

---

## PAGE: /hivemind/dashboard (PRIVATE -- OWNER ONLY)

This is the private war room view. It uses the EXACT same layout, tables, and design described in the existing LOVABLE_HIVEMIND_PRIVATE_PROMPT.md document. Do not change anything about that dashboard -- just move it from /hivemind to /hivemind/dashboard.

### Access Control

- If not authenticated: redirect to /login
- If authenticated but not owner (check `user_profiles.role = 'owner'`): show "Access Denied -- This page is restricted to system operators." with a link back to /hivemind
- Only users with `role = 'owner'` in the `user_profiles` table can see this route

### Navigation

- The /hivemind nav link goes to the PUBLIC product page (visible to everyone)
- The /hivemind/dashboard link should ONLY appear in the nav for authenticated owner users
- Use a small "Dashboard" sub-link or a lock icon next to the Hive Mind nav item for the owner

### Supabase Tables

Use the same tables from LOVABLE_HIVEMIND_PRIVATE_PROMPT.md:
- `hive_sessions` (session history)
- `hive_agent_reports` (individual agent outputs)
- `hive_agent_status` (agent health cards)
- `user_profiles` (auth + role check)

These tables should already exist if the private prompt was applied. If not, create them.

### Dashboard Layout

Replicate exactly what LOVABLE_HIVEMIND_PRIVATE_PROMPT.md describes:
- Header: "Hive Mind" title + "AI Operations Center" subtitle + online/idle status indicator
- Agent Status Grid: 4 agent cards (Claude purple, Gemini blue, Codex green, Perplexity orange)
- Recent Sessions: expandable session cards with agent reports
- Quick Stats Bar: total sessions, sessions today, tokens today, avg duration, most active agent
- Auto-refresh every 30 seconds
- Skeleton loading states
- Empty state message

---

## SUCCESS/CANCEL HANDLING

When the URL has `?success=true`:
- Show a toast notification: "Welcome to Hive Mind. Your 14-day trial has started. Check your email for download and setup instructions."
- Auto-dismiss after 8 seconds

When the URL has `?canceled=true`:
- Show a toast notification: "Checkout canceled. No charge was made. You can try again anytime."
- Auto-dismiss after 5 seconds

---

## GLOBAL NOTES

- Use the shared Everlight nav and footer from the rest of the site
- The /hivemind link in the main nav replaces the old "Join the Waitlist" version
- Smooth scroll animations on section transitions (fade-in-up on scroll)
- All sections should be responsive -- test at 375px (mobile), 768px (tablet), 1440px (desktop)
- Page load should be fast -- lazy-load the neural network animation, defer non-critical JS
- Meta tags: title "Hive Mind -- Local AI War Room | Everlight Ventures", description "Four AI agents running locally on your device with full file access. Claude, Gemini, Codex, and Perplexity in one war room. Not a chat window -- an operating environment. 14-day free trial."
