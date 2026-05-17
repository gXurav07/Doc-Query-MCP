"""Tests for PDF text extraction."""

from pathlib import Path

import fitz

from docquery_mcp.pdf_loader import load_pdf_pages


def create_pdf(path: Path, page_texts: list[str]) -> None:
    """Create a small text PDF for loader tests."""

    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_load_pdf_pages_extracts_text_and_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, ["First page text", "Second page text"])

    pages = load_pdf_pages(pdf_path)

    assert len(pages) == 2
    assert pages[0].document_name == "sample.pdf"
    assert pages[0].page_number == 1
    assert "First page text" in pages[0].text
    assert pages[1].page_number == 2
    assert "Second page text" in pages[1].text
