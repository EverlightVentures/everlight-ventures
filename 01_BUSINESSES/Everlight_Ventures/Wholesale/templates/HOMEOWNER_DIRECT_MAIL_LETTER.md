# HOMEOWNER DIRECT MAIL LETTER -- Cuyahoga Foreclosure Lane

**Author:** Piper Reeves, Senior Account Executive, Everlight Ventures
**Use case:** Cold first-touch direct mail to Cuyahoga County homeowners with a foreclosure case filed in the last 45 days. Skip-trace returned no email but the mailing address is verified.
**Channel:** Lob #10 yellow letter ($0.85 / piece) for Version A. Lob 4x6 postcard ($0.55 / piece) for Version B.
**Token convention:** matches `pdf_autofill` and `lob_mail_sender` merge variables.
**Compliance:** Ohio mandatory disclosure block (Section e of `HIVE_OPINION_OH_EQUITABLE_INTEREST.md`) is attached to BOTH versions and is non-negotiable.
**Tone:** Warm, neighbor-to-neighbor. The homeowner is having a hard year. We do not preach. We do not pity-shop. We give options, not pressure.

---

## VERSION A -- Yellow Letter ($0.85 / piece)

[OWNER_FIRST_NAME],

Y'all, I came across the filing on [PROPERTY_ADDRESS] (case [CASE_NUMBER]) and I wanted to reach out before anybody else does, because what's on a court docket and what's actually going on in a family's life are usually two very different things.

I am not writing to push you, and I am not an agent trying to list your home. I am with Everlight Ventures, and we are a local principal-buyer, meaning if you and I come to terms, the money to close comes from us, not from a bank you have to wait on or a buyer we still have to find.

Here is what I can offer, and you pick the piece that fits: a fair cash offer with a 14-day close on your timeline (we cover title and closing costs), a longer runway if you need 30 or 45 days to land somewhere, or honestly, just a phone call to talk through what your options actually look like, no commitment, no signature, no pressure.

I want to be straight with you up front: when we buy, we sometimes assign the contract to a partner investor in our network rather than closing in our own name, and I will tell you that on the front end every single time, never after the fact. You deserve to know who you're dealing with.

One more piece of plain talk: I want to be transparent that Marquise Smith, who founded Everlight Ventures, holds a California real estate salesperson license that is currently inactive (lapsed), and he is not licensed in Ohio. He is reaching out as a principal buyer, not as your agent, not as a broker, and not as anybody's representative.

If any of this is worth a conversation, call or text [CALLBACK_PHONE] any time, or email [CALLBACK_EMAIL] and I will get right back to you. If now is not the right time, I get it, and I wish you and your family the best either way.

Take care of yourself, [OWNER_FIRST_NAME].

Warmly,

[SIGNATURE_NAME]
[SIGNATURE_TITLE]

P.S. -- If you've already got a plan in place, I am genuinely glad. If you don't, save this letter in the kitchen drawer. The offer to just talk holds whether it's tomorrow or six weeks from now.

---

**REQUIRED DISCLOSURE BLOCK (rendered 8pt, body of letter, back side acceptable):**

> **DISCLOSURE OF PRINCIPAL-BUYER POSITION AND LICENSE STATUS**
>
> Marquise Smith, doing business as Everlight Ventures, is acting as the principal buyer of this property under a written purchase contract. Marquise Smith holds equitable interest in the contract and intends to assign that contract, or close in his own name, at his sole election. Marquise Smith is NOT acting as a real estate agent, broker, or fiduciary on behalf of the seller, and does NOT represent the seller. Marquise Smith is NOT a currently licensed real estate broker or salesperson in Ohio. Marquise Smith holds a California real estate salesperson license that is currently inactive (lapsed). Seller is encouraged to consult independent legal, tax, and real estate counsel of seller's choosing before signing any document. Earnest money is held by a licensed Ohio title agency under ORC 3953 and is refundable per the terms of the purchase contract. The Residential Property Disclosure Form required under ORC 5302.30 will be delivered as a passthrough document to any assignee. This transaction is governed by the laws of the State of Ohio.

---

## VERSION B -- Postcard ($0.55 / piece)

**FRONT (5 sentences):**

[OWNER_FIRST_NAME], I saw the filing on [PROPERTY_ADDRESS] (case [CASE_NUMBER]) and wanted to reach out before anybody else does. I am with Everlight Ventures, a local principal-buyer (not an agent, not a wholesaler hiding the ball), and we sometimes assign our purchase contract to a partner investor, which I will always tell you up front. We can offer a fair cash close in 14 days, a longer runway if you need it, or just a phone call to talk options, no commitment. Call or text [CALLBACK_PHONE], or email [CALLBACK_EMAIL]. Either way, [OWNER_FIRST_NAME], I hope your family is holding up okay. -- Piper Reeves, Senior Account Executive

**BACK (8pt disclosure, mandatory):**

> **DISCLOSURE OF PRINCIPAL-BUYER POSITION AND LICENSE STATUS**
>
> Marquise Smith, doing business as Everlight Ventures, is acting as the principal buyer of this property under a written purchase contract. Marquise Smith holds equitable interest in the contract and intends to assign that contract, or close in his own name, at his sole election. Marquise Smith is NOT acting as a real estate agent, broker, or fiduciary on behalf of the seller, and does NOT represent the seller. Marquise Smith is NOT a currently licensed real estate broker or salesperson in Ohio. Marquise Smith holds a California real estate salesperson license that is currently inactive (lapsed). Seller is encouraged to consult independent legal, tax, and real estate counsel of seller's choosing before signing any document. Earnest money is held by a licensed Ohio title agency under ORC 3953 and is refundable per the terms of the purchase contract. The Residential Property Disclosure Form required under ORC 5302.30 will be delivered as a passthrough document to any assignee. This transaction is governed by the laws of the State of Ohio.

---

## Token Reference (for `pdf_autofill` / `lob_mail_sender`)

| Token | Source field | Example |
|---|---|---|
| `[OWNER_FIRST_NAME]` | parsed first name from `owner_name` | "Marcus" |
| `[PROPERTY_ADDRESS]` | clean street address of subject property | "1247 East 79th Street, Cleveland, OH 44103" |
| `[CASE_NUMBER]` | Cuyahoga foreclosure case ref | "CV-26-987654" |
| `[CALLBACK_PHONE]` | hardcoded | (707) 801-0360 |
| `[CALLBACK_EMAIL]` | hardcoded | marquise@everlightventures.io |
| `[SIGNATURE_NAME]` | hardcoded | Marquise Smith |
| `[SIGNATURE_TITLE]` | hardcoded | Founder, Everlight Ventures |

**Sender block (return address on envelope and letter):** Piper Reeves, Senior Account Executive, Everlight Ventures, [physical address per CAN-SPAM and OH outbound rules].

**Justine pre-send filter:** must scan for forbidden phrases per Section (f) of `HIVE_OPINION_OH_EQUITABLE_INTEREST.md` ("list," "represent," "commission," "fiduciary," "REALTOR," etc.) before any batch ships.
