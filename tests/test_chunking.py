"""Tests for page-to-chunk conversion."""

import pytest

from docquery_mcp.chunking import chunk_page, chunk_text
from docquery_mcp.schemas import PdfPage


def test_chunk_text_uses_overlap() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=4, chunk_overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_chunk_text_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="smaller than chunk_size"):
        chunk_text("hello", chunk_size=5, chunk_overlap=5)


def test_chunk_page_preserves_source_metadata() -> None:
    page = PdfPage(
        document_name="example.pdf",
        page_number=3,
        text="Security controls require documented review.",
    )

    chunks = chunk_page(page, chunk_size=20, chunk_overlap=5)

    assert chunks[0].chunk_id == "example.pdf:page-3:chunk-1"
    assert chunks[0].document_name == "example.pdf"
    assert chunks[0].page_number == 3
