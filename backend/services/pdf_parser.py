import fitz  # PyMuPDF


def extract_pages(pdf_bytes: bytes) -> list[dict]:
    """Extract text per page. Returns [{page_number, text}] for non-empty pages."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page_number": i + 1, "text": text})
        return pages
    finally:
        doc.close()
