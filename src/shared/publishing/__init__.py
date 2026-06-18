"""Publishing pipeline shared utilities.

Submodules:
  - book_config: Central book registry (BOOKS, BASE_DIR, etc.)
  - image_utils: Image compression, drawing helpers
  - markdown_utils: Markdown parsing/stripping
  - openai_images: DALL-E generation + download (requires `requests`)

Import from submodules directly to avoid pulling in heavy deps:
  from shared.publishing.book_config import BOOKS, BASE_DIR
  from shared.publishing.image_utils import compress_image
"""

