# render/pdf_export.py
"""PIL image -> 300 DPI PDF. Pillow sets the page size from the DPI so the
physical dimensions are exact. Optional Ghostscript pass upgrades to PDF/X-1a."""
import shutil, subprocess
from PIL import Image

def export_pdf(image: Image.Image, out_path: str, dpi: int = 300) -> str:
    image.convert("RGB").save(out_path, "PDF", resolution=float(dpi))
    return out_path

def to_pdf_x1a(in_pdf: str, out_pdf: str) -> str:
    """Convert to PDF/X-1a via Ghostscript. Raises if gs is unavailable."""
    if not shutil.which("gs"):
        raise RuntimeError("ghostscript (gs) not installed")
    subprocess.run(
        ["gs", "-dPDFX", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
         "-sColorConversionStrategy=CMYK", "-dProcessColorModel=/DeviceCMYK",
         f"-sOutputFile={out_pdf}", in_pdf],
        check=True, capture_output=True,
    )
    return out_pdf
