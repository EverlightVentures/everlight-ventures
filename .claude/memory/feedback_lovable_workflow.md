---
name: Lovable deployment workflow
description: User deploys to everlightventures.io via Supabase + GitHub, NOT Lovable prompts
type: feedback
---

NEVER suggest "paste this prompt into Lovable" as a deployment step. The user does NOT use Lovable prompts anymore.

**Why:** The user has moved past the Lovable prompt workflow. The site is connected to a GitHub repo and Supabase. Updates go through code pushes to GitHub and Supabase data -- then the user clicks Publish in Lovable. No manual prompt pasting.

**How to apply:** When building frontend features for everlightventures.io:
1. Push code changes to the GitHub repo that Lovable is connected to
2. Push data/schema changes to Supabase
3. The user clicks Publish in Lovable
4. NEVER create "LOVABLE_*_PROMPT.md" files or tell the user to paste anything into Lovable
