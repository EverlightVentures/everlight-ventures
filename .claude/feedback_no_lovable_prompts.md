---
name: no_lovable_copy_paste
description: NEVER ask user to paste prompts into Lovable. Update the site code directly. User is out of Lovable prompts and will not copy/paste anything.
type: feedback
---

NEVER give the user Lovable prompts to paste. Update the site code directly yourself.

**Why:** User ran out of Lovable prompts and is frustrated about being repeatedly asked to copy/paste. They want to just press "publish/update" when changes are ready.

**How to apply:** Find the Lovable project's GitHub repo or connected codebase and push changes directly. If no repo access, use the Supabase-backed site_content table to serve dynamic content. Build the actual React components and push them via whatever deployment pipeline exists. The user should never need to interact with Lovable's prompt interface again.
