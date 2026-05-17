"""Tests for grounded answer formatting."""

from docquery_mcp.answerer import ExtractiveAnswerer
from docquery_mcp.schemas import DocumentChunk, RetrievedChunk


def test_answer_includes_sources_with_scores() -> None:
    chunk = DocumentChunk(
        chunk_id="iso.pdf:page-2:chunk-1",
        document_name="iso.pdf",
        page_number=2,
        text="ISO 27001 defines requirements for an information security management system.",
    )
    retrieved = RetrievedChunk(chunk=chunk, score=0.87)

    result = ExtractiveAnswerer().answer("What is ISO 27001?", [retrieved])

    assert "Relevant document excerpts" in result.answer
    assert "iso.pdf" in result.answer
    assert result.sources[0].document_name == "iso.pdf"
    assert result.sources[0].page_number == 2
    assert result.sources[0].score == 0.87
    assert "information security management system" in result.sources[0].excerpt


def test_answer_handles_no_retrieved_chunks() -> None:
    result = ExtractiveAnswerer().answer("Unknown question?", [])

    assert "could not find relevant information" in result.answer
    assert result.sources == []
