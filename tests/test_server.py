"""Tests for MCP server registration helpers."""

import anyio

from docquery_mcp.server import ANSWERING_INSTRUCTIONS, mcp, serialize_result
from docquery_mcp.schemas import QueryResult, SourceCitation


def test_query_documents_tool_is_registered() -> None:
    tools = anyio.run(mcp.list_tools)

    assert any(tool.name == "query_documents" for tool in tools)


def test_answering_instructions_are_available_for_tool_output() -> None:
    assert "retrieved_context" in ANSWERING_INSTRUCTIONS
    assert "document_name and page_number" in ANSWERING_INSTRUCTIONS
    assert "additional query_documents calls" in ANSWERING_INSTRUCTIONS


def test_serialize_result_returns_plain_dictionary() -> None:
    result = QueryResult(
        answer="Answer text",
        sources=[
            SourceCitation(
                document_name="sample.pdf",
                page_number=1,
                score=0.5,
                excerpt="Source excerpt",
            )
        ],
    )

    serialized = serialize_result(result)

    assert serialized == {
        "answer": "Answer text",
        "sources": [
            {
                "document_name": "sample.pdf",
                "page_number": 1,
                "score": 0.5,
                "excerpt": "Source excerpt",
            }
        ],
    }
