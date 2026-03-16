# Plan: Adventures with Sam Series -- Full Consistency Audit & Rebuild

## Context
The user corrected a duplicate publishing path. The series now lives at:
`01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/`

All 6 build scripts still point to the OLD path (`Ebook_Sells/ADVENTURES_WITH_SAM/`).
Book 3 is severely under-built. Folder naming is inconsistent. Everything needs to be uniform before republishing on Amazon.

## Steps

### Step 1: Update all build script paths (6 files)
Update BASE_DIR in each script from the old path to the new one:
- `build_books.py`
- `build_ebook_covers.py`
- `build_cover_pdfs.py`
- `build_audiobooks.py`
- `embed_images.py`
- `generate_book_images.py`

### Step 2: Create Book 3 MASTER.md
Convert `book_3/Sams_Third_Superpower.docx` into a proper MASTER.md matching the format of Books 1, 2, 4, 5:
- Title page, chapter headers, illustration markers, back matter
- Superpower: "Heightened senses -- the ability to detect clues"
- 5 chapters matching docx structure
- Phonics: blends and digraphs (sh, ch, th, bl, cr, st)
- Create `book_3/manuscript/` directory to match Books 4-5 structure

### Step 3: Add Book 3 to build_books.py
Add Book 3 config entry to BOOKS list so it generates EPUB + KDP DOCX + HTML reader.

### Step 4: Add Book 3 to embed_images.py and generate_book_images.py
- embed_images.py: add Book 3 HTML path
- generate_book_images.py: add Book 3 with custom prompts (8 scenes based on docx)

### Step 5: Rebuild ALL 5 books (EPUB + DOCX + HTML)
Run `build_books.py` to regenerate all formats from MASTER.md files, ensuring uniform output.

### Step 6: Re-embed images in all HTML readers
Run `embed_images.py` to base64-embed all images for Android compatibility.

### Step 7: Rebuild all 10 covers
Run `build_cover_pdfs.py` (5 paperback wraps) and `build_ebook_covers.py` (5 ebook JPEGs).

### Step 8: Update stale knowledge base bible
Update `/06_DEVELOPMENT/everlight_os/knowledge/sam_and_robo_bible.md` with actual superpower names instead of placeholders.

### Step 9: Update SHIPPING_BOOK_IMAGES
Add missing Books 3 and 5 entries to the shipping directory.

## Files to Modify
- `build_books.py` -- path update + add Book 3
- `build_ebook_covers.py` -- path update
- `build_cover_pdfs.py` -- path update
- `build_audiobooks.py` -- path update
- `embed_images.py` -- path update + add Book 3
- `generate_book_images.py` -- path update + add Book 3
- `book_3/manuscript/Sams_Third_Superpower_MASTER.md` -- NEW
- `everlight_os/knowledge/sam_and_robo_bible.md` -- update superpowers

## Verification
1. Run each build script and confirm 5 outputs per format (no errors)
2. Verify all PDFs are 12.360 x 9.250" with safe-zone compliance
3. Verify all ebook covers are 1600x2560
4. Spot-check Book 3 EPUB opens correctly
5. Confirm MASTER.md superpower sequence: animals > science > senses > nature > leadership
