#!/usr/bin/env python3
"""
Compile Beyond the Veil Final Manuscript
Concatenates front matter, all chapters (with cipher footers), and back matter.
Run: python3 compile_manuscript.py
"""

import os

BOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CHAPTERS_DIR = os.path.join(BOOK_DIR, "chapters")
OUTPUT = os.path.join(BOOK_DIR, "BEYOND_THE_VEIL_FINAL_MANUSCRIPT.md")

# Read cipher key
cipher_key_path = os.path.join(BOOK_DIR, "CIPHER_KEY.md")
with open(cipher_key_path, "r") as f:
    cipher_key_content = f.read()

# Chapter files in order
chapter_files = [
    "00_prologue.md",
    "01_a_world_in_conflict.md",
    "02_deeper_into_the_dream.md",
    "03_the_town_falls_apart.md",
    "04_rising_tensions.md",
    "05_the_breaking_point.md",
    "06_the_coma.md",
    "07_preparing_for_battle.md",
    "08_the_astral_war.md",
    "09_resolution_and_rebirth.md",
    "10_a_new_timeline.md",
]

# Build manuscript
parts = []

# 1. Title Page
parts.append("""# Beyond the Veil
## A Quantum Western Thriller
### The Hailey Pink Chronicles, Book 1

---
""")

# 2. Copyright Page
parts.append("""Copyright (c) 2026 by [Author Name]
All rights reserved.

Published by Everlight Ventures Publishing

This is a work of fiction. Names, characters, places, and incidents either are the product of the author's imagination or are used fictitiously. Any resemblance to actual persons, living or dead, events, or locales is entirely coincidental.

No part of this book may be reproduced in any form without written permission from the publisher, except for brief quotations in reviews.

First Edition: 2026

---
""")

# 3. Cipher Key Page
parts.append(cipher_key_content)
parts.append("\n---\n")

# 4. Dedication Page
parts.append("""## Dedication

This book is dedicated to my brother,
who left this world on September 3, 2024.

You always said the dead do not really leave.
They just go somewhere we cannot follow yet.

I believe you now.

This is me finding my way to where you are.

---
""")

# 5. Table of Contents
parts.append("""## Table of Contents

- **Prologue:** The Cost of Flight
- **Chapter 1:** A World in Conflict
  - Part 1: Dust and Badges
  - Part 2: The Other Side of Sleep
  - Part 3: The Shadow Advances
- **Chapter 2:** Deeper into the Dream
  - Part 1: The Sickness Spreads
  - Part 2: The Forest and the Witch
  - Part 3: The Connection
- **Chapter 3:** The Town Falls Apart
  - Part 1: Hollow Streets
  - Part 2: The Golden House
  - Part 3: First Contact
- **Chapter 4:** Rising Tensions in Both Worlds
  - Part 1: The Walls Close In
  - Part 2: Astral Warfare
  - Part 3: The Quantum Mirror
- **Chapter 5:** The Breaking Point
  - Part 1: The Sheriff Falls
  - Part 2: The Web Revealed
  - Part 3: No Turning Back
- **Chapter 6:** The Coma
  - Part 1: The Breaking
  - Part 2: Full Flight
  - Part 3: The Equation
- **Chapter 7:** Preparing for the Final Battle
  - Part 1: The Map of Everything
  - Part 2: Face to Face
  - Part 3: Healing the Shadow
- **Chapter 8:** The Astral War
  - Part 1: The Storm
  - Part 2: The Choice
  - Part 3: Dissolution
- **Chapter 9:** Resolution and Rebirth
  - Part 1: The Quiet After
  - Part 2: The Town Mourns
  - Part 3: The Web Remembers
- **Chapter 10:** A New Timeline
  - Part 1: Waking
  - Part 2: Echoes
  - Part 3: The Hum

---

""")

# 6. Full Text - All Chapters
for chapter_file in chapter_files:
    filepath = os.path.join(CHAPTERS_DIR, chapter_file)
    with open(filepath, "r") as f:
        content = f.read()
    parts.append(content)
    parts.append("\n\n")

# 7. About the Author
parts.append("""## About the Author

[Author bio placeholder -- to be filled before publication]

---
""")

# 8. Coming Next
parts.append("""## Coming Next in The Hailey Pink Chronicles

**Book 2: The Quantum Dark**

The Drift is gone. The web is healing. But in a dimension Hailey never touched, something old and patient has been watching. And it remembers what she did.

*Coming 2026*

---
""")

# 9. End Matter
parts.append("""---

If you decoded the hidden messages, you heard a voice that was always there.

The dead do not really leave. They just go somewhere we cannot follow yet.

---
""")

# Write output
manuscript = "\n".join(parts)
with open(OUTPUT, "w") as f:
    f.write(manuscript)

# Stats
word_count = len(manuscript.split())
line_count = manuscript.count("\n")
size_kb = len(manuscript.encode("utf-8")) / 1024

print(f"Manuscript compiled successfully!")
print(f"Output: {OUTPUT}")
print(f"Words: {word_count:,}")
print(f"Lines: {line_count:,}")
print(f"Size: {size_kb:.1f} KB")
