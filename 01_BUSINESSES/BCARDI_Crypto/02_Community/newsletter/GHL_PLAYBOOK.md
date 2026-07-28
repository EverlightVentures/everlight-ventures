# $BCARDD Newsletter on GoHighLevel - Operator Answer-Sheet

> **Status: PLAN ONLY.** Nothing here is built or paid for yet. This is the
> field-by-field sheet so you can stand the whole thing up in one sitting when
> you decide the cost is worth it. Until then, the *our-side* build
> (Resend + `bcardd_email.py`) is live and free. Per
> [[feedback_full_answer_sheets_before_forms]]: everything you'll be asked is
> answered in advance here, so you never have to bounce back mid-setup.

This is the exact stack Brody used (GoHighLevel / LeadConnector). Fingerprints
in his email: `services.msgsndr.com` unsubscribe links, `email.exosoft.io`
click-tracking domain, `filesafe.space` media CDN, MJML layout.

## 0. Decide first: do you even need GHL?
| | Our side (live now) | GoHighLevel |
|---|---|---|
| Cost | Free (Resend already paid) | ~$97/mo (Starter) |
| Signup page | `join.html` we host | GHL hosts it for you |
| Email editor | Custom HTML (`bcardd_email.py`) | Drag-and-drop, picture-rich |
| Guards | resend_guard + budget + scrub | You re-create manually |
| List ownership | Ours (Supabase) | Theirs, sync back to us |
| Best when | You want it free + controlled | You want a no-code funnel + CRM |

**Recommendation:** stay our-side until the list crosses ~500 confirmed subs or
you want SMS + pipelines in one place. Then GHL earns its keep.

## 1. Account + plan
- Sign up at gohighlevel.com. Tier: **Starter (~$97/mo)** is enough for one
  newsletter. Agency/Pro only if you resell it.
- Login owner: Rich. Store creds in Proton Pass (see [[reference_crypto_seed_vault]]
  discipline, same vault habit).

## 2. Sending domain (do this BEFORE any send)
- Use a **dedicated `bcardd` domain**, NOT everlightventures.io. Keeps the brand
  faceless + legally separate (per [[project_brand_entity_separation_roadmap]]).
- In GHL: Settings > Email Services > Dedicated Domain. Add the SPF, DKIM, and
  the tracking CNAME records they show you to your DNS (Cloudflare). Wait for
  green checks before sending, or everything lands in spam.

## 3. Signup funnel page (the capture)
- Sites > Funnels > New > "Optin". One step.
- Headline: **Join the pack**
- Sub: **Card drops, game updates, and memes that actually hit. First one's on the house.**
- Field: email only (lower friction = more signups).
- Button: **Deal me in**
- Hero: the dog image (use the same art as `_state/bcardd_ops` pages).
- Footer block, verbatim: `$BCARDD is a meme coin and a game, for fun and
  community, not an investment. DYOR. Never bet the rent.`
- Link this funnel URL from the `bcardd` share/kit pages + your X and Telegram bios.

## 4. The intro email (paste, don't retype)
- Marketing > Emails > New > Builder.
- Subject: **You found me** (with the joker emoji).
- From name: **$BCARDD**, from address: your dedicated-domain address.
- Body: paste the copy that `bcardd_email.py` already produces (run
  `python3 bcardd_email.py --preview` and copy from `preview.html`). Re-upload
  the dog hero + the GIF montage into GHL's media library; swap the `<img>` srcs.
- Keep the reply call-to-action ("hit reply, tell me your favorite hand"). GHL
  routes replies to your inbox, same deliverability win Brody gets.

## 5. Double opt-in + welcome automation
- Automation > Workflows > New.
- Trigger: **Form/Funnel submitted**.
- Step 1: send a 1-line "confirm you're in" email with a confirm link.
- Step 2 (on confirm / tag added): send the **intro email** from section 4.
- This matches Brody's "I only want people who actually want it" permission play.

## 6. List sync back to us (never let GHL own the list)
- Automation > add an **Outbound Webhook** step on confirm, POST to a small
  `bcardd-ghl-sync` Supabase edge function that upserts the email into our
  `bcardd_subscribers` table. We stay the source of truth even if we leave GHL.

## 7. Compliance footer (same as our side)
- Fun-only disclaimer (section 3) + the LLC **registered-agent postal address**
  (NEVER a PO box, per [[feedback_wholesale_digital_only_no_postal_box]]) +
  the GHL unsubscribe token. CAN-SPAM requires the physical address and a working
  unsubscribe on every send.

## What you still owe regardless of GHL vs our-side
1. Registered-agent postal address for the footer.
2. The free-gift link (gems / card / blackjack seat, rides `ak_grants`).
3. The dog hero image + a GIF montage of card drops / game clips (your
   "real pictures", the part you liked in Brody's).
