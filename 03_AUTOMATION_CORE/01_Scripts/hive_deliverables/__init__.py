"""
Hive Deliverables - Generate professional PDFs, Excel, and PowerPoint files.
Viktor's #1 feature gap: turning data into branded deliverables.

Usage:
    from hive_deliverables import generate_pdf, generate_excel, generate_pptx

    # PDF report
    pdf_path = generate_pdf(
        title="Broker OS Daily Report",
        sections=[{"heading": "Pipeline", "body": "436 leads, 4872 matches..."}],
    )

    # Excel spreadsheet
    xlsx_path = generate_excel(
        title="Lead Export",
        sheets={"Leads": [{"name": "...", "email": "..."}]},
    )

    # PowerPoint deck
    pptx_path = generate_pptx(
        title="Investor Update",
        slides=[{"title": "Revenue", "body": "$10k MRR target"}],
    )
"""
from .pdf_gen import generate_pdf
from .excel_gen import generate_excel
from .pptx_gen import generate_pptx

__all__ = ["generate_pdf", "generate_excel", "generate_pptx"]
