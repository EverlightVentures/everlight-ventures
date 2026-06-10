---
name: everlight_hyperframes
description: Turn branded HTML into short video (HTML -> MP4) for the Content Factory and SaaS launch clips. Render on e5-mother, never on the phone (proot cannot run heavy node/ffmpeg pipelines). Inspired by the hyperframes skill + the codex remotion_launch_video pattern.
---

When to use:
- A product launch needs a 15-30s clip (Onyx POS, Hive Mind SaaS, a new build).
- A report or stat deserves a short animated social asset for the Social Network Master Tree (IG/X/Discord).

NOT for:
- Long-form video, anything needing voiceover talent, or live footage.
- Quick internal updates (a Slack card is enough).

Procedure:
1. Build the scene as a single branded HTML file: gold #D4A843, dark #0A0A0A, light #E8E8E8, Playfair/Inter, EVERLIGHT VENTURES wordmark from report_template.py.
2. Inputs: product/headline + up to 3 bullets + one CTA. Keep frames short enough to read.
3. Render OFF the phone. HARD LAW: phone proot SIGSEGVs on npm install and cannot run the render pipeline. Build the HTML on the phone, render on e5-mother via the playwright MCP (screenshot frames) or a node/ffmpeg job, then rsync the MP4 back.
4. Output MP4 to 09_DASHBOARD/reports/launch_videos/. Never the workspace root.
5. Post through branded_slack (category deal or report) with the clip + a link.

Depends on: playwright MCP (queued for e5-mother), ffmpeg on e5-mother.
Register in roster.yaml under skills: owner = everlight_content_director, buddy = 63_ui_ux_designer.
