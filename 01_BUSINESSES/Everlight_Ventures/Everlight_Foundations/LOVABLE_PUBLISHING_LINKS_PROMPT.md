# LOVABLE PROMPT: Fix Publishing Page Links & Content

Paste this into Lovable to wire up all publishing content with working links.

---

## PROMPT:

Update the /publishing page and all book detail pages to use consistent, working links for downloads, samples, audio, and coloring pages. All free content is served from a public Supabase Storage bucket. Paid content goes through the checkout flow.

### PUBLIC CONTENT BASE URL
`https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/public-content/`

### BOOK COVERS (use on book cards, detail pages, OG images)
- Book 1: `covers/Book1_Cover.jpg`
- Book 2: `covers/Book2_Cover.jpg`
- Book 3: `covers/Book3_Cover.jpg`
- Book 4: `covers/Book4_Cover.jpg`
- Book 5: `covers/Book5_Cover.jpg`

### AUDIO SAMPLES (free, playable on page)
ElevenLabs Hollywood voice -- one trailer sample per book stored in Supabase:
- Book 1: `{SUPABASE_URL}/storage/v1/object/public/audio-assets/sam_1/trailer_sample.mp3`
- Book 2: `{SUPABASE_URL}/storage/v1/object/public/audio-assets/sam_2/trailer_sample.mp3`
- Book 3: `{SUPABASE_URL}/storage/v1/object/public/audio-assets/sam_3/trailer_sample.mp3`
- Book 4: `{SUPABASE_URL}/storage/v1/object/public/audio-assets/sam_4/trailer_sample.mp3`
- Book 5: `{SUPABASE_URL}/storage/v1/object/public/audio-assets/sam_5/trailer_sample.mp3`

Add an HTML5 audio player on each book's detail section. Style it with the gold/dark Everlight theme:
- Dark container (#1A1A1A), gold progress bar (#D4AF37)
- Play/pause button, progress slider, time display
- Label: "Sample audio book" (ElevenLabs Hollywood voice)

### FREE SAMPLE READERS (HTML -- rendered in modal/iframe)
- Book 1: `samples/book1_reader.html`
- Book 2: `samples/book2_reader.html`

IMPORTANT: Supabase Storage serves .html files as text/plain for security. Do NOT open these URLs directly in a new tab (they will show raw HTML source code). Instead:
1. "Read a Free Sample" button opens a full-screen modal overlay (dark backdrop, centered white container, close X button)
2. On click, fetch() the HTML content from the public URL
3. Create a Blob with type "text/html": `new Blob([htmlText], { type: "text/html" })`
4. Create a blob URL: `URL.createObjectURL(blob)`
5. Display in an iframe inside the modal: `<iframe src={blobUrl} style={{ width: "100%", height: "80vh", border: "none" }} sandbox="allow-same-origin" />`
6. Revoke the blob URL on modal close: `URL.revokeObjectURL(blobUrl)`
This renders the book reader properly with all CSS styling intact. Gold outline button style on the card.

### COLORING PAGES (free PDF download)
- Book 1 Coloring Book: `coloring/Sams_First_Firepower.pdf`

Add "Download Free Coloring Pages" button on the Adventures with Sam series section. Use an anchor tag with the `download` attribute: `<a href="https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/public-content/coloring/Sams_First_Firepower.pdf" download="Sams_First_Firepower_Coloring_Pages.pdf">`. This forces a download instead of opening in browser. Use a fun, kid-friendly button style (colorful, with crayon/pencil icon).

### PURCHASE BUTTONS (checkout flow)
Each book's "Buy Now" button should call the create-checkout Edge Function:
```
POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/create-checkout
Headers: { "Content-Type": "application/json", "apikey": "<anon-key>" }
Body: { "slug": "<slug>", "success_url": "https://everlightventures.io/purchase/success?session_id={CHECKOUT_SESSION_ID}" }
```

Anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

**Slugs and prices:**
| Book | Slug | Price |
|------|------|-------|
| Sam's First Superpower | sam-book-1 | $7.99 |
| Sam's Second Superpower | sam-book-2 | $7.99 |
| Sam's Third Superpower | sam-book-3 | $7.99 |
| Sam's Fourth Superpower | sam-book-4 | $7.99 |
| Sam's Fifth Superpower | sam-book-5 | $7.99 |
| Complete Bundle (5 Books) | sam-bundle | $29.99 |
| Beyond the Veil | beyond-the-veil | $9.99 |

### PUBLISHING PAGE LAYOUT

**Hero Section:**
- "Everlight Publishing" header in gold
- Subtitle: "Stories Built to Last"
- Brief description of the publishing arm

**Adventures with Sam Section:**
- Series banner with gradient background
- "Adventures with Sam & Robo" title
- "A 5-book children's series about emotional intelligence, friendship, and finding your superpowers"
- Age range badge: "Ages 4-10"
- Bundle deal callout: "Get all 5 books for $29.99 (save 60%!)" with "Buy Bundle" button (slug: sam-bundle)
- Grid of 5 book cards (2-3 per row on desktop, 1 on mobile)
- "Download Free Coloring Pages" button below the grid
- Each book card has:
  - Cover image (from public bucket)
  - Title
  - Brief tagline (Sam's superpower for that book)
  - Audio sample player (inline, small)
  - "Buy Now - $7.99" button
  - "Read Sample" link (Books 1 & 2 only)

**Book taglines:**
- Book 1: "Kindness is the first superpower"
- Book 2: "Courage to try new things"
- Book 3: "The power of teamwork"
- Book 4: "Believing in yourself"
- Book 5: "Leading with your heart"

**Beyond the Veil Section:**
- Separate section with darker, more mature styling
- "Beyond the Veil" title in elegant serif
- "A paranormal western where faith and fire collide"
- Genre badge: "Paranormal Western | Ages 16+"
- Cover image
- "Buy Now - $9.99" button
- Audio sample player
- Brief synopsis (2-3 sentences)

**Bottom CTA:**
- "More books coming soon. Join our mailing list for release updates."
- Email capture field (stores to Supabase or just mailto link for now)

### COPY PROTECTION NOTE
The success page should use the new token-based download system. After purchase, the verify-ebook-purchase function returns a `token_download_url`. Use that for the download button instead of the raw `download_url`. This enforces the 3-download limit. Show "3 downloads remaining" text below the button, decrementing as they download.

### CONSISTENCY REQUIREMENTS
- Every book must have a working cover image
- Every book must have a working audio sample
- Every "Buy" button must trigger the checkout flow (not a dead link)
- The Bundle must clearly show it includes all 5 books
- Beyond the Veil must have its own distinct visual treatment (not childish)
- All external links open in new tab
- Mobile responsive: cards stack, audio players full-width
